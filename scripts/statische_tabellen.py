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
  anleihen-kupon.html     <tbody id="kpis-staat">, <tbody id="kpis-oeffentlich">, <tbody id="kpis-unternehmen">
                                                           ← top10-anleihen-kupon.json, je Gruppe eine Tabelle (seit 01.10.2026)

Passt eine Seite oder Datei nicht zum Erwarteten, gibt es eine Warnung und die Seite bleibt, wie sie ist.
"""
import datetime
import html as htmllib
import json
import math
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


# ---------- Broker-Vergleich: dieselbe Rechnung und dieselben Zeilen wie das Skript in broker-vergleich.html ----------
# broker.json enthält je Anbieter das Preismodell in Bausteinen (fix, pct, min, max, staffel, marginal, plus). Daraus
# rechnen Seite und dieses Skript die Kosten – ändert sich die Rechnung an einer Stelle, muss sie an der anderen folgen.
PZ = "&nbsp;%"


def b_rund(v):
    return math.floor(v * 100 + 1e-6 + 0.5) / 100   # wie rund() im Seitenskript


def b_eur(v):
    return zahl(v, 2) + EUR


def b_glatt(v):
    return zahl(v, 2 if round(v * 100) % 100 else 0) + EUR


def b_pz(v):
    return ("%g" % v).replace(".", ",") + PZ


def b_baustein(p, B):
    f = []
    if p.get("fix"):
        f.append(b_eur(p["fix"]))
    if p.get("pct"):
        f.append(b_pz(p["pct"]) + " von " + b_glatt(B))
    roh = b_rund((p.get("fix") or 0) + B * (p.get("pct") or 0) / 100)
    v, grenze = roh, ""
    if p.get("min") is not None and roh < p["min"]:
        v, grenze = p["min"], "Mindestpreis"
    if p.get("max") is not None and roh > p["max"]:
        v, grenze = p["max"], "Höchstpreis"
    einfach = not p.get("pct")   # nur ein fester Betrag
    return {"v": v, "roh": roh, "formel": ((p.get("ft") or ("Festpreis" if p.get("fix") else "")) + " " + b_eur(p.get("fix") or 0)).strip() if einfach else " + ".join(f), "grenze": grenze, "einfach": einfach}


def b_stufe(st, i, alle):
    if st.get("t"):
        return st["t"]
    if st.get("unter") is not None:
        return "unter " + b_glatt(st["unter"])
    if st.get("bis") is not None:
        return "bis " + b_glatt(st["bis"])
    v = alle[i - 1] if i else {}
    if v.get("unter") is not None:
        return "ab " + b_glatt(v["unter"])
    return "über " + b_glatt(v["bis"]) if v.get("bis") is not None else ""


def b_rechne(w, B):
    schritte = []
    if w.get("staffel"):
        st = w["staffel"]
        i = 0
        while i < len(st) - 1 and not (B < st[i]["unter"] if st[i].get("unter") is not None else B <= st[i]["bis"] if st[i].get("bis") is not None else True):
            i += 1
        b = b_baustein(st[i], B)
        name = b_stufe(st[i], i, st)
        kurz = (name + ": " if name else "") + (b["grenze"] + " " + b_eur(b["v"]) if b["grenze"] else b["formel"])
        schritte.append(f"Preisstufe {name}: " + b["formel"] + ("" if b["einfach"] else " = " + b_eur(b["roh"])))
        if b["grenze"]:
            schritte.append(b["grenze"] + " " + b_eur(b["v"]) + " greift")
        v = b["v"]
    elif w.get("marginal"):
        rest, unten, f, summe = B, 0, [], 0
        for m in w["marginal"]:
            if rest <= 0:
                break
            teil = min(rest, m["bis"] - unten) if m.get("bis") is not None else rest
            f.append(b_pz(m["pct"]) + " von " + b_glatt(teil))
            summe += teil * m["pct"] / 100
            rest -= teil
            unten = m.get("bis")
        summe = b_rund(summe)
        v, kurz = summe, " + ".join(f)
        schritte.append(kurz + " = " + b_eur(summe))
        if w.get("min") is not None and summe < w["min"]:
            v = w["min"]
            kurz = "Mindestpreis " + b_eur(v)
            schritte.append(kurz + " greift")
        if w.get("max") is not None and summe > w["max"]:
            v = w["max"]
            kurz = "Höchstpreis " + b_eur(v)
            schritte.append(kurz + " greift")
    else:
        b = b_baustein(w, B)
        v = b["v"]
        kurz = b["grenze"] + " " + b_eur(b["v"]) if b["grenze"] else b["formel"]
        schritte.append(b["formel"] + ("" if b["einfach"] else " = " + b_eur(b["roh"])))
        if b["grenze"]:
            schritte.append(b["grenze"] + " " + b_eur(b["v"]) + " greift")
    for p in w.get("plus") or []:
        x = b_baustein(p, B)
        kurz += " + " + b_eur(x["v"]) + " " + (p.get("k") or p["t"])
        schritte.append("+ " + b_eur(x["v"]) + " " + p["t"] + ("" if x["einfach"] else " (" + x["formel"] + (", " + x["grenze"] + " greift" if x["grenze"] else "") + ")"))
        v += x["v"]
    return {"v": b_rund(v), "kurz": kurz, "schritte": schritte, "w": w}


def b_guenstigster(b, B):
    r = None
    for w in b["wege"]:
        if w.get("nur_info"):
            continue
        x = b_rechne(w, B)
        if r is None or x["v"] < r["v"] - 1e-9:
            r = x
    return r


def b_depot(b, B):
    """Depot im Jahr: fester Betrag + Prozent vom Depotwert; pmin = Mindestbetrag des Prozent-Teils."""
    d = b.get("depot") or {}
    if d.get("fix") is None and d.get("pct") is None:
        return 0
    v = (d.get("fix") or 0) + max(B * (d.get("pct") or 0) / 100, d.get("pmin") or 0)
    if d.get("min") is not None and v < d["min"]:
        v = d["min"]
    if d.get("max") is not None and v > d["max"]:
        v = d["max"]
    return b_rund(v)


def broker_teile(D, heute):
    """Kostenliste (für den Standardbetrag), Angebots-Tabelle und Quellenliste als HTML – wie das Seitenskript."""
    def gilt(x):
        return x is not None and (isinstance(x, str) or not x.get("bis") or heute <= x["bis"])

    def txt(x):
        return x if isinstance(x, str) else x["t"] + (f" (Angebot bis {datum(x['bis'])})" if x.get("zeige_bis") else "")

    def smalls(a):
        return "".join(f"<small>{txt(x)}</small>" for x in (a or []) if gilt(x))

    def handel(b):
        h = b.get("handelszeit")   # im Browser zusätzlich in MEZ/MESZ umgerechnet; hier die Angabe des Anbieters
        return b["handel"].replace("{handelszeit}", f"{h['von']}–{h['bis']} Uhr {h['zone']}") if h else b["handel"]

    def hin(b):
        return "".join(f'<span class="hin">{t}</span>' for t in b.get("hin") or [])

    def quellen(b):
        return " · ".join(f'<a href="{q["url"]}" rel="noopener">{q["t"]}</a>' + (f' ({q["stand"]})' if q.get("stand") else "") for q in b.get("quellen") or [])

    def zelle(tag, x):
        if not x:
            return f"<{tag}>–</{tag}>"
        return f'<{tag}' + (' class="warn"' if x.get("warn") else "") + f'>{x["t"]}' + (f'<small>{x["n"]}</small>' if x.get("n") else "") + f"</{tag}>"

    # 1 Kostenliste
    B = D.get("standard") or 5000
    for i, b in enumerate(D["anbieter"]):
        b["_i"] = i
    mit = [b for b in D["anbieter"] if b.get("wege")]
    zeilen = sorted(({"b": b, "r": b_guenstigster(b, B), "d": b_depot(b, B)} for b in mit), key=lambda x: (x["r"]["v"], x["b"]["_i"]))
    hoch, tief = max(x["r"]["v"] for x in zeilen) or 1, zeilen[0]["r"]["v"]
    li = ""
    for x in zeilen:
        b, r, w, d = x["b"], x["r"], x["r"]["w"], x["b"].get("depot") or {}
        andere = ""
        for y in b["wege"]:
            if y is w:
                continue
            a = b_rechne(y, B)
            andere += (f'<span>{y["name"]}: <b>{b_eur(a["v"])}</b> – {a["kurz"]}' + (f'; dazu {y["offen"]}' if y.get("offen") else "")
                       + (f' ({y["n"]})' if y.get("n") else "") + "</span>")
        ist_min = r["v"] == tief
        pz = r["v"] / B * 100
        anteil = "unter 0,01" + PZ if r["v"] > 0 and pz < 0.005 else zahl(pz, 2) + PZ
        li += (f'<li class="bk{" min" if ist_min else ""}" data-g="{b["gruppe"]}">'
               f'<div class="bk-z"><div class="bk-an"><b>{b["name"]}</b><span class="typ">{b["typ"]}</span>{hin(b)}</div>'
               f'<div class="bk-ko"><div class="bk-bar"><i style="width:calc((100% - 150px) * {r["v"] / hoch:.4f})"></i><b'
               + (' title="günstigster Preis"' if ist_min else "") + f'>{b_eur(r["v"])}</b><span class="pz">{anteil}</span></div>'
               + (f'<p class="bk-of">dazu {w["offen"]}</p>' if w.get("offen") else "")
               + f'<details class="bk-d" data-b="{b["_i"]}"><summary><span class="bk-rw">{r["kurz"]} · {w["name"]}</span>'
               f'<span class="bk-mehr">Rechnung und Quelle</span></summary><dl class="bk-dl">'
               f'<dt>Preis laut Anbieter</dt><dd>{b["preis"]}{smalls(b.get("preis_n"))}</dd>'
               f'<dt>Rechnung für {b_glatt(B)}</dt><dd><small>{w["name"]}</small>' + "".join(f"<span>{s}</span>" for s in r["schritte"])
               + f'<span class="sum">= {b_eur(r["v"])} · {anteil} vom Betrag</span>' + (f'<small>{w["n"]}</small>' if w.get("n") else "") + "</dd>"
               + (f'<dt>Nicht enthalten</dt><dd>{w["offen"]}</dd>' if w.get("offen") else "")
               + (f"<dt>Andere Wege</dt><dd>{andere}</dd>" if andere else "")
               + f'<dt>Depot</dt><dd>{d.get("t", "–")}{smalls(d.get("n"))}</dd>'
               f'<dt>Quelle</dt><dd>{quellen(b)}' + (f'<small>{b["notiz"]}</small>' if b.get("notiz") else "") + "</dd></dl></details></div>"
               f'<div class="bk-de{" kostet" if x["d"] > 0 else ""}"><span class="lab">Depot im Jahr: </span>{b_glatt(x["d"])}'
               + (f'<small>{d["kurz"]}</small>' if d.get("kurz") else "") + "</div></div></li>")

    # 2 Angebot (nur die Tabelle; die Handy-Karten zeichnet das Seitenskript)
    gruppen = {g["id"]: [] for g in D["gruppen"]}
    for b in D["anbieter"]:
        gruppen[b["gruppe"]].append(b)
    t = ('<table class="bv-t"><caption class="sr-only">Anleihen-Angebot der Broker im Vergleich, Stand ' + datum(D["stand"]) + "</caption>"
         '<thead><tr><th scope="col">Anbieter</th><th scope="col">Anleihen</th><th scope="col">Handelsplätze</th>'
         '<th scope="col">Order mit Limit</th><th scope="col">Steuer</th></tr></thead>')
    for g in D["gruppen"]:
        reihe = gruppen[g["id"]]
        t += (f'<tbody class="g-{g["id"]}"><tr class="grp"><th colspan="5" scope="rowgroup"><span class="bdg {g["id"]}">{g["bdg"]}</span>{g["titel"]}'
              f' <span class="n">· {len(reihe)} Anbieter</span></th></tr>')
        for b in reihe:
            kopf = f'<th scope="row" class="an"><b>{b["name"]}</b><span class="typ">{b["typ"]}</span></th>'
            if g["id"] == "nein":
                t += f'<tr>{kopf}<td colspan="4">{b["anleihen"]}{smalls(b.get("anleihen_n"))}</td></tr>'
                continue
            t += (f'<tr>{kopf}<td>{b["anleihen"]}{smalls(b.get("anleihen_n"))}</td><td>{handel(b)}{smalls(b.get("handel_n"))}</td>'
                  + zelle("td", b.get("limit")) + zelle("td", b.get("steuer")) + "</tr>")
        t += "</tbody>"
    t += "</table>"

    # 3 Quellen je Anbieter
    q = "".join(f'<li><b>{b["name"]}</b><span>{quellen(b) or "–"}' + (f'<br>{b["notiz"]}' if b.get("notiz") else "") + "</span></li>" for b in D["anbieter"])
    return li, t, q, B


def broker_probe(D):
    """Selbsttest: Stimmen die gerechneten Kosten mit den Kontrollwerten („probe“) aus den Preisverzeichnissen überein?"""
    for b in D["anbieter"]:
        for betrag, soll in (b.get("probe") or {}).items():
            ist = b_guenstigster(b, float(betrag))["v"]
            if abs(ist - soll) > 0.005:
                warn(f'broker.json: {b["name"]} – Rechnung für {betrag} € ergibt {ist:.2f} €, Kontrollwert ist {soll:.2f} €')


def broker(site):
    pfad = os.path.join(site, "broker-vergleich.html")
    html_ = open(pfad, encoding="utf-8").read()
    D = lade(site, "broker.json")
    broker_probe(D)
    li, tabelle, quellen, B = broker_teile(D, datetime.date.today().isoformat())
    plaetze = (
        (re.compile(r'(<ol class="bk-liste" id="bk-liste"[^>]*>)<li class="klein" id="bk-laden">[^<]*</li>(</ol>)'), li, "Kostenliste #bk-liste"),
        (re.compile(r'(<div id="bv-tabelle">)<p class="klein" id="bv-laden">[^<]*</p>(</div>)'), tabelle, "Tabelle #bv-tabelle"),
        (re.compile(r'(<ul class="bq" id="bq">)<li class="klein">[^<]*</li>(</ul>)'), quellen, "Quellenliste #bq"),
    )
    neu = html_
    for muster, inhalt, name in plaetze:
        if not muster.search(neu):
            return warn(f"broker-vergleich.html: Platzhalter für {name} nicht gefunden – nichts vorab geschrieben")
        neu = muster.sub(lambda m, inhalt=inhalt: m.group(1) + inhalt + m.group(2), neu, count=1)
    # Stand und Anzahl stehen sonst erst nach dem Skript da
    for schluessel, wert in (("stand", datum(D["stand"])), ("anzahl", str(len(D["anbieter"])))):
        neu = re.sub(r'(<span data-bv="' + schluessel + r'">)[^<]*(</span>)', lambda m, wert=wert: m.group(1) + wert + m.group(2), neu)
    # Der Hinweis „Die Liste braucht JavaScript“ stimmt dann nicht mehr
    neu = re.sub(r'\n?<noscript><p class="klein">Die Liste braucht JavaScript\..*?</noscript>', "", neu, count=1, flags=re.S)
    with open(pfad, "w", encoding="utf-8") as f:
        f.write(neu)
    print(f"broker-vergleich.html: {len(D['anbieter'])} Anbieter fest im HTML (Kosten für {zahl(B)} €, Angebot, Quellen)")


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
    """Top 30 nach Kupon (seit 01.10.2026), drei Tabellen: dieselben Zeilen wie das Seitenskript, Spalten wie die Länder-Seiten."""
    pfad = os.path.join(site, seite)
    D = lade(site, datei)
    html_ = open(pfad, encoding="utf-8").read()
    geschrieben = []
    for key in ("staat", "oeffentlich", "unternehmen"):
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
