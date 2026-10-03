#!/usr/bin/env python3
"""statische_tabellen.py – schreibt Tabellen, die sonst erst das Skript im Browser zeichnet, beim Deploy fest ins HTML
(seit 30.09.2026).

Läuft im GitHub-Workflow auf dem Veröffentlichungsordner, NACH kennzahlen.py und VOR llms.py, inline_data.py, Minify:

    python3 scripts/statische_tabellen.py _site

Warum: KI-Crawler (GPTBot, ClaudeBot, PerplexityBot …) und ein Teil der Suchmaschinen führen kein JavaScript aus.
Für sie standen die Broker und die 70 ETFs bisher nicht auf der Seite – nur „Die Übersicht wird geladen …“.
Jetzt stehen die Zeilen im ausgelieferten HTML. Im Browser ersetzt das Seitenskript sie wie bisher durch seine eigene
Fassung (innerHTML) – mit Sortieren, Aufklappen und den Handy-Karten. Die Quell-HTML im Repository bleiben unverändert.

  broker-vergleich.html   <div id="bv-tabelle">            ← broker.json (gleiche Tabelle wie das Seitenskript)
  anleihen-etf.html       <table class="etf" data-gruppe>  ← top10-anleihen-etfs.json, Kurse aus kurse-auswahl.json;
                                                             seit 02.10.2026 auch die ETF-Zahl je Kategorie-Kachel, die
                                                             Angaben <span data-etf="…"> und die Zeile „Daten-Stand“
  anleihen-laender.html, unternehmensanleihen-laender.html
                          <tbody id="kpis-body">           ← top10-…-laender.json, Gruppe „deutschland“ – erst wenn die
                                                             automatische Rangliste gilt („aktiv“); bis dahin zeigt die
                                                             Seite ihre Handauswahl, die nur das Seitenskript kennt
  anleihen-kupon.html     <tbody id="kpis-staat">, <tbody id="kpis-oeffentlich">, <tbody id="kpis-unternehmen">
                                                           ← top10-anleihen-kupon.json, je Gruppe eine Tabelle (seit 01.10.2026)
  staatsanleihen-laufzeit.html, unternehmensanleihen-laufzeit.html
                          <table class="kpis" data-gruppe>  ← automatische Rangliste, solange sie nicht „aktiv“ ist die
                                                             Handauswahl der Seite (ANLEIHEN im Seitenskript; seit 03.10.2026)

  index.html              „Sechs Beispiele“ (table.itab)  ← Rendite, Kurs und Restlaufzeit der Zeilen aus kurse-auswahl.json,
                                                             „Kurse und Renditen vom“ dessen Stand und die Rendite der
                                                             Hero-Karte (seit 03.10.2026, SEO-Runde 2)

Auf den Ranglisten-, Kupon- und ETF-Seiten schreibt das Skript dazu die Zeile „Daten-Stand“ im Wortlaut des Seitenskripts
(SEO-Runde 2) – nur zusammen mit den Zeilen, zu denen sie gehört.

Die Anleihen-Tabellen haben seit 03.10.2026 die Form der Standardtabelle (felder.js, MC.felder.tabelle; Regeln in
docs/ANLEIHEN-ANGABEN.md): hier nachgebaut in std_tabelle() mit denselben Schreibweisen aus _common.py.

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


def ist_zahl(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)


def ist_datum(iso):
    return bool(re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(iso or "")))


def datenstand_setzen(html_, text):
    """<p id="datastand">Daten-Stand: …</p> auf text setzen; None, wenn die Zeile fehlt (dann bleibt die Seite, wie sie ist)."""
    muster = re.compile(r'(<p id="datastand">)Daten-Stand:[^<]*(</p>)')
    if not muster.search(html_):
        return None
    return muster.sub(lambda m: m.group(1) + esc_js(text) + m.group(2), html_, count=1)


def esc_js(s):
    """wie MC.esc (site.js)"""
    return re.sub(r"[&<>\"']", lambda m: {"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"}[m.group(0)], str(s))


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
    """Liste „Kosten und Angebot“ (für den Standardbetrag) und Quellenliste als HTML – wie das Seitenskript."""
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

    def zelle(x):
        if not x:
            return "<dd>–</dd>"
        return "<dd" + (' class="warn"' if x.get("warn") else "") + f'>{x["t"]}' + (f'<small>{x["n"]}</small>' if x.get("n") else "") + "</dd>"

    G = {g["id"]: g for g in D["gruppen"]}

    def angebot(b):
        return ('<div class="bk-ang"><span class="lab">Anleihen: </span>' + (f'<span class="bdg aw">{G["aw"]["bdg"]}</span> ' if b["gruppe"] == "aw" else "")
                + b["anleihen"] + smalls(b.get("anleihen_n")) + "</div>")

    marke = {"ja": ("✓", "ja"), "nein": ("–", "nicht genannt"), "ka": ("?", "keine Angabe")}

    def plaetze(b):
        """Die vier Börsen aus D["boersen"] einheitlich als Marken, darunter was es außerdem gibt."""
        if not b.get("handel"):
            return '<div class="bk-hp"><span class="lab">Handelsplätze: </span>–</div>'
        m = ""
        if b.get("boersen"):
            for x in D.get("boersen") or []:
                v = b["boersen"].get(x["id"])
                k = "ja" if v is True else "nein" if v is False else "ka"
                m += f'<li class="{k}"><span aria-hidden="true">{marke[k][0]}</span><span class="sr-only">{marke[k][1]}: </span>{x["name"]}</li>'
            m = f'<ul class="bk-b">{m}</ul>'
        return f'<div class="bk-hp"><span class="lab">Handelsplätze: </span>{m}<small>{handel(b)}</small>{smalls(b.get("handel_n"))}</div>'

    def kopf(b):
        return f'<div class="bk-an"><b>{b["name"]}</b><span class="typ">{b["typ"]}</span>{hin(b)}</div>'

    def quelle(b):
        return f'<dt>Quelle</dt><dd>{quellen(b) or "–"}' + (f'<small>{b["notiz"]}</small>' if b.get("notiz") else "") + "</dd>"

    # 1 Kosten und Angebot
    B = D.get("standard") or 5000
    for i, b in enumerate(D["anbieter"]):
        b["_i"] = i
    mit = [b for b in D["anbieter"] if b.get("wege")]
    ohne = [b for b in D["anbieter"] if not b.get("wege")]
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
        li += (f'<li class="bk{" min" if ist_min else ""}" data-g="{b["gruppe"]}"><div class="bk-z">' + kopf(b)
               + f'<div class="bk-ko"><div class="bk-bar"><i style="width:calc((100% - 150px) * {r["v"] / hoch:.4f})"></i><b'
               + (' title="günstigster Preis"' if ist_min else "") + f'>{b_eur(r["v"])}</b><span class="pz">{anteil}</span></div>'
               f'<p class="bk-rw">{r["kurz"]} · {w["name"]}</p>'
               + (f'<p class="bk-of">dazu {w["offen"]}</p>' if w.get("offen") else "") + "</div>"
               + angebot(b) + plaetze(b)
               + f'<div class="bk-de{" kostet" if x["d"] > 0 else ""}"><span class="lab">Depot im Jahr: </span>{b_glatt(x["d"])}'
               + (f'<small>{d["kurz"]}</small>' if d.get("kurz") else "") + "</div>"
               f'<details class="bk-d" data-b="{b["_i"]}"><summary><span class="bk-mehr">Rechnung und Quelle</span></summary><dl class="bk-dl">'
               f'<dt>Preis laut Anbieter</dt><dd>{b["preis"]}{smalls(b.get("preis_n"))}</dd>'
               f'<dt>Rechnung für {b_glatt(B)}</dt><dd><small>{w["name"]}</small>' + "".join(f"<span>{s}</span>" for s in r["schritte"])
               + f'<span class="sum">= {b_eur(r["v"])} · {anteil} vom Betrag</span>' + (f'<small>{w["n"]}</small>' if w.get("n") else "") + "</dd>"
               + (f'<dt>Nicht enthalten</dt><dd>{w["offen"]}</dd>' if w.get("offen") else "")
               + (f"<dt>Andere Wege</dt><dd>{andere}</dd>" if andere else "")
               + f'<dt>Depot</dt><dd>{d.get("t", "–")}{smalls(d.get("n"))}</dd>'
               "<dt>Order mit Limit</dt>" + zelle(b.get("limit")) + "<dt>Steuer</dt>" + zelle(b.get("steuer"))
               + quelle(b) + "</dl></details></div></li>")
    if ohne:
        li += f'<li class="bk-grp">{G["nein"]["titel"]} <span class="n">· {len(ohne)} Anbieter</span></li>'
        for b in ohne:
            li += ('<li class="bk ohne" data-g="nein"><div class="bk-z">' + kopf(b) + '<div class="bk-ko"><p class="bk-rw">–</p></div>' + angebot(b) + plaetze(b)
                   + '<div class="bk-de"><span class="lab">Depot im Jahr: </span>–</div>'
                   f'<details class="bk-d" data-b="{b["_i"]}"><summary><span class="bk-mehr">Quelle</span></summary><dl class="bk-dl">' + quelle(b) + "</dl></details></div></li>")

    # 2 Quellen je Anbieter
    q = "".join(f'<li><b>{b["name"]}</b><span>{quellen(b) or "–"}' + (f'<br>{b["notiz"]}' if b.get("notiz") else "") + "</span></li>" for b in D["anbieter"])
    return li, q, B


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
    li, quellen, B = broker_teile(D, datetime.date.today().isoformat())
    plaetze = (
        (re.compile(r'(<ol class="bk-liste" id="bk-liste"[^>]*>)<li class="klein" id="bk-laden">[^<]*</li>(</ol>)'), li, "Liste #bk-liste"),
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
    print(f"broker-vergleich.html: {len(D['anbieter'])} Anbieter fest im HTML (Kosten für {zahl(B)} €, Angebot und Handelsplätze in einer Liste, Quellen)")


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


def etf_monat(m):
    """wie monat() im Seitenskript: „2026-08“ → „08/2026“"""
    return f"{m[5:7]}/{m[:4]}" if m else "–"


def etf_angaben(html_, D, kstand):
    """Was das Seitenskript nach dem Laden der ETF-Liste setzt (seit 02.10.2026 auch fest im HTML):
    die Zahl der ETFs je Kategorie-Kachel (.kat[data-k] .km b), die Angaben <span data-etf="…"> und die Zeile „Daten-Stand“.
    Gleicher Wortlaut wie im Skript; bei einem Fehler bleibt der Text, wie er ist (Warnung)."""
    try:
        neu, kacheln = html_, 0
        for key, g in (D.get("gruppen") or {}).items():
            if not ist_zahl(g.get("anzahl")):
                continue
            muster = re.compile(r'(<a class="kat\b[^>]*\bdata-k="' + re.escape(key) + r'"[^>]*>(?:(?!</a>).)*?<span class="km"><span><b>)[^<]*(</b>)', re.S)
            neu, n = muster.subn(lambda m: m.group(1) + zahl(g["anzahl"]) + m.group(2), neu, count=1)
            kacheln += n
        setze = {"anzahl": zahl(D.get("anzahl")) if ist_zahl(D.get("anzahl")) else None,
                 "umsatz": f"von {etf_monat(D['umsatz'].get('von'))} bis {etf_monat(D['umsatz'].get('bis'))}" if isinstance(D.get("umsatz"), dict) else None,
                 "stand-text": (f"ETF-Liste der Deutschen Börse vom {datum(D.get('stand'))}; Fondsvermögen und Handelskosten aus der "
                                f"Monatsstatistik {etf_monat(D.get('statistik'))}.") if ist_datum(D.get("stand")) else None}
        for k, text in setze.items():
            if text is not None:
                neu = re.sub(r'(<span data-etf="' + k + r'">)[^<]*(</span>)', lambda m, text=text: m.group(1) + esc_js(text) + m.group(2), neu)
        if ist_datum(D.get("stand")):
            zeile = ("Daten-Stand: " + (f"Kurse {datum(kstand)} · " if kstand else "")
                     + f"ETF-Liste {datum(D['stand'])} · Monatsstatistik {etf_monat(D.get('statistik'))}")
            neu = datenstand_setzen(neu, zeile) or neu
        print(f"anleihen-etf.html: ETF-Zahl in {kacheln} Kacheln, Stand und Daten-Stand fest im HTML")
        return neu
    except Exception as e:
        warn(f"anleihen-etf.html: Kacheln und Stand nicht vorab geschrieben ({type(e).__name__}: {e})")
        return html_


def etfs(site):
    pfad = os.path.join(site, "anleihen-etf.html")
    html_ = open(pfad, encoding="utf-8").read()
    D = lade(site, "top10-anleihen-etfs.json")
    try:
        K = lade(site, "kurse-auswahl.json")
        kurse = K.get("kurse") or {}
        kstand = K.get("stand") if ist_datum(K.get("stand")) else ""   # wie KSTAND im Seitenskript
    except Exception:
        kurse, kstand = {}, ""
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
    html_ = etf_angaben(html_, D, kstand)   # nur zusammen mit den Tabellen: Zahlen und Stand gehören zusammen
    with open(pfad, "w", encoding="utf-8") as f:
        f.write(html_)
    print(f"anleihen-etf.html: {anzahl} ETFs in {gefuellt} Tabellen fest im HTML")


# ---------- Standardtabelle (seit 03.10.2026): gleiche Spalten, Reihenfolge und Schreibweisen wie MC.felder.tabelle (felder.js) ----------
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import (bonitaet_text, datum_text, felder_katalog, kupon_text, kurs_text, kurz_name, pct_text,  # noqa: E402
                     restlaufzeit_text, stueckelung_text, titel_text, volumen_text)

STD_REIHE = felder_katalog()["reihe"]   # Gesamtliste der Spalten – einmal im Katalog (felder.js)
STD_NUM = {"rendite", "kupon", "lfd", "restlaufzeit", "duration", "aufschlag", "kurs", "stueckelung", "volumen", "handelstage", "seitHoch", "seitMerken", "zinstermin"}
STD_GROSS = {"rendite", "kupon", "restlaufzeit"}
STD_CLS = {"platz": "rk", "merken": "merkspalte"}
ARTNR = {"Staat": 0, "Öffentlich": 1, "Unternehmen": 2}


def std_kopf(ids, sort=("platz", 1)):
    F = felder_katalog()["felder"]
    out = []
    for i in [x for x in STD_REIHE if x in ids]:
        f = F.get(i, {})
        kopf, unter = ("" if i == "merken" else f.get("kurz", "")), f.get("unter", "")
        cls = " ".join(x for x in ("num" if i in STD_NUM else "", STD_CLS.get(i, "")) if x)
        aria = f' aria-sort="{"ascending" if sort[1] > 0 else "descending"}"' if sort[0] == i else ""
        title = f' title="{esc(f["title"])}"' if f.get("title") and i != "merken" else ""
        klein = f"<small>{esc(unter)}</small>" if unter else ""   # zweite Kopfzeile unter dem Sortierknopf
        knopf = f'<button type="button" class="sortbtn" data-col="{i}">{esc(kopf)}</button>{klein}' if kopf else '<span class="sr-only">Merken</span>'
        out.append(f'<th scope="col" data-col="{i}" class="{cls}"{aria}{title}>{knopf}</th>')
    return "<thead><tr>" + "".join(out) + "</tr></thead>"


def std_zeile(o, ids, ctx, fett):
    ART = felder_katalog()["art"]
    F = felder_katalog()["felder"]
    heute = datetime.date.today()
    zellen = []
    for i in [x for x in STD_REIHE if x in ids]:
        h, sub, p = "–", "", ""
        if i == "platz":
            h = str(o.get("platz") or "")
        elif i == "anleihe":
            titel = titel_text(o["kurz"], o.get("kupon"), o.get("zinsart", 0), o.get("faellig") or "")
            reg = f'Registername: {o["reg"]}' if o.get("reg") else ""
            h = (f'<a class="name-link" href="anleihe.html?isin={esc(o["isin"])}" title="{esc(reg)}" aria-label="Steckbrief {esc(titel)}">'
                 f'{esc(o["kurz"])}</a>')
            sub = esc(" · ".join(x for x in (o["isin"], ART[o["art"]] if isinstance(o.get("art"), int) else "", o.get("ccy") or "") if x))
        elif i == "rendite":
            h = pct_text(o["rend"]) if isinstance(o.get("rend"), (int, float)) else '<span title="keine Rendite in den Kursdaten">–</span>'
        elif i == "kupon":
            h = kupon_text(o.get("kupon"), o.get("zinsart", 0))
        elif i == "restlaufzeit":
            if o.get("faellig"):
                h = restlaufzeit_text((datetime.date.fromisoformat(o["faellig"]) - heute).days / 365.25)
                sub, p = datum_text(o["faellig"]), "fällig"
            else:
                h = "unbefristet"
        elif i == "kurs":
            boerse = {"F": "Börse Frankfurt", "T": "Tradegate", "X": "Xetra", "B": "Deutsche Bundesbank"}.get(o.get("boerse") or "", "")
            t = f'Schlusskurs vom {datum_text(o["kdatum"])}' + (f", {boerse}" if boerse else "") if o.get("kdatum") else ""
            h = f'<span title="{esc(t)}">{kurs_text(o.get("kurs"))}</span>'
            if o.get("kdatum") and ctx.get("kstand") and o["kdatum"] != ctx["kstand"]:
                sub = "vom " + datum_text(o["kdatum"])[:6]
        elif i == "bonitaet":
            b = bonitaet_text(o.get("bon"))
            h = esc(b) if b else '<span title="nicht auf der EZB-Liste">–</span>'
        elif i == "stueckelung":
            h = stueckelung_text(o.get("stk"), o.get("ccy") or "")
        elif i == "volumen":
            h = volumen_text(o.get("vol"), o.get("ccy") or "")
        elif i == "handelstage":
            h = (f'<span title="Umsatz {esc(volumen_text(o.get("um"), o.get("ccy") or ""))}">{o["ht"]}' + (f' von {ctx["tage"]}' if ctx.get("tage") else "") + "</span>") if isinstance(o.get("ht"), int) else "–"
        elif i == "merken":
            h = ""
        cls = " ".join(x for x in ("num" if i in STD_NUM else "", STD_CLS.get(i, ""), "gross" if i in STD_GROSS else "", "sortiert" if fett == i else "") if x)
        klein = f'<small{f" data-p={chr(34)}{esc(p)}{chr(34)}" if p else ""}>{sub}</small>' if sub else ""
        if i == "anleihe":
            zellen.append(f'<th scope="row"{f" class={chr(34)}{cls}{chr(34)}" if cls else ""}>{h}{klein}</th>')
        else:
            kopf = "" if i == "merken" else F.get(i, {}).get("kurz", "")
            zellen.append(f'<td{f" class={chr(34)}{cls}{chr(34)}" if cls else ""}{f" data-l={chr(34)}{esc(kopf)}{chr(34)}" if kopf else ""}>{h}{klein}</td>')
    return f'<tr data-isin="{esc(o["isin"])}">' + "".join(zellen) + "</tr>"


def std_objekt(r, platz, kurse, aus, default=None):
    """Zeilenobjekt wie T10.zeilen (top10-tabellen.js): Kurs aus kurse-auswahl.json, sonst aus der Zeile; Name/Bonität aus der Zeile
    (automatische Rangliste) oder anleihen-auswahl.json (Handauswahl)."""
    default = default or {}
    k = (kurse.get("kurse") or {}).get(r["isin"])
    tage = kurse.get("tage") or []
    a = (aus.get("a") or {}).get(r["isin"]) or [None, None, None, None, ""]
    art_txt = r.get("art") or default.get("art")
    art = ARTNR.get(art_txt, a[1])
    kurs, kdatum = (k[0], tage[k[2]]) if k and isinstance(k[2], int) and k[2] < len(tage) else (r.get("kurs"), r.get("datum") or default.get("date"))
    rend = (k[1] if isinstance(k[1], (int, float)) else None) if k else r.get("rendite")
    return {"platz": platz, "isin": r["isin"], "kurz": r.get("kurz") or a[0] or kurz_name(r.get("emittent") or default.get("emittent") or "", art, None, r["isin"]),
            "reg": a[4] or "", "art": art, "ccy": r.get("cur") or default.get("cur") or a[2] or "", "kupon": r.get("kupon"),
            "zinsart": 2 if r.get("kupon") == 0 else 0, "faellig": r.get("faellig") or "", "kurs": kurs, "kdatum": kdatum,
            "boerse": k[3] if k else "", "rend": rend, "bon": r.get("bon", a[3]), "vol": r.get("vol"), "stk": r.get("stk"),
            "ht": r.get("ht"), "um": r.get("um")}


def std_tabelle(zeilen, kstand, tage=0, rang=None):
    """(thead, tbody-Inhalt) der Ranglisten-Tabelle – wie T10.tabelle: Handelstage nur, wenn jede Zeile sie hat."""
    ids = ["platz", "anleihe", "rendite", "kupon", "restlaufzeit", "kurs", "bonitaet", "stueckelung", "volumen", "merken"]
    if zeilen and all(isinstance(o.get("ht"), int) for o in zeilen):
        ids.append("handelstage")
        rang = rang or "handelstage"
    ctx = {"kstand": kstand, "tage": tage}
    return std_kopf(ids), "".join(std_zeile(o, ids, ctx, rang) for o in zeilen)


def js_objekte(text):
    """JS-Objektliteral der Handauswahl ({ isin: "…", kupon: 2, … }) → Python-Listen; Schlüssel ohne Anführungszeichen."""
    return json.loads(re.sub(r'([{,]\s*)([A-Za-z_]\w*)\s*:', r'\1"\2":', text))


def ersetze_tabelle(html_, auswahl_re, thead, tbody):
    """In der Tabelle, deren Anfang auswahl_re trifft, Kopf und Rumpf ersetzen (Rumpf: erstes <tbody …>…</tbody>)."""
    m = re.search(auswahl_re, html_)
    if not m:
        return html_, False
    ende = html_.index("</table>", m.end())
    block = html_[m.start():ende]
    block2 = re.sub(r"<thead[^>]*>.*?</thead>", lambda _: thead.replace("<thead>", '<thead class="std-kopf">', 1), block, count=1, flags=re.S)
    block2 = re.sub(r"(<tbody[^>]*>).*?(</tbody>)", lambda x: x.group(1) + tbody + x.group(2), block2, count=1, flags=re.S)
    if 'class="kpis atab"' not in block2:
        block2 = block2.replace('class="kpis"', 'class="kpis atab"', 1)
    return html_[:m.start()] + block2 + html_[ende:], True


def laufzeit(site, seite, datei):
    """Laufzeit-Seiten: fünf Tabellen – automatische Rangliste, wenn „aktiv“, sonst die Handauswahl aus dem Seitenskript."""
    pfad = os.path.join(site, seite)
    html_ = open(pfad, encoding="utf-8").read()
    D, kurse, aus = lade(site, datei), lade(site, "kurse-auswahl.json"), lade(site, "anleihen-auswahl.json")
    aktiv = bool(D.get("aktiv") and D.get("gruppen") and D.get("fenster"))
    if aktiv:
        gruppen, tage, stand = D["gruppen"], D["fenster"].get("tage") or 0, D.get("stand")
    else:
        m = re.search(r"const ANLEIHEN = \{\s*date: \"([0-9-]+)\",\s*gruppen: (\{.*?\n  \})\n\};", html_, re.S)
        if not m:
            return warn(f"{seite}: Handauswahl ANLEIHEN nicht gefunden – nichts vorab geschrieben")
        stand, gruppen, tage = m.group(1), js_objekte(re.sub(r",(\s*[\]}])", r"\1", m.group(2))), 0
    n = 0
    for key, reihe in gruppen.items():
        objs = [std_objekt(r, i + 1, kurse, aus, {"date": stand}) for i, r in enumerate(reihe)]
        thead, tbody = std_tabelle(objs, kurse.get("stand") or stand, tage)
        html_, ok = ersetze_tabelle(html_, r'<table class="kpis(?: atab)?" data-gruppe="' + re.escape(key) + '">', thead, tbody)
        n += len(objs) if ok else 0
    kstand = kurse.get("stand") or stand
    if n and ist_datum(kstand):   # „Daten-Stand“ wie T10.datenstand() im Browser – nur zusammen mit den Zeilen (SEO-Runde 2)
        html_ = datenstand_setzen(html_, "Daten-Stand: " + datum(kstand)) or html_
    with open(pfad, "w", encoding="utf-8") as f:
        f.write(html_)
    print(f"{seite}: {n} Anleihen in fünf Tabellen fest im HTML ({'automatische Rangliste' if aktiv else 'Handauswahl'})")


def laender(site, seite, datei):
    """Länder-Seiten: Startansicht Deutschland – automatische Rangliste, wenn „aktiv“, sonst die Handauswahl aus dem Seitenskript."""
    pfad = os.path.join(site, seite)
    html_ = open(pfad, encoding="utf-8").read()
    D, kurse, aus = lade(site, datei), lade(site, "kurse-auswahl.json"), lade(site, "anleihen-auswahl.json")
    if D.get("aktiv") and D.get("gruppen") and D.get("fenster"):
        reihe, tage, default = D["gruppen"].get("deutschland") or [], D["fenster"].get("tage") or 0, {"date": D.get("stand")}
    else:
        m = re.search(r"\n\s*deutschland: \{(.*?)rows: (\[.*?\])\s*\}", html_, re.S)
        if not m:
            return warn(f"{seite}: Handauswahl „deutschland“ nicht gefunden – nichts vorab geschrieben")
        kopf = m.group(1)
        default = {k: (re.search(k + r': "([^"]*)"', kopf) or [None, None])[1] for k in ("emittent", "art", "cur", "date")}
        reihe, tage = js_objekte(re.sub(r",(\s*[\]}])", r"\1", m.group(2))), 0
    objs = [std_objekt(r, i + 1, kurse, aus, default) for i, r in enumerate(reihe)]
    if not objs:
        return warn(f"{seite}: keine Zeilen für Deutschland – nichts vorab geschrieben")
    thead, tbody = std_tabelle(objs, kurse.get("stand") or default.get("date"), tage)
    html_, ok = ersetze_tabelle(html_, r'<table class="kpis(?: atab)?" id="kpis">', thead, tbody)
    if not ok:
        return warn(f"{seite}: Tabelle #kpis nicht gefunden – nichts vorab geschrieben")
    kstand = kurse.get("stand") or default.get("date")
    if ist_datum(kstand):   # „Daten-Stand“ wie T10.datenstand() im Browser (SEO-Runde 2)
        html_ = datenstand_setzen(html_, "Daten-Stand: " + datum(kstand)) or html_
    with open(pfad, "w", encoding="utf-8") as f:
        f.write(html_)
    print(f"{seite}: {len(objs)} Anleihen (Deutschland) fest im HTML")


def kupon(site, seite="anleihen-kupon.html", datei="top10-anleihen-kupon.json"):
    """Top 30 nach Kupon (seit 01.10.2026), drei Tabellen: dieselben Zeilen wie das Seitenskript, Kupon fett (danach ist gerankt)."""
    pfad = os.path.join(site, seite)
    D, kurse, aus = lade(site, datei), {}, {}
    html_ = open(pfad, encoding="utf-8").read()
    geschrieben = []
    for key in ("staat", "oeffentlich", "unternehmen"):
        reihe = (D.get("gruppen") or {}).get(key) or []
        if not reihe:
            warn(f"{seite}: Gruppe „{key}“ fehlt – nichts vorab geschrieben")
            continue
        objs = [std_objekt(r, i + 1, kurse, aus, {"date": D.get("stand")}) for i, r in enumerate(reihe)]
        thead, tbody = std_tabelle(objs, D.get("stand"), 0, "kupon")
        html_, ok = ersetze_tabelle(html_, r'<table class="kpis(?: atab)?" data-gruppe="' + key + '">', thead, tbody)
        if ok:
            geschrieben.append(f"{len(objs)} {key}")
    if geschrieben:
        # „Daten-Stand“ wie das Seitenskript – nur zusammen mit den Zeilen (SEO-Runde 2)
        if ist_datum(D.get("stand")):
            ezb = (D.get("ezb") or {}).get("stand") if isinstance(D.get("ezb"), dict) else None
            html_ = datenstand_setzen(html_, "Daten-Stand: Kurse vom " + datum(D["stand"]) + (", EZB-Liste vom " + datum(ezb) if ezb else "")) or html_
        with open(pfad, "w", encoding="utf-8") as f:
            f.write(html_)
        print(f"{seite}: {', '.join(geschrieben)} fest im HTML")


def startseite(site, seite="index.html"):
    """„Sechs Beispiele“ (Standardtabelle seit 03.10.2026): In den Zeilen der Quell-HTML Rendite, Kurs und Restlaufzeit aus
    kurse-auswahl.json, „Kurse und Renditen vom“ dessen Stand und dieselbe Rendite in der Hero-Karte. Die übrigen Zellen (Kupon
    mit Zinstermin, Bonität, Stückelung) bleiben, wie sie sind. Fehlt eine Anleihe in den Kursen oder passt eine Zelle nicht,
    bleibt die Seite unverändert – Zahlen und Datum gehören zusammen (SEO-Runde 2)."""
    pfad = os.path.join(site, seite)
    K = lade(site, "kurse-auswahl.json")
    kurse, tage, stand = K.get("kurse") or {}, K.get("tage") or [], K.get("stand")
    if not ist_datum(stand):
        return warn(f"{seite}: kurse-auswahl.json ohne gültigen Stand – Seite bleibt unverändert")
    html_ = open(pfad, encoding="utf-8").read()
    tab = re.search(r'(<table class="itab(?: atab)?">(?:(?!</table>).)*?<tbody>)((?:(?!</table>).)*?)(</tbody>)', html_, re.S)
    if not tab:
        return warn(f"{seite}: Tabelle .itab nicht gefunden – Seite bleibt unverändert")
    heute, fehler = datetime.date.today(), []

    def zelle(tr, name, inhalt):
        muster = re.compile(r'(<td class="[^"]*" data-l="' + name + r'">)(?:(?!</td>).)*(</td>)', re.S)
        if len(muster.findall(tr)) != 1:
            fehler.append(f"Zelle {name}")
            return tr
        return muster.sub(lambda m: m.group(1) + inhalt + m.group(2), tr, count=1)

    def zeile(m):
        isin, tr = m.group(1), m.group(0)
        k = kurse.get(isin)
        if not (isinstance(k, list) and len(k) > 3 and ist_zahl(k[0]) and isinstance(k[2], int) and k[2] < len(tage)):
            fehler.append(isin)
            return tr
        kdatum = tage[k[2]]
        boerse = {"F": "Börse Frankfurt", "T": "Tradegate", "X": "Xetra", "B": "Deutsche Bundesbank"}.get(k[3] or "", "")
        titel = f"Schlusskurs vom {datum_text(kdatum)}" + (f", {boerse}" if boerse else "")
        tr = zelle(tr, "Rendite", pct_text(k[1]) if ist_zahl(k[1]) else '<span title="keine Rendite in den Kursdaten">–</span>')
        tr = zelle(tr, "Kurs", f'<span title="{esc(titel)}">{kurs_text(k[0])}</span>' + (f"<small>vom {datum_text(kdatum)[:6]}</small>" if kdatum != stand else ""))
        f = re.search(r'<small data-p="fällig">(\d{2})\.(\d{2})\.(\d{4})</small>', tr)
        if f:
            faellig = datetime.date(int(f.group(3)), int(f.group(2)), int(f.group(1)))
            tr = zelle(tr, "Restlaufzeit", restlaufzeit_text((faellig - heute).days / 365.25) + f.group(0))
        return tr

    body, n = re.subn(r'<tr(?: class="[^"]*")? data-isin="([A-Z]{2}[A-Z0-9]{9}[0-9])">.*?</tr>', zeile, tab.group(2), flags=re.S)
    if fehler or not n:
        return warn(f"{seite}: Tageskurs oder Zelle fehlt ({', '.join(fehler) or 'keine Zeile'}) – Seite bleibt unverändert")
    neu = html_[:tab.start(2)] + body + html_[tab.end(2):]
    neu, gesetzt = re.subn(r'(<span id="itab-stand">)[^<]*(</span>)', lambda m: m.group(1) + datum(stand) + m.group(2), neu, count=1)
    if not gesetzt:
        return warn(f"{seite}: „Kurse und Renditen vom“ (#itab-stand) nicht gefunden – Seite bleibt unverändert")
    # Hero-Karte: zeigt ohne Skript die Rückfall-Anleihe – dieselbe Rendite wie in den Kursen
    hero = re.search(r'<a class="hero-karte" href="anleihe\.html\?isin=([A-Z]{2}[A-Z0-9]{9}[0-9])"', neu)
    k = kurse.get(hero.group(1)) if hero else None
    if isinstance(k, list) and len(k) > 1 and ist_zahl(k[1]):
        neu = re.sub(r'(<span class="hk-z" id="hk-rend">)[^<]*(</span>)', lambda m: m.group(1) + pct_text(k[1]) + m.group(2), neu, count=1)
    with open(pfad, "w", encoding="utf-8") as f:
        f.write(neu)
    print(f"{seite}: {n} Beispiele mit Rendite, Kurs und Restlaufzeit vom {datum(stand)}")


def main():
    site = sys.argv[1] if len(sys.argv) > 1 else "_site"
    if not os.path.isdir(site):
        raise SystemExit(f"Ordner nicht gefunden: {site}")
    for name, schritt in (("Broker", lambda: broker(site)), ("ETFs", lambda: etfs(site)),
                          ("Staatsanleihen nach Laufzeit", lambda: laufzeit(site, "staatsanleihen-laufzeit.html", "top10-staatsanleihen-laufzeit.json")),
                          ("Unternehmensanleihen nach Laufzeit", lambda: laufzeit(site, "unternehmensanleihen-laufzeit.html", "top10-unternehmensanleihen-laufzeit.json")),
                          ("Staatsanleihen nach Ländern", lambda: laender(site, "anleihen-laender.html", "top10-staatsanleihen-laender.json")),
                          ("Unternehmensanleihen nach Ländern", lambda: laender(site, "unternehmensanleihen-laender.html", "top10-unternehmensanleihen-laender.json")),
                          ("Anleihen nach Kupon", lambda: kupon(site)),
                          ("Startseite", lambda: startseite(site))):
        try:
            schritt()
        except Exception as e:   # Daten oder Seite anders als erwartet: Seite bleibt, wie sie ist
            warn(f"{name}: nicht vorab geschrieben ({type(e).__name__}: {e})")


if __name__ == "__main__":
    main()
