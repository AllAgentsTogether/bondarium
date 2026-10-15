"""Themen für die Anleihen-Suche: themen.json aus den fertigen Seiten (seit 03.10.2026).

Die Kopfsuche jeder Seite schickt den Suchbegriff an anleihen-suche.html. Wer dort „Duration“ oder „Stückzinsen“ eingibt,
bekam bisher nur „Keine Anleihe gefunden“. Mit dieser Datei zeigt die Suche über der Trefferliste passende Lernseiten und
Glossarbegriffe („Passende Themen“).

Quellen (alles aus dem Ordner, der veröffentlicht wird – im Workflow _site, lokal der Repo-Ordner):
- Seiten: alle Adressen aus sitemap.xml und konto.html, ohne Startseite, Suche und Steckbrief-Vorlage.
  Name = Seitenname aus den Menüdaten (scripts/nav.py, menue_namen()), sonst die H1. Stichwörter = Titel, H1 und H2.
  Beschreibung = Meta-Beschreibung.
- Glossar: jeder Eintrag in begriffe.html (<div class="e" id="…" [data-k="…"]><dt>Begriff</dt><dd><p>Erklärung …).

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


def menue_namen(ordner=None):
    """Datei → Name aus den Menüdaten in scripts/nav.py (seit 15.10.2026, Gesamtprüfung E03-01).
    Bis dahin las das Skript die Links aus dem Kopfmenü der fertigen Startseite. Seit dem Menü-Umbau vom 11.10.2026 stehen
    dort Vorschauzeilen (<small class="np-kd">…</small>, <small class="nav-kurz">…</small>) im Link; die Regex entfernte
    nur <small>, und die Suche zeigte Themen wie „Markt Renditen Staat · Renditen Unternehmen · Realzins …“. Die Menüdaten
    selbst sind die eine Quelle (wie für newsletter.py, kennzahlen.py, hubs.py und weiter.py).
    Reihenfolge: Seitenname der Menüeinträge (E(…)["t"], z. B. „Staatsanleihen nach Ländern“ – der kurze Menüname „nach
    Ländern“ ist ohne das Menü mehrdeutig), dann „My Bondarium“, die kleinen Links (Über uns, Rechtliches), die Schnell-Knöpfe
    und die Fußzeile (nur Links ohne Sprungmarke: „Grundlagen“ ist kein Name für die ganze wissen.html), zuletzt die Namen der
    Menüs für ihre Übersichtsseiten (Akademie, Kaufen, Markt). Sind die Menüdaten nicht lesbar: Warnung, Namen aus der H1."""
    try:
        sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
        import nav
    except Exception as e:   # noqa: BLE001
        print(f"::warning::themen.py: Menüdaten (scripts/nav.py) nicht lesbar ({e}) – Themen-Namen aus der H1")
        return {}
    namen = {}

    def dazu(datei, name):
        if "#" not in datei and datei.endswith(".html") and name and datei not in namen:
            namen[datei] = name

    for _menue, _ziel, eintraege in nav.ALLE:
        for e in eintraege:
            if isinstance(e, dict):
                for u in e.get("sub") or [e]:
                    dazu(u["h"], u["t"])
    dazu(nav.KONTO[1], nav.KONTO[0])
    for name, datei in list(nav.KLEIN) + list(nav.SCHNELL):
        dazu(datei, name)
    for _kopf, _id, links in nav.FOOTER:
        for name, datei in links:
            dazu(datei, name)
    for menue, ziel, _eintraege in nav.ALLE:
        dazu(ziel, menue)
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
    """Glossar-Einträge [Begriff, Sprungmarke, erster Satz]. Seit 15.10.2026 (Gesamtprüfung B33-02) auch Einträge mit weiteren
    Attributen (data-k="…" für Suchwörter): Vorher fehlten „Kündbare Anleihe“, „Quellensteuer“ und „Vorabpauschale“ (68 statt 71).
    Weicht die Zahl von den Einträgen der Seite ab, gibt es eine Warnung."""
    s = (ordner / "begriffe.html").read_text(encoding="utf-8")
    out = []
    for sid, dt, dd in re.findall(r'<div class="e" id="([^"]+)"[^>]*>\s*<dt>(.*?)</dt>\s*<dd>(.*?)</dd>', s, re.S):
        p = re.search(r"<p>(.*?)</p>", dd, re.S)
        out.append([text(dt), sid, erster_satz(text(p.group(1))) if p else ""])
    auf_der_seite = len(re.findall(r'<div class="e"[\s>]', s))
    if len(out) != auf_der_seite:
        print(f"::warning::themen.py: {len(out)} von {auf_der_seite} Glossar-Einträgen gelesen – Aufbau eines Eintrags in begriffe.html geändert?")
    return out


def main():
    ordner = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    namen = menue_namen()
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
