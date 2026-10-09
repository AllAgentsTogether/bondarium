#!/usr/bin/env python3
"""pruefen.py – Qualitätsprüfung des Veröffentlichungsordners vor dem Upload (seit 30.09.2026).

    python3 scripts/pruefen.py _site

Bricht mit Fehler ab (Deploy wird rot, nichts geht live) bei:
  - internen Links auf Seiten, die es nicht gibt
  - (seit 09.10.2026) Verweisen auf Dateien, die im Bau fehlen: src, href (außer Seiten), srcset und CSS-url() der Seiten,
    Server-Steckbriefe und Stylesheets – ohne „?v=…“ gegen den Ordner geprüft (fehlendes Skript, Stylesheet oder Bild)
  - (seit 09.10.2026) einer *.json im Bau, die sich nicht als JSON lesen lässt (Daten der Seiten, kurse/, anleihen/ …)
  - Resten des alten Namens (METALCONCRETE / metalconcrete.de) im ausgelieferten Text
  - Seiten für Suchmaschinen (ohne „noindex“) ohne <title>, ohne oder mit fremder kanonischer Adresse,
    oder mit unlesbarem JSON-LD – das kostet Auffindbarkeit, ohne dass man es der Seite ansieht
Warnt (Deploy läuft weiter) bei:
  - Platzhaltern wie [VORNAME NACHNAME] oder [E-MAIL-ADRESSE] (Impressum noch nicht befüllt)
  - Anker-Links (#…) auf Ziele, die es auf der Zielseite nicht gibt
  - Angeboten in broker.json, deren „bis“-Datum abgelaufen ist oder in weniger als 14 Tagen abläuft
  - Titeln über 60 Zeichen, Beschreibungen unter 70 oder über 160 Zeichen, fehlender Beschreibung,
    keiner oder mehreren <h1>, doppelt vergebenen Titeln oder Beschreibungen
Server-Steckbriefe (seit 09.10.2026): steckbrief/<ISIN>.html wird unter anleihe.html?isin=<ISIN> ausgeliefert – Links und
Dateien werden deshalb gegen den Stammordner aufgelöst, kanonische Adresse ist anleihe.html?isin=<ISIN>. Fehler wie oben
(je Ursache eine Zeile), alle übrigen Regeln als Sammelzeilen „Server-Steckbriefe: …“; die SEO-Regeln unten gelten auch für
sie (Technik-Test 08.10.2026, T-76).
Anleihen-Tabellen (seit 03.10.2026, Konzept „Einheitliche Anleihen-Angaben“, docs/ANLEIHEN-ANGABEN.md):
  - Fehler, wenn der Katalog in felder.js kein lesbares JSON ist oder eine Anleihen-Tabelle im ausgelieferten HTML ihre Spalten
    nicht in der Reihenfolge der Gesamtliste zeigt oder einen Spaltenkopf anders nennt als der Katalog (Kurzform)
Seit 02.10.2026 außerdem (SEO-Prüfung; je Regel EINE Sammelzeile mit Anzahl und höchstens 5 Beispielen, nur auf Seiten
für Suchmaschinen):
  - Ladetext („wird geladen“, „lädt …“) im ausgelieferten Text – ohne JavaScript sieht ihn jeder Crawler (Bereiche mit dem
    Attribut hidden zählen seit 09.10.2026 nicht: Sie sind ohne JavaScript unsichtbar)
  - Seitenskript ändert link[rel=canonical], obwohl ein fester Canonical im HTML steht
  - Titel breiter als 580 px bzw. Beschreibung breiter als 990 px im Suchergebnis (Schätzung mit Arial-Zeichenbreiten)
  - Zusage- und Empfehlungswörter („lohnt sich“, „garantiert“, „risikolos“, „beste“, „sichere Rendite“ …) in Titel,
    Beschreibung, H1 und Haupttext; Ausnahmen in AUSNAHMEN_ZUSAGE
  - Hauswortschatz (Firma, Chart, Diagramm, Kupontermin, Endfälligkeit), alte Menünamen in H1 oder Brotkrumen,
    „&“ in H1/H2
  - JSON-LD: datePublished nach dateModified, letzte Brotkrume ≠ kanonische Adresse, zweite Brotkrume kein Menüname,
    @id-Verweis ohne Knoten; Artikel ohne datePublished nur als Hinweis
  - Sitemap-lastmod jünger als dateModified der Seite; sichtbarer „Daten-Stand“ mehr als 7 Tage älter oder neuer als
    dateModified
"""
import datetime
import html as htmllib
import json
import os
import posixpath
import re
import sys
import urllib.parse
from html.parser import HTMLParser

