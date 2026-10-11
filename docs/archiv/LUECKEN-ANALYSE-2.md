# Lückenanalyse 2 — was nach der Einordnung noch fehlt

Stand: 09.09.2026 · Grundlage: Dateistand nach Commit e87cec8 (Einordnung, Aktien gegen Anleihen, Realzins, Zinskurve sind drin – siehe `EINORDNUNG.md`). Geprüft: alle 18 Seiten, sechs JSONs, Pipeline, `LUECKEN-ANALYSE.md`.

Sortierung: **Nutzen für die Zielgruppe (langfristig ETF + Anleihen, Bewertung erkennen, Historie) geteilt durch Aufwand**, unter Berücksichtigung dessen, was jetzt schon an Daten und Helfern da ist. Nummern in Klammern = Punkt der ersten Liste.

---

## Stufe 1 · Sofort: Stunden, keine neuen Datenquellen

**1. Impressum ausfüllen (E4)** – die fünf Platzhalter in `rechtliches.html` stehen noch drin, die Seite ist auf `index, follow`. Rechtlich zwingend (§ 5 DDG), kann nur der Betreiber. Aufwand: 10 Minuten.

**2. Aktien-Teil entscheiden (E2)** – `verlierer.html` (Einzelaktien, eingefroren seit 18.08.2026) hängt weiter unter „Aktien“ in der Navigation aller Seiten und in den Querverweisen von Bewertung und Krisen; `update_verlierer.py` liegt noch in der Pipeline (Workflow-Schritt seit 08/2026 abgeschaltet, nur als Kommentar). Widerspricht der ETF-Positionierung und dem Aktualitätsversprechen. Entfernen (mit 301 auf die Startseite) oder als Lehrstück „Einzelaktien-Risiko verschwindet im Index“ umwidmen – Entscheidung steht aus. Aufwand entfernen: 1 Stunde.

**3. Marktlage-Tabelle „Wo stehen wir?“ (B1) + Wendepunkt-Vergleich (B2)** – alle Perzentile und Einstufungen werden jetzt berechnet, aber auf vier Seiten verteilt. Eine Tabelle auf der Startseite (Kennzahl · aktuell · Ø · Spanne · Perzentil · Einstufung) macht daraus die Synthese; direkt daneben „heute vs. 1929 / 1966 / 1999 / 2007 / 2021“ mit Shiller-KGV, Zins, Realzins, Risikoprämie (alles in `data.json`). Größter verbleibender Hebel für Ziel 2 und 3 bei minimalem Aufwand. Aufwand: halber Tag.

**4. Einordnung auf die restlichen Datenseiten bringen (neu)** – die Regel gilt bisher nur auf Startseite, Bewertung, Zinsen. Fehlt auf: VIX-Seite (Perzentil seit 1990 – Daten da), Fear & Greed (12 Monate), AAII (Saldo gegen Langfrist-Ø seit 1987 – Ø liegt in `sentiment.json`), Anleihen weltweit (Perzentil je Land seit 1970 – Jahresreihen sind in `renditen.html` eingebettet), Übersichtsseiten Börsenhistorie/Marktsentiment (E5: je Kachel aktuelle Einstufung statt nur Linktext). Konsistenz: eine Regel, überall. Aufwand: 1 Tag.

**5. Abstand zum Allzeithoch / aktueller Drawdown (B4)** – `data.json` hat die Jahresspannen; „−1,0 % vom Hoch (7.799 am …)“ auf Krisen-Seite und Startseite plus „wie oft war der Markt innerhalb von 5 % vom Hoch?“. Aufwand: 2 Stunden.

**6. Anleihen-ETFs im Steuerkapitel (C7)** – Teilfreistellung 0 % (15 % Mischfonds ab 25 % Aktienquote), Vorabpauschale bei Anleihen-ETFs, Geldmarkt-ETFs, Zinsen/Ausschüttungen. Reiner Text, aber für die Zielgruppe direkt relevant. Aufwand: 2 Stunden.

