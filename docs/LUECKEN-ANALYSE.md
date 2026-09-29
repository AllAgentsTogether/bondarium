# Lückenanalyse — was der Website noch fehlt

Stand: 08.09.2026 · Grundlage: alle 18 HTML-Seiten, site.js, die sechs JSON-Datenstände (data, valuations, renditen, sentiment, einfluss, verlierer), die Python-Pipeline und die vorhandenen Audits (PRUEFBERICHT, TECHNIK-AUDIT, DESIGN-AUDIT, OPTIMIERUNG, GITHUB-REDUKTION).

Maßstab sind die drei Ziele der Seite:
1. Zielgruppe: Menschen, die **langfristig in ETFs und Anleihen** investieren.
2. Der Anleger soll **Über- oder Unterbewertungen erkennen** können.
3. Der **aktuelle Stand soll gegen die Historie** eingeordnet werden, damit (2) bewertbar wird.

Nicht Gegenstand: Technik, Performance, SEO, Design — das ist in den vorhandenen Audits abgedeckt und weitgehend umgesetzt.

---

## Kurzfazit

Die Seite hat ein sehr gutes Fundament: lange Datenreihen (S&P 500 und US-Zinsen seit 1928, Shiller-KGV seit 1928, VIX seit 1990, Anleihen aus acht Ländern seit 1970), saubere Quellenangaben, börsentägliche Aktualisierung, ehrliche Einordnungstexte. Gemessen an den drei Zielen fehlen aber drei Dinge grundsätzlich:

- **Die Übersetzung von Zahl in Einordnung.** Die Seite zeigt Werte und Ø-Linien, sagt aber nirgends explizit „teuer / fair / günstig“ nach einer nachvollziehbaren Regel und nennt nirgends, in welchem Perzentil der eigenen Historie ein Wert heute liegt. Die Startseite zeigt z. B. „KGV 26,1“ für den MSCI World — ohne jeden Vergleichswert.
- **Anleihen als Anlageklasse.** Anleihen kommen nur als Zinsreferenz vor (Rendite 10-jähriger Staatsanleihen). Was ein Anleger, der Anleihen-ETFs hält, wissen muss — Realzins, Laufzeit/Duration, Zinskurve, Kreditaufschläge, Kursreaktion 2022, Euro-Perspektive, Steuern — fehlt vollständig.
- **Aktien gegen Anleihen.** Die Kernfrage der Zielgruppe („Sind Aktien relativ zu Anleihen teuer?“) wird nirgends gestellt. Gewinnrendite (1/CAPE ≈ 2,4 %) und Anleihenrendite (4,8 %) stehen auf verschiedenen Seiten und werden nie gegeneinander gehalten.

Alles Folgende ist mit den bereits vorhandenen Daten oder mit frei verfügbaren FRED-/Shiller-Reihen umsetzbar; wo zusätzliche Daten nötig sind, steht es dabei.

---

## A · Über-/Unterbewertung erkennen

### A1 · Explizites Bewertungsurteil je Kennzahl — HOCH · ✅ umgesetzt 08.09.2026 (siehe EINORDNUNG.md)
**Fehlt:** Eine definierte Regel, die aus dem Zahlenwert eine Einstufung macht (z. B. günstig / eher günstig / fair / eher teuer / teuer), und ihre Anzeige direkt am Wert — auf der Startseite und auf den Analyseseiten.
**Warum:** Ziel 2 ist ohne Urteil nicht erreichbar. Die Seite überlässt es dem Leser, 41,4 gegen die Ø-Linie zu lesen. Das Stimmungsbarometer hat so eine Skala (Angst/Neutral/Gier), die Bewertung und die Zinsen haben keine.
**Vorschlag:** Einstufung relativ zur eigenen Historie (Perzentil oder Abstand zum Ø in Standardabweichungen), Regel auf der Seite offengelegt. Ein Wort, eine Farbe, dazu der Abstand zum langfristigen Ø („+90 % über dem Ø seit 1928“).
**Daten:** vorhanden (capeAnnual in kgv.html, bonds.annual in data.json).

