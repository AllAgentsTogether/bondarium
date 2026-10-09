# Auffindbarkeit: Suchmaschinen und KI-Dienste

Stand 02.10.2026. Was die Seite für Google, Bing und KI-Dienste (ChatGPT, Claude, Perplexity, Gemini) tut, wo es
im Code steht und was beim Anlegen einer neuen Seite zu beachten ist.

## Grundsatz

KI-Crawler führen kein JavaScript aus und lesen nur das ausgelieferte HTML. Google führt es aus, Bing nur
unzuverlässig. Deshalb gilt: Was gefunden werden soll, steht im HTML – als Text, als Tabelle, als strukturierte
Daten. Alles Folgende entsteht beim Deploy im Ordner `_site`; die Quell-HTML im Repository bleiben unverändert.

## Was beim Deploy passiert

Reihenfolge im Workflow `update-data.yml` (alles auf `_site`):

| Schritt | Skript | Ergebnis |
| --- | --- | --- |
| Kennzahlen | `scripts/kennzahlen.py` | Zahlen im Text (`data-kz`: Anzahl Anleihen, Renditespannen, ETF- und Broker-Zahlen) und die Zeile „Daten-Stand“ der Anleihen-Suche (Register- und Kursstand aus `suchindex.json`). |
| Tabellen fest ins HTML | `scripts/statische_tabellen.py` | Die 18 Broker (`broker.json`: Liste „Kosten und Angebot“ für 5.000 € mit Rechenweg, Quellen je Anbieter, „Geprüft am“ – dieselbe Rechnung wie im Seitenskript), die 70 ETFs (`top10-anleihen-etfs.json`, dazu die ETF-Zahl je Kachel und „Daten-Stand“), die Top 30 nach Kupon (drei Tabellen und „Daten-Stand“ mit Kurs- und EZB-Liste-Datum), die vier Top-10-Seiten (Handauswahl der Seite mit Kurs und Rendite aus `kurse-auswahl.json`, solange die Rangliste nicht `aktiv` ist; Länder-Seiten: Deutschland) und auf der Startseite die sechs Beispiele mit „Kurse und Renditen vom“. Im Browser ersetzt das Seitenskript sie durch seine eigene Fassung. |
| Rückfallwerte | `scripts/rueckfallwerte.py` | Kacheln, Tabellen, Textzahlen und „Daten-Stand“ von renditen, unternehmensanleihen, zinskurve, realzins, risikoaufschlaege und langlaeufer aus den Daten-JSONs – gleiche Rechnung, Rundung und Schreibweise wie das Seitenskript. Die Zeilen des Seitenskripts, die nachgebaut sind, stehen als `ANKER` im Skript; fehlt eine, bleibt die Seite unverändert (Warnung). |
| Strukturierte Daten, Sitemap | `scripts/seo.py` | Ein JSON-LD-Block je Seite (`@graph`): Organisation und Website mit fester Kennung, je Seite ein WebPage-Knoten mit Brotkrumen, Artikel als Hauptinhalt mit Autor, Bild und erwähnten Glossar-Begriffen (`mentions`), Glossar als `DefinedTermSet` (mit `alternateName` und geprüften Wikidata-Kennungen), Rechner als `WebApplication`, sechs Zeitreihen als `Dataset` mit ihren Quellen (`isBasedOn`). Robots-Angabe mit `max-image-preview:large`. `article:modified_time`. `sitemap.xml` aus den Seiten. |
| llms.txt, llms-full.txt | `scripts/llms.py` | Kurzfassung (je Seite eine Zeile aus Titel und Beschreibung, gruppiert nach Brotkrumen, „Über Bondarium“ direkt nach „Start“) und Volltext aller Seiten als Markdown mit den aktuellen Zahlen aus den Daten-JSONs, je Seite „Seite geändert: …“ (dateModified). Rückfallwerte, deren sichtbarer Stand älter ist als die Daten, ersetzt dort ein Verweis (Warnung im Protokoll). |
| Themen für die Suche | `scripts/themen.py` | `themen.json` (seit 03.10.2026): Lernseiten und Glossarbegriffe für „Passende Themen“ in der Anleihen-Suche – aus Menü, Titel, H1/H2, Beschreibung und `begriffe.html`. |
| Steckbriefe vom Server | `scripts/steckbriefe.py` | Seit 03.10.2026 (Stufe 1, Entscheidung 02.10.2026): je Bundeswertpapier (`kurse/bund/`, 79) eine fertige Seite `steckbrief/<ISIN>.html` aus der Vorlage `anleihe.html` – Titel mit Art und ISIN, Beschreibung, kanonische Adresse `anleihe.html?isin=<ISIN>`, „index“, Überschrift, Registername, ISIN/WKN, Stammdaten ohne JavaScript (Zinstermin aus der Fälligkeit, keine Börsendaten), JSON-LD (WebPage, Brotkrumen, FinancialProduct, dazu Website und Organisation aus `seo.py`). Daten-Stand („Stammdaten TT.MM.JJJJ“), `dateModified` und `<lastmod>` = Stand der Stammdaten `anleihen/*.json` (seit 09.10.2026). Die `.htaccess` liefert sie unter `anleihe.html?isin=<ISIN>` aus (Regel an der Marke `@@STECKBRIEFE@@`, die allein auf ihrer Zeile steht), direkte Abrufe von `steckbrief/…` leiten in einem Sprung dorthin um (feste Regel vor dem HTTPS-Block, auch über http, ohne www und .com); 79 Einträge in der Sitemap, Meldung an IndexNow. Läuft nach den Versions-URLs, vor dem Minifizieren. Alle übrigen Steckbriefe: `noindex, follow` in `anleihe.html`. Scheitert der Schritt oder kommt nach dem Upload kein Server-Steckbrief zurück (Nach-Deploy-Prüfung), wird der Lauf rot. |
| Daten einbetten | `scripts/inline_data.py` | Die Daten-JSONs einer Seite als `<script type="application/json">` in die Seite. |
| CSS verkleinern | `scripts/css_klein.py` | Kommentare und Leerraum aus `base.css` und `bildwelt2.css`; vergleicht danach Regeln und Deklarationen mit dem Original, bei Abweichung bleibt die Datei unverändert. Läuft vor den Versions-URLs. |
| Versions-URLs | Workflow | Jede Einbindung von CSS und JS (und die beiden Such-Indizes) bekommt `?v=<Hash>` aus dem Inhalt. Setzt seit 02.10.2026 kein Datum mehr. |
| Prüfung | `scripts/pruefen.py` | Stoppt den Deploy bei toten internen Links, fehlendem Titel, fehlender oder fremder kanonischer Adresse, unlesbarem JSON-LD, seit 09.10.2026 auch bei Verweisen auf fehlende Skripte, Stylesheets und Bilder und bei unlesbaren `*.json` im Bau. Prüft seit 09.10.2026 auch die Server-Steckbriefe (unter ihrer Adresse `anleihe.html?isin=<ISIN>`, Warnungen als Sammelzeilen „Server-Steckbriefe: …“); Bereiche mit `hidden` zählen nicht als sichtbarer Text. Warnt (je Regel eine Sammelzeile) u. a. bei Titel über 60 bzw. 580 px, Beschreibung außerhalb 70–160 Zeichen bzw. über 990 px, Ladetext ohne JavaScript, Zusage- und Empfehlungswörtern, Hauswortschatz, Brotkrumen, `@id`-Verweisen ohne Knoten, Sitemap-`lastmod` jünger als `dateModified`, sichtbarem „Daten-Stand“ mehr als 7 Tage älter oder neuer als `dateModified`. |
| .htaccess prüfen | `scripts/htaccess_test.sh` | Startet im Runner einen Apache nur auf 127.0.0.1 mit `_site` als Docroot und fragt die wichtigsten Adressen ab (Status, Weiterleitung in genau einem Sprung, 410, Sperren, Ausnahmen der Zweitdomain). Ein harter Fehler stoppt den Lauf vor dem Upload; Cache-Köpfe und 304 nur Warnung; lässt sich Apache nicht starten, nur Warnung. |
| Meldung an Bing | `scripts/indexnow.py` | Nach dem Upload gehen neue Adressen und Adressen mit geändertem `<lastmod>` an IndexNow (Bing, Yandex, Seznam, Naver) – seit 09.10.2026 Vergleich der alten `sitemap.xml` vom Server mit der neuen, vorher jede HTML-Datei mit neuem Inhalt (täglich ~97 Steckbriefe). Schlüssel: `indexnow-key.txt`. |

