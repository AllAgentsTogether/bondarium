#!/usr/bin/env python3
"""pruefen.py – Qualitätsprüfung des Veröffentlichungsordners vor dem Upload (seit 30.09.2026).

    python3 scripts/pruefen.py _site

Bricht mit Fehler ab (Deploy wird rot, nichts geht live) bei:
  - internen Links auf Seiten, die es nicht gibt
  - Resten des alten Namens (METALCONCRETE / metalconcrete.de) im ausgelieferten Text
Warnt (Deploy läuft weiter) bei:
  - Platzhaltern wie [VORNAME NACHNAME] oder [E-MAIL-ADRESSE] (Impressum noch nicht befüllt)
  - Anker-Links (#…) auf Ziele, die es auf der Zielseite nicht gibt
"""
import os
import re
import sys

site = sys.argv[1] if len(sys.argv) > 1 else "_site"
seiten = {f for f in os.listdir(site) if f.endswith(".html")}
ids = {}
fehler, warnungen = [], []
HREF = re.compile(r'href="(?!https?:|mailto:|tel:|data:|javascript:|#)/?([^"#?]+\.html)?(?:\?[^"#]*)?(?:#([^"]+))?"')
PLATZ = re.compile(r'\[(?:VORNAME|NACHNAME|STRASSE|PLZ|E-MAIL|TELEFON)[^\]]*\]')

for f in seiten:
    html = open(os.path.join(site, f), encoding="utf-8").read()
    ids[f] = set(re.findall(r'\sid="([^"]+)"', html))

for f in sorted(seiten):
    html = open(os.path.join(site, f), encoding="utf-8").read()
    ohne_skript = re.sub(r"<script\b[^>]*>.*?</script>", "", html, flags=re.S)
    for ziel, anker in HREF.findall(ohne_skript):
        if ziel and ziel not in seiten:
            fehler.append(f"{f}: Link auf fehlende Seite {ziel}")
        elif anker and "$" not in anker and anker not in ids.get(ziel or f, set()):
            warnungen.append(f"{f}: Anker #{anker} fehlt auf {ziel or f}")
    if re.search(r"METALCONCRETE|metalconcrete\.de", ohne_skript, re.I):
        fehler.append(f"{f}: alter Name METALCONCRETE im Text")
    for p in sorted(set(PLATZ.findall(ohne_skript))):
        warnungen.append(f"{f}: Platzhalter {p}")

for w in warnungen:
    print(f"::warning::{w}")
for e in fehler:
    print(f"::error::{e}")
print(f"{len(seiten)} Seiten geprüft – {len(fehler)} Fehler, {len(warnungen)} Warnungen")
sys.exit(1 if fehler else 0)
