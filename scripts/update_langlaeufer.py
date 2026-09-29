#!/usr/bin/env python3
"""Aktualisiert langlaeufer.json – Kursverlauf der beiden Bundesanleihen auf der
Seite langlaeufer.html:
    bund2050  0 % 15.08.2050 (DE0001102481), Nullkupon, ab Emission 21.08.2019
    bund2040  4,75 % 04.07.2040 (DE0001135366), Hochkupon-Langläufer aus 2008;
              Chart-Reihe ab Mitte 2019 (Fenster der Seite), Extremwerte der
              gesamten Historie

Quelle: Deutsche Bundesbank, Zeitreihen BBSSY (Einzelrenditen börsennotierter
Bundeswertpapiere), börsentäglich Kurs (KCP) und Rendite (REN) je ISIN:
    BBSSY.D.KCP.EUR.A640.<ISIN>.A   Kurs in % des Nennwerts
    BBSSY.D.REN.EUR.A640.<ISIN>.A   Rendite in % p. a. (ISMA)
Frei nutzbar mit Quellenangabe.

Die übrigen Anleihen der Seite (BTP 2072, Österreich 2120, US-Treasury 2050,
Frankreich 2072, Microsoft 2060) haben keine frei abrufbare Kursquelle; ihre
Wochenreihen stehen manuell in langlaeufer.html (Börse Stuttgart).

Struktur von langlaeufer.json je Anleihe (bonds.<key>):
    latest  = {"date": "JJJJ-MM-TT", "price": 40.07, "yield": 3.90}
    weekly  = [["JJJJ-MM-TT", Kurs, Rendite], …]  letzter Handelstag jeder
              ISO-Woche ab weeklyFrom (Chart-Reihe, ~52/Jahr)
    high / low = {"date", "price", "yield"}  Extremwerte der Tageskurse (Gesamthistorie)
    first   = {"date", "price", "yield"}     erster Handelstag
Zeitstempel checkedAt (jeder Abruf-Lauf), updated/updatedAt (nur bei Änderung).
Einzelne Ausreißer der Quelle fliegen vor der Auswertung raus (_common.ausreisser, seit 26.09.2026: ein Tageskurs,
der von beiden Nachbarn um mehr als 8 % in dieselbe Richtung abweicht oder um mehr als 4 %, ohne dass die Rendite
gegenläufig mitgeht – Bundesbank am 30.04.2021 für die 4,75 % 2040: 166,40 zwischen 189,25 und 187,52).

Läuft im vollen Lauf des Workflows (VOLL=1); ein Abruf holt immer die kompletten
Reihen (vier Anfragen à 60–150 KB) – eine Selbstdrosselung wie bei den anderen
Skripten (checkedAt) verhindert Doppelabrufe in FAST-Läufen.
"""

import csv
import datetime
import io
import json
import os
import re
import sys
from pathlib import Path

from _common import ausreisser, get_with_retry, log_err, now_iso, plausible, today_iso, write_atomic

DATA_FILE = Path(__file__).resolve().parent.parent / "langlaeufer.json"

# key → (ISIN, Beginn der Wochenreihe, Plausibilitätsgrenze in Kurspunkten)
BONDS = {
    "bund2050": ("DE0001102481", "2019-01-01", 8.0),
    "bund2040": ("DE0001135366", "2019-07-01", 12.0),
}
BUBA_URL = "https://api.statistiken.bundesbank.de/rest/data/BBSSY/D.{item}.EUR.A640.{isin}.A?detail=dataonly"
BUBA_ACCEPT = {"Accept": "application/vnd.sdmx.data+csv;version=1.0.0",
               "User-Agent": "Mozilla/5.0 (Datenaktualisierung Langläufer)"}


def fetch_series(item: str, isin: str) -> dict[str, float]:
    """Bundesbank-SDMX-CSV einer Tagesreihe → {"JJJJ-MM-TT": Wert} ("." = kein Wert)."""
    text = get_with_retry(BUBA_URL.format(item=item, isin=isin), headers=BUBA_ACCEPT, timeout=60).decode("utf-8-sig", "replace")
    out: dict[str, float] = {}
    for rec in csv.DictReader(io.StringIO(text), delimiter=";"):
        per, val = rec.get("TIME_PERIOD", ""), rec.get("OBS_VALUE", "")
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", per) or val in ("", "."):
            continue
        try:
            out[per] = float(val)
        except ValueError:
            continue
    return out


