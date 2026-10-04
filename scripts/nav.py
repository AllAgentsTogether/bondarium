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

Menü seit 01.10.2026 abends (Nutzerentscheid „Navigation neu“, Diagramm im Chat): vier Aufklapper in der Reihenfolge
des Weges – Akademie (lernen), Anleihen (finden), Kaufen, Zinsen (beobachten) –, rechts das Suchfeld und der Knopf
„Mein Bondarium“ (KONTO). „Über uns“ steht nur noch in der Fußzeile. Jede Seite steht genau einmal im Menü und ist
mit zwei Klicks erreichbar. Der Gruppenkopf ist ein Link auf die Übersichtsseite (wissen.html, anleihen.html,
kaufen.html, beobachten.html).
  * AKADEMIE: drei Spalten (Grundlagen, Auswählen, Für Fortgeschrittene) mit allen Themen direkt im Aufklapper, darunter
    über die ganze Breite das Glossar. Die Übersicht wissen.html trägt dieselben drei Abschnitte (#grundlagen,
    #auswaehlen, #fortgeschrittene); die früheren Übersichten entscheiden.html und vertiefen.html leiten dorthin (.htaccess).
  * MENUS (ANLEIHEN, KAUFEN, ZINSEN): einfache Listen. Einträge:
  ("Beschriftung", "datei.html")  Menüeintrag
  ("Beschriftung", "datei.html", "klasse")  Menüeintrag mit CSS-Klasse (nav-hl = dezenter Rahmen, für die Anleihen-Suche)
  "Beschriftung"                  Gruppenüberschrift im Aufklapper (grüner Chip)
Jeder Aufklapper bekommt zusätzlich den Eintrag „Übersicht“ mit der Klasse nav-ov – base.css zeigt ihn nur im
Handy-Akkordeon, wo der Kopf nicht navigiert, sondern auf- und zuklappt.
Vorher (25.09.–01.10.2026): „Der Weg“ mit den Stufen Verstehen, Entscheiden, Kaufen, Vertiefen unter „Akademie“.

Menü ändern: nur AKADEMIE, ANLEIHEN, KAUFEN, ZINSEN, KONTO, FOOTER anpassen und das Skript laufen lassen.

Seit 30.09.2026 schreibt das Skript außerdem (alles idempotent, --check meldet Abweichungen):
  * die Brotkrumen-Zeile <nav class="krumen"> direkt unter der Kopfzeile – erzeugt aus dem JSON-LD
    BreadcrumbList der Seite (nicht auf index.html und 404.html; ohne BreadcrumbList keine Zeile),
  * die gemeinsame Fußzeile <footer class="fuss"> (FOOTER; fünf Spalten in der Reihenfolge des Menüs),
  * den Rückfall-Block für window.MC (FALLBACK) in einheitlicher Minimalform, falls site.js nicht lädt.
"""
import html
import json
import glob
import os
import re
import sys

# Akademie: (Beschriftung, Übersichtsseite, Spalten, Fußeintrag). Spalte = (Überschrift, Sprungmarke auf der Übersicht, Einträge).
# Grundlagen = was man vor dem ersten Kauf wissen sollte (bis 01.10.2026 „Verstehen“); Auswählen = passt das zu mir und was
# (bis 01.10.2026 „Entscheiden“, dazu die vier Beispiele nach Ziel und der ETF-Artikel); Für Fortgeschrittene = bis 01.10.2026 „Vertiefen“.
AKADEMIE = ("Akademie", "wissen.html", [
    ("Grundlagen", "grundlagen", [
        ("Anleihen einfach erklärt", "grundlagen.html"),
        ("Anleihe-Arten", "anleihe-arten.html"),
        ("Zinsniveau", "zinsniveau.html"),   # erklärt, was das Zinsniveau bewegt – vor „Laufzeit“, die zeigt, was es mit der Anleihe macht
        ("Laufzeit", "laufzeit.html"),
        ("Bonität und Ratings", "bonitaet.html"),
        ("Risiko kennen", "risiko.html"),
        ("Kündbare Anleihen", "kuendbare-anleihen.html"),
    ]),
    ("Auswählen", "auswaehlen", [
        ("Sind Anleihen etwas für dich?", "anlegerprofile.html"),
        ("Welche Anleihe wozu passt?", "anlageziele.html"),
        ("Wie viel Anleihen ins Depot?", "anleihen-anteil.html"),   # seit 01.10.2026: Anleihen neben Aktien – Mischung, Faustregeln, Nachjustieren
        ("Anleihen-Beispiele nach Ziel", "guide.html"),   # Anleitungen, keine Liste – bis 01.10.2026 im Menü „Anleihen“
        ("ETF oder Anleihe?", "etf-oder-anleihe.html"),
        ("Anleihen-ETF: Vor- und Nachteile", "anleihen-etf-erklaert.html"),
        ("Anleihen für Unternehmen", "anleihen-fuer-unternehmen.html"),   # seit 01.10.2026: Depot, LEI, Steuern, Bilanz – Hausbegriff „Unternehmen“ (nicht „Firmen“); die Listen im Menü „Anleihen“ heißen „Unternehmensanleihen …“
    ]),
    ("Für Fortgeschrittene", "fortgeschrittene", [
        ("Mehr aus Anleihen herausholen", "fortgeschrittene.html"),
        ("Duration und Konvexität", "duration.html"),
        ("Rendite richtig lesen", "rendite-lesen.html"),
        ("Leiter, Hantel, Roll-down", "anleihenleiter.html"),
        ("Marktsignale lesen", "markttechnik.html"),
    ]),
], ("Glossar", "begriffe.html", "Fachbegriffe von A bis Z"))
# „Anleihen“: alles, was konkrete Anleihen zeigt – Suche und Ranglisten. Art zuerst („Staatsanleihen nach Laufzeit“), damit
# man die Liste beim Überfliegen findet. „Top 10“ muss direkt draufstehen (Nutzerwunsch 29.09.2026).
ANLEIHEN = ("Anleihen", "anleihen.html", [
    ("Anleihen-Suche", "anleihen-suche.html", "nav-hl"),
    "Top 10 meistgehandelt",
    ("Staatsanleihen nach Laufzeit", "staatsanleihen-laufzeit.html"),
    ("Staatsanleihen nach Ländern", "anleihen-laender.html"),
    ("Unternehmensanleihen nach Laufzeit", "unternehmensanleihen-laufzeit.html"),
    ("Unternehmensanleihen nach Ländern", "unternehmensanleihen-laender.html"),
    ("Anleihen-ETFs", "anleihen-etf.html"),
    "Top 30",   # höchster Kupon unter den Anleihen der EZB-Liste – drei Top 30 auf einer Seite: Staat, Öffentlich, Unternehmen
    ("Anleihen nach Kupon", "anleihen-kupon.html"),
])
# „Kaufen“ (seit 01.10.2026 eigener Hauptpunkt): alles, was man beim Kauf braucht – Anleitung, Broker, Handelsplätze,
# Steuern und Kosten, Rechner (der Rechner stand vorher doppelt: unter Entscheiden und unter „Werkzeuge“).
# Seit 02.10.2026 mit zwei grünen Chips wie in Akademie und Anleihen (Nutzerwunsch: „bei Kaufen und Zinsen steht nirgendwo der grüne
# Kasten“): erst der Weg zum Kauf, dann was er kostet und bringt.
KAUFEN = ("Kaufen", "kaufen.html", [
    "Schritt für Schritt",
    ("Deine erste Anleihe", "erste-anleihe.html"),
    ("Broker im Vergleich", "broker-vergleich.html"),
    ("Handelsplätze", "handelsplaetze.html"),
    "Kosten und Rendite",
    ("Steuern und Handelskosten", "steuern-handelskosten.html"),
    ("Rechner", "rechner.html"),
])
# „Zinsen“: Marktdaten, täglich aktuell. Kopf = Übersicht beobachten.html (Dateiname bleibt, damit alle Links gelten).
# „Renditen“ steht vor Staats- und Unternehmensanleihen, damit die Einträge nicht wie die Listen im Menü „Anleihen“ klingen.
# Seit 02.10.2026 mit grünen Chips (Nutzerwunsch wie bei Kaufen): Staatsanleihen, Unternehmensanleihen und – eigener Chip, weil sie
# Kursverläufe einzelner Anleihen zeigen statt Renditen (Nutzer: „Langläufer passt nicht ganz in der Zuordnung“) – Lange Laufzeiten.
ZINSEN = ("Zinsen", "beobachten.html", [
    "Staatsanleihen",
    ("Renditen von Staatsanleihen seit 1970", "renditen.html"),
    ("Zinskurve seit 1972", "zinskurve.html"),
    ("Realzins seit 1970", "realzins.html"),
    "Unternehmensanleihen",
    ("Renditen von Unternehmensanleihen seit 1984", "unternehmensanleihen.html"),
    ("Risikoaufschläge seit 1984", "risikoaufschlaege.html"),
    "Lange Laufzeiten",
    ("Langläufer", "langlaeufer.html"),
])
# Die Aufklapper neben der Akademie, in dieser Reihenfolge; Rubrik-Schlüssel je Menü; Zusatzseiten, die zu einem Menü zählen
MENUS = [ANLEIHEN, KAUFEN, ZINSEN]
MENU_RUBRIK = {"Anleihen": "anleihen", "Kaufen": "kaufen", "Zinsen": "zinsen"}
MENU_EXTRA = {"Anleihen": ["anleihe.html"]}
# Knopf „Mein Bondarium“ rechts außen, hinter dem Suchfeld (Benutzerbereich konto.html: Anmeldung, Merkliste und das Musterdepot „Mein Depot“). Bis 1000 px
# steht er stattdessen als letzter Eintrag im Burger-Menü (Klasse nav-konto) – base.css zeigt jeweils nur eines von beiden.
KONTO = ("Mein Bondarium", "konto.html")
KONTO_BILD = ('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" '
              'aria-hidden="true" focusable="false"><circle cx="12" cy="8.5" r="4"/><path d="M4.5 20.5c1.2-4 4-5.5 7.5-5.5s6.3 1.5 7.5 5.5"/></svg>')
# Suchfeld rechts außen (seit 26.09.2026, Nutzerwunsch „Feld ganz oben rechts … direkt in die Anleihensuche“):
# schickt q an die Anleihen-Suche; leer abgeschickt führt site.js direkt auf die Suchseite (Fokus ins Suchfeld).
# Im DOM nach dem Menü (Tab-Reihenfolge Marke → Menü → Suche); der Lupen-Knopf steht per CSS links im Feld.
SEARCH = ('    <form class="kopfsuche" action="{p}anleihen-suche.html" method="get" role="search" aria-label="Anleihen-Suche">'
          '<input type="search" name="q" placeholder="Anleihe suchen" aria-label="Anleihe suchen – Name, ISIN oder WKN" '
          'autocomplete="off" spellcheck="false" enterkeyhint="search">'
          '<button type="submit" aria-label="Suchen"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false"><circle cx="10.5" cy="10.5" r="6.5"/><path d="M15.5 15.5L21 21"/></svg></button></form>')

# Logo 06 „Kompakt & modern“ (seit 04.10.2026, Reinzeichnung des Nutzers): Bildzeichen = volles weißes „b“ im schwarzen Quadrat,
# grüner Punkt mit schwarzem Ring oben rechts am Bauch – vermessen und nur aus Flächen gebaut (keine Maske, keine IDs).
# Wortmarke aus der Vorlage nachgezeichnet (Pfad im Pixelmaß der Vorlage, 1303 × 210), i-Punkt grün (auf dem grünen Band dunkelgrün,
# siehe base.css). Quelle: tmp/logo-06/v2 (bauen2.py, spur.py, pfad.py). Keine Webschrift nötig.
BRAND_WORT = "M0.9 18L4 17.4L30 17.1L42 17.4L42.6 18L43.2 25L43.3 81L44 83C48 80.3 52.2 76.8 56 74.8C59.8 72.7 63 71.7 67 70.7C71 69.6 75.5 68.7 80 68.4C84.5 68.2 88.8 68.2 94 68.9C99.2 69.6 106.2 71.1 111 72.8C115.8 74.4 119.2 76.3 123 78.6C126.8 80.9 130.3 83.2 134 86.6C137.7 90 142 94.8 145 99C148.1 103.2 150.2 107.2 152.1 112C154 116.8 155.5 123.7 156.3 128C157.1 132.3 157 134.7 157 138C157.1 141.3 156.9 145.2 156.6 148C156.4 150.8 156.3 152 155.5 155C154.8 158 153.8 162.5 152.4 166C151 169.5 149.9 172.2 147.2 176C144.6 179.8 139.8 185.6 136.6 189C133.4 192.4 130.8 194.2 128 196.2C125.2 198.2 122.8 199.6 120 201.1C117.2 202.6 114.5 204 111 205.2C107.5 206.4 102.3 207.7 99 208.5C95.7 209.2 94.5 209.4 91 209.6C87.5 209.8 82.5 210 78 209.5C73.5 208.9 68.5 208 64 206.3C59.5 204.6 54.7 201.8 51 199.5C47.3 197.3 45 195 42 192.8C41.7 196.8 41.5 202.7 41.2 205C40.9 207.3 40.4 205.9 40 206.4L8 206.5L0.9 206L0.9 18ZM575.8 18L577 17.4L599 17.2C604.7 17.2 612.9 17.2 616 17.4C619.1 17.5 617.2 17.8 617.8 18L618.3 41L618.1 206L617 206.6L578 206.2L577 194.2C573 197.2 568.2 201.1 565 203.1C561.8 205.2 560.8 205.4 558 206.4C555.2 207.4 552.5 208.6 548 209.2C543.5 209.7 536.2 210 531 209.6C525.8 209.1 521.3 207.8 517 206.3C512.7 204.8 508.5 202.4 505 200.3C501.5 198.3 499 196.7 496 193.9C493 191.2 489.5 187.5 486.8 184C484.1 180.5 481.8 177 479.8 173C477.8 169 476 164.2 474.8 160C473.6 155.8 472.9 152.7 472.5 148C472.1 143.3 472.2 136.2 472.4 132C472.6 127.8 473.2 125.7 473.7 123C474.3 120.3 474.6 119 475.6 116C476.6 113 478.5 108 479.9 105C481.3 102 481.6 101 483.8 98C486.1 95 490.3 90 493.3 87C496.4 84 499.1 81.8 502 79.7C504.9 77.6 508.5 75.7 511 74.4C513.5 73.1 513.8 72.8 517 71.8C520.2 70.9 526 69.3 530 68.7C534 68.1 538 68.1 541 68.1C544 68.2 544.7 68 548 68.8C551.3 69.5 556.5 70.6 561 72.5C565.5 74.4 570.3 77.7 575 80.4L575.7 77L575.8 18ZM229.1 69C233.5 68.3 235.4 68.4 239 68.3C242.6 68.3 248 68.5 251 68.8C254 69 253.2 68.7 257 69.7C260.8 70.7 269.5 73 274 74.7C278.5 76.3 280.5 77.5 284 79.7C287.5 81.9 291.7 85 295 87.9C298.3 90.8 301.3 93.9 304 97.2C306.7 100.6 309.2 103.9 311.2 108C313.3 112.1 315.1 117.5 316.3 122C317.5 126.5 318.1 130.3 318.3 135C318.5 139.7 318.2 145.3 317.5 150C316.8 154.7 316 158.7 314.3 163C312.6 167.3 310 171.9 307.3 176C304.6 180.1 301.4 183.9 298 187.3C294.6 190.7 291 193.7 287 196.3C283 199 278.3 201.4 274 203.2C269.7 205.1 265.3 206.4 261 207.5C256.7 208.5 252.3 208.9 248 209.6L230 209.3C225 208.2 219.8 207.6 215 206.1C210.2 204.5 205.5 202.6 201 200.1C196.5 197.6 191.9 194.2 188.2 191C184.4 187.8 181.4 184.5 178.7 181C175.9 177.5 173.7 174 171.7 170C169.7 166 167.9 161.7 166.7 157C165.6 152.3 165 146 164.7 142C164.4 138 164.5 136 164.8 133C165 130 165.2 127.7 166 124C166.9 120.3 168 115.3 170 111C171.9 106.7 174.4 102.2 177.6 98C180.8 93.8 185.4 89.4 189.3 86C193.2 82.6 197.1 80.1 201 77.9C204.9 75.7 208.3 74.1 213 72.7C217.7 71.2 224.8 69.7 229.1 69ZM397.4 69C400.9 68.3 402.2 68.4 405 68.4C407.8 68.3 410.8 68.2 414 68.6C417.2 69 421.3 70 424 70.7C426.7 71.4 427.5 71.6 430 72.7C432.5 73.8 436.3 75.8 439 77.5C441.7 79.2 443.7 80.6 446 82.7C448.3 84.8 450.7 87.6 452.5 90C454.4 92.4 455.5 94 457 97C458.5 100 460.3 103.8 461.3 108C462.4 112.2 462.6 117.3 463.3 122L463 206C462.7 206.2 463 206.5 462 206.6C461 206.7 458.7 206.6 457 206.6L425 206.6L421.8 206L421.5 132C421.2 129 421 125.5 420.4 123C419.9 120.5 419.4 119.1 418.2 117C417 114.9 415 112.3 413 110.6C411 108.8 408 107.5 406 106.6C404 105.7 402.7 105.6 401 105.3C399.3 105 398.3 104.7 396 105C393.7 105.2 389.8 105.7 387 106.7C384.2 107.7 381.2 109.3 379 111C376.8 112.7 375.1 114.7 373.6 117C372.1 119.3 370.6 122.5 369.8 125C369 127.5 369 129.7 368.6 132L368.3 206L367 206.7L328 206.5L327.1 205L327.3 72L331 71.3L365 71.4L365.8 72C366.1 75.7 366.3 81 366.5 83C366.6 85 366.8 83.7 367 84C368.7 82.6 369.2 81.6 372 79.7C374.8 77.9 379.8 74.6 384 72.8C388.2 71 393.9 69.7 397.4 69ZM683.1 69C687.2 68.3 687.2 68.4 691 68.3C694.8 68.2 701.3 68.2 706 68.6C710.7 69 715.7 70.1 719 70.8C722.3 71.5 722.7 71.4 726 72.8C729.3 74.1 736.2 77.4 739 78.9C741.8 80.4 741 79.9 743 81.8C745 83.6 749 87.5 751.2 90C753.4 92.5 754.6 94 756.1 97C757.7 100 759.3 104 760.4 108C761.5 112 761.8 116.7 762.5 121L762.5 205L762 206.5L725 206.3L723.7 205L723.2 195L722 194.4C720.7 195.7 719.6 197 718 198.2C716.4 199.5 714.6 200.8 712.6 202C710.6 203.2 708.1 204.4 706 205.3C703.9 206.2 703.5 206.6 700 207.3C696.5 208 689.5 209.4 685 209.7C680.5 210.1 677.3 210 673 209.4C668.7 208.9 663.3 208 659 206.4C654.7 204.9 649.9 201.9 647 200.2C644.1 198.5 643.8 198.4 641.6 196C639.4 193.6 635.5 188.5 633.8 186C632.2 183.5 632.4 183.2 631.7 181C631 178.8 629.9 176.5 629.6 173C629.3 169.5 629.7 162.8 629.9 160C630.1 157.2 630.1 158.2 630.9 156C631.7 153.8 633.4 149.4 634.8 147C636.1 144.6 637.3 143.4 639 141.7C640.7 140 643.2 138.1 645 136.8C646.8 135.4 647.7 134.8 650 133.6C652.3 132.4 655.2 130.8 659 129.6C662.8 128.4 667.8 127.2 673 126.4C678.2 125.6 684.3 125.4 690 125L717 125.1C718 125.1 719.3 125.1 720 124.9C720.7 124.7 720.9 124.3 721.4 124C721.4 122 721.8 120 721.4 118C721 116 720.2 113.9 719 112C717.8 110.1 716 108.2 714 106.7C712 105.2 710 104 707 103.1C704 102.2 698.8 101.6 696 101.4C693.2 101.1 692.3 101.3 690 101.6C687.7 101.9 685.2 102 682 103C678.8 104.1 674.5 105.7 671 107.8C667.5 110 662.8 114.5 661 115.9C659.2 117.2 660.3 115.9 660 115.9L643 104.4L636.4 99C636.8 97.7 636.6 97 637.7 95C638.7 93 641.2 88.9 642.6 87C644 85.1 644.8 84.6 646 83.5C647.2 82.5 647.8 82.1 650 80.7C652.2 79.4 656.3 76.8 659 75.5C661.7 74.1 662 73.7 666 72.7C670 71.6 678.9 69.7 683.1 69ZM1157.5 69C1161.5 68.5 1167.6 68.4 1171 68.5C1174.4 68.6 1175.8 69.2 1178 69.7C1180.2 70.2 1182 70.8 1184 71.6C1186 72.5 1188 73.4 1190 74.6C1192 75.8 1194 77.2 1196 78.8C1198 80.3 1200.5 82.5 1202 84.1C1203.5 85.6 1204 86.8 1205 88.2C1205.3 88.1 1204.7 89.1 1206 87.9C1207.3 86.7 1210.3 83 1213 80.9C1215.7 78.7 1218.3 76.6 1222 74.8C1225.7 72.9 1231.3 70.9 1235 69.9C1238.7 68.9 1240.7 68.8 1244 68.6C1247.3 68.3 1251.2 68.2 1255 68.5C1258.8 68.9 1263.2 69.7 1267 70.8C1270.8 72 1274.7 73.6 1278 75.4C1281.3 77.3 1284.6 79.9 1287 82C1289.4 84.1 1290.6 85.5 1292.4 88C1294.1 90.5 1296.3 94.7 1297.5 97C1298.6 99.3 1298.7 99.7 1299.4 102C1300 104.3 1300.9 107 1301.4 111C1301.9 115 1302.1 121 1302.5 126L1302 206L1282 206.6L1263 206.5L1261.4 206L1261.4 135C1261.2 132.3 1261.4 129.8 1260.7 127C1260 124.2 1258.6 120.3 1257.3 118C1256.1 115.7 1255 114.4 1253.5 113C1251.9 111.6 1250.2 110.5 1248 109.7C1245.8 108.9 1242.5 108.4 1240 108.2C1237.5 108 1235.5 108 1233 108.7C1230.5 109.5 1227.1 111.1 1225 112.6C1222.9 114.2 1221.7 115.8 1220.4 118C1219.2 120.2 1218.2 123 1217.4 126C1216.7 129 1216.6 132.7 1216.1 136L1215.6 206L1214 206.6L1179 206.6L1174.4 206L1174.2 135C1173.9 132 1173.8 128.7 1173.3 126C1172.8 123.3 1172.2 121.2 1171 119C1169.8 116.8 1167.3 114.1 1166 112.7C1164.7 111.3 1164.3 111.3 1163 110.6C1161.7 110 1159.8 109.1 1158 108.7C1156.2 108.2 1154.5 107.7 1152 107.9C1149.5 108 1145.7 108.6 1143 109.5C1140.3 110.5 1137.8 112.2 1136 113.7C1134.2 115.3 1133.1 116.6 1131.9 119C1130.7 121.4 1129.4 125.2 1128.8 128C1128.1 130.8 1128.2 133.3 1127.9 136L1127.4 206L1125 206.6L1089 206.6L1086.1 206L1085.7 90L1086.3 72L1095 71.3L1126 71.5L1127 86.3C1128.3 84.8 1128.7 83.8 1131 81.8C1133.3 79.9 1138.3 76.3 1141 74.6C1143.7 72.9 1144.2 72.5 1147 71.6C1149.8 70.7 1153.5 69.5 1157.5 69ZM854.8 70C857.6 69.7 859.8 69.7 862 69.9C864.2 70.1 866.1 70.6 868.1 71L868.3 109L867 109.7L849 109.7C846 110.3 842.5 110.8 840 111.6C837.5 112.5 835.7 113.8 834 114.9C832.3 115.9 831.5 116.6 830.1 118C828.7 119.4 826.9 121.3 825.7 123C824.4 124.7 823.4 126.3 822.6 128C821.7 129.7 821.2 130.7 820.6 133C820 135.3 819.5 139 819 142L818.7 206L817 206.6L778 206.6L777.5 206L777.3 201L777.4 72L778 71.1L779 71.1L815 71.5C815.2 72 815.5 69.9 815.6 73C815.8 76.1 815.9 87 816 90C816.1 93 816.1 90.7 816.1 91L817 91.3C819.7 88.4 822 85.2 825 82.6C828 80 831.7 77.5 835 75.7C838.3 73.9 841.7 72.8 845 71.8C848.3 70.9 851.9 70.3 854.8 70ZM969.5 71C971.7 71.1 974.7 71 976 71.2C977.3 71.3 976.9 71.7 977.4 72L977.5 146C977.9 149.3 978 153.2 978.7 156C979.4 158.8 980.5 161.1 981.6 163C982.6 164.9 983.1 165.7 985 167.1C986.9 168.5 990.5 170.3 993 171.3C995.5 172.2 998 172.5 1000 172.7C1002 172.9 1003.5 172.8 1005 172.6C1006.5 172.4 1006.8 172.5 1009 171.5C1011.2 170.5 1015.5 168.4 1018 166.5C1020.5 164.6 1022.4 162.6 1024 160C1025.7 157.4 1027.2 153.7 1028 151C1028.9 148.3 1028.8 146.3 1029.2 144L1029.4 72L1030 71.5L1046 71.2L1069 71.3L1070.6 72L1070.8 205L1070 206.5L1031 206.3C1030.7 205.9 1030.4 206.9 1030.2 205C1030.1 203.1 1030.1 198.3 1030 195L1029 194.2C1026.3 196.2 1024.3 198.1 1021 200.2C1017.7 202.2 1012.2 205.1 1009 206.5C1005.8 207.9 1004.5 207.9 1002 208.4C999.5 208.9 997.5 209.5 994 209.6C990.5 209.8 985 209.7 981 209.3C977 208.9 973.3 208.2 970 207.2C966.7 206.2 963.8 204.6 961 203.1C958.2 201.6 956 200.4 953.2 198C950.5 195.6 946.6 191.3 944.6 189C942.7 186.7 942.6 186 941.6 184C940.5 182 939.4 179.3 938.6 177C937.8 174.7 937.1 172.3 936.7 170C936.2 167.7 936.1 165.3 935.8 163L935 72L937 71.1L969.5 71ZM877.5 72L878 71.3L884 71.1L917 71.2L919.6 72L919.9 190C919.8 195 919.9 202.3 919.7 205C919.6 207.7 919.2 206 919 206.5L882 206.6L877.8 206L877.5 72ZM76 105C72.7 105.1 69.3 106.1 67 106.7C64.7 107.3 63.8 107.8 62 108.8C60.2 109.8 57.9 111 56 112.5C54.1 114.1 52.2 115.8 50.5 118C48.8 120.2 46.9 124 45.9 126C44.9 128 44.9 128.3 44.4 130C44 131.7 43.5 133.5 43.4 136C43.3 138.5 43.4 142.5 43.8 145C44.2 147.5 44.6 148.7 45.6 151C46.6 153.3 48.4 157 49.7 159C50.9 161 51.8 161.8 53 163C54.2 164.2 54.5 164.7 57 166.1C59.5 167.5 65 170.5 68 171.6C71 172.7 72.2 172.6 75 172.7C77.8 172.9 82.5 172.8 85 172.6C87.5 172.4 87.8 172.3 90 171.4C92.2 170.5 95.3 169.1 98 167.1C100.7 165.2 103.9 162.4 106 159.8C108.1 157.3 109.4 154.1 110.4 152C111.5 149.9 111.8 150 112.2 147C112.6 144 112.8 137.2 112.6 134C112.5 130.8 112 130.3 111.1 128C110.2 125.7 108.5 122 107.4 120C106.2 118 105.8 117.4 104.4 116C103 114.6 101.1 112.8 99 111.4C96.9 110 94 108.5 92 107.6C90 106.7 89.7 106.4 87 105.9C84.3 105.5 79.3 104.8 76 105ZM237 104.9C234.7 105.2 231.3 106 229 106.7C226.7 107.5 225 108.3 223 109.5C221 110.7 218.6 112.6 217 114C215.4 115.4 214.4 116.7 213.3 118C212.3 119.3 211.8 120 210.8 122C209.9 124 208.4 127.7 207.6 130C206.9 132.3 206.7 133.8 206.6 136C206.4 138.2 206.5 141.2 206.7 143C206.9 144.8 206.9 145 207.5 147C208.2 149 209.5 152.7 210.7 155C211.8 157.3 213.1 159.3 214.5 161C215.9 162.7 217.4 164.1 219 165.3C220.6 166.6 222 167.4 224 168.5C226 169.5 228.8 170.8 231 171.5C233.2 172.1 234.3 172.4 237 172.6C239.7 172.8 244.2 172.8 247 172.4C249.8 172.1 251.8 171.3 254 170.4C256.2 169.6 258.3 168.3 260 167.2C261.7 166.2 262.8 165.4 264.3 164C265.8 162.6 267.5 161.2 269 159C270.5 156.8 272.3 153 273.2 151C274.1 149 274.2 148.5 274.5 147C274.9 145.5 275.4 144.3 275.5 142C275.6 139.7 275.6 135.7 275.2 133C274.8 130.3 274.2 128.3 273.3 126C272.3 123.7 270.7 120.8 269.5 119C268.4 117.2 267.5 116.2 266.2 115C264.9 113.8 263.9 112.8 262 111.6C260.1 110.4 257 108.6 255 107.6C253 106.7 252 106.3 250 105.8C248 105.4 245.2 105 243 104.8C240.8 104.7 239.3 104.6 237 104.9ZM542 105C540.3 105.2 539 105.3 537 105.9C535 106.5 532 107.6 530 108.7C528 109.7 526.3 110.7 524.8 112C523.3 113.3 522.2 114.6 521 116.3C519.8 118 518.3 120 517.3 122C516.3 124 515.5 126 514.9 128C514.3 130 513.8 131.5 513.6 134C513.3 136.5 513.2 139.8 513.6 143C514 146.2 514.8 150.2 515.9 153C516.9 155.8 518.4 157.8 519.9 160C521.4 162.2 523 164.3 525.2 166C527.4 167.7 530.7 169.4 533 170.4C535.3 171.5 536.3 172 539 172.3C541.7 172.7 546 172.9 549 172.5C552 172.2 554.7 171.2 557 170.3C559.3 169.4 560.8 169 563 167.2C565.2 165.5 568.2 162.4 570.1 160C572 157.6 573.2 155.2 574.2 153C575.2 150.8 575.7 150.2 576.1 147C576.5 143.8 576.7 137.2 576.6 134C576.5 130.8 576 129.8 575.4 128C574.9 126.2 574.2 124.7 573.3 123C572.5 121.3 571.6 119.7 570.3 118C569.1 116.3 567.7 114.6 565.9 113C564.2 111.4 562.2 109.9 560 108.7C557.8 107.5 555.2 106.4 553 105.8C550.8 105.1 548.8 104.9 547 104.8C545.2 104.7 543.7 104.8 542 105ZM690 151.9C686 152.9 680.7 153.9 678 154.9C675.3 155.9 675 156.8 674 157.8C673 158.9 672.5 159.6 672 161C671.5 162.4 671 164.3 671 166C671 167.7 671.3 169.6 671.8 171C672.3 172.4 673 173.3 674 174.4C675 175.5 676.2 176.6 678 177.5C679.8 178.3 682.8 179.1 685 179.5C687.2 179.9 688.7 180 691 180C693.3 180 696.8 179.8 699 179.5C701.2 179.2 702.3 178.8 704 178.2C705.7 177.7 707.5 177 709 176.2C710.5 175.4 711.6 174.8 713 173.6C714.4 172.4 716.1 170.6 717.3 169C718.5 167.4 719.6 165.7 720.3 164C721.1 162.3 721.6 161 721.7 159C721.8 157 721.2 154.2 721 151.7L690 151.9Z"
BRAND = ('<a class="brand" href="{home}" aria-label="bondarium – Startseite">'
         '<svg class="brand-z" viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg" aria-hidden="true" focusable="false">'
         '<rect width="100" height="100" rx="22" fill="#1A1A19"/><path fill="#FBFAF7" d="M20.9 19.75C20.9 15.19 24.59 11.5 29.15 11.5C33.71 11.5 37.4 15.19 37.4 19.75L37.4 41C41.5 36.2 47 33.6 53.5 33.6C68 33.6 79.8 46.5 79.8 61C79.8 77.9 66.3 91.7 49.6 91.7C34.5 91.7 20.9 79.5 20.9 64Z"/><path fill="#1A1A19" d="M62 63C62 69.9 56.4 75.5 49.5 75.5C42.6 75.5 37 69.9 37 63C37 56.1 42.6 50.5 49.5 50.5C56.4 50.5 62 56.1 62 63ZM81.5 48.5C81.5 56.29 75.19 62.6 67.4 62.6C59.61 62.6 53.3 56.29 53.3 48.5C53.3 40.71 59.61 34.4 67.4 34.4C75.19 34.4 81.5 40.71 81.5 48.5Z"/><circle cx="67.4" cy="48.5" r="11.2" fill="#39FF14"/></svg>'
         '<svg class="brand-w" viewBox="0 0 1303 210" xmlns="http://www.w3.org/2000/svg" aria-hidden="true" focusable="false">'
         '<path fill="currentColor" d="' + BRAND_WORT + '"/><circle class="brand-i" cx="899.3" cy="28.6" r="27"/></svg></a>')

START_RE = re.compile(r'  <(?:header|div) class="topbar"(?: data-rubrik="[a-z]+")?>\n')
# Ende der Kopfzeile, samt einer schon geschriebenen Brotkrumen-Zeile (idempotent)
END_RE = re.compile(r'    </nav>\n(?:    <form class="kopfsuche"[^\n]*\n)?(?:    <a class="kopfkonto[^\n]*\n)?  </(?:header|div)>\n(?:  <nav class="krumen"[^\n]*\n)?')
FOOTER_RE = re.compile(r'  <footer\b[^>]*>.*?</footer>\n', re.S)
LDJSON_RE = re.compile(r'<script type="application/ld\+json">(.*?)</script>', re.S)
SITE = "https://www.bondarium.de/"

# Fußzeile aller Seiten (seit 30.09.2026; seit 01.10.2026 fünf Spalten in der Reihenfolge des Menüs). Spalten: (Überschrift, id, Links)
FOOTER = [
    ("Akademie", "f-akad", [("Grundlagen", "wissen.html#grundlagen"), ("Auswählen", "wissen.html#auswaehlen"),
                            ("Für Fortgeschrittene", "wissen.html#fortgeschrittene"), ("Glossar", "begriffe.html")]),
    ("Anleihen", "f-anl", [("Anleihen-Suche", "anleihen-suche.html"), ("Top-10-Listen", "anleihen.html"),
                           ("Anleihen nach Kupon", "anleihen-kupon.html"), ("Anleihen-ETFs", "anleihen-etf.html")]),
    ("Kaufen", "f-kauf", [("Deine erste Anleihe", "erste-anleihe.html"), ("Broker im Vergleich", "broker-vergleich.html"),
                          ("Steuern und Handelskosten", "steuern-handelskosten.html"), ("Rechner", "rechner.html")]),
    ("Zinsen", "f-zins", [("Renditen Staatsanleihen", "renditen.html"), ("Zinskurve", "zinskurve.html"),
                          ("Risikoaufschläge", "risikoaufschlaege.html"), ("Langläufer", "langlaeufer.html")]),
    ("Bondarium", "f-bond", [("Über uns", "ueber-uns.html"), ("Haftung und Datenquellen", "rechtliches.html#haftung"),
                             ("Impressum", "rechtliches.html#impressum"), ("Datenschutz", "rechtliches.html#datenschutz")]),
]
# Seit 03.10.2026 (Nutzertest): „Börsenkurse bis zu 15 Minuten verzögert“ beschrieb die Quelle (MiFIR), nicht das, was die Seiten zeigen –
# gezeigt werden Schlusskurse mit Datum, kein laufender Kurs.
FOOTER_HINWEIS = 'Keine Anlageberatung. Alle Angaben ohne Gewähr; Börsenkurse sind Schlusskurse, keine Echtzeitkurse. · <a href="{p}rechtliches.html">Rechtliches</a>'

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


# Seiten außerhalb der Aufklapper (anleihe.html ist der Steckbrief einer einzelnen Anleihe und zählt zum Menü „Anleihen“ – MENU_EXTRA)
RUBRIK_EXTRA = {"ueber-uns.html": "ueber"}


def links(items):
    """Nur die Einträge (Beschriftung, Datei) einer Gruppe – ohne Überschriften."""
    return [i for i in items if isinstance(i, tuple)]


def akademie_seiten():
    """Alle Seiten der Akademie: Übersicht, Themen der drei Spalten, Glossar."""
    return [AKADEMIE[1]] + [e[1] for _, _, eintraege in AKADEMIE[2] for e in eintraege] + [AKADEMIE[3][1]]


def rubrik(page):
    """Rubrik der Seite (data-rubrik am <header>): verstehen (Akademie), anleihen, kaufen, zinsen, ueber – sonst start
    (Startseite, Mein Bondarium, Rechtliches, 404). Die Kennfarbe ist seit 26.09.2026 überall dasselbe Grün."""
    if page in akademie_seiten():
        return "verstehen"
    for label, target, items in MENUS:
        if page == target or page in MENU_EXTRA.get(label, []) or any(i[1] == page for i in links(items)):
            return MENU_RUBRIK[label]
    return RUBRIK_EXTRA.get(page, "start")


def menu_items(items, page, p):
    """Zeilen eines Aufklappers: Chips (Zeichenkette) und Einträge (Beschriftung, Datei[, Klasse])."""
    out = []
    for it in items:
        if isinstance(it, str):
            out.append(f'          <span class="nav-cap">{html.escape(it, quote=False)}</span>')
        else:
            cls = " ".join(x for x in ((it[2] if len(it) > 2 else ""), "current" if it[1] == page else "") if x)
            out.append(f'          <a href="{p}{it[1]}"' + (f' class="{cls}"' if cls else "") + f'>{html.escape(it[0], quote=False)}</a>')
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
    # Aufklapper „Akademie“: drei Spalten mit allen Themen, darunter das Glossar über die ganze Breite
    a_label, a_target, spalten, fuss = AKADEMIE
    cur = " current" if rub == "verstehen" else ""
    out.append('      <div class="nav-group nav-akademie">')
    out.append(f'        <a href="{p}{a_target}" class="nav-group-btn{cur}" aria-expanded="false">'
               f'<span>{a_label}</span><span class="nav-caret" aria-hidden="true"></span></a>')
    out.append('        <div class="nav-group-menu nav-mega">')
    out.append(f'          <a href="{p}{a_target}" class="nav-ov{" current" if page == a_target else ""}">Übersicht</a>')
    out.append('          <div class="nav-spalten">')
    for titel, _, eintraege in spalten:
        out.append('          <div class="nav-spalte">')
        out += menu_items([titel] + eintraege, page, p)
        out.append('          </div>')
    out.append('          </div>')
    c = " current" if page == fuss[1] else ""
    out.append(f'          <a href="{p}{fuss[1]}" class="nav-fuss{c}">{fuss[0]}<small>{fuss[2]}</small></a>')
    out.append("        </div>")
    out.append("      </div>")
    # Aufklapper „Anleihen“, „Kaufen“ und „Zinsen“: Übersicht (nur Handy), Chips, Einträge.
    # Der Kopf ist „current“, wenn die Seite zu diesem Menü gehört (Rubrik).
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
    c = " current" if page == KONTO[1] else ""
    out.append(f'      <a href="{p}{KONTO[1]}" class="nav-konto{c}">{KONTO[0]}</a>')   # nur im Burger-Menü sichtbar (base.css)
    out.append("    </nav>")
    out.append(SEARCH.format(p=p))
    out.append(f'    <a class="kopfkonto{c}" href="{p}{KONTO[1]}"' + (' aria-current="page"' if c else "") + f'>{KONTO_BILD}<span>{KONTO[0]}</span></a>')
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
