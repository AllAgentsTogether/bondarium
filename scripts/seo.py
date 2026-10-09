#!/usr/bin/env python3
"""seo.py – strukturierte Daten, Robots-Angabe und Sitemap beim Deploy (seit 30.09.2026).

Läuft im GitHub-Workflow auf dem Veröffentlichungsordner, NACH kennzahlen.py, statische_tabellen.py und
rueckfallwerte.py (liest den Daten-Stand, den sie in die Seiten schreiben) und VOR llms.py, inline_data.py und dem Minify:

    python3 scripts/seo.py _site

Die Quell-HTML im Repository bleiben unverändert – dort pflegt jede Seite weiter nur ihren eigenen kleinen
JSON-LD-Block (Article/WebPage/CollectionPage + BreadcrumbList). Dieses Skript macht daraus je Seite EINEN
verknüpften Block (@graph):

  * Organisation und Website stehen auf jeder Seite gleich und mit fester Kennung (@id); Herausgeber, Autor und
    „Teil von“ verweisen darauf, statt die Angaben zu wiederholen. Die Website nennt die Suche (SearchAction).
  * Jede Seite hat einen WebPage-Knoten (<url>#seite) mit Brotkrumen und „Teil von“ Website. Auf
    Artikelseiten ist der Artikel (<url>#artikel) dessen Hauptinhalt (mainEntity / mainEntityOfPage) und trägt das
    Vorschaubild (image); primaryImageOfPage nur auf Nicht-Artikelseiten wie bisher – og-image.png ist auf allen Seiten
    gleich und im Seiteninhalt nicht zu sehen, also kein „Hauptbild“ eines Artikels (erst mit eigenen Bildern). Glossar,
    Rechner und Datensatz hängen über „about“ am Artikel. Jeder Verweis {"@id": …} zeigt auf einen Knoten im
    selben Block.
  * Artikel nennen die Glossar-Begriffe, auf die sie verlinken (mentions, höchstens 20, Name aus dem Glossar).
  * begriffe.html: jedes Glossar-Stichwort als DefinedTerm (Name, Erklärung, Sprungadresse); Klammerzusätze, die
    ein anderer Name für denselben Begriff sind, werden alternateName („Hochzinsanleihe (High Yield)“); geprüfte
    Wikidata-Kennungen als sameAs.
  * rechner.html: die Rechner als WebApplication.
  * Datenseiten (DATENSAETZE): die Zeitreihe als Dataset mit Zeitraum, Messgrößen und Quellen (isBasedOn, genau
    die Quellen aus dem sichtbaren Abschnitt „Datenquellen“ der Seite, siehe QUELLEN).

Datum (dateModified, <lastmod>, article:modified_time):
  * Seiten, deren Inhalt aus Daten-JSONs kommt (DATENSTAND): das jüngere von Quell-dateModified und dem Stand, den
    die gebaute Seite SICHTBAR nennt – das jüngste Datum in <p id="datastand">, auf der Startseite in #itab-stand, im
    Broker-Vergleich in <span data-bv="stand"> (TT.MM.JJJJ; „Monat JJJJ“ und „MM/JJJJ“ zählen als Monatsende; nie ein
    Datum in der Zukunft). Diese Stellen schreiben kennzahlen.py, statische_tabellen.py und rueckfallwerte.py nur
    zusammen mit den Werten. Fällt einer dieser Schritte aus, zeigt die Seite den alten Stand der Quell-HTML – dann
    bleibt das Quelldatum, statt einen frischen Stand zu melden, den das HTML ohne JavaScript nicht zeigt.
    Gegenprobe mit den Daten-JSONs: Datenstand = jüngstes Datum unter dem obersten Schlüssel "stand" (auch
    verschachtelt, z. B. {"DE": …, "US": …}) und unter jedem "latest": {"date": …}. Zeigt die Seite einen älteren
    Stand als die Daten oder gar keinen, gibt es eine Warnung (Rückfallwerte nicht erneuert).
    "updated" (Lauf-Datum des Datenbots) zählt bewusst NICHT.
  * Alle anderen Seiten behalten das dateModified aus der Quelle (bei Textänderungen dort von Hand nachziehen). Fehlt es
    einer Seite der Sitemap ganz, gibt es eine Warnung (seit 09.10.2026); <lastmod> bleibt dann beim bisherigen Eintrag.
  * Dataset (Zeitreihe, eingebettet per inline_data.py): dateModified = Datenstand der JSON (Ende von
    temporalCoverage), nicht das Datum der Seite – eine Textänderung ändert die Zeitreihe nicht.

Außerdem:
  * Robots-Angabe: „index, follow“ wird um max-image-preview:large, max-snippet:-1 ergänzt (große Vorschaubilder,
    Textausschnitt ohne Längengrenze).
  * Artikelseiten bekommen <meta property="article:modified_time"> mit dem dateModified.
  * Sichtbarer Stand (seit 04.10.2026): „Stand: TT.MM.JJJJ“ hinter der Lesezeit (<span class="stand-t">) wird auf das
    dateModified der Seite gesetzt – so zeigt die Seite nie ein anderes Datum als die strukturierten Daten.
  * sitemap.xml wird aus den Seiten neu geschrieben: jede Seite mit „index“ und eigener kanonischer Adresse steht
    drin, entfernte oder gesperrte Seiten fallen heraus, <lastmod> ist das dateModified der Seite (Regel oben).
    Die Reihenfolge der Datei im Repository bleibt erhalten, neue Seiten kommen ans Ende.

Außer dem Stand-Datum ändert nichts davon sichtbaren Text. Fehlt einer Seite etwas Erwartetes, gibt es eine Warnung –
der Deploy läuft.
"""
import calendar
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
WD = "https://www.wikidata.org/wiki/"

