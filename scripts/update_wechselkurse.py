#!/usr/bin/env python3
"""update_wechselkurse.py – Euro-Referenzkurse der EZB (seit 01.10.2026).

Die Musterdepots in My Bondarium (konto.html, wechselkurse.php) nehmen auch Anleihen in fremder Währung auf und
rechnen Nennwert, Zinsen und Rückzahlung in Euro um. Dafür schreibt dieses Skript wechselkurse.json; die Seite liest
die Datei und nimmt den Kurs als fest an (mit Sternchen und Hinweis auf das Wechselkursrisiko).

    python3 scripts/update_wechselkurse.py

Quelle: Europäische Zentralbank, Euro-Referenzkurse (eurofxref-daily.xml) – an jedem TARGET-Arbeitstag gegen 16 Uhr
für rund 30 Währungen, Angabe als „1 Euro = x Einheiten der Währung“.
Ausgabe wechselkurse.json:
    {"updated", "updatedAt", "stand" (Tag der Kurse), "quelle", "kurse": {"USD": 1.1355, …}}
Scheitert der Abruf oder sieht die Datei unplausibel aus, bleibt die bisherige Datei unverändert
(Exit-Code 1, der Workflow läuft weiter). Seit 15.10.2026 (Gesamtprüfung D13-01/D13-02): atomar geschrieben, und
unplausibel ist auch ein Kurstag älter als der gespeicherte oder ein Kurs, der mehr als MAX_AENDERUNG (20 %) vom
gespeicherten derselben Währung abweicht.
"""
import datetime
import json
import os
import re
import sys
import urllib.request
from pathlib import Path

from _common import write_atomic

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
URL = "https://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml"
MAX_AENDERUNG = 0.20   # höchstens 20 % Abstand zum gespeicherten Kurs derselben Währung


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
    pfad = Path(ROOT) / "wechselkurse.json"
    try:
        alt = json.loads(pfad.read_text(encoding="utf-8")) if pfad.is_file() else {}
    except (OSError, ValueError) as e:   # kaputte Datei: wird gleich neu geschrieben
        print(f"::warning::wechselkurse.json unlesbar ({e}) – wird neu geschrieben")
        alt = {}
    alt_stand = alt.get("stand") if isinstance(alt, dict) else None
    alt_kurse = alt.get("kurse") if isinstance(alt, dict) and isinstance(alt.get("kurse"), dict) else {}
    if isinstance(alt_stand, str) and tag.group(1) < alt_stand:
        print(f"::warning::EZB-Referenzkurse vom {tag.group(1)} sind älter als die gespeicherten ({alt_stand}) – wechselkurse.json bleibt unverändert")
        return 1
    weit = [f"{c} {alt_kurse[c]} → {v}" for c, v in sorted(kurse.items())
            if isinstance(alt_kurse.get(c), (int, float)) and alt_kurse[c] > 0 and abs(v / alt_kurse[c] - 1) > MAX_AENDERUNG]
    if weit:
        print(f"::warning::EZB-Referenzkurse unplausibel (mehr als {MAX_AENDERUNG:.0%} Abstand zum gespeicherten Kurs: {', '.join(weit[:3])}) – wechselkurse.json bleibt unverändert")
        return 1
    heute = datetime.date.today().isoformat()
    neu = {"updated": heute, "updatedAt": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
           "stand": tag.group(1), "quelle": "Europäische Zentralbank, Euro-Referenzkurse",
           "kurse": dict(sorted(kurse.items()))}
    write_atomic(pfad, neu, indent=None)   # erst in eine temporäre Datei, dann ersetzen – nie halb geschrieben
    print(f"wechselkurse.json: {len(kurse)} Währungen, Stand {tag.group(1)}, 1 € = {kurse['USD']} USD")
    return 0


if __name__ == "__main__":
    sys.exit(main())