site = sys.argv[1] if len(sys.argv) > 1 else "_site"
seiten = {f for f in os.listdir(site) if f.endswith(".html")}
# Server-Steckbriefe (scripts/steckbriefe.py): Datei → Adresse, unter der sie ausgeliefert wird
SB_ORDNER = "steckbrief"
steckbriefe = {}
if os.path.isdir(os.path.join(site, SB_ORDNER)):
    for d in sorted(os.listdir(os.path.join(site, SB_ORDNER))):
        m = re.fullmatch(r"([A-Z]{2}[A-Z0-9]{9}[0-9])\.html", d)
        if m:
            steckbriefe[f"{SB_ORDNER}/{d}"] = "anleihe.html?isin=" + m.group(1)
ids = {}
fehler, warnungen, hinweise = [], [], []
sb_fehler = {}   # Steckbriefe: Fehlermeldung → [Adressen] (eine Zeile je Ursache statt einer je Steckbrief)
funde = {}       # Regel → [(Datei, Ausschnitt)] – Sammelzeilen (SEO-Warnungen, Warnungen der Steckbriefe)
HREF = re.compile(r'href="(?!https?:|mailto:|tel:|data:|javascript:|#)(/|\./)?([^"#?]+\.html)?(?:\?[^"#]*)?(?:#([^"]+))?"')
PLATZ = re.compile(r'\[(?:VORNAME|NACHNAME|STRASSE|PLZ|E-MAIL|TELEFON)[^\]]*\]')


def lies_html(f):
    with open(os.path.join(site, f), encoding="utf-8") as d:
        return d.read()


def sb_fehler_add(meldung, adresse):
    sb_fehler.setdefault(meldung, []).append(adresse)


def fund(regel, datei, text=""):
    funde.setdefault(regel, []).append((datei, text))


for f in list(seiten) + list(steckbriefe):
    ids[f] = set(re.findall(r'\sid="([^"]+)"', lies_html(f)))

for f in sorted(seiten) + list(steckbriefe):
    html = lies_html(f)
    sb = steckbriefe.get(f)
    ohne_skript = re.sub(r"<script\b[^>]*>.*?</script>", "", html, flags=re.S)
    for wurzel, ziel, anker in HREF.findall(ohne_skript):
        if not ziel and wurzel:   # „/#akademie“ oder „./#akademie“ = Startseite
            ziel = "index.html"
        if ziel and ziel not in seiten:
            if sb:
                sb_fehler_add(f"Link auf fehlende Seite {ziel}", sb)
            else:
                fehler.append(f"{f}: Link auf fehlende Seite {ziel}")
        elif anker and "$" not in anker and anker not in ids.get(ziel or f, set()):
            if sb:
                fund("Server-Steckbriefe: Anker fehlt", sb, f"#{anker} auf {ziel or 'der Seite'}")
            else:
                warnungen.append(f"{f}: Anker #{anker} fehlt auf {ziel or f}")
    if re.search(r"METALCONCRETE|metalconcrete\.de", ohne_skript, re.I):
        if sb:
            sb_fehler_add("alter Name METALCONCRETE im Text", sb)
        else:
            fehler.append(f"{f}: alter Name METALCONCRETE im Text")
    for p in sorted(set(PLATZ.findall(ohne_skript))):
        if sb:
            fund("Server-Steckbriefe: Platzhalter", sb, p)
        else:
            warnungen.append(f"{f}: Platzhalter {p}")

# ---------- Dateien im Bau (seit 09.10.2026, T-76): Verweise der Seiten, Steckbriefe und Stylesheets; lesbares JSON ----------
URL_CSS = re.compile(r"""url\(\s*['"]?([^'")]+)""")


