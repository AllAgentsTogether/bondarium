# Technik-Audit — Bondarium Website

Stand: 2026-07-02 · Zwei Prüfrunden, alle Befunde behoben.
Geprüft: 10 HTML-Seiten, base.css, 4 Python-Scripts, GitHub-Workflow, refresh.php, 4 JSON-Dateien.

---

## Runde 1 — Befunde und Fixes

### Hoch (behoben)

1. **update_sentiment.py: AAII-Parser lieferte falsche Live-Daten.** Summe der Umfragewerte 103,7 % statt ≈100, tägliche Duplikate in der Wochen-Historie, `asOf` = Abrufdatum statt Umfragedatum. → Fix: Summen-Plausibilitätscheck (97–103), Verwerfen ohne echtes Umfragedatum, History-Dedupe. Zusätzlich wurde das korrupte sentiment.json repariert (aaii auf letzten plausiblen Stand 2026-06-10 zurückgesetzt, Duplikate ab 17.06. entfernt).
2. **Workflow: FAST-Modus wurde nie gesetzt** — die stündlichen Crons machten 48×/Tag den vollen Scrape (PDFs, HTML-Scraping) statt des vorgesehenen Schnelllaufs. → Fix: `FAST=1` per Expression für Stunden-Crons und dispatch=schnell; Nachtlauf voll.

### Mittel (behoben)

3. **Staleness-Anzeige versagte bei fetch-Fehler** (index, krisen, kgv, zinsen): `DATA_UPDATED` blieb null → kein „veraltet"-Hinweis, genau wenn Daten am ältesten. → Init mit eingebettetem Fallback-Datum.
4. **Stille Fehlerpfade:** `.catch(() => {})` schluckte auch Render-Exceptions → halb gerenderte Seiten ohne Diagnose. → console.warn + try/catch um alle Render-Aufrufe.
5. **Fehlende Feld-Guards** (fearGreed.score, bonds.y30, aaii.asOf, vix.latest, fmt(undefined)-Pfade in verlierer) → TypeError bei lückenhaftem JSON. → Guards + defensives fmt().
6. **einflussfaktoren: fit() setzte bei jedem resize die Scrollposition zurück** (springt auf Mobile). → Scale-Vergleich + Debounce; zusätzlich rAF-Loop-Pause bei Neutralstellung (Akku).
7. **Pipeline:** kein atomares Schreiben (halbe JSONs konnten online landen), keine concurrency-Gruppe, update_data.py verwarf bei Teilfehler alle Fortschritte, Frische-Alarm prüfte nur data.json. → temp+os.replace, concurrency, try/except pro Updater, erweiterte Frische-Prüfung.
8. **refresh.php: leeres Secret = offener Trigger**; Secret unescaped im Shell-Heredoc. → 503-Guard; python3-basiertes PHP-Escaping im Workflow.

### Niedrig (behoben, Auswahl)

applyLang-Loops ohne L()-Fallback (alle Seiten) · index: Achsenjahr aus Systemzeit statt Datenstand · VIX-Marker widersprach Wortschwellen · kgv: CAPE-Skala clippte bei >48, fragile Float-Key-Übersetzungen (→ titleKey) · sentiment: AAII-Balken ohne Überlauf-Clamp, VIX-Doppelpunkt · krisen/zinsen: MA-Doppelzählungs-Randfälle · verlierer: Endlabel-Clipping · toter Code (SP.markers, GLANCE.ath, forwardPE, NAMES, heute-Key u. a.) · Scripts: fehlende Datums-zfill, updated-Stempel bei Null-Erfolg, pdfplumber ungepinnt · steuer/rechtliches: falsche noscript-Texte.

---

## Runde 2 — Befunde und Fixes

Alle Runde-1-Fixes bestanden den Regressions-Check (u. a. MA-Berechnungen konkret nachgerechnet, Escaping-Roundtrip getestet, aaiiUsable-Kaskade verifiziert). Rest- und Folgefehler:

### Mittel (behoben)

1. **verlierer: Chart-Endlabel ≠ Tabellenwert** (z. B. TTD −76,1 % vs. −69,8 %) — unterschiedliche Indexierungsbasis. → Kurvenbasis auf `ranking.first` umgestellt; Endpunkt/Label/Tooltip = Tabellen-pct (an allen 10 Symbolen verifiziert).
2. **kgv: `d.latest` ohne Typ-Guard** → stumm kaputtes SVG möglich. → Guard.
3. **update_data.py: neues Partial-Write-Risiko durch try/except pro Updater** (bonds halb mutiert). → Staged-Berechnung, Zuweisung erst nach Erfolg.
4. **Frische-Prüfung hatte tote Winkel:** `updated` wurde bei Teilerfolg gestempelt → AAII-/PDF-/Treasury-Staleness unerkannt (war real eingetreten). → per-Kennzahl-Checks (aaii.asOf 12 T, fearGreed.asOf 3 T, bonds 7 T, cape 45 T) + neues `sourcesUpdated`-Feld in valuations.json, das nur echte Kennzahl-Updates stempelt.

### Niedrig (behoben)

index: VIX-Invalid-Fall inkonsistent (Marker „Ruhig" vs. Wort „Panik") → beide degradieren neutral; vix.latest/rating-Guards · krisen/kgv/zinsen: fmt()-Zahlen-Guard vereinheitlicht · krisen liest jetzt extremes/markers/crises aus data.json (Pipeline-Updates ohne Deploy) · kgv: Gridlines wachsen mit dynamischer Skala; Quellendatum dynamisch aus asOf · sentiment: fg.score-Guard; VIX/S&P-Marker mit getrennten Endzeitpunkten · zinsen: MA-Linie kann nicht mehr über die Achse hinauslaufen · verlierer: Legenden-/Chartfilter identisch · Scripts: .tmp-Cleanup bei Exception, AAII-Dedupe verwirft keine legitime Woche mehr, kein leeres History-Datum.

---

## Verifikation

Alle 10 Seiten: JS-Syntax (node --check) OK · 4 Scripts: py_compile OK · 4 JSONs: valide · Workflow-YAML: valide · eingebettetes Prüf-Python im Workflow: ast.parse OK.

## Bewusst offen

- og:image ist SVG (Social-Crawler zeigen kein Bild) — braucht ein PNG-Asset.
- Concurrency-Randfall: ein wartender Nachtlauf kann theoretisch von einem dazwischenkommenden Trigger aus der Queue verdrängt werden (durch 7-Tage-Alarm abgefedert).
- Die Pipeline ist laut Datenstand (18.06.) seit ~2 Wochen nicht gelaufen — bitte GitHub-Action/Strato-Cron prüfen; die Seiten zeigen korrekt „veraltet".
