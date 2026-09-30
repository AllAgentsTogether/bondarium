# ETF-Datenbank — Strategie und Umsetzungsstand

Stand: 30.09.2026, vierte Fassung · Register, Kursabruf und die ETF-Seiten ohne Handpflege sind gebaut und lokal getestet, aber noch nicht veröffentlicht. Suche und Steckbrief fehlen noch.
Ziel: eine Datenbank aller Anleihen-ETFs, die in Deutschland handelbar sind – mit Suche und Steckbrief, so wie es sie für die rund 33.000 Anleihen schon gibt.

**Grundsatz seit 30.09.2026 (Nutzerentscheid): Kein ETF wird von Hand gepflegt.** Keine handverlesenen Listen, keine Kennzahlen von Anbieterseiten, keine Korrekturliste. Was sich nicht automatisch aktualisieren lässt, steht nicht auf der Seite.

---

## Kurzfassung

1. **Machbar, und der größte Teil der Technik steht schon.** Die ETF-Datenbank wird wie die Anleihen-Datenbank gebaut: ein Register, Kurse (täglich), eine Suche, ein Steckbrief. Es bleibt bei statischen Dateien, ein Datenbank-Server ist nicht nötig.
2. **Umfang: 908 Anleihen-ETFs** mit zusammen 387 Mrd. € Fondsvermögen.
3. **Die Deutsche Börse liefert fast alles selbst.** Ihre ETF-Liste bringt Namen, Kosten und Index; ihre Monatsstatistik bringt Anlageklasse, Fondsvermögen, Umsatz und Handelskosten; ihre Nachhandelsdaten bringen die Kurse.
4. **Was dadurch wegfällt:** Rendite des Bestands und Duration gibt es nur bei den Fondsanbietern. Sie stehen nicht mehr auf der Seite, bis es dafür eine automatische Quelle gibt (Zustimmung der Anbieter).
5. **Offen vor der Veröffentlichung:** die Erlaubnis der Deutschen Börse für Liste und Monatsstatistik (sie sind das Rückgrat).

---

## Umsetzungsstand (30.09.2026)

| Baustein | Stand |
|---|---|
| Register `etf-index.json` (Stammdaten, Einstufung, Fondsvermögen, Umsatz, XLM) | gebaut: `scripts/update_etf_index.py`, im 10-Uhr-Lauf eingehängt |
| Neue ETFs | automatisch: Jeder Lauf liest die Börsenliste neu; ein Neuzugang steht am Tag des Listings im Register und bekommt am selben Tag einen Kurs |
| Kurse aller Register-ETFs (`etf-kurse.json`, Verlauf in `kurse/`) | gebaut: `scripts/update_kurse.py` erweitert |
| ETF-Seite `anleihen-etf.html` | umgebaut: die zehn meistgehandelten je Kategorie aus `top10-anleihen-etfs.json`, bei jedem Lauf neu |
| ETF-Karten im Guide | umgebaut: im HTML steht je Karte nur die ISIN, alles andere kommt aus `etf-auswahl.json` und den Kursen |
| Startseite und `etf-oder-anleihe.html` | Zahl der ETFs und Kostenspanne setzt der Deploy aus den Daten ein |
| Handgepflegte Datei `etfs.json` | gelöscht; nichts liest sie mehr |
| Hinweis „Angaben ohne Gewähr“ in `rechtliches.html` | angepasst: „Kennzahlen von Fondsanbietern“ stehen nicht mehr unter den von Hand erfassten Angaben |
| Lücken nachtragen | gebaut: `update_kurse.py --nachtragen` mit den gesicherten Rohdateien; der 29.09. ist lokal nachgetragen |
| Alarm bei veralteten Daten | ergänzt (Frische-Prüfung für `etf-index.json` und `etf-kurse.json`) |
| Veröffentlichung | **offen** – erst mit „push“. Dann liegen die Dateien im öffentlichen GitHub-Repo und auf dem Webserver |
| Steckbrief `etf.html`, Suche `etf-suche.html` | offen (Phase 3) |
| Rendite und Duration | offen (Phase 4, braucht eine automatische Quelle) |

