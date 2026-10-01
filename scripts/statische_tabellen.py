#!/usr/bin/env python3
"""statische_tabellen.py – schreibt Tabellen, die sonst erst das Skript im Browser zeichnet, beim Deploy fest ins HTML
(seit 30.09.2026).

Läuft im GitHub-Workflow auf dem Veröffentlichungsordner, NACH kennzahlen.py und VOR llms.py, inline_data.py, Minify:

    python3 scripts/statische_tabellen.py _site

Warum: KI-Crawler (GPTBot, ClaudeBot, PerplexityBot …) und ein Teil der Suchmaschinen führen kein JavaScript aus.
Für sie standen die 19 Broker und die 70 ETFs bisher nicht auf der Seite – nur „Die Übersicht wird geladen …“.
Jetzt stehen die Zeilen im ausgelieferten HTML. Im Browser ersetzt das Seitenskript sie wie bisher durch seine eigene
Fassung (innerHTML) – mit Sortieren, Aufklappen und den Handy-Karten. Die Quell-HTML im Repository bleiben unverändert.

  broker-vergleich.html   <div id="bv-tabelle">            ← broker.json (gleiche Tabelle wie das Seitenskript)
  anleihen-etf.html       <table class="etf" data-gruppe>  ← top10-anleihen-etfs.json, Kurse aus kurse-auswahl.json
  anleihen-laender.html, unternehmensanleihen-laender.html
                          <tbody id="kpis-body">           ← top10-…-laender.json, Gruppe „deutschland“ – erst wenn die
                                                             automatische Rangliste gilt („aktiv“); bis dahin zeigt die
                                                             Seite ihre Handauswahl, die nur das Seitenskript kennt
  anleihen-kupon.html     <tbody id="kpis-staat">, <tbody id="kpis-unternehmen">
                                                           ← top10-anleihen-kupon.json, Gruppen „staat“ und „unternehmen“ (seit 01.10.2026)

Passt eine Seite oder Datei nicht zum Erwarteten, gibt es eine Warnung und die Seite bleibt, wie sie ist.
"""
import datetime
import html as htmllib
import json
import os
import re
import sys
from decimal import ROUND_HALF_UP, Decimal

EUR = "&nbsp;€"


def warn(text):
    print(f"::warning::statische_tabellen.py: {text}")


def esc(s):
    return htmllib.escape(str(s), quote=True)


def zahl(v, nk=0):
    """Deutsches Zahlenformat wie MC.zahl (site.js): Tausenderpunkt, Komma, echtes Minus; keine Zahl → „–“."""
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        return "–"
    # kaufmännisch runden wie der Browser (104,095 → 104,10); format() allein rundet die Binärzahl (→ 104,09)
    q = Decimal(repr(float(abs(v)))).quantize(Decimal(1).scaleb(-nk), rounding=ROUND_HALF_UP)
    s = f"{q:,.{nk}f}".replace(",", "\u0000").replace(".", ",").replace("\u0000", ".")
    return ("−" if v < 0 and s.strip("0,.") else "") + s


def datum(iso):
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", str(iso or ""))
    return f"{m.group(3)}.{m.group(2)}.{m.group(1)}" if m else "–"


def lade(site, name):
    with open(os.path.join(site, name), encoding="utf-8") as f:
        return json.load(f)


