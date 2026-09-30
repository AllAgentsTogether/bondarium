#!/usr/bin/env python3
"""seo.py – strukturierte Daten, Robots-Angabe und Sitemap beim Deploy (seit 30.09.2026).

Läuft im GitHub-Workflow auf dem Veröffentlichungsordner, NACH kennzahlen.py und VOR inline_data.py und dem Minify:

    python3 scripts/seo.py _site

Die Quell-HTML im Repository bleiben unverändert – dort pflegt jede Seite weiter nur ihren eigenen kleinen
JSON-LD-Block (Article/WebPage/CollectionPage + BreadcrumbList). Dieses Skript macht daraus je Seite EINEN
verknüpften Block (@graph):

  * Organisation und Website stehen auf jeder Seite gleich und mit fester Kennung (@id); Herausgeber, Autor und
    „Teil von“ verweisen darauf, statt die Angaben zu wiederholen. Die Website nennt die Suche (SearchAction).
  * Artikel bekommen Autor und Vorschaubild, Übersichtsseiten den Verweis auf ihre Brotkrumen.
  * begriffe.html: jedes Glossar-Stichwort als DefinedTerm (Name, Erklärung, Sprungadresse).
  * rechner.html: die Rechner als WebApplication.
  * Datenseiten (DATENSAETZE): die Zeitreihe als Dataset mit Zeitraum, Messgrößen und Quellen.

Außerdem:
  * Robots-Angabe: „index, follow“ wird um max-image-preview:large, max-snippet:-1 ergänzt (große Vorschaubilder,
    Textausschnitt ohne Längengrenze).
  * sitemap.xml wird aus den Seiten neu geschrieben: jede Seite mit „index“ und eigener kanonischer Adresse steht
    drin, entfernte oder gesperrte Seiten fallen heraus, <lastmod> ist das dateModified der Seite. Die Reihenfolge
    der Datei im Repository bleibt erhalten, neue Seiten kommen ans Ende. (Das Tagesdatum der Datenseiten setzt
    danach wie bisher der Schritt „Zeitstempel & Versions-URLs“.)

Nichts davon ändert sichtbaren Text. Fehlt einer Seite etwas Erwartetes, gibt es eine Warnung – der Deploy läuft.
"""
import datetime
import html as htmllib
import json
import os
import re
import sys

BASE = "https://www.bondarium.de/"
ORG_ID = BASE + "#organisation"
SITE_ID = BASE + "#website"
BILD = {"@type": "ImageObject", "url": BASE + "og-image.png", "width": 1200, "height": 630}

# Angaben wie im Impressum (rechtliches.html). Ändert sich dort etwas, hier nachziehen – das Skript warnt,
# wenn Firmenname oder Straße im Impressum nicht mehr vorkommen.
ORGANISATION = {
    "@type": "Organization",
    "@id": ORG_ID,
    "name": "Bondarium",
    "alternateName": "bondarium.de",
    "legalName": "urbanelo GmbH",
    "url": BASE,
    "logo": {"@type": "ImageObject", "url": BASE + "apple-touch-icon.png", "width": 180, "height": 180},
    "email": "info@bondarium.com",
    "address": {"@type": "PostalAddress", "streetAddress": "Heinrich-Baumann-Straße 38", "postalCode": "70190",
                "addressLocality": "Stuttgart", "addressCountry": "DE"},
    "contactPoint": {"@type": "ContactPoint", "contactType": "customer service", "email": "info@bondarium.com",
                     "url": BASE + "ueber-uns.html#kontakt", "availableLanguage": "de"},
}
WEBSITE = {
    "@type": "WebSite",
    "@id": SITE_ID,
    "name": "Bondarium",
    "alternateName": "bondarium.de",
    "url": BASE,
    "inLanguage": "de",
    "publisher": {"@id": ORG_ID},
    # Die Suche nimmt den Begriff im Parameter q entgegen (Formular der Startseite, anleihen-suche.html)
    "potentialAction": {"@type": "SearchAction",
                        "target": {"@type": "EntryPoint", "urlTemplate": BASE + "anleihen-suche.html?q={search_term_string}"},
                        "query-input": "required name=search_term_string"},
}

# Seiten ohne Eintrag in der Sitemap, obwohl sie „index“ tragen: der Steckbrief ist ohne ISIN eine leere Hülle.
OHNE_SITEMAP = {"anleihe.html"}

