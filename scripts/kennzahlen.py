#!/usr/bin/env python3
"""kennzahlen.py – setzt Kennzahlen beim Deploy aus den Daten in die Seiten ein (seit 30.09.2026).

Läuft im GitHub-Workflow auf dem Veröffentlichungsordner, VOR inline_data.py und dem Minify:

    python3 scripts/kennzahlen.py _site

In den Quell-HTML stehen die Werte als lesbarer Rückfall, markiert mit data-kz:

    <span data-kz="anleihen-kurs">rund 33.000</span>        Anleihen mit aktuellem Kurs (Suche)
    <span data-kz="anleihen-gesamt">über 43.000</span>      alle Anleihen im Register
    <span data-kz="spanne-sl">3,0–5,0&nbsp;%</span>        Renditespanne (10.–90. Perzentil) je Top-10-Datei:
         sl = Staatsanleihen nach Laufzeit, ul = Unternehmensanleihen nach Laufzeit,
         sland = Staatsanleihen nach Ländern, uland = Unternehmensanleihen nach Ländern,
         etf = Anleihen-ETFs (Rendite des Anleihebestands laut Anbieter, etfs.json)

Außerdem wird in Meta-/og-/JSON-LD-Texten die Wendung „Suche über rund NN.000 Anleihen“ auf die aktuelle Zahl gesetzt
(nur diese Wendung – Zahlen wie „Börse Frankfurt rund 27.700 Anleihen“ bleiben unberührt).
Die Quell-HTML-Dateien im Repository bleiben unverändert.
"""
import json
import os
import re
import sys


def lade(site, name):
    for p in (os.path.join(site, name), name):
        if os.path.isfile(p):
            with open(p, encoding="utf-8") as f:
                return json.load(f)
    return None


def tausend(n, art):
    t = int(n // 1000) if art == "über" else int(round(n / 1000))
    return f"{art} {t}.000"


def de(v, nk=1):
    return f"{v:.{nk}f}".replace(".", ",")


def perzentil(r, p):
    i = (len(r) - 1) * p
    u = int(i)
    return r[u] + (r[min(u + 1, len(r) - 1)] - r[u]) * (i - u)


def main():
    site = sys.argv[1] if len(sys.argv) > 1 else "_site"
    werte = {}
    k = lade(site, "anleihen-kurse.json")
    if k and isinstance(k.get("kurse"), dict):
        werte["anleihen-kurs"] = tausend(len(k["kurse"]), "rund")
    i = lade(site, "anleihen-index.json")
    if i and isinstance(i.get("anzahl"), int):
        werte["anleihen-gesamt"] = tausend(i["anzahl"], "über")
    for key, datei in (("sl", "top10-staatsanleihen-laufzeit.json"), ("ul", "top10-unternehmensanleihen-laufzeit.json"),
                       ("sland", "top10-staatsanleihen-laender.json"), ("uland", "top10-unternehmensanleihen-laender.json")):
        d = lade(site, datei)
        if not d:
            continue
        r = sorted(a["rendite"] for g in d.get("gruppen", {}).values() for a in g if isinstance(a.get("rendite"), (int, float)))
        if len(r) >= 3:
            werte["spanne-" + key] = f"{de(perzentil(r, 0.1))}–{de(perzentil(r, 0.9))}&nbsp;%"
    e = lade(site, "etfs.json")   # Rendite des Anleihebestands je ETF (Feld y, laut Anbieter) – seit 30.09.2026
    if e:
        r = sorted(x["y"] for g in e.get("gruppen", {}).values() for x in g if isinstance(x.get("y"), (int, float)))
        if len(r) >= 3:
            werte["spanne-etf"] = f"{de(perzentil(r, 0.1))}–{de(perzentil(r, 0.9))}&nbsp;%"
    print("Kennzahlen:", werte)

    span_re = re.compile(r'(<span data-kz="([a-z-]+)">)([^<]*)(</span>)')
    # nur die feste Wendung „Suche über rund NN.000 Anleihen“ – andere Zahlen (z. B. je Börse) bleiben unberührt
    meta_re = re.compile(r'Suche über rund \d{1,3}\.\d{3} Anleihen')
    for fname in sorted(os.listdir(site)):
        if not fname.endswith(".html"):
            continue
        path = os.path.join(site, fname)
        html = open(path, encoding="utf-8").read()
        neu = span_re.sub(lambda m: m.group(1) + werte.get(m.group(2), m.group(3)) + m.group(4), html)
        if "anleihen-kurs" in werte:
            neu = meta_re.sub("Suche über " + werte["anleihen-kurs"] + " Anleihen", neu)
        if neu != html:
            with open(path, "w", encoding="utf-8") as f:
                f.write(neu)
            print(f"{fname}: Kennzahlen gesetzt")


if __name__ == "__main__":
    main()
