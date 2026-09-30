#!/usr/bin/env python3
"""nav.py – die eine Quelle für Kopfzeile und Menü aller Seiten.

Aufruf im Ordner website/:

    python3 scripts/nav.py            # schreibt die Kopfzeile in alle *.html
    python3 scripts/nav.py --check    # meldet nur Abweichungen, schreibt nichts

Ersetzt in jeder Seite den Block von `<header class="topbar">` bis `</header>`
(ältere Seiten: `<div class="topbar">` … `</nav>\n  </div>`). 404.html bekommt
absolute Pfade (`/…`), weil sie unter beliebigen URLs ausgeliefert wird.
Die aktive Seite erhält `class="current"` am Gruppenkopf und am Eintrag;
site.js setzt daraus `aria-current`.

Menü „Der Weg“ (Konzept A, seit 25.09.2026): vier Stufen als Aufklapper –
Verstehen, Entscheiden, Kaufen (seit 29.09.2026 drei; Einordnen ist jetzt das Menü „Zinsen“) – dazu rechts der Link „Über uns“
(LINKS). Der frühere Knopf „Anleihen-Suche“ (BUTTONS) ist seit 25.09.2026 abends
ein Eintrag im Menü Kaufen; BUTTONS bleibt als Mechanismus erhalten. Der Gruppenkopf
ist ein Link auf die Übersichtsseite der Stufe (wissen.html, entscheiden.html,
kaufen.html, beobachten.html – seit 25.09.2026 spät hat jede Stufe eine). Einträge in GROUPS:
  ("Beschriftung", "datei.html")  Menüeintrag
  ("Beschriftung", "datei.html", "klasse")  Menüeintrag mit CSS-Klasse (nav-hl = dezenter Rahmen, für die Suche im Menü Kaufen)
  "Beschriftung"                  Gruppenüberschrift im Aufklapper (kleine graue Zeile)
  None                            Trennlinie
Hat eine Stufe ihre Übersichtsseite nicht selbst als Eintrag (der Normalfall),
schreibt das Skript zusätzlich den Eintrag „Übersicht“ mit der Klasse nav-ov – base.css zeigt ihn nur im Handy-Akkordeon, wo der Kopf nicht
navigiert, sondern auf- und zuklappt.

Menü ändern: nur GROUPS, AKADEMIE_EXTRA, ANLEIHEN, ZINSEN, BUTTONS, LINKS anpassen und das Skript laufen lassen.

Seit 30.09.2026 schreibt das Skript außerdem (alles idempotent, --check meldet Abweichungen):
  * die Brotkrumen-Zeile <nav class="krumen"> direkt unter der Kopfzeile – erzeugt aus dem JSON-LD
    BreadcrumbList der Seite (nicht auf index.html und 404.html; ohne BreadcrumbList keine Zeile),
  * die gemeinsame Fußzeile <footer class="fuss"> (FOOTER; vier Spalten wie früher nur auf der Startseite),
  * den Rückfall-Block für window.MC (FALLBACK) in einheitlicher Minimalform, falls site.js nicht lädt.
Der Menüpunkt „Akademie“ zeigt auf ./#akademie (404.html: /#akademie) – nicht auf index.html#akademie: Diese Form
fasst der Deploy-sed (href="index.html" → "/") nicht, und .htaccess leitete sie per 301 von index.html auf / um.
"""
import html
import json
import glob
import os
import re
import sys

