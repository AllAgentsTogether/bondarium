"""Themen für die Anleihen-Suche: themen.json aus den fertigen Seiten (seit 03.10.2026).

Die Kopfsuche jeder Seite schickt den Suchbegriff an anleihen-suche.html. Wer dort „Duration“ oder „Stückzinsen“ eingibt,
bekam bisher nur „Keine Anleihe gefunden“. Mit dieser Datei zeigt die Suche über der Trefferliste passende Lernseiten und
Glossarbegriffe („Passende Themen“).

Quellen (alles aus dem Ordner, der veröffentlicht wird – im Workflow _site, lokal der Repo-Ordner):
- Seiten: alle Adressen aus sitemap.xml und konto.html, ohne Startseite, Suche und Steckbrief-Vorlage.
  Name = Text des Menü- oder Fußzeilen-Links (scripts/nav.py), sonst die H1. Stichwörter = Titel, H1 und H2.
  Beschreibung = Meta-Beschreibung.
- Glossar: jeder Eintrag in begriffe.html (<div class="e" id="…"><dt>Begriff</dt><dd><p>Erklärung …).

Format (kompakt): {"stand": "JJJJ-MM-TT", "seiten": [[Name, Datei, Beschreibung, Stichwörter], …],
"begriffe": [[Begriff, Sprungmarke, erster Satz der Erklärung], …]}

Aufruf:  python3 scripts/themen.py _site     (lokale Vorschau: python3 scripts/themen.py . – die Datei ist git-ignoriert)
Läuft mit Python 3.9 (lokal) und 3.12 (Workflow), nur Standardbibliothek.
"""
import datetime
import html
import json
import pathlib
import re
import sys

AUSLASSEN = {"index.html", "anleihen-suche.html", "anleihe.html", "404.html"}
ZUSATZ = ["konto.html"]   # nicht in der Sitemap (noindex), aber ein Ziel für „Merkliste“, „Musterdepot“, „Konto“


def text(s):
    """Tags entfernen, Entitäten auflösen, Leerraum zusammenfassen."""
    s = re.sub(r"<[^>]+>", " ", s)
    return re.sub(r"\s+", " ", html.unescape(s)).strip()


def kuerzen(s, n=170):
    if len(s) <= n:
        return s
    s = s[:n].rsplit(" ", 1)[0].rstrip(",;:–-")
    return s + " …"


def erster_satz(s):
    m = re.match(r"(.+?[.!?])(\s|$)", s)
    return kuerzen(m.group(1) if m else s)


def menue_namen(ordner):
    """Datei → Name aus Kopfmenü und Fußzeile der Startseite (einheitlich auf allen Seiten, Quelle scripts/nav.py)."""
    s = (ordner / "index.html").read_text(encoding="utf-8")
    namen = {}
    bereiche = re.findall(r'<nav class="sitenav".*?</nav>', s, re.S) + re.findall(r"<footer.*?</footer>", s, re.S)
    for b in bereiche:
        # nur Links ohne Sprungmarke: „Haftung und Datenquellen“ (rechtliches.html#haftung) ist kein Name für die ganze Seite;
        # Zusätze wie <small>Fachbegriffe von A bis Z</small> gehören nicht zum Namen
        for href, inhalt in re.findall(r'<a href="([^"#?]+\.html)"[^>]*>(.*?)</a>', b, re.S):
            name = text(re.sub(r"<small>.*?</small>", "", inhalt, flags=re.S))
            if name and href not in namen:
                namen[href] = name
    return namen


def seiten_liste(ordner):
    dateien = []
    sm = ordner / "sitemap.xml"
    if sm.exists():
        for loc in re.findall(r"<loc>([^<]+)</loc>", sm.read_text(encoding="utf-8")):
            datei = loc.rstrip("/").rsplit("/", 1)[-1]
            if datei.endswith(".html"):
                dateien.append(datei)
    for d in ZUSATZ:
        if d not in dateien:
            dateien.append(d)
    return [d for d in dateien if d not in AUSLASSEN and (ordner / d).exists()]


def seite(ordner, datei, namen):
    s = (ordner / datei).read_text(encoding="utf-8")
    titel = re.search(r"<title>(.*?)</title>", s, re.S)
    titel = text(titel.group(1)).replace(" – Bondarium", "") if titel else ""
    h1 = re.search(r"<h1[^>]*>(.*?)</h1>", s, re.S)
    h1 = text(h1.group(1)) if h1 else ""
    h2 = [text(x) for x in re.findall(r"<h2[^>]*>(.*?)</h2>", s, re.S)]
    h2 = [x for x in h2 if len(x) > 2 and x not in ("Weiter", "Datenquellen und Methodik")]   # ohne Buchstaben-Köpfe des Glossars
    beschr = re.search(r'<meta name="description" content="([^"]*)"', s)
    beschr = html.unescape(beschr.group(1)) if beschr else ""
    name = namen.get(datei) or h1 or titel.split(":")[0]
    stich = []
    for x in [titel, h1] + h2:
        if x and x != name and x not in stich:
            stich.append(x)
    return [name, datei, kuerzen(beschr), " · ".join(stich)]


def begriffe(ordner):
    s = (ordner / "begriffe.html").read_text(encoding="utf-8")
    out = []
    for sid, dt, dd in re.findall(r'<div class="e" id="([^"]+)">\s*<dt>(.*?)</dt>\s*<dd>(.*?)</dd>', s, re.S):
        p = re.search(r"<p>(.*?)</p>", dd, re.S)
        out.append([text(dt), sid, erster_satz(text(p.group(1))) if p else ""])
    return out


def main():
    ordner = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    namen = menue_namen(ordner)
    seiten = [seite(ordner, d, namen) for d in seiten_liste(ordner)]
    glossar = begriffe(ordner)
    if len(seiten) < 20 or len(glossar) < 30:
        sys.exit(f"themen.py: zu wenig gefunden ({len(seiten)} Seiten, {len(glossar)} Begriffe) – Datei nicht geschrieben")
    daten = {"stand": datetime.date.today().isoformat(), "seiten": seiten, "begriffe": glossar}
    ziel = ordner / "themen.json"
    ziel.write_text(json.dumps(daten, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"themen.json: {len(seiten)} Seiten, {len(glossar)} Begriffe, {ziel.stat().st_size:,} Byte".replace(",", "."))


if __name__ == "__main__":
    main()
