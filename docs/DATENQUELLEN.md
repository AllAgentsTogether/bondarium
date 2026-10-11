# Datenquellen — was kostenlos geht, was eine Erlaubnis braucht, warum Historie fehlt

Stand: 30.09.2026 · Anlass: „Die Website braucht mehr Daten über ETFs und Anleihen – wie komme ich kostenlos daran, und warum bekomme ich keine Historie?“
Verglichen wurde mit dem Datenstand vom 29.09.2026 (`anleihen-index.json`, `anleihen-kurse.json`, `etf-index.json`).

Kennzeichnung: **[geprüft]** = am 30.09.2026 selbst abgerufen und ausgewertet · **[Recherche]** = am 30.09.2026 von einer Hilfsrecherche abgerufen, von mir nicht einzeln nachgeprüft · **[offen]** = nicht geprüft.

---

## Kurzfassung

1. **Kurshistorie gibt es kostenlos – bei der Deutschen Börse selbst.** Ihre Website `live.deutsche-boerse.com` bietet je Wertpapier „Download Price History“ an, zu denselben Bedingungen wie die Tagesdateien, die wir schon nutzen (kostenlos, solange die Daten nicht vermarktet werden). Stichprobe: 22 von 25 Unternehmensanleihen mit Kurs hatten das ganze Jahr 2025, 18 von 20 Anleihen-ETFs ebenfalls; die übrigen sind erst 2026 gelistet. Offen ist nur, ob ein automatischer Abruf für rund 34.000 Wertpapiere gedeckt ist – das gehört in eine Anfrage.
2. **Jede vierte Anleihe hat gar keinen Kurs** (10.327 von 43.429). 6.299 davon werden in Stuttgart gehandelt. Die Börse Stuttgart stellt ihre Kurse kostenlos bereit, sperrt aber automatische Abrufe der Dateiliste. Auch hier: Anfrage.
3. **Rendite und Duration der ETFs** stehen bei den Anbietern offen zum Herunterladen, samt Kurswerten seit Auflage, Beständen und Fondsgröße. Die Nutzungsbedingungen aller Anbieter verlangen eine vorherige Zustimmung.
4. **Ohne jede Anfrage nutzbar** und noch nicht angebunden: Geld-/Briefkurse der Börse Frankfurt, die EZB-Liste notenbankfähiger Anleihen, die ESMA-Transparenzdateien, die Kurse niederländischer und belgischer Staatsanleihen, OpenFIGI.
5. **Ab Januar 2027** soll das EU-Sammelband für Anleihen (fairCT) starten: alle Umsätze aller Handelsplätze und des außerbörslichen Handels, für nicht-kommerzielle Nutzer kostenlos.

---

## Warum es nicht mehr Daten gibt

**1. Kursdaten sind ein Produkt der Börsen.** Das EU-Recht (MiFIR Art. 13) zwingt jeden Handelsplatz nur zu einem: Kurse 15 Minuten nach dem Handel kostenlos bereitzustellen. Ein Archiv muss niemand führen. Die Dateien liegen deshalb nur kurz online:

| Handelsplatz | Dateien online | Darf eine öffentliche Seite sie zeigen? |
|---|---|---|
| Deutsche Börse (Frankfurt, Xetra, Tradegate) | etwa 1 Börsentag [geprüft] | ja, solange nicht vermarktet (in Nutzung) |
| Börse Stuttgart | rund 6 Tage [geprüft] | keine Bedingungen gefunden; Dateiliste für Skripte gesperrt |
| gettex / Börse München | mindestens 24 Stunden [geprüft] | nein: nur natürliche Personen, nur privat, keine Weitergabe |
| Düsseldorf, Hamburg, Hannover, LS Exchange (BÖAG) | mindestens 24 Stunden [Recherche] | nein: Weitergabe nur mit schriftlicher Genehmigung, keine automatischen Abfragen [geprüft] |
| Börse Berlin | – | Xontro-Handel Anfang 2026 eingestellt; Tradegate ist über die Deutsche Börse abgedeckt |

**2. Unser Abruf liest nur die Tagesdatei.** Die enthält einen Tag. Der Verlauf beginnt deshalb am ersten Sammeltag (24.09.2026), bei den ETFs am 29.09.2026. In `docs/ETF-DATENBANK.md` stand als einziger Weg zu älteren Kursen „kaufen“. Das stimmt so nicht – siehe Kurzfassung 1.