# Zeitreihen der Datenseiten: Name, Beginn, Länder, Messgrößen; „json“ liefert Datum (updated) und Quellen (quelle).
DATENSAETZE = {
    "renditen.html": {
        "json": "renditen.json", "von": "1970",
        "name": "Renditen 10-jähriger Staatsanleihen der acht größten Volkswirtschaften seit 1970",
        "laender": ["USA", "China", "Deutschland", "Indien", "Japan", "Vereinigtes Königreich", "Frankreich", "Italien"],
        "groessen": ["Rendite 10-jähriger Staatsanleihen in Prozent pro Jahr (Jahresmittel, Jahresspanne, aktueller Wert)"]},
    "unternehmensanleihen.html": {
        "json": "unternehmen.json", "von": "1984",
        "name": "Renditen 10-jähriger Unternehmensanleihen nach Bonität seit 1984",
        "laender": ["USA", "Japan", "China", "Australien"],
        "groessen": ["Rendite 10-jähriger Unternehmensanleihen in Prozent pro Jahr, je Land und Bonitätsstufe"]},
    "zinskurve.html": {
        "json": "zinskurve.json", "von": "1972",
        "name": "Zinskurve: Abstand zwischen 10- und 2-jährigen Staatsanleihen, Deutschland seit 1972 und USA seit 1976",
        "laender": ["Deutschland", "USA"],
        "groessen": ["Rendite 2-jähriger Staatsanleihen in Prozent", "Rendite 10-jähriger Staatsanleihen in Prozent",
                     "Abstand 10 Jahre minus 2 Jahre in Prozentpunkten"]},
    "realzins.html": {
        "json": "realzins.json", "von": "1970",
        "name": "Realzins der 10-jährigen Bundesanleihe seit 1970",
        "laender": ["Deutschland"],
        "groessen": ["Rendite der 10-jährigen Bundesanleihe in Prozent", "Inflationsrate (Verbraucherpreise) in Prozent",
                     "Realzins: Rendite minus Inflationsrate in Prozentpunkten"]},
    "risikoaufschlaege.html": {
        "json": "risikoaufschlaege.json", "von": "1984",
        "name": "Risikoaufschläge: Euro-Staaten gegen Deutschland seit 1991, US-Unternehmen gegen US-Staatsanleihen seit 1984",
        "laender": ["Euroraum", "USA"],
        "groessen": ["Renditeabstand 10-jähriger Staatsanleihen zu Deutschland in Prozentpunkten",
                     "Renditeabstand 10-jähriger US-Unternehmensanleihen zur US-Staatsanleihe in Prozentpunkten"]},
    "langlaeufer.html": {
        "json": "langlaeufer.json", "von": "2019",
        "name": "Kurs und Rendite von Langläufer-Anleihen seit 2019",
        "laender": None,
        "groessen": ["Kurs in Prozent des Nennwerts", "Rendite bis Fälligkeit in Prozent"]},
}

LD_RE = re.compile(r'<script type="application/ld\+json">(.*?)</script>\n?', re.S)
ROBOTS_RE = re.compile(r'<meta name="robots" content="index, follow">')
ROBOTS_NEU = '<meta name="robots" content="index, follow, max-image-preview:large, max-snippet:-1, max-video-preview:-1">'


def warn(text):
    print(f"::warning::seo.py: {text}")


def klartext(s):
    """HTML-Schnipsel → reiner Text (Tags weg, Zeichen aufgelöst, Leerraum zusammengezogen)."""
    s = re.sub(r"<[^>]+>", " ", s)
    s = htmllib.unescape(s).replace("­", "").replace(" ", " ")
    return re.sub(r"\s+", " ", s).strip()


def kopf(html_, muster):
    m = re.search(muster, html_, re.S)
    return htmllib.unescape(m.group(1)).strip() if m else None


