#!/usr/bin/env python3
"""hubs.py – die Übersichtsseiten (wissen, anleihen, kaufen, beobachten) aus den Menüdaten in nav.py (seit 11.10.2026 abends,
Gesamtprüfung Punkt 12). Vorher standen Titel und Kurztexte der Kacheln von Hand in den Seiten und waren eine Kopie des Menüs.

Aufruf im Stammordner:   python3 scripts/hubs.py            # schreibt die Kacheln und die Weg-Zeile
                         python3 scripts/hubs.py --check    # meldet nur Abweichungen

Was das Skript schreibt:
  * die Weg-Zeile <nav class="weg"> unter dem Antwortsatz: die vier Bereiche in der Reihenfolge des Weges (Akademie → Anleihen →
    Kaufen → Markt), der aktuelle markiert – so sieht man, wo man steht (Stil .weg in base.css);
  * die regulären Kacheln <a class="hub-card"> in jedem <div class="hub…">: Reihenfolge, Titel, Bild und Kurztext aus nav.py,
    Etiketten je Bereich (ETIKETT). Die Abschluss-Kachel „next“ bleibt in der Seite stehen; auf kaufen.html führt sie zum Markt.
    Auf wissen.html laden die Kachelbilder ab dem zweiten Bereich (Risiken) erst beim Scrollen (loading="lazy", seit 15.10.2026);
  * (seit 15.10.2026, Gesamtprüfung B13-05) im JSON-LD der Übersicht (CollectionPage) die Liste der Kacheln als mainEntity
    (ItemList: Position, Seitenname, Adresse) – dieselben Einträge in derselben Reihenfolge wie die Kacheln.
Eigene Stile, Einleitungen, Suchfeld (anleihen.html) und Bereichs-Sprungleiste (wissen.html) bleiben unberührt."""
import json, re, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from nav import AKADEMIE, ANLEIHEN, KAUFEN, MARKT, esc   # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
WEG = [("wissen.html", "Akademie"), ("anleihen.html", "Anleihen"), ("kaufen.html", "Kaufen"), ("beobachten.html", "Markt")]
SHY = [("Unternehmensanleihen", "Unternehmens&shy;anleihen"), ("Staatsanleihen", "Staats&shy;anleihen"), ("Risikoaufschläge", "Risiko&shy;aufschläge")]
CARD_RE = re.compile(r'    <a class="hub-card(?! next)[^"]*" href="[^"]+">.*?</a>\n', re.S)
HUB_RE = re.compile(r'(<div class="hub[^"]*">\n)(.*?)(  </div>\n)', re.S)
WEG_RE = re.compile(r'  <nav class="weg".*?</nav>\n', re.S)
LD_RE = re.compile(r'(<script type="application/ld\+json">)(.*?)(</script>)', re.S)
BASE = "https://www.bondarium.de/"


def titel(t):
    t = esc(t)
    for a, b in SHY:
        t = t.replace(a, b)
    return t


def karte(it, h, etikett="", klasse="", ebene="h2", lazy=False):
    laden = ' loading="lazy" decoding="async"' if lazy else ""
    z = [f'    <a class="hub-card{(" " + klasse) if klasse else ""}" href="{it["h"]}">',
         f'      <img class="hub-img" src="{it["img"]}" alt="" width="160" height="110"{laden}>']
    if etikett:
        z.append(f'      {etikett}')
    z += [f'      <{ebene}>{titel(it["t"])}</{ebene}>', f'      <p class="desc">{esc(it["kd"])}</p>', '    </a>']
    return "\n".join(z) + "\n"


def flach(items):
    """E-Einträge in Menüreihenfolge, Gruppen (B) aufgelöst; liefert (Eintrag, Gruppe oder None)."""
    for it in items:
        if not isinstance(it, dict):
            continue
        if "sub" in it:
            for u in it["sub"]:
                yield u, it
        else:
            yield it, None


def karten_anleihen():
    out = []
    for it, grp in flach(ANLEIHEN[2]):
        if it["h"] == "anleihen-suche.html":
            et = '<span class="hub-tag neutral">Alle Anleihen</span>'
        elif grp or it["h"] == "anleihen-etf.html":
            et = '<span class="hub-tag">Top 10 meistgehandelt</span>'
        else:
            et = '<span class="hub-tag">Weitere Listen</span>'
        out.append(karte(it, it["h"], et))
    return "".join(out)


def karten_kaufen():
    out = []
    for i, (it, _) in enumerate(flach(KAUFEN[2])):
        if i < 2:
            out.append(karte(it, it["h"], f'<span class="hub-nr">Schritt {i + 1}</span>', "breit"))
        else:
            out.append(karte(it, it["h"], '<span class="hub-nr">Vertiefung</span>'))
    return "".join(out)


def karten_markt():
    out = []
    for it, _ in flach(MARKT[2]):
        et = "Renditen" if it["h"] in ("renditen.html", "unternehmensanleihen.html") else "Renditeabstände"
        out.append(karte(it, it["h"], f'<span class="hub-tag">{et}</span>'))
    return "".join(out)


BEREICHE = ("grundlagen", "risiken", "auswaehlen", "fortgeschrittene")   # Abschnitte von wissen.html in dieser Reihenfolge


