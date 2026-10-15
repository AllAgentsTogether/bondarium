#!/usr/bin/env python3
"""update_ezb.py – EZB-Einlagesatz (Deposit Facility Rate) aus dem EZB Data Portal (seit 30.09.2026).

Vorher stand der Zinspfad von Hand in zinsniveau.html und musste nach jeder EZB-Sitzung
nachgetragen werden. Jetzt schreibt dieses Skript ezb.json; zinsniveau.html und markttechnik.html
lesen die Datei (MC.load) und zeigen den aktuellen Satz samt Stand.

    python3 scripts/update_ezb.py

Quelle: EZB Data Portal, Reihe FM.B.U2.EUR.4F.KR.DFR.LEV (Einlagesatz, gilt ab dem angegebenen Tag).
Ausgabe ezb.json:
    {"updated", "updatedAt", "stand", "quelle", "reihe", "aktuell": [gilt_ab, satz], "stufen": [[gilt_ab, satz], …]}
„stand“ ist der Tag des Abrufs (die Reihe enthält nur die Tage, an denen sich der Satz ändert – einen jüngeren
Datenstand gibt es nicht); die Seiten nennen ihn „abgerufen am“.
Scheitert der Abruf, bleibt die bisherige Datei unverändert (Exit-Code 1, der Workflow läuft weiter).
Seit 15.10.2026 (Gesamtprüfung D13-01/D13-02): atomar geschrieben (_common.write_atomic), eine unlesbare alte Datei
bricht den Lauf nicht ab, und unplausible Werte (Satz außerhalb SATZ_MIN…SATZ_MAX %, Stufe größer als MAX_STUFE
Punkte) lassen die Datei unverändert.
"""
import csv
import datetime
import io
import json
import os
import sys
import urllib.request
from pathlib import Path

from _common import write_atomic

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REIHE = "FM.B.U2.EUR.4F.KR.DFR.LEV"
URL = ("https://data-api.ecb.europa.eu/service/data/FM/B.U2.EUR.4F.KR.DFR.LEV"
       "?format=csvdata&detail=dataonly&startPeriod=2015-01-01")
AB = "2019-01-01"   # Schaubild auf zinsniveau.html beginnt 2019
SATZ_MIN, SATZ_MAX = -1.0, 10.0   # % – Plausibilität je Wert
MAX_STUFE = 1.0                   # Prozentpunkte – größte Änderung von einer Stufe zur nächsten (seit 2015 höchstens 0,75)


def main():
    try:
        req = urllib.request.Request(URL, headers={"User-Agent": "bondarium-datenabruf"})
        with urllib.request.urlopen(req, timeout=60) as r:
            text = r.read().decode("utf-8")
    except Exception as e:
        print(f"::warning::EZB-Abruf fehlgeschlagen ({e}) – ezb.json bleibt unverändert")
        return 1
    werte = []
    for z in csv.DictReader(io.StringIO(text)):
        try:
            werte.append((z["TIME_PERIOD"], float(z["OBS_VALUE"])))
        except (KeyError, ValueError):
            continue
    werte.sort()
    if len(werte) < 5:
        print("::warning::EZB-Reihe unerwartet kurz – ezb.json bleibt unverändert")
        return 1
    schlecht = [w for w in werte if not SATZ_MIN <= w[1] <= SATZ_MAX]
    sprung = next(((a, b) for a, b in zip(werte, werte[1:]) if abs(b[1] - a[1]) > MAX_STUFE), None)
    if schlecht:
        print(f"::warning::EZB-Reihe unplausibel (Satz außerhalb {SATZ_MIN}…{SATZ_MAX} %: {schlecht[0]}) – ezb.json bleibt unverändert")
        return 1
    if sprung:
        print(f"::warning::EZB-Reihe unplausibel (Stufe größer als {MAX_STUFE} Punkte: {sprung[0]} → {sprung[1]}) – ezb.json bleibt unverändert")
        return 1
    # nur Änderungen (Stufen); Wert, der am 01.01.2019 galt, als Startpunkt
    stufen, letzter = [], None
    vorher = [w for w in werte if w[0] <= AB]
    if vorher:
        stufen.append([AB, vorher[-1][1]])
        letzter = vorher[-1][1]
    for d, v in werte:
        if d > AB and v != letzter:
            stufen.append([d, v])
            letzter = v
    heute = datetime.date.today().isoformat()
    pfad = os.path.join(ROOT, "ezb.json")
    alt = {}
    if os.path.isfile(pfad):
        try:
            with open(pfad, encoding="utf-8") as f:
                alt = json.load(f)
        except (OSError, ValueError) as e:   # kaputte Datei: wird gleich neu geschrieben
            print(f"::warning::ezb.json unlesbar ({e}) – wird neu geschrieben")
            alt = {}
    neu = {"updated": heute, "updatedAt": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
           "stand": heute, "quelle": "Europäische Zentralbank, Data Portal (Einlagesatz)", "reihe": REIHE,
           "aktuell": stufen[-1], "stufen": stufen}
    write_atomic(Path(pfad), neu, indent=None)   # erst in eine temporäre Datei, dann ersetzen – nie halb geschrieben
    geaendert = alt.get("stufen") != stufen if isinstance(alt, dict) else True
    print(f"ezb.json: {len(stufen)} Stufen, aktuell {stufen[-1][1]} % seit {stufen[-1][0]}" + (" (neue Stufe)" if geaendert and alt else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