def lade_json(site, name):
    try:
        with open(os.path.join(site, name), encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        warn(f"{name} nicht lesbar ({e})")
        return None


def glossar(html_, url):
    """begriffe.html: <div class="e" id="…"><dt>Stichwort</dt><dd><p>Erklärung</p>…</dd></div> → DefinedTermSet."""
    set_id = url + "#glossar"
    begriffe = []
    for anker, dt, dd in re.findall(r'<div class="e" id="([^"]+)"[^>]*>\s*<dt[^>]*>(.*?)</dt>\s*<dd[^>]*>(.*?)</dd>', html_, re.S):
        p = re.search(r"<p(?![^>]*class=\"links\")[^>]*>(.*?)</p>", dd, re.S)
        name, text = klartext(dt), klartext(p.group(1)) if p else ""
        if not name or not text:
            continue
        begriffe.append({"@type": "DefinedTerm", "@id": f"{url}#{anker}", "name": name, "description": text,
                         "url": f"{url}#{anker}", "inDefinedTermSet": {"@id": set_id}})
    if not begriffe:
        warn("begriffe.html: keine Glossar-Einträge erkannt – DefinedTermSet ausgelassen")
        return None
    return {"@type": "DefinedTermSet", "@id": set_id, "name": "Glossar: Anleihen-Begriffe von A bis Z", "url": url,
            "inLanguage": "de", "publisher": {"@id": ORG_ID}, "hasDefinedTerm": begriffe}


def rechner(html_, url, beschreibung):
    teile = [klartext(h) for h in re.findall(r"<h2[^>]*>(.*?)</h2>", html_, re.S)]
    teile = [t for t in teile if t]
    knoten = {"@type": "WebApplication", "@id": url + "#rechner", "name": "Anleihen-Rechner", "url": url,
              "description": beschreibung, "applicationCategory": "FinanceApplication", "operatingSystem": "Alle (Browser)",
              "browserRequirements": "JavaScript", "inLanguage": "de", "isAccessibleForFree": True,
              "offers": {"@type": "Offer", "price": "0", "priceCurrency": "EUR"}, "publisher": {"@id": ORG_ID}}
    if teile:
        knoten["featureList"] = teile
    return knoten


def datensatz(site, fname, url, beschreibung):
    c = DATENSAETZE[fname]
    d = lade_json(site, c["json"]) or {}
    knoten = {"@type": "Dataset", "@id": url + "#daten", "name": c["name"], "description": beschreibung, "url": url,
              "inLanguage": "de", "isAccessibleForFree": True, "temporalCoverage": c["von"] + "/..",
              "variableMeasured": c["groessen"], "creator": {"@id": ORG_ID}, "publisher": {"@id": ORG_ID}}
    if c["laender"]:
        knoten["spatialCoverage"] = c["laender"]
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(d.get("updated") or "")):
        knoten["dateModified"] = d["updated"]
    quelle = d.get("quelle")
    quellen = list(quelle.values()) if isinstance(quelle, dict) else [quelle] if isinstance(quelle, str) else []
    quellen = [q for q in quellen if isinstance(q, str) and q]
    if quellen:
        knoten["citation"] = quellen
    return knoten