### A2 · Perzentil-Einordnung („teurer als in X % aller Jahre“) — HOCH · ✅ umgesetzt 08.09.2026
**Fehlt:** Für jede Kennzahl mit Historie die Aussage, wo der heutige Wert innerhalb der Verteilung liegt: Shiller-KGV, laufendes KGV, 10J-/30J-Zins, Realzins, VIX, Fear & Greed, AAII-Saldo, Bund-Rendite.
**Warum:** Das ist die kompakteste Antwort auf Ziel 3 und die Grundlage für A1. Die Ø-Linie im Chart ersetzt sie nicht — 41 gegen Ø 17 sieht „hoch“ aus, aber ob das Platz 3 oder Platz 30 von 98 Jahren ist, erfährt man nicht.
**Daten:** vorhanden.

### A3 · Historische Bewertung der MSCI-Bausteine (World, Europe, EM) — HOCH
**Fehlt:** Die Seite sagt selbst: „Bewertungen verschiedener Regionen liest man am besten gegen ihren eigenen historischen Schnitt“ — liefert diesen Schnitt aber nicht. Für MSCI World/Europe/EM gibt es nur die Momentaufnahme (KGV, CAPE), keine Historie, keinen Ø, kein Perzentil. Die Startseiten-Kacheln zeigen „KGV 26,1 / 19,9 / 18,6“ ohne jeden Bezugspunkt.
**Warum:** Die Zielgruppe hält genau diese drei Indizes (Einkaufszettel der Gewichtungs-Seite), bewertet werden kann aber nur der S&P 500.
**Daten:** fehlen — Optionen: MSCI-Factsheet-KGVs monatlich selbst fortschreiben (Pipeline läuft schon wöchentlich über iShares-PDFs), Siblis-CAPE-Historie (World seit 1980er), Barclays/Research-Affiliates-CAPE-Reihen. Mindestens: langjähriger Ø je Index als fester Referenzwert im Text.

### A4 · Aktien gegen Anleihen: Risikoprämie / Gewinnrendite vs. Anleihenrendite — HOCH · ✅ umgesetzt 08.09.2026 (kgv.html#aktien-anleihen, Startseite)
**Fehlt:** Der Vergleich Gewinnrendite (1/CAPE bzw. 1/KGV) gegen die Rendite 10-jähriger Staatsanleihen (nominal und real), als aktueller Wert und als Verlauf seit 1928. Heute: 1/41,4 ≈ 2,4 % Gewinnrendite gegen 4,8 % Treasury — Aktien sind relativ zu Anleihen in etwa so unattraktiv wie zuletzt um 2000. Das steht so nirgends.
**Warum:** Für eine Zielgruppe, die in *beide* Anlageklassen investiert, ist das die zentrale Kennzahl — wichtiger als jeder Einzelwert. Die Zinsen-Seite nennt Zinsen zwar den „Gegenspieler der Bewertung“, zeigt den Vergleich aber nicht.
**Daten:** vorhanden (CAPE, peTTM, bonds.annual, bonds.latest). Für den Realzins wird eine Inflationsreihe gebraucht (siehe C1).

### A5 · Implizierte Folgerendite aus der Regression — MITTEL · teilweise vorhanden
**Korrektur:** Der Scatter markiert bereits „Heute“ und nennt die implizierte Rendite samt ±1σ-Band im Chart. Die Gewinnrendite (1/CAPE ≈ 2,4 %) ist seit 08.09.2026 im Abschnitt „Aktien gegen Anleihen“ enthalten. Offen bleibt nur, die implizierte Rendite auch im Fließtext bzw. in der Einordnungs-Box zu nennen.
**Warum:** Das ist die konkrete Konsequenz der Bewertung — „viel Wachstum ist eingepreist“ wird nirgends beziffert.
**Daten:** vorhanden (Regression wird bereits berechnet).

### A6 · Zweite und dritte Bewertungskennzahl zur Absicherung — MITTEL
**Fehlt:** Die Bewertung hängt am CAPE (dessen Schwächen die Seite selbst gut beschreibt) und am laufenden KGV. Zur Triangulation fehlen: Dividendenrendite des S&P 500 seit 1871 (Shiller-Daten, bereits Quelle der Seite), Forward-KGV (steht mit 19,0 in valuations.json, wird nirgends angezeigt), Marktkapitalisierung/BIP („Buffett-Indikator“), Kurs-Buchwert.
**Warum:** Ein Urteil aus einer Kennzahl ist angreifbar; wenn drei Maße dasselbe sagen, trägt es.
**Daten:** Dividendenrendite und Forward-KGV sofort verfügbar; Buffett-Indikator über FRED (Wilshire/NCBEILQ027S ÷ GDP).