### Was der Lauf jeden Tag tut

1. **Börsenliste holen** (0,5 MB). Daraus entsteht das Register neu. Ein ETF, der in der Liste neu auftaucht, ist damit im Register; einer, der verschwindet, fällt heraus. Das Protokoll nennt beide.
2. **Monatsstatistik prüfen** – nur solange die Datei des Vormonats noch fehlt, also an den ersten Tagen eines Monats. Sie bringt die Anlageklasse der Neuzugänge sowie Fondsvermögen, Umsatz und XLM.
3. **EU-Register** (FIRDS) – einmal pro Woche, für den ersten Handelstag und als Gegenprobe.
4. **Top 10 und Karten neu schreiben:** `top10-anleihen-etfs.json` für die ETF-Seite, `etf-auswahl.json` für die ETF-Karten anderer Seiten.
5. **Kurse holen** für alle Anleihen, alle Seiten-ETFs und alle Register-ETFs.

### Geprüft

- **Register:** Lauf mit den heruntergeladenen Dateien und Lauf gegen die echten Quellen liefern dasselbe Ergebnis. Der Aufbau „bis Juli, dann kommt August dazu“ ergibt denselben Stand wie der Aufbau in einem Zug.
- **Top 10:** Die automatischen Listen enthalten 64 der 70 ETFs der bisherigen Handlisten; vier der sieben Kategorien sind deckungsgleich, in allen stimmen die Plätze 1 bis 3. Die sechs neuen ETFs haben jeweils mehr Umsatz als die sechs, die sie verdrängen. Zwei davon sind Dollar-Kurzläufer ohne Absicherung; sie stehen nach der Regel bei „Staatsanleihen weltweit“.
- **Absicherung und Ausschüttung:** Beides stimmt bei allen 70 ETFs der bisherigen Handlisten mit deren Angabe überein.
- **Nachtrag:** 902 ETF-Kurse für den 29.09. ergänzt, keine Anleihe berührt, zweiter Lauf ändert nichts mehr.
- **Fehlerfälle:** Defekte Börsenliste → Register bleibt unverändert. Monatsstatistik oder FIRDS nicht erreichbar → Register mit dem letzten Zwischenstand, Schritt wird rot. Nennt eine Guide-Karte einen ETF, der nicht mehr im Register steht → Warnung im Lauf mit der ISIN.
- **Kurse:** Der neue Kursabruf, angewendet auf den Stand vor dem 29.09. und die Rohdateien vom 29.09., liefert für alle 33.102 Anleihen exakt die Datei, die der Workflow geschrieben hat. Geändert sind nur ETF-Einträge.
- **Seiten:** ETF-Seite (Desktop und Handy), Guide und Startseite in der Vorschau ohne Konsolenfehler; Veröffentlichungsschritte (`kennzahlen.py`, `inline_data.py`, `pruefen.py`) in einer Kopie ohne Fehler.
- **Nicht geprüft:** ein echter Lauf in GitHub Actions. Lokal lief alles unter Python 3.9 mit einem Hilfsstarter, der Workflow nutzt 3.12. Ob die Seiten der Börse Abrufe von GitHub-Servern zulassen, zeigt erst der erste Lauf.

### Beim Veröffentlichen zu beachten

- Lokal sind `kurse/2026/`, `kurse-auswahl.json` und `etf-kurse.json` um die ETF-Kurse vom 29.09. ergänzt. Kommt vor dem Push ein neuer Datenlauf, müssen diese Dateien verworfen und der Nachtrag wiederholt werden.
- Für spätere Tage liegen die Rohdateien im Artefakt `kurse-roh-…` des jeweiligen Laufs (90 Tage).

---

## Was geprüft ist