Tabellen, Rückfallwerte, strukturierte Daten, llms-Dateien und CSS verkleinern sind Zugaben (`continue-on-error`):
Scheitert einer, geht die Seite ohne ihn live. Alle schreiben Zahlen und „Daten-Stand“ nur gemeinsam – passt etwas
nicht, bleibt die Seite im Zustand der Quell-HTML.

### Datum der Seiten (`dateModified`, `<lastmod>`, `article:modified_time`)

- Seiten ohne Daten: das `dateModified` aus der Quelle. Bei Textänderungen dort von Hand nachziehen.
- Datenseiten (`DATENSTAND` in `scripts/seo.py`): das jüngere von Quelldatum und dem Stand, den die gebaute Seite
  sichtbar nennt – jüngstes Datum in `<p id="datastand">`, auf der Startseite `#itab-stand`, im Broker-Vergleich
  `<span data-bv="stand">`. Hat ein Skript die Rückfallwerte nicht erneuert, zeigt die Seite den alten Stand, und es
  bleibt beim Quelldatum (Warnung). So meldet die Sitemap nie einen Stand, den das HTML ohne JavaScript nicht zeigt,
  und der sichtbare Stand ist nie neuer als `dateModified`.
- Neue Datenseite: in `DATENSTAND` eintragen (Seite → Daten-JSONs für die Gegenprobe) und den Stand in einer dieser
  Stellen zeigen. Fehlt der Eintrag, meldet `pruefen.py` „Sichtbarer Daten-Stand neuer als dateModified“.