### A7 · Bewertung von Anleihen — HOCH (siehe C1–C3) · Realzins ✅ 08.09.2026
**Fehlt:** Für Anleihen gibt es kein Bewertungsmaß. „4,8 % — ist das viel?“ beantwortet nur der Realzins (nominal minus Inflation bzw. Inflationserwartung) und die Laufzeitprämie. Beides fehlt.

---

## B · Aktueller Stand im Vergleich zur Historie

### B1 · Zusammenfassende Marktlage-Tabelle („Wo stehen wir?“) — HOCH
**Fehlt:** Eine Tabelle oder Kachelzeile, die alle Kennzahlen nebeneinander stellt: Kennzahl · aktuell · Ø historisch · Hoch/Tief · Perzentil · Einstufung. Heute muss der Leser sieben Seiten besuchen und die Einordnung selbst vornehmen.
**Warum:** Das ist die Synthese, die aus dem „Cockpit“ ein Urteil macht. Alle Werte sind bereits in den JSONs.
**Ort:** Startseite (unter den Kacheln) oder eigene Seite „Marktlage“.

### B2 · Vergleich mit früheren Wendepunkten — MITTEL
**Fehlt:** Eine Gegenüberstellung „heute vs. 1929 / 1966 / 1999 / 2007 / 2021“ mit CAPE, 10J-Zins, Realzins, Risikoprämie, VIX, Fear & Greed in einer Tabelle. Die Bewertungsextreme-Tabelle zeigt nur den CAPE, die Zinsen-Tabelle nur Zinsen, die Krisen-Tabelle nur Kurse — nie gemeinsam.
**Warum:** „Nahe dem Allzeithoch von 1999“ wird erst belastbar, wenn man sieht, dass 1999 der Zins bei 5–6 % lag und heute bei 4,8 % — oder dass 2021 der Realzins negativ war und heute positiv.
**Daten:** vorhanden.

### B3 · Startseiten-Kacheln ohne historischen Bezug — HOCH · ✅ umgesetzt 08.09.2026
**Fehlt:** Die drei MSCI-Kacheln zeigen Kurs, Tagesänderung, KGV und eine ~6-Jahres-Sparkline — keinen Ø, kein Perzentil, keine Einstufung. Die Zins-Kacheln haben immerhin den Median seit 1928/1977, aber ohne Aussage, ob 4,8 % über/unter Median „gut“ oder „schlecht“ für Anleger ist. Die Stimmungs-Kacheln haben eine Skala, aber keinen Bezug zur eigenen Historie (z. B. „VIX 14,5 — niedriger als in 75 % aller Monate seit 1990“).
**Vorschlag:** Je Kachel eine Zeile „Historisch: Ø X · heute im N-ten Perzentil“ plus Einstufungswort.

### B4 · Abstand zum Allzeithoch / aktueller Drawdown — MITTEL
**Fehlt:** Die Krisen-Seite zeigt neun historische Drawdowns, aber nicht, wo der Markt *heute* relativ zum Hoch steht (z. B. „−1 % vom Allzeithoch am …“). Dazu die Einordnung: Wie oft war der Markt in 98 Jahren innerhalb von 5 % vom Hoch?
**Daten:** vorhanden (range 2026, latest.close).

### B5 · Reale und Gesamtrendite-Sicht auf die Historie — HOCH
**Fehlt:** Krisen-Chart und -Tabelle sind nominal und ohne Dividenden. Für einen ETF-Anleger (thesaurierend, langfristig) zählt die reale Gesamtrendite: „25 Jahre bis zum Vorkrisenniveau“ nach 1929 sind inkl. Dividenden und Deflation deutlich kürzer; 1966–1982 war nominal seitwärts, real −2/3 (steht im Text, nicht im Chart). Ein Umschalter „nominal / real / Total Return real“ oder eine zweite Kurve würde das Bild grundlegend verändern.
**Warum:** Die Seite wirbt mit „was hundert Jahre Börse lehren“ — die Lehre für Langfristanleger steht aber in der Total-Return-Reihe.
**Daten:** Shiller-Datensatz (Kurs, Dividende, CPI monatlich seit 1871) — bereits Quelle der Seite.