# (Beschriftung, Ziel des Gruppenkopfs, Einträge) – siehe Kopf der Datei
GROUPS = [
    ("Verstehen", "wissen.html", [
        # Seit 26.09.2026 nach Kenntnisstand geteilt (Nutzerwunsch „in Anfänger und Fortgeschrittene aufteilen“):
        # Anfänger = die Grundbegriffe, die man vor dem ersten Kauf kennen sollte; Fortgeschrittene = Themen,
        # die diese Grundlagen voraussetzen (ETF ohne festes Ende, Zinskurve/Duration/Spreads …).
        "Anfänger",
        ("Anleihen einfach erklärt", "grundlagen.html"),
        ("Anleihe-Arten", "anleihe-arten.html"),
        ("Zinsniveau", "zinsniveau.html"),   # seit 26.09.2026: erklärt, was das Zinsniveau bewegt – vor „Laufzeit“, die zeigt, was es mit der Anleihe macht
        ("Laufzeit", "laufzeit.html"),
        ("Bonität und Ratings", "bonitaet.html"),
        ("Risiko kennen", "risiko.html"),
        "Fortgeschrittene",
        ("Anleihen-ETF: Vor- und Nachteile", "anleihen-etf-erklaert.html"),
        ("Zinskurve, Duration & Co.", "fortgeschrittene.html"),
        ("Kündbare Anleihen", "kuendbare-anleihen.html"),   # seit 27.09.2026: sechs Kündigungsarten und ihre Folgen
        ("Handelsplätze", "handelsplaetze.html"),   # seit 28.09.2026: Profimarkt, Börse, elf Plätze in einer Tabelle
        # Seit 27.09.2026 (Nutzerwunsch „Profi-Wissen“): rechnen, Strategien, Steuern, Markttechnik
        "Profi",
        ("Duration und Konvexität", "duration.html"),
        ("Rendite richtig lesen", "rendite-lesen.html"),
        ("Leiter, Hantel, Roll-down", "anleihenleiter.html"),
        ("Steuern und Handelskosten", "steuern-handelskosten.html"),
        ("Markttechnik lesen", "markttechnik.html"),
        "Nachschlagen",
        ("Glossar", "begriffe.html"),
    ]),
    ("Entscheiden", "entscheiden.html", [
        # Seit 27.09.2026 mit Gruppenköpfen wie Verstehen und Kaufen (Nutzerwunsch): Orientieren = passt das zu mir,
        # Werkzeuge = Anleitungen und Rechner
        "Orientieren",
        ("Sind Anleihen etwas für dich?", "anlegerprofile.html"),
        ("Welche Anleihe wozu?", "anlageziele.html"),
        ("ETF oder Anleihe?", "etf-oder-anleihe.html"),
        "Werkzeuge",
        ("Rechner", "rechner.html"),   # „Vier Anleitungen nach Ziel“ (guide.html) seit 29.09.2026 im Menü „Anleihen“
    ]),
    ("Kaufen", "kaufen.html", [
        # Seit 29.09.2026 nur noch „So kaufst du“ – Anleihen-Suche und Top 10 stehen im Menü „Anleihen“ (ANLEIHEN)
        "So kaufst du",
        ("Deine erste Anleihe", "erste-anleihe.html"),
        ("Broker im Vergleich", "broker-vergleich.html"),
    ]),
]
# Seit 28.09.2026 (Nutzerwunsch): In der Kopfzeile steht nur noch ein Aufklapper „Akademie“; er öffnet die vier Stufen
# (Verstehen, Entscheiden, Kaufen, Einordnen) als Einträge mit Unterzeile – Ziel ist jeweils die Übersichtsseite der Stufe,
# die oben dieselben vier Kacheln als Navigation trägt. GROUPS bleibt die Quelle für Rubrik und „current“.
AKADEMIE = ("Akademie", "./#akademie", "/#akademie")   # (Beschriftung, Ziel relativ, Ziel absolut für 404.html)
# Seit 30.09.2026 (Audit „Orientierung fehlt“): unter den drei Stufen die Vertiefungsseiten und der Rechner direkt im
# Aufklapper – vorher nur über die Übersichten erreichbar. Einträge wie in ANLEIHEN (Chip = Zeichenkette).
AKADEMIE_EXTRA = [
    "Vertiefen",
    ("Duration und Konvexität", "duration.html"),
    ("Rendite richtig lesen", "rendite-lesen.html"),
    ("Leiter, Hantel, Roll-down", "anleihenleiter.html"),
    ("Markttechnik lesen", "markttechnik.html"),
    "Werkzeuge",
    ("Anleihen-Rechner", "rechner.html"),
]
# Seit 29.09.2026 (Nutzerwunsch „den Teil aus der Akademie heraustrennen“): zweiter Aufklapper „Anleihen“ mit allem, was
# konkrete Anleihen zeigt – Suche, Top-10-Listen, ETFs und die Beispiele der Redaktion (guide.html). Kopf = Übersichtsseite
# anleihen.html (Kacheln in Menüreihenfolge); Einträge wie früher die Stufen-Menüs: Chips (nav-cap), nav-hl, nav-ov.
ANLEIHEN = ("Anleihen", "anleihen.html", [
    ("Anleihen-Suche", "anleihen-suche.html", "nav-hl"),
    "Top 10 meistgehandelt",   # Nutzerwunsch 29.09.2026: „Top 10“ muss direkt draufstehen
    ("Staatsanleihen nach Laufzeit", "staatsanleihen-laufzeit.html"),
    ("Unternehmensanleihen nach Laufzeit", "unternehmensanleihen-laufzeit.html"),
    ("Staatsanleihen nach Ländern", "anleihen-laender.html"),
    ("Unternehmensanleihen nach Ländern", "unternehmensanleihen-laender.html"),
    ("Anleihen-ETFs", "anleihen-etf.html"),
    ("Anleihen-ETF: Vor- und Nachteile", "anleihen-etf-erklaert.html"),   # seit 30.09.2026 auch hier (Seite zählt zur Stufe Verstehen)
    "Beispiele",
    ("Anleihen-Beispiele nach Ziel", "guide.html"),
])
# Seit 29.09.2026 (Nutzerwunsch): dritter Aufklapper „Zinsen“ – die frühere Stufe 4 „Einordnen“ (Marktdaten, täglich aktuell)
# steht nicht mehr in der Akademie. Kopf = Übersicht beobachten.html (Dateiname bleibt, damit alle Links gelten).
ZINSEN = ("Zinsen", "beobachten.html", [
    "Zins",
    ("Staatsanleihen seit 1970", "renditen.html"),
    ("Zinskurve seit 1972", "zinskurve.html"),
    ("Realzins seit 1970", "realzins.html"),
    "Risiko",
    ("Unternehmensanleihen seit 1970", "unternehmensanleihen.html"),
    ("Risikoaufschläge seit 1953", "risikoaufschlaege.html"),
    ("Langläufer", "langlaeufer.html"),
])
# Die Aufklapper neben der Akademie, in dieser Reihenfolge; Rubrik-Schlüssel je Menü; Zusatzseiten, die zu einem Menü zählen
MENUS = [ANLEIHEN, ZINSEN]
MENU_RUBRIK = {"Anleihen": "anleihen", "Zinsen": "zinsen"}
MENU_EXTRA = {"Anleihen": ["anleihe.html"]}
STUFE_ZEILE = {"Verstehen": "Vom Einstieg bis zum Profi", "Entscheiden": "Welche Anleihe passt zu dir?",
               "Kaufen": "Broker wählen, Order aufgeben"}   # wie die Kacheln (28.09.2026 an den Inhalt angepasst)