# ---------- Broker-Vergleich: dieselbe Tabelle wie das Skript in broker-vergleich.html ----------
def broker_tabelle(D, heute):
    def gilt(x):
        return x is not None and (isinstance(x, str) or not x.get("bis") or heute <= x["bis"])

    def txt(x):
        return x if isinstance(x, str) else x["t"] + (f" (Angebot bis {datum(x['bis'])})" if x.get("zeige_bis") else "")

    def liste(a):
        return [txt(x) for x in (a or []) if gilt(x)]

    def smalls(a):
        return "".join(f"<small>{t}</small>" for t in liste(a))

    def geld(v, ab):
        return ("ab " if ab else "") + zahl(v, 2) + EUR

    def handel(b):
        h = b.get("handelszeit")   # im Browser zusätzlich in MEZ/MESZ umgerechnet; hier die Angabe des Anbieters
        return b["handel"].replace("{handelszeit}", f"{h['von']}–{h['bis']} Uhr {h['zone']}") if h else b["handel"]

    def hin(b):
        return "".join(f'<span class="hin warn">{t}</span>' for t in b.get("hin") or [])

    gruppen = {g["id"]: [] for g in D["gruppen"]}
    for i, b in enumerate(D["anbieter"]):
        gruppen[b["gruppe"]].append((1e9 if b.get("k5") is None else b["k5"], i, b))
    t = ('<table class="bv-t"><caption class="sr-only">Broker für Anleihen im Vergleich, Stand ' + datum(D["stand"]) + "</caption>"
         '<thead><tr><th scope="col">Anbieter</th><th scope="col">Anleihen</th><th scope="col">Handelsplätze</th>'
         '<th scope="col">Gebühr je Kauf</th><th scope="col" class="r">Kauf für 5.000' + EUR + '</th>'
         '<th scope="col" class="r">Kauf für 100.000' + EUR + '</th><th scope="col">Depot</th></tr></thead>')
    for g in D["gruppen"]:
        nein = g["id"] == "nein"
        reihe = [b for _, _, b in sorted(gruppen[g["id"]], key=lambda x: (x[0], x[1]))]
        t += (f'<tbody class="g-{g["id"]}"><tr class="grp"><th colspan="7" scope="rowgroup"><span class="bdg {g["id"]}">{g["bdg"]}</span>{g["titel"]}'
              f' <span class="n">· {len(reihe)} Anbieter' + ("" if nein else ", nach Kosten für 5.000" + EUR + " sortiert") + "</span></th></tr>")
        for b in reihe:
            kopf = f'<th scope="row" class="an"><b>{b["name"]}</b><span class="typ">{b["typ"]}</span>{hin(b)}</th>'
            if nein:
                t += f'<tr>{kopf}<td colspan="6">{b["anleihen"]}{smalls(b.get("anleihen_n"))}</td></tr>'
                continue
            t += (f'<tr>{kopf}<td>{b["anleihen"]}{smalls(b.get("anleihen_n"))}</td><td>{handel(b)}{smalls(b.get("handel_n"))}</td>'
                  f'<td>{b["gebuehr"]}{smalls(b.get("gebuehr_n"))}</td>'
                  f'<td class="k"><b>{geld(b["k5"], b.get("k5_ab"))}</b><small>{b["k5_w"]}</small></td>'
                  f'<td class="k"><b>{geld(b["k100"], b.get("k100_ab"))}</b><small>{"; ".join(liste(b.get("k100_w")))}</small></td>'
                  f'<td>{b["depot"]}{smalls(b.get("depot_n"))}</td></tr>')
        t += "</tbody>"
    return t + "</table>"


def broker(site):
    pfad = os.path.join(site, "broker-vergleich.html")
    html_ = open(pfad, encoding="utf-8").read()
    platz = re.compile(r'(<div id="bv-tabelle">)<p class="klein" id="bv-laden">[^<]*</p>(</div>)')
    if not platz.search(html_):
        return warn("broker-vergleich.html: Platzhalter #bv-tabelle nicht gefunden – Tabelle nicht vorab geschrieben")
    D = lade(site, "broker.json")
    tabelle = broker_tabelle(D, datetime.date.today().isoformat())
    neu = platz.sub(lambda m: m.group(1) + tabelle + m.group(2), html_, count=1)
    # Der Hinweis „Die Tabelle braucht JavaScript“ stimmt dann nicht mehr
    neu = re.sub(r'\n?<noscript><p class="klein">Die Tabelle braucht JavaScript\..*?</noscript>', "", neu, count=1, flags=re.S)
    with open(pfad, "w", encoding="utf-8") as f:
        f.write(neu)
    print(f"broker-vergleich.html: {len(D['anbieter'])} Anbieter fest im HTML")


# ---------- Anleihen-ETFs: zehn Zeilen je Kategorie (vereinfachte Fassung von rowHtml der Seite) ----------
SYM = {"EUR": "€", "USD": "$", "GBP": "£", "JPY": "¥"}


def etf_laufzeit(r):
    if r.get("endjahr"):
        return f"bis {r['endjahr']}<small>Laufzeit-ETF</small>"
    lz = r.get("laufzeit")
    if not lz:
        return "–"

    def j(x):
        return zahl(x, 0 if float(x).is_integer() else 1)

    def m(x):
        return int(x * 12 + 0.5)
    if lz[1] is None:
        return f"über {j(lz[0])} Jahre"
    if lz[1] < 1:
        return f"{m(lz[0])}–{m(lz[1])} Monate" if lz[0] > 0 else f"bis {m(lz[1])} Monate"
    return f"{j(lz[0])}–{j(lz[1])} Jahre" if lz[0] > 0 else f"bis {j(lz[1])} {'Jahr' if lz[1] == 1 else 'Jahre'}"


