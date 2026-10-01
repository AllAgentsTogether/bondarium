#!/usr/bin/env python3
"""update_wechselkurse.py – Euro-Referenzkurse der EZB (seit 01.10.2026).

„Mein Depot“ (konto.html) nimmt auch Anleihen in fremder Währung auf und rechnet Nennwert, Zinsen und Rückzahlung
in Euro um. Dafür schreibt dieses Skript wechselkurse.json; die Seite liest die Datei und nimmt den Kurs als fest an
(mit Sternchen und Hinweis auf das Wechselkursrisiko).

    python3 scripts/update_wechselkurse.py

Quelle: Europäische Zentralbank, Euro-Referenzkurse (eurofxref-daily.xml) – an jedem TARGET-Arbeitstag gegen 16 Uhr
für rund 30 Währungen, Angabe als „1 Euro = x Einheiten der Währung“.
Ausgabe wechselkurse.json:
    {"updated", "updatedAt", "stand" (Tag der Kurse), "quelle", "kurse": {"USD": 1.1355, …}}
Scheitert der Abruf oder sieht die Datei unplausibel aus, bleibt die bisherige Datei unverändert
(Exit-Code 1, der Workflow läuft weiter).
"""
import datetime
import json
import os
import re
import sys
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
URL = "https://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml"


def main():
    try:
        req = urllib.request.Request(URL, headers={"User-Agent": "bondarium-datenabruf"})
        with urllib.request.urlopen(req, timeout=60) as r:
            text = r.read().decode("utf-8")
    except Exception as e:
        print(f"::warning::Abruf der EZB-Referenzkurse fehlgeschlagen ({e}) – wechselkurse.json bleibt unverändert")
        return 1
    tag = re.search(r"<Cube\s+time=['\"](\d{4}-\d{2}-\d{2})['\"]", text)
    kurse = {}
    for cur, rate in re.findall(r"<Cube\s+currency=['\"]([A-Z]{3})['\"]\s+rate=['\"]([0-9.]+)['\"]", text):
        try:
            v = float(rate)
        except ValueError:
            continue
        if v > 0:
            kurse[cur] = v
    # Plausibilität: Tag vorhanden, genug Währungen, Dollar in einer glaubhaften Spanne
    if not tag or len(kurse) < 20 or not 0.5 < kurse.get("USD", 0) < 2:
        print("::warning::EZB-Referenzkurse unerwartet (Tag, Anzahl oder Dollarkurs) – wechselkurse.json bleibt unverändert")
        return 1
    heute = datetime.date.today().isoformat()
    neu = {"updated": heute, "updatedAt": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
           "stand": tag.group(1), "quelle": "Europäische Zentralbank, Euro-Referenzkurse",
           "kurse": dict(sorted(kurse.items()))}
    with open(os.path.join(ROOT, "wechselkurse.json"), "w", encoding="utf-8") as f:
        json.dump(neu, f, ensure_ascii=False, separators=(",", ":"))
    print(f"wechselkurse.json: {len(kurse)} Währungen, Stand {tag.group(1)}, 1 € = {kurse['USD']} USD")
    return 0


if __name__ == "__main__":
    sys.exit(main())
