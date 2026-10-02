#!/usr/bin/env python3
"""update_bonitaet.py – Bonitätsstufe laut EZB je Anleihe (seit 02.10.2026).

Warum: Ratings gehören den Agenturen und dürfen ohne Lizenz nicht gezeigt werden (docs/DATENQUELLEN.md). Frei nutzbar
ist die Liste der notenbankfähigen Sicherheiten der EZB – dieselbe Tagesdatei wie in update_top10_kupon.py. Sie nennt
kein Rating, aber je Wertpapier den Bewertungsabschlag („Haircut“). Der Abschlag hängt nach den Regeln der EZB nur von
vier Dingen ab: Abschlagsklasse (I–IV), Restlaufzeit, Kuponart und Bonitätsstufe. Die ersten drei stehen in der Liste –
die Bonitätsstufe lässt sich deshalb aus der amtlichen Abschlagstabelle zurücklesen:
    Stufen 1 und 2  = AAA bis A−     (bei Moody’s Aaa bis A3)
    Stufe 3         = BBB+ bis BBB−  (bei Moody’s Baa1 bis Baa3)
Feiner trennt die Tabelle nicht (Stufe 1 und 2 haben denselben Abschlag).

Quellen:
  EZB, Liste der notenbankfähigen marktfähigen Sicherheiten, Tagesdatei
      https://www.ecb.europa.eu/paym/coll/assets/html/dla/ea_MID/ea_csv_<JJMMTT>.csv.gz   (UTF-16, Tabulator)
      Spalten: ISIN_CODE, HAIRCUT_CATEGORY (L1A–L1E = Klasse I–V), DENOMINATION, MATURITY_DATE, COUPON_DEFINITION,
      HAIRCUT. Nutzung laut EZB frei, wenn die EZB als Quelle genannt und eine Bearbeitung kenntlich gemacht wird.
  Abschlagstabelle: Leitlinie EZB/2015/35 (EU 2016/65) in der Fassung der Leitlinie EZB/2022/49, gültig seit
      29.06.2023, Anhang Tabelle 2 – unten als TABELLE. Am 02.10.2026 mit der Liste vom 01.10.2026 verglichen: Jede
      Zelle, die in der Liste vorkommt, stimmt.
  Stufen und Ratingnoten: „Eurosystem’s harmonised rating scale“ (ecb.europa.eu, Eurosystem credit assessment framework).
      Gibt es mehrere Ratings, zählt für die EZB das beste der von ihr anerkannten Agenturen.

Rechenweg (stufe()):
  * Fremdwährung: Die Liste rechnet bei Dollar und Pfund 16 %, bei Yen 26 % Währungsabschlag ein:
    Abschlag = 1 − (1 − Tabellenwert) × (1 − Währungsabschlag). Das wird zurückgerechnet.
  * Restlaufzeit am Tag der Liste → Laufzeitband; passt der Abschlag zu einem der beiden Tabellenwerte des Bands
    (Spalte laut Kuponart: fester/variabler Kupon oder Nullkupon), steht die Stufe fest. Wenige Tage vor oder nach
    einer Bandgrenze zählen beide Bänder – die Stufe gilt dann nur, wenn sie in beiden dieselbe ist.
  * Klasse V (Verbriefungen, L1E) und alles, was nicht passt: auf der Liste, Stufe offen (0).
  Steht eine Anleihe nicht auf der Liste, gibt es keine Angabe – das sagt nichts über ihre Bonität (die Liste führt
  nur im Europäischen Wirtschaftsraum begebene, nicht nachrangige Papiere in Euro, Dollar, Pfund und Yen).

Schutz: Ist keine Liste der letzten Tage abrufbar, ist sie unplausibel klein oder passen weniger als MIN_TREFFER der
Abschläge zur Tabelle (dann hat die EZB die Tabelle geändert), bleibt alles beim letzten Stand.

Schreibt:
  bonitaet/ezb-stufen.json   {"stand": Datum der Liste, "stufen": {ISIN: 1 | 3 | 0}} – nur Anleihen des Index; wird
                             committet, nicht veröffentlicht. Gelesen von suchindex.py (Filter der Suche).
  anleihen/<hh>.json         Teildateien des Steckbriefs: Kopf „ezb“ = Stand der Liste; jede Anleihe der Liste bekommt
                             als 16. Feld die Stufe (1 = Stufen 1 und 2, 3 = Stufe 3, 0 = auf der Liste, Stufe offen).
                             Fehlt das 15. Feld (Zinstermine, update_zinstermine.py), steht dort 0 als Platzhalter.
                             update_anleihen_index.py schreibt die Teildateien wöchentlich neu (ohne das Feld);
                             dieses Skript läuft danach und setzt es wieder ein.

Aufruf:
  python scripts/update_bonitaet.py                 Liste holen, Datei und Teildateien schreiben
  python scripts/update_bonitaet.py --ohne-abruf    nur die Teildateien aus der vorhandenen Datei neu setzen
  FIXTURE_DIR=<Ordner> python scripts/update_bonitaet.py
                                                    Liste lokal lesen (<Ordner>/ea_csv_<JJMMTT>.csv.gz, die jüngste)
"""