class Verweise(HTMLParser):
    """src, href (außer Seiten – die prüft der Link-Teil oben), srcset und style-url() aller Tags."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.refs = []

    def handle_starttag(self, tag, attrs):
        a = {k: v for k, v in attrs if v}
        for k in ("src", "href"):
            if k in a and not (k == "href" and re.search(r"\.html(?:[?#]|$)", a[k])):
                self.refs.append(a[k])
        for teil in (a.get("srcset") or "").split(","):
            if teil.strip():
                self.refs.append(teil.strip().split()[0])
        self.refs += URL_CSS.findall(a.get("style") or "")

    handle_startendtag = handle_starttag


def lokaler_pfad(ref):
    """Pfad im Bau zu einem Verweis (ohne ?v=… und #…, gegen den Stammordner) oder None bei fremden Adressen."""
    ref = htmllib.unescape(ref.strip())
    if not ref or re.match(r"^(?:[a-z][a-z0-9+.-]*:|//|#)", ref, re.I) or "${" in ref or "{{" in ref:
        return None
    pfad = urllib.parse.unquote(ref.split("#")[0].split("?")[0])
    pfad = re.sub(r"^(?:\./|/)+", "", pfad)
    if not pfad or pfad.endswith("/"):
        return None
    return posixpath.normpath(pfad)


fehlt_datei = {}   # Pfad → [Seiten]
for f in sorted(seiten) + list(steckbriefe):
    # Inhalt der Skripte weg (Zeichenketten im Code sind keine Verweise), das Tag bleibt – <script src="…"> zählt
    html = re.sub(r"(<script\b[^>]*>).*?(</script>)", r"\1\2", lies_html(f), flags=re.S)
    v = Verweise()
    v.feed(html)
    v.close()
    for ref in v.refs + URL_CSS.findall(html):
        pfad = lokaler_pfad(ref)
        if pfad and not os.path.isfile(os.path.join(site, pfad)):
            fehlt_datei.setdefault(pfad, []).append(steckbriefe.get(f, f))
for f in sorted(x for x in os.listdir(site) if x.endswith(".css")):
    for ref in URL_CSS.findall(lies_html(f)):
        pfad = lokaler_pfad(ref)
        if pfad and not os.path.isfile(os.path.join(site, pfad)):
            fehlt_datei.setdefault(pfad, []).append(f)
for pfad, wo in sorted(fehlt_datei.items()):
    wo = sorted(set(wo))
    fehler.append(f"Verweis auf fehlende Datei {pfad} (in {', '.join(wo[:5])}" + (f" und {len(wo) - 5} weiteren" if len(wo) > 5 else "") + ")")
kaputt = []
for wurzel, _, dateien in os.walk(site):
    for d in sorted(dateien):
        if d.endswith(".json"):
            pfad = os.path.join(wurzel, d)
            try:
                with open(pfad, encoding="utf-8") as j:
                    json.load(j)
            except (OSError, ValueError) as e:
                kaputt.append(f"{os.path.relpath(pfad, site)} ({e})")
for k in kaputt:
    fehler.append(f"JSON unlesbar: {k}")

# ---------- Auffindbarkeit (seit 30.09.2026): Titel, Beschreibung, kanonische Adresse, H1, strukturierte Daten ----------
BASE = "https://www.bondarium.de/"
# Steckbrief: eine kanonische Adresse je ISIN, gesetzt vom Seitenskript (bzw. per Link-Header) – fehlt der feste Canonical
# im HTML, ist das dort Absicht und nur ein Hinweis (seit 02.10.2026).
JS_CANONICAL = {"anleihe.html"}
CANONICAL_JS = re.compile(r"""link\[rel=\\?["']?canonical\\?["']?\]""")
titel_von, text_von = {}, {}
for f in sorted(seiten) + list(steckbriefe):
    html = lies_html(f)
    sb = steckbriefe.get(f)
    kopf = html.split("</head>")[0]
    if f == "404.html" or re.search(r'<meta name="robots" content="[^"]*noindex', kopf):
        continue
    # Steckbriefe: Fehler je Ursache in einer Zeile, Warnungen als Sammelzeilen je Regel
    def warn(regel, text, f=f, sb=sb):
        if sb:
            fund(f"Server-Steckbriefe: {regel}", sb, text)
        else:
            warnungen.append(f"{f}: {text}")

    def feh(text, f=f, sb=sb):
        if sb:
            sb_fehler_add(text.replace(sb, "<Adresse>"), sb)
        else:
            fehler.append(f"{f}: {text}")
    name = sb or f
    m = re.search(r"<title>(.*?)</title>", kopf, re.S)
    titel = htmllib.unescape(m.group(1)).strip() if m else ""
    if not titel:
        feh("<title> fehlt")
    else:
        titel_von.setdefault(titel, []).append(name)
        if len(titel) > 60:
            warn("Titel über 60 Zeichen", f"Titel hat {len(titel)} Zeichen (über 60 wird er im Suchergebnis abgeschnitten)")
    m = re.search(r'<meta name="description" content="([^"]*)"', kopf)
    text = htmllib.unescape(m.group(1)).strip() if m else ""
    if not text:
        warn("Beschreibung fehlt", "Beschreibung (meta description) fehlt")
    else:
        text_von.setdefault(text, []).append(name)
        if not 70 <= len(text) <= 160:
            warn("Beschreibung nicht 70 bis 160 Zeichen", f"Beschreibung hat {len(text)} Zeichen (gut sind 70 bis 160)")
    m = re.search(r'<link rel="canonical" href="([^"]+)"', kopf)
    eigen = BASE + (sb or ("" if f == "index.html" else f))
    if not m and f in JS_CANONICAL and CANONICAL_JS.search(html):
        hinweise.append(f"{f}: kein fester Canonical – die kanonische Adresse setzt das Seitenskript (je ISIN)")
    elif not m:
        feh("kanonische Adresse (link rel=canonical) fehlt")
    elif m.group(1) != eigen:
        feh(f"kanonische Adresse zeigt auf {m.group(1)} statt auf {eigen}")
    h1 = len(re.findall(r"<h1\b", re.sub(r"<script\b[^>]*>.*?</script>", "", html, flags=re.S)))
    if h1 != 1:
        warn("nicht genau eine <h1>", f"{h1} Hauptüberschriften (<h1>) statt einer")
    for roh in re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, re.S):
        try:
            json.loads(roh)
        except ValueError as e:
            feh(f"JSON-LD unlesbar ({e})")
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

