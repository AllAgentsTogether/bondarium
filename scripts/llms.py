#!/usr/bin/env python3
"""llms.py – schreibt llms.txt und llms-full.txt beim Deploy aus den Seiten selbst (seit 30.09.2026).

Läuft im GitHub-Workflow auf dem Veröffentlichungsordner, NACH kennzahlen.py, statische_tabellen.py und seo.py
(braucht deren Sitemap und die fest geschriebenen Tabellen) und VOR inline_data.py und dem Minify:

    python3 scripts/llms.py _site

  llms.txt        Kurzfassung für KI-Dienste (Format: llmstxt.org): wer Bondarium ist, wie die Daten entstehen,
                  und je Seite eine Zeile – Titel, Adresse, Beschreibung. Titel und Beschreibung kommen aus
                  <title> und <meta name="description"> der Seite, die Gruppe aus ihren Brotkrumen.
  llms-full.txt   Volltext: die aktuellen Zahlen aus den Daten-JSONs und der Inhalt jeder Seite als Markdown
                  (Überschriften, Absätze, Listen, Tabellen, Links).

Beide Dateien entstehen bei jedem Deploy neu und gehören NICHT ins Repository – eine neue Seite steht von selbst
drin, sobald sie Titel, Beschreibung, Brotkrumen und einen Eintrag in der Sitemap hat. Bis 30.09.2026 war llms.txt
von Hand gepflegt (54 KB, mit internen Änderungsnotizen); diese Fassung liegt als docs/SEITEN.md im Repository.
Nur der Rahmentext unten (KOPF, HINWEISE) ist von Hand geschrieben.
"""
import html as htmllib
import json
import os
import re
import sys
from html.parser import HTMLParser

BASE = "https://www.bondarium.de/"

KOPF = """# Bondarium

> Bondarium (www.bondarium.de) erklärt Anleihen auf Deutsch und hilft, passende zu finden: Wissen in kurzen
> Schritten vom Einstieg bis zur Duration, Renditen von Staatsanleihen seit 1970 und Unternehmensanleihen seit 1984,
> Zinskurve, Realzins und Risikoaufschläge, die meistgehandelten Anleihen und Anleihen-ETFs, ein Broker-Vergleich,
> vier Rechner und eine Suche über {anleihen} Anleihen an deutschen Börsen. Für Privatanleger und Unternehmen,
> kostenlos und ohne Anmeldung.
"""
HINWEISE = """Zur Einordnung:

- Sprache Deutsch; geschrieben für Privatanleger und Unternehmen in Deutschland (Steuern und Broker: deutsche Sicht).
- Die Daten kommen automatisch, Montag bis Freitag um 10 Uhr: Kurse vom letzten Börsentag (Deutsche Börse –
  Börse Frankfurt, Xetra, Tradegate; Bundeswertpapiere: Deutsche Bundesbank), Renditen und Zeitreihen von
  Zentralbanken, Finanzministerien und der OECD. Jede Datenseite nennt ihren Stand und ihre Quellen.
- Bondarium gibt keine Anlageberatung und empfiehlt keine einzelnen Wertpapiere. Beispiele zeigen, wie man vorgeht.
- Herausgeber: urbanelo GmbH, Stuttgart – Impressum: {base}rechtliches.html, Kontakt: info@bondarium.com.
- Zitate und Zusammenfassungen sind willkommen – bitte mit Link auf die Seite und dem dort genannten Datenstand.
- Volltext aller Seiten mit den aktuellen Zahlen: {base}llms-full.txt
"""

# Reihenfolge der Abschnitte (Name der zweiten Brotkrume); alles Übrige folgt alphabetisch, „Optional“ am Ende.
ABSCHNITTE = ["Verstehen", "Entscheiden", "Kaufen", "Anleihen", "Zinsen"]
OPTIONAL = {"ueber-uns.html", "rechtliches.html"}
OHNE_VOLLTEXT = {"rechtliches.html"}   # Impressum und Datenschutz: nur verlinkt

LEER = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}
AUSLASSEN = {"script", "style", "svg", "nav", "button", "select", "form", "noscript", "template", "canvas", "input",
             "textarea", "label", "output", "iframe"}
BLOCK = {"p", "div", "section", "article", "ul", "ol", "li", "table", "h1", "h2", "h3", "h4", "h5", "h6", "dl", "dt", "dd",
         "blockquote", "figure", "figcaption", "details", "summary", "header", "footer", "main", "aside", "hr", "pre"}


def warn(text):
    print(f"::warning::llms.py: {text}")


