#!/usr/bin/env python3
"""pruefen.py – Qualitätsprüfung des Veröffentlichungsordners vor dem Upload (seit 30.09.2026).

    python3 scripts/pruefen.py _site

Bricht mit Fehler ab (Deploy wird rot, nichts geht live) bei:
  - internen Links auf Seiten, die es nicht gibt
  - Resten des alten Namens (METALCONCRETE / metalconcrete.de) im ausgelieferten Text
  - Seiten für Suchmaschinen (ohne „noindex“) ohne <title>, ohne oder mit fremder kanonischer Adresse,
    oder mit unlesbarem JSON-LD – das kostet Auffindbarkeit, ohne dass man es der Seite ansieht
Warnt (Deploy läuft weiter) bei:
  - Platzhaltern wie [VORNAME NACHNAME] oder [E-MAIL-ADRESSE] (Impressum noch nicht befüllt)
  - Anker-Links (#…) auf Ziele, die es auf der Zielseite nicht gibt
  - Angeboten in broker.json, deren „bis“-Datum abgelaufen ist oder in weniger als 14 Tagen abläuft
  - Titeln über 60 Zeichen, Beschreibungen unter 70 oder über 160 Zeichen, fehlender Beschreibung,
    keiner oder mehreren <h1>, doppelt vergebenen Titeln oder Beschreibungen
Anleihen-Tabellen (seit 03.10.2026, Konzept „Einheitliche Anleihen-Angaben“, docs/ANLEIHEN-ANGABEN.md):
  - Fehler, wenn der Katalog in felder.js kein lesbares JSON ist oder eine Anleihen-Tabelle im ausgelieferten HTML ihre Spalten
    nicht in der Reihenfolge der Gesamtliste zeigt oder einen Spaltenkopf anders nennt als der Katalog (Kurzform)
"""
import datetime
import html as htmllib
import json
import os
import re
import sys

site = sys.argv[1] if len(sys.argv) > 1 else "_site"
seiten = {f for f in os.listdir(site) if f.endswith(".html")}
ids = {}
fehler, warnungen = [], []
HREF = re.compile(r'href="(?!https?:|mailto:|tel:|data:|javascript:|#)(/|\./)?([^"#?]+\.html)?(?:\?[^"#]*)?(?:#([^"]+))?"')
PLATZ = re.compile(r'\[(?:VORNAME|NACHNAME|STRASSE|PLZ|E-MAIL|TELEFON)[^\]]*\]')

for f in seiten:
    html = open(os.path.join(site, f), encoding="utf-8").read()
    ids[f] = set(re.findall(r'\sid="([^"]+)"', html))

for f in sorted(seiten):
    html = open(os.path.join(site, f), encoding="utf-8").read()
    ohne_skript = re.sub(r"<script\b[^>]*>.*?</script>", "", html, flags=re.S)
    for wurzel, ziel, anker in HREF.findall(ohne_skript):
        if not ziel and wurzel:   # „/#akademie“ oder „./#akademie“ = Startseite
            ziel = "index.html"
        if ziel and ziel not in seiten:
            fehler.append(f"{f}: Link auf fehlende Seite {ziel}")
        elif anker and "$" not in anker and anker not in ids.get(ziel or f, set()):
            warnungen.append(f"{f}: Anker #{anker} fehlt auf {ziel or f}")
    if re.search(r"METALCONCRETE|metalconcrete\.de", ohne_skript, re.I):
        fehler.append(f"{f}: alter Name METALCONCRETE im Text")
    for p in sorted(set(PLATZ.findall(ohne_skript))):
        warnungen.append(f"{f}: Platzhalter {p}")

# ---------- Auffindbarkeit (seit 30.09.2026): Titel, Beschreibung, kanonische Adresse, H1, strukturierte Daten ----------
BASE = "https://www.bondarium.de/"
titel_von, text_von = {}, {}
for f in sorted(seiten):
    html = open(os.path.join(site, f), encoding="utf-8").read()
    kopf = html.split("</head>")[0]
    if f == "404.html" or re.search(r'<meta name="robots" content="[^"]*noindex', kopf):
        continue
    m = re.search(r"<title>(.*?)</title>", kopf, re.S)
    titel = htmllib.unescape(m.group(1)).strip() if m else ""
    if not titel:
        fehler.append(f"{f}: <title> fehlt")
    else:
        titel_von.setdefault(titel, []).append(f)
        if len(titel) > 60:
            warnungen.append(f"{f}: Titel hat {len(titel)} Zeichen (über 60 wird er im Suchergebnis abgeschnitten)")
    m = re.search(r'<meta name="description" content="([^"]*)"', kopf)
    text = htmllib.unescape(m.group(1)).strip() if m else ""
    if not text:
        warnungen.append(f"{f}: Beschreibung (meta description) fehlt")
    else:
        text_von.setdefault(text, []).append(f)
        if not 70 <= len(text) <= 160:
            warnungen.append(f"{f}: Beschreibung hat {len(text)} Zeichen (gut sind 70 bis 160)")
    m = re.search(r'<link rel="canonical" href="([^"]+)"', kopf)
    eigen = BASE + ("" if f == "index.html" else f)
    if not m:
        fehler.append(f"{f}: kanonische Adresse (link rel=canonical) fehlt")
    elif m.group(1) != eigen:
        fehler.append(f"{f}: kanonische Adresse zeigt auf {m.group(1)} statt auf {eigen}")
    h1 = len(re.findall(r"<h1\b", re.sub(r"<script\b[^>]*>.*?</script>", "", html, flags=re.S)))
    if h1 != 1:
        warnungen.append(f"{f}: {h1} Hauptüberschriften (<h1>) statt einer")
    for roh in re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, re.S):
        try:
            json.loads(roh)
        except ValueError as e:
            fehler.append(f"{f}: JSON-LD unlesbar ({e})")