**3. Anleihen werden kaum an der Börse gehandelt.** Von 33.102 Anleihen mit Kurs hatten am 29.09. nur 794 einen Umsatz. Alle anderen Kurse sind Preisfeststellungen der Frankfurter Spezialisten ohne Geschäft. Der eigentliche Handel läuft zwischen Banken; veröffentlicht wird er über Meldestellen (Bloomberg, Tradeweb, MarketAxess), deren Daten nicht frei weiterverwendbar sind. Genau diese Lücke soll das EU-Sammelband schließen.

**4. Frankfurt führt nicht jede Anleihe.** 10.327 Anleihen im Index haben keinen Kurs: 6.299 mit Stuttgart als Börse, 2.899 an anderen Regionalbörsen, 1.129 in Frankfurt ohne Feststellung. 9.227 davon sind Unternehmensanleihen.

**5. ETF-Kennzahlen rechnet nur der Anbieter.** Rendite des Bestands und Duration ergeben sich aus den Beständen, und die veröffentlicht nur der Fonds. Die Börse liefert Name, Kosten, Umsatz, Fondsvermögen – und die Kosten teils veraltet (iShares Core € Corp Bond: Börsenliste 0,20 %, Anbieterdatei 0,09 % [geprüft]).

**6. Ratings gehören den Agenturen.** Moody’s, S&P und Fitch lizenzieren jede Weitergabe.

**7. „Kostenlose“ Kursdienste sind für den Eigengebrauch.** Alle geprüften Gratis-Tarife verbieten die Anzeige auf einer öffentlichen Seite (siehe unten).

---

## Sofort nutzbar, ohne jemanden zu fragen

| Anbieter | Was | Was es bringt | Stand |
|---|---|---|---|
| **Deutsche Börse, MiFIR-Delayed-Data, Dienst `DFRA-pretrade`** – `https://mfs.deutsche-boerse.com/api/DFRA-pretrade` | Geld- und Briefkurs der Frankfurter Spezialisten, Minutendateien (je 2,5 MB) | Geld-Brief-Spanne je Anleihe = die echten Handelskosten. In einer einzigen Minute: 9.253 Index-Anleihen, 5.410 mit Geld und Brief; dazu 693 Register-ETFs | [geprüft] gleiche Lizenz wie die Kurse |
| **EZB, Liste der notenbankfähigen Sicherheiten** – `https://www.ecb.europa.eu/paym/coll/assets/html/dla/ea_MID/ea_csv_<JJMMTT>.csv.gz` | täglich, 31.241 Wertpapiere: Bewertungsabschlag (Haircut) und -kategorie, Emittentengruppe, Garant, Kupon-Art | 14.979 Index-Anleihen bekommen ein amtliches Qualitätsmerkmal: „von der EZB als Sicherheit akzeptiert, Abschlag x %“. Der nächste freie Ersatz für ein Rating | [geprüft] 1,1 MB, UTF-16 |
| **ESMA FITRS** – Dateien `FULNCR_<Datum>_D_*` über `registers.esma.europa.eu` | je ISIN: Anleiheart laut ESMA (Staat, öffentlich, Unternehmen, Pfandbrief, Wandelanleihe) und „liquide ja/nein“ | saubere Pfandbrief-Kennzeichnung, Liquiditätsmerkmal. Keine Umsätze | [geprüft] 5 Dateien, je rund 690 MB entpackt |
| **Niederländische Schuldenagentur DSTA** – `https://english.dsta.nl/latest/statistical-information/yields-on-dsls` | Tageskurs, Rendite und Duration je Staatsanleihe seit 2002 (MTS-Fixing), monatlich aktualisiert | Historie für die 26 niederländischen Staatsanleihen im Index. Lizenz CC0 [geprüft]; Quelle „MTS Amsterdam“ nennen | Datei [Recherche] |
| **Belgische Schuldenagentur** – `https://www.debtagency.be/sites/default/files/content/download/files/dm_olos.xml` | Kurs und Rendite je OLO, täglich gegen 15 Uhr | alle 37 OLOs stehen im Index. Keine Historie – ab jetzt selbst sammeln. Als „indikativ“ kennzeichnen; Lizenz schweigt | [geprüft] |
| **OpenFIGI** (Bloomberg) – `https://api.openfigi.com` | ISIN → Börsenkürzel, Wertpapierart | nur Kennungen, keine Kurse; Weiterverwendung ausdrücklich frei | [Recherche] |
| **Deutsche Börse, Monatsstatistik** (schon heruntergeladen, 181 Dateien seit 08/2011) | Fondsvermögen, Umsatz, XLM je ETF und Monat | Verlauf des Fondsvermögens über 15 Jahre – liegt vor, ist nur noch nicht gebaut | siehe `ETF-DATENBANK.md` |

---

## Nutzbar nach einer Anfrage

