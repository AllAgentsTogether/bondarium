#!/usr/bin/env python3
"""Gemeinsame Helfer für die update_*.py-Skripte.

Nur Standardbibliothek – KEINE externen Abhängigkeiten (die Pipeline
installiert ausschließlich pdfplumber). Die Skripte laufen in GitHub Actions
als `python scripts/update_xxx.py` vom Repo-Root; das Skript-Verzeichnis liegt
dann auf sys.path, daher funktioniert `from _common import ...` direkt.

Konsolidiert die bislang vierfach duplizierten Helfer:
- write_atomic  (vorher _write_atomic in allen vier Skripten)
- plausible     (vorher _plausible in update_data.py und update_valuations.py;
  seit 09/2026 auch mit absoluter Schranke max_abs für Renditen)
- get_with_retry (vorher Retry-Varianten in update_sentiment.py und
  update_verlierer.py; update_data.py und update_valuations.py hatten
  bisher keinen Retry und bekommen ihn hierüber)
- now_iso / today_iso (vorher in jedem Skript einzeln ausgeschriebene
  Zeitstempel-Zeilen für "updated"/"updatedAt")
"""

import datetime
import email.utils
import http.client
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

# Chrome-Browserkennung – bisher identisch dupliziert in update_sentiment.py
# und update_verlierer.py. Hinweis: Das Vortäuschen eines Browsers gegenüber
# inoffiziellen Endpunkten (CNN, Nasdaq, AAII) birgt ToS-/Sperr-Risiken –
# offizielle Quellen (FRED, Treasury, CBOE) sind zu bevorzugen.
UA_CHROME = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)
HEADERS = {"User-Agent": UA_CHROME, "Accept": "*/*"}


def log_err(msg: str) -> None:
    """Kurzer Warn-Logger nach stderr (für bislang stumme except-Zweige).

    In GitHub Actions (Umgebungsvariable GITHUB_ACTIONS) zusätzlich als
    ::warning::-Annotation auf stdout – die Warnung erscheint dann in der
    Lauf-Zusammenfassung, obwohl die Updater mit continue-on-error laufen
    und ein Fehlschlag sonst nur im Schritt-Protokoll sichtbar wäre.
    Workflow-Kommandos müssen einzeilig sein; Zeilenumbrüche und '%'
    werden nach GitHub-Konvention maskiert (%0A, %0D, %25)."""
    print(f"WARN: {msg}", file=sys.stderr, flush=True)
    if os.environ.get("GITHUB_ACTIONS"):
        einzeilig = (str(msg).replace("%", "%25")
                     .replace("\r", "%0D").replace("\n", "%0A"))
        print(f"::warning::{einzeilig}", flush=True)


def now_iso() -> str:
    """Aktueller UTC-Zeitstempel im Format 2026-09-02T22:47:51Z (Feld updatedAt/checkedAt)."""
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def today_iso() -> str:
    """Heutiges Datum als ISO-String 2026-09-02 (Feld updated/asOf).
    Bewusst today_iso() statt today() benannt: In mehreren Skripten heißt eine
    lokale Variable bereits `today` (date-Objekt) – ein gleichnamiger Import
    würde dort zu Verwechslungen/UnboundLocalError einladen."""
    return datetime.date.today().isoformat()


def write_atomic(path: Path, obj, indent: int = 1) -> None:
    """JSON atomar schreiben: erst in temporäre Datei im selben Verzeichnis,
    dann os.replace() – so entsteht nie eine halb geschriebene/korrupte Datei."""
    text = json.dumps(obj, ensure_ascii=False, indent=indent) + "\n"
    tmp = path.with_name(path.name + ".tmp")
    try:
        tmp.write_text(text, encoding="utf-8")
        os.replace(tmp, path)
    except BaseException:
        tmp.unlink(missing_ok=True)  # keine .tmp-Leiche zurücklassen
        raise


