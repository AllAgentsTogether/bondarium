#!/usr/bin/env python3
"""update_kurse.py – Tageskurse und Kursverlauf aller Anleihen der Suche und aller Anleihen/ETFs der Datenseiten.

Quellen (beide kostenlos, beide mit ausdrücklicher Erlaubnis zur Anzeige):
  * Deutsche Börse, MiFIR-Delayed-Data-Service (MiFIR Art. 13(2), Delegierte Verordnung (EU) 2025/1156):
    Nachhandelsdaten 15 Minuten verzögert, ohne Registrierung, als Tagesdatei je Handelsplatz
        https://mfs.deutsche-boerse.com/api/<Dienst>                  Dateiliste (JSON)
        https://mfs.deutsche-boerse.com/api/download/<Datei>          Download (Weiterleitung zu Google Cloud Storage)
    Dienste: DFRA-posttrade (Börse Frankfurt, Spezialisten-Kurse für ~33.000 Anleihen),
             DETR-posttrade (Xetra, ETFs), DGAT-posttrade (Tradegate).
    Nutzungsbedingungen (Stand 25.09.2026): kostenlose, nicht exklusive Lizenz, solange die Daten nicht
    kommerzialisiert werden (keine Weitergabe gegen Entgelt, keine verkauften Mehrwertdienste).
    Jede Datei bleibt nur etwa einen Börsentag abrufbar – deshalb sammelt dieses Skript den Verlauf selbst.
  * Deutsche Bundesbank, BBSSY: Kurs und Rendite börsennotierter Bundeswertpapiere (täglich, Historie seit Ausgabe).

Schreibt (alle im Website-Ordner):
  anleihen-kurse.json      Suche: {"stand", "tage": [Datum …], "kurse": {ISIN: [kurs, rendite, tag, boerse, umsatz, tagesdaten,
                           vortag, aufschlag]}}
                           kurs in % des Nennwerts; rendite in % p. a. oder null (BERECHNET, siehe unten); tag = Index in "tage";
                           boerse "F" Frankfurt · "T" Tradegate · "X" Xetra · "B" Bundesbank; umsatz in Anleihewährung
                           (Frankfurt + Tradegate, BERECHNET als Stück × Kurs; 0 = Kurs ohne Umsatz);
                           tagesdaten (seit 26.09.2026, geliefert von der Börse): [eroeffnung, hoch, tief, feststellungen,
                           abschluesse, umsatz_frankfurt, umsatz_tradegate, umsatz_xetra] – oder nur [feststellungen], wenn
                           alle Feststellungen des Tags denselben Kurs hatten und es keinen Umsatz gab (spart Platz) – oder null;
                           vortag: vorheriger Schlusskurs aus unserer Datei (für die Veränderung, BERECHNET) oder null;
                           aufschlag: Rendite minus Bund-Rendite gleicher Restlaufzeit in Prozentpunkten (BERECHNET, nur Euro-
                           Anleihen mit Rendite und bis 30 Jahren Restlaufzeit – seit 27.09.2026 auch unter einem halben
                           Jahr, das kürzeste Bundeswertpapier bildet den Anfang der Kurve; Bundeswertpapiere selbst: null)
                           oder null.
                           Einträge ohne neuen Kurs bleiben bis zu 45 Tage mit ihrem Datum stehen.
  kurse-auswahl.json       dieselben Felder für alle ISINs, die in den übrigen HTML-Seiten vorkommen (Länder, Laufzeit,
                           Langläufer, Startseite, ETFs) – klein, wird per inline_data.py in diese Seiten eingebettet.
                           ETFs: Kurs in Euro je Anteil (Xetra), umsatz in Euro.
  kurse/<Jahr>/<hh>.json   Kursverlauf ab 24.09.2026, 256 Teildateien je Jahr (hh = teil(ISIN), zwei Hex-Ziffern):
                           {"tage": [Datum …], "k": {ISIN: [kurs|null …]}, "u": {ISIN: {"<tag>": umsatz}},
                            "h": {ISIN: {"<tag>": [abschl_F, abschl_T, abschl_X, umsatz_F, umsatz_T, umsatz_X]}},
                            "stand", "aktuell": {ISIN: [kurs, rendite, datum, boerse, umsatz, tagesdaten, vortag, aufschlag]}}
                           – "h" (Handel, seit 26.09.2026): nur Tage mit mindestens einem Abschluss oder Umsatz; Abschlüsse je
                           Handelsplatz (Frankfurt, Tradegate, Xetra) so von der Börse geliefert, Umsätze je Platz BERECHNET als
                           Stück × Kurs in Anleihewährung (bei Stücknotiz in Euro/Währung je Stück × Stück). Grundlage für spätere
                           Auswertungen wie „meistgehandelt in 30 Tagen“ – die Börse hält die Tagesdateien nur einen Tag bereit.
                           – "aktuell" (seit 26.09.2026, nur in der Datei des laufenden Jahres) trägt den jüngsten Eintrag jeder
                           Anleihe/jedes ETFs der Teildatei wie in anleihen-kurse.json, aber mit Datum statt Tag-Index; die
                           Steckbrief-Seite anleihe.html lädt so nur diese eine Datei plus die Index-Teildatei anleihen/<hh>.json.
  kurse/bund/<ISIN>.json   Kursverlauf der Bundeswertpapiere (Bundesbank): {"t": [Datum …], "k": [...], "r": [...]}
                           täglich für die letzten zwei Jahre, davor ein Wert je Woche (Freitagsschluss). Einzelne
                           Ausreißer der Quelle fliegen raus (_common.ausreisser: ein Punkt, der von beiden Nachbarn
                           um mehr als 8 % in dieselbe Richtung abweicht, oder um mehr als 4 %, ohne dass die Rendite
                           gegenläufig mitgeht – Bundesbank am 30.04.2021: Bund 2042 101,01 zwischen 165,34 und 163,60).

Die Seite rechnet nichts nach: Die Rendite bis Fälligkeit steht fertig in der Datei (jährliche Verzinsung,
Zeit taggenau, Valuta zwei Börsentage nach dem Handelstag – wie auf den Länder- und Langläufer-Seiten).
Zinstermine werden vom Fälligkeitstag aus zurückgerechnet, ein Monatsende bleibt Monatsende (31.08. → 28.02. →
31.08.); halbjährlich zahlen Anleihen in USD/GBP/CAD/AUD/NZD/JPY/MXN/ZAR/HKD/SGD und italienische Staatsanleihen
(BTP), alle übrigen jährlich (_common.zinsfrequenz).
Eine Rendite bis Fälligkeit (und damit einen Aufschlag) gibt es nur für festen Kupon oder Nullkupon mit
Rückzahlung am Ende auf einmal (_common.ohne_rendite, seit 26.09.2026 laut Prüfbericht Datenbasis). Ohne
Rendite bleiben: variabel verzinste und Fix-to-Float-Anleihen („FLR“ im Namen), Stufenzinsanleihen, Wandel-
und Umtauschanleihen, Tilgungsanleihen (Tilgungsspanne im Namen, z. B. „2020(24-30)“ – nicht bei kurzer Tilgung
erst am Ende wie Südafrika „2012(47-49)“, dort ist die Rendite bis Fälligkeit eine gute Näherung), inflationsindexierte
und unbefristete Anleihen, Anleihen ohne bekannten Kupon, Restlaufzeiten unter 14 Tagen und „Nullkupons“,
deren Kurs nicht zu einem Nullkupon passt (unter 0,5 % Rendite bei mehr als einem Jahr Laufzeit, außer CHF und
JPY – dann fehlt meist der Kupon im Register oder die Anleihe wird über 100 zurückgezahlt), dazu Euro-Anleihen
anderer Emittenten als Staaten mit einer Rendite mehr als 1 Punkt unter Bund (unplausibel – meist eine Taxe ohne
Umsatz oder eine Sonderausstattung). Für Bundeswertpapiere gilt die Rendite der Bundesbank.

Verarbeitet jede gelistete Tagesdatei, die jünger ist als der gespeicherte Stand (normal eine, nach einem
ausgefallenen Lauf auch zwei) – Tag für Tag, älteste zuerst.

Aufruf:
  python scripts/update_kurse.py                  Tagesdateien holen (im 10-Uhr-Lauf)
  python scripts/update_kurse.py --bund-historie  zusätzlich den Bund-Verlauf komplett neu aus der Bundesbank bauen
  FIXTURE_DIR=<Ordner> python scripts/update_kurse.py
  ROH_DIR=<Ordner> python scripts/update_kurse.py   heruntergeladene Tagesdateien zusätzlich dort ablegen (Workflow: Artefakt)
                                                  Tagesdateien (DFRA-/DETR-/DGAT-posttrade-daily-*.json[.gz]) lokal lesen
  python scripts/update_kurse.py --neu-rechnen    ohne Abruf: Rendite und Aufschlag aller gespeicherten Kurse mit dem
                                                  aktuellen Index und den aktuellen Regeln neu rechnen (nach Änderungen
                                                  am Index oder an den Regeln); Anleihen, die nicht mehr im Index
                                                  stehen, fallen heraus
  python scripts/update_kurse.py --bund-bereinigen
                                                  ohne Abruf: Ausreißer aus den vorhandenen Bund-Verläufen entfernen
"""

