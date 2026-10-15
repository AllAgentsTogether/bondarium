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

  index.html              „Was gerade viel gehandelt wird“ (table.itab) und Hero-Karte ← seit 15.10.2026 dieselbe Liste wie die vier
                                                             Top-10-Seiten (Handauswahl der Seite bzw. automatische Liste, wenn
                                                             „aktiv“) als JSON in #top10-pool, dazu sechs Zeilen und die Karte der
                                                             Bau-Stunde (Rückfall: feste Zeilen mit Tageskursen, seit 03.10.2026);
                          Zinsstand-Band (.zs-band)        ← zinskurve.json, langlaeufer.json, ezb.json: Werte, Veränderung, „Stand“
                                                             (seit 15.10.2026; vorher erst im Browser)
  staatsanleihen-laufzeit.html usw. bei „aktiv“           ← AKTIV_TEXTE der Seite, Elemente „nur-hand“ entfernt (seit 15.10.2026)

  bundeswertpapiere.html  <!--BUNDESLISTE-->…<!--/BUNDESLISTE-->
                                                           ← alle laufenden Bundeswertpapiere mit Kurs und Rendite der Deutschen
                                                             Bundesbank (kurse/bund/<ISIN>.json) und Stammdaten aus dem
                                                             ESMA-Register (anleihen/); dazu die Zeilen als JSON (#bl-daten) für
                                                             das Sortieren im Browser (seit 04.10.2026, SEO-Runde 2). Lokal:
                                                             python3 scripts/statische_tabellen.py . bundeswertpapiere

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


def datenstand_setzen(html_, text, stale=None):
    """<p id="datastand">Daten-Stand: …</p> auf text setzen; None, wenn die Zeile fehlt (dann bleibt die Seite, wie sie ist).
    stale True/False setzt bzw. entfernt die Klasse „stale“ (rote Schrift, base.css; seit 09.10.2026), None lässt den Tag,
    wie er ist."""
    muster = re.compile(r'(<p id="datastand")(?: class="([^"]*)")?(>)Daten-Stand:[^<]*(</p>)')
    if not muster.search(html_):
        return None

    def ersatz(m):
        klassen = [k for k in (m.group(2) or "").split() if stale is None or k != "stale"] + (["stale"] if stale else [])
        return m.group(1) + (f' class="{" ".join(klassen)}"' if klassen else "") + m.group(3) + esc_js(text) + m.group(4)
    return muster.sub(ersatz, html_, count=1)


# „veraltet“ wie MC.veraltet (site.js, MC.STALE_TAGE): ab 5 Börsentagen (Mo–Fr) nach dem Datum bis heute einschließlich;
# „heute“ in deutscher Zeit wie beim Besucher (rueckfallwerte.py rechnet ebenso)
STALE_TAGE = 5
try:
    from zoneinfo import ZoneInfo
    BERLIN = ZoneInfo("Europe/Berlin")
except Exception:   # ohne Zeitzonendaten gilt UTC
    BERLIN = None


def veraltet(iso):
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", str(iso or ""))
    if not m:
        return False
    d, n = datetime.date(int(m.group(1)), int(m.group(2)), int(m.group(3))), 0
    ende = datetime.datetime.now(BERLIN or datetime.timezone.utc).date()
    while d < ende:
        d += datetime.timedelta(days=1)
        if d.weekday() < 5:
            n += 1
    return n >= STALE_TAGE


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
                     restlaufzeit_text, stueckelung_text, titel_text, volumen_text, NBSP)

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
            vor = ctx["nameVor"](o) if callable(ctx.get("nameVor")) else ""   # z. B. Farbpunkt der Linie (langlaeufer.html)
            h = (f'{vor}<a class="name-link" href="anleihe.html?isin={esc(o["isin"])}" title="{esc(reg)}" aria-label="Steckbrief {esc(titel)}">'
                 f'{esc(o["kurz"])}</a>')
            sub = esc(" · ".join(x for x in (o["isin"], ART[o["art"]] if isinstance(o.get("art"), int) else "", o.get("ccy") or "") if x))
        elif i == "rendite":
            h = (pct_text(o["rend"]) + ('<span title="Realrendite (inflationsindexiert)">*</span>' if o.get("real") else "")
                 if isinstance(o.get("rend"), (int, float)) else f'<span title="{esc(o.get("rendGrund") or "keine Rendite in den Kursdaten")}">–</span>')
        elif i == "kupon":
            h = kupon_text(o.get("kupon"), o.get("zinsart", 0))
            if callable(ctx.get("kuponZeile")):   # Zinstermin unter dem Kupon (Startseite, wie ctx.kuponZeile in felder.js)
                sub, p = esc(ctx["kuponZeile"](o)), "Zinsen"
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
        elif i == "seitHoch":
            h = "–" if not isinstance(o.get("seitHoch"), (int, float)) else zahl(o["seitHoch"], 0) + NBSP + "%"
            sub = o.get("hochText") or ""
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


# ---------- Texte bei automatischer Rangliste („aktiv“, seit 15.10.2026, Gesamtprüfung B05-01) ----------
# Mit „aktiv“ ersetzt das Seitenskript die Texte zur Handauswahl: AKTIV_TEXTE der Seite (id → neuer Inhalt, {zeit} usw.) und die
# Elemente mit der Klasse „nur-hand“ (Übergangshinweis, Notizen zur Handauswahl). Dieselben Änderungen schreibt dieses Skript ins
# ausgelieferte HTML – vorher lasen Crawler und KI „Übergangsweise … Auswahl vom 22.09.2026“, „Gezählt wird der Handel an der Börse
# Stuttgart“ und „umlaufender Betrag, Stand 23.09.2026“ neben der automatischen Liste. Die Texte stehen nur in der Seite.
ZAHL = ["keine", "eine", "zwei", "drei", "vier", "fünf", "sechs", "sieben", "acht", "neun", "zehn"]
ZAHL_GROSS = ["Keine", "Ein", "Zwei", "Drei", "Vier", "Fünf", "Sechs", "Sieben", "Acht", "Neun", "Zehn"]