def plausible(new: float, old, label: str, max_rel: float = 0.5,
              max_abs: float | None = None) -> bool:
    """True, wenn der neue Wert nicht zu stark vom zuletzt gespeicherten abweicht.
    Fängt grobe Parser-/Einheitenfehler ab (z. B. Faktor 10 durch falsche Spalte),
    lässt aber normale Bewegungen zu. Ohne (numerischen) Vorwert immer True.

    max_rel: relative Höchstabweichung (0.5 = 50 %) – für Kurse/Kennzahlen.
    max_abs: absolute Höchstabweichung in der Einheit des Werts (z. B. 2,5
             Prozentpunkte bei Renditen). Ist max_abs gesetzt, wird NUR absolut
             geprüft – eine relative Prüfung taugt bei Werten nahe null nicht.
    Ein verworfener Wert wird per log_err gemeldet (in GitHub Actions als
    ::warning::-Annotation sichtbar)."""
    if old is None:
        return True
    try:
        old = float(old)
        new = float(new)
    except (TypeError, ValueError):
        return True
    if max_abs is not None:
        if abs(new - old) > max_abs:
            log_err(f"{label}: {new} weicht > {max_abs:g} vom Vorwert {old} ab "
                    f"(absolut) – verworfen (vermutlich Parser-/Quellenfehler).")
            return False
        return True
    if old > 0 and abs(new - old) / old > max_rel:
        log_err(f"{label}: {new} weicht >{int(max_rel * 100)} % vom Vorwert {old} ab "
                f"– verworfen (vermutlich Parser-Fehler).")
        return False
    return True


# HTTP-Statuscodes, bei denen ein Wiederholversuch sinnvoll ist: Zeitüberschreitung
# der Anfrage (408), Ratenbegrenzung (429) und Serverfehler (5xx). Alle übrigen
# 4xx (403 gesperrt, 404 nicht vorhanden, 401 …) sind dauerhaft – ein erneuter
# Versuch würde nur Zeit kosten und die Sperre ggf. verschärfen.
_RETRY_CODES = frozenset({408, 429})
_RETRY_AFTER_MAX = 30.0  # Sekunden – Obergrenze für ein Retry-After des Servers


def _retry_after_seconds(headers) -> float | None:
    """Wartezeit aus dem Retry-After-Header (Sekunden oder HTTP-Datum), auf
    0–_RETRY_AFTER_MAX Sekunden begrenzt; None, wenn Header fehlt/unlesbar."""
    try:
        raw = headers.get("Retry-After") if headers is not None else None
    except Exception:  # noqa: BLE001 – exotische Header-Objekte
        raw = None
    if not raw:
        return None
    raw = str(raw).strip()
    secs: float | None = None
    if raw.isdigit():
        secs = float(raw)
    else:
        try:
            when = email.utils.parsedate_to_datetime(raw)
            if when.tzinfo is None:
                when = when.replace(tzinfo=datetime.timezone.utc)
            secs = (when - datetime.datetime.now(datetime.timezone.utc)).total_seconds()
        except (TypeError, ValueError, IndexError):
            return None
    return max(0.0, min(secs, _RETRY_AFTER_MAX))


def _should_retry(exc: BaseException) -> bool:
    """Wiederholen nur bei Netzfehlern (Timeout, Verbindungsabbruch, DNS, TLS,
    unvollständige Antwort) sowie HTTP 408/429/5xx. HTTPError ist eine Unterklasse
    von URLError/OSError und muss daher ZUERST geprüft werden."""
    if isinstance(exc, urllib.error.HTTPError):
        return exc.code in _RETRY_CODES or 500 <= exc.code <= 599
    # URLError (DNS/Verbindung), OSError (socket.timeout, TimeoutError, TLS,
    # ConnectionReset), http.client.HTTPException (IncompleteRead, BadStatusLine)
    return isinstance(exc, (urllib.error.URLError, OSError, http.client.HTTPException))