### Deutsche Börse – Kurshistorie (größter Hebel)

- **Was:** „Download Price History“ auf `live.deutsche-boerse.com` (früher boerse-frankfurt.de), je Anleihe (Frankfurt) und je ETF (Xetra), Tageswerte mit Umsatz.
- **Bedingungen** (`https://live.deutsche-boerse.com/disclaimer`, Abschnitt „Download Price History“) [geprüft]: kostenlose, nicht übertragbare Lizenz, nur solange der Nutzer die Daten nicht vermarktet. Als Vermarktung gilt die Weitergabe gegen Entgelt und das Anbieten von Mehrwertdiensten an Dritte. Das ist derselbe Wortlaut, auf den sich der tägliche Kursabruf schon stützt. Die Seite ist werbefrei und ohne Provisionen.
- **Wie weit zurück** [geprüft, Stichprobe über die Schnittstelle der Seite]: iShares Core € Corp Bond und Bund 4 % 2037 liefern Tageswerte für 2015. Von 25 zufälligen Unternehmensanleihen mit Kurs haben 22 Werte für 2025 (die drei übrigen sind 2026 gelistet), 15 auch für 2022. Von 20 zufälligen Anleihen-ETFs haben 18 Werte für 2025, 12 für 2022. Anleihen ohne heutigen Kurs haben auch dort fast nie Historie (1 von 15).
- **Was zu klären ist:** Die Lizenz spricht vom Herunterladen über die Website. Ein automatischer Abruf für rund 34.000 Wertpapiere über die Schnittstelle der Seite ist dort nicht geregelt. Deshalb vorher fragen – zusammen mit der ohnehin offenen Frage zur ETF-Liste und Monatsstatistik. Kontakt: `data.services@deutsche-boerse.com`.
- `scripts/import_kurshistorie.py` kann solche Daten bereits einlesen.

### Börse Stuttgart – Kurse für Anleihen ohne Frankfurter Kurs

- **Was:** Dienst „XSTU Post-Trade“, Minutendateien, rund 6 Tage online [geprüft]: `https://www.boerse-stuttgart.de/de-de/fuer-geschaeftspartner/reports/mifir-ii-delayed-data/`.
- **Was es bringt** [geprüft]: Stichprobe aus 51 der 1.137 Minutendateien des 29.09. – 9.654 Index-Anleihen mit Stuttgarter Preis, davon 2.598 bisher ganz ohne Kurs. Mit allen Dateien des Tages entsprechend mehr (Obergrenze 6.299).
- **Hindernis:** Die Seite mit der Dateiliste antwortet Skripten mit „403“ (Cloudflare-Schutz); die Dateien selbst laden frei. Der Schutz wird nicht umgangen. Nutzungsbedingungen stehen auf der Seite keine.
- **Anfrage:** Erlaubnis zur Anzeige auf einer kostenlosen Informationsseite und ein Zugang, den ein Skript nutzen darf.

### ETF-Anbieter – Rendite, Duration, Bestände, Kurswerte seit Auflage, Ausschüttungen

Technisch liegt alles offen, rechtlich verlangt jeder Anbieter eine vorherige Zustimmung. iShares, Xtrackers und Amundi stellen 45 % der 908 Anleihen-ETFs, die fünf größten 62 %.

| Anbieter | Was offen abrufbar ist | Bedingungen | Kontakt |
|---|---|---|---|
| **iShares (BlackRock)** | eine Datei je Fonds: Kurswerte seit Auflage, alle Bestände, Rendite, Duration, Kosten, Fondsgröße [geprüft: IE00B3F81R35, 7 MB]; Ausschüttungen auf der Produktseite | nur persönlicher Gebrauch; Vervielfältigung von Daten nur mit Zustimmung [Recherche] | info@iShares.de |
| **Xtrackers (DWS)** | Bestände als CSV; Kostendatei für alle Fonds (EMT) [geprüft: 113 Register-ETFs enthalten] | Herunterladen und Verbreiten nur mit schriftlicher Zustimmung; `robots.txt` sperrt die Export-Adressen [Recherche] | Kontaktseite etf.dws.com |
| **Amundi** | Kurswerte, Bestände, Fondsgröße, Kosten; Rendite und Duration nur auf Index-Ebene [Recherche] | Wiedergabe nur mit schriftlicher Zustimmung | info_de@amundi.com |
| **Vanguard** | Kurswert- und Kursverlauf, Ausschüttungen, Bestände, Kosten [Recherche] | nur persönlich; automatischer Zugriff untersagt | info.deutschland@vanguard.com |
| **SPDR (State Street)** | Kurswerte seit Auflage, Bestände, Rendite, Duration, Produktliste [Recherche] | keine Vervielfältigung | Kontaktformular |
| **JPMorgan** | Produktliste, Kosten, Fondsgröße [Recherche] | offen | data_support@jpmorgan.com |
| **Invesco, UBS, PIMCO, BNP Paribas** | hinter Bot-Schutz oder Anlegerabfrage, nicht geprüft | Zustimmung nötig | deutsche Niederlassung |