def aktiv_texte(html_):
    """AKTIV_TEXTE aus dem Seitenskript (gültiges JSON) oder None."""
    m = re.search(r"const AKTIV_TEXTE = (\{.*?\n\});", html_, re.S)
    return json.loads(m.group(1)) if m else None


def zeitraum(fenster):
    """wie im Seitenskript: volles Fenster (60 Börsentage) = „in den letzten drei Monaten“"""
    tage = fenster.get("tage") or 0
    return "in den letzten drei Monaten" if tage >= (fenster.get("soll") or 0) else f"in den letzten {tage} Börsentagen"


def inhalt_setzen(html_, id_, inhalt):
    """Inhalt des Elements (p, span, h2) mit dieser id ersetzen; (html, Anzahl)."""
    muster = re.compile(r'(<(p|span|h2)\b[^>]*\bid="' + re.escape(id_) + r'"[^>]*>).*?(</\2>)', re.S)
    return muster.subn(lambda m: m.group(1) + inhalt + m.group(3), html_, count=1)


def zahlwort(text, n, ohne):
    """„die zehn meistgehandelten“ → Zahl n (wie T10 im Browser); n = 0 → ohne"""
    return re.sub(r"die (?:zehn|neun|acht|sieben|sechs|fünf|vier|drei|zwei|eine|\d+) meistgehandelten",
                  lambda _: f"die {ZAHL[n] if n <= 10 else n} meistgehandelten" if n else ohne, text, count=1)


def aktiv_anwenden(html_, seite, fenster, mehr=None):
    """AKTIV_TEXTE einsetzen und die Elemente mit „nur-hand“ entfernen – wie aktiv() im Browser."""
    texte = aktiv_texte(html_)
    if texte is None:
        warn(f"{seite}: AKTIV_TEXTE nicht gefunden – Texte zur Handauswahl bleiben im HTML")
        return html_
    werte = {"zeit": zeitraum(fenster)}
    werte.update(mehr or {})
    fehlt, n = [], 0
    for id_, text in texte.items():
        if id_.startswith("_"):   # Baustein, kein Element
            continue
        html_, k = inhalt_setzen(html_, id_, re.sub(r"\{(\w+)\}", lambda m: str(werte.get(m.group(1), m.group(0))), text))
        n += k
        if not k:
            fehlt.append(id_)
    html_, weg = re.subn(r'[ \t]*<p\b[^>]*\bclass="[^"]*\bnur-hand\b[^"]*"[^>]*>.*?</p>\n?', "", html_, flags=re.S)
    if fehlt:
        warn(f"{seite}: Element(e) {', '.join(fehlt)} aus AKTIV_TEXTE nicht gefunden")
    print(f"{seite}: automatische Rangliste – {n} Texte gesetzt, {weg} Hinweise zur Handauswahl entfernt")
    return html_


def laufzeit(site, seite, datei):
    """Laufzeit-Seiten: fünf Tabellen – automatische Rangliste, wenn „aktiv“, sonst die Handauswahl aus dem Seitenskript."""
    pfad = os.path.join(site, seite)
    html_ = open(pfad, encoding="utf-8").read()
    D, kurse, aus = lade(site, datei), lade(site, "kurse-auswahl.json"), lade(site, "anleihen-auswahl.json")
    aktiv = bool(D.get("aktiv") and D.get("gruppen") and D.get("fenster"))
    if aktiv:   # die Gruppen der Seite; fehlt eine in der Datei, bleibt ihre Tabelle leer wie im Browser
        tage, stand = D["fenster"].get("tage") or 0, D.get("stand")
        gruppen = {g: D["gruppen"].get(g) or [] for g in re.findall(r'<table class="kpis(?: atab)?" data-gruppe="([^"]+)"', html_)}
    else:
        m = re.search(r"const ANLEIHEN = \{\s*date: \"([0-9-]+)\",\s*gruppen: (\{.*?\n  \})\n\};", html_, re.S)
        if not m:
            return warn(f"{seite}: Handauswahl ANLEIHEN nicht gefunden – nichts vorab geschrieben")
        stand, gruppen, tage = m.group(1), js_objekte(re.sub(r",(\s*[\]}])", r"\1", m.group(2))), 0
    n = 0
    for key, reihe in gruppen.items():
        objs = [std_objekt(r, i + 1, kurse, aus, {"date": stand}) for i, r in enumerate(reihe)]
        thead, tbody = std_tabelle(objs, kurse.get("stand") or stand, tage)
        if not objs:   # wie MC.felder.tabelle mit „leer“ (top10-tabellen.js)
            spalten = thead.count("<th ")
            tbody = (f'<tr><td class="leer" colspan="{spalten}">In den letzten {tage} Börsentagen wurde keine Anleihe dieser Gruppe an der '
                     'Börse Frankfurt oder bei Tradegate gehandelt.</td></tr>')
        html_, ok = ersetze_tabelle(html_, r'<table class="kpis(?: atab)?" data-gruppe="' + re.escape(key) + '">', thead, tbody)
        n += len(objs) if ok else 0
        if ok and aktiv:   # Tabellenbeschriftung wie im Browser: „die neun meistgehandelten“ bzw. „keine gehandelten“
            html_ = re.sub(r'(<table class="kpis(?: atab)?" data-gruppe="' + re.escape(key) + r'">\s*<caption[^>]*>)([^<]*)',
                           lambda m: m.group(1) + zahlwort(m.group(2), len(objs), "keine gehandelten"), html_, count=1)
    if aktiv:
        html_ = aktiv_anwenden(html_, seite, D["fenster"])
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
    aktiv = bool(D.get("aktiv") and D.get("gruppen") and D.get("fenster"))
    if aktiv:
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
    if aktiv:
        html_ = laender_aktiv(html_, seite, D, len(objs))
    with open(pfad, "w", encoding="utf-8") as f:
        f.write(html_)
    print(f"{seite}: {len(objs)} Anleihen (Deutschland) fest im HTML")