# ---------- SEO-Warnungen (seit 02.10.2026): nur Warnungen, je Regel eine Sammelzeile (funde, fund() oben) ----------
INLINE = r"abbr|b|em|i|mark|strong|sub|sup|wbr"   # Auszeichnung im Wort: ohne Leerraum entfernen, alle übrigen Tags trennen


LEER = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}


class Versteckt(HTMLParser):
    """Bereiche (Anfang, Ende) der Elemente mit dem Attribut hidden – ohne JavaScript unsichtbar (z. B. der Inhalt des
    Server-Steckbriefs bis zum Laden der Kurse, SEO-09). Verschachtelte Elemente gleichen Namens zählt ein Stapel mit."""

    def __init__(self, text):
        super().__init__(convert_charrefs=False)
        self.text, self.stapel, self.bereiche, self.offen = text, [], [], None
        self.zeilen = [0] + [m.end() for m in re.finditer("\n", text)]
        self.feed(text)
        self.close()
        if self.offen:
            self.bereiche.append((self.offen[1], len(text)))

    def _pos(self):
        z, s = self.getpos()
        return self.zeilen[z - 1] + s

    def handle_starttag(self, tag, attrs):
        if tag in LEER:
            return
        if self.offen is None and any(k == "hidden" for k, _ in attrs):
            self.offen = (len(self.stapel), self._pos())
        self.stapel.append(tag)

    def handle_startendtag(self, tag, attrs):
        pass   # <x … /> hat keinen Inhalt

    def handle_endtag(self, tag):
        if tag not in self.stapel:
            return
        while self.stapel.pop() != tag:
            pass
        if self.offen and len(self.stapel) <= self.offen[0]:
            ende = self.text.find(">", self._pos())
            self.bereiche.append((self.offen[1], ende + 1 if ende >= 0 else len(self.text)))
            self.offen = None


def ohne_versteckte(s):
    if not re.search(r"<[a-z][^>]*\shidden(?=[\s=/>])", s, re.I):
        return s
    for a, b in reversed(Versteckt(s).bereiche):
        s = s[:a] + " " + s[b:]
    return s


def klartext(s):
    """Sichtbarer Text eines HTML-Stücks: ohne Skripte, Stile, Vorlagen, Kommentare und (seit 09.10.2026) ohne Bereiche mit
    dem Attribut hidden."""
    s = re.sub(r"<(script|style|template)\b[^>]*>.*?</\1\s*>", " ", s, flags=re.S | re.I)
    s = ohne_versteckte(s)
    s = re.sub(r"<!--.*?-->", " ", s, flags=re.S)
    s = re.sub(rf"</?(?:{INLINE})\b[^>]*>", "", s, flags=re.I)
    s = re.sub(r"<[^>]+>", " ", s)
    s = htmllib.unescape(s).replace("\u00ad", "").replace("\u00a0", " ")
    return re.sub(r"\s+([.,;:!?])", r"\1", re.sub(r"\s+", " ", s)).strip()