# Knopf rechts (immer sichtbar, am Handy ganz oben im Akkordeon) – seit 25.09.2026 abends leer:
# Nutzerwunsch „Die Anleihen-Suche soll ganz oben raus“ → Eintrag im Menü Kaufen (Gruppe „Finden“)
BUTTONS = []
# Direktlinks ohne Aufklapper (ganz rechts)
LINKS = [("Über uns", "ueber-uns.html")]
# Suchfeld rechts außen (seit 26.09.2026, Nutzerwunsch „Feld ganz oben rechts … direkt in die Anleihensuche“):
# schickt q an die Anleihen-Suche; leer abgeschickt führt site.js direkt auf die Suchseite (Fokus ins Suchfeld).
# Im DOM nach dem Menü (Tab-Reihenfolge Marke → Menü → Suche); der Lupen-Knopf steht per CSS links im Feld.
SEARCH = ('    <form class="kopfsuche" action="{p}anleihen-suche.html" method="get" role="search" aria-label="Anleihen-Suche">'
          '<input type="search" name="q" placeholder="Anleihe suchen" aria-label="Anleihe suchen – Name, ISIN oder WKN" '
          'autocomplete="off" spellcheck="false" enterkeyhint="search">'
          '<button type="submit" aria-label="Suchen"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false"><circle cx="10.5" cy="10.5" r="6.5"/><path d="M15.5 15.5L21 21"/></svg></button></form>')

BRAND = ('<a class="brand" href="{home}"><svg viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">'
         '<rect width="100" height="100" rx="24" fill="#1A1A19"/>'
         '<rect x="20" y="62" width="60" height="13" rx="6.5" fill="#39FF14"/>'
         '<rect x="20" y="43.5" width="44" height="13" rx="6.5" fill="#39FF14"/>'
         '<rect x="20" y="25" width="28" height="13" rx="6.5" fill="#39FF14"/></svg>'
         '<span>bondari<b>um</b></span></a>')