def laender_aktiv(html_, seite, D, n_de):
    """Länder-Seite mit „aktiv“ wie T10.laender im Browser (seit 15.10.2026, B05-01): Länder ohne Anleihe verlieren ihren Knopf,
    die Länderzahl (data-anzahl-laender) folgt, die Notiz unter der Tabelle ist nur noch der gemeinsame Hinweis (noteCommon),
    der Titel nennt die Zahl der Anleihen Deutschlands, dazu AKTIV_TEXTE und „nur-hand“."""
    namen = re.findall(r'^  ([a-z]+): \{\s*name: "([^"]+)"', html_, re.M)   # LAENDER in Reihenfolge der Seite
    if not namen:
        warn(f"{seite}: LAENDER nicht gefunden – Länderknöpfe und Länderzahl bleiben")
    mit = [(k, n) for k, n in namen if D["gruppen"].get(k)]
    ohne = [(k, n) for k, n in namen if not D["gruppen"].get(k)]
    if namen:
        for k, _ in ohne:
            html_ = re.sub(r'\s*<button type="button" class="lbtn" data-land="' + re.escape(k) + r'"[^>]*>[^<]*</button>', "", html_, count=1)
        z = len(mit)
        html_ = re.sub(r'(<span data-anzahl-laender(?:="([a-z]*)")?>)[^<]*(</span>)',
                       lambda m: m.group(1) + ((ZAHL_GROSS[z] if z <= 10 else str(z)) if m.group(2) == "gross" else (ZAHL[z] if z <= 10 else str(z))) + m.group(3), html_)
    hinweis = re.search(r'noteCommon: ("(?:[^"\\]|\\.)*")', html_)
    if hinweis:
        html_, _ = inhalt_setzen(html_, "land-note", esc_js(json.loads(hinweis.group(1))))
    else:
        warn(f"{seite}: noteCommon nicht gefunden – Notiz unter der Tabelle bleibt")
    html_ = re.sub(r'(<h2 id="land-titel"[^>]*>)([^<]*)', lambda m: m.group(1) + zahlwort(m.group(2), n_de, "zurzeit keine gehandelten"), html_, count=1)
    texte = aktiv_texte(html_) or {}
    mehr = {"namen": ", ".join(n for _, n in mit),
            "weg": texte.get("_weg", "").replace("{liste}", ", ".join(n for _, n in ohne)) if ohne else ""}
    return aktiv_anwenden(html_, seite, D["fenster"], mehr)


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


# ---------- Startseite: Liste „Top 10 meistgehandelt“ wie auf den Top-10-Seiten (seit 15.10.2026, Gesamtprüfung B01-21, B01-03) ----------
# Tabelle „Was gerade viel gehandelt wird“ und Hero-Karte wählten bis 14.10.2026 aus den automatischen Ranglisten (top10-*.json), auch
# solange sie noch nicht „aktiv“ waren – die Top-10-Seiten zeigten dagegen ihre Handauswahl (209 von 324 ISINs der Startseite standen
# auf keiner Top-10-Seite). Jetzt dieselbe Quelle wie jede Top-10-Seite: ist ihre Datei „aktiv“, die automatische Liste, sonst die
# Handauswahl der Seite (Länder ohne Handauswahl – auto – wie auf der Länderseite aus der Datei). Kurs, Rendite und Kursdatum wie
# T10.zeilen aus kurse-auswahl.json; nur Anleihen mit Kurs und Rendite (wie bisher im Seitenskript). Die Liste steht als JSON in
# <script type="application/json" id="top10-pool"> – das Seitenskript zieht daraus stündlich sechs Zeilen und die Hero-Karte;
# die sechs Zeilen und die Karte der Bau-Stunde stehen mit derselben Zufallsregel fest im HTML.
TOP10_QUELLEN = (("staatsanleihen-laufzeit.html", "top10-staatsanleihen-laufzeit.json", "staat"),
                 ("anleihen-laender.html", "top10-staatsanleihen-laender.json", "staat"),
                 ("unternehmensanleihen-laufzeit.html", "top10-unternehmensanleihen-laufzeit.json", "unternehmen"),
                 ("unternehmensanleihen-laender.html", "top10-unternehmensanleihen-laender.json", "unternehmen"))
POOL_RE = re.compile(r'(<script type="application/json" id="top10-pool">)(.*?)(</script>)', re.S)


def handauswahl(html_):
    """[(Zeile, Vorgaben), …] der Handauswahl einer Top-10-Seite und die Schlüssel der Länder ohne Handauswahl (auto)."""
    m = re.search(r"const ANLEIHEN = \{\s*date: \"([0-9-]+)\",\s*gruppen: (\{.*?\n  \})\n\};", html_, re.S)
    if m:   # Laufzeit-Seite
        gruppen = js_objekte(re.sub(r",(\s*[\]}])", r"\1", m.group(2)))
        return [(r, {"date": m.group(1)}) for reihe in gruppen.values() for r in reihe], []
    m = re.search(r"const LAENDER = (\{.*?\n\});", html_, re.S)
    if not m:
        raise ValueError("weder ANLEIHEN noch LAENDER im Seitenskript")
    laender = js_objekte(re.sub(r",(\s*[\]}])", r"\1", m.group(1)))
    zeilen = [(r, {k: c.get(k) for k in ("emittent", "art", "cur", "date")}) for c in laender.values() if not c.get("auto") for r in c.get("rows") or []]
    return zeilen, [k for k, c in laender.items() if c.get("auto")]


