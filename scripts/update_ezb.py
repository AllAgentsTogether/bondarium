#!/usr/bin/env python3
"""update_ezb.py – EZB-Einlagesatz (Deposit Facility Rate) aus dem EZB Data Portal (seit 30.09.2026).

Vorher stand der Zinspfad von Hand in zinsniveau.html und musste nach jeder EZB-Sitzung
nachgetragen werden. Jetzt schreibt dieses Skript ezb.json; zinsniveau.html und markttechnik.html
lesen die Datei (MC.load) und zeigen den aktuellen Satz samt Stand.

    python3 scripts/update_ezb.py

Quelle: EZB Data Portal, Reihe FM.B.U2.EUR.4F.KR.DFR.LEV (Einlagesatz, gilt ab dem angegebenen Tag).
Ausgabe ezb.json:
    {"updated", "updatedAt", "stand", "quelle", "reihe", "aktuell": [gilt_ab, satz], "stufen": [[gilt_ab, satz], …]}
Scheitert der Abruf, bleibt die bisherige Datei unverändert (Exit-Code 1, der Workflow läuft weiter).
"""
import csv
import datetime
import io
import json
import os
import sys
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REIHE = "FM.B.U2.EUR.4F.KR.DFR.LEV"
URL = ("https://data-api.ecb.europa.eu/service/data/FM/B.U2.EUR.4F.KR.DFR.LEV"
       "?format=csvdata&detail=dataonly&startPeriod=2015-01-01")
AB = "2019-01-01"   # Schaubild auf zinsniveau.html beginnt 2019


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
        with open(pfad, encoding="utf-8") as f:
            alt = json.load(f)
    neu = {"updated": heute, "updatedAt": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
           "stand": heute, "quelle": "Europäische Zentralbank, Data Portal (Einlagesatz)", "reihe": REIHE,
           "aktuell": stufen[-1], "stufen": stufen}
    with open(pfad, "w", encoding="utf-8") as f:
        json.dump(neu, f, ensure_ascii=False, separators=(",", ":"))
    geaendert = alt.get("stufen") != stufen
    print(f"ezb.json: {len(stufen)} Stufen, aktuell {stufen[-1][1]} % seit {stufen[-1][0]}" + (" (neue Stufe)" if geaendert and alt else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
