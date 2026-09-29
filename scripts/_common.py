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

# Halbjährliche Zinszahlung nach Währung (US-/britische Konvention usw.), sonst jährlich (Euro-Konvention)
HALBJAEHRLICH = {"USD", "GBP", "CAD", "AUD", "NZD", "JPY", "MXN", "ZAR", "HKD", "SGD"}
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
    """Zinszahlungen je Jahr einer Indexzeile [isin, name, art, waehrung, …]: halbjährlich in USD/GBP/CAD/AUD/NZD/
    JPY/MXN/ZAR/HKD/SGD und bei italienischen Staatsanleihen (BTP – ISIN IT, Art Staat), sonst jährlich."""
    return 2 if zeile[3] in HALBJAEHRLICH or (zeile[0].startswith("IT") and zeile[2] == 0) else 1


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