def pool_zeile(r, vorgabe, kurse, aus, termine):
    """Zeile für die Startseite (Felder wie in top10-*.json) – Kurs und Rendite wie T10.zeilen; None ohne Kurs oder Rendite."""
    k = (kurse.get("kurse") or {}).get(r["isin"])
    tage = kurse.get("tage") or []
    if k and isinstance(k[2], int) and k[2] < len(tage):
        kurs, kdatum, rend = k[0], tage[k[2]], k[1]
    else:
        kurs, kdatum, rend = r.get("kurs"), r.get("datum") or vorgabe.get("date"), r.get("rendite")
    if not (ist_zahl(kurs) and ist_zahl(rend) and r.get("faellig")):
        return None
    a = (aus.get("a") or {}).get(r["isin"]) or [None, None, None, None, ""]
    art = r.get("art") or vorgabe.get("art") or {0: "Staat", 1: "Öffentlich", 2: "Unternehmen"}.get(a[1], "Staat")
    emittent = r.get("emittent") or vorgabe.get("emittent") or ""
    z = {"isin": r["isin"], "kurz": r.get("kurz") or a[0] or kurz_name(emittent, ARTNR.get(art), None, r["isin"]), "emittent": emittent,
         "art": art, "cur": r.get("cur") or vorgabe.get("cur") or a[2] or "", "kupon": r.get("kupon"), "zins": r.get("zins") or 1,
         "faellig": r["faellig"], "kurs": kurs, "datum": kdatum, "rendite": rend, "bon": r["bon"] if "bon" in r else a[3],
         "stk": r.get("stk"), "vol": r.get("vol"), "reg": a[4] or ""}
    zt = r.get("zt")
    e = termine.get(r["isin"])
    if not zt and e and len(e) > 1:   # Zinstage laut Börsenliste (die Handauswahl kennt nur die Zahl der Zahlungen)
        z["zins"], zt = e[0], e[1:]
    if zt:
        z["zt"] = zt
    return z


def top10_pool(site, kurse, aus):
    """{"stand", "staat": […], "unternehmen": […]} – je Art die Anleihen aller Top-10-Seiten, nach ISIN sortiert."""
    from _common import zinstermine_laden
    termine = zinstermine_laden()
    pool, quellen = {"staat": {}, "unternehmen": {}}, []
    for seite, datei, art in TOP10_QUELLEN:
        D = lade(site, datei)
        if D.get("aktiv") and D.get("gruppen") and D.get("fenster"):
            zeilen = [(r, {"date": D.get("stand")}) for reihe in D["gruppen"].values() for r in reihe]
            quellen.append(f"{seite} automatisch")
        else:
            zeilen, auto = handauswahl(open(os.path.join(site, seite), encoding="utf-8").read())
            if D.get("gruppen") and D.get("fenster"):   # Länder ohne Handauswahl zeigt die Seite schon vor „aktiv“ aus der Datei
                zeilen += [(r, {"date": D.get("stand")}) for k in auto for r in D["gruppen"].get(k) or []]
            quellen.append(f"{seite} Handauswahl")
        for r, vorgabe in zeilen:
            z = pool_zeile(r, vorgabe, kurse, aus, termine)
            if z:
                pool[art][z["isin"]] = z
    stand = kurse.get("stand") if ist_datum(kurse.get("stand")) else max((z["datum"] for t in pool.values() for z in t.values()), default="")
    return {"stand": stand, "staat": [pool["staat"][i] for i in sorted(pool["staat"])],
            "unternehmen": [pool["unternehmen"][i] for i in sorted(pool["unternehmen"])]}, quellen


def xorshift(seed):
    """Zufallszahlen wie zufall() im Seitenskript (xorshift32, Startwert aus der Stundennummer)."""
    t = ((seed ^ 0x9E3779B9) & 0xFFFFFFFF) or 1

    def rnd():
        nonlocal t
        t = (t ^ (t << 13)) & 0xFFFFFFFF
        t ^= t >> 17
        t = (t ^ (t << 5)) & 0xFFFFFFFF
        return t / 4294967296
    return rnd


def ziehe(liste, n, rnd):
    """wie ziehe() im Seitenskript: mischen, erst verschiedene Emittenten, dann auffüllen"""
    a = list(liste)
    for i in range(len(a) - 1, 0, -1):
        j = math.floor(rnd() * (i + 1))
        a[i], a[j] = a[j], a[i]
    wahl, em = [], set()
    for x in a:
        e = x.get("kurz") or x.get("emittent")
        if len(wahl) < n and e not in em:
            em.add(e)
            wahl.append(x)
    for x in a:
        if len(wahl) < n and x not in wahl:
            wahl.append(x)
    return wahl


def zt_termine(x):
    return sorted(((int(md[3:5]), int(md[:2])) for md in x.get("zt") or []), key=lambda p: (p[1], p[0]))


def zt_text(x):
    """Zinstermin unter dem Kupon wie ZT.text im Seitenskript"""
    if not (ist_zahl(x.get("kupon")) and x["kupon"] > 0):
        return "kein Zinstermin"
    l = [f"{t:02d}.{m:02d}." for t, m in zt_termine(x)]
    if not l:
        return ""
    return ("monatlich" if x.get("zins") == 12 else "vierteljährlich") if len(l) > 2 else " · ".join(l) if len(l) > 1 else "am " + l[0]