# Angaben wie im Impressum (rechtliches.html). Ändert sich dort etwas, hier nachziehen – das Skript warnt,
# wenn Firmenname, Straße, E-Mail oder Registernummer im Impressum nicht mehr vorkommen.
# Bewusst (noch) ohne description, publishingPrinciples und sameAs – erst, wenn Entitätssatz und Grundsätze-Seite stehen.
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
    "identifier": {"@type": "PropertyValue", "propertyID": "Handelsregister Amtsgericht Stuttgart", "value": "HRB 800184"},
    "areaServed": "DE",
    "knowsAbout": [{"@type": "Thing", "name": "Anleihe", "sameAs": WD + "Q11693"},
                   {"@type": "Thing", "name": "Staatsanleihe", "sameAs": WD + "Q2324820"},
                   {"@type": "Thing", "name": "Unternehmensanleihe", "sameAs": WD + "Q1662098"},
                   {"@type": "Thing", "name": "Anleihen-ETF"}],
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

# Zeitreihen der Datenseiten: Name, Beginn, Länder, Messgrößen; „json“ liefert den Datenstand (Ende des Zeitraums)
# und – wo vorhanden – die Quellentexte (Feld "quelle", siehe QUELLEN).
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

# Seiten, deren Inhalt aus Daten-JSONs kommt: dateModified = jüngeres von Quelldatum und dem sichtbaren Daten-Stand
# der gebauten Seite (siehe oben); die Dateien hier dienen der Gegenprobe (Warnung, wenn die Seite älter ist).
# Die vier Top-10-Seiten zeigen ihre festen Zeilen mit Kursen aus kurse-auswahl.json (statische_tabellen.py).
# anleihen-suche.html: Kursstand aus anleihen-kurse.json (= kstand in suchindex.json; suchindex.json selbst nicht –
# dort ist "stand" das Registerdatum, und die Datei hat über 5 MB).
_TOP10 = "kurse-auswahl.json"
DATENSTAND = {
    "renditen.html": ("renditen.json",),
    "unternehmensanleihen.html": ("unternehmen.json",),
    "zinskurve.html": ("zinskurve.json",),
    "realzins.html": ("realzins.json",),
    "risikoaufschlaege.html": ("risikoaufschlaege.json",),
    "langlaeufer.html": ("langlaeufer.json",),
    # seit 04.10.2026 (rueckfallwerte.py): zeigen nur den deutschen Stand – ohne Gegenprobe, sonst meldete der jüngere US-Stand in
    # zinskurve.json jeden Tag eine „veraltete“ Seite
    "zinsniveau.html": (),
    "fortgeschrittene.html": (),
    "bundeswertpapiere.html": (),                             # seit 04.10.2026 (statische_tabellen.py, Kurse der Bundesbank)
    "staatsanleihen-laufzeit.html": ("top10-staatsanleihen-laufzeit.json", _TOP10),
    "unternehmensanleihen-laufzeit.html": ("top10-unternehmensanleihen-laufzeit.json", _TOP10),
    "anleihen-laender.html": ("top10-staatsanleihen-laender.json", _TOP10),
    "unternehmensanleihen-laender.html": ("top10-unternehmensanleihen-laender.json", _TOP10),
    "anleihen-kupon.html": ("top10-anleihen-kupon.json",),
    "anleihen-etf.html": ("top10-anleihen-etfs.json",),
    "broker-vergleich.html": ("broker.json",),
    "index.html": ("kurse-auswahl.json",),
    "anleihen-suche.html": ("anleihen-kurse.json",),
}
# Nur diese Schlüssel unter "stand" zählen für Gegenprobe und Ende des Datensatzes (seit 09.10.2026, Technik-Test T-74):
# realzins.json nennt unter stand.linker auch den Stand der Realrenditen inflationsindexierter Bundesanleihen – die gehören
# nicht zur Reihe des Datensatzes (Rendite, Inflation, Realzins). Sonst meldete der Datensatz ein Ende, das Reihe und Seite
# nicht zeigen (07.10. statt 02.10.).
STAND_NUR = {"realzins.html": ("zins", "vpi")}
# Wo die gebaute Seite ihren Daten-Stand nennt: <p id="datastand">, Startseite <span id="itab-stand">, Broker-Vergleich
# <span data-bv="stand">. Nicht verschachtelt – der Inhalt reicht bis zum ersten schließenden Tag desselben Namens.
SICHTBAR_RE = re.compile(r'<(p|span)\b[^>]*?\b(?:id="(?:datastand|itab-stand)"|data-bv="stand")[^>]*>(.*?)</\1>', re.S)
MONATSNAMEN = ["Januar", "Februar", "März", "April", "Mai", "Juni", "Juli", "August", "September", "Oktober",
               "November", "Dezember"]
