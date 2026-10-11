# Prüfbericht Website

Geprüft am 16.06.2026. Umfang: 9 HTML-Seiten, 4 Python-Skripte, 4 JSON-Dateien, GitHub-Actions-Workflow & Strato-Deployment. **Es wurden keine Dateien geändert** – dies ist nur ein Befundbericht.

## Gesamteinschätzung

Die Codebasis ist überdurchschnittlich solide: JS-Feldnamen passen sauber zu den JSON-Strukturen, alle internen Links lösen auf, alle JSON-Dateien sind valide, die Python-Pipeline ist defensiv geschrieben (Plausibilitätsbänder, Fallback-Quellen, Timeouts, keine Secrets im Code, TLS-Prüfung aktiv). Es gibt keine akuten Totalausfälle. Die wichtigsten Schwachstellen liegen in zwei Bereichen: möglicher stiller Datenverlust in der Datenpipeline und durchgängig fehlende SEO-/Social-Meta-Tags.

Die folgenden Befunde sind nach Schweregrad sortiert. Verifizierte Befunde sind mit ✓ markiert.

---

## Kritisch

**K1 — Stiller Datenverlust: Monatsreihe wird überschrieben statt fortgeschrieben** (`scripts/update_data.py`, Z. 192–217 S&P, 168–180 Anleihen)
`update_sp500` baut `data["monthly"]` ausschließlich aus den frisch geholten Zeilen neu auf. Liefert die Quelle (FRED) eine kürzere Reihe, gehen bereits gespeicherte Monatsschlusskurse still verloren – es gibt kein Merge mit dem bestehenden Bestand. Gleiches Muster bei `bonds["monthly"]`.
*Fix:* bestehende Monatswerte laden, per `date[:7]` aktualisieren statt ersetzen, dann sortieren.

**K2 — Irreführender Aktualitäts-Zeitstempel bei Teilausfall** ✓ (`scripts/update_data.py`, Z. 296–311)
`main()` schreibt data.json, sobald *irgendeine* Teilquelle erfolgreich war, und setzt `updated`/`updatedAt` (Z. 306–307) unbedingt auf heute. Wenn z. B. nur das CAPE-Update klappt, die Kurse aber veraltet sind, zeigt die Website trotzdem „frisch aktualisiert". Für S&P/Anleihen gibt es keinen eigenen Zeitstempel, mit dem die Frische-Prüfung das erkennen könnte.
*Fix:* globales `updated` nur setzen, wenn die Kerndaten (S&P/Anleihen) erfolgreich waren; pro Sektion einen `asOf`-Zeitstempel führen.

---

## Mittel

**M1 — Doppelter Datumseintrag in der Fear-&-Greed-Historie** ✓ (`sentiment.json` → `fearGreed.history`)
Verifiziert: `2026-06-16` ist zweimal hintereinander enthalten (`[..., ['2026-06-16',41.3], ['2026-06-16',41.3]]`). Erzeugt im Verlaufschart einen Punkt mit X-Abstand 0 (überlappende Marker). Ursache liegt im Generierungs-Skript, das den letzten Tag doppelt anhängt.
*Fix:* beim Append deduplizieren (letzten Eintrag prüfen, bevor angehängt wird).

**M2 — `verlierer.html` fehlt in der Hauptnavigation** ✓ (alle 9 Seiten)
Verifiziert: Die Seite ist nur über den schwebenden „Aktien"-Button (`fab-aktien`) erreichbar, in keiner `.sitenav` verlinkt. Nutzer ohne sichtbaren FAB und Screenreader-Nutzer finden sie über die normale Navigation nicht.
*Fix:* `verlierer.html` als regulären Nav-Eintrag aufnehmen.

**M3 — Anleihen-Update bricht bei einer Jahres-Lücke komplett ab** (`scripts/update_data.py`, Z. 143–148)
Ein einziger fehlgeschlagener Jahres-Abruf führt zu `return False` für die gesamte Anleihen-Aktualisierung – auch wenn das laufende Jahr verfügbar wäre. Temporärer Treasury-Ausfall für ein altes Jahr legt damit auch aktuelle Renditen lahm.
*Fix:* pro Jahr fehlertolerant sammeln (`continue` statt `return`), nur abbrechen wenn das laufende Jahr fehlt.