def ausschnitt(text, m, rand=30):
    a, b = max(0, m.start() - rand), min(len(text), m.end() + rand)
    return "„" + ("…" if a else "") + text[a:b].strip() + ("…" if b < len(text) else "") + "“"


def datum(wert):
    try:
        return datetime.date.fromisoformat(str(wert)[:10])
    except ValueError:
        return None


# Zeichenbreiten von Arial in 1/2048 em (aus Arial.ttf gemessen, 02.10.2026). Google zeigt den Titel in etwa 20 px, die
# Beschreibung in etwa 14 px Arial und kürzt ab rund 580 bzw. 990 px; unbekannte Zeichen zählen wie eine Ziffer.
ARIAL = {391: "'", 455: "ijl‚‘’", 532: "|", 569: " !,./:;I[\\]ftíìî", 682: "()-`r„“”·²³", 684: "{}", 717: "•", 727: '"',
         797: "*", 819: "°", 961: "^", 1024: "Jcksvxyzç", 1124: "≥≤",
         1139: "#$0123456789?L_abdeghnopquäöüéèêáàâóòôúùûñ–€«»§", 1196: "+<=>~×−", 1251: "FTZß", 1366: "&ABEKPSVXYÄÉÈ",
         1479: "CDHNRUwÜ", 1509: "©®", 1593: "GOQÖ", 1706: "Mm", 1821: "%", 1933: "W", 2048: "—…→™", 2079: "@"}
BREITE = {z: w for w, zeichen in ARIAL.items() for z in zeichen}


def pixel(text, px):
    return round(sum(BREITE.get(z, 1139) for z in text.replace("\u00ad", "").replace("\u00a0", " ")) * px / 2048)


# Zusage- und Empfehlungswörter (Hausregel): mit Wortgrenzen, damit Fachbegriffe wie „Einlagensicherung“, „Garantiegeber“
# oder „Staatsgarantie“ nicht treffen; verneint („nicht garantiert“, „keine Garantie“) ist es eine Beschreibung.
ZUSAGE = [
    ("lohnt sich", re.compile(r"\blohn(?:t|en|end|ende|enden|ender|endes)\b", re.I)),
    ("garantiert", re.compile(r"\bgarantier(?:t|te|ten|tem|ter|tes|en)\b", re.I)),
    ("Garantie", re.compile(r"\bGarantien?\b")),
    ("risikolos", re.compile(r"\brisikolos(?:e|en|em|er|es)?\b", re.I)),
    ("beste", re.compile(r"\bbeste[nmrs]?\b(?!\s+Bonität)", re.I)),
    ("sichere Rendite", re.compile(r"\bsicher(?:e|er|en|em|es|ste|sten|ster)?\s+(?:Rendite|Zinsen|Zins|Anlage|Geldanlage|Ertrag)\b", re.I)),
    ("sicherste", re.compile(r"\bsicherste[nmrs]?\b", re.I)),
    ("beliebteste", re.compile(r"\bbeliebteste[nmrs]?\b", re.I)),
]
VERNEINT = re.compile(r"\b(?:nicht|kein|keine|keinen|keiner|keinem|nie|ohne)\s+(?:\w+\s+)?$", re.I)
# Fachbegriffe und beschreibende Stellen, die nichts versprechen: (Datei oder "*", Text im Umfeld des Treffers).
AUSNAHMEN_ZUSAGE = [
    ("*", "staatlich garantiert"),          # Emittenten mit Staatsgarantie (EZB-Liste)
    ("*", "Besicherung oder Garantie"),     # Merkmal im Steckbrief bzw. in der Suche
    ("*", "AAA (beste"),                    # Ratingskala
    ("*", "die beste Note"),                # Ratingskala
    ("*", "das beste der von ihr anerkannten"),   # EZB-Regel: bestes Rating der anerkannten Agenturen
    ("*", "ist die beste Gruppe"),          # Ratingskala: Bonität laut EZB im Server-Steckbrief (seit 09.10.2026 geprüft)
    ("*", "sich für ihn lohnt"),            # Kündigung: Abwägung des Emittenten, keine Aussage über den Anleger
]
WORTSCHATZ = [   # (Fundwort → Hauswort), im sichtbaren Text
    ("Firma/Firmen → Unternehmen", re.compile(r"\bFirm(?:a|en)\b")),
    ("Chart → Schaubild", re.compile(r"\bCharts?\b")),
    ("Diagramm → Schaubild", re.compile(r"\bDiagramm(?:e|en|s)?\b")),
    ("Kupontermin → Zinstermin", re.compile(r"\bKupontermin(?:e|en|s)?\b")),
    ("Endfälligkeit → Fälligkeit", re.compile(r"\bEndfälligkeit\b")),
]
ALTE_NAMEN = re.compile(r"\b(?:Verstehen|Entscheiden|Vertiefen)\b")   # Menüstufen bis 01.10.2026
LADEN = re.compile(r"\b(?:wird|werden)\s+geladen\b|\blädt\s*(?:…|\.\.\.)|\bLaden\s*(?:…|\.\.\.)")