| Quelle | Liefert | Ergebnis der Prüfung |
|---|---|---|
| **Deutsche Börse, Liste der handelbaren ETFs & ETPs** (Excel, 0,5 MB, Stand 30.09.2026) | Name, ISIN, Anbieter, Xetra-Kürzel, laufende Kosten, ausschüttend/thesaurierend, Nachbildung, Fondswährung, Handelswährung, Index | Ausgewertet. 3.718 Zeilen, 3.565 ISINs, davon 2.999 ETFs. Keine Spalte für die Anlageklasse. |
| **Deutsche Börse, Monatsstatistik ETFs & ETPs** (Excel je Monat, rund 1,6 MB) | je ETF: Xetra-Umsatz des Monats, Fondsvermögen, Handelskosten XLM, aktiv/passiv; dazu die Neuzugänge des Monats mit **Anlageklasse** | 300 Monatsdateien seit 08/2001. Die 181 im heutigen Excel-Format (seit 08/2011, 197 MB) heruntergeladen und ausgewertet. Die Neuzugangs-Liste mit Anlageklasse gibt es seit 07/2016. |
| **ESMA FIRDS, Datei der Fonds** (`FULINS_C`, wöchentlich, 3,8 MB) | CFI-Code (ETF, Anlageklasse, Ausschüttung), erster Handelstag | Ausgewertet. Alle 2.999 ETFs sind enthalten; bei neun fehlt der erste Handelstag (darunter ein Anleihen-ETF). |
| **Deutsche Börse, Nachhandelsdaten** (Xetra, Tradegate, Frankfurt) | Kurs, Umsatz, Abschlüsse je Tag | Läuft täglich in `update_kurse.py`. Tagesdateien vom 29.09. ausgewertet: Xetra stellt für jeden der 908 ETFs täglich Auktionspreise fest, auch ohne Umsatz. |
| **Anbieter-Seiten** (iShares, Xtrackers, Amundi …) | Rendite des Bestands, Duration, Fondsgröße über alle Anteilsklassen, Zahl der Anleihen | Nur die Rechtslage angesehen: iShares verlangt laut seinen Bedingungen eine vorherige Zustimmung für die Vervielfältigung von Daten (aus einer Suchauswertung, Wortlaut noch im Original prüfen). |

### Befunde, die den Bauplan bestimmen

- **Die Börse stuft selbst ein.** 2.275 der 2.999 ETFs (76 %) wurden seit Juli 2016 gelistet und tragen damit eine Anlageklasse der Börse; 733 davon sind Anleihen-ETFs („Fixed Income“). Von den 724 älteren ETFs sind nach Name und Index 175 Anleihen-ETFs – diese Liste habe ich einmal durchgesehen, sie enthält keinen Fehltreffer.
- **Wie gut die Ersatzsignale sind**, gemessen an der Einstufung der Börse:

  | Signal | findet von 733 Anleihen-ETFs | Fehltreffer |
  |---|---|---|
  | Stichwörter in Name und Index (mit Ausschlussliste) | 729 (99,5 %) | 0 |
  | CFI-Code „Anleihen“ | 457 (62 %) | 8 |

  Der CFI-Code entscheidet deshalb nicht mit. Viele Luxemburger Fonds (Xtrackers II, Amundi, UBS) sind als „gemischt/sonstige“ gemeldet, einzelne Anleihen-ETFs als „Aktien“.
- **Die Rangfolge lässt sich nachrechnen.** Der Xetra-Umsatz der letzten zwölf Monate aus der Statistik ergibt bei „Euro-Staatsanleihen“ für die bisherigen zehn ETFs exakt die bisherige Reihenfolge; in den anderen Gruppen stimmen die Plätze 1 bis 3.
- **Fondsvermögen steht je Anteilsklasse in der Statistik, nicht je Fonds.** Beispiel iShares € Ultrashort Bond: 2.794 Mio. € (thesaurierend) und 3.322 Mio. € (ausschüttend); der Anbieter nennt für den ganzen Fonds 6.251 Mio. €. Die Seiten schreiben deshalb „Anteilsklasse“ dazu.
- **Manche ETFs haben mehrere Handelswährungen.** 24 Anleihen-ETFs werden an Xetra unter derselben ISIN in mehr als einer Währung gehandelt, fast immer Euro und Dollar; der bisherige Kursabruf hätte beide gemischt. 36 Anteilsklassen haben gar keine Euro-Zeile (27 USD, je 3 GBP und SEK, 2 CHF, 1 AUD) – ihr Kurs steht in dieser Währung.
- **Die Börsenliste ist gut, aber nicht fehlerfrei – und ohne Handpflege zeigen die Seiten ihre Fehler.**
  - Bei 6 der 70 zuletzt handgepflegten ETFs wichen die Kosten ab. Ein Fall ist nachgeprüft (über eine Websuche, nicht auf der Anbieterseite selbst): iShares Core € Corp Bond steht in der Börsenliste mit 0,20 %, der Anbieter nennt 0,09 % (Stand 21.09.2026). Die ETF-Seite zeigt jetzt 0,20 % mit dem Hinweis „laut Deutscher Börse“.
  - Die Spalte „Homepage“ ist unbrauchbar (falsche Anbieter-Adressen), bei zwei Aktien-ETFs von Xtrackers steht ein Anleihen-Index.
  - Drei Euro-Anteilsklassen von Invesco-ETFs auf US-Staatsanleihen tragen keine Absicherung im Namen. Eine davon stand in den Handlisten, dort als abgesichert. Eine Regel fängt das ab (siehe Einstufung).
  - Der CFI-Code widerspricht der Liste bei der Ertragsverwendung von 22 ETFs.