def bereich_wissen(anker):
    for it in AKADEMIE[2]:
        if isinstance(it, dict) and it.get("h") == f"wissen.html#{anker}":
            return it["sub"]
    raise SystemExit(f"wissen.html: Bereich #{anker} nicht in nav.py")


def karten_wissen(anker):
    # der erste Bereich steht oben auf der Seite; die Bilder der übrigen lädt der Browser erst beim Scrollen (B13-03)
    return "".join(karte(u, u["h"], ebene="h3", lazy=anker != BEREICHE[0]) for u in bereich_wissen(anker))


def eintraege(seite):
    """Die Seiten der Kacheln einer Übersicht in ihrer Reihenfolge (für die ItemList im JSON-LD)."""
    if seite == "wissen.html":
        return [u for anker in BEREICHE for u in bereich_wissen(anker)]
    menue = {"anleihen.html": ANLEIHEN, "kaufen.html": KAUFEN, "beobachten.html": MARKT}[seite]
    return [it for it, _ in flach(menue[2])]


def setze_liste(s, seite):
    """mainEntity (ItemList) im JSON-LD-Block der CollectionPage; die übrigen Angaben des Blocks bleiben, wie sie sind."""
    for m in LD_RE.finditer(s):
        d = json.loads(m.group(2))
        if d.get("@type") != "CollectionPage":
            continue
        d["mainEntity"] = {"@type": "ItemList", "numberOfItems": len(eintraege(seite)), "itemListElement": [
            {"@type": "ListItem", "position": i + 1, "name": u["t"], "url": BASE + u["h"]} for i, u in enumerate(eintraege(seite))]}
        roh = json.dumps(d, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
        return s[:m.start(2)] + roh + s[m.end(2):]
    raise SystemExit(f"{seite}: kein JSON-LD-Block mit CollectionPage")


def weg(seite):
    teile = []
    for i, (h, name) in enumerate(WEG):
        if i:
            teile.append('<span class="weg-pf" aria-hidden="true">→</span>')
        cur = ' class="current" aria-current="page"' if h == seite else ""
        teile.append(f'<a href="{h}"{cur}><span class="n">{i + 1}</span>{name}</a>')
    return '  <nav class="weg" aria-label="Dein Weg: Akademie, Anleihen, Kaufen, Markt">' + "".join(teile) + '</nav>\n'


def ersetze_hub(s, neue_karten, anker=None):
    """Tauscht in einem <div class="hub…"> die regulären Kacheln; anker: nur der Hub im Abschnitt mit dieser id (wissen.html)."""
    start = 0
    if anker:
        start = s.index(f'<section class="ak-teil" id="{anker}"')
    m = HUB_RE.search(s, start)
    if not m:
        raise SystemExit("kein <div class=\"hub\">")
    innen = m.group(2)
    rest = CARD_RE.sub("", innen)          # nur „next“ und Leerraum bleiben
    neu = m.group(1) + neue_karten + rest.lstrip("\n") + m.group(3)
    return s[:m.start()] + neu + s[m.end():]


def setze_weg(s, seite):
    s = WEG_RE.sub("", s)
    m = re.search(r'  <p class="sub">.*?</p>\n', s, re.S)
    if not m:
        raise SystemExit(f"{seite}: kein Antwortsatz")
    return s[:m.end()] + weg(seite) + s[m.end():]


KAUFEN_NEXT = ('    <a class="hub-card next" href="beobachten.html">\n'
               '      <img class="hub-img" src="spot-renditen.svg?v=2" alt="" width="160" height="110">\n'
               '      <h2>Weiter: den Markt im Blick behalten</h2>\n'
               '      <p class="desc">Renditen, Realzins, Zinskurve und Risikoaufschläge – fünf Schaubilder, täglich aktuell</p>\n'
               '    </a>\n')


def baue(seite):
    s = (ROOT / seite).read_text(encoding="utf-8")
    if seite == "wissen.html":
        for anker in BEREICHE:
            s = ersetze_hub(s, karten_wissen(anker), anker)
    elif seite == "anleihen.html":
        s = ersetze_hub(s, karten_anleihen())
    elif seite == "kaufen.html":
        s = ersetze_hub(s, karten_kaufen())
        s = re.sub(r'    <a class="hub-card next" href="[^"]+">.*?</a>\n', lambda m: KAUFEN_NEXT, s, count=1, flags=re.S)
    elif seite == "beobachten.html":
        s = ersetze_hub(s, karten_markt())
    return setze_liste(setze_weg(s, seite), seite)


def main():
    check = "--check" in sys.argv
    geaendert = []
    for seite, _ in WEG:
        alt = (ROOT / seite).read_text(encoding="utf-8")
        neu = baue(seite)
        if neu != alt:
            geaendert.append(seite)
            if not check:
                (ROOT / seite).write_text(neu, encoding="utf-8")
    print(f"{len(geaendert)} Seiten {'abweichend' if check else 'geschrieben'}, {4 - len(geaendert)} unverändert" + (": " + ", ".join(geaendert) if geaendert else ""))


if __name__ == "__main__":
    main()