SICHTBAR_DATUM_RE = re.compile(r"\b(\d{1,2})\.(\d{1,2})\.(\d{4})\b|\b(" + "|".join(MONATSNAMEN) + r")\s+(\d{4})\b"
                               r"|(?<![\d.])(\d{1,2})/(\d{4})\b")


# ---------- Wikidata ----------
# Nur von Hand geprüfte Kennungen (Bezeichnung und Beschreibung passen zum Begriff, 02.10.2026). Im Zweifel keine:
# Ein falsches sameAs ordnet die Seite einem fremden Begriff zu. Bewusst ohne: „Anleihen-ETF“ (Q845477 ist ETF
# allgemein), „Bonität und Rating“ und „ISIN und WKN“ (Doppelbegriffe), „Investment Grade“ (Q2713035 ohne
# deutsche/englische Bezeichnung), mehrdeutige Treffer wie Rendite, Nennwert, Liquidität.
def _org(name, wikidata=None):
    o = {"@type": "Organization", "name": name}
    if wikidata:
        o["sameAs"] = WD + wikidata
    return o


BUBA = _org("Deutsche Bundesbank", "Q162222")
OECD = _org("OECD", "Q41550")
FED = _org("Federal Reserve System", "Q53536")
UST = _org("U.S. Department of the Treasury", "Q648666")
BOERSE_STUTTGART = _org("Börse Stuttgart", "Q558524")
DEUTSCHE_BOERSE = _org("Deutsche Börse", "Q157852")
FINANZAGENTUR = _org("Bundesrepublik Deutschland – Finanzagentur", "Q1202537")
IWF = _org("Internationaler Währungsfonds (IWF)")
CHINABOND = _org("ChinaBond (China Central Depository & Clearing)")
MOF_JAPAN = _org("Finanzministerium Japan")
JSDA = _org("Japan Securities Dealers Association (JSDA)")
RBA = _org("Reserve Bank of Australia")
NBER = _org("National Bureau of Economic Research (NBER)")
DESTATIS = _org("Statistisches Bundesamt (Destatis)")

# Glossar-Anker → Wikidata (begriffe.html#…)
WIKIDATA = {
    "anleihe": "Q11693", "staatsanleihe": "Q2324820", "unternehmensanleihe": "Q1662098", "pfandbrief": "Q13994919",
    "abgeltungsteuer": "Q320243", "nullkupon": "Q507494", "wandelanleihe": "Q1056625", "floater": "Q1429050",
    "inflationsindexiert": "Q359180", "leitzins": "Q1210392", "euribor": "Q648194", "realzins": "Q1140421",
    "hochzins": "Q1050279", "basispunkt": "Q750178", "medium-term-notes": "Q493012",
    "freistellungsauftrag": "Q1454742", "einlagensicherung": "Q376935", "bail-in": "Q15785285",
    "zinsaenderungsrisiko": "Q205273", "emittent": "Q1337949", "ausfallrisiko": "Q162714",
}
# Klammerzusätze der Stichwörter, die KEIN anderer Name für denselben Begriff sind (Unterarten, Erläuterungen).
# Zusätze, die mit einem Kleinbuchstaben beginnen („variabler Zins“, „allgemeines“, „und Hantel“), zählen ohnehin nicht.
KEIN_SYNONYM = {"WKN", "AT1", "Tier 2", "Hybrid", "Referenzzins"}
MENTIONS_MAX = 20

