# Optimierung 09/2026 — metalconcrete Website

Stand: 02.09.2026 · Umfang: alle 14 Seiten, base.css, site.js, .htaccess, Workflow, Build-Skripte, Python-Pipeline.
Zwei Schleifen: (1) Analyse aller Ebenen + Umsetzung, (2) Re-Audit (Regressionen, Rest, Härtung) + Umsetzung.

## Ergebnis in Zahlen (Lighthouse mobil, gebaute Seiten)

| Seite | Performance vorher → nachher | CLS vorher → nachher |
|---|---|---|
| Startseite | 72 → 97 | 0,08 → 0,00 |
| renditen | 78 → 98 | 0,58 → 0,00 |
| einflussfaktoren | 80 → 98 | 0,45 → 0,00 |
| kgv / krisen / zinsen | 84–85 → 98 | 0,30 → 0,00 |
| vix / aaii / fear-greed | 84–94 → 88–98* | 0,15–0,31 → 0,00 |
| übrige | 90–100 → 98–100 | ≤ 0,21 → 0,00 |

Accessibility 100, Best Practices 100, SEO 100 auf allen Seiten. Startseiten-Script 1,5 s → 0,1 s.
(*Die letzte Lighthouse-Messung lief vor den Schleife-2-Fixes für vix/aaii/fear-greed; die eigene CLS-Messung zeigt danach überall 0,000.)

## Was umgesetzt wurde

**Architektur / Performance**
- Daten werden beim Deploy in die Seiten eingebettet (`scripts/inline_data.py` → `<script type="application/json" data-mc="…">`; `site.js: MC.load` nutzt sie, sonst fetch). Ein Request statt bis zu vier, kein Render-Sprung, kein „Flash“ alter Fallback-Werte, Fallbacks immer so frisch wie der Lauf. Die Quell-HTML im Repo bleiben unverändert (lokal weiter fetch).
- Layout-Sprünge beseitigt: reservierte Chart-Höhen, statische Fallbacks in Render-Struktur (Kacheln, Eyebrows, Tabellen, Tacho), Nav-Pfeil als CSS-Dreieck statt Fallback-Schriftzeichen.
- `.htaccess`: gzip für JSON/CSS/JS/SVG (Strato komprimierte nur HTML), non-www → www, `index.html` → `/`, eigene 404-Seite (`404.html`), COOP-Header, CSS/JS 7 Tage gecacht mit Inhalts-Hash als Versions-URL (`?v=`), gesetzt im Workflow.
- Startseite: gecachte Intl-Formatter, ein Render nach allen Daten (`Promise.allSettled`).
- EN-Kopien ohne `data-hover`/`data-tips`-Ballast (bis 90 KB je Seite).

**SEO**
- Keine Auto-Umschaltung nach Browsersprache mehr (Googlebot bekam auf deutschen URLs englischen Inhalt). Stattdessen dezente, schließbare Leiste „Also available in English“ (fixiert unten, kein Layout-Shift).
- `dateModified`/`lastmod` werden jetzt wirklich gesetzt – nur für Datenseiten; statische Seiten behalten ihr Datum.
- Titles ≤ 60, Descriptions ≤ 155 Zeichen, überall identisch (meta/og/twitter/T); `og:locale` en_GB (passend zum Datumsformat); EN-Breadcrumb/Publisher; llms.txt mit /en/-Hinweis.
- EN-Kopie: DE-Knopf setzt die Sprachwahl (vorher blieb die DE-Seite englisch); zur Laufzeit gerenderte Links zeigen auf /en/ (MutationObserver).

**UX / Inhalt**
- Startseiten-Kacheln verlinken auf die Analyseseiten; Zeitstempel kollidiert nicht mehr mit Kickern; Tooltips mit echten Datumsangaben, auch per Touch.
- renditen: Indien/Italien unterscheidbar (Italien rosé + gestrichelt), interaktive Legende (Hover hebt hervor, Klick blendet aus, Tastatur), Endlabels mit Wert, Tooltip lässt Länder ohne Daten aus, präzisierte Aktualisierungsangaben, Datenstand je Zeile.
- verlierer: „< <2 Wo.“-Bug, Widerspruch „eingefroren“ vs. „veraltet“ (jetzt „Daten-Stand … (eingefroren)“), Fallback = aktueller JSON-Stand (kein Content-Flash), Legende als Buttons, Texte auf den Datenstand bezogen.
- kgv: Fließtexte (Aufschläge, KGVs, „as reported“) werden aus den Live-Werten befüllt – Text und Chart widersprechen sich nicht mehr; Factsheet-Datum aus `valuations.sp500.asOf`.
- Label-Kollisionen behoben (AAII-Ø-Linien, VIX-Ø jetzt in der Legende, Zinsen-Endlabel, Krisen-„2025“-Band, kgv-Narrow-Labels).
- Typografisches Minus überall (Tabellen, EN-Währung „−€2,000“), EN-Datumsformate einheitlich, Prozentpunkte statt „%“ bei Zinsänderungen, Wording (Vortag, Q2 2026, Gedankenstriche).
- Crossnav ergänzt (einflussfaktoren, zinsen → kgv/renditen), Textlinks auf krisen.html; rechtliches.html in Seitenbreite (Nav bricht nicht mehr um).

