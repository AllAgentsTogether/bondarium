#!/usr/bin/env python3
"""kennzahlen.py – setzt Kennzahlen beim Deploy aus den Daten in die Seiten ein (seit 30.09.2026).

Läuft im GitHub-Workflow auf dem Veröffentlichungsordner, VOR inline_data.py und dem Minify:

    python3 scripts/kennzahlen.py _site

In den Quell-HTML stehen die Werte als lesbarer Rückfall, markiert mit data-kz:

    <span data-kz="anleihen-kurs">rund 33.000</span>        Anleihen mit aktuellem Kurs (Suche)
    <span data-kz="anleihen-gesamt">über 43.000</span>      alle Anleihen im Register
    <span data-kz="spanne-sl">3,0–5,0&nbsp;%</span>        Renditespanne (10.–90. Perzentil) je Top-10-Datei:
         sl = Staatsanleihen nach Laufzeit, ul = Unternehmensanleihen nach Laufzeit,
         sland = Staatsanleihen nach Ländern, uland = Unternehmensanleihen nach Ländern
    <span data-kz="etf-anzahl">908</span>                   Anleihen-ETFs im Register (etf-index.json, seit 30.09.2026 –
         vorher „spanne-etf“ aus handgepflegten Renditen laut Anbieter; ETFs werden nicht mehr von Hand gepflegt)
    <span data-kz="etf-top-anzahl">70</span>, „etf-kosten-spanne“, „etf-kosten-guenstig“, „etf-stand“
         Kosten der ETFs auf der Seite anleihen-etf.html (top10-anleihen-etfs.json): Anzahl, niedrigste bis höchste
         laufende Kosten, Anzahl mit höchstens 0,2 % und das Datum der ETF-Liste – für etf-oder-anleihe.html
    <span data-kz="broker-spanne">0 bis rund 18&nbsp;€</span>, „broker-stand“, „broker-anzahl“
         Broker-Vergleich (broker.json, seit 01.10.2026): niedrigste bis höchste Kosten für einen Kauf über den
         Standardbetrag (5.000 €), je Anbieter der günstigste Handelsweg – gerechnet mit derselben Funktion wie die
         Seite (scripts/statische_tabellen.py) –, der Tag der Prüfung und die Zahl der Anbieter; für
         steuern-handelskosten.html, erste-anleihe.html, kaufen.html. Dazu wird die Wendung „NN Anbieter/Broker im Vergleich“
         in Titeln, Beschreibungen und Knöpfen auf die Zahl der Anbieter gesetzt.

Außerdem wird in Meta-/og-/JSON-LD-Texten die Wendung „Suche über rund NN.000 Anleihen“ auf die aktuelle Zahl gesetzt
(nur diese Wendung – Zahlen wie „Börse Frankfurt rund 27.700 Anleihen“ bleiben unberührt).
Seit 02.10.2026 ebenso, in Kopf und Text aller Seiten:
    „NN Anleihen-ETFs“ (ein- oder zweistellig)  → Kennzahl etf-top-anzahl (die ETFs auf anleihen-etf.html); dreistellige
                                                 Zahlen meinen das Register (data-kz „etf-anzahl“) und bleiben unberührt
    „NN Themen und das Glossar“ (wissen.html)    → Zahl der Akademie-Themen im Menü (AKADEMIE in scripts/nav.py, ohne Glossar)
und auf anleihen-suche.html die Zeile <p id="datastand">Daten-Stand: wird geladen</p> mit demselben Text, den das
Seitenskript setzt (Register- und Kursstand aus suchindex.json – derselbe Datenlauf wie „rund 33.000“ auf der Seite).
Den „Daten-Stand“ der Seiten mit Tabellen (anleihen-etf, anleihen-kupon, Top-10-Seiten) schreibt statische_tabellen.py –
nur zusammen mit den Zeilen, zu denen er gehört.
Jede Ergänzung ist mit try/except abgesichert: Dieser Schritt läuft im Workflow ohne continue-on-error; geht etwas schief,
gibt es eine Warnung, und der Rückfall-Text der Seite bleibt stehen.
Die Quell-HTML-Dateien im Repository bleiben unverändert.
"""
import html as htmllib
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


