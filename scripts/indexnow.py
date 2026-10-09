#!/usr/bin/env python3
"""indexnow.py – meldet neue und geänderte Seiten nach dem Upload an IndexNow (seit 30.09.2026).

    python3 scripts/indexnow.py alt-sitemap.xml _site

IndexNow (indexnow.org) ist die Meldestelle von Bing, Yandex, Seznam und Naver: Statt auf den nächsten Besuch des
Crawlers zu warten, erfährt die Suchmaschine sofort, welche Adressen sich geändert haben. Bing ist zugleich der
Suchindex hinter ChatGPT-Suche und Copilot – frische Zahlen kommen so schneller in KI-Antworten an. Google nimmt
an IndexNow nicht teil und liest weiter die Sitemap.

Gemeldet werden seit 09.10.2026 nur Adressen, die neu in der Sitemap stehen oder deren <lastmod> sich geändert hat –
Vergleich der sitemap.xml, die vor dem Upload auf dem Server lag (der Workflow holt sie wie das Manifest als
alt-sitemap.xml), mit der neuen aus dem Bau. Vorher zählte jede HTML-Datei mit neuem SHA-1: Die rund 79 Server-Steckbriefe
betten die Wechselkurse ein und änderten sich deshalb täglich, ihr lastmod aber nicht – gemeldet wurden ~97 Adressen am
Tag, die die Sitemap als unverändert auswies (Technik-Test 08.10.2026, T-75). Fehlt die alte Sitemap oder ist sie leer,
wird nichts gemeldet (sonst gälte jede Adresse als neu). Übertragen werden ausschließlich öffentliche Adressen der eigenen
Seite und der Schlüssel aus indexnow-key.txt – dieselbe Datei liegt öffentlich auf dem Server und beweist der
Suchmaschine, dass die Meldung vom Betreiber kommt.

Ein Fehler hier ist nie schlimm: Das Skript endet immer mit 0, der Deploy ist da schon fertig.
"""
import json
import os
import re
import sys
import urllib.request

HOST = "www.bondarium.de"
BASE = f"https://{HOST}/"
ZIEL = "https://api.indexnow.org/indexnow"
DATEI = "indexnow-key.txt"


def eintraege(pfad):
    """{Adresse: lastmod} aus einer sitemap.xml; {} wenn sie fehlt oder unlesbar ist."""
    try:
        text = open(pfad, encoding="utf-8").read()
    except (OSError, UnicodeDecodeError):
        return {}
    m = {}
    for block in re.findall(r"<url>(.*?)</url>", text, re.S):
        loc = re.search(r"<loc>\s*([^<]+?)\s*</loc>", block)
        if loc:
            lm = re.search(r"<lastmod>\s*([^<]+?)\s*</lastmod>", block)
            m[loc.group(1).replace("&amp;", "&")] = lm.group(1) if lm else ""
    return m


def main():
    if len(sys.argv) < 3:
        print("Aufruf: indexnow.py alt-sitemap.xml _site")
        return
    alt, site = eintraege(sys.argv[1]), sys.argv[2]
    try:
        key = open(os.path.join(site, DATEI), encoding="utf-8").read().strip()
    except OSError as e:
        print(f"::warning::IndexNow: {e} – nichts gemeldet")
        return
    if not re.fullmatch(r"[0-9a-f]{32}", key):
        print(f"::warning::IndexNow: {DATEI} enthält keinen gültigen Schlüssel – nichts gemeldet")
        return
    neu = eintraege(os.path.join(site, "sitemap.xml"))
    if not neu:
        print("::warning::IndexNow: sitemap.xml im Bau fehlt oder ist leer – nichts gemeldet")
        return
    if not alt:
        print("::warning::IndexNow: alte sitemap.xml vom Server fehlt oder ist leer – nichts gemeldet (sonst gälte jede Adresse als neu)")
        return
    adressen = sorted(u for u, lm in neu.items() if u.startswith(BASE) and alt.get(u) != lm)
    neue = sum(1 for u in adressen if u not in alt)
    if not adressen:
        print("IndexNow: keine neue Adresse und kein geändertes lastmod – nichts zu melden")
        return
    print(f"IndexNow: {neue} neue Adressen, {len(adressen) - neue} mit geändertem lastmod")
    daten = json.dumps({"host": HOST, "key": key, "keyLocation": BASE + DATEI, "urlList": adressen}).encode("utf-8")
    req = urllib.request.Request(ZIEL, data=daten, method="POST",
                                 headers={"Content-Type": "application/json; charset=utf-8", "User-Agent": "bondarium-deploy"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            print(f"IndexNow: {len(adressen)} Adressen gemeldet (HTTP {r.status})")
    except Exception as e:   # 4xx/5xx oder Netzfehler: nur melden, nie den Lauf rot machen
        print(f"::warning::IndexNow: Meldung fehlgeschlagen ({e}) – {len(adressen)} Adressen nicht gemeldet")


if __name__ == "__main__":
    main()
