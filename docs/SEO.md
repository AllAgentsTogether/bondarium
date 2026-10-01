# Auffindbarkeit: Suchmaschinen und KI-Dienste

Stand 30.09.2026. Was die Seite für Google, Bing und KI-Dienste (ChatGPT, Claude, Perplexity, Gemini) tut, wo es
im Code steht und was beim Anlegen einer neuen Seite zu beachten ist.

## Grundsatz

KI-Crawler führen kein JavaScript aus und lesen nur das ausgelieferte HTML. Google führt es aus, Bing nur
unzuverlässig. Deshalb gilt: Was gefunden werden soll, steht im HTML – als Text, als Tabelle, als strukturierte
Daten. Alles Folgende entsteht beim Deploy im Ordner `_site`; die Quell-HTML im Repository bleiben unverändert.

## Was beim Deploy passiert

Reihenfolge im Workflow `update-data.yml`, nach `kennzahlen.py` und vor `inline_data.py`:

| Schritt | Skript | Ergebnis |
| --- | --- | --- |
| Tabellen fest ins HTML | `scripts/statische_tabellen.py` | Die 19 Broker (`broker.json`: Kostenliste für 5.000 € mit Rechenweg, Angebots-Tabelle, Quellen je Anbieter – dieselbe Rechnung wie im Seitenskript) und die 70 ETFs (`top10-anleihen-etfs.json`) stehen fest im HTML. Im Browser ersetzt das Seitenskript sie durch seine eigene Fassung. Die Top 10 nach Ländern (Deutschland) folgen, sobald die automatische Rangliste gilt (`aktiv`). |
| Strukturierte Daten, Sitemap | `scripts/seo.py` | Ein JSON-LD-Block je Seite (`@graph`): Organisation und Website mit fester Kennung, Artikel mit Autor und Bild, Glossar als `DefinedTermSet` (67 Begriffe), Rechner als `WebApplication`, sechs Zeitreihen als `Dataset`. Robots-Angabe mit `max-image-preview:large`. `sitemap.xml` aus den Seiten. |
| llms.txt, llms-full.txt | `scripts/llms.py` | Kurzfassung (je Seite eine Zeile aus Titel und Beschreibung, gruppiert nach Brotkrumen) und Volltext aller Seiten als Markdown mit den aktuellen Zahlen aus den Daten-JSONs. |
| Prüfung | `scripts/pruefen.py` | Stoppt den Deploy bei fehlendem Titel, fehlender oder fremder kanonischer Adresse, unlesbarem JSON-LD. Warnt bei Titel über 60, Beschreibung außerhalb 70–160 Zeichen, keiner oder mehreren H1, doppelten Titeln. |
| Meldung an Bing | `scripts/indexnow.py` | Nach dem Upload gehen die Adressen der geänderten Seiten an IndexNow (Bing, Yandex, Seznam, Naver). Schlüssel: `indexnow-key.txt`. |

Die ersten drei Schritte sind Zugaben (`continue-on-error`): Scheitert einer, geht die Seite ohne ihn live.

## Server (`.htaccess`, `robots.txt`)

- `bondarium.com` und `www.bondarium.com` leiten dauerhaft auf `www.bondarium.de` um (vorher: gleicher Inhalt
  unter zwei Adressen). Ausgenommen `/trigger/` und `/.well-known/`.
- JSON-Dateien und die beiden llms-Dateien tragen `X-Robots-Tag: noindex`: abrufbar, aber kein eigener Suchtreffer.
- `robots.txt` nennt die KI-Crawler ausdrücklich (GPTBot, OAI-SearchBot, ChatGPT-User, ClaudeBot, Claude-SearchBot,
  Claude-User, PerplexityBot, Google-Extended und weitere). Es gelten dieselben Regeln wie für alle: alles erlaubt,
  außer `/trigger/`. Wer KI-Training nicht mehr zulassen will, setzt dort `Disallow: /` für GPTBot, ClaudeBot,
  Google-Extended, Applebot-Extended, Meta-ExternalAgent und CCBot – die Such-Crawler (OAI-SearchBot,
  Claude-SearchBot, PerplexityBot) bleiben dann erlaubt.