import collections
import csv
import datetime
import gzip
import io
import json
import os
import re
import sys
import urllib.error
from pathlib import Path

from _common import (INFLATION, ausreisser, get_with_retry, log_err, now_iso, ohne_rendite, today_iso, write_atomic,
                     zinsfrequenz)

ROOT = Path(__file__).resolve().parent.parent
OUT_SUCHE = ROOT / "anleihen-kurse.json"
OUT_AUSWAHL = ROOT / "kurse-auswahl.json"
DIR_VERLAUF = ROOT / "kurse"
DIR_BUND = DIR_VERLAUF / "bund"
INDEX = ROOT / "anleihen-index.json"

API = "https://mfs.deutsche-boerse.com/api/"
DIENSTE = {"F": "DFRA-posttrade", "X": "DETR-posttrade", "T": "DGAT-posttrade"}
UA = {"User-Agent": "metalconcrete.de Kursaufbereitung (MiFIR Delayed Data)", "Accept": "*/*"}
BBK = "https://api.statistiken.bundesbank.de/rest/data/BBSSY/D.{item}.EUR...?detail=dataonly&{zeit}"
BBK_H = {"Accept": "application/vnd.sdmx.data+csv;version=1.0.0",
         "User-Agent": "metalconcrete.de Anleihen-Suche (Datenaufbereitung)"}