# ---------- Quellen der Datensätze (Dataset.isBasedOn) ----------
# GENAU die Quellen aus dem sichtbaren Abschnitt „Datenquellen“ der Seite. „beleg“ muss im Text dieses Abschnitts
# stehen, sonst fällt die Quelle mit Warnung weg (nie eine Quelle angeben, die die Seite nicht nennt).
# „json“: Name = Text aus dem Feld "quelle" der Datendatei (Schlüssel), sonst „name“. „von“: Herausgeber.
QUELLEN = {
    "renditen.html": [
        {"beleg": "OECD-Langfristzinsen", "von": [OECD],
         "name": "OECD-Langfristzinsen (über FRED), OECD Economic Outlook und OECD-Monatswerte"},
        {"beleg": "IWF International Financial Statistics", "von": [IWF],
         "name": "IWF International Financial Statistics (Indien 1970–1985)"},
        {"beleg": "ChinaBond", "von": [CHINABOND], "name": "ChinaBond-Renditekurve (China ab 2002)"},
        {"beleg": "U.S. Treasury", "von": [UST], "name": "U.S. Treasury: aktuelle Werte, börsentäglich (USA)"},
        {"beleg": "Deutsche Bundesbank", "von": [BUBA],
         "name": "Deutsche Bundesbank: 10-jährige Bundesanleihe mit jährlichem Kupon, aus der Zinsstruktur abgeleitet "
                 "(Deutschland, börsentäglich)"},
        {"beleg": "Finanzministerium Japan", "von": [MOF_JAPAN],
         "name": "Finanzministerium Japan: aktuelle Werte, börsentäglich (Japan)"},
    ],
    "unternehmensanleihen.html": [
        {"beleg": "HQM Corporate Bond Yield Curve", "von": [UST],
         "name": "U.S. Treasury, HQM Corporate Bond Yield Curve (Spot-Rendite 10 Jahre, monatlich, über FRED)"},
        {"beleg": "Japan Securities Dealers Association", "von": [JSDA],
         "name": "Japan Securities Dealers Association (JSDA): Rating-Matrix der Referenzkurse, Anleihen mit Rating "
                 "AA bzw. A, 10 Jahre Restlaufzeit"},
        {"beleg": "ChinaBond", "von": [CHINABOND],
         "name": "ChinaBond: Renditekurve Unternehmensanleihen AAA, Punkt 10 Jahre"},
        {"beleg": "Reserve Bank of Australia", "von": [RBA],
         "name": "Reserve Bank of Australia, Tabelle F3: Anleihen nichtfinanzieller Unternehmen mit Rating A bzw. BBB, "
                 "Zielrestlaufzeit 10 Jahre"},
    ],
    "zinskurve.html": [
        {"beleg": "Deutsche Bundesbank", "json": "DE", "von": [BUBA],
         "name": "Deutsche Bundesbank, Zinsstrukturkurve am Rentenmarkt (Svensson), Restlaufzeit 2 und 10 Jahre"},
        {"beleg": "Federal Reserve", "json": "US", "von": [FED],
         "name": "Federal Reserve, Statistical Release H.15, Treasury constant maturities 2 und 10 Jahre"},
        {"beleg": "NBER", "von": [NBER], "name": "NBER: Datierung der US-Rezessionen"},
    ],
    "realzins.html": [
        {"beleg": "OECD", "json": "zins", "von": [OECD, BUBA],
         "name": "Bund 10 Jahre: OECD Main Economic Indicators; Tageswert: Deutsche Bundesbank"},
        {"beleg": "Statistischen Bundesamts", "json": "vpi", "von": [DESTATIS],
         "name": "Verbraucherpreisindex (Destatis)"},
        {"beleg": "inflationsindexierten Bundesanleihen", "json": "linker", "von": [BUBA],
         "name": "Realrendite inflationsindexierter Bundesanleihen: Deutsche Bundesbank"},
        {"beleg": "Finanzagentur", "von": [FINANZAGENTUR], "art": "CreativeWork",
         "name": "Finanzagentur: Einstellung der Neuemission inflationsindexierter Bundesanleihen"},
    ],
    "risikoaufschlaege.html": [
        {"beleg": "OECD", "json": "laender", "von": [OECD],
         "name": "OECD, Main Economic Indicators, Long-term interest rates"},
        {"beleg": "HQM Corporate Bond Yield Curve", "json": "us", "von": [UST, OECD],
         "name": "U.S. Treasury, HQM Corporate Bond Yield Curve (über FRED) minus 10-jährige US-Staatsanleihe (OECD)"},
    ],
    "langlaeufer.html": [
        {"beleg": "Deutsche Bundesbank", "von": [BUBA],
         "name": "Deutsche Bundesbank: Kurse und Renditen der Bundesanleihen, börsentäglich"},
        # Emittenten und Anleihe-Angaben (Bedingungen, Stammdaten), keine Datenreihen → CreativeWork
        {"beleg": "Deutsche Finanzagentur", "von": [FINANZAGENTUR], "art": "CreativeWork", "name": "Deutsche Finanzagentur"},
        {"beleg": "Börse Stuttgart", "von": [BOERSE_STUTTGART],
         "name": "Börse Stuttgart: Wochenschlusskurse (einmalig erfasst)"},
        {"beleg": "Börse Frankfurt", "von": [DEUTSCHE_BOERSE],
         "name": "Börse Frankfurt (Deutsche Börse): Schlusskurse, täglich"},
        {"beleg": "Dipartimento del Tesoro", "von": [_org("Dipartimento del Tesoro")], "art": "CreativeWork",
         "name": "Dipartimento del Tesoro"},
        {"beleg": "Agence France Trésor", "von": [_org("Agence France Trésor")], "art": "CreativeWork",
         "name": "Agence France Trésor"},
        {"beleg": "OeBFA", "von": [_org("Österreichische Bundesfinanzierungsagentur (OeBFA)")], "art": "CreativeWork",
         "name": "OeBFA"},
        {"beleg": "TreasuryDirect", "von": [UST], "art": "CreativeWork", "name": "TreasuryDirect"},
        {"beleg": "Microsoft", "von": [_org("Microsoft")], "art": "CreativeWork", "name": "Microsoft"},
        {"beleg": "Cbonds", "von": [_org("Cbonds")], "art": "CreativeWork", "name": "Cbonds"},
    ],
}