START_RE = re.compile(r'  <(?:header|div) class="topbar"(?: data-rubrik="[a-z]+")?>\n')
# Ende der Kopfzeile, samt einer schon geschriebenen Brotkrumen-Zeile (idempotent)
END_RE = re.compile(r'    </nav>\n(?:    <form class="kopfsuche"[^\n]*\n)?  </(?:header|div)>\n(?:  <nav class="krumen"[^\n]*\n)?')
FOOTER_RE = re.compile(r'  <footer\b[^>]*>.*?</footer>\n', re.S)
LDJSON_RE = re.compile(r'<script type="application/ld\+json">(.*?)</script>', re.S)
SITE = "https://www.bondarium.de/"

# Fußzeile aller Seiten (seit 30.09.2026; Vorbild: Startseite, dort seit 29.09.2026). Spalten: (Überschrift, id, Links)
FOOTER = [
    ("Anleihen", "f-anl", [("Anleihen-Suche", "anleihen-suche.html"), ("Top-10-Listen", "anleihen.html"),
                           ("Anleihen-Beispiele", "guide.html"), ("Anleihen-ETFs", "anleihen-etf.html")]),
    ("Akademie", "f-akad", [("Verstehen", "wissen.html"), ("Entscheiden", "entscheiden.html"), ("Kaufen", "kaufen.html"),
                            ("Glossar", "begriffe.html")]),
    ("Zinsen", "f-zins", [("Renditen seit 1970", "renditen.html"), ("Zinskurve", "zinskurve.html"),
                          ("Risikoaufschläge", "risikoaufschlaege.html"), ("Langläufer", "langlaeufer.html")]),
    ("Bondarium", "f-bond", [("Über uns", "ueber-uns.html"), ("Datenquellen", "rechtliches.html#haftung"),
                             ("Impressum", "rechtliches.html#impressum"), ("Datenschutz", "rechtliches.html#datenschutz")]),
]
FOOTER_HINWEIS = 'Keine Anlageberatung. Alle Angaben ohne Gewähr; Börsenkurse bis zu 15&nbsp;Minuten verzögert. · <a href="{p}rechtliches.html">Rechtliches</a>'

# Rückfall, falls site.js nicht lädt (Netzfehler): eine Minimalform für alle Seiten statt der früher je Seite
# verschieden kopierten Zeilen (esc, minus, load, hoverWrap …). Die volle Fassung steht in site.js.
FALLBACK = ('// Rückfall, falls site.js nicht lädt (Netzfehler): Minimalform, damit die Seite trotzdem rendert – die volle Fassung steht in site.js.\n'
            'window.MC = window.MC || { esc: function (s) { return String(s).replace(/[&<>"\']/g, function (c) { return "&#" + c.charCodeAt(0) + ";"; }); }, '
            'minus: function (s) { return String(s).replace(/^-/, "\\u2212"); }, '
            'zahl: function (v, d) { return typeof v === "number" && isFinite(v) ? v.toLocaleString("de-DE", { minimumFractionDigits: d || 0, maximumFractionDigits: d || 0 }).replace(/^-/, "\\u2212") : "\\u2013"; }, '
            'load: function (n) { return fetch(n).then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); }); }, '
            'hoverWrap: function (s) { return s; }, navInit: function () {} };\n')
FALLBACK_RE = re.compile(
    r'(?:// (?:Fallback, falls site\.js nicht l(?:ae|ä)dt|Rückfall, falls site\.js nicht lädt)[^\n]*\n(?://(?! Nav)[^\n]*\n)?)?'
    r'window\.MC = window\.MC \|\| \{[^\n]*\};\n'
    r'(?:(?://[^\n]*\n)?window\.MC\.\w+ = window\.MC\.\w+ \|\| [^\n]*;\n)*')


RUBRIK = {"Verstehen": "verstehen", "Entscheiden": "entscheiden", "Kaufen": "kaufen"}
# Seiten außerhalb der Aufklapper (die Anleihen-Suche steht seit 25.09.2026 abends im Menü Kaufen;
# anleihe.html ist der Steckbrief einer einzelnen Anleihe, erreichbar aus der Suche und den Datenseiten)
RUBRIK_EXTRA = {"ueber-uns.html": "ueber"}


