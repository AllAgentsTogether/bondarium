#!/usr/bin/env python3
"""update_zinstermine.py – Zinstermine der Anleihen aus der Instrumentenliste der Deutschen Börse (seit 02.10.2026).

Warum: Das Register (ESMA FIRDS) nennt weder die Zahl der Zinszahlungen je Jahr noch die Zinstermine. Bis 02.10.2026
schätzte die Website beides aus Währung und Fälligkeitstag. Gemessen an dieser Liste lag die Schätzung bei rund 1.500 von
29.700 Anleihen falsch (Pfund- und Dollar-Anleihen mit internationaler ISIN, Euro-Hochzinsanleihen, Mittelstandsanleihen
mit Halbjahres- oder Quartalszins, Staatsanleihen Maltas) – damit auch Stückzinsen, Zahlungsplan und Rendite.

Quelle (frei abrufbar, ohne Anmeldung, börsentäglich neu):
  Deutsche Börse, „T7 (Frankfurt) – Alle handelbaren Instrumente“ (t7-xfra-BF-allTradableInstruments.csv, ~44 MB,
  Trennzeichen „;“, zwei Kopfzeilen „Market:“ und „Date Last Update:“). Der Link trägt eine Prüfsumme und steht auf
  https://www.cashmarket.deutsche-boerse.com/cash-de/Handel/Handelbare-Werte-Xetra/frankfurt – er wird bei jedem Lauf
  von dort gelesen. Genutzte Spalten: ISIN, Instrument Type (BOND), Issue Date, Previous Coupon Payment Date,
  Next Coupon Payment Date.
  Nutzungsrechte: Zu dieser Liste nennt die Börse keine Bedingungen (Stand 02.10.2026) – gleiche Lage wie bei der
  ETF-Liste (scripts/update_etf_index.py). Die Website zeigt nur die daraus abgeleiteten Zinstage, nicht die Liste.

Was daraus wird (rhythmus()):
  * Liegt der letzte Zinstermin nach dem Ausgabetag, ist er ein echter Termin: Der Abstand zum nächsten Termin gibt die
    Zahl der Zahlungen je Jahr (12 Monate → 1, 6 → 2, 3 → 4, 1 → 12), die beiden Termine geben die Zinstage.
  * Vor dem ersten Zinstermin steht als „letzter Termin“ der Ausgabetag. Dann zählt die Lage des nächsten Termins zum
    Fälligkeitstag: um ein halbes Jahr versetzt → halbjährlich, um ein Vierteljahr → vierteljährlich; auf dem Jahrestag
    und mindestens zwölf Monate nach der Ausgabe → jährlich. Auf dem Jahrestag, aber früher: offen (kurzer erster
    Kupon einer jährlichen oder regulärer Kupon einer halbjährlichen Anleihe) – kein Eintrag, bis der Termin vorbei ist.
  * Alles andere (keine Termine, ungerader Abstand): kein Eintrag.
  Ein einmal erkannter Eintrag bleibt stehen, bis die Liste etwas anderes sagt oder die Anleihe aus dem Index fällt –
  so übersteht er Tage, an denen die Liste fehlt oder die Anleihe dort nicht gehandelt wird.
  Gegenprobe am 02.10.2026 mit Börsen-Stammdaten einer zweiten Quelle (947 Anleihen, nur nachgeschlagen): 943 gleich;
  die vier Abweichungen waren neue Anleihen vor dem ersten Zinstermin – der Fall „offen“ oben.

Schreibt:
  zinstermine/zinstermine.json   {"stand": Datum der Liste, "termine": {ISIN: [zahlungen_je_jahr, "MM-TT", …]}} –
                                 nur Anleihen des Index mit festem Kupon über 0; wird committet, nicht veröffentlicht.
                                 Gelesen von update_kurse.py (Rendite), update_top10.py, update_top10_kupon.py
                                 (_common.zinsplan / zins_felder).
  anleihen/<hh>.json             Teildateien des Steckbriefs: jede Zeile einer Anleihe mit festem Kupon über 0 bekommt
                                 als 15. Feld [zahlungen_je_jahr, "MM-TT", …] laut Liste oder – geschätzt – nur
                                 [zahlungen_je_jahr] (_common.zinsfrequenz). anleihe.html und konto.html lesen es.
                                 Ein 16. Feld (Bonitätsstufe laut EZB, update_bonitaet.py) bleibt unberührt; steht es
                                 ohne Zinstermine da, ist das 15. Feld der Platzhalter 0.
                                 update_anleihen_index.py schreibt die Teildateien wöchentlich neu (ohne das Feld);
                                 dieses Skript läuft danach und setzt es wieder ein.

Aufruf:
  python scripts/update_zinstermine.py                 Liste holen, Datei und Teildateien schreiben
  python scripts/update_zinstermine.py --ohne-abruf    nur die Teildateien aus der vorhandenen Datei neu setzen
  FIXTURE_DIR=<Ordner> python scripts/update_zinstermine.py
                                                       Liste lokal lesen (<Ordner>/t7-xfra-BF-allTradableInstruments.csv)
"""