LD_RE = re.compile(r'<script type="application/ld\+json">(.*?)</script>\n?', re.S)
ROBOTS_RE = re.compile(r'<meta name="robots" content="index, follow">')
ROBOTS_NEU = '<meta name="robots" content="index, follow, max-image-preview:large, max-snippet:-1, max-video-preview:-1">'
OG_TYPE_RE = re.compile(r'<meta property="og:type" content="article">\n?')
MODIFIED_RE = re.compile(r'<meta property="article:modified_time" content="[^"]*">')
TAG_RE = re.compile(r"\d{4}-\d{2}-\d{2}")
MONAT_RE = re.compile(r"\d{4}-\d{2}")


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


_JSON_CACHE = {}


def lade_json(site, name):
    schluessel = (site, name)
    if schluessel in _JSON_CACHE:
        return _JSON_CACHE[schluessel]
    try:
        with open(os.path.join(site, name), encoding="utf-8") as f:
            d = json.load(f)
    except Exception as e:
        warn(f"{name} nicht lesbar ({e})")
        d = None
    _JSON_CACHE[schluessel] = d
    return d


def heute():
    """Kalendertag in Deutschland (der Runner läuft in UTC); Rückfall: Tag des Rechners."""
    try:
        from zoneinfo import ZoneInfo
        return datetime.datetime.now(ZoneInfo("Europe/Berlin")).date()
    except Exception:
        return datetime.date.today()


def als_datum(wert, bis):
    """'JJJJ-MM-TT' → Datum (None, wenn nach „bis“); 'JJJJ-MM' → Monatsende, höchstens „bis“; sonst None."""
    s = wert.strip() if isinstance(wert, str) else ""
    try:
        if TAG_RE.fullmatch(s):
            d = datetime.date.fromisoformat(s)
            return d if d <= bis else None
        if MONAT_RE.fullmatch(s):
            j, m = int(s[:4]), int(s[5:])
            return min(datetime.date(j, m, calendar.monthrange(j, m)[1]), bis)
    except ValueError:
        pass
    return None


def datenstand(site, namen, nur=None):
    """Jüngster Datenstand (JJJJ-MM-TT) der Dateien „namen“ oder None.

    Gesammelt werden alle Werte unter dem obersten Schlüssel "stand" (auch verschachtelt, egal unter welchem inneren
    Schlüssel: {"DE": …, "US": …}, {"zins": …, "vpi": …}) und jedes "latest": {"date": …} (Länder, Reihen, Anleihen).
    nur: Ist "stand" ein Objekt, zählen nur diese inneren Schlüssel (STAND_NUR).
    Nicht gezählt: "updated" (Lauf-Datum des Datenbots) und tiefer liegende "stand"-Angaben anderer Bestandteile
    (z. B. "ezb": {"stand": …} in top10-anleihen-kupon.json = Datum der EZB-Liste, nicht der Kurse)."""
    bis = heute()
    funde = []

    def alle_werte(o):
        if isinstance(o, dict):
            for v in o.values():
                alle_werte(v)
        elif isinstance(o, list):
            for v in o:
                alle_werte(v)
        else:
            funde.append(o)

    def latest(o):
        if isinstance(o, dict):
            for k, v in o.items():
                if k == "latest":
                    funde.append(v.get("date") if isinstance(v, dict) else v)
                elif isinstance(v, (dict, list)):
                    latest(v)
        elif isinstance(o, list):
            for v in o:
                if isinstance(v, (dict, list)):
                    latest(v)

    for name in namen:
        d = lade_json(site, name)
        if not isinstance(d, dict):
            continue
        st = d.get("stand")
        alle_werte({k: st.get(k) for k in nur} if nur and isinstance(st, dict) else st)
        latest(d)
    daten = [x for x in (als_datum(f, bis) for f in funde) if x]
    return max(daten).isoformat() if daten else None