**M4 — Brüchige Scraping-Selektoren, v. a. Wikipedia** (`update_verlierer.py` Z. 74–78, `update_sentiment.py` Z. 128, `update_data.py` Z. 266, `update_valuations.py` Z. 75/90/143)
Mehrere Werte hängen an sehr spezifischen Regex über Roh-HTML/PDF. Größter realer Bruchpunkt: das Wikipedia-Constituents-Regex erwartet exakt `<td><a href="https://www.(nyse|nasdaq|cboe).com/...">SYM</a>`. Jede Tabellenänderung lässt `len(out) < 400` greifen → Skript-Abbruch. AAII-Bull/Bear-Werte haben keinen Fallback (nur `neutral`). Yardeni nutzt eine `archive.yardeni.com`-URL (Archiv-Pfade verschwinden erfahrungsgemäß).
*Fix:* HTML-Parser statt Regex; Symbol-Spalte unabhängig von der Börsen-Domain matchen; Schema-/Sanity-Logging pro Quelle.

**M5 — Keine Plausibilitätsprüfung gegen den Vorwert** (alle Skripte)
Einzelwerte werden gegen feste Bänder geprüft (gut), aber ein Sprung von CAPE 42 → 8 würde unkritisch übernommen, solange im 3–100-Band.
*Fix:* zusätzlich relative Abweichung zum letzten gespeicherten Wert prüfen (z. B. > X % → verwerfen/loggen).

**M6 — SEO: durchgängig fehlende canonical-/OG-/Structured-Data-Tags** (alle 9 Seiten)
Auf allen Seiten fehlen `<link rel="canonical">`, Open-Graph-Tags (`og:title/description/image/url`), `twitter:card`, `robots` und JSON-LD. Für eine börsentäglich aktualisierte Daten-Website wären mindestens canonical + OG-Block + ein `Dataset`-Schema wertvoll (bessere Vorschau beim Teilen, sauberere Indexierung).
*Fix:* pro Seite OG-Block + canonical ergänzen, ein Vorschaubild bereitstellen.

**M7 — Code-Duplizierung über alle Seiten** ✓ (alle 9 HTML-Dateien)
Style-Grundgerüst, Inline-Brand-SVG-Logo, Navigationsliste, Footer und die i18n-Maschinerie sind in jede Datei einkopiert. Jede Änderung muss neunfach gepflegt werden – genau das hat zu M2 geführt (Nav-Eintrag in einer Datei vergessen). Verifiziert: `logo.svg` und `logo-icon.svg` liegen im Ordner, werden aber in **keiner** HTML referenziert.
*Fix:* gemeinsames externes `style.css` + `nav.js`/`i18n.js` auslagern; Logo per `<use>`/`<img>` aus `logo-icon.svg` ziehen statt inline zu duplizieren.

**M8 — Accessibility: Sprach-Buttons & Chart-SVGs ohne ARIA** (alle Seiten)
Die `.langswitch`-Buttons haben kein `aria-pressed`/`aria-label` – die aktive Sprache wird nur per CSS-Klasse vermittelt, Screenreader erkennen sie nicht. Nicht alle per JS erzeugten Chart-`<svg>` erhalten ein `role="img"`+`aria-label` (kgv/scatter teils ja, `#vix-chart`, `#fg-history`, `#chart` in verlierer prüfen).
*Fix:* `aria-pressed` an Sprach-Buttons toggeln; jedem generierten Chart-SVG ein `aria-label` geben.

---

## Niedrig

**N1 — Code-Duplizierung in der Python-Pipeline** (`scripts/`)
Drei verschiedene `_get`/`_fetch_csv`-Implementierungen mit eigenen Headers/Retries/Timeouts; Yahoo-Chart-Parsing und Monats-Aggregation in mehreren Skripten nahezu identisch dupliziert.
*Fix:* gemeinsames `_common.py` mit `_get`-Helfer (Retry/Backoff), Yahoo-Parser und Monats-Aggregation.

**N2 — `update_data.py` ohne Retries** (Z. 41, 114)
Anders als sentiment (3 Versuche) und verlierer (2 Versuche) hat data.py keine Retries – ein transienter FRED-Fehler führt sofort zum Ausfall. Timeout (30 s) ist gesetzt.