## Neue Seite anlegen

Eine Seite steht von selbst in Sitemap, llms.txt und llms-full.txt, wenn ihr Kopf vollständig ist:

1. `<title>` bis 60 Zeichen, mit „ – Bondarium“ am Ende; das Suchwort vorn.
2. `<meta name="description">` mit 70 bis 160 Zeichen; derselbe Text in `og:description` und `twitter:description`.
3. `<link rel="canonical" href="https://www.bondarium.de/<datei>.html">` und `<meta name="robots" content="index, follow">`.
4. Ein JSON-LD-Block `Article` (oder `WebPage`/`CollectionPage`) mit `headline`, `description`, `dateModified` und
   ein Block `BreadcrumbList`. Die zweite Brotkrume (Verstehen, Entscheiden, Kaufen, Anleihen, Zinsen) bestimmt
   den Abschnitt in llms.txt. Herausgeber, Autor, Bild und Website ergänzt `seo.py`.
5. Genau eine `<h1>`; der Inhalt in `<main>`.
6. Zeichnet ein Skript eine Tabelle aus einer JSON-Datei, gehört sie in `statische_tabellen.py`.

`dateModified` von Hand nachziehen, wenn sich der Text ändert – daraus wird `<lastmod>` der Sitemap. Bei
Datenseiten setzt der Deploy das Tagesdatum selbst.

## Lokal prüfen

```bash
S=tmp/seo-site; rm -rf $S; mkdir -p $S
cp *.html *.json *.svg *.css *.js *.png *.webp *.woff2 robots.txt sitemap.xml indexnow-key.txt $S/
python3 scripts/kennzahlen.py $S && python3 scripts/statische_tabellen.py $S && python3 scripts/seo.py $S \
  && python3 scripts/llms.py $S && python3 scripts/inline_data.py $S && python3 scripts/pruefen.py $S
```

Die vier neuen Skripte laufen auch mit dem lokalen Python 3.9. Ansehen: `http://localhost:8080/tmp/seo-site/…`.

## Nicht im Code lösbar

- **Google Search Console und Bing Webmaster Tools**: Domain bestätigen, `sitemap.xml` einreichen. Erst dort sieht
  man, welche Seiten im Index sind und wofür sie gefunden werden.
- **Alte Domain metalconcrete.de**: `https://www.metalconcrete.de` antwortet mit einem Zertifikatsfehler, `http://`
  leitet auf diese kaputte https-Adresse. Bei STRATO als Weiterleitung auf `https://www.bondarium.de` einrichten –
  sonst gehen alte Links und Lesezeichen verloren.
- **Verweise von außen**: Erwähnungen und Links von anderen Seiten bleiben der stärkste Hebel, für Suchmaschinen
  wie für KI-Dienste.

## Offen

- **Steckbriefe der rund 33.000 Anleihen** (`anleihe.html?isin=…`): entstehen erst im Browser; Titel und kanonische
  Adresse setzt das Skript. Für Suchen nach ISIN oder WKN wäre eine vom Server erzeugte Seite je Anleihe der größte
  einzelne Hebel (PHP bei STRATO oder vorab erzeugte Dateien) – eine Entscheidung über 33.000 zusätzliche Adressen.
- **Rückfallwerte der Datenseiten**: Tabellen und Kacheln in `renditen.html`, `zinskurve.html` usw. tragen im HTML
  den Stand der letzten Handpflege; aktuell werden sie erst im Browser. In `llms-full.txt` stehen die aktuellen
  Werte. Wer sie auch im HTML will, ergänzt `statische_tabellen.py` je Seite.
- **Überschriften der Übersichtsseiten**: „Verstehen“, „Kaufen“, „Zinsen“, „Glossar“ sind als H1 kurz. Für
  Suchmaschinen wäre „Anleihen verstehen“, „Anleihen kaufen“ besser – eine Textentscheidung.