- **Wenige Anbieter decken fast alles ab.** iShares, Xtrackers und Amundi stellen 45 % der Anleihen-ETFs, die fünf größten 62 %, die neun größten 82 %.
- **422 ETFs teilen sich ihren Index mit mindestens einem anderen ETF** (174 Indizes). Das erlaubt einen Vergleich „gleicher Index, andere Kosten“ ganz ohne Anbieterdaten.
- **Zusammensetzung der 908:** 476 thesaurierend, 432 ausschüttend · 183 aktiv gemanagt · 184 währungsgesichert · 73 Laufzeit-ETFs mit Endjahr · Kosten von 0,03 % bis 1,28 %, Median 0,15 %.
- **Abdeckung der Statistik:** 904 der 908 haben Fondsvermögen und XLM (die vier übrigen sind im September gelistet oder fehlen in der Statistik). Gut ein Viertel (28 %) hatte im August weniger als 100.000 € Xetra-Umsatz.

Gezählt sind Anteilsklassen (je ISIN eine).

---

## Zwei Begriffe

**Geldmarkt-ETF.** Ein ETF, der keine Anleihen mit Jahren Laufzeit hält, sondern den Zins für Geld „über Nacht“ abbildet – den Satz, zu dem sich Banken untereinander für einen Tag Geld leihen (im Euroraum „€STR“, er liegt nah am Einlagesatz der EZB). Der Kurs steigt fast jeden Tag ein kleines Stück und schwankt praktisch nicht. Für Anleger ist das Tagesgeld an der Börse, allerdings ohne Einlagensicherung. 14 der 22 Geldmarkt-ETFs bilden den Zins über ein Tauschgeschäft mit einer Bank nach („Swap“) und halten selbst gar keine Anleihen.

- 22 ETFs, 39 Mrd. € Fondsvermögen, gut 10 Mrd. € Xetra-Umsatz in zwölf Monaten. Das ist fast ein Viertel des Umsatzes aller Anleihen-ETFs.
- Der meistgehandelte, Xtrackers II EUR Overnight Rate Swap, kam auf 6,7 Mrd. € – das Sechsfache des meistgehandelten klassischen Anleihen-ETFs (iShares € Ultrashort Bond, 1,1 Mrd. €).
- Sie stehen im Register, aber in keiner Tabelle der ETF-Seite. Der Deka EUROGOV Germany Money Market hält trotz seines Namens kurzlaufende Bundeswertpapiere; er zählt als Staatsanleihen-ETF und steht wie bisher unter „Kurze Laufzeiten“.

**Aktiver ETF.** Ein gewöhnlicher ETF ist passiv: Er bildet einen Index nach festen Regeln nach, niemand wählt aus. Bei einem aktiven ETF entscheidet ein Fondsmanager, welche Anleihen gekauft werden. Gehandelt wird er an der Börse wie jeder ETF.