import csv
import datetime
import io
import json
import os
import re
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import ZINSTERMINE, get_with_retry, log_err, monate_zurueck, now_iso, write_atomic, zinsfrequenz  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
INDEX = ROOT / "anleihen-index.json"
DIR_TEILE = ROOT / "anleihen"
BASIS = "https://www.cashmarket.deutsche-boerse.com"
SEITE = BASIS + "/cash-de/Handel/Handelbare-Werte-Xetra/frankfurt"
DATEI = "t7-xfra-BF-allTradableInstruments.csv"
UA = {"User-Agent": "bondarium.de Anleihen-Suche (Datenaufbereitung)", "Accept": "*/*"}
MIN_ANLEIHEN = 15000    # weniger Anleihen mit Zinsterminen in der Liste → Quelle defekt, nichts ändern (02.10.2026: ~35.000)
MIN_ANTEIL = 0.8        # weniger als 80 % der bisherigen Einträge bestätigt oder ersetzt → ebenso
AUSGABE_TOLERANZ = 10   # Tage: „letzter Zinstermin“ so nah am Ausgabetag ist der Ausgabetag (Zinslaufbeginn), kein Zinstermin
RHYTHMUS = {12: 1, 6: 2, 3: 4, 1: 12}


def lade(pfad: Path, leer):
    try:
        return json.loads(pfad.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return leer


def teil(isin: str) -> str:
    """Teildatei der Stammdaten – derselbe Hash wie in update_anleihen_index.py und site.js (MC.teil)."""
    h = 0
    for ch in isin:
        h = (h * 31 + ord(ch)) % 65536
    return f"{h % 256:02x}"


def datum(s: str):
    try:
        return datetime.date.fromisoformat((s or "").strip())
    except ValueError:
        return None


def md(d: datetime.date) -> str:
    return f"{d.month:02d}-{d.day:02d}"


def zinstage(anker: datetime.date, freq: int) -> list[str]:
    """Die Zinstage eines Jahres „MM-TT“ zu einem Termin und der Zahl der Zahlungen je Jahr, aufsteigend."""
    return sorted({md(monate_zurueck(anker, k * 12 // freq)) for k in range(freq)})


def rhythmus(letzter, naechster, ausgabe, faellig):
    """[zahlungen_je_jahr, "MM-TT", …] aus den Terminen der Liste oder None (keine Aussage) – Regeln im Kopf der Datei."""
    if not letzter or not naechster or naechster <= letzter:
        return None
    monate = (naechster.year - letzter.year) * 12 + naechster.month - letzter.month
    if ausgabe is None or (letzter - ausgabe).days > AUSGABE_TOLERANZ:      # echter Zinstermin
        freq = RHYTHMUS.get(monate)
        if not freq:
            return None
        if freq <= 2:                                   # die Termine selbst (30.04. und 30.10. – nicht 31.10.)
            return [freq] + sorted({md(naechster)} if freq == 1 else {md(letzter), md(naechster)})
        return [freq] + zinstage(max(letzter, naechster, key=lambda d: d.day), freq)
    if not faellig:
        return None
    versatz = ((faellig.year - naechster.year) * 12 + faellig.month - naechster.month) % 12
    if versatz == 6:
        return [2] + zinstage(naechster, 2)
    if versatz in (3, 9):
        return [4] + zinstage(naechster, 4)
    if versatz == 0 and monate >= 12:
        return [1, md(naechster)]
    return None


def boersenliste():
    """Zeilen der Instrumentenliste als Textstrom (Zeile für Zeile gelesen – die Datei hat ~44 MB)."""
    fix = os.environ.get("FIXTURE_DIR")
    if fix:
        return open(Path(fix) / DATEI, encoding="utf-8", errors="replace", newline="")
    html = get_with_retry(SEITE, headers=UA, timeout=60).decode("utf-8", "replace")
    m = re.search(r'href="((?:https://www\.cashmarket\.deutsche-boerse\.com)?/resource/blob/[^"]+/' + re.escape(DATEI) + r')"', html)
    if not m:
        raise ValueError("Link zur Instrumentenliste auf der Seite der Börse nicht gefunden")
    link = m.group(1) if m.group(1).startswith("http") else BASIS + m.group(1)
    antwort = urllib.request.urlopen(urllib.request.Request(link, headers=UA), timeout=300)  # noqa: S310 – feste Adresse der Börse
    return io.TextIOWrapper(antwort, encoding="utf-8", errors="replace", newline="")


def lies_liste(zeilen: dict) -> tuple[str, dict, int]:
    """(Stand der Liste, {ISIN: [zahlungen_je_jahr, "MM-TT", …]} der Anleihen in `zeilen`, Zahl der Anleihen der Liste
    mit beiden Terminen)."""
    stand, out, mit_terminen = "", {}, 0
    with boersenliste() as strom:
        kopf = None
        for z in csv.reader(strom, delimiter=";"):
            if kopf is None:
                if z and z[0].startswith("Date Last Update") and len(z) > 1:
                    t = z[1].strip().split(".")
                    stand = "-".join(reversed(t)) if len(t) == 3 else ""
                elif "ISIN" in z and "Next Coupon Payment Date" in z:
                    kopf = {name: n for n, name in enumerate(z)}
                    s_isin, s_typ, s_aus = kopf["ISIN"], kopf["Instrument Type"], kopf["Issue Date"]
                    s_vor, s_nae = kopf["Previous Coupon Payment Date"], kopf["Next Coupon Payment Date"]
                    breite = max(s_isin, s_typ, s_aus, s_vor, s_nae)
                continue
            if len(z) <= breite or z[s_typ] != "BOND":
                continue
            letzter, naechster = datum(z[s_vor]), datum(z[s_nae])
            if letzter and naechster:
                mit_terminen += 1
            r = zeilen.get(z[s_isin])
            if r is None:
                continue
            e = rhythmus(letzter, naechster, datum(z[s_aus]), datum(r[5]))
            if e:
                out[z[s_isin]] = e
    if kopf is None:
        raise ValueError("Kopfzeile der Instrumentenliste nicht gefunden")
    return stand, out, mit_terminen


def teildateien(zeilen: dict, termine: dict) -> int:
    """Feld 15 (Zinstermine) in anleihen/<hh>.json setzen; gibt die Zahl der geänderten Dateien zurück."""
    geaendert = 0
    for pfad in sorted(DIR_TEILE.glob("*.json")):
        d = lade(pfad, None)
        if not d or not isinstance(d.get("rows"), dict):
            continue
        neu = False
        for isin, row in d["rows"].items():
            r = zeilen.get(isin)   # nur Anleihen mit festem Kupon; alle anderen bleiben ohne das Feld
            e = (termine.get(isin) or [zinsfrequenz(r)]) if r else None
            alt = (row[14] if len(row) > 14 else None) or None   # 0 = Platzhalter von update_bonitaet.py
            if e != alt:
                rest = row[15:]        # Feld 16 (Bonitätsstufe laut EZB, update_bonitaet.py) bleibt stehen
                del row[14:]
                if e or rest:
                    row.append(e or 0)
                    row.extend(rest)
                neu = True
        if neu:
            write_atomic(pfad, d, indent=None)
            geaendert += 1
    return geaendert


def fest(r: list) -> bool:
    """Fester Kupon über 0 mit Fälligkeit – nur dafür gibt es Zinstermine auf der Website."""
    return r[10] == 0 and isinstance(r[4], (int, float)) and r[4] > 0 and bool(r[5])


def main() -> int:
    zeilen = {r[0]: r for r in lade(INDEX, {}).get("rows", []) if fest(r)}
    if not zeilen:
        log_err("Zinstermine: anleihen-index.json fehlt oder ist leer – nichts geändert.")
        return 1
    alt = lade(ZINSTERMINE, {})
    termine = {i: e for i, e in (alt.get("termine") or {}).items() if i in zeilen}
    rc = 0
    if "--ohne-abruf" not in sys.argv:
        try:
            stand, neu, mit_terminen = lies_liste(zeilen)
        except Exception as e:  # noqa: BLE001
            log_err(f"Zinstermine: Instrumentenliste der Deutschen Börse nicht lesbar ({e}) – bisherige Termine bleiben.")
            neu, rc = None, 1
        if neu is not None:
            if mit_terminen < MIN_ANLEIHEN or (termine and len(neu) < MIN_ANTEIL * len(termine)):
                log_err(f"Zinstermine: Liste mit nur {mit_terminen} Anleihen mit Terminen, {len(neu)} davon im Index "
                        f"(bisher {len(termine)}) – bisherige Termine bleiben.")
                rc = 1
            else:
                anders = sum(1 for i, e in neu.items() if i in termine and termine[i] != e)
                dazu = sum(1 for i in neu if i not in termine)
                termine.update(neu)
                ZINSTERMINE.parent.mkdir(parents=True, exist_ok=True)
                inhalt = {"stand": stand or alt.get("stand") or "", "quelle": "Deutsche Börse, T7 (Frankfurt) – Alle handelbaren "
                          "Instrumente: letzter und nächster Zinstermin", "felder": ["zahlungen_je_jahr", "zinstage MM-TT …"],
                          "anzahl": len(termine), "termine": dict(sorted(termine.items()))}
                if inhalt != {k: v for k, v in alt.items() if k not in ("updatedAt",)}:
                    # eine Anleihe je Zeile, damit Git-Diffs klein bleiben
                    kopf = json.dumps({**{k: v for k, v in inhalt.items() if k != "termine"}, "updatedAt": now_iso()}, ensure_ascii=False)
                    text = kopf[:-1] + ', "termine": {\n' + ",\n".join(
                        f'{json.dumps(i)}: {json.dumps(e, separators=(",", ":"))}' for i, e in inhalt["termine"].items()) + "\n}}\n"
                    tmp = ZINSTERMINE.with_name(ZINSTERMINE.name + ".tmp")
                    tmp.write_text(text, encoding="utf-8")
                    os.replace(tmp, ZINSTERMINE)
                geschaetzt = len(zeilen) - len(termine)
                print(f"Zinstermine (Liste vom {stand or '?'}): {len(termine)} von {len(zeilen)} Anleihen mit festem Kupon, "
                      f"{dazu} neu, {anders} geändert; {geschaetzt} ohne Angabe (geschätzt)")
    n = teildateien(zeilen, termine)
    print(f"anleihen/<hh>.json: {n} Teildateien mit Zinsterminen aktualisiert")
    return rc


if __name__ == "__main__":
    sys.exit(main())