**7. Forward-KGV aufräumen (E3)** – `valuations.json` führt `forwardPE: 19.0`, der Abruf (Yardeni) wurde 09/2026 entfernt: das Feld veraltet unbemerkt und wird nirgends gezeigt. Entweder streichen oder eine Quelle anbinden (z. B. multpl „Forward P/E“ existiert nicht frei – S&P/Factset-Zahlen nur via Factsheets). Aufwand: 30 Minuten (streichen).

---

## Stufe 2 · Der Kern für „langfristig“: ein Datenimport, dann drei Seiten

Gemeinsame Basis: die Shiller-Monatsdaten seit 1871 (Kurs, Dividende, Gewinne, CPI – Excel von Yale, einmalig importieren, jährlich per Pipeline nachziehen) und eine Anleihen-Gesamtrendite, die sich aus der 10-J-Rendite (bereits in `data.json`) nach dem Standardverfahren rekonstruieren lässt. Mit dieser Basis fallen 8–11 fast gemeinsam ab.

**8. Reale Gesamtrendite (B5)** – Krisen-Chart und -Tabelle sind nominal ohne Dividenden. Umschalter nominal / real / Total Return real; die Tabellenspalte „Erholung“ in Total-Return-Sicht (nach 1929 statt 25 Jahre deutlich kürzer; 1966–1982 real −2/3 sichtbar). Das ist die Lehre, die die Seite verspricht. Aufwand: 1 Tag nach Import.

**9. Rollierende Renditen nach Haltedauer (B6)** – schlechteste / mittlere / beste reale Rendite über 1, 5, 10, 15, 20, 30 Jahre seit 1928; ab welcher Haltedauer gab es keinen realen Verlust; und die Verteilung der 10-Jahres-Renditen **nach Startbewertung** (günstig / fair / teuer nach der neuen Einstufung) – verbindet Ziel 1 mit Ziel 2 und macht die Einstufung überprüfbar. Aufwand: 1 Tag.

**10. Aktien-/Anleihen-Quote (D1)** – die erste Entscheidung der Zielgruppe kommt nirgends vor. Neue Seite unter „Optimierung“: 100/0, 80/20, 60/40, 40/60 historisch (Rendite, größter Verlust, Erholungsdauer, Anteil negativer 5-Jahres-Fenster), Rebalancing zwischen den Anlageklassen, Wahl nach Horizont und Risikotragfähigkeit. Aufwand: 1–2 Tage.

**11. Anleihen in Aktienkrisen als Zahl (C6)** – Zinsen-Seite beschreibt die Reaktion nur im Text; mit der Anleihen-Gesamtrendite: 60/40-Ergebnis je Krise und rollierende Aktien-Anleihen-Korrelation (positiv 1970er/2022, negativ 2000–2020). Aufwand: halber Tag, fällt mit 10 ab.

**12. Leitfaden „So nutzt man diese Seite als Langfristanleger“ (D2 + A5-Rest)** – die Seite sagt überall „kein Timing-Signal“, erklärt aber nie, wozu die Einstufung dann taugt: Renditeerwartung ableiten (implizierte Rendite aus dem Streudiagramm steht schon im Chart, gehört in die Einordnungs-Box), Rebalancing-Bänder, Nachkaufregel in Angstphasen, Quote am Horizont ausrichten. Nach 8–10 mit Zahlen belegbar. Aufwand: 1 Tag Text.

---

## Stufe 3 · Anleihen als Anlageklasse vervollständigen (FRED/Bundesbank-Reihen, Pipeline)

**13. Duration und Zinsänderungsrisiko (C3)** – was ±1 Prozentpunkt Zins mit dem Kurs eines Anleihen-ETFs je Laufzeit macht (Tabelle Geldmarkt / 1–3 / 3–7 / 7–10 / 15–30 Jahre), 2022 als Beleg, Duration aus den iShares-Factsheets der Anleihen-ETFs (dieselbe PDF-Routine, die die Pipeline schon für die Aktien-ETFs nutzt). Ohne das können Anleihen-Anleger die Zinsen-Seiten nicht in eine Entscheidung übersetzen. Aufwand: 1 Tag.