def sichtbarer_stand(html_):
    """Jüngstes Datum (JJJJ-MM-TT), das die gebaute Seite in ihrer Daten-Stand-Angabe zeigt (SICHTBAR_RE), oder None
    (Angabe fehlt oder ohne Datum, z. B. „Daten-Stand: wird geladen“). „TT.MM.JJJJ“ zählt als Tag, „Monat JJJJ“ und
    „MM/JJJJ“ als Monatsende (höchstens heute); ein Tag in der Zukunft zählt nicht."""
    bis = heute()
    daten = []
    for _, inhalt in SICHTBAR_RE.findall(html_):
        for m in SICHTBAR_DATUM_RE.finditer(klartext(inhalt)):
            if m.group(1):
                wert = f"{m.group(3)}-{int(m.group(2)):02d}-{int(m.group(1)):02d}"
            elif m.group(4):
                wert = f"{m.group(5)}-{MONATSNAMEN.index(m.group(4)) + 1:02d}"
            else:
                wert = f"{m.group(7)}-{int(m.group(6)):02d}"
            d = als_datum(wert, bis)
            if d:
                daten.append(d)
    return max(daten).isoformat() if daten else None


def stichwort(roh):
    """'Hochzinsanleihe (High Yield)' → ('Hochzinsanleihe', ['High Yield']). Klammerzusätze ohne Synonym
    (KEIN_SYNONYM, Kleinschreibung) bleiben im Namen stehen: 'Anleihenleiter (und Hantel)' → (unverändert, [])."""
    m = re.fullmatch(r"(.+?)\s*\(([^()]+)\)", roh)
    if not m:
        return roh, []
    syn = [s.strip() for s in m.group(2).split(",")]
    syn = [s for s in syn if s and s not in KEIN_SYNONYM and not s[0].islower()]
    return (m.group(1).strip(), syn) if syn else (roh, [])


def glossar_eintraege(html_):
    """begriffe.html: <div class="e" id="…"><dt>Stichwort</dt><dd><p>Erklärung</p>…</dd></div>
    → [(Anker, Name, Synonyme, Erklärung)]."""
    aus = []
    for anker, dt, dd in re.findall(r'<div class="e" id="([^"]+)"[^>]*>\s*<dt[^>]*>(.*?)</dt>\s*<dd[^>]*>(.*?)</dd>', html_, re.S):
        p = re.search(r"<p(?![^>]*class=\"links\")[^>]*>(.*?)</p>", dd, re.S)
        roh, text = klartext(dt), klartext(p.group(1)) if p else ""
        if not roh or not text:
            continue
        name, syn = stichwort(roh)
        aus.append((anker, name, syn, text))
    return aus


def glossar(html_, url):
    """begriffe.html → DefinedTermSet mit einem DefinedTerm je Stichwort."""
    set_id = url + "#glossar"
    begriffe = []
    for anker, name, syn, text in glossar_eintraege(html_):
        term = {"@type": "DefinedTerm", "@id": f"{url}#{anker}", "name": name, "description": text,
                "url": f"{url}#{anker}", "inDefinedTermSet": {"@id": set_id}}
        if syn:
            term["alternateName"] = syn
        if anker in WIKIDATA:
            term["sameAs"] = WD + WIKIDATA[anker]
        begriffe.append(term)
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


def quellen(site, fname, html_):
    """Dataset.isBasedOn: die Quellen aus QUELLEN, die im Abschnitt „Datenquellen“ der Seite stehen."""
    c = DATENSAETZE[fname]
    d = lade_json(site, c["json"]) or {}
    jq = d.get("quelle") if isinstance(d.get("quelle"), dict) else {}
    m = re.search(r'<details class="quellen"[^>]*>(.*?)</details>', html_, re.S)
    if not m:
        warn(f"{fname}: Abschnitt „Datenquellen“ (details.quellen) nicht gefunden – Quellen ausgelassen")
        return []
    sichtbar = klartext(m.group(1))
    aus = []
    for q in QUELLEN.get(fname, []):
        if q["beleg"] not in sichtbar:
            warn(f"{fname}: Quelle „{q['beleg']}“ steht nicht (mehr) im Abschnitt „Datenquellen“ – "
                 "ausgelassen, QUELLEN in scripts/seo.py anpassen")
            continue
        name = jq.get(q["json"]) if q.get("json") else None
        if not isinstance(name, str) or not name.strip():
            name = q["name"]
        aus.append({"@type": q.get("art", "Dataset"), "name": name.strip(),
                    "creator": q["von"][0] if len(q["von"]) == 1 else q["von"]})
    return aus