def seite(site, fname):
    """Schreibt den verknüpften JSON-LD-Block und die Robots-Angabe; gibt (URL, dateModified) für die Sitemap zurück."""
    pfad = os.path.join(site, fname)
    html_ = open(pfad, encoding="utf-8").read()
    teil_kopf = html_.split("</head>")[0]
    robots = kopf(teil_kopf, r'<meta name="robots" content="([^"]*)"') or ""
    if "noindex" in robots:
        return None
    url = kopf(teil_kopf, r'<link rel="canonical" href="([^"]+)"')
    eigen = BASE + ("" if fname == "index.html" else fname)
    if not url:
        warn(f"{fname}: keine kanonische Adresse – Seite ausgelassen")
        return None
    beschreibung = kopf(teil_kopf, r'<meta name="description" content="([^"]*)"') or ""
    titel = re.sub(r"\s+[–-]\s+Bondarium$", "", kopf(teil_kopf, r"<title>(.*?)</title>") or "")

    haupt, krumen = None, None
    for roh in LD_RE.findall(html_):
        try:
            k = json.loads(roh)
        except ValueError as e:
            warn(f"{fname}: JSON-LD unlesbar ({e}) – Block verworfen")
            continue
        for knoten in (k.get("@graph") if isinstance(k, dict) and "@graph" in k else [k]):
            if not isinstance(knoten, dict):
                continue
            knoten.pop("@context", None)
            art = knoten.get("@type")
            if art == "BreadcrumbList":
                krumen = knoten
            elif art not in ("Organization", "WebSite") and haupt is None:
                haupt = knoten
    if haupt is None:   # z. B. rechtliches.html: bisher nur Brotkrumen
        haupt = {"@type": "WebPage", "name": titel, "description": beschreibung, "inLanguage": "de", "isAccessibleForFree": True}

    artikel = haupt.get("@type") == "Article"
    haupt["@id"] = url + ("#artikel" if artikel else "#seite")
    haupt["url"] = url
    haupt["publisher"] = {"@id": ORG_ID}
    haupt["isPartOf"] = {"@id": SITE_ID}
    if artikel:
        haupt["author"] = {"@id": ORG_ID}
        haupt["image"] = BILD
        if len(haupt.get("headline", "")) > 110:
            warn(f"{fname}: headline länger als 110 Zeichen")
    else:
        haupt["primaryImageOfPage"] = BILD
    graph = [haupt]
    if krumen:
        krumen["@id"] = url + "#brotkrumen"
        if not artikel:
            haupt["breadcrumb"] = {"@id": krumen["@id"]}
        graph.append(krumen)
    if fname == "begriffe.html":
        g = glossar(html_, url)
        if g:
            haupt["about"] = {"@id": g["@id"]}
            graph.append(g)
    if fname == "rechner.html":
        graph.append(rechner(html_, url, beschreibung))
    if fname in DATENSAETZE:
        graph.append(datensatz(site, fname, url, beschreibung))
    website = dict(WEBSITE)
    if fname == "index.html":
        website["description"] = beschreibung
    graph += [website, ORGANISATION]

    block = ('<script type="application/ld+json">'
             + json.dumps({"@context": "https://schema.org", "@graph": graph}, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
             + "</script>\n")
    if LD_RE.search(html_):
        erster = [True]

        def ersetze(m):
            if erster[0]:
                erster[0] = False
                return block
            return ""
        neu = LD_RE.sub(ersetze, html_)
    else:
        neu = html_.replace("</head>", block + "</head>", 1)
    neu = ROBOTS_RE.sub(ROBOTS_NEU, neu)
    with open(pfad, "w", encoding="utf-8") as f:
        f.write(neu)
    if url != eigen or fname in OHNE_SITEMAP:
        return None
    return url, haupt.get("dateModified")


def sitemap(site, seiten, behalten=()):
    """seiten: {URL: dateModified}. Reihenfolge und Rückfall-Datum aus der vorhandenen sitemap.xml;
    behalten: Adressen, deren Seite nicht verarbeitet werden konnte – ihr bisheriger Eintrag bleibt stehen."""
    pfad = os.path.join(site, "sitemap.xml")
    alt = []
    if os.path.isfile(pfad):
        alt = re.findall(r"<loc>([^<]+)</loc>(?:<lastmod>([^<]+)</lastmod>)?", open(pfad, encoding="utf-8").read())
    altdatum = dict(alt)
    for u in behalten:
        if u in altdatum:
            seiten.setdefault(u, None)
    reihenfolge = [u for u, _ in alt if u in seiten] + sorted(u for u in seiten if u not in altdatum)
    heute = datetime.date.today().isoformat()
    zeilen = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for u in reihenfolge:
        datum = seiten[u] or altdatum.get(u) or heute
        zeilen.append(f"  <url><loc>{u}</loc><lastmod>{datum}</lastmod></url>")
    zeilen.append("</urlset>")
    with open(pfad, "w", encoding="utf-8") as f:
        f.write("\n".join(zeilen) + "\n")
    neu = [u for u in seiten if u not in altdatum]
    weg = [u for u, _ in alt if u not in seiten]
    print(f"sitemap.xml: {len(reihenfolge)} Adressen" + (f", neu: {', '.join(neu)}" if neu else "")
          + (f", entfernt: {', '.join(weg)}" if weg else ""))


def main():
    site = sys.argv[1] if len(sys.argv) > 1 else "_site"
    if not os.path.isdir(site):
        raise SystemExit(f"Ordner nicht gefunden: {site}")
    seiten, behalten = {}, set()
    for fname in sorted(os.listdir(site)):
        if not fname.endswith(".html") or fname == "404.html":
            continue
        try:
            erg = seite(site, fname)
        except Exception as e:   # eine unerwartet gebaute Seite darf den Deploy nicht stoppen …
            warn(f"{fname}: nicht verarbeitet ({e})")
            behalten.add(BASE + ("" if fname == "index.html" else fname))   # … und nicht aus der Sitemap fallen
            continue
        if erg:
            seiten[erg[0]] = erg[1]
    print(f"seo.py: {len(seiten)} Seiten mit verknüpften strukturierten Daten")
    if seiten:
        sitemap(site, seiten, behalten)
    impressum = os.path.join(site, "rechtliches.html")
    if os.path.isfile(impressum):
        text = open(impressum, encoding="utf-8").read()
        for angabe in (ORGANISATION["legalName"], ORGANISATION["address"]["streetAddress"], ORGANISATION["email"]):
            if angabe not in text:
                warn(f"„{angabe}“ steht nicht (mehr) im Impressum – ORGANISATION in scripts/seo.py anpassen")


if __name__ == "__main__":
    main()