**14. Euro-Perspektive (C5)** – Bund-Kachel auf der Startseite (Daten in `renditen.json` vorhanden: Tageswert + Jahresreihe seit 1970 → Perzentil sofort möglich), deutscher Realzins (Destatis-VPI via FRED `DEUCPIALLMINMEI`), EZB-Leitzins, EUR/USD (FRED `DEXUSEU`) mit dem Hinweis, dass MSCI-World-ETFs zu ~70 % in USD notieren – „Währungsrisiko“ kommt auf der ganzen Website nicht vor. Aufwand: 1–2 Tage.

**15. Kreditaufschläge (C4)** – IG- und HY-Spread (FRED `BAMLC0A0CM`, `BAMLH0A0HYM2`, seit 1997) mit Perzentil: die Bewertung von Unternehmensanleihen, heute nur als F&G-Teilindikator sichtbar. Aufwand: halber Tag (Pipeline + Abschnitt auf Anleihen-Seite).

**16. Inflation sichtbar machen (B8)** – die Jahresreihe seit 1928 liegt seit gestern in `data.json`, wird aber nur als Linie im Realzins-Chart gezeigt. Kleiner Abschnitt mit Einordnung (aktuelle Rate 3,4 % im Perzentil), Monatsreihe der letzten 20 Jahre, Vergleich USA/Deutschland. Aufwand: 2 Stunden.

---

## Stufe 4 · Bewertung verbreitern (Wochen, Quellenlage teils offen)

**17. MSCI-Historien (A3 + E1)** – die drei Bausteine des Einkaufszettels haben weiter keine Bewertungshistorie; Startseite zeigt „KGV 26,1“ ohne Bezug, Europe/EM-CAPE sind Handwerte ohne Datum. Pragmatischer Weg: die iShares-Factsheet-KGVs, die die Pipeline wöchentlich holt, ab jetzt monatlich speichern (eigene Historie wächst), dazu einmalig MSCI-Factsheet-Archive / Siblis prüfen; bis dahin feste Langfrist-Ø als Referenz und Datum an den Handwerten. Aufwand: 1 Tag Pipeline + Recherche.

**18. Weitere Bewertungsmaße (A6)** – Dividendenrendite seit 1871 (kommt mit dem Shiller-Import aus Stufe 2 fast umsonst), Marktkapitalisierung/BIP (FRED), Kurs-Buchwert. Triangulation gegen die CAPE-Schwäche, die die Seite selbst beschreibt. Aufwand: 1 Tag.

**19. Sentiment: „was danach geschah“ (B7)** – die Kontraindikator-These steht auf vier Seiten ohne Beleg. Tabelle „S&P 500 in den 6/12 Monaten nach VIX > 40, AAII-Bären > 50 %, F&G < 20“ – braucht eine S&P-Monatsreihe seit 1990 (Yahoo-Backfill in der Pipeline; `data.json` hat nur Jahreswerte + Spannen). AAII-Chart nebenbei von 52 Wochen auf die vorhandenen fünf Jahre verlängern. Aufwand: 1 Tag.

---

## Stufe 5 · Kleinigkeiten

**20.** Sparplan in Krisen (D3), Glossar mit Ankerlinks (D4), Datenstand-Hinweis an den Handwerten Europe/EM-CAPE, Streichung der toten `fabAktien`-i18n-Reste nach Punkt 2.

---

## Empfohlene Reihenfolge

Stufe 1 komplett (ein Arbeitstag, davon Punkt 1 nur du) → Shiller-Import und Punkte 8–10 (Kern für „langfristig“) → 13 + 14 (macht die Seite für Anleihen-Anleger vollständig) → 12 (Leitfaden, sobald die Zahlen da sind) → Rest nach Gelegenheit. Nach dem nächsten Deploy außerdem einmal die Live-Seite gegen die Kontrollwerte in `EINORDNUNG.md` prüfen.