def zt_karte(x, heute):
    """Kalenderblatt der Hero-Karte wie ZT.karte im Seitenskript"""
    mon = ["Jan", "Feb", "Mär", "Apr", "Mai", "Jun", "Jul", "Aug", "Sep", "Okt", "Nov", "Dez"]
    kupon_ = x.get("kupon")
    if not (ist_zahl(kupon_) and kupon_ > 0):
        return ('<span class="hk-ztt"><b>Nullkupon: keine laufenden Zinsen</b>'
                + (f"<span>Ertrag aus dem Kurs unter 100{NBSP}%</span>" if ist_zahl(x.get("kurs")) and x["kurs"] < 100 else "") + "</span>")
    l = zt_termine(x)
    if not l:
        return f'<span class="hk-ztt"><b>Kupon {zahl(kupon_, 3 if round(kupon_ * 1000) % 10 else 2)}{NBSP}%</b></span>'
    naechster = None
    for j in (heute.year, heute.year + 1):
        for t, m in l:
            try:
                d = datetime.date(j, m, t)
            except ValueError:
                continue
            if d >= heute and (naechster is None or d < naechster):
                naechster = d
    zins = x.get("zins") or 1
    s = esc_js({"EUR": "€", "USD": "$", "GBP": "£"}.get(x.get("cur"), x.get("cur") or ""))
    je = math.floor(kupon_ * 1000 / zins + 0.5) / 100
    betrag = f"{zahl(je, 2 if je % 1 else 0)}{NBSP}{s} je 1.000{NBSP}{s}"
    txt = [f"{t:02d}.{m:02d}." for t, m in l]
    kopf = (("Zinsen " + ("jeden Monat" if zins == 12 else "alle drei Monate")) if zins > 2 else f"Zinsen am {txt[0]} und {txt[1]}" if zins == 2 and len(txt) > 1
            else f"Zinsen jedes Jahr am {txt[0]}")
    return (f'<span class="hk-blatt" aria-hidden="true"><i>{mon[naechster.month - 1]}</i>{naechster.day}</span><span class="hk-ztt"><b>{kopf}</b>'
            f'<span>{"jeweils " + betrag if zins >= 2 else betrag + " Nennwert"}</span></span>')