def links(items):
    """Nur die Einträge (Beschriftung, Datei) einer Gruppe – ohne Überschriften und Trennlinien."""
    return [i for i in items if isinstance(i, tuple)]


def rubrik(page):
    """Rubrik der Seite (Kennfarbe in base.css): verstehen, entscheiden, kaufen, beobachten, ueber – sonst start (Startseite, Rechtliches, 404)."""
    for label, target, items in GROUPS:
        if page == target or any(i[1] == page for i in links(items)):
            return RUBRIK[label]
    for label, target, items in MENUS:
        if page == target or page in MENU_EXTRA.get(label, []) or any(i[1] == page for i in links(items)):
            return MENU_RUBRIK[label]
    return RUBRIK_EXTRA.get(page, "start")


def menu_items(items, page, p):
    """Zeilen eines Aufklappers: Chips (Zeichenkette) und Einträge (Beschriftung, Datei[, Klasse])."""
    out = []
    for it in items:
        if isinstance(it, str):
            out.append(f'          <span class="nav-cap">{it}</span>')
        else:
            cls = " ".join(x for x in ((it[2] if len(it) > 2 else ""), "current" if it[1] == page else "") if x)
            out.append(f'          <a href="{p}{it[1]}"' + (f' class="{cls}"' if cls else "") + f'>{it[0]}</a>')
    return out


def krumen(page, s, absolute=False):
    """Brotkrumen-Zeile aus dem JSON-LD BreadcrumbList der Seite; leer auf Startseite/404 oder ohne Liste."""
    if page in ("index.html", "404.html"):
        return ""
    liste = None
    for m in LDJSON_RE.finditer(s):
        try:
            d = json.loads(m.group(1))
        except ValueError:
            continue
        stack = [d]
        while stack and liste is None:
            x = stack.pop()
            if isinstance(x, dict):
                if x.get("@type") == "BreadcrumbList":
                    liste = x.get("itemListElement") or []
                else:
                    stack.extend(x.values())
            elif isinstance(x, list):
                stack.extend(x)
    if not liste or len(liste) < 2:
        return ""
    liste = sorted(liste, key=lambda i: i.get("position", 0))
    li = []
    for n, it in enumerate(liste):
        name = html.escape(str(it.get("name", "")), quote=False)
        url = str(it.get("item", ""))
        if n == len(liste) - 1:
            li.append(f'<li><span aria-current="page">{name}</span></li>')
            continue
        rel = url[len(SITE):] if url.startswith(SITE) else url
        href = ("/" if absolute else "index.html") if rel in ("", "index.html") else ("/" if absolute else "") + rel
        li.append(f'<li><a href="{href}">{name}</a></li>')
    return f'  <nav class="krumen" aria-label="Brotkrumen"><ol>{"".join(li)}</ol></nav>\n'


def footer(page, absolute=False):
    """Gemeinsame Fußzeile (FOOTER); der Link der aktuellen Seite trägt aria-current."""
    p = "/" if absolute else ""
    out = ['  <footer class="fuss">']
    for titel, fid, eintraege in FOOTER:
        a = "".join(f'<a href="{p}{ziel}"' + (' aria-current="page"' if ziel == page else "") + f'>{text}</a>' for text, ziel in eintraege)
        out.append(f'    <nav aria-labelledby="{fid}"><p class="fuss-k" id="{fid}">{titel}</p>{a}</nav>')
    out.append(f'    <p class="fuss-hw">{FOOTER_HINWEIS.format(p=p)}</p>')
    out.append("  </footer>")
    return "\n".join(out) + "\n"