**Barrierefreiheit**
- Kontrast-Fails behoben (kgv EM-Zeile, aaii-Neutral-Label, steuer Narrow-Chart); Chart-Tooltips als `role="group"` mit Live-Region; Sparklines nicht mehr in Links verschachtelt (sentiment); Slider mit 28-px-Touchziel und `aria-valuetext`; Faktor-Beschreibungen per `aria-describedby`; Überschriften-Hierarchie (fear-greed, einflussfaktoren, steuer); `th scope="row"`; Krisentyp auch als Text; sprechende Chart-Labels (steuer, aaii, bip-Fazit als Text + sr-Tabelle).

**Robustheit**
- Typ-Guards für alle JSON-Felder (kein TypeError/NaN/„Invalid Date“ bei lückenhaften Daten), `MC.esc` für alle JSON-Strings, try/catch um alle Renders, einheitliche `stale`-Klasse für „veraltet“.

**Pipeline / Betrieb (`.github/workflows/update-data.yml` – ersetzt `update-data.NEU.yml`)**
- Werktags alle 3 h (FAST) + nächtlicher Volllauf; Push-Deploys holen die Startseiten-Daten mit (keine älteren Repo-JSONs mehr online).
- `update_renditen.py` läuft jetzt (vorher nie: renditen.json war live seit 27.08. eingefroren) und `update_einfluss.py` nur im Volllauf (Drosselung greift nur mit Commit).
- Fehler werden nicht mehr verschluckt (`continue-on-error` statt `|| true`), Frische-Prüfung nur 1×/Tag (statt bis zu 48 Mails), je Land für Anleihen (OECD-Monatswerte „JJJJ-MM“ crashten die Prüfung), zusätzlich VIX-Datum.
- Build-Werkzeuge exakt gepinnt (`package.json` + `package-lock.json`, `npm ci --ignore-scripts`), Trigger-Konfiguration erst direkt vor dem Upload, Post-Deploy-Check (refresh-config.php darf nicht lesbar sein), Rebase-Abbruch bei Konflikt.
- Python: relative/absolute Plausibilitätsprüfungen (S&P, Renditen, F&G, VIX), `updated` in renditen.json nur bei echter Änderung (+ `checkedAt`), Tageswert wird nicht mehr durch OECD-Monatswert überschrieben, `sp500.asOf` aus dem Factsheet, iShares-PDFs wöchentlich statt täglich, Yardeni-Abruf (ungenutztes forwardPE) entfernt, Siblis-Parser an neues Tabellenlayout angepasst (World-CAPE war seit 12/2025 eingefroren), Retry nur bei Netz-/5xx-Fehlern, `::warning::`-Annotationen in Actions, Totalausfälle schreiben nichts mehr.

## Verifikation
Alle 14 Seiten + 404 in DE und EN, Desktop und Mobile: keine Konsolenfehler, kein Überlauf, CLS 0,000; i18n-Keys DE/EN vollständig; JSON-LD valide; HTML-Validierung ohne Befund; EN-Build (build_en.js) für alle 14 Seiten fehlerfrei; Workflow-YAML und eingebettetes Python geparst; Python-Skripte kompiliert, 50 Offline-Tests grün.

## Nächste Schritte für dich
1. **Impressum:** Platzhalter `[VORNAME NACHNAME]`, `[STRASSE HAUSNUMMER]`, `[PLZ ORT]`, `[E-MAIL-ADRESSE]` in `rechtliches.html` (Markup, T.de und T.en) ausfüllen – § 5 DDG; die Seite ist bis dahin `noindex`.
2. **Committen & pushen** (`git add -A && git commit && git push`): der Push löst den neuen Workflow aus (FAST-Lauf + Deploy). `update-data.NEU.yml` liegt jetzt in `_to_delete/` (Inhalt ist im aktiven Workflow aufgegangen) – Ordner nach Prüfung löschen.
3. **Nach dem ersten Deploy prüfen:** `https://www.metalconcrete.de/` (Header `content-encoding: gzip` auch für `data.json`), `https://metalconcrete.de/` → 301 auf www, `/index.html` → 301 auf `/`, eine Fantasie-URL → eigene 404-Seite, `/en/` inkl. DE-Knopf, `/trigger/refresh-config.php` → 403.
4. **Strato-Cron** an den neuen Takt anpassen (z. B. 1×/Tag `voll` als Fallback) oder abschalten; die GitHub-Crons decken werktags alles ab.
5. Optional: Verlierer-Ranking wöchentlich statt abgeschaltet (Kommentar im Workflow); Datenschutzerklärung um konkrete Strato-Löschfrist ergänzen.
