#!/usr/bin/env python3
"""kurse_jahre.py – schreibt kurse/jahre.json: welche Kursverlauf-Dateien es gibt.

Aufruf im Projektordner (nach jedem Lauf, der kurse/ ändert – update_kurse.py, import_kurshistorie.py):

    python3 scripts/kurse_jahre.py           # schreibt kurse/jahre.json (nur bei Änderung)
    python3 scripts/kurse_jahre.py --check   # meldet nur, ob die Datei aktuell ist (Exit 1 = veraltet)

Hintergrund (30.09.2026): site.js MC.verlauf fragte früher blind jedes Jahr ab 2021 ab
(kurse/<Jahr>/<teil>.json) – viele Teile existieren in frühen Jahren nicht, das gab 404-Anfragen
(langlaeufer.html: 12 × 404). Jetzt liest MC.verlauf zuerst diese kleine Liste und lädt nur Dateien,
die es gibt. Fehlt die Liste (z. B. lokal nicht erzeugt), fällt site.js auf die alte Jahresschleife zurück.

Format (deterministisch, ohne Zeitstempel – ändert sich nur, wenn sich die Dateien ändern):
    {"jahre": {"2021": "0003…", …},   # je Jahr die vorhandenen Teile als Folge zweistelliger Hex-Kürzel (teil() in site.js)
     "bund": ["DE0001…", …]}          # ISINs mit Bundesbank-Verlauf in kurse/bund/<ISIN>.json
"""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KURSE = os.path.join(ROOT, "kurse")
ZIEL = os.path.join(KURSE, "jahre.json")


def erzeugen():
    jahre = {}
    for name in sorted(os.listdir(KURSE)):
        pfad = os.path.join(KURSE, name)
        if re.fullmatch(r"\d{4}", name) and os.path.isdir(pfad):
            teile = sorted(f[:2] for f in os.listdir(pfad) if re.fullmatch(r"[0-9a-f]{2}\.json", f))
            if teile:
                jahre[name] = "".join(teile)
    bund_dir = os.path.join(KURSE, "bund")
    bund = sorted(f[:-5] for f in os.listdir(bund_dir) if f.endswith(".json")) if os.path.isdir(bund_dir) else []
    return json.dumps({"jahre": jahre, "bund": bund}, ensure_ascii=False, separators=(",", ":")) + "\n"


def main():
    neu = erzeugen()
    alt = open(ZIEL, encoding="utf-8").read() if os.path.exists(ZIEL) else ""
    if "--check" in sys.argv:
        print("kurse/jahre.json aktuell" if neu == alt else "kurse/jahre.json veraltet – python3 scripts/kurse_jahre.py ausführen")
        return 0 if neu == alt else 1
    if neu != alt:
        with open(ZIEL, "w", encoding="utf-8") as f:
            f.write(neu)
        d = json.loads(neu)
        print(f"kurse/jahre.json geschrieben: {', '.join(f'{j} ({len(t) // 2} Teile)' for j, t in d['jahre'].items())}, {len(d['bund'])} Bund-Verläufe")
    else:
        print("kurse/jahre.json unverändert")
    return 0


if __name__ == "__main__":
    sys.exit(main())