- 183 der 908 (20 %), aber nur 18 Mrd. € Fondsvermögen und 2,2 Mrd. € Umsatz – jeweils rund 5 %.
- Kosten im Median 0,25 % statt 0,15 %; Handelskosten (XLM) im Median 37 statt 21 Basispunkte.
- Sie wachsen schnell: 2025 war jeder zweite neu gelistete Anleihen-ETF aktiv (79 von 158).
- Sie stehen im Register und kommen in die Tabellen, wenn ihr Umsatz reicht. Heute schafft das einer: PIMCO Advantage Euro Short-Term High Yield bei den Hochzinsanleihen (er stand auch in der Handliste).

---

## Grundsätze

1. **Kein ETF wird von Hand gepflegt.** Von Hand gewählt sind nur die Beispiele im Guide – dort steht je ETF die ISIN, sonst nichts.
2. **Nur Quellen mit Erlaubnis.** Jede Zahl trägt ihre Quelle und ihr Datum.
3. **Quelldaten bleiben unverändert.** Widersprüche zwischen Quellen werden im Register vermerkt (Feld `pruef`). Stimmt eine Einstufung nicht, wird die Regel verbessert, nicht der einzelne ETF gesetzt.
4. **Eigene Berechnungen sind als „berechnet“ gekennzeichnet**, Ableitungen aus dem Namen als „abgeleitet“.
5. **Neutral.** Der Steckbrief zeigt Werte, keine Bewertung und keine Empfehlung; `neutral_check.py` prüft auch die neue Seite.
6. **Automatisch und überwacht.** Alles läuft im bestehenden Workflow, mit Alarm bei veralteten oder stark geschrumpften Daten.

---

## Aufbau in vier Schichten

### 1 · Register (täglich) → `etf-index.json`

- **Quellen:** Börsenliste für die Stammdaten, Monatsstatistik für Anlageklasse und Monatswerte, EU-Register für den ersten Handelstag und als Gegenprobe.
- **Direkt übernommen:** Name, ISIN, Anbieter, Xetra-Kürzel, laufende Kosten, ausschüttend/thesaurierend, Nachbildung, Fondswährung, Handelswährung, Index, aktiv/passiv, erster Handelstag, Fondsvermögen der Anteilsklasse, Xetra-Umsatz der letzten zwölf Monate, XLM.
- **Aus Name und Index abgeleitet** (in der Datei als „abgeleitet“ benannt):
  - Kategorie: Geldmarkt, Staat, Unternehmen, Hochzins, Schwellenländer, breit gestreut, inflationsgeschützt, Pfandbriefe, Sonstige
  - Markt: Währung oder Raum der Anleihen (EUR, USD, GBP, Welt …)
  - Laufzeitband, nur wenn es ausdrücklich im Namen steht (288 ETFs)
  - Endjahr eines Laufzeit-ETFs
  - Währung der Absicherung
  - Gruppe: die Tabelle der ETF-Seite, in die der ETF gehört
- **Größe:** 908 Zeilen, 234 KB.
- **Zwischenstände** im Ordner `etf/` (Anlageklassen seit 07/2016, Monatswerte, CFI-Codes). Sie werden committet, aber nicht auf den Webserver kopiert.
- **Für die Seiten:** `top10-anleihen-etfs.json` (die zehn meistgehandelten je Tabelle) und `etf-auswahl.json` (ETFs, die eine Seite per ISIN nennt). Beide tragen je ETF einen `kurzname`: der Name ohne „UCITS ETF“, Anteilsklasse und Absicherungszusatz, mit „EUR“ und „USD“ statt „€“ und „$“ (die Börsenliste schreibt beides).

### 2 · Handel (täglich) → `etf-kurse.json`, Verlauf in `kurse/`

- Kurs je Anteil in der Handelswährung des Registers, Xetra vor Tradegate vor Frankfurt.
- Für jeden ETF gibt es jeden Börsentag einen Kurs, weil Xetra auch ohne Umsatz Auktionspreise feststellt.
- Der Kursverlauf liegt im selben Format wie bei den Anleihen in `kurse/<Jahr>/<hh>.json`; der Steckbrief kann ihn genauso laden.
- **Noch zu bauen:** Wertentwicklung über feste Zeiträume, Schwankung, größter Rückgang – sinnvoll erst mit mehr Handelstagen. Die Schwankung aus eigenen Kursen wäre der automatische Ersatz für die Duration.
- **Grenzen:** Der Verlauf beginnt am 24.09.2026 (für die meisten ETFs am 29.09.). Die Wertentwicklung wäre eine reine Kursentwicklung; bei ausschüttenden ETFs fehlen die Ausschüttungen.