def datensatz(site, fname, url, beschreibung, html_, datum, stand):
    """Dataset der Datenseite. datum: dateModified der Seite (nur Rückfall); stand: Datenstand der JSON (Ende des
    Zeitraums) oder None. dateModified des Datensatzes = stand: Die Zeitreihe ändert sich mit neuen Daten, nicht mit
    einer Textänderung der Seite (sonst hieße es „aktualisiert 02.10.“ für eine Monatsreihe bis August)."""
    c = DATENSAETZE[fname]
    knoten = {"@type": "Dataset", "@id": url + "#daten", "name": c["name"], "description": beschreibung, "url": url,
              "inLanguage": "de", "isAccessibleForFree": True, "temporalCoverage": c["von"] + "/" + (stand or ".."),
              "variableMeasured": c["groessen"], "creator": {"@id": ORG_ID}, "publisher": {"@id": ORG_ID},
              "mainEntityOfPage": {"@id": url + "#seite"},
              # Search Console 03.10.2026: „Feld license fehlt“ – keine offene Lizenz (die Reihen stammen aus Drittquellen),
              # sondern der Verweis auf die geltenden Bedingungen: Datenquellen, Urheberrecht, Angaben ohne Gewähr
              "license": BASE + "rechtliches.html#haftung"}
    if c["laender"]:
        knoten["spatialCoverage"] = c["laender"]
    if stand or datum:
        knoten["dateModified"] = stand or datum
    basis = quellen(site, fname, html_)
    if basis:
        knoten["isBasedOn"] = basis
    return knoten


def erwaehnte_begriffe(fname, html_, glossar_namen):
    """Article.mentions: Glossar-Begriffe, auf die der Hauptteil verlinkt (Reihenfolge im Text, höchstens MENTIONS_MAX)."""
    m = re.search(r"<main\b.*?</main>", html_, re.S)
    if not m or not glossar_namen:
        return []
    aus = []
    for a in dict.fromkeys(re.findall(r'href="(?:/|\./)?begriffe\.html#([A-Za-z0-9_-]+)"', m.group(0))):
        if a not in glossar_namen:
            warn(f"{fname}: Verweis auf begriffe.html#{a} – diesen Glossar-Eintrag gibt es nicht")
            continue
        term = {"@type": "DefinedTerm", "@id": BASE + "begriffe.html#" + a, "name": glossar_namen[a],
                "url": BASE + "begriffe.html#" + a}
        if a in WIKIDATA:
            term["sameAs"] = WD + WIKIDATA[a]
        aus.append(term)
    return aus[:MENTIONS_MAX]


def seite(site, fname, glossar_namen=None):
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

    # Datum: Datenseiten bekommen den Stand, den sie sichtbar zeigen, wenn er jünger ist als das Quelldatum (siehe
    # DATENSTAND und Kopf dieser Datei). Der Datenstand der JSONs ist nur die Gegenprobe – und das Ende des Datensatzes.
    stand = datenstand(site, DATENSTAND[fname], STAND_NUR.get(fname)) if fname in DATENSTAND else None
    if fname in DATENSTAND:
        zeigt = sichtbarer_stand(html_)
        if not zeigt:
            warn(f"{fname}: kein sichtbarer Daten-Stand mit Datum (#datastand, #itab-stand, data-bv=\"stand\") – "
                 "dateModified bleibt beim Quelldatum")
        else:
            if stand and zeigt < stand:
                warn(f"{fname}: Seite zeigt Daten-Stand {zeigt}, die Daten reichen bis {stand} – Rückfallwerte im HTML "
                     "nicht erneuert? dateModified folgt dem sichtbaren Stand")
            if zeigt > str(haupt.get("dateModified") or "")[:10]:
                haupt["dateModified"] = zeigt
    datum = haupt.get("dateModified")

    # Jede Seite hat einen WebPage-Knoten (#seite); auf Artikelseiten ist der Artikel (#artikel) sein Hauptinhalt.
    if artikel:
        seite_k = {"@type": "WebPage", "name": titel, "description": beschreibung, "inLanguage": "de"}
        for k in ("datePublished", "dateModified"):
            if haupt.get(k):
                seite_k[k] = haupt[k]
        haupt["@id"] = url + "#artikel"
        haupt["url"] = url
        haupt["publisher"] = {"@id": ORG_ID}
        haupt["author"] = {"@id": ORG_ID}
        haupt["image"] = BILD
        haupt["isPartOf"] = {"@id": url + "#seite"}
        haupt["mainEntityOfPage"] = {"@id": url + "#seite"}
        if len(haupt.get("headline", "")) > 110:
            warn(f"{fname}: headline länger als 110 Zeichen")
        seite_k["mainEntity"] = {"@id": haupt["@id"]}
        graph = [seite_k, haupt]
    else:
        seite_k = haupt
        seite_k.pop("mainEntityOfPage", None)
        # name und description wie auf Artikelseiten aus <title> und meta description (seit 09.10.2026, Technik-Test T-73:
        # CollectionPages hatten nur headline, beobachten.html eine ältere description als die Seite)
        seite_k.setdefault("name", titel)
        if beschreibung:
            seite_k["description"] = beschreibung
        graph = [seite_k]
    seite_k["@id"] = url + "#seite"
    seite_k["url"] = url
    seite_k["publisher"] = {"@id": ORG_ID}
    seite_k["isPartOf"] = {"@id": SITE_ID}
    if not artikel:   # Artikel: Vorschaubild nur als Article.image (og-image.png ist auf der Seite nicht zu sehen)
        seite_k["primaryImageOfPage"] = BILD
    if seite_k.get("@type") == "AboutPage":
        seite_k["mainEntity"] = {"@id": ORG_ID}
    if krumen:
        krumen["@id"] = url + "#brotkrumen"
        seite_k["breadcrumb"] = {"@id": krumen["@id"]}
        graph.append(krumen)

    # Worum es geht: Glossar, Rechner, Datensatz – Knoten im selben Block, „about“ am Hauptinhalt
    bezug = []
    if fname == "begriffe.html":
        g = glossar(html_, url)
        if g:
            bezug.append(g)
    if fname == "rechner.html":
        bezug.append(rechner(html_, url, beschreibung))
    if fname in DATENSAETZE:
        bezug.append(datensatz(site, fname, url, beschreibung, html_, datum, stand))
    if bezug:
        haupt["about"] = [{"@id": b["@id"]} for b in bezug]
        graph += bezug
    if artikel and fname != "begriffe.html":
        erwaehnt = erwaehnte_begriffe(fname, html_, glossar_namen or {})
        if erwaehnt:
            haupt["mentions"] = erwaehnt
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
    if artikel and datum:
        neu = aenderungsdatum(neu, datum)
    neu = stand_anzeige(neu, datum, fname)
    with open(pfad, "w", encoding="utf-8") as f:
        f.write(neu)
    if url != eigen or fname in OHNE_SITEMAP:
        return None
    if not datum:   # seit 09.10.2026 (Technik-Test T-58): nicht mehr still beim alten <lastmod> der Repo-Sitemap bleiben
        warn(f"{fname}: kein dateModified im JSON-LD – <lastmod> bleibt beim bisherigen Eintrag der Sitemap; "
             "datePublished/dateModified in der Quell-HTML ergänzen")
    return url, datum