def menuenamen():
    """Zulässige zweite Brotkrume: die Menüs aus scripts/nav.py (nur Konstanten, nav.py schreibt beim Import nichts),
    dazu „Über uns“ und „Rechtliches“ (Fußzeile). Rückfall: die Namen vom 01.10.2026."""
    namen = {"Über uns", "Rechtliches"}
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import nav
        return namen | {nav.AKADEMIE[0], nav.KONTO[0]} | {m[0] for m in nav.MENUS}
    except Exception:
        return namen | {"Akademie", "Anleihen", "Kaufen", "Zinsen", "Mein Bondarium"}


MENUE = menuenamen()
ohne_datum = []   # Artikel ohne datePublished (Hinweis)
geaendert = {}    # Datei → dateModified (für Sitemap und Daten-Stand)
# Stand-Angabe einer Datenseite: <p id="datastand">, Startseite #itab-stand, Broker-Vergleich data-bv="stand"
STAND_STELLE = re.compile(r'<(p|span)\b[^>]*?\b(?:id="(?:datastand|itab-stand)"|data-bv="stand")[^>]*>(.*?)</\1>', re.S)


def seo_pruefung(f, html, adresse=None):
    """SEO-Warnungen einer Seite (nur Seiten für Suchmaschinen). adresse: Server-Steckbrief, ausgeliefert unter dieser
    Adresse (anleihe.html?isin=…) – sie steht dann in den Meldungen, gilt als kanonische Adresse und als Schlüssel für die
    Sitemap-Prüfung."""
    kopf = html.split("</head>")[0]
    if f == "404.html" or re.search(r'<meta name="robots" content="[^"]*noindex', kopf):
        return
    if adresse:
        f = adresse
    eigen = BASE + ("" if f == "index.html" else f)
    m = re.search(r"<title>(.*?)</title>", kopf, re.S)
    titel = htmllib.unescape(m.group(1)).strip() if m else ""
    m = re.search(r'<meta name="description" content="([^"]*)"', kopf)
    beschreibung = htmllib.unescape(m.group(1)).strip() if m else ""
    m = re.search(r"<h1\b[^>]*>(.*?)</h1>", re.sub(r"<script\b[^>]*>.*?</script>", "", html, flags=re.S), re.S)
    h1 = klartext(m.group(1)) if m else ""
    m = re.search(r"<main\b[^>]*>(.*)</main>", html, re.S)
    haupt = klartext(m.group(1)) if m else ""
    sichtbar = klartext(html.split("</head>", 1)[-1])

    # Ladetext und Canonical per Skript
    m = LADEN.search(sichtbar)
    if m:
        fund("Ladetext im ausgelieferten HTML (ohne JavaScript sichtbar)", f, ausschnitt(sichtbar, m))
    if re.search(r'<link rel="canonical"', kopf) and not adresse:   # Steckbrief: Vorlage anleihe.html setzt ihn je ISIN (JS_CANONICAL)
        skripte = "".join(re.findall(r"<script\b(?![^>]*\bsrc=)(?![^>]*application/(?:ld\+)?json)[^>]*>(.*?)</script>", html, re.S))
        for src in re.findall(r'<script\b[^>]*\bsrc="(?:\./|/)?([\w.-]+\.js)(?:\?[^"]*)?"', html):
            if os.path.isfile(os.path.join(site, src)):
                skripte += open(os.path.join(site, src), encoding="utf-8").read()
        if CANONICAL_JS.search(skripte):
            fund("Seitenskript ändert link[rel=canonical], obwohl ein fester Canonical im HTML steht", f)

    # Breite im Suchergebnis
    if titel and pixel(titel, 20) > 580:
        fund("Titel breiter als 580 px im Suchergebnis", f, f"{pixel(titel, 20)} px")
    if beschreibung and pixel(beschreibung, 14) > 990:
        fund("Beschreibung breiter als 990 px im Suchergebnis", f, f"{pixel(beschreibung, 14)} px")

    # Zusage- und Empfehlungswörter, Hauswortschatz
    for ort, text in (("Titel", titel), ("Beschreibung", beschreibung), ("H1", h1), ("Text", haupt)):
        for wort, muster in ZUSAGE:
            for m in muster.finditer(text):
                umfeld = text[max(0, m.start() - 60): m.end() + 60]
                if VERNEINT.search(text[max(0, m.start() - 40): m.start()]):
                    continue
                if any(d in ("*", f) and a in umfeld for d, a in AUSNAHMEN_ZUSAGE):
                    continue
                fund("Zusage- oder Empfehlungswort", f, f"{ort} {wort}: {ausschnitt(text, m)}")
        if ort == "H1":
            continue   # die H1 steht auch im Haupttext
        for wort, muster in WORTSCHATZ:
            for m in muster.finditer(text):
                fund("Hauswortschatz", f, f"{wort}: {ausschnitt(text, m)}")
    m = ALTE_NAMEN.search(h1)
    if m:
        fund("Alter Menüname (Verstehen/Entscheiden/Vertiefen)", f, f"H1 {ausschnitt(h1, m)}")
    for stufe, roh in re.findall(r"<h([12])\b[^>]*>(.*?)</h\1>", re.sub(r"<script\b[^>]*>.*?</script>", "", html, flags=re.S), re.S):
        if "&" in klartext(roh):
            fund("„&“ in Überschrift (Hausregel: „und“)", f, f"H{stufe} „{klartext(roh)}“")

    # Strukturierte Daten
    knoten = []
    for roh in re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, re.S):
        try:
            k = json.loads(roh)
        except ValueError:
            continue   # unlesbares JSON-LD meldet schon die Prüfung oben als Fehler
        for n in (k.get("@graph") if isinstance(k, dict) and "@graph" in k else k if isinstance(k, list) else [k]):
            if isinstance(n, dict):
                knoten.append(n)
    kennungen, verweise = set(), []

    def sammeln(o, wurzel=False):
        if isinstance(o, dict):
            if "@id" in o:
                if len(o) == 1 and not wurzel:
                    verweise.append(o["@id"])
                else:
                    kennungen.add(o["@id"])
            for v in o.values():
                sammeln(v)
        elif isinstance(o, list):
            for v in o:
                sammeln(v)
    for n in knoten:
        sammeln(n, wurzel=True)
        art = n.get("@type")
        if art == "BreadcrumbList":
            e = [x for x in n.get("itemListElement") or [] if isinstance(x, dict)]
            namen = [str(x.get("name") or "") for x in e]
            letzte = e[-1].get("item") if e else None
            if isinstance(letzte, dict):
                letzte = letzte.get("@id")
            if letzte and letzte != eigen:
                fund("Letzte Brotkrume ≠ kanonische Adresse", f, str(letzte))
            if len(namen) > 1 and namen[1] not in MENUE:
                fund("Zweite Brotkrume ist kein Menüname", f, f"„{namen[1]}“")
            alt = [x for x in namen if ALTE_NAMEN.fullmatch(x.strip())]
            if alt:
                fund("Alter Menüname (Verstehen/Entscheiden/Vertiefen)", f, f"Brotkrume „{alt[0]}“")
        elif art not in ("Organization", "WebSite", "Dataset", "DefinedTermSet", "DefinedTerm", "WebApplication"):
            if n.get("dateModified") and f not in geaendert:
                geaendert[f] = datum(n["dateModified"])
            if art == "Article" and not n.get("datePublished"):
                ohne_datum.append(f)
            v, b = datum(n.get("datePublished")), datum(n.get("dateModified"))
            if v and b and v > b:
                fund("datePublished liegt nach dateModified", f, f"{v} > {b}")
    for ziel in sorted(set(verweise) - kennungen):
        # nur Kennungen dieser Seite und der Startseite (#organisation, #website) müssen im selben Block stehen;
        # Verweise auf andere Seiten (z. B. begriffe.html#kupon) sind gültige Adressen
        if ziel.split("#")[0] in (eigen, BASE, ""):
            fund("@id-Verweis ohne Knoten im JSON-LD", f, ziel)

    # Sichtbarer Daten-Stand gegen dateModified – maßgeblich ist das jüngste Datum der Zeile
    # („Daten-Stand: 26.09.2026 (ESMA-Register) · Kurse: 30.09.2026“ zählt mit dem 30.09.)
    b = geaendert.get(f)
    for m in re.finditer(r"Daten-Stand:?", sichtbar):
        daten = [datum(f"{j}-{mo}-{t}") for t, mo, j in re.findall(r"(\d{2})\.(\d{2})\.(\d{4})", sichtbar[m.end(): m.end() + 100])]
        d = max((x for x in daten if x), default=None)
        if b and d and (b - d).days > 7:
            fund("Sichtbarer Daten-Stand mehr als 7 Tage älter als dateModified", f, f"{d:%d.%m.%Y} gegen {b:%d.%m.%Y}")
            break
    # … und umgekehrt: Die Stand-Angabe der Seite (dieselben Stellen, die scripts/seo.py liest) darf nicht neuer sein
    # als dateModified – sonst fehlt die Seite in DATENSTAND von seo.py (so war es bei anleihen-suche.html).
    daten = [datum(f"{j}-{mo}-{t}") for _, z in STAND_STELLE.findall(html)
             for t, mo, j in re.findall(r"(\d{2})\.(\d{2})\.(\d{4})", klartext(z))]
    d = max((x for x in daten if x), default=None)
    if b and d and d > b:
        fund("Sichtbarer Daten-Stand neuer als dateModified (Seite in DATENSTAND von scripts/seo.py?)", f,
             f"{d:%d.%m.%Y} gegen {b:%d.%m.%Y}")