- `Dataset.dateModified` ist der Datenstand der Zeitreihe (Ende von `temporalCoverage`), nicht das Seitendatum. Nennt eine
  Daten-JSON unter `stand` auch Reihen, die nicht zum Datensatz gehören, zählen nur die Schlüssel aus `STAND_NUR`
  (`realzins.html`: `zins` und `vpi`, nicht `linker`).
- Hat eine Seite der Sitemap gar kein `dateModified`, warnt `seo.py`; `<lastmod>` bleibt dann beim bisherigen Eintrag.
- `updated` in den JSONs (Lauf-Datum des Datenbots) zählt nirgends – sonst hätte jede Seite jeden Tag ein neues Datum.

### Pflege in `scripts/seo.py`

- `QUELLEN`: genau die Quellen aus dem sichtbaren Abschnitt „Datenquellen“ einer Datenseite. `beleg` muss dort
  wörtlich stehen, sonst fällt die Quelle mit Warnung weg. Datenreihen als `Dataset`, Emittenten und Angaben zu
  Anleihen (Bedingungen, Stammdaten) als `CreativeWork` (`"art"`). Neue oder entfernte Quelle auf der Seite → hier
  im selben Commit nachziehen.
- `KEIN_SYNONYM`: Klammerzusätze von Glossar-Stichwörtern, die KEIN anderer Name für denselben Begriff sind
  (Unterarten, Erläuterungen). Neues Stichwort mit Klammer → prüfen, ob es hierher gehört.
- `WIKIDATA`: nur von Hand geprüfte Kennungen; im Zweifel keine.
- `ORGANISATION`: Angaben wie im Impressum; das Skript warnt, wenn sie dort nicht mehr stehen.

