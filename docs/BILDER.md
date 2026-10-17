# Bilder, Zeichen und Schriften – Herkunft

Stand: 15.10.2026 · Grundlage: Angabe des Betreibers (Compliance-Prüfung 30.09.2026, Punkt E6), nachgeführt nach der Gesamtprüfung
(14.10.2026, A09-01). Alle Dateien liegen im Stammordner des Repositorys und gehen beim Deploy mit (`cp … *.svg *.png *.webp *.woff2`).

| Datei | Verwendung | Herkunft / Lizenz |
|---|---|---|
| `guide-nadine.webp`, `guide-tobias.webp`, `guide-michael.webp`, `guide-jonas.webp` und je `…-160.webp` (kleinere Fassung für `srcset`) | die vier erfundenen Beispielpersonen (anlageziele.html, Startseite „Was hast du mit deinem Geld vor?“) | mit KI erzeugt |
| `einstieg-portraet.webp`, `einstieg-portraet-240.webp` (kleinere Fassung, seit 15.10.2026) | Startseite, Block „Anleihen? Fang hier an.“ (`#bnd-einstieg`) – fiktive Beispielperson, freigestellt | mit KI erzeugt |
| `startseite-hero.webp` | Startseite, Kopf (ab 761 px Breite), Verlauf Weiß → Grün | mit KI erzeugt |
| `spot-*.svg` (47 Dateien) | Titel-Illustrationen der Themenseiten, Kacheln der Übersichten, Bilder im Menü (Regeln: docs/TITELBILD.md) | eigene Zeichnungen der Bildwelt 2.0 nach der Vorlage des Betreibers („Bondarium_Bildwelt_Unterseiten.pdf“ mit Asset-Paket, 30.09.2026), im selben Stil ergänzt, von Claude erzeugt |
| Icons, Illustrationen und Laufzeit-Ringe der Startseite, Schaubilder der Seiten | als SVG im HTML | eigene Zeichnungen, von Claude erzeugt (Bildwelt-Mockup des Betreibers, 30.09.2026); ersetzen die KI-Renderings `lernen-anlageziele.webp` und `lernen-anleihen-etf.webp` |
| `weltkarte.svg` | Top 10 nach Ländern (Staats- und Unternehmensanleihen, über `top10-tabellen.js`) | eigene Zeichnung, von Claude erzeugt, keine fremde Vorlage |
| Logo (Bildzeichen und Wortmarke) | Kopfzeile jeder Seite, als SVG im HTML (`scripts/nav.py`) | Logo 06 nach der Reinzeichnung des Betreibers (04.10.2026), vermessen und nachgezeichnet |
| `favicon.svg`, `favicon.ico`, `favicon-32.png`, `apple-touch-icon.png` | Browser-Tab, Lesezeichen, Startbildschirm; `apple-touch-icon.png` auch als Logo im JSON-LD | Bildzeichen von Logo 06 (04.10.2026) |
| `og-image.png` | Vorschaubild, wenn eine Seite geteilt wird (alle Seiten, 1200 × 630) | eigene Gestaltung aus Logo 06, Kupon-Zeitachse und der Schrift Manrope, von Claude erzeugt (04.10.2026); Quelle `tmp/logo-06/v2/og-image.html`, nicht im Repository |
| `logo.svg`, `logo-icon.svg` | auf der Website nicht mehr eingebunden (Logo steht inline); noch genutzt von `scripts/htaccess_test.sh` (Cache-Prüfung) und Vorschau-Werkzeugen in `tmp/` | ältere Logo-Fassungen, eigene Gestaltung |
| `source-sans-3.woff2`, `source-serif-4.woff2` | Schriften der Website (Text bzw. Titel, seit 11.10.2026) | Source Sans 3 und Source Serif 4 von Adobe, SIL Open Font License 1.1 |
| `manrope-*.woff2` | auf der Website nicht mehr eingebunden (bis 11.10.2026 Schrift der Website); noch genutzt von Vorschau-Werkzeugen in `tmp/` (der Deploy veröffentlicht sie seit 15.10.2026 nicht mehr; `scripts/htaccess_test.sh` fragt seit dem Schriftwechsel `source-sans-3.woff2` ab) (u. a. Quelle des og-image) | Manrope, SIL Open Font License 1.1 |

Hinweis auf der Website: `haftung.html`, Abschnitt „Bilder“ (KI-Fotos, erfundene Personen, eigene Weltkarte; bis 11.10.2026
`rechtliches.html`); dazu ein Satz auf `anlageziele.html`. Die gezeigten Personen gibt es nicht.

Kommt ein neues Bild dazu, hier eintragen – mit Herkunft und, bei fremden Bildern, Lizenz und Urheber.