def get_with_retry(url: str, headers: dict | None = None, timeout: int = 30,
                   tries: int = 3, backoff: float = 2.0, data: bytes | None = None) -> bytes:
    """HTTP-GET (bzw. POST, wenn data gesetzt ist – z. B. b"" für Endpunkte, die
    nur POST annehmen wie die ChinaBond-Renditekurve) mit Wiederholversuchen und linear wachsender Wartezeit
    (backoff * Versuchsnummer Sekunden, wie bisher in update_sentiment.py;
    für tries=2 identisch zur alten festen 2-s-Pause in update_verlierer.py).

    Wiederholt wird NUR bei Netzfehlern und HTTP 408/429/5xx (siehe
    _should_retry); HTTP 403/404 & Co. werden sofort weitergeworfen. Bei 429
    (und 503, gleiche Semantik) wird ein Retry-After des Servers beachtet –
    gedeckelt auf 30 s, damit ein einzelner Abruf den Lauf nicht blockiert.
    Beim endgültigen Fehlschlag wird die letzte Exception weitergeworfen."""
    hdrs = dict(HEADERS) if headers is None else dict(headers)
    for attempt in range(tries):
        try:
            req = urllib.request.Request(url, data=data, headers=hdrs)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read()
        except Exception as exc:
            if attempt == tries - 1 or not _should_retry(exc):
                raise
            wait = backoff * (attempt + 1)
            if isinstance(exc, urllib.error.HTTPError) and exc.code in (429, 503):
                ra = _retry_after_seconds(getattr(exc, "headers", None))
                if ra is not None:
                    wait = ra
            print(f"HTTP-Abruf fehlgeschlagen (Versuch {attempt + 1}/{tries}: "
                  f"{type(exc).__name__}: {exc}) – neuer Versuch in {wait:g} s: {url}",
                  file=sys.stderr, flush=True)
            time.sleep(wait)
    raise RuntimeError("unreachable")


# ---------------------------------------------------------------- Anleihen: gemeinsame Regeln (seit 26.09.2026)
# Für update_kurse.py (Rendite, Aufschlag, Bund-Verlauf), update_top10.py (Auswahl) und update_langlaeufer.py
# (Ausreißer) – eine Regel an einer Stelle. Hintergrund: Prüfbericht Datenbasis der Anleihen vom 26.09.2026.

# Zinstermine (seit 02.10.2026): Die Termine stehen in zinstermine/zinstermine.json – aus der Instrumentenliste der
# Deutschen Börse (scripts/update_zinstermine.py). Nur wo sie fehlen, gilt die Schätzregel zinsfrequenz().
# Währungen mit halbjährlicher Zinszahlung im Heimatmarkt und das ISIN-Land dieses Markts. Gemessen an der Börsenliste
# (02.10.2026): mit Heimat-ISIN zahlen praktisch alle halbjährlich, mit internationaler ISIN (XS, DE, FR …) die meisten
# jährlich – außer in US-Dollar (dort 88 % halbjährlich; deutsche und österreichische Emittenten jährlich) und Yen.
HEIMATMARKT = {"USD": "US", "GBP": "GB", "CAD": "CA", "AUD": "AU", "NZD": "NZ", "JPY": "JP", "MXN": "MX", "ZAR": "ZA",
               "HKD": "HK", "SGD": "SG"}
REG_S = re.compile(r"reg\.?\s?s\b|144a", re.I)             # Hochzins-Bauart (Rule 144A/Regulation S): meist halbjährlich
MTN = re.compile(r"med|mtn|m\.-t\.", re.I)                 # Medium-Term Notes: auch mit „Reg.S“ jährlich
ZINSTERMINE = Path(__file__).resolve().parent.parent / "zinstermine" / "zinstermine.json"
INFLATION = re.compile(r"infl|inflat|linker|\blkd\b|i/l|\btips\b|hicp|hvpi|\bcpi\b|\brpi\b|index", re.I)
FLR = re.compile(r"FLR\b|floating|\bFRN\b|variab|\bvar\.", re.I)          # variabel, Fix-to-Float, Reset – „FLR“ ohne Wortgrenze davor: WM klebt es an den Emittenten („AGFLR-Anleihe“, 27.09.2026)
STUFE = re.compile(r"stufenz|step[ -]?up|step[ -]?down|\bstep\b", re.I)     # Stufenzins
# Wandel-/Umtauschanleihen: „Conv.“, „Exch.“, „Exchang.“ – nicht „Intercontinental Exchange“, „Convex“
WANDEL = re.compile(r"wandel|umtausch|\bconv\.|\bconvertible|\bexch\.|\bexchang\.|\bexchangeable", re.I)
# Tilgung in Raten laut WM-Name: Tilgungsspanne „2020(24-30)“, „(20/28-41)“ oder „Tilgungsanleihe“
TILGUNG = re.compile(r"\(\s*(?:\d{2,4}\s*/\s*)?\d{2,4}\s*-\s*\d{2,4}\s*\)|tilg", re.I)
TILGUNG_SPANNE = re.compile(r"\(\s*(?:\d{2,4}\s*/\s*)?(\d{2,4})\s*-\s*(\d{2,4})\s*\)")