HALTEN_TAGE = 45                 # Kurse ohne neue Feststellung bleiben so lange stehen (mit Datum)
KURS_GRENZEN = (1.0, 400.0)      # Plausibilität, % des Nennwerts
RENDITE_GRENZEN = (-10.0, 60.0)  # außerhalb: keine Rendite anzeigen (Notlage, Kurs kaum aussagekräftig)
MIN_ANTEIL = 0.5                 # weniger als 50 % der Kurse des Vortags → Quelle defekt, nichts schreiben
NULLKUPON_MIN = 0.5             # „Nullkupon“ mit weniger Rendite (Laufzeit > 1 Jahr) passt nicht zum Kurs → keine Rendite
NIEDRIGZINS = {"CHF", "JPY"}     # dort sind Nullkupons nahe oder über 100 plausibel
AUFSCHLAG_MIN = -1.0             # Nicht-Staat mehr als 1 Punkt UNTER Bund: Kurs oder Stammdaten unplausibel → keine Rendite
# Halbjährliche Währungen, INFLATION, zinsfrequenz, ohne_rendite: _common.py (dieselben Regeln wie update_top10.py)
ISIN_RE = re.compile(r"\b[A-Z]{2}[A-Z0-9]{9}[0-9]\b")
BOERSE_NAME = {"F": "Börse Frankfurt", "T": "Tradegate", "X": "Xetra", "B": "Deutsche Bundesbank"}


# ---------- Hilfen ----------
def teil(isin: str) -> str:
    """Teildatei des Kursverlaufs: einfacher Hash, identisch in anleihen-suche.html (JS)."""
    h = 0
    for ch in isin:
        h = (h * 31 + ord(ch)) % 65536
    return f"{h % 256:02x}"


def isin_ok(s: str) -> bool:
    """Prüfziffer nach ISO 6166 (Luhn über die in Ziffern umgesetzten Zeichen)."""
    if not re.fullmatch(r"[A-Z]{2}[A-Z0-9]{9}[0-9]", s):
        return False
    ziffern = "".join(str(int(c, 36)) for c in s[:-1])
    summe = 0
    for i, c in enumerate(reversed(ziffern)):
        d = int(c)
        if i % 2 == 0:
            d *= 2
            d = d - 9 if d > 9 else d
        summe += d
    return (10 - summe % 10) % 10 == int(s[-1])


def plus_boersentage(d: datetime.date, n: int) -> datetime.date:
    while n:
        d += datetime.timedelta(days=1)
        if d.weekday() < 5:
            n -= 1
    return d


def lade_json(path: Path, leer):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return leer


# ---------- Rendite (jährliche Verzinsung, wie langlaeufer.html / anleihen-laender.html) ----------
def _monate_zurueck(d: datetime.date, m: int) -> datetime.date:
    j, mo = divmod(d.year * 12 + d.month - 1 - m, 12)
    mo += 1
    letzter = (datetime.date(j + (mo == 12), mo % 12 + 1, 1) - datetime.timedelta(days=1)).day
    return datetime.date(j, mo, min(d.day, letzter))