def iso_de(iso):
    """„2026-09-30“ → „30.09.2026“ (wie MC.datum); kein gültiges Datum → None"""
    return ".".join(reversed(iso.split("-"))) if re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(iso or "")) else None


def datenstand_suche(site):
    """„Daten-Stand“ der Anleihen-Suche im Wortlaut des Seitenskripts (anleihen-suche.html, T.stand):
    „Daten-Stand: <Register> (ESMA-Register) · Kurse: <Kurse> (Deutsche Börse, Bundesbank)“ – aus suchindex.json
    (stand, kstand), Rückfall wie die Seite auf anleihen-index.json und anleihen-kurse.json. Ohne beide Daten: None."""
    try:
        s = lade(site, "suchindex.json")
    except Exception:
        s = None
    if not isinstance(s, dict):
        ix, ku = lade(site, "anleihen-index.json") or {}, lade(site, "anleihen-kurse.json") or {}
        s = {"stand": ix.get("stand"), "kstand": ku.get("stand")}
    d, k = iso_de(s.get("stand")), iso_de(s.get("kstand"))
    if not (d and k):
        return None
    return f"Daten-Stand: {d} (ESMA-Register) · Kurse: {k} (Deutsche Börse, Bundesbank)"


def akademie_themen():
    """Zahl der Themen im Akademie-Menü (scripts/nav.py, AKADEMIE: drei Spalten, ohne das Glossar) – gelesen, nicht ausgeführt."""
    import ast
    pfad = os.path.join(os.path.dirname(os.path.abspath(__file__)), "nav.py")
    with open(pfad, encoding="utf-8") as f:
        baum = ast.parse(f.read())
    for knoten in baum.body:
        if isinstance(knoten, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "AKADEMIE" for t in knoten.targets):
            akademie = ast.literal_eval(knoten.value)
            return sum(len(spalte[2]) for spalte in akademie[2])
    return None


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
    e = lade(site, "etf-index.json")   # Register der Anleihen-ETFs (scripts/update_etf_index.py)
    if e and isinstance(e.get("anzahl"), int) and e["anzahl"] > 0:
        werte["etf-anzahl"] = f"{e['anzahl']:,}".replace(",", ".")
    t = lade(site, "top10-anleihen-etfs.json")   # die ETFs der Seite anleihen-etf.html
    if t:
        k = sorted(x["kosten"] for g in (t.get("gruppen") or {}).values() for x in g.get("etfs", []) if isinstance(x.get("kosten"), (int, float)))
        if len(k) >= 3:
            werte["etf-top-anzahl"] = str(len(k))
            werte["etf-kosten-spanne"] = f"{de(k[0], 2)} bis {de(k[-1], 2)}&nbsp;%"
            werte["etf-kosten-guenstig"] = str(sum(1 for x in k if x <= 0.2 + 1e-9))
            if re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(t.get("stand") or "")):
                werte["etf-stand"] = ".".join(reversed(t["stand"].split("-")))
    b = lade(site, "broker.json")   # Broker-Vergleich: Kosten je Anbieter rechnet dieselbe Funktion wie die Seite
    if b:
        try:
            from statische_tabellen import b_guenstigster
            if b.get("anbieter"):
                werte["broker-anzahl"] = str(len(b["anbieter"]))
            betrag = b.get("standard") or 5000
            k = sorted(b_guenstigster(x, betrag)["v"] for x in b.get("anbieter", []) if x.get("wege"))
            if len(k) >= 3:
                glatt = lambda v: str(int(v)) if float(v).is_integer() else de(v, 2)
                werte["broker-spanne"] = f"{glatt(k[0])} bis rund {int(k[-1] + 0.5)}&nbsp;€"
            if re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(b.get("stand") or "")):
                werte["broker-stand"] = ".".join(reversed(b["stand"].split("-")))
        except Exception as e:   # Rechnung nicht möglich: der Rückfall-Text der Seiten bleibt stehen
            print(f"::warning::kennzahlen.py: Broker-Kennzahlen nicht gesetzt ({type(e).__name__}: {e})")
    try:   # Zahl der Akademie-Themen für „NN Themen und das Glossar“ (wissen.html)
        n = akademie_themen()
        if n:
            werte["akademie-themen"] = str(n)
    except Exception as e:
        print(f"::warning::kennzahlen.py: Zahl der Akademie-Themen nicht gesetzt ({type(e).__name__}: {e})")
    datenstand = {}
    try:   # „Daten-Stand“ der Anleihen-Suche (sonst „wird geladen“ bis zum Skript)
        t = datenstand_suche(site)
        if t:
            datenstand["anleihen-suche.html"] = t
    except Exception as e:
        print(f"::warning::kennzahlen.py: Daten-Stand der Anleihen-Suche nicht gesetzt ({type(e).__name__}: {e})")
    print("Kennzahlen:", werte, datenstand)

    span_re = re.compile(r'(<span data-kz="([a-z-]+)">)([^<]*)(</span>)')
    # nur die feste Wendung „Suche über rund NN.000 Anleihen“ – andere Zahlen (z. B. je Börse) bleiben unberührt
    meta_re = re.compile(r'Suche über rund \d{1,3}\.\d{3} Anleihen')
    # „19 Anbieter im Vergleich“ / „19 Broker im Vergleich“ (Titel, Beschreibungen, Knöpfe) – Zahl aus broker.json
    broker_re = re.compile(r'\b\d+( (?:Anbieter|Broker) im Vergleich)')
    # „70 Anleihen-ETFs“ (anleihen.html, Beschreibungen) – nur ein- und zweistellig: dreistellige Zahlen meinen das Register
    etf_re = re.compile(r'(?<![\d.,])\b\d{1,2}( Anleihen-ETFs)\b')
    # „19 Themen und das Glossar“ (wissen.html, Beschreibungen) – Zahl der Akademie-Themen aus nav.py
    themen_re = re.compile(r'\b\d+( Themen und das Glossar)\b')
    stand_re = re.compile(r'(<p id="datastand">)Daten-Stand: wird geladen(</p>)')
    for fname in sorted(os.listdir(site)):
        if not fname.endswith(".html"):
            continue
        path = os.path.join(site, fname)
        html = open(path, encoding="utf-8").read()
        neu = span_re.sub(lambda m: m.group(1) + werte.get(m.group(2), m.group(3)) + m.group(4), html)
        if "anleihen-kurs" in werte:
            neu = meta_re.sub("Suche über " + werte["anleihen-kurs"] + " Anleihen", neu)
        if "broker-anzahl" in werte:
            neu = broker_re.sub(lambda m: werte["broker-anzahl"] + m.group(1), neu)
        try:
            if "etf-top-anzahl" in werte:
                neu = etf_re.sub(lambda m: werte["etf-top-anzahl"] + m.group(1), neu)
            if "akademie-themen" in werte:
                neu = themen_re.sub(lambda m: werte["akademie-themen"] + m.group(1), neu)
            if fname in datenstand:
                neu = stand_re.sub(lambda m: m.group(1) + htmllib.escape(datenstand[fname], quote=False) + m.group(2), neu, count=1)
        except Exception as e:   # Rückfall-Text der Seite bleibt
            print(f"::warning::kennzahlen.py: {fname}: Zahlen im Kopf oder Daten-Stand nicht gesetzt ({type(e).__name__}: {e})")
        if neu != html:
            with open(path, "w", encoding="utf-8") as f:
                f.write(neu)
            print(f"{fname}: Kennzahlen gesetzt")


if __name__ == "__main__":
    main()