def tilgung_wesentlich(name: str, jahr_heute: int | None = None) -> bool:
    """Tilgung in Raten, die die Rendite bis Fälligkeit verfälscht: Tilgungsspanne im Namen, die schon läuft, im
    nächsten Jahr beginnt oder länger als zwei Jahre dauert („Argentinien 2020(24-30)“), oder „Tilg…“ ohne Spanne.
    Eine kurze Tilgung am Ende (Südafrika „RC-Loan 2012(47-49)“: je ein Drittel 2047, 2048, 2049) ändert die Rendite
    nur um Hundertstel – dann bleibt die Rendite bis Fälligkeit als Näherung."""
    if not TILGUNG.search(name or ""):
        return False
    m = TILGUNG_SPANNE.search(name)
    if not m:
        return True
    def jahr(t: str) -> int:
        v = int(t)
        return v if len(t) == 4 else (2000 + v if v < 70 else 1900 + v)
    erstes, letztes = jahr(m.group(1)), jahr(m.group(2))
    return erstes <= (jahr_heute or datetime.date.today().year) + 1 or letztes - erstes > 2


def zinsfrequenz(zeile: list) -> int:
    """GESCHÄTZTE Zinszahlungen je Jahr einer Indexzeile [isin, name, art, waehrung, …] – nur für Anleihen ohne
    Zinstermine in der Börsenliste (zinsplan()). Halbjährlich: Staatsanleihen Italiens und Maltas; Anleihen in einer
    Währung aus HEIMATMARKT mit der ISIN dieses Markts; US-Dollar-Anleihen von Staaten und – außer bei deutscher oder
    österreichischer ISIN bzw. Konzernsitz dort – von allen anderen; Yen-Anleihen; Euro-Unternehmensanleihen mit
    „Reg.S“/„144A“ im Namen, die keine Medium-Term Notes sind. Sonst jährlich."""
    isin, name, art, cur = zeile[0], zeile[1] or "", zeile[2], zeile[3]
    land = isin[:2]
    if art == 0 and land in ("IT", "MT"):
        return 2
    if cur in HEIMATMARKT:
        if land == HEIMATMARKT[cur] or cur == "JPY":
            return 2
        if cur == "USD":
            return 2 if art == 0 or not (land in ("DE", "AT") or zeile[11] in ("DE", "AT")) else 1
        return 1
    if cur == "EUR" and art == 2 and REG_S.search(name) and not MTN.search(name):
        return 2
    return 1


def zinstermine_laden() -> dict:
    """{ISIN: [zahlungen_je_jahr, "MM-TT", …]} aus zinstermine/zinstermine.json (update_zinstermine.py); leer, wenn
    die Datei fehlt."""
    try:
        return json.loads(ZINSTERMINE.read_text(encoding="utf-8")).get("termine") or {}
    except (OSError, json.JSONDecodeError):
        return {}


def zinsplan(zeile: list, termine: dict) -> tuple[int, list | None]:
    """(Zahlungen je Jahr, Zinstage ["MM-TT", …] oder None) einer Indexzeile: aus der Börsenliste, sonst geschätzt
    (zinsfrequenz(), Tage None = am Jahrestag der Fälligkeit)."""
    e = termine.get(zeile[0])
    if e and len(e) > 1:
        return e[0], e[1:]
    return zinsfrequenz(zeile), None


def zins_felder(zeile: list, termine: dict) -> dict:
    """Felder einer Listenzeile (Top-10-Dateien): zins = Zahlungen je Jahr, zt = Zinstage ["MM-TT", …] laut Börsenliste –
    zt fehlt, wenn der Rhythmus geschätzt ist (die Seiten nennen dann keinen Zinstermin)."""
    freq, tage = zinsplan(zeile, termine)
    return {"zins": freq, "zt": tage} if tage else {"zins": freq}


def monate_zurueck(d: datetime.date, m: int) -> datetime.date:
    """Datum minus m Monate, ohne Monatsüberlauf (31.05. → 30.11.). Ist d ein Monatsletzter am 30. oder 31., bleibt das
    Ergebnis ein Monatsletzter (30.11. → 31.05., wie bei US-Staatsanleihen; vorher 30.05., Nutzertest 03.10.2026). Ende
    Februar bleibt beim Tag – ob dort der 28. oder der Monatsletzte gemeint ist, lässt sich nicht erkennen. Gleiche Regel
    in bond.js (monthsBack)."""
    j, mo = divmod(d.year * 12 + d.month - 1 - m, 12)
    mo += 1
    letzter = (datetime.date(j + (mo == 12), mo % 12 + 1, 1) - datetime.timedelta(days=1)).day
    ende = d.day >= 30 and (d + datetime.timedelta(days=1)).month != d.month
    return datetime.date(j, mo, letzter if ende else min(d.day, letzter))