def rendite(kupon: float, faellig: datetime.date, kurs: float, valuta: datetime.date, freq: int):
    """Rendite bis Fälligkeit in % aus dem Kurs (clean, % des Nennwerts); None, wenn nicht bestimmbar."""
    if faellig <= valuta:
        return None
    # Zinstermine vom Fälligkeitstag aus zurückrechnen (nicht Schritt für Schritt – sonst wandert der Tag am
    # Monatsende: 31.08. → 28.02. → 28.08. statt 31.08.)
    termine, t, k = [], faellig, 0
    while t > valuta:
        termine.insert(0, t)
        k += 1
        t = _monate_zurueck(faellig, k * 12 // freq)
    vorher, c = t, kupon / freq
    stueckzins = c * (valuta - vorher).days / max(1, (termine[0] - vorher).days)
    zeiten = [(x - valuta).days / 365.25 for x in termine]
    flows = [c + (100 if i == len(termine) - 1 else 0) for i in range(len(termine))]

    def preis(y):
        return sum(f / (1 + y) ** z for f, z in zip(flows, zeiten)) - stueckzins

    lo, hi = -0.09, 1.5
    if not (preis(lo) >= kurs >= preis(hi)):
        return None
    for _ in range(48):
        mid = (lo + hi) / 2
        if preis(mid) > kurs:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2 * 100


def kurve_rendite(kurve: list, jahre: float):
    """Bund-Rendite gleicher Restlaufzeit, linear zwischen den beiden nächsten Bundeswertpapieren; None außerhalb."""
    if len(kurve) < 4 or jahre < kurve[0][0] or jahre > kurve[-1][0]:
        return None
    for (j0, r0), (j1, r1) in zip(kurve, kurve[1:]):
        if j0 <= jahre <= j1:
            return r0 if j1 == j0 else r0 + (r1 - r0) * (jahre - j0) / (j1 - j0)
    return None


def rendite_und_aufschlag(z: list, kurs: float, valuta: datetime.date, kurve: list | None):
    """(Rendite, Aufschlag zu Bund) einer Anleihe (Indexzeile z) zum Kurs – beide BERECHNET, None wo nicht sinnvoll."""
    if ohne_rendite(z):
        return None, None
    f = datetime.date.fromisoformat(z[5])
    if (f - valuta).days < 14:
        return None, None
    r = rendite(float(z[4]), f, kurs, valuta, zinsfrequenz(z))
    if r is None or not RENDITE_GRENZEN[0] < r < RENDITE_GRENZEN[1]:
        return None, None
    jahre = (f - valuta).days / 365.25
    if z[10] == 2 and r < NULLKUPON_MIN and jahre > 1 and z[3] not in NIEDRIGZINS:
        return None, None   # „Nullkupon“ laut Register, der Kurs passt aber nicht dazu
    rend, aufschlag = round(r, 3), None
    if z[3] == "EUR" and kurve and jahre <= 30:   # auch Kurzläufer (seit 27.09.2026): Taxen ohne Umsatz fallen dort am stärksten auf
        b = kurve_rendite(kurve, jahre)
        if b is not None:
            aufschlag = round(rend - b, 2)
            if z[2] != 0 and aufschlag < AUFSCHLAG_MIN:
                return None, None   # z. B. Taxe ohne Umsatz weit über dem Markt oder Sonderausstattung (aufzinsender Nullkupon)
    return rend, aufschlag


def auswahl_isins() -> set:
    """Alle ISINs der übrigen HTML-Seiten (Länder, Laufzeit, Langläufer, Startseite, ETFs)."""
    auswahl = set()
    for html in ROOT.glob("*.html"):
        if html.name in ("anleihen-suche.html", "404.html"):
            continue
        auswahl |= {i for i in ISIN_RE.findall(html.read_text(encoding="utf-8")) if isin_ok(i)}
    return auswahl


def schreibe_kursdateien(alle: dict, zeilen: dict, auswahl: set, stand: str) -> tuple[int, int]:
    """anleihen-kurse.json (Index-Anleihen) und kurse-auswahl.json (Seiten-ISINs) aus alle = {ISIN: [kurs, rendite,
    datum, boerse, umsatz, tagesdaten, vortag, aufschlag]} schreiben; gibt die Zahl der Einträge zurück."""
    def kompakt(auswahl_isins):
        tage = sorted({e[2] for i, e in alle.items() if i in auswahl_isins}, reverse=True)
        pos = {t: n for n, t in enumerate(tage)}
        return tage, {i: [e[0], e[1], pos[e[2]], e[3], e[4], e[5], e[6], e[7]] for i, e in sorted(alle.items()) if i in auswahl_isins}

    kopf = {"updated": today_iso(), "updatedAt": now_iso(), "checkedAt": now_iso(), "stand": stand,
            "quelle": "Deutsche Börse (Börse Frankfurt, Xetra, Tradegate; MiFIR-Nachhandelsdaten, 15 Minuten verzögert) "
                      "und Deutsche Bundesbank (Bundeswertpapiere)",
            "boersen": BOERSE_NAME}
    tage_s, kurse_s = kompakt(set(zeilen))
    write_atomic(OUT_SUCHE, {**kopf, "tage": tage_s, "kurse": kurse_s}, indent=None)
    tage_a, kurse_a = kompakt(auswahl)
    # anzahl = Anleihen in der Suche (Kurs in den letzten zwei Wochen) – Startseite zeigt „rund 33.000“ daraus
    write_atomic(OUT_AUSWAHL, {**kopf, "anzahl": len(kurse_s), "tage": tage_a, "kurse": kurse_a}, indent=None)
    return len(kurse_s), len(kurse_a)


# ---------- Deutsche Börse: Tagesdateien ----------
def tagesdateien(kuerzel: str) -> list[tuple[str, str]]:
    """[(Datum, Dateiname)] aller gelisteten Tagesdateien eines Dienstes, älteste zuerst – lokal (FIXTURE_DIR) oder online.
    Tagesdateien heißen „…-daily-2026-09-24.json.gz“, um Mitternacht kurzzeitig auch „…-2026-daily-09-25.json.gz“."""
    dienst = DIENSTE[kuerzel]
    fix = os.environ.get("FIXTURE_DIR")
    namen = [p.name for p in Path(fix).glob(f"{dienst}-*daily*")] if fix else \
        [f for f in json.loads(get_with_retry(API + dienst, headers=UA, timeout=60)).get("CurrentFiles", []) if "daily" in f]
    out = []
    for f in namen:
        m = re.search(r"(\d{4})-(?:daily-)?(\d{2})-(\d{2})", f)
        if m:
            out.append(("-".join(m.groups()), f))
    return sorted(out)


def tagesdatei_holen(kuerzel: str, name: str) -> bytes | None:
    """Inhalt einer Tagesdatei; None, wenn sie nicht (mehr) abrufbar ist (HTTP 400/404 – gelistete Dateien
    verschwinden nach etwa einem Börsentag)."""
    fix = os.environ.get("FIXTURE_DIR")
    if fix:
        return (Path(fix) / name).read_bytes()
    try:
        roh = get_with_retry(API + "download/" + name, headers=UA, timeout=180)
        # Rohdatei zusätzlich sichern (ROH_DIR, seit 29.09.2026): Der Workflow lädt den Ordner als Artefakt hoch
        # (90 Tage) – so lässt sich ein fehlerhaft verarbeiteter Tag später mit FIXTURE_DIR neu rechnen, obwohl die
        # Börse die Datei nur etwa einen Börsentag bereithält.
        roh_dir = os.environ.get("ROH_DIR")
        if roh_dir and roh:
            Path(roh_dir).mkdir(parents=True, exist_ok=True)
            (Path(roh_dir) / name).write_bytes(roh)
        return roh
    except urllib.error.HTTPError as e:
        if e.code not in (400, 404):
            raise
        log_err(f"{DIENSTE[kuerzel]}: {name} nicht abrufbar (HTTP {e.code}).")
        return None


def auswerten(roh: bytes, behalten: set) -> tuple[str, dict]:
    """Je ISIN: letzter Kurs, Höchst, Tiefst, Anzahl Feststellungen, Umsatz, Zahl der Abschlüsse.
    Übersprungen: indikative Kurse (MMT-Handelsmodus „I“) und Stornos („C“)."""
    if roh[:2] == b"\x1f\x8b":
        roh = gzip.decompress(roh)
    out, tage = {}, {}
    for zeile in io.BytesIO(roh):
        zeile = zeile.strip()
        if not zeile:
            continue
        try:
            d = json.loads(zeile)
            isin = d["instrumentIdentificationCode"]
            if isin not in behalten or d.get("mmtTradingMode") == "I" or d.get("mmtModificationInd") == "C":
                continue
            zeit, preis, menge = d["tradingDateAndTime"], float(d["price"]), float(d.get("quantity") or 0)
            notiz = int(d.get("priceNotation") or 2)
        except (KeyError, TypeError, ValueError):
            continue
        tage[zeit[:10]] = tage.get(zeit[:10], 0) + 1
        a = out.get(isin)
        if a is None:
            a = out[isin] = {"t": zeit, "p": preis, "t0": zeit, "o": preis, "hi": preis, "lo": preis, "n": 0, "u": 0.0, "abs": 0,
                             "notiz": notiz, "cur": d.get("priceCurrency")}
        if zeit >= a["t"]:
            a["t"], a["p"], a["notiz"] = zeit, preis, notiz
        if zeit < a["t0"]:
            a["t0"], a["o"] = zeit, preis
        a["hi"], a["lo"] = max(a["hi"], preis), min(a["lo"], preis)
        a["n"] += 1
        if menge > 0:
            a["abs"] += 1
            a["u"] += menge * preis / 100 if notiz == 2 else menge * preis
    tag = max(tage, key=tage.get) if tage else ""
    return tag, out


# ---------- Bundesbank ----------
def bundesbank(zeit: str) -> dict[str, list[tuple[str, float, float | None]]]:
    """ISIN → [(Datum, Kurs, Rendite)], sortiert. zeit: 'lastNObservations=1' oder 'startPeriod=…'."""
    def reihe(item):
        text = get_with_retry(BBK.format(item=item, zeit=zeit), headers=BBK_H, timeout=180).decode("utf-8-sig", "replace")
        out = {}
        for rec in csv.DictReader(io.StringIO(text), delimiter=";"):
            try:
                isin, datum, wert = rec["BBK_SEIS_ISIN"], rec["TIME_PERIOD"], float(rec["OBS_VALUE"])
            except (KeyError, TypeError, ValueError):
                continue
            out.setdefault(isin, {})[datum] = wert
        return out
    kcp, ren = reihe("KCP"), reihe("REN")
    res = {}
    for isin, werte in kcp.items():
        r = ren.get(isin, {})
        res[isin] = [(d, k, r.get(d)) for d, k in sorted(werte.items()) if KURS_GRENZEN[0] < k < KURS_GRENZEN[1]]
    return res


def bund_verlauf_schreiben(isin: str, punkte: list[tuple[str, float, float | None]]) -> None:
    """Letzte zwei Jahre täglich, davor der letzte Wert jeder Kalenderwoche; einzelne Ausreißer der Quelle fliegen raus."""
    if not punkte:
        return
    raus = ausreisser([p[1] for p in punkte], renditen=[p[2] for p in punkte])
    if raus:
        print(f"Bund-Verlauf {isin}: Ausreißer verworfen – " + ", ".join(f"{punkte[i][0]} {punkte[i][1]}" for i in sorted(raus)))
        punkte = [p for i, p in enumerate(punkte) if i not in raus]
    grenze = (datetime.date.fromisoformat(punkte[-1][0]) - datetime.timedelta(days=730)).isoformat()
    alt, neu = [p for p in punkte if p[0] < grenze], [p for p in punkte if p[0] >= grenze]
    woche = {}
    for p in alt:
        woche[datetime.date.fromisoformat(p[0]).isocalendar()[:2]] = p
    punkte = sorted(woche.values()) + neu
    DIR_BUND.mkdir(parents=True, exist_ok=True)
    write_atomic(DIR_BUND / f"{isin}.json", {
        "isin": isin, "quelle": "Deutsche Bundesbank (BBSSY)",
        "t": [p[0] for p in punkte], "k": [round(p[1], 3) for p in punkte],
        "r": [None if p[2] is None else round(p[2], 3) for p in punkte]}, indent=None)


# ---------- Hauptlauf ----------
def main() -> int:
    if "--neu-rechnen" in sys.argv:
        return neu_rechnen()
    if "--bund-bereinigen" in sys.argv:
        return bund_bereinigen()
    idx = lade_json(INDEX, {})
    zeilen = {r[0]: r for r in idx.get("rows", [])}
    if not zeilen:
        log_err("anleihen-index.json fehlt oder ist leer – keine Kurse.")
        return 1
    # Alle ISINs der übrigen Seiten (Länder, Laufzeit, Langläufer, Startseite, ETFs)
    auswahl = auswahl_isins()
    alt_stand = (lade_json(OUT_SUCHE, {}) or {}).get("stand") or ""

    # Bundesbank (Bundeswertpapiere): Kurs und Rendite der letzten Tage
    bbk = {}
    try:
        bbk = bundesbank(f"startPeriod={(datetime.date.today() - datetime.timedelta(days=12)).isoformat()}")
    except Exception as e:  # noqa: BLE001
        log_err(f"Bundesbank BBSSY nicht abrufbar ({e}) – Bund-Kurse von der Börse Frankfurt.")

    # 1) Deutsche Börse: alle gelisteten Tagesdateien, die jünger sind als der gespeicherte Stand –
    #    so geht kein Tag verloren, wenn ein Lauf ausfällt oder eine Datei erst spät erscheint.
    listen = {}
    for k in ("F", "X", "T"):
        try:
            listen[k] = tagesdateien(k)
        except Exception as e:  # noqa: BLE001
            log_err(f"{DIENSTE[k]}: Dateiliste nicht abrufbar ({e}).")
            listen[k] = []
    tage = sorted({d for k in listen for d, _ in listen[k] if d > alt_stand})
    if not tage:
        log_err(f"Keine neue Tagesdatei (Stand {alt_stand or 'unbekannt'}) – Kurse bleiben unverändert.")
        bund_verlauf(zeilen, bbk)
        return 0
    rc = 0
    for tag in tage:
        feed = {}
        for k in ("F", "X", "T"):
            for d, name in listen[k]:
                if d != tag:
                    continue
                try:
                    roh = tagesdatei_holen(k, name)
                except Exception as e:  # noqa: BLE001
                    log_err(f"{DIENSTE[k]}: {name} nicht abrufbar ({e}).")
                    roh = None
                if roh:
                    t, daten = auswerten(roh, set(zeilen) | auswahl)
                    feed[k] = daten
                    print(f"{name}: {len(daten)} Papiere, Handelstag {t}")
                    break
        if "F" not in feed:
            log_err(f"Börse Frankfurt fehlt für {tag} – dieser Tag wird übersprungen.")
            rc = 1
            continue
        rc = verarbeite(tag, feed, zeilen, auswahl, bbk) or rc
    bund_verlauf(zeilen, bbk)
    return rc


def verarbeite(tag: str, feed: dict, zeilen: dict, auswahl: set, bbk: dict) -> int:
    """Kurse eines Handelstags in die Kursdateien und den Kursverlauf schreiben."""
    behalten = set(zeilen) | auswahl
    d_tag = datetime.date.fromisoformat(tag)
    # 2) Bundesbank: für den Handelstag gilt der Bundesbank-Kurs
    bund = {i: p for i, pts in bbk.items() for p in pts if p[0] == tag}

    # Bund-Renditekurve des Tags (Bundesbank): (Restlaufzeit in Jahren, Rendite) der Bundeswertpapiere ohne Inflationsschutz –
    # Grundlage für den BERECHNETEN Renditeaufschlag der Euro-Anleihen
    valuta = plus_boersentage(d_tag, 2)
    kurve = []
    for isin, (datum, kurs, rend) in bund.items():
        z = zeilen.get(isin)
        if z and z[5] and rend is not None and not INFLATION.search(z[1]):
            kurve.append(((datetime.date.fromisoformat(z[5]) - valuta).days / 365.25, rend))
    kurve.sort()

    # Vortag: bisheriger Schlusskurs aus der eigenen Datei (für die BERECHNETE Veränderung)
    vor = {}
    for pfad in (OUT_AUSWAHL, OUT_SUCHE):
        alt0 = lade_json(pfad, {})
        if isinstance(alt0.get("kurse"), dict) and alt0.get("tage"):
            for isin, e in alt0["kurse"].items():
                try:
                    if alt0["tage"][e[2]] < tag:
                        vor[isin] = e[0]
                except (IndexError, TypeError):
                    pass

    def tagesdaten(isin, quelle, faktor):
        """[eroeffnung, hoch, tief, feststellungen, abschluesse, umsatz F, T, X] aus der Datei des Handelsplatzes."""
        a = feed.get(quelle, {}).get(isin)
        if not a:
            return None
        u = [round(feed[k][isin]["u"]) if k in feed and isin in feed[k] else 0 for k in ("F", "T", "X")]
        r = lambda x: round(x * faktor, 4 if x * faktor < 10 else 3)
        if a["o"] == a["hi"] == a["lo"] == a["p"] and a["abs"] == 0 and not any(u):
            return [a["n"]]
        return [r(a["o"]), r(a["hi"]), r(a["lo"]), a["n"], a["abs"]] + u

    # 3) Kurs je ISIN für den Handelstag
    neu = {}
    for isin in behalten:
        z = zeilen.get(isin)
        ist_anleihe = z is not None
        reihenfolge = ("F", "T") if ist_anleihe else ("X", "T", "F")
        quelle = next((k for k in reihenfolge if isin in feed.get(k, {})), None)
        umsatz = sum(feed[k][isin]["u"] for k in ("F", "T", "X") if k in feed and isin in feed[k]
                     and (k != "X" or not ist_anleihe))
        if isin in bund:
            datum, kurs, rend = bund[isin]
            neu[isin] = [round(kurs, 3), None if rend is None else round(rend, 3), datum, "B", round(umsatz),
                         tagesdaten(isin, "F", 1.0), vor.get(isin), None]
            continue
        if quelle is None:
            continue
        a = feed[quelle][isin]
        kurs, faktor = a["p"], 1.0
        if ist_anleihe:
            if a["notiz"] == 1:   # Stücknotiz → in % des Nennwerts
                if not isinstance(z[7], (int, float)) or z[7] <= 0:
                    continue
                faktor = 100 / z[7]
                kurs = kurs * faktor
            if not KURS_GRENZEN[0] < kurs < KURS_GRENZEN[1]:
                continue
        rend, aufschlag = rendite_und_aufschlag(z, kurs, valuta, kurve) if ist_anleihe else (None, None)
        neu[isin] = [round(kurs, 4 if kurs < 10 else 3), rend, a["t"][:10], quelle, round(umsatz),
                     tagesdaten(isin, quelle, faktor), vor.get(isin), aufschlag]

    # 4) Mit dem Vortag zusammenführen, Schutzregel
    alt = lade_json(OUT_SUCHE, {})
    alt_kurse, alt_tage = {}, alt.get("tage") or []
    if isinstance(alt.get("kurse"), dict) and alt_tage:   # neues Format
        for isin, e in alt["kurse"].items():
            try:
                alt_kurse[isin] = [e[0], e[1], alt_tage[e[2]], e[3], e[4]] + (list(e[5:8]) + [None, None, None])[:3]
            except (IndexError, TypeError):
                pass
    frisch_alt = sum(1 for e in alt_kurse.values() if e[2] == alt.get("stand"))
    frisch_neu = sum(1 for isin, e in neu.items() if isin in zeilen and e[2] == tag)
    if frisch_alt and frisch_neu < MIN_ANTEIL * frisch_alt:
        log_err(f"Nur {frisch_neu} Anleihekurse statt zuvor {frisch_alt} – Dateien bleiben unverändert.")
        return 1
    grenze = (d_tag - datetime.timedelta(days=HALTEN_TAGE)).isoformat()
    alle = {i: e for i, e in alt_kurse.items() if e[2] >= grenze and (i in behalten)}
    alle.update(neu)

    n_suche, n_auswahl = schreibe_kursdateien(alle, zeilen, auswahl, tag)
    print(f"anleihen-kurse.json: {n_suche} Anleihen ({frisch_neu} vom {tag}); kurse-auswahl.json: {n_auswahl} Papiere")

    def handel(isin):
        """[Abschlüsse F, T, X, Umsatz F, T, X] des Handelstags für die Historie – nur, wenn gehandelt wurde, sonst None."""
        da = [feed[k][isin] if k in feed and isin in feed[k] else None for k in ("F", "T", "X")]
        ab = [x["abs"] if x else 0 for x in da]
        um = [round(x["u"]) if x else 0 for x in da]
        return ab + um if any(ab) or any(um) else None

    # 5) Kursverlauf (nur Kurse dieses Handelstags) und aktueller Eintrag je Teildatei
    jahr_dir = DIR_VERLAUF / tag[:4]
    jahr_dir.mkdir(parents=True, exist_ok=True)
    teile, akt = {}, {}
    for isin, e in neu.items():
        if e[2] == tag:
            teile.setdefault(teil(isin), {})[isin] = e
    for isin, e in alle.items():
        akt.setdefault(teil(isin), {})[isin] = e
    geschrieben = 0
    for t in (f"{i:02x}" for i in range(256)):
        pfad = jahr_dir / f"{t}.json"
        v = lade_json(pfad, {"tage": [], "k": {}, "u": {}})
        if not (v["tage"] and v["tage"][-1] >= tag):   # Tag noch nicht erfasst (sonst Wochenende / zweiter Lauf)
            n = len(v["tage"])
            v["tage"].append(tag)
            heute = teile.get(t, {})
            for isin in set(v["k"]) | set(heute):
                reihe = v["k"].setdefault(isin, [None] * n)
                reihe.append(heute[isin][0] if isin in heute else None)
                if isin in heute and heute[isin][4] > 0:
                    v["u"].setdefault(isin, {})[str(n)] = heute[isin][4]
                h = handel(isin) if isin in heute else None
                if h:
                    v.setdefault("h", {}).setdefault(isin, {})[str(n)] = h
        v["stand"] = tag
        v["aktuell"] = dict(sorted(akt.get(t, {}).items()))
        write_atomic(pfad, v, indent=None)
        geschrieben += 1
    print(f"Kursverlauf {tag}: {geschrieben} Teildateien ergänzt")

    return 0


def bund_verlauf(zeilen: dict, bbk: dict) -> None:
    # 6) Bund-Verlauf (Bundesbank)
    if "--bund-historie" in sys.argv:
        try:
            hist = bundesbank("startPeriod=1990-01-01")
        except Exception as e:  # noqa: BLE001
            log_err(f"Bundesbank-Historie nicht abrufbar ({e}).")
            hist = {}
        for isin, punkte in hist.items():
            if isin in zeilen and punkte:
                bund_verlauf_schreiben(isin, punkte)
        print(f"Bund-Verlauf neu gebaut: {sum(1 for i in hist if i in zeilen)} Bundeswertpapiere")
    elif bbk:
        n = 0
        for isin, pts in bbk.items():
            if isin not in zeilen or not pts:
                continue
            v = lade_json(DIR_BUND / f"{isin}.json", None) or {"t": [], "k": [], "r": []}
            dazu = [p for p in pts if not v["t"] or p[0] > v["t"][-1]]
            if dazu:
                bund_verlauf_schreiben(isin, list(zip(v["t"], v["k"], v["r"])) + dazu)
                n += 1
        print(f"Bund-Verlauf: {n} Bundeswertpapiere ergänzt")



def neu_rechnen() -> int:
    """--neu-rechnen: Rendite und Aufschlag aller gespeicherten Kurse mit dem aktuellen Index und den aktuellen Regeln
    neu rechnen – ohne Abruf, Kurse bleiben unverändert. Bundeswertpapiere behalten die Bundesbank-Rendite, ETFs haben
    keine. Anleihen, die nicht mehr im Index stehen (und auf keiner Seite), fallen heraus. Schreibt anleihen-kurse.json,
    kurse-auswahl.json und „aktuell“ in kurse/<Jahr>/<hh>.json."""
    zeilen = {r[0]: r for r in lade_json(INDEX, {}).get("rows", [])}
    such, ausw = lade_json(OUT_SUCHE, {}), lade_json(OUT_AUSWAHL, {})
    stand = such.get("stand")
    if not zeilen or not isinstance(such.get("kurse"), dict) or not stand:
        log_err("anleihen-index.json oder anleihen-kurse.json fehlt – nichts neu gerechnet.")
        return 1
    alle = {}
    for d in (ausw, such):                      # die Suchdatei zuletzt: sie hat Vorrang
        tage = d.get("tage") or []
        for isin, e in (d.get("kurse") or {}).items():
            try:
                alle[isin] = [e[0], e[1], tage[e[2]], e[3], e[4]] + (list(e[5:8]) + [None, None, None])[:3]
            except (IndexError, TypeError):
                pass
    auswahl = auswahl_isins()
    vorher = len(alle)
    alle = {i: e for i, e in alle.items() if i in zeilen or i in auswahl}
    # Bund-Renditekurve je Kursdatum aus den Bundesbank-Einträgen (wie im Tageslauf)
    kurven = {}
    for isin, e in alle.items():
        z = zeilen.get(isin)
        if e[3] == "B" and z and z[5] and e[1] is not None and not INFLATION.search(z[1]):
            val = plus_boersentage(datetime.date.fromisoformat(e[2]), 2)
            kurven.setdefault(e[2], []).append(((datetime.date.fromisoformat(z[5]) - val).days / 365.25, e[1]))
    for k in kurven.values():
        k.sort()
    geaendert = collections.Counter()
    for isin, e in alle.items():
        z = zeilen.get(isin)
        if not z or e[3] == "B":
            continue
        rend, auf = rendite_und_aufschlag(z, e[0], plus_boersentage(datetime.date.fromisoformat(e[2]), 2), kurven.get(e[2]))
        if e[2] not in kurven and rend is not None:
            auf = e[7]                          # kein Bund-Kurs vom selben Tag gespeichert: Aufschlag bleibt
        if e[1] != rend:
            geaendert["Rendite"] += 1
        if e[7] != auf:
            geaendert["Aufschlag"] += 1
        e[1], e[7] = rend, auf
    n_suche, n_auswahl = schreibe_kursdateien(alle, zeilen, auswahl, stand)
    # „aktuell“ der Verlaufs-Teildateien des laufenden Jahres (Steckbrief anleihe.html)
    akt = {}
    for isin, e in alle.items():
        akt.setdefault(teil(isin), {})[isin] = e
    n_teil = 0
    for t in (f"{i:02x}" for i in range(256)):
        pfad = DIR_VERLAUF / stand[:4] / f"{t}.json"
        v = lade_json(pfad, None)
        if v is None:
            continue
        v["aktuell"] = dict(sorted(akt.get(t, {}).items()))
        write_atomic(pfad, v, indent=None)
        n_teil += 1
    print(f"Neu gerechnet (Stand {stand}): Rendite {geaendert['Rendite']}× und Aufschlag {geaendert['Aufschlag']}× geändert; "
          f"{vorher - len(alle)} Einträge ohne Index/Seite entfernt; anleihen-kurse.json {n_suche} Anleihen, "
          f"kurse-auswahl.json {n_auswahl} Papiere, {n_teil} Verlaufsdateien („aktuell“)")
    return 0


def bund_bereinigen() -> int:
    """--bund-bereinigen: Ausreißer aus den vorhandenen Bund-Verläufen kurse/bund/<ISIN>.json entfernen (ohne Abruf)."""
    n = 0
    for pfad in sorted(DIR_BUND.glob("*.json")):
        v = lade_json(pfad, None)
        if not v or not v.get("t"):
            continue
        punkte = list(zip(v["t"], v["k"], v["r"]))
        if ausreisser([p[1] for p in punkte], renditen=[p[2] for p in punkte]):
            bund_verlauf_schreiben(v.get("isin") or pfad.stem, punkte)
            n += 1
    print(f"Bund-Verlauf bereinigt: {n} Dateien geändert")
    return 0


if __name__ == "__main__":
    sys.exit(main())