def etf_volumen(v):
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        return "–"
    return f"{zahl(v / 1000, 1)} Mrd. €" if v >= 1000 else f"{zahl(v, 1 if v < 10 else 0)} Mio. €"


def etf_zeile(r, rang, kurse):
    fokus = "aktiv gemanagt, ohne Index" if r.get("aktiv") else f"Index: {r['index']}" if r.get("index") else ""
    k = kurse.get(r["isin"])
    kurs = f"{zahl(k[0], 2)} {SYM.get(r.get('handelswaehrung'), r.get('handelswaehrung') or '€')}" if k and isinstance(k[0], (int, float)) else "–"
    use = "ja<small>ausschüttend</small>" if r.get("ausschuettend") else "nein<small>thesaurierend</small>"
    kosten = f"{zahl(r['kosten'], 2)} %" if isinstance(r.get("kosten"), (int, float)) else "–"
    return (f'<tr><td class="num rk">{rang}</td>'
            f'<th scope="row">{esc(r.get("kurzname") or r["name"])}<small>{esc(fokus)}</small><span class="isin">{esc(r["isin"])}</span></th>'
            f'<td class="num" data-l="Kurs">{kurs}</td><td class="num" data-l="Kosten p. a.">{kosten}</td>'
            f'<td class="num" data-l="Laufzeit">{etf_laufzeit(r)}</td><td class="num" data-l="Größe">{etf_volumen(r.get("vermoegen"))}</td>'
            f'<td class="num" data-l="Umsatz">{etf_volumen(r.get("umsatz12"))}</td><td class="use" data-l="Zinsen aufs Konto?">{use}</td></tr>')


def etfs(site):
    pfad = os.path.join(site, "anleihen-etf.html")
    html_ = open(pfad, encoding="utf-8").read()
    D = lade(site, "top10-anleihen-etfs.json")
    try:
        kurse = lade(site, "kurse-auswahl.json").get("kurse") or {}
    except Exception:
        kurse = {}
    gefuellt, anzahl = 0, 0
    for key, g in (D.get("gruppen") or {}).items():
        reihe = g.get("etfs") or []
        leer = re.compile(r'(<table class="etf" data-gruppe="' + re.escape(key) + r'">.*?<tbody>)\s*(</tbody>)', re.S)
        if not reihe or not leer.search(html_):
            continue
        zeilen = "".join(etf_zeile(r, i + 1, kurse) for i, r in enumerate(reihe))
        html_ = leer.sub(lambda m: m.group(1) + zeilen + m.group(2), html_, count=1)
        gefuellt, anzahl = gefuellt + 1, anzahl + len(reihe)
    if not gefuellt:
        return warn("anleihen-etf.html: keine leere ETF-Tabelle gefunden – nichts vorab geschrieben")
    html_ = re.sub(r'\n?<noscript><p class="note">Die Tabellen der ETFs brauchen JavaScript\.</p></noscript>', "", html_, count=1)
    with open(pfad, "w", encoding="utf-8") as f:
        f.write(html_)
    print(f"anleihen-etf.html: {anzahl} ETFs in {gefuellt} Tabellen fest im HTML")


# ---------- Top 10 nach Ländern: Deutschland (Startansicht), vereinfachte Fassung von zeileHtml (top10-tabellen.js) ----------
def restlaufzeit(jahre):
    tage = round(jahre * 365.25)
    if tage <= 0:
        return "fällig"
    if tage < 31:
        return f"{tage} {'Tag' if tage == 1 else 'Tage'}"
    monate = round(tage / 30.44)
    if monate < 12:
        return f"{monate} {'Monat' if monate == 1 else 'Monate'}"
    return zahl(jahre, 1) + " Jahre"