for f in sorted(seiten) + list(steckbriefe):
    try:   # die Zusatzprüfung darf den Deploy nie stoppen – ein unerwarteter Aufbau wird nur gemeldet
        seo_pruefung(f, lies_html(f), steckbriefe.get(f))
    except Exception as e:
        fund("SEO-Prüfung übersprungen (unerwarteter Aufbau)", steckbriefe.get(f, f), f"{type(e).__name__}: {e}")


# Sitemap: lastmod darf nicht jünger sein als das Änderungsdatum der Seite
sm = os.path.join(site, "sitemap.xml")
if os.path.isfile(sm):
    for loc, lastmod in re.findall(r"<loc>([^<]+)</loc>\s*<lastmod>([^<]+)</lastmod>", open(sm, encoding="utf-8").read()):
        datei = loc[len(BASE):] or "index.html"
        lm, b = datum(lastmod), geaendert.get(datei)
        if loc.startswith(BASE) and lm and b and lm > b:
            fund("Sitemap-lastmod jünger als dateModified der Seite", datei, f"{lm} > {b}")

if ohne_datum:
    hinweise.append(f"{len(ohne_datum)} Artikel ohne datePublished im JSON-LD (z. B. {', '.join(ohne_datum[:3])})")

for meldung, wo in sb_fehler.items():
    fehler.append(f"Server-Steckbriefe: {meldung} ({len(wo)}×, z. B. {', '.join(wo[:3])})")

for w in warnungen:
    print(f"::warning::{w}")
for regel, liste in funde.items():
    beispiele = "; ".join(f"{d}{' ' + a if a else ''}" for d, a in liste[:5])
    print(f"::warning::{regel}: {len(liste)}× – {beispiele}" + (f"; und {len(liste) - 5} weitere" if len(liste) > 5 else ""))
for h in hinweise:
    print(f"::notice::{h}")
for e in fehler:
    print(f"::error::{e}")
anzahl = len(warnungen) + sum(len(x) for x in funde.values())
print(f"{len(seiten)} Seiten und {len(steckbriefe)} Server-Steckbriefe geprüft – {len(fehler)} Fehler, {anzahl} Warnung{'' if anzahl == 1 else 'en'}"
      + (f" (davon {anzahl - len(warnungen)} in {len(funde)} Sammelzeile{'' if len(funde) == 1 else 'n'})" if funde else "")
      + (f", {len(hinweise)} Hinweis{'' if len(hinweise) == 1 else 'e'}" if hinweise else ""))
sys.exit(1 if fehler else 0)