### B6 · Rollierende Renditen nach Haltedauer — HOCH
**Fehlt:** Das wichtigste Argument für „langfristig“: Wie sah die schlechteste / mittlere / beste reale Rendite über 1, 5, 10, 15, 20, 30 Jahre aus, und ab welcher Haltedauer gab es seit 1928 keinen realen Verlust mehr? Dazu: Verteilung der 10-Jahres-Renditen nach Start-Bewertung (günstig / fair / teuer) — die Brücke zwischen Ziel 1 und Ziel 2.
**Daten:** Shiller-Daten wie B5.

### B7 · Sentiment: Historie und „was danach geschah“ — MITTEL
**Fehlt:** Fear & Greed zeigt nur 12 Monate, AAII nur 52 Wochen (die AAII-Historie in sentiment.json reicht fünf Jahre zurück). Vor allem fehlt der Beleg für die Kontraindikator-These, die auf mehreren Sentiment-Seiten steht: eine Tabelle „Rendite des S&P 500 in den 6 / 12 Monaten nach extremer Angst (F&G < 20, VIX > 40, AAII-Bären > 50 %)“ — analog zur Tabelle „Bewertungsextreme und was danach geschah“, die für den CAPE existiert.
**Daten:** VIX seit 1990 und AAII seit 1987 verfügbar; F&G-Historie müsste von einer Drittquelle nachgeladen werden.

### B8 · Inflation als eigene Reihe — MITTEL
**Fehlt:** Inflation ist die Basis für Realzins, reale Renditen und die CAPE-Berechnung — auf der Seite existiert sie nur als 10-Jahres-Sparkline im Faktorenmodell. Eine Langfristreihe (US seit 1928, Deutschland seit 1950/1991) fehlt.
**Daten:** FRED CPIAUCSL (seit 1947), Shiller-CPI (seit 1871), Destatis/Bundesbank.

### B9 · Statischer Kontext am dynamischen Wert — NIEDRIG · ✅ umgesetzt 08.09.2026 (Kontext und Ausblick aus der Einstufung)
**Fehlt:** In der Bewertungsextreme-Tabelle wird der heutige CAPE dynamisch eingesetzt, der Kontexttext „Nahe dem Allzeithoch von 1999“ ist aber fest. Fällt der CAPE auf 30, stimmt die Zeile nicht mehr. Gleiches Muster bei „Offen – historisch folgten …“. Der Kontext sollte aus der Einstufung (A1) erzeugt werden.

---

## C · Anleihen als Anlageklasse (derzeit nur Zinsreferenz)

### C1 · Realzins — HOCH · ✅ umgesetzt 08.09.2026 (zinsen.html#realzins, Startseite)
**Fehlt:** Rendite minus Inflation (bzw. minus Break-even-Inflation aus TIPS/inflationsindexierten Bundesanleihen), aktuell und historisch. Heute: 4,8 % − 3,3 % ≈ +1,5 % real (USA); 2021: negativ. Das ist *die* Bewertungskennzahl für Anleihen und fehlt komplett.
**Daten:** FRED DFII10 (10J-TIPS-Realrendite seit 2003), T10YIE (Break-even), CPI für die lange Reihe.

### C2 · Zinskurve / 2J-10J-Abstand — HOCH · ✅ umgesetzt 08.09.2026 (zinsen.html#zinskurve, Startseite)
**Fehlt:** data.json enthält bereits die 2-Jahres-Rendite (bonds.y2 = 4,39 %), sie wird aber nirgends angezeigt. Die Zinskurve (2J/10J/30J) und ihre Steilheit fehlen — als Rezessionsindikator (inverse Kurve) und als Entscheidungsgrundlage für die Laufzeitwahl (lohnt sich Duration?). Historie 2J–10J seit 1976 via FRED T10Y2Y.
**Daten:** teilweise vorhanden.

