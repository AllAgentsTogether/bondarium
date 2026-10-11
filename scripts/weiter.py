#!/usr/bin/env python3
"""weiter.py – die eine Quelle für den Lernpfad am Ende jeder Inhaltsseite (seit 11.10.2026 abends, Gesamtprüfung Punkt 7 und 8).

Aufruf im Stammordner:   python3 scripts/weiter.py            # schreibt die Blöcke
                         python3 scripts/weiter.py --check    # meldet nur Abweichungen

Jede Inhaltsseite endet mit zwei Teilen:
  1. <div class="weiter"> – zwei bis drei Knöpfe. Der erste („Weiter: …“, Klasse go) ist die nächste Seite im Lernpfad, also in
     der Reihenfolge des Menüs (scripts/nav.py); am Ende eines Bereichs geht es in den nächsten (Akademie → Kaufen bzw. Listen → Kaufen,
     Markt → Suche). Die weiteren (Klasse go leise) sind Quereinstiege, die zum Thema passen.
  2. <nav class="crossnav"> – „Verwandte Seiten“ (bis 11.10.2026 „Weiter“): die handgepflegte Liste bleibt in der Seite.
Beschriftung: der Titel der Seite aus nav.py (E(…)["t"]), außer eine Zeile hier nennt eine eigene.
Übersichten, Startseite, My Bondarium, Über uns und Rechtliches haben keinen Block (sie enden mit Kacheln bzw. Kontakt)."""
import re, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from nav import AKADEMIE, ANLEIHEN, KAUFEN, MARKT   # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
TITEL = {}
for _label, _ziel, items in (AKADEMIE, ANLEIHEN, KAUFEN, MARKT):
    for it in items:
        if not isinstance(it, dict):
            continue
        for u in it.get("sub", [it]):
            TITEL[u["h"]] = u["t"]
TITEL.update({"anleihen-suche.html": "Anleihen-Suche", "beobachten.html": "Markt im Überblick", "wissen.html": "Akademie"})

# Seite → Knöpfe: Ziel oder (Ziel, eigene Beschriftung). Der erste Knopf ist der Lernpfad.
WEITER = {
    # Akademie – Grundlagen
    "grundlagen.html": ["anleihe-arten.html", ("anlageziele.html#fuer-wen", "Für wen Anleihen passen"), "anleihe-festgeld-tagesgeld.html"],
    "anleihe-arten.html": ["zinsniveau.html", "anlageziele.html", ("anleihen-suche.html", "Anleihen durchsuchen")],
    "zinsniveau.html": ["laufzeit.html", "anleihen-simulator.html", "zinskurve.html"],
    "laufzeit.html": ["rendite-lesen.html", "anleihen-simulator.html", ("staatsanleihen-laufzeit.html", "Top 10 nach Laufzeit")],
    "anleihen-simulator.html": ["beobachten.html", "duration.html", ("anleihen-suche.html", "Eine echte Anleihe suchen")],   # seit 11.10.2026 abends letzter Eintrag unter Kaufen
    "rendite-lesen.html": ["risiko.html", ("rechner.html", "Rendite selbst rechnen"), "kuendbare-anleihen.html"],
    # Akademie – Risiken
    "risiko.html": ["bonitaet.html", "zahlungsausfall.html", "langlaeufer.html"],
    "bonitaet.html": ["zahlungsausfall.html", "risikoaufschlaege.html", ("anleihen-laender.html", "Staatsanleihen nach Ländern")],
    "zahlungsausfall.html": ["kuendbare-anleihen.html", "eisenbahn-blase-1873.html", "cds.html"],
    "kuendbare-anleihen.html": ["eisenbahn-blase-1873.html", ("anleihen-suche.html?w=EUR&amp;kue=n,m,p", "Euro-Anleihen ohne nachteilige Kündigung"), ("risiko.html#kuendigung", "Risiko kennen: Kündigung")],
    "eisenbahn-blase-1873.html": ["anleihen-anteil.html", "zahlungsausfall.html", "markttechnik.html"],
    # Akademie – Auswählen
    "anleihen-anteil.html": ["anlageziele.html", "anleihen-etf.html", "anleihenleiter.html"],
    "anlageziele.html": ["anleihe-festgeld-tagesgeld.html", ("anleihen-suche.html", "Passende Anleihe suchen"), "erste-anleihe.html"],
    "anleihe-festgeld-tagesgeld.html": ["etf-oder-anleihe.html", ("anlageziele.html#kurzfristig", "Geld kurzfristig parken"), "bundeswertpapiere.html"],
    "etf-oder-anleihe.html": ["erste-anleihe.html", "anleihen-etf.html", "anleihen-fuer-unternehmen.html"],
    "anleihen-fuer-unternehmen.html": ["erste-anleihe.html", "broker-vergleich.html", "steuern-handelskosten.html"],
    # Akademie – Fortgeschrittene
    "duration.html": ["anleihenleiter.html", "anleihen-simulator.html", "langlaeufer.html"],
    "anleihenleiter.html": ["markttechnik.html", "zinskurve.html", ("staatsanleihen-laufzeit.html", "Top 10 nach Laufzeit")],
    "markttechnik.html": ["cds.html", "zinskurve.html", "beobachten.html"],
    "cds.html": ["risikoaufschlaege.html", "bonitaet.html", "zahlungsausfall.html"],
    "begriffe.html": ["grundlagen.html", "anlageziele.html"],
    # Kaufen
    "erste-anleihe.html": ["nach-dem-kauf.html", ("anleihen-suche.html?art=0,1&amp;land=DE&amp;w=EUR&amp;zins=0&amp;rest=b&amp;vol=b", "Passende Anleihen finden"), "broker-vergleich.html"],
    "broker-vergleich.html": ["handelsplaetze.html", ("erste-anleihe.html#order", "Die Order richtig eingeben"), "anleihen-suche.html"],
    "handelsplaetze.html": ["anleihe-nicht-kaufbar.html", "broker-vergleich.html", "anleihen-suche.html"],
    "anleihe-nicht-kaufbar.html": ["nach-dem-kauf.html", "broker-vergleich.html", "etf-oder-anleihe.html"],
    "nach-dem-kauf.html": ["steuern-handelskosten.html", "rechner.html", ("konto.html", "Termine in My Bondarium")],
    "steuern-handelskosten.html": [("rechner.html#netto", "Rechner: Zinsen netto nach Steuer"), "broker-vergleich.html", "nach-dem-kauf.html"],
    "rechner.html": ["anleihen-simulator.html", "anleihen-suche.html", "erste-anleihe.html"],
    # Anleihen (Listen und Steckbrief) → Kaufen
    "staatsanleihen-laufzeit.html": [("erste-anleihe.html", "So kaufst du sie"), "anleihen-laender.html", "anleihen-suche.html"],
    "anleihen-laender.html": [("erste-anleihe.html", "So kaufst du sie"), "staatsanleihen-laufzeit.html", "anleihen-suche.html"],
    "unternehmensanleihen-laufzeit.html": [("erste-anleihe.html", "So kaufst du sie"), "unternehmensanleihen-laender.html", "anleihen-suche.html"],
    "unternehmensanleihen-laender.html": [("erste-anleihe.html", "So kaufst du sie"), "unternehmensanleihen-laufzeit.html", "anleihen-suche.html"],
    "anleihen-etf.html": [("erste-anleihe.html", "So kaufst du sie"), "etf-oder-anleihe.html", "broker-vergleich.html"],
    "anleihen-kupon.html": [("erste-anleihe.html", "So kaufst du sie"), "kuendbare-anleihen.html", "bonitaet.html"],
    "bundeswertpapiere.html": [("erste-anleihe.html", "So kaufst du sie"), "broker-vergleich.html", "realzins.html"],
    "langlaeufer.html": ["duration.html", ("risiko.html#kurs", "Risiko kennen: wenn der Kurs fällt"), ("anleihen-suche.html?rest=e", "Suche: über 30 Jahre Restlaufzeit")],
    "anleihen-suche.html": ["erste-anleihe.html", "broker-vergleich.html", "anlageziele.html"],
    "anleihe.html": [("broker-vergleich.html", "Wo du sie kaufst"), "handelsplaetze.html", "anleihe-nicht-kaufbar.html"],
    # Markt → Suche
    "renditen.html": ["unternehmensanleihen.html", ("anleihen-laender.html", "Staatsanleihen je Land"), "anleihen-suche.html"],
    "unternehmensanleihen.html": ["realzins.html", ("unternehmensanleihen-laufzeit.html", "Unternehmensanleihen nach Laufzeit"), "anleihen-suche.html"],
    "realzins.html": ["zinskurve.html", "anleihen-suche.html", "rendite-lesen.html"],
    "zinskurve.html": ["risikoaufschlaege.html", ("staatsanleihen-laufzeit.html", "Top 10 nach Laufzeit"), "anleihenleiter.html"],
    "risikoaufschlaege.html": [("anleihen-suche.html", "Passende Anleihe suchen"), "bonitaet.html", "cds.html"],
}