def weekly_points(price: dict[str, float], yld: dict[str, float], start: str) -> list[list]:
    """Letzter Handelstag jeder ISO-Woche ab start: [Datum, Kurs, Rendite]."""
    by_week: dict[tuple, str] = {}
    for d in sorted(price):
        if d < start:
            continue
        iso = datetime.date.fromisoformat(d).isocalendar()
        by_week[(iso[0], iso[1])] = d          # jede Woche: zuletzt gesehener (= letzter) Tag
    return [[d, round(price[d], 2), round(yld[d], 3) if d in yld else None] for d in sorted(by_week.values())]


def point(d: str, price: dict, yld: dict) -> dict:
    return {"date": d, "price": round(price[d], 2), "yield": round(yld[d], 2) if d in yld else None}


def update_bond(data: dict, key: str, isin: str, start: str, max_abs: float) -> bool:
    price = fetch_series("KCP", isin)
    yld = fetch_series("REN", isin)
    if not price:
        raise RuntimeError(f"Bundesbank lieferte keine Kurse für {isin}")
    tage = sorted(price)
    raus = ausreisser([price[d] for d in tage], renditen=[yld.get(d) for d in tage])
    if raus:
        print(f"{key}: Ausreißer der Quelle verworfen – " + ", ".join(f"{tage[i]} {price[tage[i]]}" for i in sorted(raus)))
        for i in raus:
            price.pop(tage[i], None)
            yld.pop(tage[i], None)
    bonds = data.setdefault("bonds", {})
    b = bonds.setdefault(key, {"isin": isin})
    days = sorted(price)
    newest = days[-1]
    old = b.get("latest") or {}
    if not plausible(price[newest], old.get("price"), f"langlaeufer {key}", max_abs=max_abs):
        return False   # Ausreißer (Parser-/Quellenfehler): Stand unverändert lassen
    new = {
        "isin": isin,
        "latest": point(newest, price, yld),
        "first": point(days[0], price, yld),
        "high": point(max(days, key=lambda d: price[d]), price, yld),
        "low": point(min(days, key=lambda d: price[d]), price, yld),
        "weeklyFrom": start,
        "weekly": weekly_points(price, yld, start),
    }
    # der jüngste Tag ist immer der letzte Chart-Punkt (weekly_points nimmt je Woche
    # den letzten vorhandenen Tag, das ist bereits newest)
    changed = new != {k: b.get(k) for k in new}
    b.update(new)
    if changed:
        print(f"{key}: {new['latest']['price']} % (Rendite {new['latest']['yield']} %, Stand {newest}), "
              f"{len(new['weekly'])} Wochenpunkte ab {start}; Historie seit {days[0]}.")
    return changed


def update(data: dict) -> bool:
    changed = False
    for key, (isin, start, max_abs) in BONDS.items():
        changed = update_bond(data, key, isin, start, max_abs) or changed
    return changed


def main() -> int:
    try:
        data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    except FileNotFoundError:
        data = {"bonds": {}}
    except Exception as e:
        log_err(f"langlaeufer.json unlesbar – Abbruch, Datei bleibt unangetastet: {e}")
        return 1
    heute = today_iso()
    if os.environ.get("FAST") and str(data.get("checkedAt", ""))[:10] == heute:
        print(f"Quelle heute bereits abgefragt (checkedAt {data['checkedAt']}) – übersprungen (FAST-Lauf).")
        return 0
    try:
        changed = update(data)
    except Exception as e:
        log_err(f"langlaeufer: Bundesbank nicht abrufbar – langlaeufer.json bleibt unverändert: {e}")
        return 1
    data["checkedAt"] = now_iso()
    if changed:
        data["updated"] = heute
        data["updatedAt"] = now_iso()
    write_atomic(DATA_FILE, data)
    print("langlaeufer.json geschrieben." + ("" if changed else " (keine Änderungen – nur checkedAt)"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