STAND_T_RE = re.compile(r'(<span class="stand-t">Stand: )(\d{2}\.\d{2}\.\d{4})(</span>)')


def stand_anzeige(html_, datum, fname):
    """„Stand: TT.MM.JJJJ“ hinter der Lesezeit = dateModified der Seite (seit 04.10.2026, SEO-Runde 2)."""
    try:
        soll = datetime.date.fromisoformat(str(datum)[:10]).strftime("%d.%m.%Y")
    except (TypeError, ValueError):
        return html_

    def ersetze(m):
        if m.group(2) != soll:
            print(f"{fname}: sichtbarer Stand {m.group(2)} → {soll} (dateModified)")
        return m.group(1) + soll + m.group(3)
    return STAND_T_RE.sub(ersetze, html_, count=1)


def aenderungsdatum(html_, datum):
    """<meta property="article:modified_time"> im Kopf setzen (nach og:type, sonst vor </head>)."""
    tag = f'<meta property="article:modified_time" content="{htmllib.escape(str(datum), quote=True)}">'
    kopfteil, trenner, rest = html_.partition("</head>")
    if not trenner:
        return html_
    if MODIFIED_RE.search(kopfteil):
        kopfteil = MODIFIED_RE.sub(tag, kopfteil, count=1)
    else:
        m = OG_TYPE_RE.search(kopfteil)
        if m:
            kopfteil = kopfteil[:m.end()] + ("" if m.group(0).endswith("\n") else "\n") + tag + "\n" + kopfteil[m.end():]
        else:
            kopfteil += tag + "\n"
    return kopfteil + trenner + rest


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
    glossar_namen = {}
    try:
        with open(os.path.join(site, "begriffe.html"), encoding="utf-8") as f:
            glossar_namen = {a: name for a, name, _, _ in glossar_eintraege(f.read())}
    except Exception as e:
        warn(f"begriffe.html nicht lesbar ({e}) – Artikel ohne mentions")
    for fname in sorted(os.listdir(site)):
        if not fname.endswith(".html") or fname == "404.html":
            continue
        try:
            erg = seite(site, fname, glossar_namen)
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
        for angabe in (ORGANISATION["legalName"], ORGANISATION["address"]["streetAddress"], ORGANISATION["email"],
                       ORGANISATION["identifier"]["value"]):
            if angabe not in text:
                warn(f"„{angabe}“ steht nicht (mehr) im Impressum – ORGANISATION in scripts/seo.py anpassen")


if __name__ == "__main__":
    main()
