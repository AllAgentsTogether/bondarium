# Design-Audit — metalconcrete Website

Stand: 2026-07-02 · Geprüft: alle 10 HTML-Seiten, base.css, logo.svg, logo-icon.svg
Fokus: Design, Konsistenz, Responsive, Typografie/Kontrast, designbezogene Accessibility (kein Daten-/Funktionsaudit).

---

## Schweregrad HOCH

1. **rechtliches.html (Z. 54–63): Nav-Link „Einflussfaktoren" fehlt.**
   Alle anderen Seiten haben 9 Nav-Links, diese nur 8. Auch der i18n-Key `navEinfluss` fehlt in beiden Übersetzungstabellen der Seite.

2. **verlierer.html (Z. 82): i18n-Key `fabAktien` fehlt in der Übersetzungstabelle.**
   Der Nav-Link „Aktien" nutzt `data-i18n="fabAktien"`, der Key existiert weder in DE noch EN → beim Umschalten auf Englisch bleibt „Aktien" als einziger Link unübersetzt. (rechtliches.html nutzt denselben Key — dort ebenfalls prüfen.)

3. **einflussfaktoren.html (Z. 59, 65–66): Kontrast-Fail.**
   `.unit`, `.ends`, `.ends-mid` nutzen `#9a9890` auf Weiß ≈ **2,8:1** — klar unter WCAG AA (4,5:1). Betroffen sind funktional wichtige Slider-Beschriftungen („unter/über Erwartung").

4. **einflussfaktoren.html (Z. 69): `outline: none` auf allen 14 Slidern ohne Focus-Ersatz.**
   Tastaturnutzer sehen nicht, welcher Slider fokussiert ist.

5. **sentiment.html (Z. 72, JS Z. 3405/3415): Pill-Kontraste.**
   Weiß auf `#B0883B` („Neutral") ≈ 3,3:1, auf `#D85A30` („Angst") ≈ 3,9:1 — bei 11,5 px klarer AA-Fail. Gleiches Problem in bip.html (Z. 316): weiße Zahlen auf Gold-Segment ≈ 3,3:1.

6. **kgv.html (Z. 136, 144): Inline-Styles hebeln Mobile-Typografie aus.**
   `<h2 style="font-size:26px">` überschreibt die Media Queries → diese h2 bleiben auf Smartphones 26 px statt 21 px, während die anderen Überschriften schrumpfen. Inkonsistente mobile Hierarchie.

---

## Schweregrad MITTEL

### Konsistenz zwischen Seiten

7. **Tote `.fab-aktien`-Regeln auf ALLEN Seiten + base.css (Z. 22–23).**
   Ein Floating-Action-Button ist definiert und hat auf jeder Seite Mobile-Overrides — aber kein einziges Dokument enthält das Element. Relikt eines entfernten Features, 10-fach dupliziert.

8. **`:root`-Variablen doppelt und driftend definiert.**
   base.css definiert die Palette, jede Seite wiederholt sie komplett und ergänzt eigene. Drift ist bereits passiert: dieselbe Farbe `#993C1D` heißt `--rot` (verlierer), `--neg` (steuer), `--eco-strong` (zinsen); `#1F7A5E` ist mal `--kgv`, mal `--pos`, mal hardcodiert (verlierer Z. 48).

9. **Uneinheitliche Überschriftengrößen.**
   h1: 34 px auf den meisten Seiten, aber 30 px auf verlierer.html (Z. 34) und sentiment.html (Z. 37); h2: 26 px (kgv) vs. 24 px (sentiment). Dadurch sind die 760px-Media-Queries mit `h1 { font-size: 30px }` auf diesen Seiten wirkungslos (No-Op, Kopierfehler).

10. **Footer-Muster uneinheitlich.**
    index/krisen: leerer `#datastand`-Span vor JS-Load → Footer beginnt mit verwaistem „·"; bip: langer 3-Zeilen-Disclaimer statt Kurzmuster; steuer: als einzige Datenseite ohne Datenstand; einflussfaktoren: Punkt + Mittelpunkt gemischt.

### CSS

11. **bip.html (Z. 320–321): Trennlinien werden nie gerendert.**
    Kommentar „dünne Trennlinien zwischen Segmenten", aber `stroke-width: 0` — gleichfarbige Segmente im gestapelten Balken stoßen hart aneinander.

12. **index.html (Z. 112): Inline-Style + `!important`-Krücke.**
    `style="margin-bottom:34px"` auf `.glance` überschreibt die Klassenregel (44 px); die Mobile-Anpassung braucht deshalb `!important`.

13. **Fehlende `:focus-visible`-Styles im gesamten Auftritt.**
    Hover ist überall sorgfältig gestaltet (Nav, Langswitch, Cards, Stats) — Focus nirgends. Nur Browser-Default-Outline, auf dem cremefarbenen Hintergrund teils schwach.

### Responsive / Touch

14. **Touch-Targets zu klein (alle Seiten, base.css Z. 14–21).**
    Nav-Links und DE/EN-Buttons: 12-px-Text, nur `padding-bottom: 3px` → Trefferflächen ~15 px hoch, 9 Links dicht nebeneinander auf Mobile (Empfehlung: ~44×44 px).

15. **SVG-Chart-Beschriftungen auf Mobile unlesbar.**
    10,5–12-px-Texte im 1000er-viewBox schrumpfen bei 560 px Darstellungsbreite auf effektiv ~6–7 px (krisen, kgv, sentiment, verlierer, zinsen). Zwischen ~600–1000 px Viewport gibt es zudem keine Scroll-Option (`.chart-scroll` greift erst < 600 px).

16. **einflussfaktoren.html (Z. 47–50, 367): Modell auf Mobile schwer benutzbar.**
    Bühne fix 1620×1186 px, Mindest-Scale 0,64 → ~1037 px Mindestbreite auf einem 390-px-Phone. Horizontales Wischen konkurriert mit dem Slider-Ziehen (Touch-Konflikt); Slider-Thumbs nur 12 px.

17. **index.html (Z. 37, 55): Glance-Grid-Trennlinien brechen bei 2 Spalten.**
    Zwischen ~460–920 px ist das Grid zweispaltig, die Border-Logik schaltet aber nur zwischen 1-spaltig/4-spaltig um → fehlende vertikale und fälschliche obere Trennlinien.

18. **`table { display: block }` (verlierer Z. 54, zinsen Z. 73, steuer Z. 61).**
    Zerstört in einigen Browsern die Tabellensemantik für Screenreader. Besser: Wrapper-Div mit `overflow-x: auto`. verlierer.html: 10-Spalten-Tabelle wird zwischen 680–1000 px stark gequetscht, ohne Scroll-Hinweis.

### Typografie / Charts

19. **verlierer.html (Z. 103): Überschrift als gestyltes `<p>` statt `<h2>`.**
    „Die Zusatzspalten erklärt" — die Seite hat gar kein `<h2>`, Hierarchie h1 → nichts. Auch krisen.html hat kein h2 (definiert aber eine h2-Regel = toter Stil).

20. **Chart-Labelfarben fallen als Text durch AA:**
    `#B0883B` ≈ 3,0:1 (kgv Regressions-Legende Z. 615; verlierer Endlabels), `#D85A30` ≈ 3,6:1, `#3E7CB8` ≈ 4,1:1 (verlierer COLORS Z. 2740).

21. **kgv.html Chart-Legenden fehlerhaft:**
    MSCI-Balkenchart (Z. 560–563): Legenden-Swatches grau/neutral, Balken aber farbig — Legendenfarbe kommt im Chart nicht vor. KGV-Chart: der „laufend ~26"-Punkt taucht im Chart auf, fehlt in der Legende.

22. **Chart-Interaktionen nur per Maus:**
    verlierer.html Hover-Fokus via `:has()` (Z. 50–52) + Hinweis „Linie mit der Maus fokussieren" — auf Touch-Geräten existiert das Feature nicht, der Hinweis ist dort irreführend; keine Tastatur-Alternative. einflussfaktoren.html: Tooltips hängen an nicht fokussierbaren `div`s (`cursor: help` suggeriert Interaktivität, die für Tastatur/Screenreader unzugänglich ist).

### Sonstiges

23. **og:image ist ein SVG (alle Seiten, Z. 17/21).**
    Facebook, X/Twitter, LinkedIn rendern keine SVG-Previews → Share-Karten ohne Bild. PNG/JPG 1200×630 nötig.

24. **rechtliches.html (Z. 48): falscher noscript-Banner.**
    „Diese Seite benötigt JavaScript für Charts und aktuelle Marktdaten" — die Seite hat weder Charts noch Marktdaten (Copy-Paste).

25. **sentiment.html: aria-Labels der Charts hardcodiert statt übersetzt.**
    Z. 3261/3358 englisch auch im DE-Modus, Z. 3391 deutsch auch im EN-Modus. kgv.html macht es korrekt via `L()`.

---

## Schweregrad NIEDRIG

26. **Tote Selektoren/Variablen (seitenweise):**
    krisen: `--kgv`, `.sw-kgv`; bip: `--kgv`; index: `--ma`, `.stat .ind`; einflussfaktoren: `.factor-card .note`; kgv: `.toc`, `section` (kein `<section>` im Markup!), `.sw-ma`, `.tag`-Familie; sentiment: `.compare`-Block, `.bigscore small`, kompletter ungenutzter i18n-Absatz `whySp500` (DE+EN); zinsen: `--kgv`, `.sw-kgv`, h2-Regeln ohne h2; verlierer/steuer: `--ma` ungenutzt.

27. **Hardcodierte Farben statt CSS-Variablen — flächig.**
    Die Palette wird in JS-Chart-Code und Inline-Styles auf praktisch jeder Seite dupliziert (z. T. dreifach: `--geo/--eco` in kgv Z. 159 UND sentiment Z. 3295 UND als Variable). Da SVGs inline gerendert werden, wäre `var(--…)` möglich. Eine Palettenänderung erfordert derzeit Suchen-und-Ersetzen über ~6 Dateien.

28. **Chaotische Media-Query-Struktur:**
    Regeln ohne Umbruch an Zeilenenden angehängt; kgv und zinsen haben je DREI getrennte `@media (max-width:600px)`-Blöcke. Wartbarkeitsrisiko.

29. **Kleinere Maß-Drifts zwischen Seiten:**
    `.sub`: 17 px/40 px (index) vs. 16 px/28 px (Rest); max-width 660 vs. 680 px; `section` margin-bottom 72 vs. 64 px; Tabellen-margin 36/32/28 px; Chart-min-width mobil 560 vs. 520 px; rechtliches definiert `.brand` neu, obwohl base.css sie liefert.

30. **10-px-Schriftgrade** an mehreren Stellen (index `.stand`, `.chart-x`, `.fg-ends`; einflussfaktoren Z. 67/77) — auf Mobile grenzwertig.

31. **`--muted` #6B6A64 ≈ 5:1** — besteht AA, aber knapp, und wird viel für 12–12,5-px-Text genutzt (Footer, Notes).

32. **Favicon: nur SVG-Data-URI**, kein `apple-touch-icon`/PNG-Fallback; Favicon-Design (flach) weicht von der Gradient-Bildmarke `logo-icon.svg` ab.

33. **Drei parallele ID-Schemata fürs Logo:** logo.svg und logo-icon.svg nutzen beide `id="c"/"stone"/"steel"` (Kollisionsrisiko bei Inline-Einbettung); die Inline-Header-Variante nutzt bereits `mcclip/mcstone/mcsteel`.

34. **Typografische Details:** deutsche Anführungszeichen mischen „ mit geradem " statt " (verlierer Z. 108–111, rechtliches Z. 87/111); Minuszeichen mal typografisch (−), mal ASCII-Hyphen (steuer Z. 230).

35. **`<nav>` ohne `aria-label`, kein Skip-Link** vor 9 Nav-Links + Topbar. Tabellen ohne `scope="col/row"`; steuer.html Z. 118 leere `<th>`.

36. **Sprachlogik-Details:** `og:locale:alternate en_US` deklariert, JS formatiert aber en-GB (dd/mm/yyyy); `applyLang` tauscht title/description, aber nicht og:/twitter:-Tags; verlierer Z. 2900 baut Label per fragilem String-Replace; sentiment: `datastand`-Fallbackfarbe inkonsistent zu kgv.

37. **Chart-Kleinigkeiten:** sentiment Z. 3246: „extreme Angst"-Label ragt über den viewBox-Rand (Clipping); Dual-Achsen nur halb farbcodiert (rechte Achse farbig, linke neutral); VIX-Chart zeigt nur 5 von 9 angekündigten Krisenbändern; AAII-Ø-Label auch im EN-Modus „Ø"; verlierer: lange Endlabels (x=928) können rechts anschneiden; einflussfaktoren Z. 47: `96vw` ignoriert Scrollbar-Breite.

---

## Positiv (kein Handlungsbedarf)

- Navigation auf 9 von 10 Seiten identisch, `class="current"` korrekt gesetzt.
- Grundkontraste solide: `--ink` ≈ 13:1, `--line` ≈ 6,1:1.
- Viewport-Meta überall; Tabellen/Charts bekommen unter 600–680 px horizontales Scrollen.
- Gute ARIA-Ansätze: Charts mit `role="img"` + `aria-label`/`<title>`, Langswitch mit `role="group"`/`aria-pressed`, Brand-SVG `aria-hidden` + Textlabel.
- Systemfonts → kein FOUT-Risiko.

## Nachtrag: Umgesetzte Design-Optimierungen (2026-07-02)

Alle Befunde dieses Audits wurden behoben. Zusätzlich umgesetzt: og-image.png (1200×630) + summary_large_image auf allen Seiten · apple-touch-icon.png + favicon-32.png · Skip-Link + `<main>`-Landmark (10 Seiten) · Chart-Scroll greift ab 900 px (min-width 700 px) · Scroll-Schatten an Tabellen/Charts · prefers-reduced-motion (site-weit + Partikel/Ring in einflussfaktoren) · Basis-Farbpalette nur noch zentral in base.css · sitemap.xml + robots.txt · theme-color + og:image-Maße/-Alt.

Bewusst nicht umgesetzt (Design-Entscheidungen): Dark Mode, Touch-Tooltips für Chart-Datenpunkte.

## Kernbefund

Zwei strukturelle Muster hinter den meisten Einzelbefunden:

1. **Geteilte Styles nur halb in base.css extrahiert** — der Rest ist ~10-fach kopiert und driftet bereits (tote FAB-Regeln, uneinheitliche h1-Größen, dreifach benannte Farben, tote Selektoren).
2. **Hover-Politur ohne Focus-/Kontrast-Pendant** — Maus-Nutzer bekommen überall liebevolle Zustände, Tastatur- und kontrastschwache Nutzer gehen leer aus.
