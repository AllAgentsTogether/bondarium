# Einheitliche Anleihen-Angaben

Seit 03.10.2026 (Nutzerentscheid „setze alles um außer die Kopfkarte“). Konzept mit Begründung und Bestandsaufnahme:
`tmp/Bondarium-Konzept-Anleihen-Angaben.docx` (nicht im Repository), Mockup: `tmp/anleihen-mockup/`.

**Grundsatz:** Eine Angabe – ein Name, eine Schreibweise, eine Quelle, eine Rechenregel. Jede Stelle, die Anleihen zeigt (Seiten,
Handy-Karten, PDFs, CSV, Kalender, E-Mails), nimmt Bezeichnung und Format aus demselben Katalog.

## Wo die Regeln stehen

| Datei | Inhalt |
|---|---|
| `felder.js` | **Katalog** (zwischen `/*KATALOG*/` und `/*KATALOG-ENDE*/`, reines JSON): Bezeichnungen je Angabe (`kurz` = Tabellenkopf und Handy-Beschriftung, `unter` = zweite Kopfzeile, `lang` = Steckbrief und Vergleich, `title` = Erklärung beim Überfahren), Gesamtliste der Spalten (`reihe`), Art, Bonitätsspannen, Ländernamen der Staaten, Rechtsform-Regel, Ausnahmen für sperrige Emittentennamen. Dazu die Schreibweisen (`MC.felder.pct`, `kupon`, `kurs`, `pkt`, `restlaufzeit`, `volumen`, `stueckelung`, `betrag`, `bonitaet`), Kurzname und Titel (`kurzName`, `titel`) und die **Standardtabelle** (`MC.felder.tabelle`, `sortierbar`). |
| `base.css` | Stile der Standardtabelle `table.kpis.atab` und ihre Handy-Karten bis 640 px |
| `scripts/_common.py` | dieselben Regeln für Python: `felder_katalog()` liest den Katalog aus `felder.js`, `kurz_name`, `lesbar`, `kupon_text`, `kurs_text`, `pct_text`, `pkt_text`, `restlaufzeit_text`, `volumen_text`, `stueckelung_text`, `titel_text`, `stamm_felder` |
| `scripts/statische_tabellen.py` | Standardtabelle als festes HTML beim Veröffentlichen (`std_kopf`, `std_zeile`, `std_tabelle`) – Ranglisten, Top 30 nach Kupon |
| `scripts/pruefen.py` | bricht das Veröffentlichen ab, wenn eine Anleihen-Tabelle ihre Spalten nicht in der Reihenfolge der Gesamtliste zeigt oder einen Spaltenkopf anders nennt als der Katalog |

## Kurzname und Titel

- **Kurzname** (erste Spalte „Anleihe“): Staat (Art 0, Land ≠ INT) → Ländername aus dem Katalog („Deutschland“, „USA“,
  „Großbritannien“); sonst der Emittent in lesbarer Schreibung ohne Rechtsform („Mercedes-Benz Group“, „Volkswagen Leasing“);
  sperrige Registernamen über die Ausnahmen („Kreditanstalt für Wiederaufbau KfW“ → „KfW“). Ohne Emittent: Registername.
- **Titel**: Kurzname, Kupon, Fälligkeitsjahr – „Italien 3,50 % 2030“, „DZ Bank variabel 2027“, „Nestlé Finance International Nullkupon 2033“.
  Für Legenden, Listen, Kalender, Auswahlfelder, E-Mails und den Rechner.
- Berechnet wird der Kurzname in JavaScript (`MC.felder.kurzName`) und Python (`_common.kurz_name`) nach derselben Regel aus demselben
  Katalog; PHP nimmt ihn fertig aus `newsletter/anleihen.json`. Im Datenlauf stehen Kurzname und Bonität in den Zeilen der Ranglisten
  (`kurz`, `bon`) und für die übrigen Seiten in `anleihen-auswahl.json` (`scripts/suchindex.py`).
- Neue Ausnahme: im Katalog unter `ausnahmen` eintragen (Schlüssel = Emittent in lesbarer Schreibung, wie in `suchindex.json`).

## Tabellenstandard

**Fünf Kernspalten in fester Reihenfolge:** Anleihe (darunter ISIN · Art · Währung) · Rendite · Kupon · Restlaufzeit (darunter
Fälligkeit) · Kurs. Zusatzspalten stehen dahinter, immer in der Reihenfolge der Gesamtliste (`reihe` im Katalog):
Platz, Anleihe, Rendite, Kupon, lfd. Verzinsung, Restlaufzeit, Duration, Risikoaufschlag, Kurs, Bonität, Kündigung, Stückelung,
Volumen, Handelstage, Seit Hoch, Seit dem Merken, Nächster Zinstermin, Merken. Eine Tabelle darf Spalten weglassen, nie umstellen.