### 3 · Monatsstatistik der Börse (monatlich)

- **Fondsvermögen der Anteilsklasse**, **Xetra-Umsatz** und **XLM** je ETF – stehen im Register.
- XLM sind die Handelskosten für Kauf und sofortigen Verkauf von 100.000 € in Basispunkten (Geld-Brief-Spanne und Marktwirkung). Eine neutrale Zahl, die kaum eine Vergleichsseite zeigt.
- **Rangfolge „meistgehandelt“** aus dem Umsatz der letzten zwölf Monate.
- **Noch zu bauen:** der Verlauf des Fondsvermögens über die Jahre. Die Dateien gibt es seit 2011.

### 4 · Rendite und Duration (offen)

- Beides veröffentlichen nur die Anbieter. Ein automatischer Abruf je Anbieter ist möglich, braucht aber deren Zustimmung; Reihenfolge iShares, Xtrackers, Amundi, BNP Paribas, Invesco.
- **Eigener Ersatz, wo es geht:** Für klar abgegrenzte Staatsanleihen-Klassen lässt sich eine Vergleichsrendite aus der eigenen Anleihen-Datenbank rechnen (Durchschnitt der Euro-Staatsanleihen eines Laufzeitbands). Für Unternehmens- und Hochzins-ETFs geht das nicht, weil die Anleihen-Datenbank keine Ratings hat.

---

## Einstufung: Was ist ein Anleihen-ETF, und in welche Tabelle gehört er?

Das Feld `klasse` sagt, woher die Einstufung als Anleihen-ETF stammt:

- **B – die Börse.** Anlageklasse „Fixed Income“ in der Neuzugangs-Liste des Monats, in dem der ETF gelistet wurde. Gilt für jeden ETF seit Juli 2016 (733 der 908).
- **S – Stichwörter** in Name und Index, mit einer Ausschlussliste für Aktien- und Rohstoffprodukte. Gilt für ältere ETFs (175) und für Neuzugänge, bis ihre Monatsstatistik erscheint – also höchstens rund fünf Wochen.

Der CFI-Code dient nur als Gegenprobe. Wo er widerspricht, steht es im Feld `pruef`; die kurze `pruefliste` im Kopf der Datei (heute acht Einträge) nennt die Fälle, in denen nur Stichwörter und CFI-Code gegeneinander stehen. Eine Handliste gibt es nicht.

**Tabellen der ETF-Seite** (Feld `gruppe`). Jeder ETF steht höchstens in einer; die Reihenfolge entscheidet:

1. Schwellenländer, dann Hochzins – nach dem Risiko.
2. Kurze Laufzeiten: Laufzeitband bis höchstens drei Jahre oder Laufzeit-ETF, der spätestens im übernächsten Jahr endet – nur Euro-Anleihen oder in Euro abgesichert.
3. Breit gestreut, Unternehmensanleihen.
4. Staatsanleihen, auch inflationsgeschützte: Euro-Staatsanleihen oder Staatsanleihen weltweit, je nach Währung.
5. Ohne Tabelle bleiben Geldmarkt-ETFs, Pfandbriefe und „Sonstige“ (Wandel- und Nachranganleihen, verbriefte Kredite, Strategien, Unklares) – zusammen 105 ETFs.

**Währungsabsicherung.** Aus dem Namen. Schweigt der Name, gilt eine Euro-Anteilsklasse eines ETFs auf Dollar-, Pfund- oder Yen-Anleihen als in Euro abgesichert: Am 30.09.2026 gab es 87 solche Klassen; 84 tragen die Absicherung im Namen, die Regel greift nur bei den drei übrigen (Invesco US Treasury). Umgekehrt gilt es nicht – die Dollar-Klasse eines China- oder Indien-ETFs ist nur die Fondswährung.

---

## Seiten

