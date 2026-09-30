# GitHub-Abrufe reduzieren — zwei Strategien

Stand: 04.09.2026 · Grundlage: `.github/workflows/update-data.yml`, `strato-cron/refresh.php`, `scripts/update_*.py`, `OPTIMIERUNG.md`

## 1. Ist-Zustand (Baseline)

Jeder Aufruf der Website selbst macht **keinen** GitHub-Abruf mehr – die JSONs sind seit 09/2026 in die Seiten eingebettet, Strato liefert alles. Die GitHub-Abrufe entstehen ausschließlich durch die **Workflow-Läufe** in GitHub Actions. Jeder Lauf zieht das Repo, installiert Python und Node-Pakete (`npm ci`), fragt alle Datenquellen ab, baut die Seiten und lädt sie zweimal per SFTP zu Strato.

**Läufe pro Woche (nur Werktage, ohne manuelle Pushes):**

| Auslöser | Cron | Läufe/Tag | Läufe/Woche |
|---|---|---|---|
| FAST (Startseiten-Daten, kein Commit) | `17 */3 * * 1-5` | 8 | 40 |
| VOLL (alle Quellen, Commit, Frische-Prüfung) | `23 22 * * 1-5` | 1 | 5 |
| **Summe** | | **9** | **45** (≈ 195/Monat) |

