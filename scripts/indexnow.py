#!/usr/bin/env python3
"""indexnow.py – meldet geänderte Seiten nach dem Upload an IndexNow (seit 30.09.2026).

    python3 scripts/indexnow.py alt.manifest neu.manifest _site

IndexNow (indexnow.org) ist die Meldestelle von Bing, Yandex, Seznam und Naver: Statt auf den nächsten Besuch des
Crawlers zu warten, erfährt die Suchmaschine sofort, welche Adressen sich geändert haben. Bing ist zugleich der
Suchindex hinter ChatGPT-Suche und Copilot – frische Zahlen kommen so schneller in KI-Antworten an. Google nimmt
an IndexNow nicht teil und liest weiter die Sitemap.

Gemeldet werden nur Seiten aus der Sitemap, deren HTML sich seit dem letzten Upload geändert hat (Vergleich der
beiden Manifest-Dateien von scripts/deploy_manifest.py). Übertragen werden ausschließlich öffentliche Adressen der
eigenen Seite und der Schlüssel aus indexnow-key.txt – dieselbe Datei liegt öffentlich auf dem Server und beweist
der Suchmaschine, dass die Meldung vom Betreiber kommt.

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


def lies(pfad):
    m = {}
    if os.path.isfile(pfad):
        for z in open(pfad, encoding="utf-8"):
            z = z.rstrip("\n")
            if len(z) > 42:
                m[z[42:]] = z[:40]
    return m


def main():
    if len(sys.argv) < 4:
        print("Aufruf: indexnow.py alt.manifest neu.manifest _site")
        return
    alt, neu, site = lies(sys.argv[1]), lies(sys.argv[2]), sys.argv[3]
    try:
        key = open(os.path.join(site, DATEI), encoding="utf-8").read().strip()
        sitemap = set(re.findall(r"<loc>([^<]+)</loc>", open(os.path.join(site, "sitemap.xml"), encoding="utf-8").read()))
    except OSError as e:
        print(f"::warning::IndexNow: {e} – nichts gemeldet")
        return
    if not re.fullmatch(r"[0-9a-f]{32}", key):
        print(f"::warning::IndexNow: {DATEI} enthält keinen gültigen Schlüssel – nichts gemeldet")
        return
    adressen = []
    for pfad, summe in sorted(neu.items()):
        if "/" in pfad or not pfad.endswith(".html") or alt.get(pfad) == summe:
            continue
        u = BASE + ("" if pfad == "index.html" else pfad)
        if u in sitemap:
            adressen.append(u)
    if not adressen:
        print("IndexNow: keine geänderte Seite – nichts zu melden")
        return
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