- **`anleihen-etf.html`** – sieben Tabellen mit den zehn meistgehandelten ETFs: Kurs, Kosten, Laufzeit, Größe, Umsatz, Ausschüttung; im Aufklapper Tageswerte, Handelskosten, erster Handelstag, Kursverlauf. Die Kategorie-Karten zeigen, wie viele ETFs die Kategorie im Register hat. „Gut zu wissen“ wird aus den zehn ETFs gerechnet.
- **Guide** – sechs ETF-Karten, je nur mit ISIN im HTML. Steht der ETF unter den zehn seiner Kategorie, führt der Name dorthin.
- **Noch zu bauen: `etf-suche.html`** – Suche über alle ETFs nach Name, ISIN oder Kürzel. Filter: Kategorie, Laufzeitband, Währung und Absicherung, ausschüttend/thesaurierend, Anbieter, Kosten, Laufzeit-ETF, aktiv/passiv. Vorbild ist `anleihen-suche.html`.
- **Noch zu bauen: `etf.html?isin=…`** – Steckbrief: Stammdaten mit Quelle, Kurs und Kursverlauf, Handel je Börsenplatz, Kosten und Handelskosten, Fondsvermögen im Zeitverlauf, „ETFs auf denselben Index“ und die anderen Anteilsklassen desselben Fonds. Vorbild ist `anleihe.html`. Damit wird jede ETF-Karte anklickbar.

---

## Reihenfolge

Jede Phase endet mit einem Ergebnis, das du in der Vorschau ansehen kannst. Veröffentlicht wird erst auf dein „push“.

### Phase 0 · Klären und reparieren

- ✅ **Fehler behoben:** Der Kursabruf erfasst die ETFs der ETF-Seite wieder (im Datenstand vom 29.09. haben live nur 2 der 70 einen Kurs).
- **Erlaubnis einholen:** Anfrage an die Deutsche Börse für ETF-Liste und Monatsstatistik. Den Text entwerfe ich, du schickst ihn.

### Phase 1 · Register und Monatswerte

- ✅ `scripts/update_etf_index.py`, Zwischenstände in `etf/`, Prüfliste.
- ✅ Top-10-Listen automatisch; Abgleich mit den bisherigen Handlisten (64 von 70 gleich).

### Phase 2 · Kurse und eigene Berechnungen

- ✅ Kursabruf für alle Register-ETFs, `etf-kurse.json`, Nachtrag.
- Offen: Wertentwicklung, Schwankung und größter Rückgang – sobald genug Handelstage vorliegen.

### Phase 3 · Steckbrief und Suche

- ✅ ETF-Seite, Guide-Karten und Startseite ohne Handpflege.
- Offen: erst der Steckbrief (kleiner, macht jede ETF-Karte anklickbar), dann die Suche; Navigation, Sitemap, `llms.txt`, Neutralitätstest.
- **Abnahme:** Vorschau auf Desktop und Handy, keine Konsolenfehler, `pruefen.py` ohne tote Links.

### Phase 4 · Rendite und Duration

- Je Anbieter ein automatischer Abruf, sobald die Zustimmung vorliegt; bis dahin die Vergleichsrendite aus der eigenen Anleihen-Datenbank für Staatsanleihen-ETFs und die Schwankung aus eigenen Kursen.

### Phase 5 · Ausbau (später entscheiden)

- Geld-Brief-Spanne aus den Vorhandelsdaten der Börse (Datei existiert, ist aber groß).
- Bestände der ETFs: „In welchen ETFs steckt diese Anleihe?“ – die Brücke zwischen beiden Datenbanken. Braucht Anbieterdaten.
- Ausschüttungen, damit die Wertentwicklung vollständig ist.
- Ältere Kurse über eine einmalige Lieferung der Börse (`import_kurshistorie.py` kann das schon einlesen).

---

## Entscheidungen, die bei dir liegen