Pflichtdokumente als Ausweg für einzelne Werte: Das Basisinformationsblatt (PDF je ISIN) und die Kostendateien EMT/EPT nennen laufende Kosten, Transaktionskosten und Risikoklasse. Offen abrufbar bei DWS, BlackRock und Vanguard; eine Freigabe zur Wiedergabe steht auch dort nicht.

### Weitere

- **Banco de España, „Boletín del Mercado de Deuda Pública“** – `https://repositorio.bde.es/handle/123456789/16881`: Tageskurse je spanischer Staatsanleihe 1993 bis April 2018, Lizenz CC BY-NC-SA (nicht-kommerziell, Quelle nennen). Endet 2018. [Recherche]
- **Ratings:** Die Agenturen müssen ihre Rating-Historie nach US-Recht (SEC-Regel 17g-7) kostenlos veröffentlichen, mit zwölf Monaten Verzug. Die Weiterverwendung regeln ihre eigenen Bedingungen. [offen]

---

## Kommt 2027: EU-Sammelband für Anleihen (fairCT)

- ESMA hat Ediphy (fairCT) am 03.07.2025 als Betreiber ausgewählt; die Zulassung läuft [geprüft, ESMA-Seite].
- Start laut fairCT: Januar 2027; voraussichtlich mit Echtzeit- und historischen Handelsmeldungen [Recherche, fairCT-FAQ].
- MiFIR Art. 27h schreibt kostenlosen Zugang für Privatanleger, Wissenschaft und zivilgesellschaftliche Organisationen vor; laut fairCT entfallen die Gebühren für nicht-kommerzielle Nutzer [Recherche].
- Bedeutung: erstmals alle Umsätze einer Anleihe über alle Handelsplätze und den außerbörslichen Handel. Ob eine öffentliche Seite die Daten zeigen darf, steht noch nicht fest. Kontakt: fairctinfo@fairct.org.

---

## Nicht nutzbar für eine öffentliche Seite

- **Gratis-Schnittstellen** [Recherche, Bedingungen vom 30.09.2026]: Alpha Vantage (25 Abrufe/Tag, nur persönlich), Twelve Data (kein Xetra im Gratis-Tarif), EODHD (20 Abrufe/Tag, keine Anzeige), Tiingo, Financial Modeling Prep, Finnhub, Polygon/Massive (nur USA), Marketstack (Gratis-Tarif nicht-kommerziell, 100 Abrufe/Monat).
- **Stooq:** Browser-Prüfung per JavaScript vor jedem Abruf [geprüft]. **Yahoo Finance:** keine automatische Nutzung, keine Weitergabe.
- **justETF, extraETF, Morningstar, onvista, ariva:** automatische Abfragen und Wiedergabe untersagt.
- **Xetra Public Dataset** (Minutendaten ab 2017 bei Amazon): abgeschaltet, Zugriff verweigert [geprüft].
- **gettex / München, BÖAG-Börsen:** siehe Tabelle oben.
- **Staatsanleihen-Kurse anderer Länder:** Frankreich veröffentlicht seit 10.07.2024 keine OAT-Sätze mehr; Italien, Österreich, Finnland, Irland nur Auktionen und Bestände; Großbritannien hinter Bot-Schutz, seit 2017 Daten von Tradeweb/FTSE; Japan (JSDA) nur mit Zustimmung. [Recherche]

---

## Empfohlene Reihenfolge

1. **Eine Anfrage an die Deutsche Börse** mit drei Punkten: ETF-Liste und Monatsstatistik (seit 30.09. ohne Zusage veröffentlicht), Kurshistorie per automatischem Abruf, Bestätigung, dass eine werbefreie Informationsseite nicht als Vermarktung gilt.
2. **Parallel bauen, was frei ist:** Geld-/Briefkurse (Spanne im Steckbrief und in der Suche), EZB-Merkmal, ESMA-Anleiheart, Verlauf des Fondsvermögens aus den vorhandenen Monatsdateien, niederländische und belgische Staatsanleihen.
3. **Anfrage an die Börse Stuttgart.**
4. **Anfragen an iShares, DWS und Amundi**, danach Vanguard und SPDR.
5. **Januar 2027:** fairCT prüfen.