| Tabelle | Spalten |
|---|---|
| Anleihen-Suche | Anleihe · Rendite · Kupon · Restlaufzeit · Kurs · Bonität · Stückelung · Volumen · Merken/Kurzansicht |
| Top-10 (Laufzeit, Länder) | # · Anleihe · Rendite · Kupon · Restlaufzeit · Kurs · Bonität · Stückelung · Volumen · Handelstage (nur automatische Rangliste, fett) · Merken |
| Top 30 nach Kupon | wie Top-10 ohne Handelstage, Kupon fett |
| Langläufer | Anleihe · Rendite · Kupon · Restlaufzeit · Kurs · Seit Hoch · Merken |
| Startseite „Sechs Beispiele“ | Anleihe · Rendite · Kupon (Zinstermin darunter) · Restlaufzeit · Kurs · Bonität · Stückelung · Merken |
| Merkliste | Vergleichen · Anleihe · Rendite · Kupon · Restlaufzeit · Kurs (zum Vortag) · Seit dem Merken · Nächster Zinstermin · Aktionen |
| Vergleich | Zeilen in Langform: Rendite bis Fälligkeit · Kupon · Laufende Verzinsung · Restlaufzeit · Duration · Risikoaufschlag zu Bund · Kurs · Bonität laut EZB · Kündigungsrecht Emittent · Stückelung (Mindestanlage) · Volumen · Zinsen pro Jahr je 1.000 |
| Musterdepots | wie am 03.10.2026 entschieden (Rendite · Kupon/lfd. Verzinsung · Restlaufzeit/Fälligkeit · Duration · Nennwert · Kaufpreis/Kurs · Anteil · Zinsen pro Jahr); Kurs steht dort unter dem Kaufpreis |
| Realzins | Anleihe (Titel) · Realrendite · Bund nominal · Breakeven |

- **Fett** ist nur die Spalte, nach der sortiert oder gerankt ist.
- **PDF = Tabelle**: gleiche Spalten, gleiche Reihenfolge (Merkliste, Musterdepot). **CSV**: Spalten der Tabelle in Langform mit Einheit
  („Rendite bis Fälligkeit in %“), dazu ISIN, Art, Währung, Fälligkeit.
- **Handy**: Karten – Name oben, darunter groß Rendite · Kupon · Restlaufzeit, dann die übrigen Werte; zweite Zeilen mit Vorsatz
  („fällig 15.08.2033“, „zum Vortag +0,12 Pkt.“). Die Suche behält ihre „Sortieren nach“-Chips.
- **E-Mails**: erste Zeile Titel, zweite Zeile „Rendite 3,85 % · Restlaufzeit 4,2 Jahre (fällig 15.08.2033) · Kurs 98,50 %“.

## Schreibweisen

| Angabe | Schreibweise |
|---|---|
| Rendite, lfd. Verzinsung | zwei Stellen, geschütztes Leerzeichen vor % – „3,85 %“ |
| Kupon | zwei Stellen, drei wenn nötig; „variabel“, „Nullkupon“ als Wort (nie „0,00 %“) |
| Kurs | zwei Stellen (drei, wenn die Börse sie liefert), **immer mit %** – „98,50 %“ |
| Veränderungen | mit Vorzeichen und „Pkt.“ – „+0,12 Pkt.“ |
| Fälligkeit, Termine | TT.MM.JJJJ; „vom TT.MM.“ beim alten Kurs; Jahr allein nur im Titel |
| Restlaufzeit, Duration | unter einem Monat Tage, unter einem Jahr Monate, sonst „4,2 Jahre“ |
| Volumen, Umsatz | ab 1 Mrd. in Mrd., darunter Mio., höchstens drei gültige Ziffern, immer mit Währungscode – „1,25 Mrd. EUR“ |
| Stückelung | bis drei Stellen ohne Endnullen, mit Währungscode – „1.000 EUR“, „0,01 EUR“; Langform „Stückelung (Mindestanlage)“ |
| Beträge | zwei Stellen, Währungscode – „9.973,45 EUR“ (nicht „€“) |
| Bonität | „AAA bis A−“, „BBB+ bis BBB−“, „mindestens BBB−“ (laut EZB-Liste) |
| Fehlender Wert | Tabelle „–“ (Grund beim Überfahren), Steckbrief Grund in Worten |

## Steckbrief (anleihe.html)

Kopf (Titel, Registername, Emittent, ISIN/WKN, Merkmal-Schilder) · Kennzahlen **Rendite · Kupon · Restlaufzeit · Kurs** · weitere
Kennzahlen (laufende Verzinsung, Duration/mod. Duration, Risikoaufschlag, zum Vortag) · Merkmale in vier Gruppen (Zins: Kupon, Zinsart,
Zinsrhythmus, Zinstermine, nächster Zinstermin, Stückzinsen je 1.000 · Laufzeit und Rückzahlung · Emittent und Sicherheit · Ausstattung)
· Kursverlauf · Handel mit Handelstagen. Das Rechenbeispiel samt Zahlungsplan je 1.000 ist seit 03.10.2026 auf Nutzerwunsch entfallen.

## Nächster Zinstermin – eine Quelle

Laut Instrumentenliste der Deutschen Börse, sonst geschätzt (Regel in `_common.zinsfrequenz`/`zinsplan`, im Browser `MC.bond.couponDates`
mit den Stammdaten-Feldern). Merkliste, Meldungen und Wochenbrief nehmen ihn aus `newsletter/anleihen.json` (Feld 6, Feld 8 = geschätzt),
an die Seite geliefert als `termine` und `termine_geschaetzt`; Musterdepots, Steckbrief und Vergleich rechnen ihn aus denselben Stammdaten.

## Neue Anleihen-Tabelle bauen

1. Zeilenobjekte bilden (Felder siehe Kopf von `felder.js`), 2. `MC.felder.tabelle(spaltenIds, zeilen, { sort, sortieren: true, rang, ctx })`
in ein `<table class="kpis atab">` schreiben, 3. `MC.felder.sortierbar(table, sort, neuZeichnen)`. Seitenspezifische Spalten über
`opt.extra`. Wird die Tabelle auch vorgerendert, `scripts/statische_tabellen.py` (`std_tabelle`) nutzen.