| Frage | Mein Vorschlag | Was es ausmacht |
|---|---|---|
| Geldmarkt-ETFs in die Tabellen? | Ja, als eigene achte Kategorie. Sie sind der direkte Vergleich zum Tagesgeld und die meistgehandelten Produkte im ganzen Feld. Heute stehen sie nur im Register. | 22 ETFs, fast ein Viertel des Umsatzes |
| Aktive ETFs ausblenden? | Nein. Sie stehen im Register; in die Tabellen kommen sie nur mit genug Umsatz. | 183 ETFs, 5 % des Vermögens |
| Rendite und Duration zurückholen? | Ja, aber nur automatisch: Anfrage an die fünf größten Anbieter. | die beiden Zahlen, die Leser zuerst suchen |
| Ältere Kurse kaufen oder wachsen lassen? | Wachsen lassen; nach einigen Monaten neu entscheiden. | – |

---

## Risiken

- **Rechte.** Für ETF-Liste und Monatsstatistik habe ich keine Nutzungsbedingungen gefunden. In den Dateien steht nur „Data is provided with the condition of no liability“; der Haftungsausschluss der Seite regelt die Weiterverwendung nicht. Die Erlaubnis für die Kursdaten deckt das nicht ab. Mit dem Push stehen Daten aus beiden Dateien im öffentlichen GitHub-Repo und auf dem Webserver. Ohne Zusage bliebe als Grundlage das EU-Register – dort stehen aber nur abgekürzte Namen, keine Kosten, kein Fondsvermögen.
- **Rendite und Duration fehlen.** Die ETF-Seite ist stark bei Kosten, Handel, Größe und Laufzeit, zeigt aber nicht mehr die Zahl, die Leser zuerst suchen.
- **Fehler in den Quellen werden sichtbar.** Ohne Handpflege korrigiert niemand eine veraltete Kostenangabe der Börsenliste. Gegenmittel: die Quelle dazuschreiben; später ein zweiter automatischer Kostenwert vom Anbieter.
- **Kategorien sind aus Namen abgeleitet.** Ob ein ETF ein Anleihen-ETF ist, entscheidet weitgehend die Börse; Kategorie, Laufzeit und Absicherung bleiben eine Näherung. Gegenmittel: Kennzeichnung, Regeln verbessern.
- **Aufbau der Börsenseiten.** Der Link zur Liste und die Monatsdateien werden aus den Seiten der Börse gelesen. Ändert die Börse den Aufbau, schlägt der Schritt fehl; das Register bleibt dann auf dem letzten Stand, und nach sieben Tagen schlägt die Frische-Prüfung Alarm.
- **Kurzer Kursverlauf.** Ein-Jahres-Werte gibt es frühestens im Herbst 2027, außer mit einer Kurslieferung.
- **Kurse in Fremdwährung.** 36 Anteilsklassen werden an Xetra nicht in Euro gehandelt; ihr Kurs und ihr Tagesumsatz stehen in der Handelswährung. Die ETF-Seite schreibt das Währungszeichen dazu.

---

## Anhang: Felder in `etf-index.json`

Eine Zeile je ETF, damit Git-Unterschiede klein bleiben:

```
[isin, name, anbieter, kuerzel, aktiv, kosten, ausschuettend, nachbildung, fondswaehrung, handelswaehrung, index,
 klasse, kategorie, markt, laufzeit, endjahr, abgesichert, gruppe, erster_handelstag, vermoegen, umsatz12, xlm, pruef]
```

- `kosten` in Prozent pro Jahr laut Börsenliste.
- `ausschuettend` laut Börsenliste; `pruef.ertrag`, wenn der CFI-Code widerspricht (22 ETFs).
- `klasse`: B oder S (siehe Einstufung). `pruef.cfi`, wenn der CFI-Code eine andere Anlageklasse nennt (13 ETFs).
- `kategorie` bis `gruppe` sind abgeleitet.
- `erster_handelstag` laut ESMA FIRDS; fehlt bei einem ETF.
- `handelswaehrung`: Euro, wenn es an Xetra eine Euro-Zeile gibt (872 ETFs), sonst die Währung der einzigen Zeile. Der Kursabruf nimmt nur Kurse in dieser Währung.
- `vermoegen` in Mio. € (Anteilsklasse), `umsatz12` in Mio. € (Xetra-Orderbuch, Monate laut Kopf der Datei), `xlm` in Basispunkten.
