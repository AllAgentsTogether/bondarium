#!/usr/bin/env python3
"""inline_data.py – bettet die Daten-JSONs beim Deploy in die HTML-Seiten ein.

Läuft im GitHub-Workflow auf dem Veröffentlichungsordner (_site), NACH dem
Kopieren der Dateien und VOR dem Minify:

    python3 scripts/inline_data.py _site

Für jede Seite werden alle `MC.load("<datei>.json")`-Aufrufe gesucht und die
jeweilige JSON-Datei kompakt als

    <script type="application/json" data-mc="<datei>.json">…</script>

vor dem site.js-Tag eingefügt. site.js (MC.load) nimmt eingebettete Daten
bevorzugt und lädt nur ohne Einbettung per fetch (lokale Entwicklung).

Effekt: kein zusätzlicher Daten-Request, kein zweiter Render („Flash“ alter
Fallback-Werte), keine Layout-Sprünge durch nachgeladene Charts – und die
Zahlen im ausgelieferten HTML sind so frisch wie die JSONs des Laufs.
Die Quell-HTML-Dateien im Repository bleiben unverändert.
"""
import json
import os
import re
import sys

LOAD_RE = re.compile(r'MC\.load\("([a-z0-9_-]+\.json)"\)')
# Seit 30.09.2026 zusätzlich: Dateinamen als String-Literal (z. B. ["sl", "top10-….json"] oder const TOP10 = "….json"),
# die per Variable an MC.load gehen. Nur Dateien im Stammordner und bis MAX_KB – große Such-/Kursdateien bleiben fetch.
LIT_RE = re.compile(r'"([a-z0-9_-]+\.json)"')
MAX_KB = 200
ISIN_RE = re.compile(r'\b([A-Z]{2}[A-Z0-9]{9}[0-9])\b')


def kuerzen(data, html):
    """kurse-auswahl.json u. ä.: nur die ISINs einbetten, die auf der Seite vorkommen (Startseite: 6 statt 324).
    Seit 09.10.2026 ebenso anleihen-auswahl.json (Feld „a“, je ISIN Kurzname und Bonität): langlaeufer.html nutzt 7 von 310
    (Technik-Test T-61). Automatische Listen (top10-*.json) bringen Kurzname und Bonität in ihren Zeilen selbst mit."""
    for feld in ("kurse", "a"):
        if isinstance(data, dict) and isinstance(data.get(feld), dict):
            isins = set(ISIN_RE.findall(html))
            if isins:
                data = dict(data)
                data[feld] = {k: v for k, v in data[feld].items() if k in isins}
    return data
ANCHOR_RE = re.compile(r'<script src="site\.js[^"]*"></script>')


def embed(site, fname):
    path = os.path.join(site, fname)
    html = open(path, encoding="utf-8").read()
    names = []
    for n in LOAD_RE.findall(html):
        if n not in names:
            names.append(n)
    if "MC.load(" in html:
        for n in LIT_RE.findall(html):
            p = os.path.join(site, n)
            if n not in names and os.path.isfile(p) and os.path.getsize(p) <= MAX_KB * 1024:
                names.append(n)
    if not names:
        return None
    m = ANCHOR_RE.search(html)
    if not m:
        raise SystemExit(f"{fname}: site.js-Tag nicht gefunden – Einbettung abgebrochen")
    blocks, total = [], 0
    for n in names:
        marker = f'data-mc="{n}"'
        if marker in html:
            continue  # bereits eingebettet (Idempotenz)
        jpath = os.path.join(site, n)
        try:
            with open(jpath, encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:  # defekte/fehlende Datei: Seite lädt dann per fetch
            print(f"::warning::{fname}: {n} nicht einbettbar ({e}) – Seite nutzt fetch")
            continue
        data = kuerzen(data, html)
        compact = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
        # "</" darf in einem Script-Block nicht vorkommen (würde ihn beenden)
        compact = compact.replace("</", "<\\/")
        blocks.append(f'<script type="application/json" {marker}>{compact}</script>')
        total += len(compact)
    if not blocks:
        return (names, 0)
    html = html[: m.start()] + "\n".join(blocks) + "\n" + html[m.start():]
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    return (names, total)


def main():
    site = sys.argv[1] if len(sys.argv) > 1 else "_site"
    if not os.path.isdir(site):
        raise SystemExit(f"Ordner nicht gefunden: {site}")
    for fname in sorted(os.listdir(site)):
        if not fname.endswith(".html"):
            continue
        res = embed(site, fname)
        if res:
            names, total = res
            print(f"{fname}: {', '.join(names)} eingebettet ({total // 1024} KB)")


if __name__ == "__main__":
    main()