def laender_zeile(r, rang, stand):
    try:
        jahre = (datetime.date.fromisoformat(r["faellig"]) - datetime.date.fromisoformat(stand)).days / 365.25
        rest = restlaufzeit(jahre)
    except Exception:
        rest = "–"
    kupon = zahl(r["kupon"], 3 if round(r["kupon"] * 1000) % 10 else 2) if isinstance(r.get("kupon"), (int, float)) else "–"
    rendite = zahl(r["rendite"], 2) + " %" if isinstance(r.get("rendite"), (int, float)) else "–"
    vol = f"{r['vol'] / 1e9:.3g}".replace(".", ",") + " Mrd." if isinstance(r.get("vol"), (int, float)) else "–"
    stk = zahl(r["stk"], 0 if float(r["stk"]).is_integer() else 3 if round(r["stk"] * 1000) % 10 else 2) if isinstance(r.get("stk"), (int, float)) else "–"
    return (f'<tr><td class="num rk">{rang}</td><th scope="row">{esc(r.get("emittent") or "")}<small class="fa-mobil">fällig {datum(r.get("faellig"))}</small></th>'
            f'<td class="num">{rendite}</td><td class="num">{zahl(r.get("kurs"), 2)}</td><td class="num">{kupon} %</td>'
            f'<td class="num">{datum(r.get("faellig"))}</td><td class="num">{rest}</td>'
            f'<td class="isin"><a href="anleihe.html?isin={esc(r["isin"])}" title="Steckbrief: Kurs, Rendite, Kursverlauf, Handel und Stammdaten">{esc(r["isin"])}</a></td>'
            f'<td class="txt">{esc(r.get("cur") or "")}</td><td class="num">{vol}</td><td class="num">{stk}</td></tr>')


def laender(site, seite, datei):
    pfad = os.path.join(site, seite)
    D = lade(site, datei)
    if not (D.get("aktiv") and D.get("gruppen") and D.get("fenster")):
        return print(f"{seite}: automatische Rangliste noch nicht aktiv – Handauswahl der Seite bleibt (nichts vorab geschrieben)")
    reihe = D["gruppen"].get("deutschland") or []
    html_ = open(pfad, encoding="utf-8").read()
    leer = re.compile(r'(<tbody id="kpis-body">)\s*(</tbody>)')
    if not reihe or not leer.search(html_):
        return warn(f"{seite}: leere Tabelle #kpis-body oder Gruppe „deutschland“ fehlt – nichts vorab geschrieben")
    zeilen = "".join(laender_zeile(r, i + 1, D.get("stand")) for i, r in enumerate(reihe))
    with open(pfad, "w", encoding="utf-8") as f:
        f.write(leer.sub(lambda m: m.group(1) + zeilen + m.group(2), html_, count=1))
    print(f"{seite}: {len(reihe)} Anleihen (Deutschland) fest im HTML")


def kupon(site, seite="anleihen-kupon.html", datei="top10-anleihen-kupon.json"):
    """Top 30 nach Kupon (seit 01.10.2026), zwei Tabellen: dieselben Zeilen wie das Seitenskript, Spalten wie die Länder-Seiten."""
    pfad = os.path.join(site, seite)
    D = lade(site, datei)
    html_ = open(pfad, encoding="utf-8").read()
    geschrieben = []
    for key in ("staat", "unternehmen"):
        reihe = (D.get("gruppen") or {}).get(key) or []
        leer = re.compile(r'(<tbody id="kpis-' + key + r'">)\s*(</tbody>)')
        if not reihe or not leer.search(html_):
            warn(f"{seite}: leere Tabelle #kpis-{key} oder Gruppe „{key}“ fehlt – nichts vorab geschrieben")
            continue
        zeilen = "".join(laender_zeile(r, i + 1, D.get("stand")) for i, r in enumerate(reihe))
        html_ = leer.sub(lambda m: m.group(1) + zeilen + m.group(2), html_, count=1)
        geschrieben.append(f"{len(reihe)} {key}")
    if geschrieben:
        with open(pfad, "w", encoding="utf-8") as f:
            f.write(html_)
        print(f"{seite}: {', '.join(geschrieben)} fest im HTML")


def main():
    site = sys.argv[1] if len(sys.argv) > 1 else "_site"
    if not os.path.isdir(site):
        raise SystemExit(f"Ordner nicht gefunden: {site}")
    for name, schritt in (("Broker", lambda: broker(site)), ("ETFs", lambda: etfs(site)),
                          ("Staatsanleihen nach Ländern", lambda: laender(site, "anleihen-laender.html", "top10-staatsanleihen-laender.json")),
                          ("Unternehmensanleihen nach Ländern", lambda: laender(site, "unternehmensanleihen-laender.html", "top10-unternehmensanleihen-laender.json")),
                          ("Anleihen nach Kupon", lambda: kupon(site))):
        try:
            schritt()
        except Exception as e:   # Daten oder Seite anders als erwartet: Seite bleibt, wie sie ist
            warn(f"{name}: nicht vorab geschrieben ({type(e).__name__}: {e})")


if __name__ == "__main__":
    main()