ENDE_TOLERANZ = 20   # Tage: Ein Zinstermin so kurz vor der Fälligkeit ist der Fälligkeitstag selbst (Bankarbeitstag-Verschiebung)


def zinszahlungen(kupon: float, faellig: datetime.date, valuta: datetime.date, freq: int,
                  tage: list | None = None) -> tuple[datetime.date, list[tuple[datetime.date, float]]]:
    """(letzter Zinstermin bis zum Valutatag, [(Termin, Zins in % des Nennwerts) …] nach dem Valutatag bis zur Fälligkeit).
    Mit tage (Zinstage „MM-TT“ aus der Börsenliste) fallen die Termine jedes Jahr auf diese Tage; der letzte Zins kommt am
    Fälligkeitstag – liegt der mehr als ENDE_TOLERANZ Tage hinter dem letzten Zinstag, anteilig nach Tagen (kurze
    Schlussperiode). Ohne tage (Schätzung): vom Fälligkeitstag in Schritten von 12/freq Monaten rückwärts, ein Monatsende
    bleibt Monatsende (31.08. → 28.02. → 31.08.). Dieselbe Rechnung in bond.js (couponDates)."""
    c = kupon / freq
    if not tage:
        termine, t, k = [], faellig, 0
        while t > valuta:
            termine.insert(0, (t, c))
            k += 1
            t = monate_zurueck(faellig, k * 12 // freq)
        return t, termine

    def im_jahr(j: int) -> list[datetime.date]:
        out = []
        for md in tage:
            mo, tg = int(md[:2]), int(md[3:])
            letzter = (datetime.date(j + (mo == 12), mo % 12 + 1, 1) - datetime.timedelta(days=1)).day
            out.append(datetime.date(j, mo, min(tg, letzter)))
        return out
    grenze = faellig - datetime.timedelta(days=ENDE_TOLERANZ)
    alle = sorted(d for j in range(valuta.year - 1, faellig.year + 1) for d in im_jahr(j))
    vorher = max(d for d in alle if d <= valuta and d < grenze)
    termine = [(d, c) for d in alle if valuta < d < grenze]
    davor = max(d for d in alle if d < grenze)                 # letzter Zinstag vor der Fälligkeit
    naechster = min((d for d in alle + im_jahr(faellig.year + 1) if d >= grenze), default=None)
    regulaer = naechster is not None and abs((naechster - faellig).days) <= ENDE_TOLERANZ
    schluss = c if regulaer else kupon * (faellig - davor).days / 365.25
    termine.append((faellig, schluss))
    return vorher, termine


def ohne_rendite(zeile: list) -> str | None:
    """Grund, warum für eine Anleihe (Indexzeile) keine Rendite bis Fälligkeit gerechnet wird – None: rechnen.
    Eine Rendite bis Fälligkeit gibt es nur für festen Kupon oder Nullkupon mit Rückzahlung am Ende auf einmal."""
    name = zeile[1] or ""
    if len(zeile) > 14 and isinstance(zeile[14], dict) and zeile[14]:
        return "Registerangaben widersprüchlich"   # Feld pruef (update_anleihen_index.py, seit 27.09.2026): Kurzname/Name gegen Register
    if zeile[10] not in (0, 2) or not isinstance(zeile[4], (int, float)) or not zeile[5]:
        return "variabel, Kupon unbekannt oder unbefristet"
    if INFLATION.search(name):
        return "inflationsindexiert"
    if FLR.search(name):
        return "variabel oder Fix-to-Float"
    if STUFE.search(name):
        return "Stufenzins"
    if WANDEL.search(name):
        return "Wandel-/Umtauschanleihe"
    if tilgung_wesentlich(name):
        return "Tilgung in Raten"
    return None


def ausreisser(werte: list, schwelle: float = 0.08, renditen: list | None = None, schwelle_mit_rendite: float = 0.04) -> set:
    """Indizes einzelner Ausreißer einer Kursreihe (Fehler der Quelle, z. B. Bundesbank BBSSY am 30.04.2021: Bund 2042
    bei 101,01 zwischen 165,34 und 163,60). Ein Punkt ist ein Ausreißer, wenn er von BEIDEN Nachbarn in dieselbe
    Richtung abweicht, und zwar
      - um mehr als `schwelle` (8 %) – so springt kein Anleihekurs hin und sofort zurück, oder
      - mit Renditen (gleich lang wie werte): um mehr als `schwelle_mit_rendite` (4 %), während die Rendite nicht
        gegenläufig mitgeht (Kurs hoch, Rendite nicht mindestens 0,05 Punkte tiefer – bzw. umgekehrt). Echte
        Bewegungen (Oktober 2022, August 2010) haben immer die gegenläufige Rendite und bleiben stehen.
    Der erste und der letzte Punkt lassen sich nicht prüfen."""
    def zahl(x):
        return isinstance(x, (int, float)) and not isinstance(x, bool)
    raus = set()
    for i in range(1, len(werte) - 1):
        a, p, b = werte[i - 1], werte[i], werte[i + 1]
        if not all(zahl(x) and x > 0 for x in (a, p, b)):
            continue
        da, db = p / a - 1, p / b - 1
        if da * db <= 0:
            continue
        m = min(abs(da), abs(db))
        if m > schwelle:
            raus.add(i)
        elif renditen is not None and m > schwelle_mit_rendite:
            ra, rp, rb = renditen[i - 1], renditen[i], renditen[i + 1]
            if all(zahl(x) for x in (ra, rp, rb)):
                richtung = 1 if da > 0 else -1          # Kurs gestiegen: Rendite hätte fallen müssen
                if (rp - ra) * richtung > -0.05 and (rp - rb) * richtung > -0.05:
                    raus.add(i)
    return raus


# ---------------------------------------------------------------- Anleihen-Angaben (seit 03.10.2026)
# Feldkatalog, Kurzname und Schreibweisen – dieselben Regeln wie felder.js (MC.felder) auf der Website. Der Katalog selbst steht
# einmal in felder.js zwischen /*KATALOG*/ und /*KATALOG-ENDE*/ (reines JSON); hier wird er gelesen, nicht kopiert.
# Konzept „Einheitliche Anleihen-Angaben“, Regeln in docs/ANLEIHEN-ANGABEN.md.
_KATALOG = None


def felder_katalog() -> dict:
    """Katalog aus felder.js: {felder, art, bonitaet, rechtsform, staaten}."""
    global _KATALOG
    if _KATALOG is None:
        quelle = (Path(__file__).resolve().parent.parent / "felder.js").read_text(encoding="utf-8")
        m = re.search(r"/\*KATALOG\*/(.*?)/\*KATALOG-ENDE\*/", quelle, re.S)
        _KATALOG = json.loads(m.group(1))
    return _KATALOG


# Lesbare Schreibung der GLEIF-Versalien (gleiche Regel wie MC.felder.lesbar in felder.js)
RF_SCHREIB = {"AG": "AG", "SE": "SE", "KG": "KG", "KGAA": "KGaA", "GMBH": "GmbH", "MBH": "mbH", "N.V.": "N.V.", "B.V.": "B.V.", "S.A.": "S.A.", "S.A": "S.A.",
              "S.P.A.": "S.p.A.", "SPA": "S.p.A.", "S.A.S.": "S.A.S.", "S.À": "S.à", "R.L.": "r.l.", "S.R.L.": "S.r.l.", "SRL": "S.r.l.", "S.L.": "S.L.", "SARL": "S.à r.l.",
              "INC.": "Inc.", "INC": "Inc.", "LTD.": "Ltd.", "LTD": "Ltd", "CORP.": "Corp.", "CORP": "Corp.", "CO.": "Co.", "CO": "Co.", "PTE.": "Pte.", "PTE": "Pte.", "PTY": "Pty",
              "OYJ": "Oyj", "P.L.C.": "p.l.c.", "L.P.": "L.P.", "LLP": "LLP", "LLC": "LLC", "PLC": "PLC", "A/S": "A/S", "ASA": "ASA", "AB": "AB", "AS": "AS", "SA": "SA",
              "NV": "NV", "BV": "BV", "SAS": "SAS", "C.V.": "C.V.", "S.A.B.": "S.A.B.", "KFW": "KfW", "ENBW": "EnBW", "E.ON": "E.ON", "AT&T": "AT&T"}
RF_IMMER = {"KFW", "ENBW", "E.ON", "AT&T"}
KLEINWORT = set("OF AND THE FOR DE DI DEL DELLA DES DU LA LE LES Y E ET EN IN FÜR UND DER DIE DAS DEN VON VAN ZU AM IM AUF PER DA DO DOS".split())
KUERZEL = set("BASF BBVA AMRO BAWAG NIBC RATP SICAV SOFOM HSBC LBBW NRW USA UK US EU".split())
WORT3 = set("OIL GAS NEW AIR SEA SUN BAY CAR ONE TWO TEN BIG RED OWL TOP WAY KEY AID ART BIO BOX CAP FIN LAB LAW MAX NET PAY PRO RIO SKY SOL TEA TEL WEB BAU".split())
_VOKAL = re.compile(r"[AEIOUYÄÖÜÉÈÀÁÍÓÚÂÊÎÔÛİ]")
_BUCHST = re.compile(r"([A-Za-zÀ-ÖØ-öø-ÿİŞĞÇ]+)")
_RAND = re.compile(r"^[,;()\"']+|[,;()\"']+$")


def _lesbar_wort(w, erstes, nach_apostroph):
    u = w.upper()
    if len(w) == 1:
        return w.lower() if nach_apostroph else w
    if not erstes and u in KLEINWORT:
        return w.lower()
    if u in KUERZEL or not _VOKAL.search(u):
        return w
    if len(w) <= 3 and u not in WORT3 and u not in KLEINWORT:
        return w
    return w[0] + w[1:].replace("İ", "i").lower()


def lesbar(name):
    s = str(name or "").strip()
    if not s or re.search(r"[a-zß-ÿ]", s) or not re.search(r"[A-Z]", s):
        return s   # schon gemischt geschrieben oder keine lateinische Schrift
    out = []
    for i, tok in enumerate(s.split()):
        kern = _RAND.sub("", tok)
        vor = tok[:tok.index(kern)] if kern else tok
        nach = tok[len(vor) + len(kern):] if kern else ""
        k = kern.upper()
        if k in RF_SCHREIB and (i > 0 or k in RF_IMMER):
            out.append(vor + RF_SCHREIB[k] + nach)
            continue
        teile = _BUCHST.split(tok)
        out.append("".join(_lesbar_wort(t, i == 0 and j == 1, (teile[j - 1] if j else "").endswith("'")) if j % 2 else t
                           for j, t in enumerate(teile)))
    return " ".join(out)


def kurz_name(emittent, art, land, reg=""):
    """Kurzname einer Anleihe: Staat (art 0, Land ≠ INT) → Ländername laut Katalog; sonst Emittent in lesbarer Schreibung ohne
    Rechtsform; ohne Emittent der Registername. Gleiche Regel wie MC.felder.kurzName."""
    k = felder_katalog()
    if art == 0 and land and land != "INT":
        return k["staaten"].get(land) or land
    e = lesbar(emittent)
    if not e:
        return str(reg or "")
    if e in k.get("ausnahmen", {}):
        return k["ausnahmen"][e]   # sperrige Registernamen großer Emittenten („Kreditanstalt für Wiederaufbau KfW“ → „KfW“)
    rf = re.compile(k["rechtsform"])
    for _ in range(3):
        e = re.sub(r"[\s&,\-–]+$", "", rf.sub("", e).strip())   # „Fresenius SE & Co. KGaA“ → „Fresenius“
    return e


def zahl_de(v, d=0) -> str:
    """Zahl mit Dezimalkomma, Tausenderpunkt und echtem Minus (wie MC.zahl)."""
    if not isinstance(v, (int, float)) or isinstance(v, bool):
        return "–"
    s = f"{abs(v):,.{d}f}".replace(",", "#").replace(".", ",").replace("#", ".")
    return ("−" if v < 0 and float(s.replace(".", "").replace(",", ".")) != 0 else "") + s


NBSP = " "


def pct_text(v) -> str:
    return zahl_de(v, 2) + NBSP + "%" if isinstance(v, (int, float)) else "–"


def kupon_text(kupon, zinsart=0) -> str:
    """„3,50 %“, „3,625 %“, „variabel“, „Nullkupon“ (wie MC.felder.kupon)."""
    if zinsart == 1 or kupon == "var":
        return "variabel"
    if zinsart == 2 or (kupon == 0 and zinsart != 0):
        return "Nullkupon"
    if not isinstance(kupon, (int, float)):
        return "–"
    return zahl_de(kupon, 3 if round(kupon * 1000) % 10 else 2) + NBSP + "%"


def kurs_text(v) -> str:
    if not isinstance(v, (int, float)):
        return "–"
    return zahl_de(v, 3 if abs(v * 100 - round(v * 100)) > 1e-6 else 2) + NBSP + "%"


def pkt_text(v, d=2) -> str:
    if not isinstance(v, (int, float)):
        return "–"
    r = round(v, d) or 0.0
    return ("+" if r > 0 else "") + zahl_de(r, d) + NBSP + "Pkt."


def datum_text(iso) -> str:
    return f"{iso[8:10]}.{iso[5:7]}.{iso[0:4]}" if iso and len(iso) >= 10 else "–"


def restlaufzeit_text(jahre) -> str:
    """Wie MC.restlaufzeit: unter einem Monat Tage, unter einem Jahr Monate, sonst Jahre mit einer Stelle."""
    if jahre is None:
        return "unbefristet"
    tage = int(jahre * 365.25 + 0.5)
    if tage <= 0:
        return "fällig"
    if tage < 31:
        return f"{tage} {'Tag' if tage == 1 else 'Tage'}"
    monate = int(tage / 30.44 + 0.5)
    if monate < 12:
        return f"{monate} {'Monat' if monate == 1 else 'Monate'}"
    return zahl_de(jahre, 1) + " Jahre"


def _signifikant(x: float, n: int = 3) -> str:
    """Höchstens n gültige Ziffern, ohne Endnullen, deutsch geschrieben (wie toLocaleString maximumSignificantDigits)."""
    if x == 0:
        return "0"
    import math
    stellen = max(0, n - 1 - int(math.floor(math.log10(abs(x)))))
    s = zahl_de(round(x, stellen), stellen)
    if "," in s:
        s = s.rstrip("0").rstrip(",")
    return s


def volumen_text(v, w="") -> str:
    """„1,25 Mrd. EUR“, „250 Mio. EUR“, unter 1 Mio. ganze Zahl (wie MC.felder.volumen)."""
    if not isinstance(v, (int, float)) or v <= 0:
        return "–"
    t = zahl_de(v, 0) if v < 1e6 else (_signifikant(v / 1e9) + NBSP + "Mrd." if v >= 1e9 else _signifikant(v / 1e6) + NBSP + "Mio.")
    return t + (NBSP + w if w else "")


def stueckelung_text(v, w="") -> str:
    if not isinstance(v, (int, float)):
        return "–"
    s = zahl_de(v, 3)
    if "," in s:
        s = s.rstrip("0").rstrip(",")
    return s + (NBSP + w if w else "")


def bonitaet_text(b) -> str:
    return felder_katalog()["bonitaet"].get(str(b), "") if b is not None else ""


def titel_text(kurz, kupon, zinsart, faellig) -> str:
    """„Italien 3,50 % 2030“ (wie MC.felder.titel)."""
    return f"{kurz} {kupon_text(kupon, zinsart)} {faellig[:4] if faellig else 'unbefristet'}"


def bonitaet_stufen() -> dict:
    """{ISIN: 1 | 3 | 0} aus bonitaet/ezb-stufen.json (scripts/update_bonitaet.py); fehlt die Datei: leer."""
    try:
        d = json.loads((Path(__file__).resolve().parent.parent / "bonitaet" / "ezb-stufen.json").read_text(encoding="utf-8"))
        return d.get("stufen") or {}
    except (OSError, ValueError):
        return {}


def stamm_felder(zeile: list, emittenten: list, stufen: dict) -> dict:
    """Felder, die jede Anleihen-Tabelle zum Namen braucht – aus einer Zeile von anleihen-index.json:
    kurz (Kurzname), bon (Bonität laut EZB, nur wenn auf der Liste). Für die Top-Listen (update_top10*.py) und anleihen-auswahl.json."""
    e = emittenten[zeile[9]] if isinstance(zeile[9], int) and 0 <= zeile[9] < len(emittenten) else ""
    out = {"kurz": kurz_name(e, zeile[2], zeile[11], zeile[1])}
    if zeile[0] in stufen:
        out["bon"] = stufen[zeile[0]]
    return out
