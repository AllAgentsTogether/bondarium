#!/usr/bin/env python3
"""update_kurse.py – Tageskurse und Kursverlauf aller Anleihen der Suche, aller Anleihen/ETFs der Datenseiten und aller
Anleihen-ETFs des Registers (etf-index.json, scripts/update_etf_index.py – seit 30.09.2026).

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
                           Langläufer, Startseite, Guide) und für die ETFs der Top-10-Listen der ETF-Seite
                           (top10-anleihen-etfs.json aus update_etf_index.py – die ISINs stehen nicht im HTML);
                           klein, wird per inline_data.py in diese Seiten eingebettet.
                           ETFs: Kurs in Euro je Anteil (Xetra), umsatz in Euro.
  etf-kurse.json           dieselben Felder für alle Anleihen-ETFs des Registers etf-index.json (seit 30.09.2026).
                           Kurs je Anteil in der Handelswährung des Registers – fast immer Euro; einige Anteilsklassen
                           werden an Xetra nur in USD, GBP, SEK oder CHF gehandelt. Einige ETFs haben eine Euro- UND eine
                           Dollar-Handelszeile unter derselben ISIN: Für ETFs zählen nur Feststellungen in der Handelswährung
                           des Registers (sonst wäre der „letzte Kurs“ mal ein Euro-, mal ein Dollar-Kurs).
                           Xetra stellt für jeden ETF täglich Auktionspreise fest, auch ohne Umsatz – jeder ETF hat also
                           jeden Börsentag einen Kurs. Wie bei den Anleihen bleiben Einträge ohne neuen Kurs bis zu 45 Tage
                           mit ihrem Datum stehen (für ETFs und andere Papiere außerhalb des Anleihen-Index seit 30.09.2026).
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
Zeit taggenau, Valuta zwei Abwicklungstage nach dem Handelstag ohne TARGET-Feiertage – _common.plus_abwicklungstage, wie
Steckbrief und Rechner; Stückzinsen aus dem Betrag der nächsten Zahlung, in einer kurzen Schlussperiode also anteilig).
Zinstermine (seit 02.10.2026): aus der Instrumentenliste der Deutschen Börse (zinstermine/zinstermine.json,
scripts/update_zinstermine.py) – Zahlungen je Jahr und die Zinstage. Nur wo die Liste nichts sagt, wird geschätzt:
Termine vom Fälligkeitstag aus zurückgerechnet, ein Monatsende bleibt Monatsende (31.08. → 28.02. → 31.08.),
Zahlungen je Jahr nach _common.zinsfrequenz (Währung, ISIN-Land, Bauart). Beides in _common.zinsplan/zinszahlungen.
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
  FIXTURE_DIR=<Ordner> python scripts/update_kurse.py --nachtragen
                                                  Tage, die schon im Kursverlauf stehen, für ETFs und andere Papiere außerhalb
                                                  des Anleihen-Index ergänzen, die an dem Tag noch keinen Wert haben (z. B. nach
                                                  der Aufnahme ins Register) – aus den Tagesdateien im Ordner (Rohdaten-Artefakt
                                                  des Workflows) oder, ohne FIXTURE_DIR, aus den bei der Börse noch gelisteten.
                                                  Vorhandene Werte und alle Anleihen des Index bleiben unangetastet.
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

from _common import (INFLATION, ausreisser, get_with_retry, log_err, now_iso, ohne_rendite, plus_abwicklungstage, today_iso,
                     write_atomic, zinsplan, zinstermine_laden, zinszahlungen)

ROOT = Path(__file__).resolve().parent.parent
OUT_SUCHE = ROOT / "anleihen-kurse.json"
OUT_AUSWAHL = ROOT / "kurse-auswahl.json"
OUT_ETF = ROOT / "etf-kurse.json"
DIR_VERLAUF = ROOT / "kurse"
DIR_BUND = DIR_VERLAUF / "bund"
INDEX = ROOT / "anleihen-index.json"
ETF_INDEX = ROOT / "etf-index.json"   # Register der Anleihen-ETFs (scripts/update_etf_index.py)
ETF_TOP10 = ROOT / "top10-anleihen-etfs.json"   # die zehn meistgehandelten je Kategorie (ETF-Seite)

API = "https://mfs.deutsche-boerse.com/api/"
DIENSTE = {"F": "DFRA-posttrade", "X": "DETR-posttrade", "T": "DGAT-posttrade"}
UA = {"User-Agent": "bondarium.de Kursaufbereitung (MiFIR Delayed Data)", "Accept": "*/*"}
BBK = "https://api.statistiken.bundesbank.de/rest/data/BBSSY/D.{item}.EUR...?detail=dataonly&{zeit}"
BBK_H = {"Accept": "application/vnd.sdmx.data+csv;version=1.0.0",
         "User-Agent": "bondarium.de Anleihen-Suche (Datenaufbereitung)"}

HALTEN_TAGE = 45                 # Kurse ohne neue Feststellung bleiben so lange stehen (mit Datum)
KURS_GRENZEN = (1.0, 400.0)      # Plausibilität, % des Nennwerts
RENDITE_GRENZEN = (-10.0, 60.0)  # außerhalb: keine Rendite anzeigen (Notlage, Kurs kaum aussagekräftig)
MIN_ANTEIL = 0.5                 # weniger als 50 % der Kurse des Vortags → Quelle defekt, nichts schreiben
NULLKUPON_MIN = 0.5             # „Nullkupon“ mit weniger Rendite (Laufzeit > 1 Jahr) passt nicht zum Kurs → keine Rendite
NIEDRIGZINS = {"CHF", "JPY"}     # dort sind Nullkupons nahe oder über 100 plausibel
AUFSCHLAG_MIN = -1.0             # Nicht-Staat mehr als 1 Punkt UNTER Bund: Kurs oder Stammdaten unplausibel → keine Rendite
KURVE_MIN = 10                   # weniger Bundeswertpapiere mit Rendite: keine brauchbare Bund-Kurve für den Aufschlag
KURVE_ALTER_TAGE = 7             # Rückfall: Bund-Kurve höchstens so viele Kalendertage vor dem Handelstag (bund_kurve_rueckfall)
KURVE_WARNEN_TAGE = 4            # ab diesem Alter der Rückfall-Kurve zusätzlich „Bund-Kurve ist N Tage alt“ (seit 09.10.2026)
PRUEFKURVE_ALTER_TAGE = 14       # ohne Kurve für den Aufschlag: AUFSCHLAG_MIN gegen eine bis so alte Kurve prüfen (seit 09.10.2026)
# INFLATION, zinsplan (Zinstermine), ohne_rendite: _common.py (dieselben Regeln wie update_top10.py)
ZINSTERMINE = None   # {ISIN: [zahlungen_je_jahr, "MM-TT", …]} – beim ersten Gebrauch geladen (zinstermine())


def zinstermine() -> dict:
    global ZINSTERMINE
    if ZINSTERMINE is None:
        ZINSTERMINE = zinstermine_laden()
    return ZINSTERMINE
ISIN_RE = re.compile(r"\b[A-Z]{2}[A-Z0-9]{9}[0-9]\b")


def bund_kurve(zeilen: dict, punkte: dict, valuta: datetime.date) -> list:
    """Bund-Renditekurve [(Restlaufzeit in Jahren, Rendite)] aus {ISIN: (Datum, Kurs, Rendite)} der Bundesbank –
    nur Bundeswertpapiere ohne Inflationsschutz, sortiert."""
    kurve = []
    for isin, (datum, kurs, rend) in punkte.items():
        z = zeilen.get(isin)
        if z and z[5] and rend is not None and not INFLATION.search(z[1]):
            kurve.append(((datetime.date.fromisoformat(z[5]) - valuta).days / 365.25, rend))
    return sorted(kurve)


def bund_kurve_rueckfall(zeilen: dict, bbk: dict, tag: str, valuta: datetime.date,
                         fenster: int | None = None) -> tuple[list, str]:
    """Bund-Kurve, wenn die Bundesbank für den Handelstag nichts liefert (02.10.2026: Schnittstelle antwortete mit
    HTTP 400, statt 13.234 Aufschlägen gab es 16): die jüngste Kurve der letzten `fenster` Tage (Standard
    KURVE_ALTER_TAGE; PRUEFKURVE_ALTER_TAGE nur für die Plausibilitätsprüfung) aus dem Abruf oder aus
    kurse/bund/<ISIN>.json. Gibt (Kurve, Datum) zurück, ([], "") ohne brauchbare Kurve."""
    grenze = (datetime.date.fromisoformat(tag) - datetime.timedelta(days=fenster or KURVE_ALTER_TAGE)).isoformat()
    je_tag = collections.defaultdict(dict)
    for pfad in DIR_BUND.glob("*.json"):
        v = lade_json(pfad, None) or {}
        for d, k, r in zip(v.get("t", []), v.get("k", []), v.get("r", [])):
            if grenze <= d < tag:
                je_tag[d][pfad.stem] = (d, k, r)
    for isin, pts in bbk.items():
        for p in pts:
            if grenze <= p[0] < tag:
                je_tag[p[0]][isin] = p
    for d in sorted(je_tag, reverse=True):
        kurve = bund_kurve(zeilen, je_tag[d], valuta)
        if len(kurve) >= KURVE_MIN:
            return kurve, d
    return [], ""
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


# Valuta: Handelstag + 2 Abwicklungstage ohne TARGET-Feiertage (_common.plus_abwicklungstage, seit 09.10.2026, T-49). Der alte
# Name bleibt für bestehende Aufrufe von außen (Prüf- und Nachrechen-Skripte) – vorher zählte er nur Mo–Fr.
plus_boersentage = plus_abwicklungstage


def lade_json(path: Path, leer):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return leer


# ---------- Rendite (jährliche Verzinsung, wie langlaeufer.html / anleihen-laender.html) ----------
def rendite(kupon: float, faellig: datetime.date, kurs: float, valuta: datetime.date, freq: int, tage: list | None = None):
    """Rendite bis Fälligkeit in % aus dem Kurs (clean, % des Nennwerts); None, wenn nicht bestimmbar.
    freq = Zinszahlungen je Jahr, tage = Zinstage „MM-TT“ aus der Börsenliste (None: aus der Fälligkeit geschätzt)."""
    if faellig <= valuta:
        return None
    vorher, zahlungen = zinszahlungen(kupon, faellig, valuta, freq, tage)
    # Stückzinsen aus dem Betrag der nächsten Zahlung (seit 09.10.2026, Technik-Test 08.10.2026 T-17): In einer kurzen
    # Schlussperiode ist das der anteilige Schlusskupon – vorher wuchsen sie bis zum vollen Kupon, gezahlt wurde aber nur
    # der anteilige (Rendite ab 15.12.2026 bei rund 150 Anleihen um Punkte falsch). Gleiche Regel in bond.js (accrued).
    stueckzins = zahlungen[0][1] * (valuta - vorher).days / max(1, (zahlungen[0][0] - vorher).days)
    zeiten = [(t - valuta).days / 365.25 for t, _ in zahlungen]
    flows = [z + (100 if i == len(zahlungen) - 1 else 0) for i, (_, z) in enumerate(zahlungen)]

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


def bundeswertpapier(z: list) -> bool:
    """Staatsanleihe Deutschlands (Indexzeile: art 0, land DE) – kein Aufschlag zu Bund, sonst wäre es ein Aufschlag zu
    sich selbst (seit dem Bundesbank-Ausfall kommen ihre Kurse von der Börse; Technik-Test 08.10.2026, T-04)."""
    return z[2] == 0 and z[11] == "DE"


def rendite_und_aufschlag(z: list, kurs: float, valuta: datetime.date, kurve: list | None,
                          pruefkurve: list | None = None):
    """(Rendite, Aufschlag zu Bund) einer Anleihe (Indexzeile z) zum Kurs – beide BERECHNET, None wo nicht sinnvoll.
    pruefkurve (seit 09.10.2026, T-01): ohne `kurve` eine bis PRUEFKURVE_ALTER_TAGE alte Bund-Kurve – gegen sie gilt nur
    die Plausibilitätsregel AUFSCHLAG_MIN, ein Aufschlag wird daraus nicht geschrieben."""
    if ohne_rendite(z):
        return None, None
    f = datetime.date.fromisoformat(z[5])
    if (f - valuta).days < 14:
        return None, None
    r = rendite(float(z[4]), f, kurs, valuta, *zinsplan(z, zinstermine()))
    if r is None or not RENDITE_GRENZEN[0] < r < RENDITE_GRENZEN[1]:
        return None, None
    jahre = (f - valuta).days / 365.25
    if z[10] == 2 and r < NULLKUPON_MIN and jahre > 1 and z[3] not in NIEDRIGZINS:
        return None, None   # „Nullkupon“ laut Register, der Kurs passt aber nicht dazu
    rend, aufschlag = round(r, 3), None
    if z[3] == "EUR" and kurve and jahre <= 30 and not bundeswertpapier(z):   # auch Kurzläufer (seit 27.09.2026): Taxen ohne Umsatz fallen dort am stärksten auf
        b = kurve_rendite(kurve, jahre)
        if b is not None:
            aufschlag = round(rend - b, 2)
            if z[2] != 0 and aufschlag < AUFSCHLAG_MIN:
                return None, None   # z. B. Taxe ohne Umsatz weit über dem Markt oder Sonderausstattung (aufzinsender Nullkupon)
    elif z[3] == "EUR" and not kurve and pruefkurve and jahre <= 30 and z[2] != 0:
        b = kurve_rendite(pruefkurve, jahre)
        if b is not None and round(rend - b, 2) < AUFSCHLAG_MIN:
            return None, None   # dieselbe Regel ohne aktuelle Kurve – sonst kämen unplausible Renditen zurück (z. B. −5,36 %)
    return rend, aufschlag


def auswahl_isins() -> set:
    """Alle ISINs der übrigen HTML-Seiten (Länder, Laufzeit, Langläufer, Startseite, Guide) und der Top-10-Listen
    der ETF-Seite (top10-anleihen-etfs.json). Die ETF-Seite baut ihre Tabellen aus dieser Datei – die ISINs stehen
    nicht im HTML (vom 29.09. bis 30.09.2026 blieben deshalb 68 der 70 ETFs ohne Kurs)."""
    auswahl = set()
    for html in ROOT.glob("*.html"):
        if html.name in ("anleihen-suche.html", "404.html"):
            continue
        auswahl |= {i for i in ISIN_RE.findall(html.read_text(encoding="utf-8")) if isin_ok(i)}
    for gruppe in (lade_json(ETF_TOP10, {}).get("gruppen") or {}).values():
        auswahl |= {x["isin"] for x in gruppe.get("etfs") or [] if isinstance(x, dict) and isin_ok(str(x.get("isin") or ""))}
    return auswahl


def etf_register() -> dict:
    """{ISIN: Handelswährung} aller Anleihen-ETFs aus etf-index.json; leer, solange es das Register nicht gibt."""
    idx = lade_json(ETF_INDEX, {})
    felder = idx.get("felder") or []
    if "isin" not in felder or "handelswaehrung" not in felder:
        return {}
    i, w = felder.index("isin"), felder.index("handelswaehrung")
    return {r[i]: r[w] or "EUR" for r in idx.get("rows") or [] if isin_ok(str(r[i]))}


def alte_eintraege(*pfade: Path) -> dict:
    """{ISIN: [kurs, rendite, datum, boerse, umsatz, tagesdaten, vortag, aufschlag]} aus Kursdateien (Datum statt
    Tag-Index); spätere Dateien haben Vorrang."""
    out = {}
    for pfad in pfade:
        alt = lade_json(pfad, {})
        tage = alt.get("tage") or []
        if isinstance(alt.get("kurse"), dict) and tage:
            for isin, e in alt["kurse"].items():
                try:
                    out[isin] = [e[0], e[1], tage[e[2]], e[3], e[4]] + (list(e[5:8]) + [None, None, None])[:3]
                except (IndexError, TypeError):
                    pass
    return out


def schreibe_kursdateien(alle: dict, zeilen: dict, auswahl: set, stand: str, etf: dict | None = None,
                         suche: bool = True) -> tuple[int, int, int]:
    """anleihen-kurse.json (Index-Anleihen; nur mit suche=True), kurse-auswahl.json (Seiten-ISINs) und etf-kurse.json
    (ETF-Register, sobald es eines gibt) aus alle = {ISIN: [kurs, rendite, datum, boerse, umsatz, tagesdaten, vortag,
    aufschlag]} schreiben; gibt die Zahl der Einträge zurück."""
    def kompakt(auswahl_isins):
        tage = sorted({e[2] for i, e in alle.items() if i in auswahl_isins}, reverse=True)
        pos = {t: n for n, t in enumerate(tage)}
        return tage, {i: [e[0], e[1], pos[e[2]], e[3], e[4], e[5], e[6], e[7]] for i, e in sorted(alle.items()) if i in auswahl_isins}

    kopf = {"updated": today_iso(), "updatedAt": now_iso(), "checkedAt": now_iso(), "stand": stand,
            "quelle": "Deutsche Börse (Börse Frankfurt, Xetra, Tradegate; MiFIR-Nachhandelsdaten, 15 Minuten verzögert) "
                      "und Deutsche Bundesbank (Bundeswertpapiere)",
            "boersen": BOERSE_NAME}
    tage_s, kurse_s = kompakt(set(zeilen))
    if suche:
        write_atomic(OUT_SUCHE, {**kopf, "tage": tage_s, "kurse": kurse_s}, indent=None)
    tage_a, kurse_a = kompakt(auswahl)
    # anzahl = Anleihen in der Suche (Kurs in den letzten zwei Wochen) – Startseite zeigt „rund 33.000“ daraus
    write_atomic(OUT_AUSWAHL, {**kopf, "anzahl": len(kurse_s), "tage": tage_a, "kurse": kurse_a}, indent=None)
    kurse_e = {}
    if etf:
        tage_e, kurse_e = kompakt(set(etf))
        write_atomic(OUT_ETF, {**kopf, "quelle": "Deutsche Börse (Xetra, Tradegate, Börse Frankfurt; MiFIR-Nachhandelsdaten, 15 Minuten verzögert)",
                               "tage": tage_e, "kurse": kurse_e}, indent=None)
    return len(kurse_s), len(kurse_a), len(kurse_e)


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


def auswerten(roh: bytes, behalten: set, waehrung: dict | None = None) -> tuple[str, dict]:
    """Je ISIN: letzter Kurs, Höchst, Tiefst, Anzahl Feststellungen, Umsatz, Zahl der Abschlüsse.
    Übersprungen: indikative Kurse (MMT-Handelsmodus „I“) und Stornos („C“) – und für die Papiere in `waehrung`
    ({ISIN: Währung}, die ETFs) alle Feststellungen in einer anderen Währung: Manche ETFs werden an Xetra unter
    derselben ISIN in Euro und in Dollar gehandelt (seit 30.09.2026)."""
    waehrung = waehrung or {}
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
            if isin in waehrung and d.get("priceCurrency") not in (None, waehrung[isin]):
                continue
            zeit, preis, menge = d["tradingDateAndTime"], float(d["price"]), float(d.get("quantity") or 0)
            notiz = int(d.get("priceNotation") or 2)
            # Satz ohne Zeitstempel oder Preis überspringen (Tradegate 05.10.2026: XS2356041165 mit Zeit null und Preis 0 –
            # der TypeError brach den ganzen Kursabruf ab, Technik-Test 08.10.2026, T-03)
            if not isinstance(zeit, str) or not re.match(r"\d{4}-\d{2}-\d{2}", zeit) or preis <= 0:
                continue
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
    if "--nachtragen" in sys.argv:
        return nachtragen()
    idx = lade_json(INDEX, {})
    zeilen = {r[0]: r for r in idx.get("rows", [])}
    if not zeilen:
        log_err("anleihen-index.json fehlt oder ist leer – keine Kurse.")
        return 1
    # Alle ISINs der übrigen Seiten (Länder, Laufzeit, Langläufer, Startseite, ETFs) und das ETF-Register
    auswahl = auswahl_isins()
    etf = etf_register()
    waehrung = ohne_index(zeilen, auswahl, etf)
    alt_stand = (lade_json(OUT_SUCHE, {}) or {}).get("stand") or ""

    # Bundesbank (Bundeswertpapiere): Kurs und Rendite der letzten Tage
    bbk = {}
    try:
        bbk = bundesbank(f"startPeriod={(datetime.date.today() - datetime.timedelta(days=12)).isoformat()}")
    except Exception as e:  # noqa: BLE001
        log_err(f"Bundesbank BBSSY nicht abrufbar ({e}) – Bund-Kurse von der Börse Frankfurt.")

    # 1) Deutsche Börse: alle gelisteten Tagesdateien, die jünger sind als der gespeicherte Stand –
    #    so geht kein Tag verloren, wenn ein Lauf ausfällt oder eine Datei erst spät erscheint.
    listen, ohne_liste = {}, 0
    for k in ("F", "X", "T"):
        try:
            listen[k] = tagesdateien(k)
        except Exception as e:  # noqa: BLE001
            log_err(f"{DIENSTE[k]}: Dateiliste nicht abrufbar ({e}).")
            listen[k] = []
            ohne_liste += 1
    tage = sorted({d for k in listen for d, _ in listen[k] if d > alt_stand})
    rc = 0
    # Bund-Verlauf im finally (seit 09.10.2026, T-01): geholte Bundesbank-Daten gehen auch bei einem Absturz nicht verloren
    try:
        if ohne_liste == len(listen):
            # Totalausfall (seit 09.10.2026, Technik-Test 08.10.2026 T-62): vorher hieß es nur „Keine neue Tagesdatei“ mit
            # Exit 0. Jetzt Exit 1 – in kurse-nachholen.yml bricht der Schritt damit gewollt ab (kein Commit, kein Anstoß).
            log_err("Deutsche Börse: keine der drei Dateilisten abrufbar – keine Kurse.")
            return 1
        if not tage:
            log_err(f"Keine neue Tagesdatei (Stand {alt_stand or 'unbekannt'}) – Kurse bleiben unverändert.")
            return 0
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
                        # Eine nicht auswertbare Datei gilt als fehlend (seit 09.10.2026, T-03) – ohne Frankfurt wird der
                        # Tag wie bisher übersprungen, ohne Xetra/Tradegate geht es ohne sie weiter.
                        try:
                            t, daten = auswerten(roh, set(zeilen) | auswahl | set(etf), waehrung)
                        except Exception as e:  # noqa: BLE001
                            log_err(f"{DIENSTE[k]}: {name} nicht auswertbar ({type(e).__name__}: {e}).")
                            continue
                        feed[k] = daten
                        print(f"{name}: {len(daten)} Papiere, Handelstag {t}")
                        break
            if "F" not in feed:
                log_err(f"Börse Frankfurt fehlt für {tag} – dieser Tag wird übersprungen.")
                rc = 1
                continue
            rc = verarbeite(tag, feed, zeilen, auswahl, bbk, etf) or rc
    finally:
        bund_verlauf(zeilen, bbk)
    return rc


def ohne_index(zeilen: dict, auswahl: set, etf: dict) -> dict:
    """{ISIN: Währung} der Papiere außerhalb des Anleihen-Index – die ETFs. Für sie zählen nur Feststellungen in
    dieser Währung: die Handelswährung des Registers, sonst Euro (ETFs der Seiten ohne Registereintrag)."""
    return {i: etf.get(i) or "EUR" for i in (auswahl | set(etf)) if i not in zeilen}


def tagesdaten(feed: dict, isin: str, quelle: str, faktor: float):
    """[eroeffnung, hoch, tief, feststellungen, abschluesse, umsatz F, T, X] aus der Datei des Handelsplatzes."""
    a = feed.get(quelle, {}).get(isin)
    if not a:
        return None
    u = [round(feed[k][isin]["u"]) if k in feed and isin in feed[k] else 0 for k in ("F", "T", "X")]
    r = lambda x: round(x * faktor, 4 if x * faktor < 10 else 3)
    if a["o"] == a["hi"] == a["lo"] == a["p"] and a["abs"] == 0 and not any(u):
        return [a["n"]]
    return [r(a["o"]), r(a["hi"]), r(a["lo"]), a["n"], a["abs"]] + u


def handel(feed: dict, isin: str):
    """[Abschlüsse F, T, X, Umsatz F, T, X] des Handelstags für die Historie – nur, wenn gehandelt wurde, sonst None."""
    da = [feed[k][isin] if k in feed and isin in feed[k] else None for k in ("F", "T", "X")]
    ab = [x["abs"] if x else 0 for x in da]
    um = [round(x["u"]) if x else 0 for x in da]
    return ab + um if any(ab) or any(um) else None


def eintrag_ohne_index(feed: dict, isin: str, vortag):
    """Kurseintrag eines Papiers außerhalb des Anleihen-Index (ETF): Kurs je Anteil, Xetra vor Tradegate vor
    Frankfurt, Umsatz aller drei Plätze; None ohne Feststellung."""
    quelle = next((k for k in ("X", "T", "F") if isin in feed.get(k, {})), None)
    if quelle is None:
        return None
    a = feed[quelle][isin]
    umsatz = sum(feed[k][isin]["u"] for k in ("F", "T", "X") if k in feed and isin in feed[k])
    return [round(a["p"], 4 if a["p"] < 10 else 3), None, a["t"][:10], quelle, round(umsatz),
            tagesdaten(feed, isin, quelle, 1.0), vortag, None]


def verarbeite(tag: str, feed: dict, zeilen: dict, auswahl: set, bbk: dict, etf: dict | None = None) -> int:
    """Kurse eines Handelstags in die Kursdateien und den Kursverlauf schreiben."""
    etf = etf or {}
    behalten = set(zeilen) | auswahl | set(etf)
    d_tag = datetime.date.fromisoformat(tag)
    # 2) Bundesbank: für den Handelstag gilt der Bundesbank-Kurs
    bund = {i: p for i, pts in bbk.items() for p in pts if p[0] == tag}

    # Bund-Renditekurve des Tags (Bundesbank): (Restlaufzeit in Jahren, Rendite) der Bundeswertpapiere ohne Inflationsschutz –
    # Grundlage für den BERECHNETEN Renditeaufschlag der Euro-Anleihen
    valuta = plus_abwicklungstage(d_tag, 2)
    kurve = bund_kurve(zeilen, bund, valuta)
    pruefkurve = None
    if len(kurve) < KURVE_MIN:
        kurve, kstand = bund_kurve_rueckfall(zeilen, bbk, tag, valuta)
        if kurve:
            # als Warnung mit Alter der Kurve (seit 09.10.2026, T-01) – vorher nur eine Zeile im Protokoll
            alter = (d_tag - datetime.date.fromisoformat(kstand)).days
            log_err(f"Bundesbank ohne Kurse vom {tag} – Aufschlag zu Bund gegen die Bund-Kurve vom {kstand}, "
                    f"{alter} Tage alt ({len(kurve)} Bundeswertpapiere).")
            if alter >= KURVE_WARNEN_TAGE:
                log_err(f"Bund-Kurve ist {alter} Tage alt")
        else:
            pruefkurve, pstand = bund_kurve_rueckfall(zeilen, bbk, tag, valuta, PRUEFKURVE_ALTER_TAGE)
            log_err(f"Keine Bund-Kurve vom {tag} und keine aus den letzten {KURVE_ALTER_TAGE} Tagen – kein Aufschlag zu Bund. "
                    + (f"Plausibilitätsregel (mehr als {-AUFSCHLAG_MIN:g} Punkt unter Bund) gegen die Bund-Kurve vom {pstand}."
                       if pruefkurve else f"Auch keine Bund-Kurve aus den letzten {PRUEFKURVE_ALTER_TAGE} Tagen für die "
                                          f"Plausibilitätsregel."))

    # Vortag: bisheriger Schlusskurs aus der eigenen Datei (für die BERECHNETE Veränderung)
    vor = {}
    for pfad in (OUT_ETF, OUT_AUSWAHL, OUT_SUCHE):
        alt0 = lade_json(pfad, {})
        if isinstance(alt0.get("kurse"), dict) and alt0.get("tage"):
            for isin, e in alt0["kurse"].items():
                try:
                    if alt0["tage"][e[2]] < tag:
                        vor[isin] = e[0]
                except (IndexError, TypeError):
                    pass

    # 3) Kurs je ISIN für den Handelstag
    neu = {}
    for isin in behalten:
        z = zeilen.get(isin)
        if z is None and isin not in bund:      # ETF oder anderes Papier außerhalb des Anleihen-Index
            e = eintrag_ohne_index(feed, isin, vor.get(isin))
            if e:
                neu[isin] = e
            continue
        ist_anleihe = z is not None
        reihenfolge = ("F", "T") if ist_anleihe else ("X", "T", "F")
        quelle = next((k for k in reihenfolge if isin in feed.get(k, {})), None)
        umsatz = sum(feed[k][isin]["u"] for k in ("F", "T", "X") if k in feed and isin in feed[k]
                     and (k != "X" or not ist_anleihe))
        if isin in bund:
            datum, kurs, rend = bund[isin]
            neu[isin] = [round(kurs, 3), None if rend is None else round(rend, 3), datum, "B", round(umsatz),
                         tagesdaten(feed, isin, "F", 1.0), vor.get(isin), None]
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
        rend, aufschlag = rendite_und_aufschlag(z, kurs, valuta, kurve, pruefkurve) if ist_anleihe else (None, None)
        neu[isin] = [round(kurs, 4 if kurs < 10 else 3), rend, a["t"][:10], quelle, round(umsatz),
                     tagesdaten(feed, isin, quelle, faktor), vor.get(isin), aufschlag]

    # 4) Mit dem Vortag zusammenführen, Schutzregel
    alt = lade_json(OUT_SUCHE, {})
    alt_kurse = alte_eintraege(OUT_SUCHE)
    frisch_alt = sum(1 for e in alt_kurse.values() if e[2] == alt.get("stand"))
    frisch_neu = sum(1 for isin, e in neu.items() if isin in zeilen and e[2] == tag)
    if frisch_alt and frisch_neu < MIN_ANTEIL * frisch_alt:
        log_err(f"Nur {frisch_neu} Anleihekurse statt zuvor {frisch_alt} – Dateien bleiben unverändert.")
        return 1
    grenze = (d_tag - datetime.timedelta(days=HALTEN_TAGE)).isoformat()
    # ETFs und andere Papiere außerhalb des Index: letzter Eintrag aus den eigenen Dateien – auch sie bleiben ohne
    # neuen Kurs bis zu HALTEN_TAGE stehen (seit 30.09.2026; vorher verschwand ein ETF ohne Feststellung sofort)
    alt_kurse.update({i: e for i, e in alte_eintraege(OUT_ETF, OUT_AUSWAHL).items() if i not in zeilen})
    alle = {i: e for i, e in alt_kurse.items() if e[2] >= grenze and (i in behalten)}
    alle.update(neu)

    n_suche, n_auswahl, n_etf = schreibe_kursdateien(alle, zeilen, auswahl, tag, etf)
    print(f"anleihen-kurse.json: {n_suche} Anleihen ({frisch_neu} vom {tag}); kurse-auswahl.json: {n_auswahl} Papiere"
          + (f"; etf-kurse.json: {n_etf} ETFs ({sum(1 for i in etf if i in neu and neu[i][2] == tag)} vom {tag})" if etf else ""))

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
                h = handel(feed, isin) if isin in heute else None
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
    kurse-auswahl.json, etf-kurse.json und „aktuell“ in kurse/<Jahr>/<hh>.json."""
    zeilen = {r[0]: r for r in lade_json(INDEX, {}).get("rows", [])}
    such = lade_json(OUT_SUCHE, {})
    stand = such.get("stand")
    if not zeilen or not isinstance(such.get("kurse"), dict) or not stand:
        log_err("anleihen-index.json oder anleihen-kurse.json fehlt – nichts neu gerechnet.")
        return 1
    alle = alte_eintraege(OUT_ETF, OUT_AUSWAHL, OUT_SUCHE)   # die Suchdatei zuletzt: sie hat Vorrang
    auswahl, etf = auswahl_isins(), etf_register()
    vorher = len(alle)
    alle = {i: e for i, e in alle.items() if i in zeilen or i in auswahl or i in etf}
    # Bund-Renditekurve je Kursdatum aus den Bundesbank-Einträgen (wie im Tageslauf)
    kurven = {}
    for isin, e in alle.items():
        z = zeilen.get(isin)
        if e[3] == "B" and z and z[5] and e[1] is not None and not INFLATION.search(z[1]):
            val = plus_abwicklungstage(datetime.date.fromisoformat(e[2]), 2)
            kurven.setdefault(e[2], []).append(((datetime.date.fromisoformat(z[5]) - val).days / 365.25, e[1]))
    for k in kurven.values():
        k.sort()
    geaendert = collections.Counter()
    pruef = {}   # Kursdatum ohne eigene Kurve → Bund-Kurve bis PRUEFKURVE_ALTER_TAGE alt, nur für AUFSCHLAG_MIN (seit 09.10.2026)
    for isin, e in alle.items():
        z = zeilen.get(isin)
        if not z or e[3] == "B":
            continue
        valuta = plus_abwicklungstage(datetime.date.fromisoformat(e[2]), 2)
        if e[2] not in kurven and e[2] not in pruef:
            pruef[e[2]] = bund_kurve_rueckfall(zeilen, {}, e[2], valuta, PRUEFKURVE_ALTER_TAGE)[0]
        rend, auf = rendite_und_aufschlag(z, e[0], valuta, kurven.get(e[2]), pruef.get(e[2]))
        if e[2] not in kurven and rend is not None and not bundeswertpapier(z):
            auf = e[7]                          # kein Bund-Kurs vom selben Tag gespeichert: Aufschlag bleibt
        if e[1] != rend:
            geaendert["Rendite"] += 1
        if e[7] != auf:
            geaendert["Aufschlag"] += 1
        e[1], e[7] = rend, auf
    n_suche, n_auswahl, _ = schreibe_kursdateien(alle, zeilen, auswahl, stand, etf)
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