## Server (`.htaccess`, `robots.txt`)

- `bondarium.com` und `www.bondarium.com` leiten dauerhaft auf `www.bondarium.de` um (vorher: gleicher Inhalt
  unter zwei Adressen). Ausgenommen `/trigger/` und `/.well-known/`.
- Frühere Adressen (index.html, /en/…, alte Laufzeit-Seiten, entscheiden/vertiefen …) leiten in genau EINEM Sprung
  auf die absolute Zieladresse `https://www.bondarium.de/…`. Neue Umleitungen in denselben Block vor dem HTTPS-Block
  und in die Prüfliste von `scripts/htaccess_test.sh`.
- Frühere Aktien-Seiten antworten mit **410** („gibt es nicht mehr“) statt einer Weiterleitung auf die Startseite
  (Soft-404). `ErrorDocument 410 /404.html` zeigt dabei die eigene Fehlerseite; die 410-Regeln stehen bewusst nach
  dem HTTPS-/Host-Block.
- Cache: HTML `no-cache` (immer nachfragen), Daten-JSONs 15 Minuten, Such-Indizes 30 Tage (nur mit Versions-URL),
  **CSS und JS ein Jahr `immutable`** – jede Einbindung braucht deshalb `?v=<Hash>` (setzt der Deploy für `<script
  src>` und `<link href>`; wer CSS oder JS anders nachlädt, muss die Versions-URL selbst mitgeben). Schriften
  (`*.woff2`) ein Jahr ohne Versions-URL: eine geänderte Schrift bekommt einen **neuen Dateinamen**. Bilder,
  `robots.txt`, Sitemap einen Tag.
- Revalidierung: `RequestHeader edit "If-None-Match"` gleicht das „-gzip“-ETag von mod_deflate aus, damit
  unveränderte Dateien mit 304 antworten.
- Lokal prüfen: `bash scripts/htaccess_test.sh <Bau-Ordner>` (macOS-Apache genügt). Die Ausnahmen `/trigger/` und
  `/.well-known/` prüft das Skript nur, wenn beide Dateien im Bau liegen (siehe „Lokal prüfen“).
- JSON-Dateien und die beiden llms-Dateien tragen `X-Robots-Tag: noindex`: abrufbar, aber kein eigener Suchtreffer.
- `robots.txt` nennt die KI-Crawler ausdrücklich (GPTBot, OAI-SearchBot, ChatGPT-User, ClaudeBot, Claude-SearchBot,
  Claude-User, PerplexityBot, Google-Extended und weitere). Es gelten dieselben Regeln wie für alle: alles erlaubt,
  außer `/trigger/`. Wer KI-Training nicht mehr zulassen will, setzt dort `Disallow: /` für GPTBot, ClaudeBot,
  Google-Extended, Applebot-Extended, Meta-ExternalAgent und CCBot – die Such-Crawler (OAI-SearchBot,
  Claude-SearchBot, PerplexityBot) bleiben dann erlaubt.

## Sichtbare Texte für Suche und KI-Antworten (seit 04.10.2026, SEO-Runde 2)

- **Seitentitel nach dem Muster „Seitenname: Suchzusatz“**, das Suchwort vorn, höchstens 60 Zeichen und 580 px samt
  „ – Bondarium“. Am 04.10.2026 geändert (Freigabe 02.10.2026): kaufen, erste-anleihe, anlegerprofile, zinsniveau,
  anleihen-kupon, anleihen, rechtliches („und“ statt „&“), wissen, beobachten, laufzeit, rendite-lesen, anleihen-etf.
  Der Titel steht dreimal im Kopf (title, og:title, twitter:title); die `headline` im JSON-LD darf die H1 sein.