BLOCK_RE = re.compile(r'    <div class="weiter">.*?</div>\n', re.S)


def label(ziel):
    if isinstance(ziel, tuple):
        return ziel[0], ziel[1]
    return ziel, TITEL[ziel.split("#")[0].split("?")[0]]


def block(seite):
    zeilen = []
    for i, z in enumerate(WEITER[seite]):
        href, text = label(z)
        if i == 0:
            zeilen.append(f'      <a class="go" href="{href}">Weiter: {text}&nbsp;→</a>')
        else:
            zeilen.append(f'      <a class="go leise" href="{href}">{text}&nbsp;→</a>')
    return '    <div class="weiter">\n' + "\n".join(zeilen) + '\n    </div>\n'


def setze(seite, s):
    neu = block(seite)
    if BLOCK_RE.search(s):
        s = BLOCK_RE.sub(lambda m: neu, s, count=1)
    else:
        for marke in ('    <nav class="crossnav', '    <details class="quellen', '  </main>'):
            i = s.find(marke)
            if i >= 0:
                s = s[:i] + neu + "\n" + s[i:] if marke != '  </main>' else s[:i] + neu + s[i:]
                break
        else:
            raise SystemExit(f"{seite}: kein Platz für den Block")
    s = s.replace('<nav class="crossnav" aria-label="Weiter">', '<nav class="crossnav" aria-label="Verwandte Seiten">')
    s = s.replace('<nav class="crossnav crossnav-gruppen" aria-label="Weiter">', '<nav class="crossnav crossnav-gruppen" aria-label="Verwandte Seiten">')
    s = s.replace('<p class="crossnav-t">Weiter</p>', '<p class="crossnav-t">Verwandte Seiten</p>')
    return s


def main():
    check = "--check" in sys.argv
    geaendert, gleich = [], []
    for seite in WEITER:
        p = ROOT / seite
        alt = p.read_text(encoding="utf-8")
        neu = setze(seite, alt)
        if neu != alt:
            geaendert.append(seite)
            if not check:
                p.write_text(neu, encoding="utf-8")
        else:
            gleich.append(seite)
    print(f"{len(geaendert)} Seiten {'abweichend' if check else 'geschrieben'}, {len(gleich)} unverändert")
    if geaendert:
        print("  " + ", ".join(geaendert))


if __name__ == "__main__":
    main()