def nachtragen() -> int:
    """--nachtragen: Tage, die schon im Kursverlauf stehen, für ETFs und andere Papiere außerhalb des Anleihen-Index
    ergänzen, die an dem Tag noch keinen Wert haben – etwa ETFs, die erst später ins Register kamen, oder die 68 ETFs,
    die vom 29.09.2026 an ohne Kurs blieben. Liest die Tagesdateien aus FIXTURE_DIR (Rohdaten-Artefakt des Workflows)
    oder die bei der Börse noch gelisteten. Vorhandene Werte bleiben, Anleihen des Index werden nicht angefasst.
    Schreibt kurse/<Jahr>/<hh>.json (k, u, h, aktuell), kurse-auswahl.json und etf-kurse.json."""
    zeilen = {r[0]: r for r in lade_json(INDEX, {}).get("rows", [])}
    stand = (lade_json(OUT_SUCHE, {}) or {}).get("stand") or ""
    if not zeilen or not stand:
        log_err("anleihen-index.json oder anleihen-kurse.json fehlt – nichts nachgetragen.")
        return 1
    auswahl, etf = auswahl_isins(), etf_register()
    waehrung = ohne_index(zeilen, auswahl, etf)
    je_teil = collections.defaultdict(list)
    for isin in sorted(waehrung):
        je_teil[teil(isin)].append(isin)
    listen = {}
    for k in ("X", "T", "F"):
        try:
            listen[k] = tagesdateien(k)
        except Exception as e:  # noqa: BLE001
            log_err(f"{DIENSTE[k]}: Dateiliste nicht abrufbar ({e}).")
            listen[k] = []
    tage = sorted({d for k in listen for d, _ in listen[k] if d <= stand})
    if not tage:
        print(f"Keine Tagesdatei bis zum Stand {stand} – nichts nachzutragen.")
        return 0
    alle = alte_eintraege(OUT_ETF, OUT_AUSWAHL, OUT_SUCHE)
    gesamt = 0
    for tag in tage:
        feed = {}
        for k in ("X", "T", "F"):
            for d, name in listen[k]:
                if d == tag:
                    try:
                        roh = tagesdatei_holen(k, name)
                    except Exception as e:  # noqa: BLE001
                        log_err(f"{DIENSTE[k]}: {name} nicht abrufbar ({e}).")
                        roh = None
                    if roh:
                        feed[k] = auswerten(roh, set(waehrung), waehrung)[1]
                    break
        n_tag = 0
        for t, isins in je_teil.items():
            pfad = DIR_VERLAUF / tag[:4] / f"{t}.json"
            v = lade_json(pfad, None)
            if not v or tag not in (v.get("tage") or []):
                continue
            n, geaendert = v["tage"].index(tag), False
            for isin in isins:
                reihe = v["k"].get(isin) or []
                if len(reihe) > n and reihe[n] is not None:
                    continue                                   # Wert vorhanden – bleibt
                e = eintrag_ohne_index(feed, isin, next((x for x in reversed(reihe[:n]) if x is not None), None))
                if not e or e[2] != tag:
                    continue
                reihe = v["k"].setdefault(isin, reihe)
                reihe.extend([None] * (len(v["tage"]) - len(reihe)))
                reihe[n] = e[0]
                if e[4] > 0:
                    v.setdefault("u", {}).setdefault(isin, {})[str(n)] = e[4]
                h = handel(feed, isin)
                if h:
                    v.setdefault("h", {}).setdefault(isin, {})[str(n)] = h
                if "aktuell" in v and (isin not in v["aktuell"] or v["aktuell"][isin][2] < tag):
                    v["aktuell"][isin] = e
                if isin not in alle or alle[isin][2] < tag:
                    alle[isin] = e
                geaendert, n_tag = True, n_tag + 1
            if geaendert:
                if "aktuell" in v:
                    v["aktuell"] = dict(sorted(v["aktuell"].items()))
                write_atomic(pfad, v, indent=None)
        print(f"Nachgetragen {tag}: {n_tag} Kurse")
        gesamt += n_tag
    if gesamt:
        _, n_auswahl, n_etf = schreibe_kursdateien(alle, zeilen, auswahl, stand, etf, suche=False)
        print(f"kurse-auswahl.json: {n_auswahl} Papiere; etf-kurse.json: {n_etf} ETFs")
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