def startseite(site, seite="index.html"):
    """Startseite: Liste der Top-10-Seiten als JSON, sechs Zeilen und Hero-Karte der Bau-Stunde (seit 15.10.2026); geht das nicht, die
    festen Zeilen der Quell-HTML mit Tageskursen wie bisher (startseite_feste_zeilen)."""
    pfad = os.path.join(site, seite)
    html_ = open(pfad, encoding="utf-8").read()
    kurse, aus = lade(site, "kurse-auswahl.json"), lade(site, "anleihen-auswahl.json")
    try:
        P, quellen = top10_pool(site, kurse, aus)
    except Exception as e:
        warn(f"{seite}: Liste der Top-10-Seiten nicht gebildet ({type(e).__name__}: {e}) – feste Zeilen")
        return startseite_feste_zeilen(site, seite)
    tab = re.search(r'(<table class="itab(?: atab)?">)(.*?)(</table>)', html_, re.S)
    if len(P["staat"]) < 3 or len(P["unternehmen"]) < 3 or not tab or not POOL_RE.search(html_) or not ist_datum(P["stand"]):
        warn(f"{seite}: zu wenige Anleihen ({len(P['staat'])} Staat, {len(P['unternehmen'])} Unternehmen), Tabelle oder #top10-pool fehlt – feste Zeilen")
        return startseite_feste_zeilen(site, seite)
    h = int(datetime.datetime.now(datetime.timezone.utc).timestamp() // 3600)
    wahl = ziehe(P["staat"], 3, xorshift(h)) + ziehe(P["unternehmen"], 3, xorshift(h + 7919))
    ids = ["anleihe", "rendite", "kupon", "restlaufzeit", "kurs", "bonitaet", "stueckelung", "merken"]
    objs = []
    for i, x in enumerate(wahl):
        o = std_objekt(x, i + 1, kurse, aus, {"date": x["datum"]})
        o.update({"kurz": x["kurz"], "reg": x["reg"], "art": ARTNR.get(x["art"], 0), "ccy": x["cur"], "rend": x["rendite"], "kurs": x["kurs"],
                  "kdatum": x["datum"], "bon": x.get("bon"), "quelle": x})
        objs.append(o)
    ctx = {"kstand": P["stand"], "kuponZeile": lambda o: zt_text(o["quelle"])}
    tbody = "".join(std_zeile(o, ids, ctx, None).replace("<tr ", '<tr class="gr-ende" ', 1) if o["platz"] == 3 else std_zeile(o, ids, ctx, None) for o in objs)
    neu = html_[:tab.start(2)] + std_kopf(ids, sort=(None, 1)) + "<tbody>" + tbody + "</tbody>" + html_[tab.end(2):]
    neu = re.sub(r'(<span id="itab-stand">)[^<]*(</span>)', lambda m: m.group(1) + datum(P["stand"]) + m.group(2), neu, count=1)
    neu = re.sub(r'(<span id="itab-her">)[^<]*(</span>)', lambda m: m.group(1) + "Aus den Top-10-Listen" + m.group(2), neu, count=1)
    schlank = {k: [{f: v for f, v in z.items() if f not in ("reg", "vol")} for z in v] if isinstance(v, list) else v for k, v in P.items()}   # reg, vol zeigt die Seite nicht
    daten = json.dumps(schlank, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    neu = POOL_RE.sub(lambda m: m.group(1) + daten + m.group(3), neu, count=1)
    neu = hero_karte(neu, P, h)
    with open(pfad, "w", encoding="utf-8") as f:
        f.write(neu)
    print(f"{seite}: Liste der Top-10-Seiten ({len(P['staat'])} Staat, {len(P['unternehmen'])} Unternehmen; {', '.join(quellen)}), "
          f"sechs Beispiele und Hero-Karte vom {datum(P['stand'])}")


def hero_karte(html_, P, h):
    """Hero-Karte der Stunde h wie im Seitenskript: Anleihe isins[t % n] aus allen Einträgen der Liste."""
    alle = {x["isin"]: x for x in P["staat"] + P["unternehmen"]}
    isins = sorted(alle)
    t = (h ^ 0x9E3779B9) & 0xFFFFFFFF
    t = (t ^ (t << 13)) & 0xFFFFFFFF
    t ^= t >> 17
    t = (t ^ (t << 5)) & 0xFFFFFFFF
    x = alle[isins[t % len(isins)]]
    heute = datetime.datetime.now(BERLIN or datetime.timezone.utc).date()
    f = x["faellig"]
    teile = (
        (r'(<a class="hero-karte" href=")[^"]*(")', "anleihe.html?isin=" + esc(x["isin"])),
        (r'(<b id="hk-name")[^>]*(>)[^<]*', None),
        (r'(<span class="hk-art" id="hk-art">)[^<]*(</span>)', "Unternehmen" if x["art"] == "Unternehmen" else "Staat"),
        (r'(<span class="hk-z" id="hk-rend">)[^<]*(</span>)', pct_text(x["rendite"])),
        (r'(<span class="hk-achse" data-faellig=")[^"]*(")', f),
        (r'(<b id="hk-rueck">)[^<]*(</b>)', f"Rückzahlung {datum(f)}"),
    )
    for muster, wert in teile:
        if wert is None:
            ersatz = lambda m: f'{m.group(1)} title="{esc(x.get("emittent") or "")}"{m.group(2)}{esc(x["kurz"])}'
        else:
            ersatz = lambda m, wert=wert: m.group(1) + wert + m.group(2)
        html_, n = re.subn(muster, ersatz, html_, count=1)
        if not n:
            warn(f"index.html: Hero-Karte – Stelle {muster[:40]} nicht gefunden")
    i = html_.find('<span class="hk-zt" id="hk-kupon">')
    j = html_.find('<b id="hk-rueck">', i)
    if i >= 0 and j > i:
        ende = html_.rfind("</span>", i, j)
        html_ = html_[:i] + '<span class="hk-zt" id="hk-kupon">' + zt_karte(x, heute) + html_[ende:]
    return html_


# ---------- Startseite: Zinsstand-Laufband (seit 15.10.2026, Gesamtprüfung B01-01, B01-02, B01-10) ----------
# Bund 2 und 10 Jahre und USA 10 Jahre aus zinskurve.json (jüngster Tageswert, Veränderung zum Monatsdurchschnitt des Vormonats in
# Prozentpunkten), Bund 0 % 2050 aus langlaeufer.json (Veränderung zum Durchschnitt der Wochenwerte des Vormonats), EZB-Einlagesatz aus
# ezb.json (ohne Veränderung) – dieselbe Rechnung wie bis 14.10.2026 das Seitenskript, das die drei Dateien dafür einbetten ließ.
# „Stand“ = Tag der Bundesbank-Kurve; Werte von einem anderen Tag (USA laut Fed H.15, Bund 2050) mit ihrem Tag dahinter.
# Fällt eine Datei aus, bleibt ihr Rückfallwert stehen (Warnung).
def zinsstand(site, seite="index.html"):
    pfad = os.path.join(site, seite)
    html_ = open(pfad, encoding="utf-8").read()
    if 'class="zs-band"' not in html_:
        return warn(f"{seite}: Zinsstand-Band nicht gefunden")

    def vormonat(iso):
        j, m = int(iso[:4]), int(iso[5:7]) - 1
        return f"{j - 1}-12" if not m else f"{j}-{m:02d}"

    def pkt(d):   # wie pkt() bisher im Seitenskript: auf 0,01 gerundet, „±0,00“ ohne Bewegung
        n = math.floor(d * 100 + 0.5) / 100
        return ("+" if n > 0 else "−" if n < 0 else "±") + zahl(abs(n), 2)

    werte, tage = {}, {}
    try:
        z = lade(site, "zinskurve.json")
        for land in ("DE", "US"):
            h = (z.get("heute") or {}).get(land)
            if not (h and ist_datum(h[0])):
                continue
            vm = vormonat(h[0])
            row = next((r for r in (z.get("monate") or {}).get(land) or [] if r and r[0] == vm), None)
            if land == "DE":
                werte["bund2"] = (h[1], h[1] - row[1] if row and ist_zahl(h[1]) and ist_zahl(row[1]) else None)
            werte["bund10" if land == "DE" else "us10"] = (h[2], h[2] - row[2] if row and ist_zahl(h[2]) and ist_zahl(row[2]) else None)
            tage[land] = h[0]
    except Exception as e:
        warn(f"{seite}: Zinsstand – zinskurve.json nicht gelesen ({type(e).__name__}: {e})")
    try:
        e = lade(site, "ezb.json")
        if e.get("aktuell"):
            werte["ezb"] = (e["aktuell"][1], None)
    except Exception as e:
        warn(f"{seite}: Zinsstand – ezb.json nicht gelesen ({type(e).__name__}: {e})")
    try:
        b = (lade(site, "langlaeufer.json").get("bonds") or {}).get("bund2050") or {}
        neu = b.get("latest") or {}
        if ist_datum(neu.get("date")) and ist_zahl(neu.get("yield")):
            vm = vormonat(neu["date"])
            w = [r[2] for r in b.get("weekly") or [] if r and str(r[0])[:7] == vm and ist_zahl(r[2])]
            werte["bund2050"] = (neu["yield"], neu["yield"] - sum(w) / len(w) if w else None)
            tage["B50"] = neu["date"]
    except Exception as e:
        warn(f"{seite}: Zinsstand – langlaeufer.json nicht gelesen ({type(e).__name__}: {e})")
    gesetzt = 0
    for key, (wert, delta) in werte.items():
        if not ist_zahl(wert):
            continue

        def link(m, wert=wert, delta=delta):
            a = re.sub(r"<b>[^<]*</b>", f"<b>{zahl(wert, 2)}&nbsp;%</b>", m.group(0), count=1)
            return re.sub(r"<i>[^<]*</i>", f"<i>{pkt(delta)}</i>", a, count=1) if ist_zahl(delta) else a
        html_, n = re.subn(r'<a [^>]*data-zs="' + key + r'"[^>]*>.*?</a>', link, html_)
        gesetzt += 1 if n else 0
    if tage.get("DE"):
        kurz = lambda iso: datum(iso)[:6]
        neben = [f"{name} {kurz(tage[k])}" for k, name in (("US", "USA"), ("B50", "Bund 2050")) if tage.get(k) and tage[k] != tage["DE"]]
        stand = "Stand " + kurz(tage["DE"]) + "".join(" · " + t for t in neben)
        html_ = re.sub(r'(<span class="zs-stand">)[^<]*(</span>)', lambda m: m.group(1) + stand + m.group(2), html_)
    else:
        stand = "Stand unverändert (keine Bundesbank-Kurve)"
        warn(f"{seite}: Zinsstand – ohne Bundesbank-Kurve bleibt der Stand der Quell-HTML")
    with open(pfad, "w", encoding="utf-8") as f:
        f.write(html_)
    print(f"{seite}: Zinsstand-Band – {gesetzt} von 5 Werten gesetzt, {stand}")


def startseite_feste_zeilen(site, seite="index.html"):
    """Rückfall (bis 14.10.2026 der einzige Weg): „Sechs Beispiele“ (Standardtabelle seit 03.10.2026): In den Zeilen der Quell-HTML Rendite, Kurs und Restlaufzeit aus
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


# ---------- Bundeswertpapiere (seit 04.10.2026, SEO-Runde 2: neue Seite, Entscheidung 02.10.2026) ----------
BL_SPALTEN = ["anleihe", "rendite", "kupon", "restlaufzeit", "kurs", "volumen", "merken"]
# Grüne Bundeswertpapiere laut Finanzagentur (deutsche-finanzagentur.de → Bundeswertpapierarten → Grüne Bundeswertpapiere, abgerufen
# am 15.10.2026; seit 15.10.2026, Gesamtprüfung B11-01): Der Registername der ersten grünen Bundesanleihe DE0001030708 (0 % 2030) trägt
# kein „Grüne“ – sie hieß in der Liste „Bundesanleihe“ wie ihr konventioneller Zwilling DE0001102507. Neue grüne Papiere erkennt
# art_von() weiter am Namen; diese Liste ergänzt nur. Bei neuen Emissionen ohne „Grüne“ im Namen hier nachtragen.
GRUENE_BUND = {"DE0001030708", "DE0001030724", "DE0001030732", "DE0001030740", "DE0001030757",
               "DE000BU35025", "DE000BU3F007", "DE000BU3Z005", "DE000BU3Z047"}
BL_RE = re.compile(r"(<!--BUNDESLISTE-->).*?(<!--/BUNDESLISTE-->)", re.S)


def bundeswertpapiere(site, seite="bundeswertpapiere.html"):
    """Alle laufenden Bundeswertpapiere: Kurs und Rendite der Deutschen Bundesbank (kurse/bund/), Art und Stammdaten aus dem
    ESMA-Register (anleihen/). Nur Bundesbank-Daten – Börsenkurse stehen wie bei den Server-Steckbriefen nicht im HTML."""
    import glob
    from steckbriefe import art_von, stammdaten
    pfad = os.path.join(site, seite)
    if not os.path.isfile(pfad):
        return
    html_ = open(pfad, encoding="utf-8").read()
    if not BL_RE.search(html_):
        return warn(f"{seite}: Marke <!--BUNDESLISTE--> fehlt – Tabelle nicht geschrieben")
    kurse = {}
    for f in sorted(glob.glob(os.path.join(site, "kurse", "bund", "*.json"))):
        d = lade(site, os.path.relpath(f, site))
        t, k, r = d.get("t") or [], d.get("k") or [], d.get("r") or []
        i = max((j for j in range(min(len(t), len(k))) if ist_zahl(k[j])), default=None)
        if i is not None:
            kurse[d.get("isin") or os.path.basename(f)[:-5]] = (t[i], k[i], r[i] if i < len(r) and ist_zahl(r[i]) else None)
    stamm = stammdaten(site, list(kurse))
    heute = datetime.date.today().isoformat()
    objs = []
    for isin, (tag, kurs_, rend) in kurse.items():
        z = stamm.get(isin)
        if not z or not z[4] or z[4] < heute:
            continue
        art = art_von(z[0])
        if not art:
            continue
        if isin in GRUENE_BUND and not art.startswith("Grüne"):
            art = "Grüne " + art
        kupon_ = z[3] if ist_zahl(z[3]) else None
        objs.append({"isin": isin, "kurz": art, "reg": z[0], "art": 0, "ccy": z[2] or "EUR", "kupon": kupon_,
                     "zinsart": 2 if (len(z) > 9 and z[9] == 2) or kupon_ == 0 else 0, "faellig": z[4], "kurs": kurs_,
                     "kdatum": tag, "boerse": "B", "rend": rend, "real": art.startswith("Inflationsindexierte"),
                     "vol": z[5] if ist_zahl(z[5]) else None})
    if len(objs) < 30:   # Daten unvollständig: lieber die Seite lassen, wie sie ist
        return warn(f"{seite}: nur {len(objs)} Bundeswertpapiere mit Kurs und Stammdaten – Tabelle nicht geschrieben")
    objs.sort(key=lambda o: (o["faellig"], o["isin"]))
    for i, o in enumerate(objs):
        o["platz"] = i + 1
    stand = max(o["kdatum"] for o in objs)
    thead = std_kopf(BL_SPALTEN, sort=("restlaufzeit", 1)).replace("<thead>", '<thead class="std-kopf">', 1)
    tbody = "".join(std_zeile(o, BL_SPALTEN, {"kstand": stand}, "restlaufzeit") for o in objs)
    daten = json.dumps(objs, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    block = (f'<table class="kpis atab" id="bl-tabelle" aria-labelledby="h-liste">{thead}<tbody>{tbody}</tbody></table>'
             f'<script type="application/json" id="bl-daten">{daten}</script>')
    html_ = BL_RE.sub(lambda m: m.group(1) + block + m.group(2), html_, count=1)
    html_ = re.sub(r'(<span data-bl="anzahl">)\d+(</span>)', lambda m: m.group(1) + str(len(objs)) + m.group(2), html_)
    # seit 09.10.2026 (Technik-Test T-01): veraltete Bundesbank-Kurse beim Veröffentlichen kennzeichnen wie im Browser (MC.veraltet)
    alt = veraltet(stand)
    html_ = datenstand_setzen(html_, "Daten-Stand: " + datum(stand) + " (Deutsche Bundesbank)" + (" · veraltet" if alt else ""),
                              stale=alt) or html_
    with open(pfad, "w", encoding="utf-8") as f:
        f.write(html_)
    print(f"{seite}: {len(objs)} Bundeswertpapiere fest im HTML, Kurse vom {datum(stand)}")


# ---------- Langläufer: Volumen „heute“ in „Die sieben Anleihen im Einzelnen“ (seit 15.10.2026, Gesamtprüfung B12-01) ----------
# Die Volumen standen von Hand im HTML und alterten (Österreich 2120: 5,2 statt 6,3 Mrd., BTP 2072: 7,4 statt 9,4 Mrd.). Jetzt der
# ausgegebene Nennbetrag laut ESMA-Register (anleihen/<teil>.json, wie Anleihen-Suche und Top-10-Seiten) in <span data-vol="ISIN">.
WSYM = {"EUR": "€", "USD": "$", "GBP": "£"}


def langlaeufer_volumen(site, seite="langlaeufer.html"):
    from steckbriefe import stammdaten
    pfad = os.path.join(site, seite)
    html_ = open(pfad, encoding="utf-8").read()
    isins = re.findall(r'<span data-vol="([A-Z]{2}[A-Z0-9]{9}[0-9])">', html_)
    if not isins:
        return warn(f"{seite}: keine Volumen-Marken (data-vol) gefunden")
    stamm, fehlt = stammdaten(site, isins), []

    def setze(m):
        z = stamm.get(m.group(2))
        if not (z and ist_zahl(z[5]) and z[5] > 0 and z[2] in WSYM):
            fehlt.append(m.group(2))
            return m.group(0)
        return m.group(1) + volumen_text(z[5]).replace(NBSP, "&nbsp;") + "&nbsp;" + WSYM[z[2]] + m.group(3)
    html_ = re.sub(r'(<span data-vol="([A-Z0-9]{12})">)[^<]*(</span>)', setze, html_)
    if fehlt:
        warn(f"{seite}: Volumen ohne Stammdaten, Rückfall bleibt: {', '.join(fehlt)}")
    # „Daten-Stand“ wie renderAll() im Browser: Tag des jüngsten Bundesbank-Kurses der Bund 0 % 2050 (stand ohne Skript auf dem Tag der
    # Handpflege, 16.09.2026)
    stand = ((((lade(site, "langlaeufer.json").get("bonds") or {}).get("bund2050") or {}).get("latest") or {}).get("date"))
    if ist_datum(stand):
        alt = veraltet(stand)
        html_ = datenstand_setzen(html_, "Daten-Stand: " + datum(stand) + (" · veraltet" if alt else ""), stale=alt) or html_
    with open(pfad, "w", encoding="utf-8") as f:
        f.write(html_)
    print(f"{seite}: {len(isins) - len(fehlt)} Volumen aus dem ESMA-Register, Daten-Stand {datum(stand) if ist_datum(stand) else 'unverändert'}")


def main():
    site = sys.argv[1] if len(sys.argv) > 1 else "_site"
    nur = {a.lower() for a in sys.argv[2:]}   # lokal z. B. „bundeswertpapiere“: nur diese Tabelle schreiben
    if not os.path.isdir(site):
        raise SystemExit(f"Ordner nicht gefunden: {site}")
    for name, schritt in (("Broker", lambda: broker(site)), ("ETFs", lambda: etfs(site)),
                          ("Staatsanleihen nach Laufzeit", lambda: laufzeit(site, "staatsanleihen-laufzeit.html", "top10-staatsanleihen-laufzeit.json")),
                          ("Unternehmensanleihen nach Laufzeit", lambda: laufzeit(site, "unternehmensanleihen-laufzeit.html", "top10-unternehmensanleihen-laufzeit.json")),
                          ("Staatsanleihen nach Ländern", lambda: laender(site, "anleihen-laender.html", "top10-staatsanleihen-laender.json")),
                          ("Unternehmensanleihen nach Ländern", lambda: laender(site, "unternehmensanleihen-laender.html", "top10-unternehmensanleihen-laender.json")),
                          ("Anleihen nach Kupon", lambda: kupon(site)),
                          ("Startseite", lambda: startseite(site)),
                          ("Zinsstand", lambda: zinsstand(site)),
                          ("Bundeswertpapiere", lambda: bundeswertpapiere(site)),
                          ("Langläufer", lambda: langlaeufer_volumen(site))):
        if nur and name.lower() not in nur:
            continue
        try:
            schritt()
        except Exception as e:   # Daten oder Seite anders als erwartet: Seite bleibt, wie sie ist
            warn(f"{name}: nicht vorab geschrieben ({type(e).__name__}: {e})")


if __name__ == "__main__":
    main()