**N3 — Encoding-Annahme in `_fetch_csv`** (`update_data.py`, Z. 37–42)
Dekodiert hart als `utf-8` ohne `errors=`-Strategie, inkonsistent zu den anderen Skripten (`decode("utf-8","replace")`). Bei einer Latin-1-/HTML-Fehlerseite verschleiert das die Ursache.

**N4 — Große Inline-Daten + Doppel-Laden** (`sentiment.html` 81 KB, `verlierer.html` 71 KB, `kgv.html` 64 KB)
Umfangreiche eingebettete Datenarrays (VIX-Reihe seit 1990, komplette Kursserien) werden als Fallback mitgeliefert UND danach erneut per fetch geladen → doppelte Payload, blockiert das Parsen.
*Fix:* Inline-Fallback auf das Nötigste reduzieren.

**N5 — Veraltete eingebettete Fallback-Werte** (alle Seiten)
Hartkodierte Fallbacks (z. B. `index.html` `sp.close 7394.30`) driften gegenüber `data.json` (aktuell 7554.29). Nur sichtbar wenn der fetch scheitert, aber driftet mit der Zeit.

**N6 — Hartcodierte Mittelwerte/Defaults veralten** (`update_sentiment.py` Z. 160, `update_valuations.py` Z. 158–163)
AAII-Langfristmittel (37.5/31.5/31.0) und Valuations-Defaults (forwardPE 19.7, sp500.pe 25.88, EU/EM-CAPE manuell) sind `setdefault`-Fallbacks, die bei längerem Update-Ausfall veralten.

**N7 — Kein `<noscript>`-Fallback** (alle Seiten)
Bei deaktiviertem JS bleiben Charts und i18n-Text leer, ohne Hinweis.

**N8 — Kontrast kleiner Texte** (`--muted` #6B6A64 auf #FBFAF7)
Verhältnis ~4.9:1 – AA-konform für Normaltext, aber grenzwertig für 10-px-Texte (`.stat .stand`, `.chart-x`).

**N9 — `verlierer`-Cutoff quellenabhängig** (`update_verlierer.py` Z. 54–55)
`CUTOFF_FIRST = FROM + 50 Tage` filtert über das Anfangsdatum; Yahoo (Monats-) und Nasdaq (Tageswerte) können um Tage abweichen → dasselbe Papier je nach Quelle ein-/ausgeschlossen.
*Fix:* auf Mindestanzahl Monatspunkte prüfen statt auf das Anfangsdatum.

**N10 — Kleinere Inkonsistenzen**
`kgv.html` Z. 638 überschreibt den Spaltenkopf „Heute" mit dem Jahr (z. B. „2026"). `sentiment.html` nutzt eine abweichende i18n-Hilfsfunktion (`tt()`) gegenüber den anderen Seiten. Doppelte `@media (max-width:600px)`-Blöcke in mehreren Dateien. `rechtliches.html` nur im Footer, nicht in `.sitenav` (vertretbar).

---

## Was in Ordnung ist

- Alle JSON-Dateien valide; JS-Feldnamen passen zu den JSON-Strukturen.
- Alle internen Links und TOC-Anker lösen auf; keine kaputten `href`.
- Externe Quell-Links (CNN, AAII, FRED, Treasury, Wikipedia, multpl) korrekt.
- Genau ein `<h1>` pro Seite, saubere Heading-Hierarchie, `lang="de"` gesetzt.
- Python: TLS-Prüfung aktiv, keine Secrets im Code, kein `eval`/`pickle`/Shell, Timeouts überall gesetzt, Plausibilitätsbänder vorhanden, „behalte letzten Stand"-Muster bei Quell-Ausfall.
- Der `FAST`-Modus (schneller Lauf) ist sauber umgesetzt.
- GitHub-Workflow (nach Action-Update auf v5/v6) ohne Befund.

## Empfohlene Reihenfolge

1. **K1 + K2** – Datenpipeline absichern (Merge statt Überschreiben, Zeitstempel nur bei Erfolg).
2. **M2 + M7** – `verlierer.html` in die Nav, dann Nav/Styles/Logo/i18n in gemeinsame externe Dateien auslagern (behebt die Duplizierungs-Fehlerquelle dauerhaft).
3. **M1** – Doppel-Datum im Sentiment-Skript fixen.
4. **M6 + M8** – canonical/OG-Tags und ARIA an Sprach-Buttons/Charts ergänzen.
5. **M3–M5, N*** – Robustheit & Aufräumen nach Bedarf.