- **Vier neue Seiten** (Entscheidung 02.10.2026, live 04.10.2026): bundeswertpapiere, anleihe-festgeld-tagesgeld,
  anleihe-nicht-kaufbar, zahlungsausfall – je mit Antwortsatz, Stand, datePublished, Quellen-Aufklapper (docs/SEITEN.md).
- **Antwortsatz**: Der erste Satz der Einleitung unter der H1 (`<p class="sub">`) beantwortet die Hauptfrage der Seite in
  einem Satz – das, was Suchmaschinen und KI-Dienste als Antwort zitieren. Gesetzt auf grundlagen, rendite-lesen, bonitaet,
  zinsniveau, anleihen-etf-erklaert, steuern-handelskosten, laufzeit, risiko (duration hatte ihn schon); neue Themenseiten
  bekommen ihn von Anfang an. Nur Aussagen, die die Seite selbst belegt.
- **Stand sichtbar**: hinter der Lesezeit `· <span class="stand-t">Stand: TT.MM.JJJJ</span>`. `seo.py` setzt das Datum beim
  Deploy auf das `dateModified` der Seite – sichtbare Angabe und strukturierte Daten stimmen immer überein. Seiten mit
  eigener Stand-Pille (`<p class="stand">`, z. B. steuern-handelskosten) bekommen keine zweite Angabe.
- **datePublished** im JSON-LD jeder Artikelseite: der Tag, an dem die Seite auf bondarium.de erschien (erste Aufnahme ins
  Repository; das Repository beginnt mit der Veröffentlichung am 30.09.2026).
- **Keine Zusage-Wörter** („lohnt sich“, „sicherer Zins“, „beste“ …): am 04.10.2026 die letzten 18 Stellen beschreibend
  umformuliert („bringt mehr“, „passt“, „Grundzins“); `pruefen.py` warnt bei neuen.

## Neue Seite anlegen

Eine Seite steht von selbst in Sitemap, llms.txt und llms-full.txt, wenn ihr Kopf vollständig ist:

1. `<title>` bis 60 Zeichen, mit „ – Bondarium“ am Ende; das Suchwort vorn.
2. `<meta name="description">` mit 70 bis 160 Zeichen; derselbe Text in `og:description` und `twitter:description`.
3. `<link rel="canonical" href="https://www.bondarium.de/<datei>.html">` und `<meta name="robots" content="index, follow">`.
4. Ein JSON-LD-Block `Article` (oder `WebPage`/`CollectionPage`) mit `headline`, `description`, `datePublished`, `dateModified` und
   ein Block `BreadcrumbList`. Die zweite Brotkrume (Verstehen, Entscheiden, Kaufen, Anleihen, Zinsen) bestimmt
   den Abschnitt in llms.txt. Herausgeber, Autor, Bild und Website ergänzt `seo.py`; auf Seiten ohne `Article` auch
   `name` (aus `<title>`) und `description` (aus der meta description).
5. Genau eine `<h1>`; der Inhalt in `<main>`.
6. Zeichnet ein Skript eine Tabelle aus einer JSON-Datei, gehört sie in `statische_tabellen.py`.
7. Einleitung mit Antwortsatz und `Lesezeit: etwa N Minuten · <span class="stand-t">Stand: TT.MM.JJJJ</span>` (siehe oben).

`dateModified` von Hand nachziehen, wenn sich der Text ändert – daraus wird `<lastmod>` der Sitemap. Datenseiten
bekommen beim Deploy zusätzlich ihren sichtbaren Daten-Stand, wenn er jünger ist (siehe „Datum der Seiten“).

## Lokal prüfen

```bash
S=tmp/seo-site; rm -rf $S; mkdir -p $S
cp *.html *.json *.svg *.css *.js *.png *.webp *.woff2 favicon.ico robots.txt sitemap.xml indexnow-key.txt .htaccess $S/
cp -r kurse anleihen $S/
python3 scripts/security_txt.py $S
mkdir -p $S/trigger && cp strato-cron/refresh.php strato-cron/.htaccess $S/trigger/
python3 scripts/kennzahlen.py $S && python3 scripts/statische_tabellen.py $S && python3 scripts/rueckfallwerte.py $S \
  && python3 scripts/seo.py $S && python3 scripts/llms.py $S && python3 scripts/themen.py $S && python3 scripts/inline_data.py $S \
  && python3 scripts/css_klein.py $S && python3 scripts/pruefen.py $S
bash scripts/htaccess_test.sh $S
```