Dazu kommen Push-Läufe bei jedem Commit von dir (Bot-Commits lösen nichts aus) und – **unbekannt** – die Aufrufe des Strato-Crons, der per `refresh.php` einen `workflow_dispatch` an die GitHub-API schickt. `OPTIMIERUNG.md` Punkt 4 („Strato-Cron anpassen oder abschalten") ist noch offen. Falls der Strato-Cron noch im alten Takt läuft, ist er vermutlich die größte Einzelquelle von Läufen; das bitte zuerst im Strato-Kundenmenü prüfen.

**Was ein Lauf kostet:**

| Kennzahl | FAST-Lauf | VOLL-Lauf |
|---|---|---|
| GitHub-Actions-Minuten (Schätzung) | ~2–3 min | ~3–5 min |
| GitHub-API/Registry-Zugriffe | Checkout, setup-python, `npm ci` (~30 Pakete), 2× SFTP-Action | dito + Commit/Push |
| Externe Datenabrufe | ~10 (FRED S&P, Treasury, multpl ×2, CNN F&G, CBOE VIX, AAII, Yahoo ×3) | ~22 (+ wöchentlich 4 iShares-PDFs, Siblis, 14 FRED-Reihen) |

**Wochenwerte:** ~45 Läufe · ~110–135 Actions-Minuten · ~510 externe Datenabrufe.

**Kernbefund:** Von den ~10 Quellen eines FAST-Laufs ändern sich zwischen zwei 3-Stunden-Läufen nur zwei überhaupt intraday (CNN Fear & Greed, Yahoo-ETF-Kurse). S&P-Schluss, Treasury-Renditen, VIX-Historie, multpl-KGVs ändern sich **einmal am Tag**, AAII **einmal pro Woche**. Sieben von acht FAST-Läufen holen also fast ausschließlich Daten, die sich seit dem letzten Lauf nicht geändert haben.

---

## 2. Strategie A — Takt-Reduktion (minimal-invasiv, nur YAML)

**Idee:** Der 3-Stunden-Takt wird durch genau einen FAST-Lauf am Morgen ersetzt. Der nächtliche VOLL-Lauf bleibt. Zwei Läufe pro Werktag decken den realen Änderungsrhythmus der Daten vollständig ab.

**Neuer Zeitplan:**

```yaml
on:
  schedule:
    # Morgens 07:17 Berlin: alle Quellen haben den US-Schluss vom Vortag
    # veröffentlicht (FRED, Treasury, CBOE). Kein Commit.
    - cron: "17 5 * * 1-5"
    # Börsentäglich nach US-Handelsschluss: voller Lauf + Commit (unverändert)
    - cron: "23 22 * * 1-5"
  push:
    branches: [ main ]
    paths-ignore:            # Doku-Commits lösen keinen Deploy mehr aus
      - "**.md"
      - "_to_delete/**"
      - ".gitattributes"
      - ".gitignore"
  workflow_dispatch: ...     # unverändert
```

Die FAST-Bedingung im `env`-Block auf den neuen Cron-String anpassen (`github.event.schedule == '17 5 * * 1-5'`). Sonst keine Codeänderung nötig.

**Zusätzlich im Morgen-Lauf einsparbar (optional, 2 Zeilen in `update_valuations.py`):** Um 07:17 Berlin sind die US-Börsen geschlossen, die Yahoo-Kurse sind identisch mit dem Nacht-Lauf – `yahoo_quote` kann bei `FAST=1` übersprungen werden (3 Abrufe weniger).

**Strato-Cron:** abschalten. Fallback bleibt der manuelle `workflow_dispatch` in GitHub. Wer einen Sicherheitsanker will: Strato-Cron 1×/Tag um 23:30 Berlin auf `mode=voll` – dann aber die Concurrency-Gruppe beachten, der Lauf wartet, statt zu doppeln.

**Ergebnis:**

| Kennzahl | vorher | nachher | Reduktion |
|---|---|---|---|
| Geplante Läufe/Woche | 45 | 10 | **−78 %** |
| Actions-Minuten/Woche | ~110–135 | ~25–40 | **−75 bis −78 %** |
| Externe Datenabrufe/Woche | ~510 | ~145 (mit Yahoo-Skip) / ~160 (ohne) | **−72 % / −69 %** |

**Was sich für Leser ändert:** Fear & Greed und die MSCI-ETF-Kurse auf der Startseite zeigen nicht mehr den Intraday-Stand, sondern den Stand vom Vorabend (22:23 UTC = 00:23 Berlin, also nach US-Schluss). Für deutsche Leser ist das der vollständige Vortag – die Datenseiten (kgv, zinsen, vix, krisen) zeigen ohnehin schon Tagesschlusswerte.

**Aufwand:** ~15 Minuten, ein Commit. Risiko: minimal, jederzeit rückgängig zu machen.

---

## 3. Strategie B — GitHub nur noch 1×/Tag, Intraday-Frische ohne GitHub

**Idee:** GitHub Actions wird auf das reduziert, wofür es unersetzlich ist: der nächtliche Voll-Lauf mit Python-Pipeline, Commit und Deploy. Alles, was intraday frisch sein soll, holt Strato selbst – ohne GitHub, ohne Build, ohne SFTP.

**Baustein 1 – Workflow:** Nur noch `23 22 * * 1-5` (VOLL). Der FAST-Modus bleibt nur für `workflow_dispatch` und Push-Deploys erhalten. `paths-ignore` wie in Strategie A. Strato-Cron-Trigger (`refresh.php`) wird nicht mehr gebraucht und entfällt – damit verschwindet auch das GitHub-Token vom Strato-Server (Sicherheitsgewinn).

**Baustein 2 – Intraday-Overlay auf Strato (`/live/live.json`):** Ein kleines PHP-Skript (`strato-cron/live.php`, ~60 Zeilen, nutzt dieselbe curl-Infrastruktur wie `refresh.php`) holt per Strato-Cron werktags alle 3 Stunden nur die beiden Quellen, die sich intraday ändern:

- CNN Fear & Greed (1 Abruf) → `fearGreed.score`, `.rating`, `.asOf`
- Yahoo-Quotes für die 3 MSCI-ETFs (3 Abrufe) → `price`, `change`, `asOf`

Ergebnis: eine ~1 KB große `live.json` mit Zeitstempel, direkt auf Strato geschrieben, Cache-Header 15 Minuten.

**Baustein 3 – Overlay in `site.js`:** `MC.load` bekommt eine Ergänzung: Nach dem Laden der eingebetteten Daten wird `live.json` geholt (ein zusätzlicher kleiner Request, nur auf Seiten, die Intraday-Werte zeigen: index, fear-greed, sentiment, kgv) und die vier Felder werden überschrieben, **wenn** der Zeitstempel jünger ist als der eingebettete Stand. Plausibilitätsgrenzen wie in Python (F&G 0–100, Kursabweichung < 15 %). Fehlt oder scheitert `live.json`, bleibt alles wie bisher – der Overlay ist rein additiv.

**Ergebnis:**

| Kennzahl | vorher | nachher | Reduktion |
|---|---|---|---|
| Geplante GitHub-Läufe/Woche | 45 | 5 | **−89 %** |
| Actions-Minuten/Woche | ~110–135 | ~15–25 | **−85 bis −88 %** |
| Externe Datenabrufe über GitHub/Woche | ~510 | ~110 | **−78 %** |
| Externe Datenabrufe gesamt (inkl. Strato-Overlay) | ~510 | ~270 | −47 % |
| GitHub-Token auf dem Strato-Server | ja | nein | entfällt |

**Variante B-light (ohne Overlay):** Nur Baustein 1. Dann −89 % Läufe und −78 % externe Abrufe, dafür kein Intraday-Stand mehr – identisches Leser-Erlebnis wie Strategie A, nur mit einem Lauf weniger pro Tag. Das ist die einfachste Variante überhaupt (Cron-Zeile löschen) und liegt trotzdem klar über dem 70-%-Ziel.

**Aufwand:** Baustein 1: 10 Minuten. Bausteine 2+3: ein halber Tag inkl. Test (PHP-Skript, Cron in Strato einrichten, `.htaccess`-Cache-Regel, JS-Merge, DE+EN prüfen). Risiko: gering, weil der Overlay ausfallsicher ist; Strato-PHP muss ausgehende HTTPS-Verbindungen zulassen (tut es – `refresh.php` nutzt bereits curl gegen api.github.com).

---

## 4. Gegenüberstellung

| | Strategie A | Strategie B | B-light |
|---|---|---|---|
| Läufe/Woche | 10 (−78 %) | 5 (−89 %) | 5 (−89 %) |
| Ziel ≥ 70 % erreicht | ja | ja | ja |
| Intraday-Werte (F&G, ETF-Kurse) | nein (Vortag) | ja, alle 3 h | nein (Vortag) |
| Änderungen | nur YAML | YAML + PHP + JS | nur YAML |
| Aufwand | 15 min | ~½ Tag | 5 min |
| Abhängigkeit vom Strato-Cron | keine | ja (für Intraday) | keine |
| GitHub-Token auf Strato | bleibt (falls Cron-Fallback) | entfällt | entfällt |

## 5. Umgesetzt am 04.09.2026: Variante C — ein Morgen-Lauf pro Handelstag

Nach Rücksprache umgesetzt (Leser sitzt in Deutschland, kein Strato-Cron gewünscht): **Ein einziger VOLL-Lauf um 05:17 UTC (06:17/07:17 Berlin), Dienstag bis Samstag.** Alle Quellen der Seite sind US-Daten; morgens liegt der komplett abgeschlossene US-Vortag vor (FRED, Treasury, CBOE, CNN, Yahoo veröffentlichen über Nacht). Samstag statt Montag, damit der Freitagsschluss geholt wird – montags gäbe es nichts Neues.

Änderungen in `.github/workflows/update-data.yml`:

- `schedule`: nur noch `17 5 * * 2-6`; die Crons `17 */3 * * 1-5` (FAST) und `23 22 * * 1-5` (VOLL) sind entfernt.
- `FAST` gilt nur noch für Push-Deploys und den manuellen `schnell`-Start; `VOLL` für jeden geplanten Lauf und den manuellen `voll`-Start.
- `paths-ignore` im Push-Trigger: Commits, die nur `*.md`, `_to_delete/`, `.gitattributes` oder `.gitignore` berühren, lösen keinen Lauf mehr aus.
- Kommentare angepasst; Frische-Prüfung, Commit-Schritt, Deploy unverändert.

| Kennzahl | vorher | nachher | Reduktion |
|---|---|---|---|
| Geplante Läufe/Woche | 45 | 5 | **−89 %** |
| Actions-Minuten/Woche | ~110–135 | ~15–25 | ~−85 % |
| Externe Datenabrufe/Woche | ~510 | ~110 | **−78 %** |

**Noch zu tun (außerhalb des Repos):** Strato-Cron für `refresh.php` deaktivieren – sonst löst er weiterhin zusätzliche Läufe aus. `refresh.php` bleibt als manueller Notfall-Trigger deploybar.

**Nach den ersten Läufen prüfen:** Im Lauf-Protokoll der Frische-Prüfung steht „Letztes Kursdatum: …". Das sollte jeweils der vorherige US-Handelstag sein. Zeigt es dauerhaft zwei Tage zurück, veröffentlicht FRED den Schlusskurs erst mit einem Tag Verzug – dann in `update_data.py` (`fetch_rows`) die Reihenfolge auf Yahoo → FRED → Stooq drehen oder den Cron auf z. B. `17 7 * * 2-6` schieben.

Die Schwellen der Frische-Prüfung passen zum neuen Takt: Der Dienstag-Lauf sieht Daten von Montag (1 Tag), nach einem US-Feiertag am Montag den Freitagsschluss (4 Tage, Schwelle 5).

## 6. Ursprüngliche Empfehlung (vor Rücksprache)

Sofort **B-light** umsetzen (eine Zeile löschen, Strato-Cron deaktivieren): −89 % ab dem nächsten Tag, kein Risiko. Falls dir die Intraday-Anzeige auf der Startseite wichtig ist, danach entweder den Morgen-Lauf aus Strategie A dazunehmen (dann −78 %) oder den Strato-Overlay aus Strategie B nachrüsten (bleibt bei −89 % auf GitHub-Seite).

In beiden Fällen unabhängig davon: den Strato-Cron prüfen und `paths-ignore` für Doku-Commits setzen – sonst löst jede Änderung an einer `.md`-Datei einen kompletten Lauf mit Deploy aus.

## 7. Kontrolle nach der Umstellung

Unter `https://github.com/PhilGerEsp/website/actions` sollte Dienstag bis Samstag genau ein Lauf pro Tag erscheinen (morgens), Sonntag und Montag keiner. In Settings → Billing → Actions lässt sich der Minutenverbrauch pro Monat gegen die Baseline (~500 min/Monat) vergleichen. Die Frische-Prüfung im VOLL-Lauf meldet weiterhin per Mail, wenn eine Quelle ausfällt – daran ändert keine der Strategien etwas.

## 8. Umgestellt am 23.09.2026: höchstens ein Abruf pro Tag, um 10:00 Uhr

**Befund:** GitHubs Zeitplan ist unpünktlich. Der auf 07:17 Berlin gestellte Lauf startete laut `updatedAt` der JSONs vom 09. bis 23.09. täglich erst zwischen 11:28 und 12:12 Uhr (4–5 Stunden zu spät). Außerdem hat jeder Push erneut Daten geholt (FAST-Lauf) – am 23.09. sechs zusätzliche Abrufrunden, eine davon während des US-Handels (18:11 Uhr): Sie veröffentlichte einen Intraday-Kurs als „Schlusskurs 23.09.“.

**Neue Regeln (`.github/workflows/update-data.yml`):**

- **10-Uhr-Lauf:** Ein externer Cron ruft um 10:00 `https://www.bondarium.de/trigger/refresh.php?mode=voll` auf und sendet den Schlüssel im Kopf `X-Trigger-Key` (seit 30.09.2026 nicht mehr in der Adresse – Adressen stehen im Server-Log; `?key=…` wird nicht mehr angenommen); `refresh.php` startet den Workflow per `workflow_dispatch` (beginnt binnen Sekunden).
- **Reserve:** GitHub-Zeitplan `15 10 * * 2-6` mit `timezone: "Europe/Berlin"` (Sommer-/Winterzeit automatisch). Er ruft nur ab, wenn heute noch nichts abgefragt wurde.
- **Tagessperre:** Job `sperre` liest `data.json` von `main` (per `gh api`, kein Checkout) und vergleicht `updatedAt` (in Berliner Zeit) mit heute. Schon abgefragt → der Lauf endet ohne Abruf und ohne Deploy. Übergehen nur manuell mit dem Häkchen `erzwingen`.
- **Push-Deploys und `schnell`:** kein einziger Datenabruf mehr, nur Veröffentlichen des Repo-Stands. Der Checkout nutzt `ref: main`, damit ein Push, der auf den 10-Uhr-Lauf warten musste, dessen frische JSONs veröffentlicht.
- **Tage:** Dienstag bis Samstag (US-Vortag komplett; Samstag holt den Freitagsschluss).
- **Anleihen-Suche** (`scripts/update_anleihen_index.py`, ab 23.09.2026): läuft im Abruf-Lauf mit, fragt aber erst, wenn `anleihen-index.json` 7 Tage alt ist, und baut nur bei neuer ESMA-Gesamtdatei neu – praktisch samstags, ~2 Minuten.
- `scripts/update_data.py`: `fetch_rows` lässt den laufenden US-Handelstag weg (vor 16:30 New York kein Schlusskurs) – Schutz für späte Reserve- oder manuelle Läufe.

**Einrichtung (einmalig, außerhalb des Repos):**

1. GitHub → Settings → Secrets and variables → Actions: `TRIGGER_KEY` (langer Zufallswert) und `GH_DISPATCH_TOKEN` (Fine-grained Token, nur dieses Repo, Berechtigung „Actions: Read and write“, Ablaufdatum notieren) anlegen. Stand 23.09.2026 antwortet `refresh.php` mit „not configured“ – die Secrets fehlen.
2. Einmal pushen, damit der Deploy `trigger/refresh-config.php` schreibt.
3. cron-job.org (kostenlos): Cronjob mit der URL `https://www.bondarium.de/trigger/refresh.php?mode=voll`, 10:00 Uhr, Montag–Freitag (seit 30.09.2026), Zeitzone Europe/Berlin, Benachrichtigung bei Fehlern. Unter „Erweitert“ die Kopfzeile `X-Trigger-Key` mit dem Wert von `TRIGGER_KEY` eintragen – der Schlüssel gehört nicht in die Adresse.
4. Test: in cron-job.org „Testlauf“ → Antwort „OK – Workflow ausgelöst (Modus: voll)“. Wegen der Tagessperre entsteht am selben Tag kein zweiter Abruf.

Der Strato-Cron eignet sich nicht als pünktlicher Auslöser: Laut Strato-FAQ ist er ein Best-Effort-Dienst mit Verzögerungen bis zu 4 Stunden und auf der neuen Strato-Plattform nicht verfügbar.

| Kennzahl | vorher (09/2026) | nachher |
|---|---|---|
| Datenabrufe pro Tag | 1 geplanter + 1 je Push | höchstens 1 |
| Uhrzeit | nominal 07:17, real 11:30–12:15 | 10:00 (Reserve 10:15 + GitHub-Verzug) |
| Push-Lauf | Abruf (~10 Quellen) + Deploy | nur Deploy |

## 9. Seit 23.09.2026 nur noch Anleihen

Der Aktien-Teil (Börse heute, Börsenhistorie, Marktsentiment, Markteinflüsse, Aktien, Gewichtung, Steuern) liegt jetzt in `../website_aktien_archiv/` (Anleitung zum Reaktivieren dort in der `README.md`). Der Abruf-Lauf fragt deshalb nur noch die Anleihen-Quellen ab:

- entfallen: `update_data.py`, `update_sentiment.py`, `update_valuations.py` (samt `pip install pdfplumber`), `update_einfluss.py`; `update_verlierer.py` war schon abgeschaltet.
- bleiben: `update_renditen.py`, `update_unternehmen.py`, `update_langlaeufer.py`, `update_bundkurse.py`, `update_anleihen_index.py` (1×/Woche).
- **Tagessperre** liest jetzt `renditen.json → checkedAt` (setzt jeder Abruf, auch ohne Wertänderung) statt `data.json → updatedAt`.
- **Frische-Prüfung:** Renditen je Land, `anleihen-index.json → stand` (16 Tage) und `anleihen-kurse.json → stand` (7 Tage).
- **Strato:** Der Deploy löscht keine Dateien. Die alten Seiten bleiben auf dem Server liegen, werden aber per `.htaccess` dauerhaft umgeleitet (301 auf die Startseite, `zinsen.html` auf `renditen.html`, Gewichtung/Steuern auf `wissen.html`); die alten Daten-JSONs antworten mit 410 „Gone“. Wer aufräumen will, löscht sie per SFTP.
- Ein Abruf-Lauf ist damit kürzer: keine Abrufe mehr bei CNN, CBOE, AAII, Yahoo, multpl, iShares, Siblis und Yardeni.