import datetime
import gzip
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import get_with_retry, log_err, now_iso, today_iso, write_atomic  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
INDEX = ROOT / "anleihen-index.json"
DIR_TEILE = ROOT / "anleihen"
OUT = ROOT / "bonitaet" / "ezb-stufen.json"

EZB_URL = "https://www.ecb.europa.eu/paym/coll/assets/html/dla/ea_MID/ea_csv_{:%y%m%d}.csv.gz"
EZB_TAGE_ZURUECK = 7      # Wochenende plus Feiertage – älter soll die Liste nicht sein (wie update_top10_kupon.py)
EZB_MIN_ZEILEN = 20000    # die Liste hat rund 31.000 Zeilen
MIN_TREFFER = 0.95        # Anteil der Papiere der Klassen I–IV, deren Abschlag zur Tabelle passt (01.10.2026: 99,9 %)
SPALTEN = ("ISIN_CODE", "HAIRCUT_CATEGORY", "DENOMINATION", "MATURITY_DATE", "COUPON_DEFINITION", "HAIRCUT")

# Laufzeitbänder in Jahren: [0-1) [1-3) [3-5) [5-7) [7-10) [10-15) [15-30) [30-∞)
BAENDER = (1, 3, 5, 7, 10, 15, 30)
# Abschläge in Prozent je Klasse: (Stufen 1 und 2, Stufe 3), jeweils (fester oder variabler Kupon, Nullkupon) je Band
TABELLE = {
    "L1A": (((0.5, 1.0, 1.5, 2.0, 3.0, 4.0, 5.0, 6.0), (0.5, 2.0, 2.5, 3.0, 4.0, 5.0, 6.0, 9.0)),
            ((5.0, 6.0, 8.5, 10.0, 11.5, 12.5, 13.5, 14.0), (5.0, 7.0, 10.0, 11.5, 13.0, 14.0, 15.0, 17.0))),
    "L1B": (((1.0, 1.5, 2.5, 3.5, 4.5, 6.5, 8.0, 10.0), (1.0, 2.5, 3.5, 4.5, 6.5, 8.5, 11.5, 13.0)),
            ((5.5, 7.5, 11.0, 12.5, 14.0, 17.0, 20.0, 22.0), (5.5, 10.5, 16.0, 17.0, 21.0, 25.5, 28.5, 32.5))),
    "L1C": (((1.0, 2.0, 3.0, 4.5, 6.0, 7.5, 9.0, 11.0), (1.0, 3.0, 4.5, 6.0, 8.0, 10.0, 13.0, 16.0)),
            ((6.5, 9.5, 13.0, 15.0, 17.0, 19.5, 22.0, 25.0), (6.5, 12.0, 18.0, 21.5, 23.5, 28.0, 31.0, 35.5))),
    "L1D": (((7.5, 10.0, 12.0, 14.0, 16.0, 18.0, 21.0, 24.0), (7.5, 11.5, 13.0, 15.0, 17.5, 22.5, 25.0, 31.5)),
            ((11.5, 18.5, 23.0, 25.5, 26.5, 28.5, 31.5, 34.5), (11.5, 20.0, 27.0, 29.5, 31.5, 35.0, 39.0, 43.0))),
}
WAEHRUNGSABSCHLAG = {"USD": 16.0, "GBP": 16.0, "JPY": 26.0}   # Prozent; Euro und frühere Euro-Währungen: keiner
TOLERANZ = 0.06   # die Liste rundet auf eine Nachkommastelle
RAND_TAGE = 3     # so nah an einer Bandgrenze kann die EZB das andere Band rechnen (Zählweise, Stand der Liste)