def render(page, absolute=False):
    """Kopfzeile für die Seite `page` (Dateiname); absolute=True für 404.html."""
    p = "/" if absolute else ""
    home = "/" if absolute else "index.html"
    out = [f'  <header class="topbar" data-rubrik="{rubrik(page)}">', "    " + BRAND.format(home=home),
           # Burger-Knopf: nur am Handy sichtbar (base.css), klappt das Menü auf (site.js)
           '    <button type="button" class="nav-toggle" aria-expanded="false" aria-controls="sitenav" aria-label="Menü öffnen">'
           '<span class="nav-toggle-i" aria-hidden="true"></span></button>',
           '    <nav class="sitenav" id="sitenav" aria-label="Hauptnavigation">']
    rub = rubrik(page)
    cur = " current" if rub in RUBRIK.values() else ""
    out.append('      <div class="nav-group nav-akademie">')
    out.append(f'        <a href="{AKADEMIE[2] if absolute else AKADEMIE[1]}" class="nav-group-btn{cur}" aria-expanded="false">'
               f'<span>{AKADEMIE[0]}</span><span class="nav-caret" aria-hidden="true"></span></a>')
    out.append('        <div class="nav-group-menu">')
    for label, target, items in GROUPS:
        in_group = page == target or any(i[1] == page for i in links(items))
        c = ' class="nav-stufe current"' if in_group else ' class="nav-stufe"'
        out.append(f'          <a href="{p}{target}"{c}>{label}</a>')   # seit 28.09.2026 ohne Unterzeile (Nutzerwunsch)
    out += menu_items(AKADEMIE_EXTRA, page, p)
    out.append("        </div>")
    out.append("      </div>")
    # Aufklapper „Anleihen“ und „Zinsen“ (seit 29.09.2026): Übersicht (nur Handy), Chips, Einträge.
    # Der Kopf ist „current“, wenn die Seite zu diesem Menü gehört (Rubrik) – ein Eintrag, der zusätzlich in einem
    # anderen Menü steht (z. B. anleihen-etf-erklaert.html), markiert dort nur den Eintrag selbst.
    for a_label, a_target, a_items in MENUS:
        out.append(f'      <div class="nav-group nav-{MENU_RUBRIK[a_label]}">')
        c_kopf = " current" if rub == MENU_RUBRIK[a_label] else ""
        c_ov = " current" if page == a_target else ""
        out.append(f'        <a href="{p}{a_target}" class="nav-group-btn{c_kopf}" aria-expanded="false">'
                   f'<span>{a_label}</span><span class="nav-caret" aria-hidden="true"></span></a>')
        out.append('        <div class="nav-group-menu">')
        out.append(f'          <a href="{p}{a_target}" class="nav-ov{c_ov}">Übersicht</a>')
        out += menu_items(a_items, page, p)
        out.append("        </div>")
        out.append("      </div>")
    for label, target in BUTTONS:
        c = " current" if target == page else ""
        out.append(f'      <a href="{p}{target}" class="nav-cta{c}">{label}</a>')
    for label, target in LINKS:
        c = ' class="current"' if target == page else ""
        out.append(f'      <a href="{p}{target}"{c}>{label}</a>')
    out.append("    </nav>")
    out.append(SEARCH.format(p=p))
    out.append("  </header>")
    return "\n".join(out) + "\n"


def apply(check_only=False):
    changed, same, missing, ohne_fuss, ohne_mc = [], [], [], [], []
    for f in sorted(glob.glob("*.html")):
        s = open(f, encoding="utf-8").read()
        absolute = f == "404.html"
        m1 = START_RE.search(s)
        m2 = END_RE.search(s, m1.end()) if m1 else None
        if not (m1 and m2):
            missing.append(f)
            continue
        new = s[:m1.start()] + render(f, absolute=absolute) + krumen(f, s, absolute=absolute) + s[m2.end():]
        mf = FOOTER_RE.search(new)
        if mf:
            new = new[:mf.start()] + footer(f, absolute=absolute) + new[mf.end():]
        else:
            ohne_fuss.append(f)
        if FALLBACK_RE.search(new):
            new = FALLBACK_RE.sub(lambda m: FALLBACK, new, count=1)
        elif "site.js" in new and f != "404.html":
            ohne_mc.append(f)
        if new == s:
            same.append(f)
        else:
            changed.append(f)
            if not check_only:
                open(f, "w", encoding="utf-8").write(new)
    verb = "abweichend" if check_only else "geschrieben"
    print(f"{len(changed)} Seiten {verb}, {len(same)} unverändert" + (f", ohne Kopfzeile: {missing}" if missing else ""))
    if changed:
        print("  " + ", ".join(changed))
    if ohne_fuss:
        print(f"  ohne <footer>: {ohne_fuss}")
    if ohne_mc:
        print(f"  ohne MC-Rückfall-Block: {ohne_mc}")
    return 1 if (check_only and changed) or missing else 0


if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)) + "/..")
    sys.exit(apply(check_only="--check" in sys.argv))
