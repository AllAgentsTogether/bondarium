#!/usr/bin/env python3
"""llms.py – schreibt llms.txt und llms-full.txt beim Deploy aus den Seiten selbst (seit 30.09.2026).

Läuft im GitHub-Workflow auf dem Veröffentlichungsordner, NACH kennzahlen.py, statische_tabellen.py und seo.py
(braucht deren Sitemap und die fest geschriebenen Tabellen) und VOR inline_data.py und dem Minify:

    python3 scripts/llms.py _site

  llms.txt        Kurzfassung für KI-Dienste (Format: llmstxt.org): wer Bondarium ist, wie die Daten entstehen,
                  fünf aktuelle Zahlen mit Stand und je Seite eine Zeile – Titel, Adresse, Beschreibung. Titel und
                  Beschreibung kommen aus <title> und <meta name="description"> der Seite, die Gruppe aus ihren
                  Brotkrumen; „Über uns“ steht als eigener Abschnitt direkt nach „Start“.
  llms-full.txt   Volltext: die aktuellen Zahlen aus den Daten-JSONs und der Inhalt jeder Seite als Markdown
                  (Überschriften, Absätze, Listen, Tabellen, Links), in der Reihenfolge der Kurzfassung und je Seite
                  mit „Seite geändert:“ aus dem dateModified des JSON-LD (seo.py läuft vorher) – das Datum der Seite;
                  den Daten-Stand nennt jede Datenseite in ihrem Text.

Seit 02.10.2026 bereinigt der Volltext (nur hier, die Seiten bleiben unverändert): Dachzeilen und Bedienhinweise
(AUS_KLASSEN, BEDIENUNG), leere Tabellenspalten, die ISIN doppelt im Linktext, Ladetexte, Tabellen, deren Zeilen nicht
zum Kopf passen, und zusammengeklebte Kartenteile. Kacheln, Tabellen und Stand-Zeilen, deren sichtbarer Stand älter ist
als die Daten der Seite (Rückfallwerte im HTML), ersetzt ein Verweis – so steht kein Wert mit zwei Ständen in der Datei.

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
from decimal import ROUND_HALF_UP, Decimal
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
# Vor den Rubriken: „Start“ (Startseite) und „Über Bondarium“ (Herausgeber und Kontakt – geht beim Kürzen nicht verloren).
ABSCHNITTE = ["Akademie", "Anleihen", "Kaufen", "Zinsen"]
UEBER = {"ueber-uns.html"}
OPTIONAL = {"rechtliches.html"}
OHNE_VOLLTEXT = {"rechtliches.html"}   # Impressum und Datenschutz: nur verlinkt

LEER = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}
AUSLASSEN = {"script", "style", "svg", "nav", "button", "select", "form", "noscript", "template", "canvas", "input",
             "textarea", "label", "output", "iframe"}
BLOCK = {"p", "div", "section", "article", "ul", "ol", "li", "table", "h1", "h2", "h3", "h4", "h5", "h6", "dl", "dt", "dd",
         "blockquote", "figure", "figcaption", "details", "summary", "header", "footer", "main", "aside", "hr", "pre"}
# Dachzeilen, Nummern- und Schaubild-Köpfe, Bedienhinweise: auf der Seite Gestaltung bzw. Bedienung, im Text ohne Sinn
# (Klassen-Token; „kicker dach“ trifft über „dach“, „kicker“ allein steht in Karten und bleibt)
AUS_KLASSEN = {"dach", "za-dach", "hk-dach", "bc-k", "bc-kk", "za-nr", "eyebrow", "leg-hint", "hint-hover", "hint-touch",
               "maphint", "fl-tipp"}
# Teilsätze mit Bedienhinweis in sonst inhaltlichen Absätzen („Klick auf einen Spaltentitel sortiert.“)
BEDIENUNG = re.compile(r"\b(?:antippen|anklicken|Antippen|Anklicken|Tippen|Tippe|Überfahren|überfahren|Maus|Esc)\b"
                       r"|Klick auf einen Spaltentitel")
LADEN = re.compile(r"\b(?:wird|werden)\s+geladen\b|\blädt\s*(?:…|\.\.\.)", re.I)
ISIN = re.compile(r"[A-Z]{2}[A-Z0-9]{9}[0-9]")
KACHELN = {"heute", "live"}   # Klassen der Kachelgruppen mit Tageswerten (Zinsen-Seiten, Zinsniveau)
MONATE = ["Januar", "Februar", "März", "April", "Mai", "Juni", "Juli", "August", "September", "Oktober", "November", "Dezember"]
DATUM = r"\d{2}\.\d{2}\.\d{4}|\d{2}\.\d{2}\.(?!\d)|\d{2}[./]\d{4}|(?:" + "|".join(MONATE) + r") \d{4}"
# Sichtbarer Stand eines Werts: „Daten-Stand: 25.09.2026“, „Stand 25.09.2026“, „Stand: Renditen 25.09.2026“,
# „Tageswert 25.09.2026“, „Monatsdurchschnitt August 2026“, „Kurse und Renditen vom 25.09.2026“, „Stand 25.09.:“
STAND = re.compile(rf"(Daten-Stand|Kurse und Renditen vom|Stand|Tageswert|Monatsdurchschnitt)\b:?\s*(?:Renditen\s+|Kurse\s+vom\s+)?({DATUM})")
MELDUNGEN = []   # Bereinigungen, die auf einen Fehler in den Seiten hindeuten – eine Warnung je Seite


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


def klassen(k):
    return set((k.attrs.get("class") or "").split())


def versteckt(k):
    a = k.attrs
    return k.tag in AUSLASSEN or "hidden" in a or a.get("aria-hidden") == "true" or bool(AUS_KLASSEN & klassen(k))


def glatt(s):
    return re.sub(r"\s+", " ", s.replace("\u00ad", "").replace("\u00a0", " "))


def rohtext(k):
    """Sichtbarer Text eines Knotens ohne Markdown (für die Suche nach Ständen)."""
    if k.text is not None:
        return k.text
    if versteckt(k):
        return ""
    return " ".join(rohtext(c) for c in k.kinder)


def ohne_bedienung(text):
    """Teilsätze mit Bedienhinweis weglassen („Klick auf einen Spaltentitel sortiert.“, „Beim Überfahren …“)."""
    if not BEDIENUNG.search(text):
        return text
    return " ".join(t for t in re.split(r"(?<=[.;!?])\s+", text) if not BEDIENUNG.search(t)).strip()


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
        # (<b>Name</b><span>Typ</span>) – hier mit „ · “ bzw. Leerzeichen trennen; Hoch-/Tiefstellung bleibt verbunden.
        # Seit 02.10.2026 auch nach Satzzeichen, Anführung, „%“ und Währung („…bringen.“Nadine“, „3,47 %Rendite“).
        t, davor = "", None
        for c, x in zip(k.kinder, teile):
            if not x:
                continue
            if t and davor is not None and (c.tag or davor.tag) and "sub" not in (c.tag, davor.tag) and "sup" not in (c.tag, davor.tag) \
                    and re.search(r"[\w*)%€$£¥“”»!?.…]$", t) and re.match(r"[\w*\[„«]", x):
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
    """Tabelle als Markdown. Seit 02.10.2026: Ladezeilen („Die Daten werden geladen …“) und Spalten, die in allen
    Datenzeilen leer sind (z. B. „Steckbrief“), fallen weg; steht die ISIN in einer eigenen Spalte, entfällt sie im
    Linktext. Eine Tabelle ohne Datenzeilen oder mit Zeilen, die nicht zum Kopf passen (Rückfallzeilen im HTML nach
    altem Aufbau), wird durch einen Verweis auf die Seite ersetzt – lieber kein Wert als ein Wert in der falschen Spalte."""
    titel = finde(k, "caption")
    titel = zeile(titel, seite).strip() if titel else ""

    def knoepfe(n):   # Spaltentitel stehen oft in Sortier-Knöpfen
        for c in n.kinder:
            if c.tag == "button":
                c.tag = "span"
            if c.tag:
                knoepfe(c)
    def spannweite(c, art):
        n = str(c.attrs.get(art) or "1")
        return int(n) if n.isdigit() and int(n) > 1 else 1
    reihen, kopf_echt, offen = [], False, {}   # offen: Spalte → [Zeilen, Wert] einer Zelle mit rowspan
    for tr in alle(k, "tr"):
        zellen = [c for c in tr.kinder if c.tag in ("th", "td")]
        for c in zellen:
            if c.tag == "th":
                knoepfe(c)
        werte, rest = [], list(zellen)
        while rest or len(werte) in offen:   # verbundene Zellen zählen in jeder Spalte bzw. Zeile, die sie überdecken
            if len(werte) in offen:
                o = offen[len(werte)]
                werte.append(o[1])
                o[0] -= 1
                if not o[0]:
                    del offen[len(werte) - 1]
                continue
            c = rest.pop(0)
            text = zeile(c, seite).strip().replace("|", "/")
            for j in range(spannweite(c, "colspan")):
                if spannweite(c, "rowspan") > 1:
                    offen[len(werte)] = [spannweite(c, "rowspan") - 1, text if j == 0 else ""]
                werte.append(text if j == 0 else "")
        if not any(werte) or (LADEN.search(" ".join(werte)) and sum(1 for w in werte if w) <= 1):
            continue
        if not reihen:
            kopf_echt = bool(zellen) and all(c.tag == "th" for c in zellen)
        reihen.append(werte)
    verweis = f"*{titel or 'Tabelle'} – die Werte setzt die Seite beim Aufruf ein: {seite}*"
    if len(reihen) < 2:
        aus.append(verweis)
        return
    kopf, daten = reihen[0], reihen[1:]
    if kopf_echt:
        haeufig = max(set(len(r) for r in daten), key=lambda n: sum(1 for r in daten if len(r) == n))
        if haeufig != len(kopf):
            MELDUNGEN.append((seite, f"Tabelle mit {haeufig} statt {len(kopf)} Spalten"))
            aus.append(verweis)
            return
    breite = max(len(r) for r in reihen)
    reihen = [r + [""] * (breite - len(r)) for r in reihen]
    leer = [i for i in range(breite) if not any(r[i] for r in reihen[1:])]
    reihen = [[x for i, x in enumerate(r) if i not in leer] for r in reihen]
    isin_spalten = [i for i in range(len(reihen[0]))
                    if any(r[i] for r in reihen[1:]) and all(not r[i] or ISIN.fullmatch(r[i]) for r in reihen[1:])]
    for r in reihen[1:]:
        for i in isin_spalten:
            if r[i]:
                r[:] = [x if j == i else x.replace(f" ({r[i]})", "") for j, x in enumerate(r)]
    if titel:
        aus.append(f"**{titel}**")
    md = ["| " + " | ".join(reihen[0]) + " |", "|" + " --- |" * len(reihen[0])]
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


def absatz(text, aus):
    """Fließtext ohne Bedienhinweise; ein kurzer Ladetext („Daten-Stand: wird geladen“) entfällt ganz."""
    text = ohne_bedienung(text.strip())
    if text and not (len(text) <= 80 and LADEN.search(text)):
        aus.append(text)


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
        absatz(zeile(k, seite), aus)
        return
    lauf = []   # Fließtext zwischen Blöcken zusammenhalten

    def spuelen():
        if lauf:
            h = Knoten("span")
            h.kinder = list(lauf)
            absatz(zeile(h, seite), aus)
            del lauf[:]
    for c in k.kinder:
        if c.tag in BLOCK or c.tag == "table" or (c.tag and any(g.tag in BLOCK or g.tag == "table" for g in c.kinder) and c.tag != "a"):
            spuelen()
            block(c, seite, aus)
        else:
            lauf.append(c)
    spuelen()


# ---------- Rückfallwerte mit altem Stand (seit 02.10.2026) ----------
# Die Datenseiten tragen im HTML Rückfallwerte, die erst das Seitenskript im Browser durch die Tageswerte ersetzt. Ist so
# ein Wert älter als die Daten des Laufs, stünde er im Volltext neben dem aktuellen – mit anderem Stand. Solche Kacheln,
# Tabellen und Stand-Zeilen ersetzt ein Verweis. Schreibt der Deploy die Rückfallwerte aktuell, greift das nicht.
def schluessel(anz, jahr=None):
    """Sichtbares Datum → (Jahr, Monat, Tag) zum Vergleich; Monatsangaben zählen als Monatsende, „TT.MM.“ im Jahr jahr."""
    m = re.fullmatch(r"(\d{2})\.(\d{2})\.(\d{4})?", anz)
    if m and (m.group(3) or jahr):
        return int(m.group(3) or jahr), int(m.group(2)), int(m.group(1))
    m = re.fullmatch(r"(\d{2})[./](\d{4})", anz)
    if m:
        return int(m.group(2)), int(m.group(1)), 31
    m = re.fullmatch(r"(\S+) (\d{4})", anz)
    if m and m.group(1) in MONATE:
        return int(m.group(2)), MONATE.index(m.group(1)) + 1, 31
    return None


def anzeigen(iso):
    """Schreibweisen eines Stands aus den Daten („JJJJ-MM-TT“ bzw. „JJJJ-MM“), wie die Seiten ihn zeigen."""
    m = re.match(r"(\d{4})-(\d{2})(?:-(\d{2}))?", str(iso or ""))
    if not m:
        return set()
    j, mo, t = m.groups()
    if t:
        return {f"{t}.{mo}.{j}", f"{t}.{mo}."}
    return {f"{mo}.{j}", f"{mo}/{j}", f"{MONATE[int(mo) - 1]} {j}"}


def rueckfall(haupt, aktuell, verweis):
    """Ersetzt Kacheln, Tabellen und kurze Stand-Zeilen, deren sichtbarer Stand älter ist als die Daten der Seite
    (aktuell: Schreibweisen der gültigen Stände), durch den Verweis. Gibt die alten Stände zurück."""
    neu = max((x for x in map(schluessel, aktuell) if x), default=None)
    if not neu:
        return []
    funde, alt = [], set()

    def wann(d):   # „TT.MM.“ ohne Jahr: im Jahr des jüngsten Stands, liegt es danach, im Vorjahr
        s = schluessel(d, neu[0])
        return (s[0] - 1,) + s[1:] if s and len(d) == 6 and s > neu else s

    def alte(text, bar=False):
        treffer = [(m.group(1), m.group(2)) for m in STAND.finditer(text)]
        if bar:   # Tabelle mit Spalte „Stand“: dort stehen die Daten ohne Stichwort
            treffer += [("Stand", m.group(0)) for m in re.finditer(DATUM, text)]
        return [(w, d) for w, d in treffer if d not in aktuell and wann(d) and wann(d) < neu]

    def kopftext(k):   # Spaltentitel stehen oft in Sortier-Knöpfen, die rohtext auslässt
        if k.text is not None:
            return k.text
        return "" if k.tag in ("script", "style", "svg") else " ".join(kopftext(c) for c in k.kinder)

    def ueberschrift(k):
        return k.tag in ("h1", "h2", "h3", "h4", "h5", "h6") or any(ueberschrift(c) for c in k.kinder if c.tag)

    def einheit(pfad, k):   # k selbst, wenn es Werte trägt („3,63 %“); sonst der größte Behälter ohne Überschrift und
        if re.search(r"\d\s?%", glatt(rohtext(k))):   # mit wenig Text (Bildkasten mit Werten neben der Stand-Zeile)
            return k
        for a in reversed(pfad):
            if a.tag in ("wurzel", "body", "main", "section", "article", "details") or ueberschrift(a) or len(glatt(rohtext(a))) > 400:
                break
            k = a
        return k

    def gruppen(k):   # Tabellen und Kachelgruppen unter k
        if k.text is not None or versteckt(k):
            return []
        if k.tag == "table" or KACHELN & klassen(k):
            return [k]
        return [g for c in k.kinder for g in gruppen(c)]

    def gang(k, pfad):
        if k.text is not None or versteckt(k):
            return
        if k.tag == "table" or KACHELN & klassen(k):
            kopf = [glatt(kopftext(c)).strip() for tr in alle(k, "tr")[:1] for c in tr.kinder if c.tag == "th"]
            gefunden = alte(glatt(rohtext(k)), bar="Stand" in kopf)
        elif k.tag in BLOCK and not any(c.tag in BLOCK or c.tag == "table" for c in k.kinder):
            text = glatt(rohtext(k))
            gefunden = alte(text) if len(text) <= 200 else []   # lange Absätze: Methodik, kein Rückfallwert
        else:
            for c in k.kinder:
                gang(c, pfad + [k])
            return
        if gefunden:
            funde.append(einheit(pfad, k))
            alt.update(d for _, d in gefunden)
            if any(w == "Kurse und Renditen vom" for w, _ in gefunden):   # gilt für die Tabellen des ganzen Abschnitts
                bereich = next((a for a in reversed(pfad) if a.tag in ("section", "main")), None)
                funde.extend(gruppen(bereich) if bereich else [])
    gang(haupt, [])

    def enthaelt(a, b):
        return any(c is b or (c.tag and enthaelt(c, b)) for c in a.kinder)
    einheiten = []
    for u in funde:
        if not any(u is e for e in einheiten):
            einheiten.append(u)
    einheiten = [u for u in einheiten if not any(e is not u and enthaelt(e, u) for e in einheiten)]
    for i, u in enumerate(einheiten):
        if i == 0:
            u.tag, u.attrs, u.kinder = "p", {}, [Knoten(text=verweis)]
        else:
            u.attrs["hidden"] = ""
    return sorted(alt, key=wann)


def markdown(html_, seite, aktuell=None, verweis=""):
    b = Baum()
    b.feed(html_)
    haupt = finde(b.wurzel, "main") or finde(b.wurzel, "body") or b.wurzel
    if aktuell:
        try:
            alt = rueckfall(haupt, aktuell, verweis)
        except Exception as e:   # die Prüfung ist Zugabe – der Volltext der Seite bleibt
            warn(f"{seite}: Rückfallwerte nicht geprüft ({type(e).__name__}: {e})")
            alt = []
        if alt:
            MELDUNGEN.append((seite, f"Stand {', '.join(alt)}"))
    aus = []
    block(haupt, seite, aus)
    return "\n\n".join(x for x in aus if x.strip())


# ---------- Angaben je Seite ----------
def kopf(html_, muster):
    m = re.search(muster, html_, re.S)
    return re.sub(r"\s+", " ", htmllib.unescape(m.group(1)).replace("\u00ad", "")).strip() if m else ""


def ld_knoten(html_):
    """Alle Knoten der JSON-LD-Blöcke einer Seite."""
    aus = []
    for roh in re.findall(r'<script type="application/ld\+json">(.*?)</script>', html_, re.S):
        try:
            k = json.loads(roh)
        except ValueError:
            continue
        aus += [n for n in (k.get("@graph") if isinstance(k, dict) and "@graph" in k else [k]) if isinstance(n, dict)]
    return aus


def krume(html_):
    """(Name der zweiten Brotkrume = Rubrik, ist die Seite selbst deren Übersicht?) aus dem JSON-LD der Seite."""
    for knoten in ld_knoten(html_):
        if knoten.get("@type") == "BreadcrumbList":
            e = knoten.get("itemListElement") or []
            return (e[1].get("name"), len(e) == 2) if len(e) > 1 else (None, False)
    return None, False


def geaendert(html_):
    """dateModified der Seite selbst (Artikel bzw. Webseite – nicht Datensatz, Organisation oder Website)."""
    for knoten in ld_knoten(html_):
        if knoten.get("dateModified") and knoten.get("@type") not in (
                "Dataset", "Organization", "WebSite", "DefinedTermSet", "WebApplication", "BreadcrumbList"):
            return str(knoten["dateModified"])[:10]
    return None


def seiten(site):
    pfad = os.path.join(site, "sitemap.xml")
    adressen = re.findall(r"<loc>([^<]+)</loc>(?:\s*<lastmod>([^<]+)</lastmod>)?",
                          open(pfad, encoding="utf-8").read()) if os.path.isfile(pfad) else []
    aus = []
    for u, lastmod in adressen:
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
                    "text": kopf(h, r'<meta name="description" content="([^"]*)"'), "stand": geaendert(h) or lastmod or None})
    return aus


def gliederung(S):
    """[(Abschnitt, Seiten)]: Start, Über Bondarium, die Rubriken in Menü-Reihenfolge (Übersicht zuerst, dann wie in
    der Sitemap), weitere Rubriken alphabetisch, Optional. Gilt für llms.txt und llms-full.txt."""
    start = [s for s in S if s["datei"] == "index.html"]
    ueber = [s for s in S if s["datei"] in UEBER]
    optional = [s for s in S if s["datei"] in OPTIONAL]
    gruppen = {}
    for s in S:
        if s["datei"] != "index.html" and s["datei"] not in UEBER and s["datei"] not in OPTIONAL:
            gruppen.setdefault(s["rubrik"] or "Weitere Seiten", []).append(s)
    namen = [a for a in ABSCHNITTE if a in gruppen] + sorted(g for g in gruppen if g not in ABSCHNITTE)
    aus = [("Start", start), ("Über Bondarium", ueber)]
    aus += [(g, sorted(gruppen[g], key=lambda s: not s["uebersicht"])) for g in namen]
    aus.append(("Optional", optional))
    return [(n, liste) for n, liste in aus if liste]


# ---------- Zahlen ----------
def zahl(v, nk=2):
    """Wie MC.zahl auf den Seiten (Intl.NumberFormat de-DE): exakter Wert kaufmännisch gerundet, Tausenderpunkt, echtes Minus."""
    d = Decimal(v).quantize(Decimal(1).scaleb(-nk), rounding=ROUND_HALF_UP)
    return ("−" if d < 0 else "") + f"{abs(d):,.{nk}f}".replace(",", " ").replace(".", ",").replace(" ", ".")


def vz(v, nk=2):
    """Mit Vorzeichen wie vz() in den Seitenskripten: „+0,39“, „−0,12“, „±0,00“."""
    return ("+" if v > 0 else "−" if v < 0 else "±") + zahl(abs(v), nk)


def tag(iso):
    """„2026-09-30“ → „30.09.2026“, „2026-08“ → „August 2026“."""
    m = re.match(r"(\d{4})-(\d{2})(?:-(\d{2}))?", str(iso or ""))
    return "–" if not m else f"{m.group(3)}.{m.group(2)}.{m.group(1)}" if m.group(3) else f"{MONATE[int(m.group(2)) - 1]} {m.group(1)}"


def lade(site, name):
    with open(os.path.join(site, name), encoding="utf-8") as f:
        return json.load(f)


LAND = {"us": "USA", "cn": "China", "de": "Deutschland", "in": "Indien", "jp": "Japan", "gb": "Großbritannien",
        "fr": "Frankreich", "it": "Italien"}
# Seiten, deren Tageswerte im Abschnitt „Aktuelle Zahlen“ stehen – der Verweis für alte Rückfallwerte zeigt dorthin
ZAHLEN_SEITEN = {"renditen.html", "zinskurve.html", "realzins.html", "risikoaufschlaege.html", "zinsniveau.html",
                 "fortgeschrittene.html"}
TOP10 = {"staatsanleihen-laufzeit.html": "top10-staatsanleihen-laufzeit.json",
         "unternehmensanleihen-laufzeit.html": "top10-unternehmensanleihen-laufzeit.json",
         "anleihen-laender.html": "top10-staatsanleihen-laender.json",
         "unternehmensanleihen-laender.html": "top10-unternehmensanleihen-laender.json"}


def zahlen(site):
    """Die wichtigsten Tageswerte aus den Daten-JSONs, gerechnet und gerundet wie auf den Seiten (MC.zahl, vz).
    Gibt (Zeilen für llms.txt, Blöcke für llms-full.txt) zurück; jeder Wert für sich – fehlt eine Datei, fehlt nur er."""
    erg = {}

    def versuch(name, f):
        try:
            erg[name] = f()
        except Exception as e:
            warn(f"Aktuelle Zahlen – {name}: ausgelassen ({type(e).__name__}: {e})")

    def renditen():
        c = lade(site, "renditen.json")["countries"]
        bund = c["de"]["latest"]
        k = f"- [Rendite der 10-jährigen Bundesanleihe]({BASE}renditen.html): {zahl(bund['yield'])} % (Stand {tag(bund['date'])})"
        z = ["### Renditen 10-jähriger Staatsanleihen", "", "| Land | Rendite | Stand |", "| --- | --- | --- |"]
        z += [f"| {LAND.get(x, x)} | {zahl(v['latest']['yield'])} % | {tag(v['latest']['date'])} |" for x, v in c.items()]
        return k, "\n".join(z) + f"\n\nJede Rendite gilt in der Währung des Landes. Seite mit Verlauf seit 1970: {BASE}renditen.html"

    def zinskurve():
        h = lade(site, "zinskurve.json")["heute"]
        d, zwei, zehn = h["DE"]
        k = f"- [Zinskurve Deutschland]({BASE}zinskurve.html): Abstand 10 minus 2 Jahre {vz(zehn - zwei)} Prozentpunkte (Stand {tag(d)})"
        z = ["### Zinskurve: 10 Jahre minus 2 Jahre", "", "| Land | Abstand | Rendite 2 Jahre | Stand |", "| --- | --- | --- | --- |"]
        for x, name in (("DE", "Deutschland"), ("US", "USA")):
            d, zwei, zehn = h[x]
            z.append(f"| {name} | {vz(zehn - zwei)} Prozentpunkte | {zahl(zwei)} % | {tag(d)} |")
        return k, ("\n".join(z) + "\n\nRenditen aus der Zinsstrukturkurve (Deutschland: Deutsche Bundesbank, USA: Federal Reserve). "
                   f"Seite mit Verlauf seit 1972: {BASE}zinskurve.html")

    def realzins():
        h = lade(site, "realzins.json")["heute"]
        (dz, zins), (dv, vpi) = h["zins10"], h["vpi"]
        # beide Werte nennen, damit die Zeile nachrechenbar ist (die Bund-Rendite oben stammt aus renditen.json und
        # kann einen anderen Tag haben)
        teile = (f"{zahl(zins)} % Rendite der 10-jährigen Bundesanleihe (Tageswert {tag(dz)}) minus "
                 f"{zahl(vpi, 1)} % Inflationsrate ({tag(dv)})")
        k = f"- [Realzins Deutschland]({BASE}realzins.html): {vz(zins - vpi, 1)} Prozentpunkte – {teile}"
        return k, (f"### Realzins Deutschland\n\n- Realzins: {vz(zins - vpi, 1)} Prozentpunkte – {teile}\n"
                   f"- Inflationsrate: Verbraucherpreise Deutschland gegenüber dem Vorjahresmonat\n\n"
                   f"Seite mit Verlauf seit 1970: {BASE}realzins.html")

    def ezb():
        d = lade(site, "ezb.json")
        text = f"{zahl(d['aktuell'][1])} % seit {tag(d['aktuell'][0])} (abgerufen am {tag(d['stand'])})"
        return (f"- [Einlagesatz der Europäischen Zentralbank]({BASE}zinsniveau.html#ezb): {text}",
                f"### Leitzins\n\n- Einlagesatz der Europäischen Zentralbank: {text}\n\nErklärt auf der Seite: {BASE}zinsniveau.html#ezb")

    def risiko():
        d = lade(site, "risikoaufschlaege.json")
        heute = d["laender"]["heute"]
        nach = {x["code"]: x for x in heute}
        it, fr = nach["IT"], nach["FR"]
        if it["monat"] == fr["monat"]:
            werte = f"Italien {vz(it['aufschlag'])}, Frankreich {vz(fr['aufschlag'])} Prozentpunkte (Monatsdurchschnitt {tag(it['monat'])})"
        else:
            werte = (f"Italien {vz(it['aufschlag'])} Prozentpunkte ({tag(it['monat'])}), "
                     f"Frankreich {vz(fr['aufschlag'])} Prozentpunkte ({tag(fr['monat'])})")
        k = f"- [Risikoaufschlag gegenüber Deutschland]({BASE}risikoaufschlaege.html): {werte}"
        z = ["### Risikoaufschläge", "", "Rendite 10-jähriger Staatsanleihen minus Rendite der Bundesanleihe, Monatsdurchschnitt.", "",
             "| Land | Aufschlag gegenüber Deutschland | Stand |", "| --- | --- | --- |"]
        z += [f"| {x['name']} | {vz(x['aufschlag'])} Prozentpunkte | {tag(x['monat'])} |" for x in heute]
        uh = (d.get("us") or {}).get("heute")
        if uh:
            z += ["", f"USA: Unternehmensanleihen (Bonität AAA bis A, 10 Jahre) gegenüber der US-Staatsanleihe {vz(uh[1])} Prozentpunkte ({tag(uh[0])})."]
        return k, "\n".join(z) + f"\n\nSeite mit Verlauf seit 1984: {BASE}risikoaufschlaege.html"

    for name, f in (("Renditen", renditen), ("Zinskurve", zinskurve), ("Realzins", realzins), ("EZB", ezb),
                    ("Risikoaufschläge", risiko)):
        versuch(name, f)
    # llms.txt: Bund, Zinskurve, Realzins, EZB, Risikoaufschlag; llms-full.txt: Leitzins zuletzt (wie bisher)
    return ([erg[n][0] for n in ("Renditen", "Zinskurve", "Realzins", "EZB", "Risikoaufschläge") if n in erg],
            [erg[n][1] for n in ("Renditen", "Zinskurve", "Realzins", "Risikoaufschläge", "EZB") if n in erg])


def staende(site):
    """Je Datenseite die Schreibweisen der gültigen Stände aus ihren Daten-JSONs (für rueckfall). Fehlt eine Datei,
    wird die Seite nicht geprüft."""
    aus = {}

    def setze(datei, *isos):
        aus.setdefault(datei, set()).update(*[anzeigen(i) for i in isos if i])

    def versuch(name, f):
        try:
            f()
        except Exception as e:
            warn(f"Stand aus {name} nicht lesbar – Rückfallwerte dort ungeprüft ({type(e).__name__}: {e})")

    def renditen():
        setze("renditen.html", *(v["latest"]["date"] for v in lade(site, "renditen.json")["countries"].values()))

    def zinskurve():
        h = lade(site, "zinskurve.json")["heute"]
        setze("zinskurve.html", *(v[0] for v in h.values()))
        setze("zinsniveau.html", h["DE"][0])
        setze("fortgeschrittene.html", h["DE"][0])   # Kasten „Bund, Stand …“ im Schritt Zinskurve

    def realzins():
        h = lade(site, "realzins.json")["heute"]
        setze("realzins.html", h["zins10"][0], h["vpi"][0], *(x.get("datum") for x in h.get("linker") or []))
        setze("zinsniveau.html", h["vpi"][0])

    def risiko():
        d = lade(site, "risikoaufschlaege.json")
        setze("risikoaufschlaege.html", *(x["monat"] for x in d["laender"]["heute"]), d["laender"]["monate"][-1][0],
              d["us"]["heute"][0], d["us"]["monate"][-1][0])

    def unternehmen():
        setze("unternehmensanleihen.html", *((v.get("latest") or {}).get("date") for v in lade(site, "unternehmen.json")["series"].values()))

    def kurse():
        stand = lade(site, "kurse-auswahl.json")["stand"]
        setze("index.html", stand)
        setze("langlaeufer.html", stand, *(b["latest"]["date"] for b in lade(site, "langlaeufer.json")["bonds"].values()))
        for datei, json_ in TOP10.items():
            setze(datei, stand, lade(site, json_).get("stand"))

    for name, f in (("renditen.json", renditen), ("zinskurve.json", zinskurve), ("realzins.json", realzins),
                    ("risikoaufschlaege.json", risiko), ("unternehmen.json", unternehmen), ("Kursdaten", kurse)):
        versuch(name, f)
    return aus


# ---------- llms.txt ----------
def kurzfassung(site, S, kurz):
    m = re.search(r"Suche über (rund \d{1,3}\.\d{3}) Anleihen", next((s["text"] for s in S if s["datei"] == "index.html"), ""))
    teile = [KOPF.format(anleihen=m.group(1) if m else "rund 33.000"), HINWEISE.format(base=BASE)]
    if kurz:
        teile.append("## Aktuelle Zahlen\n\nAutomatisch aus den Daten der Seiten, mit dem Stand je Wert.\n\n" + "\n".join(kurz))

    def eintrag(s):
        return f"- [{s['titel']}]({s['url']}): {s['text']}"
    abschnitte = gliederung(S)
    for name, liste in abschnitte:
        teile.append(f"## {name}\n\n" + "\n".join(eintrag(s) for s in liste))
    with open(os.path.join(site, "llms.txt"), "w", encoding="utf-8") as f:
        f.write("\n\n".join(t.rstrip() for t in teile) + "\n")
    print(f"llms.txt: {len(S)} Seiten in {len(abschnitte)} Abschnitten, {len(kurz)} aktuelle Zahlen")


# ---------- llms-full.txt ----------
def volltext(site, S, voll):
    start = next((s for s in S if s["datei"] == "index.html"), None)
    m = re.search(r"Suche über (rund \d{1,3}\.\d{3}) Anleihen", start["text"] if start else "")
    teile = [KOPF.format(anleihen=m.group(1) if m else "rund 33.000").replace("# Bondarium", "# Bondarium – Volltext aller Seiten", 1),
             HINWEISE.format(base=BASE).replace(f"- Volltext aller Seiten mit den aktuellen Zahlen: {BASE}llms-full.txt\n",
                                                f"- Kurzfassung mit allen Adressen: {BASE}llms.txt\n")]
    if voll:
        teile.append("## Aktuelle Zahlen\n\nAutomatisch aus den Daten der Seiten, mit dem Stand je Wert. Werte in den Seitentexten "
                     "weiter unten, deren sichtbarer Stand älter ist, sind durch einen Verweis auf diesen Abschnitt bzw. auf die "
                     "Seite ersetzt.\n\n" + "\n\n".join(voll))
    gueltig = staende(site)
    n = 0
    for _, liste in gliederung(S):
        for s in liste:
            if s["datei"] in OHNE_VOLLTEXT:
                continue
            verweis = ("*Aktuelle Werte: siehe „Aktuelle Zahlen“ am Anfang dieser Datei und die Seite selbst.*"
                       if s["datei"] in ZAHLEN_SEITEN and voll else f"*Aktuelle Werte zeigt die Seite selbst: {s['url']}*")
            try:
                md = markdown(s["html"], s["url"], gueltig.get(s["datei"]), verweis)
            except Exception as e:
                warn(f"{s['datei']}: Volltext ausgelassen ({type(e).__name__}: {e})")
                continue
            # Datum der Seite (dateModified), nicht der Daten – den Daten-Stand nennt die Seite selbst im Text
            stand = f"\nSeite geändert: {tag(s['stand'])}" if s["stand"] else ""
            teile.append(f"---\n\n## {s['h1'] or s['titel']}\n\nAdresse: {s['url']}{stand}\n\n{s['text']}\n\n{md}")
            n += 1
    pfad = os.path.join(site, "llms-full.txt")
    with open(pfad, "w", encoding="utf-8") as f:
        f.write("\n\n".join(t.rstrip() for t in teile) + "\n")
    print(f"llms-full.txt: {n} Seiten, {os.path.getsize(pfad) // 1024} KB")
    if MELDUNGEN:   # eine Sammelzeile: Rückfallwerte oder Tabellen im HTML, die nicht zu den Daten passen
        je = {}
        for seite, text in MELDUNGEN:
            je.setdefault(seite[len(BASE):] or "index.html", []).append(text)
        teile = [f"{d} ({', '.join((f'{t.count(x)}× ' if t.count(x) > 1 else '') + x for x in dict.fromkeys(t))})"
                 for d, t in je.items()]
        warn("Volltext: alte Rückfallwerte bzw. Tabellen, deren Zeilen nicht zum Kopf passen, durch Verweis ersetzt – "
             + "; ".join(teile[:5]) + (f"; und {len(teile) - 5} weitere Seiten" if len(teile) > 5 else ""))


def main():
    site = sys.argv[1] if len(sys.argv) > 1 else "_site"
    if not os.path.isdir(site):
        raise SystemExit(f"Ordner nicht gefunden: {site}")
    S = seiten(site)
    if not S:
        raise SystemExit("llms.py: keine Seiten in sitemap.xml gefunden – llms.txt nicht geschrieben")
    kurz, voll = zahlen(site)
    kurzfassung(site, S, kurz)
    try:
        volltext(site, S, voll)
    except Exception as e:   # der Volltext ist Zugabe – ein Fehler dort stoppt den Deploy nicht
        warn(f"llms-full.txt nicht geschrieben ({type(e).__name__}: {e})")


if __name__ == "__main__":
    main()