### C3 · Laufzeit, Duration und Zinsänderungsrisiko — HOCH
**Fehlt:** Erklärung und Zahlen dazu, was eine Zinsänderung mit dem Kurs eines Anleihen-ETFs macht (Duration), warum 2022 lang laufende Staatsanleihen-ETFs 20–40 % verloren, während Geldmarkt-ETFs stabil blieben. Die Zinsen-Tabelle „Der Anleihenmarkt in den Krisen“ nennt nur Renditeänderungen in Prozentpunkten — nicht, was das für den Kurs bedeutete. Dazu: Geldmarkt vs. kurz / mittel / lang, Staats- vs. Unternehmensanleihen.
**Warum:** Ohne Duration kann die Zielgruppe die Anleihen-Seiten nicht in eine Anlageentscheidung übersetzen.
**Daten:** Kursreihen z. B. FRED-Total-Return-Indizes oder iShares-Factsheets (Duration je ETF).

### C4 · Kreditaufschläge (IG/HY-Spreads) — MITTEL
**Fehlt:** Für Unternehmensanleihen ist der Spread zur Staatsanleihe das Bewertungsmaß — heute vs. Historie seit 1997. Kommt nur indirekt als Teilindikator von Fear & Greed vor.
**Daten:** FRED BAMLC0A0CM (IG), BAMLH0A0HYM2 (HY).

### C5 · Euro-Perspektive: Bund, Euro-Zinsen, Wechselkurs — HOCH
**Fehlt:** Die Startseite zeigt ausschließlich US-Zinsen; die deutsche 10-Jahres-Rendite (3,41 %) steht nur in der Ländertabelle. Für einen deutschen Anleger fehlen: Bund-Rendite und Bund-Historie (Bundesbank seit 1956) mit Ø/Perzentil im Cockpit, EZB-Leitzins, Euro-Realzins, und vor allem das Währungsthema — „EUR/USD“ oder „Währungsrisiko“ kommt – abgesehen von dem Halbsatz „Wechselkurseffekte sind nicht enthalten“ auf der Anleihen-Seite – auf der ganzen Website nicht vor, obwohl MSCI-World-ETFs zu ~70 % in USD notieren und US-Anleihen für Euro-Anleger ein Wechselkursrisiko tragen. Die Kacheln zeigen ETF-Kurse in USD.
**Daten:** Bundesbank (BBK01.WT1010), FRED DEXUSEU / EZB-Referenzkurs.

### C6 · Anleihen in Aktienkrisen: Korrelation und Diversifikationsnutzen — MITTEL
**Fehlt:** Die Zinsen-Seite beschreibt die Anleihenreaktion je Krise im Text. Was fehlt: die Rendite eines Anleihen-Portfolios (bzw. 60/40) in jeder der neun Krisen als Zahl, und die rollierende Aktien-Anleihen-Korrelation (positiv in Inflationsphasen wie 1970er/2022, negativ 2000–2020). Daraus folgt, wann Anleihen als Puffer taugen und wann nicht.

### C7 · Anleihen-ETFs im Steuerkapitel — MITTEL
**Fehlt:** Die Steuer-Seite behandelt nur Aktien-ETFs (Teilfreistellung 30 %). Für die Zielgruppe fehlt: Teilfreistellung 0 % bei Anleihen-ETFs (15 % bei Mischfonds ab 25 % Aktienquote), Vorabpauschale bei Anleihen-ETFs, Behandlung von Zinsen/Ausschüttungen, ggf. Geldmarkt-ETFs.

---

## D · Langfristanleger-Perspektive

### D1 · Aktien-/Anleihen-Quote — HOCH
**Fehlt:** Die Gewichtungs-Seite regelt nur die Regionen *innerhalb* des Aktienanteils. Die Aufteilung zwischen Aktien und Anleihen — für die Zielgruppe die erste und wichtigste Entscheidung — kommt nirgends vor: Risikotragfähigkeit, Anlagehorizont, historische Rendite/Drawdown von 100/0, 80/20, 60/40, 40/60, Rebalancing zwischen den Anlageklassen (Rebalancing wird auf der BIP-Seite nur zwischen Aktien-Bausteinen erwähnt).
**Daten:** Shiller-Aktien + Anleihen-Total-Return (z. B. aus GS10 rekonstruierbar).

### D2 · „Was mache ich mit dem Signal?“ — Leitfaden für Langfristanleger — MITTEL
**Fehlt:** Die Seite sagt an mehreren Stellen „kein Timing-Signal“ bzw. „kein Kaufsignal“ und „keine Anlageberatung“, erklärt aber nie, wozu die Bewertung dann taugt: Renditeerwartung anpassen, Sparrate/Rebalancing-Bänder, Aktienquote am Horizont ausrichten, Nachkaufen in Angstphasen als Regel statt Bauchgefühl. Eine kurze Seite „So liest man diese Seite als Langfristanleger“ würde Ziel 1 und Ziel 2 verbinden.