def lade(pfad: Path, leer):
    try:
        return json.loads(pfad.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return leer


def band(faellig: datetime.date, tag: datetime.date) -> int:
    """Laufzeitband (0–7) zur Restlaufzeit am Tag der Liste – nach Jahrestagen, nicht nach Tagen ÷ 365."""
    for n, jahre in enumerate(BAENDER):
        try:
            grenze = tag.replace(year=tag.year + jahre)
        except ValueError:            # 29. Februar
            grenze = tag.replace(year=tag.year + jahre, day=28)
        if faellig < grenze:
            return n
    return len(BAENDER)


def stufe(klasse: str, waehrung: str, faellig, nullkupon: bool, abschlag: float, tag: datetime.date) -> int:
    """1 = Bonitätsstufen 1 und 2, 3 = Stufe 3, 0 = nicht ablesbar (Regeln im Kopf der Datei)."""
    tab = TABELLE.get(klasse)
    if tab is None or faellig is None:
        return 0
    wa = WAEHRUNGSABSCHLAG.get(waehrung, 0.0)
    wert = (1 - (1 - abschlag / 100) / (1 - wa / 100)) * 100 if wa else abschlag

    def im_band(b: int, spalte: int) -> int:
        oben, unten = abs(wert - tab[0][spalte][b]) <= TOLERANZ, abs(wert - tab[1][spalte][b]) <= TOLERANZ
        return 1 if oben and not unten else 3 if unten and not oben else 0

    # An einer Bandgrenze (± RAND_TAGE) zählen beide Bänder – die Stufe gilt nur, wenn sie in allen dieselbe ist
    baender = {band(faellig, tag + datetime.timedelta(days=d)) for d in (-RAND_TAGE, 0, RAND_TAGE)}
    for spalte in ((1, 0) if nullkupon else (0, 1)):   # erst die Spalte laut Kuponart, dann die andere
        funde = {im_band(b, spalte) for b in baender} - {0}
        if funde:
            return funde.pop() if len(funde) == 1 else 0
    return 0


def ezb_datei(heute: datetime.date):
    """Jüngste Tagesdatei der EZB: (Datum der Datei, Rohdaten) oder (None, None)."""
    fix = os.environ.get("FIXTURE_DIR")
    if fix:
        dateien = sorted(Path(fix).glob("ea_csv_*.csv.gz"))
        if not dateien:
            return None, None
        return datetime.datetime.strptime(dateien[-1].name[7:13], "%y%m%d").date(), dateien[-1].read_bytes()
    for n in range(EZB_TAGE_ZURUECK + 1):
        tag = heute - datetime.timedelta(days=n)
        if tag.weekday() > 4:
            continue
        try:
            return tag, get_with_retry(EZB_URL.format(tag), timeout=60)
        except Exception as e:   # 404 = Datei des Tages gibt es (noch) nicht – den Vortag versuchen
            print(f"EZB-Liste vom {tag.isoformat()}: nicht abrufbar ({e})")
    return None, None


def lies_liste(heute: datetime.date):
    """(Datum der Liste, {ISIN: Stufe} aller Papiere der Liste, Anteil der Klassen I–IV mit ablesbarer Stufe)."""
    tag, roh = ezb_datei(heute)
    if roh is None:
        raise ValueError("keine EZB-Liste der letzten Tage abrufbar")
    zeilen = gzip.decompress(roh).decode("utf-16").splitlines()
    kopf = zeilen[0].split("\t") if zeilen else []
    if any(s not in kopf for s in SPALTEN) or len(zeilen) < EZB_MIN_ZEILEN:
        raise ValueError(f"EZB-Liste vom {tag.isoformat()}: unerwartetes Format ({len(zeilen)} Zeilen, Kopf {kopf[:3]})")
    s_isin, s_kl, s_w, s_f, s_k, s_h = (kopf.index(s) for s in SPALTEN)
    breite = max(s_isin, s_kl, s_w, s_f, s_k, s_h)
    out, einstufbar, erkannt = {}, 0, 0
    for z in zeilen[1:]:
        f = z.split("\t")
        if len(f) <= breite or len(f[s_isin]) != 12:
            continue
        try:
            faellig = datetime.datetime.strptime(f[s_f][:10], "%d/%m/%Y").date()
        except ValueError:
            faellig = None
        try:
            s = stufe(f[s_kl], f[s_w], faellig, f[s_k] == "CD1", float(f[s_h]), tag)   # CD1 = Nullkupon
        except ValueError:
            s = 0
        if f[s_kl] in TABELLE:
            einstufbar += 1
            erkannt += 1 if s else 0
        out[f[s_isin]] = s
    return tag, out, (erkannt / einstufbar if einstufbar else 0.0)


def teildateien(stufen: dict, stand: str) -> int:
    """Feld 16 (Bonitätsstufe laut EZB) und den Kopf „ezb“ in anleihen/<hh>.json setzen; Zahl der geänderten Dateien."""
    geaendert = 0
    for pfad in sorted(DIR_TEILE.glob("*.json")):
        d = lade(pfad, None)
        if not d or not isinstance(d.get("rows"), dict):
            continue
        neu = d.get("ezb") != stand
        d["ezb"] = stand
        for isin, row in d["rows"].items():
            s = stufen.get(isin)
            alt = row[15] if len(row) > 15 else None
            if s == alt:
                continue
            del row[15:]
            if s is not None:
                if len(row) == 14:
                    row.append(0)      # Platzhalter für die Zinstermine (Feld 15)
                row.append(s)
            elif len(row) == 15 and not row[14]:
                del row[14:]           # Platzhalter wieder entfernen
            neu = True
        if neu:
            write_atomic(pfad, d, indent=None)
            geaendert += 1
    return geaendert


def main() -> int:
    index = {r[0] for r in lade(INDEX, {}).get("rows", [])}
    if not index:
        log_err("Bonitätsstufe: anleihen-index.json fehlt oder ist leer – nichts geändert.")
        return 1
    alt = lade(OUT, {})
    stufen = {i: s for i, s in (alt.get("stufen") or {}).items() if i in index}
    stand, rc = alt.get("stand") or "", 0
    if "--ohne-abruf" not in sys.argv:
        try:
            tag, liste, anteil = lies_liste(datetime.date.fromisoformat(today_iso()))
        except Exception as e:  # noqa: BLE001
            log_err(f"Bonitätsstufe: {e} – bisherige Stufen bleiben.")
            liste, rc = None, 1
        if liste is not None and anteil < MIN_TREFFER:
            log_err(f"Bonitätsstufe: nur {anteil:.1%} der Abschläge der EZB-Liste vom {tag.isoformat()} passen zur "
                    "Abschlagstabelle – hat die EZB die Tabelle geändert? Bisherige Stufen bleiben.")
            liste, rc = None, 1
        if liste is not None:
            neu = {i: s for i, s in liste.items() if i in index}
            anders = sum(1 for i, s in neu.items() if i in stufen and stufen[i] != s)
            stufen, stand = neu, tag.isoformat()
            inhalt = {"stand": stand, "quelle": "EZB, Liste der notenbankfähigen marktfähigen Sicherheiten: Bonitätsstufe "
                      "aus dem Bewertungsabschlag abgelesen (scripts/update_bonitaet.py)",
                      "felder": "1 = Bonitätsstufen 1 und 2 (AAA bis A−), 3 = Stufe 3 (BBB+ bis BBB−), 0 = auf der Liste, Stufe offen",
                      "anzahl": len(stufen), "stufen": dict(sorted(stufen.items()))}
            if inhalt != {k: v for k, v in alt.items() if k != "updatedAt"}:
                # eine Anleihe je Zeile, damit Git-Diffs klein bleiben
                kopf = json.dumps({**{k: v for k, v in inhalt.items() if k != "stufen"}, "updatedAt": now_iso()}, ensure_ascii=False)
                text = kopf[:-1] + ', "stufen": {\n' + ",\n".join(f'{json.dumps(i)}: {s}' for i, s in inhalt["stufen"].items()) + "\n}}\n"
                OUT.parent.mkdir(parents=True, exist_ok=True)
                tmp = OUT.with_name(OUT.name + ".tmp")
                tmp.write_text(text, encoding="utf-8")
                os.replace(tmp, OUT)
            zahl = {s: sum(1 for v in stufen.values() if v == s) for s in (1, 3, 0)}
            print(f"Bonitätsstufe (EZB-Liste vom {stand}, {len(liste)} Papiere, {anteil:.1%} ablesbar): {len(stufen)} Anleihen "
                  f"des Index – Stufen 1 und 2: {zahl[1]}, Stufe 3: {zahl[3]}, offen: {zahl[0]}; {anders} geändert")
    if not stand:
        log_err("Bonitätsstufe: noch keine Stufen vorhanden – Teildateien unverändert.")
        return 1
    n = teildateien(stufen, stand)
    print(f"anleihen/<hh>.json: {n} Teildateien mit Bonitätsstufe aktualisiert")
    return rc


if __name__ == "__main__":
    sys.exit(main())