for art, gruppen in (("Titel", titel_von), ("Beschreibung", text_von)):
    for wert, dateien in gruppen.items():
        if len(dateien) > 1:
            warnungen.append(f"{art} doppelt vergeben ({', '.join(dateien)}): {wert[:60]}")

# Broker-Angebote mit Ablaufdatum (broker.json, Feld „bis“ im Format JJJJ-MM-TT)
bj = os.path.join(site, "broker.json")
if os.path.isfile(bj):
    heute = datetime.date.today()
    for bis in re.findall(r'"bis"\s*:\s*"(\d{4}-\d{2}-\d{2})"', open(bj, encoding="utf-8").read()):
        rest = (datetime.date.fromisoformat(bis) - heute).days
        if rest < 14:
            warnungen.append(f"broker.json: Angebot bis {bis} " + ("abgelaufen – Eintrag pflegen" if rest < 0 else f"läuft in {rest} Tagen ab"))

# Anleihen-Tabellen gegen den Katalog (felder.js): Reihenfolge der Spalten und Kurzform im Kopf. Erkannt wird eine Anleihen-Tabelle an
# ihren Spalten-Kennungen (data-col): mindestens vier aus der Gesamtliste. Die Suche nutzt ältere Kennungen (name, rest, bon, stk, vol).
ALIAS = {"name": "anleihe", "rest": "restlaufzeit", "bon": "bonitaet", "stk": "stueckelung", "vol": "volumen", "faellig": "restlaufzeit", "delta": "seitMerken", "zt": "zinstermin"}
try:
    quelle = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "felder.js"), encoding="utf-8").read()
    KAT = json.loads(re.search(r"/\*KATALOG\*/(.*?)/\*KATALOG-ENDE\*/", quelle, re.S).group(1))
except (OSError, ValueError, AttributeError) as e:
    KAT = None
    fehler.append(f"felder.js: Katalog nicht lesbar ({e})")
if KAT:
    REIHE, F = KAT["reihe"], KAT["felder"]
    for f in sorted(seiten):
        html = open(os.path.join(site, f), encoding="utf-8").read()
        for kopf in re.findall(r"<thead[^>]*>(.*?)</thead>", re.sub(r"<script\b[^>]*>.*?</script>", "", html, flags=re.S), re.S):
            spalten = []
            for col, inhalt in re.findall(r'<th scope="col" data-col="([^"]+)"[^>]*>(.*?)</th>', kopf, re.S):
                knopf = re.search(r'<button[^>]*class="sortbtn"[^>]*>(.*?)</button>', inhalt, re.S)
                text = htmllib.unescape(re.sub(r"<[^>]+>", "", knopf.group(1) if knopf else re.sub(r"<small>.*?</small>", "", inhalt, flags=re.S))).strip()
                spalten.append((ALIAS.get(col, col), text))
            bekannt = [(c, t) for c, t in spalten if c in REIHE]
            if len(bekannt) < 4:
                continue
            pos = [REIHE.index(c) for c, _ in bekannt]
            if pos != sorted(pos):
                fehler.append(f"{f}: Anleihen-Tabelle mit Spalten {', '.join(c for c, _ in bekannt)} – nicht in der Reihenfolge der Gesamtliste (felder.js)")
            for c, t in bekannt:
                soll = F.get(c, {}).get("kurz", "")
                if t and soll and t != soll:
                    fehler.append(f"{f}: Spaltenkopf „{t}“ statt „{soll}“ (Katalog felder.js, Feld {c})")

for w in warnungen:
    print(f"::warning::{w}")
for e in fehler:
    print(f"::error::{e}")
print(f"{len(seiten)} Seiten geprüft – {len(fehler)} Fehler, {len(warnungen)} Warnungen")
sys.exit(1 if fehler else 0)