### D3 · Sparplan und Krisen — NIEDRIG
**Fehlt:** Was passiert mit einem laufenden Sparplan in jeder der neun Krisen (Einstiegskurs-Effekt, Zeit bis zum Break-even)? Das Wort „Sparplan“ kommt nur im FIFO-Kontext vor.

### D4 · Glossar — NIEDRIG
**Fehlt:** CAPE, laufendes KGV, Duration, Rendite vs. Kupon, Realzins, Perzentil, Drawdown, Total Return — werden verstreut erklärt, ein zentrales Glossar mit Ankerlinks fehlt.

---

## E · Konsistenz und Betrieb (hindert die Ziele indirekt)

### E1 · MSCI-Europe/EM-CAPE sind Handwerte — MITTEL
valuations.json: `capeManual: true` mit 22,0 / 16,0. Die Werte werden nicht aktualisiert, auf der Seite steht nur „~22“ und „~16“ ohne Datum. Für eine börsentäglich aktualisierte Bewertungsseite ist das eine unsichtbare Schwachstelle — mindestens ein Datenstand-Hinweis, besser eine automatisierte Quelle.

### E2 · Top-Verlierer-Seite passt nicht zur Zielgruppe — MITTEL
Eine eingefrorene Einzelaktien-Rangliste (Datenstand 18.08.2026, keine Aktualisierung mehr) unter dem Nav-Punkt „Aktien“ widerspricht der ETF-Positionierung und der Aktualitätsversprechung der Seite. Entweder entfernen oder als Lehrstück umwidmen („warum Einzelaktien-Risiko im Index verschwindet“ — z. B. Anteil dieser zehn Werte am S&P 500).

### E3 · Forward-KGV wird geholt, aber nicht gezeigt — NIEDRIG
valuations.json enthält `forwardPE: 19.0`, keine Seite nutzt es (siehe A6).

### E4 · Impressum unvollständig — HOCH (rechtlich, nicht inhaltlich)
rechtliches.html enthält weiterhin die Platzhalter [VORNAME NACHNAME], [STRASSE HAUSNUMMER], [PLZ ORT], [E-MAIL-ADRESSE] (§ 5 DDG). Die Seite steht im Quelltext auf `index, follow`.

### E5 · Übersichtsseiten ohne Zahlen — NIEDRIG
historie.html, marktsentiment.html, optimierung.html sind reine Linklisten. Sie versprechen „zeigen, wo der Markt heute im historischen Vergleich steht“ — könnten je Kachel den aktuellen Wert samt Einstufung (A1) tragen.

---

## Umsetzungsstand

08.09.2026: Punkte A1, A2, B3 (Einstufung/Perzentil, Startseite), A4, C1, C2 (Aktien gegen Anleihen, Realzins, Zinskurve) umgesetzt – Details in `EINORDNUNG.md`. Nebenbei erledigt: B9 (dynamischer Kontext), A7 teilweise (Realzins), B8 teilweise (Inflations-Jahresreihe liegt jetzt in data.json, noch ohne eigene Darstellung).

## Reihenfolge, wenn man mit dem Wirksamsten anfängt

1. **A1 + A2 + B3** — Einstufung und Perzentil an jeden Wert, zuerst auf der Startseite. Nur vorhandene Daten, größter Hebel für Ziel 2 und 3.
2. **A4 + C1 + C2** — Risikoprämie, Realzins, Zinskurve: macht aus „Zinsen“ die Anleihen-Bewertung und stellt Aktien gegen Anleihen. y2 liegt schon in data.json.
3. **B1** — Marktlage-Tabelle als Synthese.
4. **B5 + B6** — reale Gesamtrendite und rollierende Renditen: das Fundament für „langfristig“.
5. **C3 + C5 + D1** — Duration, Euro-Sicht, Aktien-/Anleihen-Quote: macht die Seite für Anleihen-Anleger überhaupt erst nutzbar.
6. **A3** — MSCI-Historien, sobald eine Quelle steht.
7. Rest nach Gelegenheit; E4 unabhängig davon sofort.