# ---------- HTML → Baum → Markdown ----------
class Knoten:
    def __init__(self, tag=None, attrs=None, text=None):
        self.tag, self.attrs, self.text, self.kinder = tag, dict(attrs or {}), text, []


class Baum(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.wurzel = Knoten("wurzel")
        self.stapel = [self.wurzel]

    def handle_starttag(self, tag, attrs):
        k = Knoten(tag, attrs)
        self.stapel[-1].kinder.append(k)
        if tag not in LEER:
            self.stapel.append(k)

    def handle_startendtag(self, tag, attrs):
        self.stapel[-1].kinder.append(Knoten(tag, attrs))

    def handle_endtag(self, tag):
        for i in range(len(self.stapel) - 1, 0, -1):
            if self.stapel[i].tag == tag:
                del self.stapel[i:]
                break

    def handle_data(self, data):
        self.stapel[-1].kinder.append(Knoten(text=data))


def finde(k, tag):
    if k.tag == tag:
        return k
    for c in k.kinder:
        f = finde(c, tag)
        if f:
            return f
    return None


def alle(k, tag, aus=None):
    aus = [] if aus is None else aus
    for c in k.kinder:
        if c.tag == tag:
            aus.append(c)
        elif c.tag and c.tag != "table":   # keine verschachtelten Tabellen einsammeln
            alle(c, tag, aus)
    return aus


def versteckt(k):
    a = k.attrs
    return k.tag in AUSLASSEN or "hidden" in a or a.get("aria-hidden") == "true"


def glatt(s):
    return re.sub(r"\s+", " ", s.replace("­", "").replace(" ", " "))


def adresse(href, seite):
    if not href or href.startswith(("javascript:", "data:")):
        return None
    if href.startswith(("http://", "https://", "mailto:")):
        return href
    if href.startswith("#"):
        return seite + href
    href = re.sub(r"^(\./|/)", "", href)
    return BASE + ("" if href == "index.html" else re.sub(r"^index\.html(?=#)", "", href))


def zeile(k, seite):
    """Inhalt eines Knotens als eine Markdown-Zeile (ohne Blockstruktur)."""
    if k.text is not None:
        return glatt(k.text)
    if versteckt(k):
        return ""
    if k.tag == "br":
        return " "
    if k.tag == "img":
        return glatt(k.attrs.get("alt") or "")
    teile = [zeile(c, seite) for c in k.kinder]
    elemente = [c for c in k.kinder if c.tag and zeile(c, seite).strip()]
    nur_elemente = not any(c.text is not None and c.text.strip() for c in k.kinder)
    if any(c.tag in BLOCK for c in k.kinder) or (k.tag == "a" and len(elemente) > 1 and nur_elemente):
        # Karte: <a><h3>…</h3><p>…</p></a> oder <a><span>Titel</span><b>Zeile</b><span>Text</span></a>
        t = " – ".join(x.strip() for x in teile if x.strip())
    else:
        # Elemente, die im Quelltext ohne Leerraum aneinanderstoßen, stehen auf der Seite untereinander
        # (<b>Name</b><span>Typ</span>) – hier mit „ · “ bzw. Leerzeichen trennen; Hoch-/Tiefstellung bleibt verbunden
        t, davor = "", None
        for c, x in zip(k.kinder, teile):
            if not x:
                continue
            if t and davor is not None and (c.tag or davor.tag) and "sub" not in (c.tag, davor.tag) and "sup" not in (c.tag, davor.tag) \
                    and re.search(r"[\w*)]$", t) and re.match(r"[\w*\[]", x):
                t += " · " if c.tag and davor.tag else " "
            t += x
            davor = c
    t = re.sub(r"\)\[", ") · [", glatt(t))   # Links ohne Zwischenraum (Pillen, Reiter) trennen
    if not t.strip():
        return ""
    if k.tag == "a":
        ziel = adresse(k.attrs.get("href"), seite)
        t = t.replace("**", "").strip()
        return f"[{t}]({ziel})" if ziel else t
    if k.tag in ("strong", "b"):
        return f"**{t.strip()}**" + (" " if t.endswith(" ") else "")
    if k.tag == "em":
        return f"*{t.strip()}*" + (" " if t.endswith(" ") else "")
    if k.tag == "small":
        return f" ({t.strip()})"
    return t


def tabelle(k, seite, aus):
    titel = finde(k, "caption")
    if titel:
        t = zeile(titel, seite).strip()
        if t:
            aus.append(f"**{t}**")
    def knoepfe(n):   # Spaltentitel stehen oft in Sortier-Knöpfen
        for c in n.kinder:
            if c.tag == "button":
                c.tag = "span"
            if c.tag:
                knoepfe(c)
    reihen = []
    for tr in alle(k, "tr"):
        for c in tr.kinder:
            if c.tag == "th":
                knoepfe(c)
        zellen = [zeile(c, seite).strip().replace("|", "/") for c in tr.kinder if c.tag in ("th", "td")]
        if any(zellen):
            reihen.append(zellen)
    if not reihen:
        return
    breite = max(len(r) for r in reihen)
    reihen = [r + [""] * (breite - len(r)) for r in reihen]
    md = ["| " + " | ".join(reihen[0]) + " |", "|" + " --- |" * breite]
    md += ["| " + " | ".join(r) + " |" for r in reihen[1:]]
    aus.append("\n".join(md))


def liste(k, seite, aus, tiefe=0):
    zeilen = []

    def sammeln(knoten, t):
        n = 0
        for li in knoten.kinder:
            if li.tag != "li" or versteckt(li):
                continue
            n += 1
            eigen = Knoten("span")
            eigen.kinder = [c for c in li.kinder if c.tag not in ("ul", "ol")]
            text = zeile(eigen, seite).strip()
            if text:
                zeilen.append("  " * t + (f"{n}. " if knoten.tag == "ol" else "- ") + text)
            for c in li.kinder:
                if c.tag in ("ul", "ol"):
                    sammeln(c, t + 1)
    sammeln(k, tiefe)
    if zeilen:
        aus.append("\n".join(zeilen))


def block(k, seite, aus):
    """Hängt die Markdown-Blöcke des Knotens an aus an."""
    if k.text is not None or versteckt(k):
        return
    t = k.tag
    if t == "h1":
        return   # steht schon als Seitenüberschrift
    if t in ("h2", "h3", "h4", "h5", "h6"):
        text = zeile(k, seite).strip()
        if text:
            aus.append("#" * (int(t[1]) + 1) + " " + text)
        return
    if t in ("ul", "ol"):
        return liste(k, seite, aus)
    if t == "table":
        return tabelle(k, seite, aus)
    if t == "dt" or t == "summary":
        text = zeile(k, seite).strip()
        if text:
            aus.append(f"**{text}**")
        return
    if t == "blockquote":
        innen = []
        for c in k.kinder:
            block(c, seite, innen)
        aus.extend("> " + b.replace("\n", "\n> ") for b in innen)
        return
    if not any(c.tag in BLOCK or c.tag == "table" for c in k.kinder):
        # reiner Fließtext – oder eine Hülle um Karten-Links (<div><a><h3>…</h3></a><a>…</a></div>)
        if any(c.tag == "a" and any(g.tag in BLOCK for g in c.kinder) for c in k.kinder):
            karten = [zeile(c, seite).strip() for c in k.kinder if c.tag == "a"]
            karten = [x for x in karten if x]
            if karten:
                aus.append("\n".join("- " + x for x in karten))
            return
        text = zeile(k, seite).strip()
        if text:
            aus.append(text)
        return
    lauf = []   # Fließtext zwischen Blöcken zusammenhalten

    def spuelen():
        if lauf:
            h = Knoten("span")
            h.kinder = list(lauf)
            text = zeile(h, seite).strip()
            if text:
                aus.append(text)
            del lauf[:]
    for c in k.kinder:
        if c.tag in BLOCK or c.tag == "table" or (c.tag and any(g.tag in BLOCK or g.tag == "table" for g in c.kinder) and c.tag != "a"):
            spuelen()
            block(c, seite, aus)
        else:
            lauf.append(c)
    spuelen()


def markdown(html_, seite):
    b = Baum()
    b.feed(html_)
    haupt = finde(b.wurzel, "main") or finde(b.wurzel, "body") or b.wurzel
    aus = []
    block(haupt, seite, aus)
    return "\n\n".join(x for x in aus if x.strip())


# ---------- Angaben je Seite ----------
def kopf(html_, muster):
    m = re.search(muster, html_, re.S)
    return re.sub(r"\s+", " ", htmllib.unescape(m.group(1)).replace("­", "")).strip() if m else ""


def krume(html_):
    """(Name der zweiten Brotkrume = Rubrik, ist die Seite selbst deren Übersicht?) aus dem JSON-LD der Seite."""
    for roh in re.findall(r'<script type="application/ld\+json">(.*?)</script>', html_, re.S):
        try:
            k = json.loads(roh)
        except ValueError:
            continue
        for knoten in (k.get("@graph") if isinstance(k, dict) and "@graph" in k else [k]):
            if isinstance(knoten, dict) and knoten.get("@type") == "BreadcrumbList":
                e = knoten.get("itemListElement") or []
                return (e[1].get("name"), len(e) == 2) if len(e) > 1 else (None, False)
    return None, False


def seiten(site):
    pfad = os.path.join(site, "sitemap.xml")
    adressen = re.findall(r"<loc>([^<]+)</loc>", open(pfad, encoding="utf-8").read()) if os.path.isfile(pfad) else []
    aus = []
    for u in adressen:
        fname = u[len(BASE):] or "index.html"
        p = os.path.join(site, fname)
        if not u.startswith(BASE) or not os.path.isfile(p):
            continue
        h = open(p, encoding="utf-8").read()
        titel = re.sub(r"\s+[–-]\s+Bondarium$", "", kopf(h, r"<title>(.*?)</title>"))
        if fname == "index.html":
            titel = "Startseite"
        h1 = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", kopf(h, r"<h1[^>]*>(.*?)</h1>"))).strip()
        rubrik, uebersicht = krume(h)
        aus.append({"datei": fname, "url": u, "titel": titel, "h1": h1, "rubrik": rubrik, "uebersicht": uebersicht, "html": h,
                    "text": kopf(h, r'<meta name="description" content="([^"]*)"')})
    return aus


# ---------- llms.txt ----------
def kurzfassung(site, S):
    m = re.search(r"Suche über (rund \d{1,3}\.\d{3}) Anleihen", next((s["text"] for s in S if s["datei"] == "index.html"), ""))
    teile = [KOPF.format(anleihen=m.group(1) if m else "rund 33.000"), HINWEISE.format(base=BASE)]
    gruppen, optional = {}, []
    start = [s for s in S if s["datei"] == "index.html"]
    for s in S:
        if s["datei"] == "index.html":
            continue
        if s["datei"] in OPTIONAL:
            optional.append(s)
        else:
            gruppen.setdefault(s["rubrik"] or "Weitere Seiten", []).append(s)
    namen = [a for a in ABSCHNITTE if a in gruppen] + sorted(g for g in gruppen if g not in ABSCHNITTE)

    def eintrag(s):
        return f"- [{s['titel']}]({s['url']}): {s['text']}"
    if start:
        teile.append("## Start\n\n" + "\n".join(eintrag(s) for s in start))
    for g in namen:   # Übersichtsseite der Rubrik zuerst, dann in der Reihenfolge der Sitemap
        reihe = sorted(gruppen[g], key=lambda s: not s["uebersicht"])
        teile.append(f"## {g}\n\n" + "\n".join(eintrag(s) for s in reihe))
    if optional:
        teile.append("## Optional\n\n" + "\n".join(eintrag(s) for s in optional))
    with open(os.path.join(site, "llms.txt"), "w", encoding="utf-8") as f:
        f.write("\n\n".join(t.rstrip() for t in teile) + "\n")
    print(f"llms.txt: {len(S)} Seiten in {len(namen) + bool(start) + bool(optional)} Abschnitten")


# ---------- llms-full.txt ----------
def de(v, nk=2):
    return f"{v:.{nk}f}".replace(".", ",").replace("-", "−")


def tag(iso):
    m = re.match(r"(\d{4})-(\d{2})(?:-(\d{2}))?", str(iso or ""))
    return "–" if not m else f"{m.group(3)}.{m.group(2)}.{m.group(1)}" if m.group(3) else f"{m.group(2)}/{m.group(1)}"


def lade(site, name):
    with open(os.path.join(site, name), encoding="utf-8") as f:
        return json.load(f)


LAND = {"us": "USA", "cn": "China", "de": "Deutschland", "in": "Indien", "jp": "Japan", "gb": "Vereinigtes Königreich",
        "fr": "Frankreich", "it": "Italien"}


def zahlen(site):
    """Die wichtigsten Tageswerte aus den Daten-JSONs; jeder Block für sich – fehlt eine Datei, fehlt nur ihr Block."""
    aus = []

    def versuch(name, f):
        try:
            aus.append(f())
        except Exception as e:
            warn(f"Aktuelle Zahlen – {name}: ausgelassen ({type(e).__name__}: {e})")

    def renditen():
        c = lade(site, "renditen.json")["countries"]
        z = ["### Renditen 10-jähriger Staatsanleihen", "", "| Land | Rendite | Stand |", "| --- | --- | --- |"]
        z += [f"| {LAND.get(k, k)} | {de(v['latest']['yield'])} % | {tag(v['latest']['date'])} |" for k, v in c.items()]
        return "\n".join(z) + f"\n\nSeite mit Verlauf seit 1970: {BASE}renditen.html"

    def zinskurve():
        h = lade(site, "zinskurve.json")["heute"]
        z = ["### Zinskurve: 10 Jahre minus 2 Jahre", "", "| Land | 2 Jahre | 10 Jahre | Abstand | Stand |", "| --- | --- | --- | --- | --- |"]
        for k, name in (("DE", "Deutschland"), ("US", "USA")):
            d, zwei, zehn = h[k]
            z.append(f"| {name} | {de(zwei)} % | {de(zehn)} % | {de(zehn - zwei)} Prozentpunkte | {tag(d)} |")
        return "\n".join(z) + f"\n\nSeite mit Verlauf seit 1972: {BASE}zinskurve.html"

    def realzins():
        h = lade(site, "realzins.json")["heute"]
        (dz, zins), (dv, vpi) = h["zins10"], h["vpi"]
        return ("### Realzins Deutschland\n\n"
                f"- Rendite der 10-jährigen Bundesanleihe: {de(zins)} % (Stand {tag(dz)})\n"
                f"- Inflationsrate (Verbraucherpreise, gegenüber Vorjahr): {de(vpi, 1)} % (Stand {tag(dv)})\n"
                f"- Realzins (Rendite minus Inflationsrate): {de(zins - vpi)} Prozentpunkte\n\n"
                f"Seite mit Verlauf seit 1970: {BASE}realzins.html")

    def ezb():
        d = lade(site, "ezb.json")
        return f"### Leitzins\n\n- Einlagesatz der Europäischen Zentralbank: {de(d['aktuell'][1])} % (gültig seit {tag(d['aktuell'][0])}, geprüft am {tag(d['stand'])})"

    for name, f in (("Renditen", renditen), ("Zinskurve", zinskurve), ("Realzins", realzins), ("EZB", ezb)):
        versuch(name, f)
    return aus


def volltext(site, S):
    start = next((s for s in S if s["datei"] == "index.html"), None)
    m = re.search(r"Suche über (rund \d{1,3}\.\d{3}) Anleihen", start["text"] if start else "")
    teile = [KOPF.format(anleihen=m.group(1) if m else "rund 33.000").replace("# Bondarium", "# Bondarium – Volltext aller Seiten", 1),
             HINWEISE.format(base=BASE).replace(f"- Volltext aller Seiten mit den aktuellen Zahlen: {BASE}llms-full.txt\n",
                                                f"- Kurzfassung mit allen Adressen: {BASE}llms.txt\n")]
    z = zahlen(site)
    if z:
        teile.append("## Aktuelle Zahlen\n\nAutomatisch aus den Daten der Seiten, mit dem Stand je Wert. Zahlen in den Seitentexten weiter unten "
                     "können einige Tage älter sein – maßgeblich sind die Werte hier und auf den Seiten selbst.\n\n" + "\n\n".join(z))
    n = 0
    for s in S:
        if s["datei"] in OHNE_VOLLTEXT:
            continue
        try:
            md = markdown(s["html"], s["url"])
        except Exception as e:
            warn(f"{s['datei']}: Volltext ausgelassen ({type(e).__name__}: {e})")
            continue
        teile.append(f"---\n\n## {s['h1'] or s['titel']}\n\nAdresse: {s['url']}\n\n{s['text']}\n\n{md}")
        n += 1
    pfad = os.path.join(site, "llms-full.txt")
    with open(pfad, "w", encoding="utf-8") as f:
        f.write("\n\n".join(t.rstrip() for t in teile) + "\n")
    print(f"llms-full.txt: {n} Seiten, {os.path.getsize(pfad) // 1024} KB")


def main():
    site = sys.argv[1] if len(sys.argv) > 1 else "_site"
    if not os.path.isdir(site):
        raise SystemExit(f"Ordner nicht gefunden: {site}")
    S = seiten(site)
    if not S:
        raise SystemExit("llms.py: keine Seiten in sitemap.xml gefunden – llms.txt nicht geschrieben")
    kurzfassung(site, S)
    try:
        volltext(site, S)
    except Exception as e:   # der Volltext ist Zugabe – ein Fehler dort stoppt den Deploy nicht
        warn(f"llms-full.txt nicht geschrieben ({type(e).__name__}: {e})")


if __name__ == "__main__":
    main()