Die Skripte laufen auch mit dem lokalen Python 3.9 – außer `statische_tabellen.py`, das seit 03.10.2026 `_common.py` nutzt
(Typangaben ab Python 3.10; lokal über einen Starter mit `from __future__ import annotations`). Ansehen: `http://localhost:8080/tmp/seo-site/…`. Lokal fehlen
Minify, Versions-URLs und die Trigger-Konfiguration – die prüft nur der Workflow.

## Nicht im Code lösbar

- **Google Search Console und Bing Webmaster Tools**: Domain bestätigen, `sitemap.xml` einreichen. Erst dort sieht
  man, welche Seiten im Index sind und wofür sie gefunden werden.
- **Alte Domain metalconcrete.de**: `https://www.metalconcrete.de` antwortet mit einem Zertifikatsfehler, `http://`
  leitet auf diese kaputte https-Adresse. Bei STRATO als Weiterleitung auf `https://www.bondarium.de` einrichten –
  sonst gehen alte Links und Lesezeichen verloren.
- **Verweise von außen**: Erwähnungen und Links von anderen Seiten bleiben der stärkste Hebel, für Suchmaschinen
  wie für KI-Dienste.

## Offen

- **Steckbriefe der übrigen rund 33.000 Anleihen** (`anleihe.html?isin=…`): entstehen erst im Browser und tragen `noindex, follow`. Stufe 1 (seit 03.10.2026): die 79 Bundeswertpapiere als Server-Steckbriefe (`scripts/steckbriefe.py`). Ausbau nach 6–8 Wochen Search Console; Börsendaten (Kurse, Zinstermine) kommen erst ins Server-HTML, wenn die Rechtefrage geklärt ist. Ab einigen tausend Seiten eher PHP statt vorab erzeugter Dateien.
- **Rückfallwerte**: seit 04.10.2026 schreibt der Deploy alle Zinsen-Zahlen aktuell ins HTML – die sechs Zinsen-Datenseiten,
  `zinsniveau.html` (Kacheln „Zinsniveau heute“, EZB-Einlagesatz) und `fortgeschrittene.html` (Kasten „Bund heute“) über
  `rueckfallwerte.py`, die Top-10-Seiten, Top 30 nach Kupon, ETFs, Startseite und die Liste der Bundeswertpapiere über
  `statische_tabellen.py`. Ändert sich ein Seitenskript, bleibt die Seite auf dem alten Stand und das Protokoll warnt
  (ANKER) – dann die Nachbildung nachziehen.
- **Top-10-Seiten bei „aktiv“**: Sobald eine Rangliste `"aktiv": true` trägt, lässt `statische_tabellen.py` die
  Laufzeit-Seiten im Quellzustand (Handauswahl, alter „Daten-Stand“) – `dateModified` bleibt dann beim Quelldatum.
  Fehlt eine ISIN der Handauswahl in `kurse-auswahl.json` (z. B. nach ihrer Fälligkeit), bleibt ebenfalls die ganze
  Seite auf dem alten Stand; dann die Handauswahl im Seitenskript nachziehen.
- **Überschriften der Übersichtsseiten**: seit 02.10.2026 mit Thema („Akademie: Anleihen verstehen“, „Anleihen finden: …“,
  „Anleihen kaufen: …“, „Zinsen im Verlauf: …“, „Glossar: Anleihen-Begriffe von A bis Z“); im Menü bleiben die kurzen Namen.
  Liste aller Überschriften mit Urteil: `tmp/ueberschriften/bewertung.py`.
