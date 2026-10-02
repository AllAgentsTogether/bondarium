# Benutzerbereich „Mein Bondarium“

Stand 01.10.2026. Der Bereich hieß bis 01.10.2026 „Mein Depot“; seit dem Nutzerentscheid von diesem Tag heißt er
„Mein Bondarium“ (Seite und Menü) und hat zwei Reiter nebeneinander: **Merkliste** und **Mein Depot**. Besucher
registrieren sich mit E-Mail-Adresse und Passwort (seit 30.09.2026 abends, vorher Anmeldung per E-Mail-Link) und
merken sich Anleihen. „Mein Depot“ ist ein Musterdepot: gemerkte Anleihen mit einem gedachten Nennwert, darunter
die Zahlungen als Schaubild. Beides liegt auf dem Server und ist auf jedem Gerät da, auf dem man sich anmeldet. Es
ist ein Planspiel, kein Wertpapierdepot: keine echten Bestände, keine Kaufpreise, keine Orders.

## Bausteine

| Datei | Aufgabe |
| --- | --- |
| `konto.html` | Seite „Mein Bondarium“: Anmelden, Registrieren, Passwort vergessen – oder die Reiter „Merkliste“ und „Mein Depot“. Für alle gleich, `noindex`. Lädt `bond.js` für die Zinstermine. |
| `konto.js` | Spricht mit `konto.php` (`MC.konto`, darunter `depot(isin, nennwert)`), zeichnet den Merken-Knopf („Merken“ / „Gemerkt“). Geladen auf `konto.html`, `anleihe.html`, `anleihen-suche.html`. |
| `konto.php` | Schnittstelle auf dem Server (PHP bei STRATO), Antwort immer JSON. |
| `konto-daten/` | Entsteht nur auf dem Server: SQLite-Datei mit zufälligem Namen. Nicht im Repository, nicht im Bau. |
| `pdf.js` | Kleiner PDF-Schreiber im Browser (`MC.pdf`: Helvetica, WinAnsi, Linien, Flächen, SVG-Pfade fürs Logo, Links; A4 hoch oder quer) für den Depot-Auszug. Nur auf `konto.html`. |
| `base.css` | `.merkbtn` (Merken-Knopf). |
| `scripts/nav.py` | Menüpunkt „Mein Bondarium“ (`LINKS`). |
| `rechtliches.html#konto` | Abschnitt der Datenschutzerklärung. |

## Abläufe

**Registrieren.** E-Mail-Adresse und Passwort → `aktion=registrieren` schickt eine E-Mail mit Link (24 Stunden).
Gespeichert wird nur eine offene Registrierung mit dem Hashwert des Passworts; ein Konto gibt es noch nicht. Der Link
führt auf `konto.html#bestaetigen=<Kennwort>`. Dort gibt man das Passwort noch einmal ein (`aktion=bestaetigen`) – erst
dann entsteht das Konto, und man ist angemeldet. Das zweite Eingeben ist Absicht: Wer nur die E-Mail bekommt, das
Passwort aber nicht kennt, kann kein Konto anlegen. So lässt sich niemandem ein Konto mit fremdem Passwort unterschieben.

**Anmelden.** `aktion=anmelden` mit E-Mail und Passwort. Der Browser bekommt zwei Cookies, 90 Tage gültig, bei Nutzung
verlängert: `__Host-bondarium-sitzung` (zufällige Kennung; HttpOnly, Secure, SameSite=Strict) und
`bondarium-angemeldet=1` (für `konto.js` lesbar). Dasselbe Konto gilt auf jedem Gerät.

**Passwort vergessen.** `aktion=vergessen` schickt einen Link (30 Minuten, einmal) auf `konto.html#passwort=<Kennwort>`;
`aktion=passwort-neu` setzt das Passwort, meldet alle Geräte ab und das aktuelle an.

**Angemeldet.** Merken, Entfernen, ins Depot legen (`aktion=depot` mit ISIN und Nennwert; Nennwert 0 nimmt die
Anleihe heraus), Abmelden, Passwort ändern (mit dem aktuellen Passwort; andere Geräte werden abgemeldet, eine E-Mail
weist darauf hin), Konto löschen (mit Passwort). Dazu `aktion=uebernehmen` für eine geteilte Merkliste (siehe unten).

Der Teil hinter `#` eines Links geht nicht an den Server und steht in keinem Log; die Seite nimmt ihn sofort aus der
Adresse. Wer nicht angemeldet ist, löst keine Anfrage an `konto.php` aus: `konto.js` fragt den Stand nur ab, wenn der
Merker `bondarium-angemeldet` da ist. Klickt ein nicht angemeldeter Besucher auf „Merken“, führt der Knopf auf
`konto.html?merken=<ISIN>`; die ISIN geht mit der Anmeldung oder Registrierung mit und steht danach auf der Merkliste. Ist jemand
schon angemeldet, legt `?merken=` nichts von selbst ab (ein fremder Link soll nichts auf die Merkliste setzen können) – die
Seite zeigt dann einen Knopf.

## Reiter „Merkliste“: Tabelle und PDF-Auszug

Die Merkliste ist unverändert die Tabelle vom 30.09.2026 (Nutzerwunsch 01.10.2026: „so wie die aktuell schon
existierende“, ohne Filter). Sie und der PDF-Auszug zeigen dieselben Spalten wie die Anleihen-Suche: Anleihe (Name,
darunter der Registername), Rendite, Kurs, Kupon, Fälligkeit, Restlaufzeit, Art, ISIN, Währung, Volumen, Stückelung;
die Seite dazu „Gemerkt“ und „Entfernen“. Formate und Regeln wie in `anleihen-suche.html` (Rendite ohne Befund und ohne
unplausible Taxe, „?“ bei fraglicher Taxe, „*“ bei Realrendite, „Daten?“ bei Widerspruch im ESMA-Register). Die Tabelle
ist breit; auf schmalen Bildschirmen wischt man quer, am Handy erscheint jede Anleihe als Karte mit allen Werten. Über der
Tabelle stehen Anzahl und Kursdatum, darunter wie auf den übrigen Datenseiten der Aufklapper „Datenquellen und Methodik“
mit dem Daten-Stand („Keine Anlageberatung“ steht in der Fußzeile jeder Seite).

## Reiter „Mein Depot“: Musterdepot und Zahlungen

Seit 01.10.2026 (Nutzerwunsch: „eine Funktion ‚mein depot‘, wo du Anleihen rein legen kannst und den Nennwert
reinschreiben kannst … darunter genau deine Zahlungen grafisch dargestellt“). Oben ein Formular: Anleihe von der
Merkliste wählen, Nennwert eintragen, „Zum Depot hinzufügen“. Darunter die Tabelle (Anleihe, Kurs, Kupon, Fälligkeit,
Nennwert als Eingabefeld, Kurswert, Zinsen pro Jahr, Entfernen) mit Summenzeile.

Begriffe (seit 01.10.2026 abends, Nutzerwunsch: „überprüfe, ob die Begrifflichkeiten professionell sind, und optimiere“):
die Fachwörter der übrigen Website – „Kurswert“ statt „Kaufbetrag heute“, „Kursgewinn“/„Kursverlust“ statt „Rückzahlung +/−“
unter dem Kurswert, „Zinsen pro Jahr“, „Rückzahlung zum Nennwert (100 %)“, „Fremdwährungen“; bei den Knöpfen „hinzufügen“ und
„entfernen“ statt „hineinlegen“ und „herausnehmen“. Auf Rückfrage vom Nutzer bestätigt („ja“): „Musterdepot“ statt
„Beispieldepot“ – auch im Datenschutztext (`rechtliches.html#konto`) – und die Sternchen-Zeile
„* Fremdwährungen werden zur Vereinfachung in Euro umgerechnet“ statt „* Andere Währungen … in EUR …“.

Kurs und Kurswert (Nutzerwunsch 01.10.2026: „in der Anleihe muss auch der aktuelle Kurs stehen. Bei der Rückzahlung
muss die Differenz zwischen Kaufkurs und 100 % Rückzahlung erkenntlich sein“): Als Kaufkurs gilt der Schlusskurs von
heute – das Depot rechnet, als wäre heute der Kauftag; ein eigener Kaufkurs wird nicht gespeichert. Kurswert =
Nennwert × Kurs, ohne Stückzinsen und Gebühren. Der Unterschied zur Rückzahlung zu 100 % (Kursgewinn grün, Kursverlust
orange) steht unter dem Kurswert, in der Summenzeile, im Satz über den Schaubildern und an jedem Rückzahlungsbalken.

Ins Depot kommen nur Anleihen mit festem Kupon oder ohne Kupon (Nutzerentscheid); alles andere steht
ausgegraut mit Grund in der Auswahl (`grund()` in `konto.html`).

Fremdwährungen (seit 01.10.2026 abends, Nutzerwunsch: „jetzt akzeptiere auch andere Währungen und rechne sie dann in
EUR um. Füge ein * hinzu und weise auf Wechselkursrisiken hin. Der Wechselkurs wird hier als ‚fest‘ angenommen“): Der
Nennwert steht in der Währung der Anleihe (so speichert ihn `konto.php` schon immer – am Server ändert sich nichts); hinter
dem Eingabefeld steht das Währungskürzel, darunter der Betrag in Euro. Kurswert, Zinsen und Rückzahlung werden mit dem
Euro-Referenzkurs der EZB in Euro umgerechnet (`wechselkurse.json`, geschrieben von `scripts/update_wechselkurse.py` im
täglichen Datenlauf; rund 30 Währungen, „1 Euro = x“). Der Kurs gilt für die ganze Laufzeit als fest. Das Sternchen
steht nur einmal: am Namen der Anleihe in der Depot-Tabelle (Nutzerwunsch 01.10.2026: „das Sternchen soll nur einmal bei
der Anleihe, die nicht EUR ist, zu sehen sein. Nicht überall!“) – nicht an Beträgen, Summen, Legende oder Schaubild. In der
Einzel-Liste steht zusätzlich der Betrag in der Währung der Anleihe. Unter der Tabelle steht zugeklappt nur die Zeile
„* Fremdwährungen werden zur Vereinfachung in Euro umgerechnet“ (`<details id="kd-fx">`); erst ein Klick zeigt Kurs und
Stichtag, „als fest angenommen“ und das Wechselkursrisiko (`fxHinweis()`). Währungen ohne
EZB-Referenzkurs (auch die alten Euro-Vorgänger wie DEM) und der Fall, dass `wechselkurse.json` fehlt: „kein Wechselkurs
für …“ – die Anleihe bleibt aus dem Schaubild. Zinstermine (seit 02.10.2026): Zahlungen je
Jahr und Zinstage aus den Stammdaten `anleihen/<teil>.json`, Feld 15 (`scripts/update_zinstermine.py`, Instrumentenliste der
Deutschen Börse) – die Seite lädt dafür die Teildatei jeder Depot-Anleihe; ohne Angabe der Börse geschätzt, die Anleihe
steht dann im Hinweis unter den Zinsterminen.

Immer der neueste Kurs (seit 01.10.2026, Nutzerwunsch: „die EZB-Kurse sollen auch immer aktuell sein“): Der Datenlauf um
10 Uhr holt den Kurs des Vortags – die EZB veröffentlicht erst gegen 16 Uhr. Deshalb lädt die Seite `wechselkurse.php`:
Das Skript fragt selbst bei der EZB nach (höchstens alle 30 Minuten, nach einem Fehlschlag nach 5 Minuten, gar nicht mehr,
sobald der Kurs von heute da ist) und legt den Stand in `wechselkurs-daten/kurse.json` ab (Ordner legt das Skript an,
git-ignoriert, nie im Bau). Es nimmt keine Eingaben an und speichert nichts über Besucher; der Browser spricht nur mit
bondarium.de. Antwortet es nicht, nimmt die Seite `wechselkurse.json` aus dem Datenlauf.

Knopf in der Merkliste (seit 01.10.2026, Nutzerwunsch: „in der Merkliste muss es auch einen Button geben, zu meinem Depot
hinzufügen“): In jeder Zeile steht vor dem × ein rundes „+“ (`depotKnopf()`; am Handy ausgeschrieben „Zum Depot
hinzufügen“). Ein Klick legt die Anleihe mit einem Nennwert-Vorschlag ins Depot (`nennVorschlag()`: rund 1.000 in der
Währung der Anleihe, mindestens die Stückelung) und meldet das in der Statuszeile mit dem Verweis „Nennwert ändern“. Liegt
die Anleihe schon im Depot, zeigt der Knopf einen Haken und öffnet „Mein Depot“; lässt sie sich nicht rechnen, ist er
gesperrt und nennt den Grund. Damit die Tabelle so breit bleibt wie bisher (1.180 px), ist die Namensspalte 26 px schmaler
und der Spaltenabstand 1 px kleiner.

Auswahl im Schaubild (seit 01.10.2026, Nutzerwunsch: „bei Zahlungen je Jahr soll die Farbkachel klickbar sein, so dass ich
mir auch nur ein paar Werte aus dem Depot zusammenklicken kann“): Die Legende besteht aus Schaltern (`.kd-wahl`,
`aria-pressed`). Ein Klick blendet eine Anleihe aus oder wieder ein; Satz („Auswahl: 3 von 10 Anleihen“), Schaubild
(Zeitachse bis zur letzten Fälligkeit der Auswahl) und Einzel-Liste zeigen nur die Auswahl, die Tabelle darüber bleibt das
ganze Depot. „Alle zeigen“ setzt zurück. Die Auswahl (`AUS`) gilt nur für diesen Seitenaufruf und wird nirgends gespeichert. Der Nennwert ist eine ganze Zahl von 1 bis 100 Mio.;
liegt er unter der Stückelung oder ist er kein Vielfaches davon, steht ein Hinweis in der Zeile. Ins Depot passen höchstens zehn Anleihen (`MAX_DEPOT` in
`konto.php`, `DEPOT_MAX` in `konto.html`); ist es voll, ist das Formular gesperrt.

Unter der Tabelle die Zahlungen (Fassung vom 01.10.2026 abends, Nutzerwunsch: „max 10 Anleihen ins Depot. Die Zinsen und
die Rückzahlungen von unterschiedlichen Anleihen müssen farblich unterschiedlich sein. Die nächsten 12 Monate sind
uninteressant … 10 Jahre und danach gestrichelt mit dem Hinweis, die nächsten Jahre werden nicht angezeigt. Ganz unten
muss die Summe aus Zinsen und Rückzahlung stehen“): ein Satz mit den Summen, ein Schaubild „Zahlungen je Jahr“ und der
Aufklapper „Zinstermine im Jahr JJJJ“ (seit 02.10.2026, Nutzerwunsch: „nicht alle Zahlungstermine, sondern nur exemplarisch
für das nächste Jahr … nur Zinsen und keine Rückzahlungen … es soll ab Januar anfangen“ – vorher alle Zahlungen bis zur letzten
Fälligkeit; jetzt die Zinstermine des nächsten Kalenderjahrs von Januar bis Dezember mit Summe, ohne Rückzahlungen). Das Schaubild (`jahresbild()`) reicht von heute bis zur
letzten Fälligkeit, höchstens 30 Jahre (`JAHRE_MAX`; Nutzerwunsch vom selben Abend: „das muss dynamisch sein … bis 30
Jahre. So bleibt nicht alles weiß auf der rechten Seite“ – davor erst zehn, dann fest zwanzig Jahre). Bei vielen Jahren
werden die Spalten schmal; die Zahlen über den Balken weichen dann nach oben aus, statt sich zu überdecken. Es
hat drei Reihen mit eigener Höhe, in dieser
Reihenfolge (Nutzerwunsch: „ganz oben sollen die Zinsen stehen, dann die 100 % Rückzahlung des Nennwertes und dann in
der letzten Zeile alle Rückzahlungen, also Zinsen plus 100 % Nennwert“): Zinsen (gestapelt, der Kupon-Punkt markiert
die nächste Zahlung), Rückzahlung zum Nennwert (100 %) mit der Differenz zum Kurswert darunter, und „Alle
Zahlungen: Zinsen und Rückzahlung“. Eine Reihe mit der fortlaufend aufsummierten Rückzahlung und eine dunkle Zahlenzeile
gab es am 01.10.2026 kurz; beide sind durch die dritte Reihe ersetzt. Jede Anleihe hat ihre Farbe (`FARBEN`, in der Reihenfolge des Hineinlegens) – in der Tabelle, in der Legende, in den Balken und in der Einzel-Liste; fährt man über
ein Segment, nennt es Anleihe und Betrag. Seit 01.10.2026 abends sind es die Farben der Website (Nutzerwunsch: „passe die
Farben an die Website an“): Tiefgrün, Tinte, Orange, danach Abstufungen aus denselben Familien. Das Orange (#DD803D) ist
eine Spur heller als `--orange`, damit es sich bei Rot-Grün-Schwäche vom Tiefgrün abhebt; die ersten sechs Farben bestehen
die Prüfung über alle Paare, sieben bis zehn liegen enger beieinander (Zahlen, Legende und Liste helfen). Jedes zweite Jahr
ist ganz leicht hinterlegt, damit man sieht, wo ein neues Jahr anfängt. Läuft das Depot länger als 30 Jahre, folgt eine gestrichelte Spalte, und unter dem Bild steht, welche Jahre fehlen und was dort noch kommt. Ein Schaubild der nächsten zwölf Monate
gab es am 01.10.2026 kurz; es ist auf Nutzerwunsch entfernt. Gerechnet wird wie im Steckbrief:
Zinstermine an den Zinstagen laut Deutscher Börse, sonst geschätzt vom Fälligkeitstag rückwärts (`MC.bond.couponDates`);
Zinsen je Termin = Nennwert × Kupon ÷ Termine im Jahr; Rückzahlung zum Nennwert; vor Steuern und Kosten, ohne
vorzeitige Kündigung. Die Schaubilder zeichnen sich in der sichtbaren Breite (am Handy breiter als der Bildschirm,
zum Wischen) und deshalb erst, wenn der Reiter offen ist. `konto.html#depot` öffnet den Reiter direkt.

## Merkliste teilen (PDF)

Über der Tabelle stehen „Merkliste teilen“ und „Als PDF speichern“. „Merkliste teilen“ öffnet das Teilen-Menü des Geräts (Web
Share API mit Datei – Handy, Tablet, Safari); wo der Browser keine Dateien teilen kann, wird das PDF heruntergeladen.
Nutzerentscheid: nichts Persönliches im PDF (kein Name, keine E-Mail-Adresse), und das PDF geht nicht über den Server.
Dateiname `Bondarium-Merkliste-JJJJ-MM-TT.pdf`. Das Musterdepot hat sein eigenes PDF (siehe unten).

**Geteilte Merkliste übernehmen** (seit 01.10.2026, Nutzerwunsch: „im geteilten Dokument soll stehen: in meine
Merkliste übernehmen … eine andere Person soll diese Merkliste in ihre Merkliste bei Bondarium übernehmen können“).
Unten links auf der letzten Seite des PDFs, über den Hinweisen, steht der grüne Knopf „In meine Merkliste übernehmen“ –
ohne erklärenden Text (Nutzerwunsch 01.10.2026, vorher oben unter der Überschrift mit zwei Zeilen Erklärung). Er führt auf
`konto.html#liste=ISIN,ISIN,…` – die ISINs stehen hinter „#“, gehen beim Öffnen also nicht an den Server, und die Seite
nimmt sie sofort aus der Adresse. Die Seite zeigt den Kasten „Geteilte Merkliste“ mit den Anleihen und fragt nach;
nichts wird von selbst übernommen (ein fremder Link soll nichts auf die Merkliste setzen können). Erst der Klick ruft
`aktion=uebernehmen` (`MC.konto.uebernehmen(isins)`): übernommen wird, was Bondarium kennt und noch nicht gemerkt ist,
bis die Merkliste voll ist (200); die Antwort nennt `neu` und `uebrig`. Wer nicht angemeldet ist, meldet sich erst an –
die Liste bleibt so lange im Speicher der Seite (kein Cookie, kein Browser-Speicher); nach einer neuen Registrierung
muss der Knopf im PDF noch einmal geklickt werden. Gespeichert wird nichts Neues: nur ISINs auf der Merkliste des
Empfängers, wie beim Merken. Wer mit wem teilt, erfährt der Server nicht.

Gestaltung schlicht: A4 hochkant, Helvetica, grünes Band mit dem Logo der Website (Bildzeichen „Orbit“ und
Wortmarke als Vektor, die Wortmarke aus der Kopfzeile der Seite gelesen), „Merkliste“ mit Datum, Anzahl und Kursstand,
die Tabelle in der gewählten Sortierung (Name mit Link auf den Steckbrief). Damit alle Angaben der Suche hochkant passen, stehen
je zwei übereinander: Name über ISIN · Registername, Fälligkeit über Restlaufzeit, Art über Währung, Volumen über Stückelung
(Nutzerwunsch; kurz vorher war der Auszug quer mit elf Spalten). Unten Erklärungen, „Keine Anlageberatung“ und
die Seitenzahl. Eine Fassung im Design der Startseite (Kacheln, Karte, eingebettete Manrope) war kurz live und ist auf
Wunsch des Nutzers wieder entfernt (Commit 684be7e).

## Musterdepot teilen (PDF)

Seit 02.10.2026 (Nutzerentscheid nach PDF-Mockup): Im Reiter „Mein Depot“ steht zwischen Formular und Tabelle dieselbe Leiste
wie bei der Merkliste – links Anzahl und Kursstand, rechts „Musterdepot teilen“ und „Als PDF speichern“ (gemeinsame Funktion
`teilen(nurSpeichern, art)`, eigene Statuszeile `#kd-teilen-status`). `musterPdf()` baut das PDF im Browser, es geht nicht
über den Server und enthält nichts Persönliches. Inhalt wie der Reiter: Tabelle (Anleihe mit ISIN · Registername, Kurs,
Kupon, Fälligkeit mit Restlaufzeit, Nennwert in der Währung der Anleihe mit Euro-Betrag darunter, Kurswert mit
Kursgewinn/-verlust, Zinsen pro Jahr) und Summe, der Satz zu Zinsen und Rückzahlung, „Zahlungen pro Jahr“ und die
Zinstermine des nächsten Kalenderjahrs. Statt des farbigen Schaubilds steht eine Jahrestabelle mit Balken (Zinsen grün,
Rückzahlung Tinte; jedes zweite Jahr hinterlegt) – auch schwarz-weiß gedruckt lesbar. Immer das ganze Depot, auch wenn im
Schaubild Anleihen ausgeblendet sind. Fremdwährungen: Sternchen am Namen, der EZB-Kurs einmal in den Hinweisen unten. Lange
Depots laufen auf eine zweite Seite weiter. Dateiname `Bondarium-Musterdepot-JJJJ-MM-TT.pdf`.

Euro-Zeichen mitten im Text: macOS-Vorschau (PDFKit) kennt für die Standardschrift Helvetica keine Breite des „€“ und
zeichnet es breiter, der folgende Text liefe hinein. `tx()` setzt deshalb jedes Stück einzeln und lässt hinter „€“ ein
Viertel Geviert Luft. Rechtsbündige Beträge sind nicht betroffen.

## Zum Depot hinzufügen im Steckbrief

Seit 02.10.2026 (Nutzerentscheid nach PDF-Mockup): In `anleihe.html` steht neben „Merken“ der Knopf „Zum Depot hinzufügen“
(Form wie `.merkbtn`, Funktion `depotFeld()`). Er öffnet ein kleines Feld mit dem Nennwert – vorgeschlagen ist der Betrag aus
dem Rechenbeispiel, liegt die Anleihe schon im Depot, ihr Nennwert. Gespeichert wird über `MC.konto.depot(isin, nennwert)`
wie in Mein Depot; die Merkliste bleibt unverändert. Danach zeigt der Knopf „Im Depot“, darunter „Liegt mit … in deinem
Musterdepot · Mein Depot öffnen“; ein neuer Klick ändert den Nennwert oder nimmt die Anleihe heraus. Dieselbe Regel wie
`grund()` in `konto.html`: ohne Fälligkeit, nach der Fälligkeit, mit variablem Zins oder ohne Kupon ist der Knopf gesperrt und
nennt den Grund; bei Fremdwährungen prüft das Feld beim Öffnen, ob es einen EZB-Kurs gibt. Ist das Depot voll, sagt das Feld
es. Nicht angemeldet führt der Knopf auf `konto.html?merken=<ISIN>&depot=1`: Nach dem Anmelden steht die Anleihe auf der
Merkliste, „Mein Depot“ ist offen und die Anleihe im Formular ausgewählt (hinzugefügt wird erst mit dem Klick).

## Was gespeichert wird

SQLite-Datei `konto-daten/konto-<zufällig>.sqlite` (Fassung 3):

| Tabelle | Inhalt | Löschung |
| --- | --- | --- |
| `nutzer` | E-Mail-Adresse, Hashwert des Passworts, angelegt am, zuletzt angemeldet | „Konto löschen“ sofort; nach zwei Jahren ohne Anmeldung |
| `favoriten` | ISIN und Zeitpunkt je Nutzer, höchstens 200 | „Entfernen“, mit dem Konto |
| `depot` | Musterdepot (seit 01.10.2026, Fassung 3): ISIN, gedachter Nennwert (ganze Zahl) und Zeitpunkt je Nutzer, höchstens 10 | „Entfernen“, mit dem Konto |
| `links` | offene Registrierungen (Adresse, Hashwert des Passworts, vorgemerkte ISIN) und Links „Passwort vergessen“; jeweils Hashwert des Link-Kennworts und Ablauf | beim Einlösen; sonst nach Ablauf |
| `sitzungen` | Hashwert des Cookies, Ablauf | Abmelden, Passwortwechsel; nach Ablauf |
| `zaehler` | verschlüsselte Hashwerte von Adresse und IP-Adresse: verschickte E-Mails, falsche Passwörter | nach 24 Stunden |
| `meta` | Schlüssel für diese Hashwerte, Zeitpunkt des letzten Aufräumens, Vergleichs-Hashwert | – |

Passwörter, Link-Kennwörter und Cookies stehen nie im Klartext in der Datei. Passwörter: Argon2id, wo PHP es kann,
sonst bcrypt (Kosten 12); beim Anmelden wird ein älterer Hashwert auf das aktuelle Verfahren gehoben. „Nach Ablauf“
heißt: beim nächsten Aufräumen. Es läuft höchstens einmal je Stunde bei jeder Anfrage, die die Datenbank öffnet – auch
bei der Nach-Deploy-Prüfung des Workflows, also mindestens einmal je Werktag.

Konten aus der ersten Fassung (Anmeldung per Link, 30.09.2026 nachmittags) haben kein Passwort; „Passwort vergessen“
setzt eines.

Ändert sich etwas an diesen Daten oder an den Cookies: erst den Betreiber fragen, dann `rechtliches.html#konto` mitziehen.

## Schutz

- Der Ordner `konto-daten/` wird nie ausgeliefert: Regel in der `.htaccess` des Stammordners (vor allen
  Weiterleitungen, auf beiden Domains), eigene `.htaccess` im Ordner (legt `konto.php` an), Sperre für `*.sqlite`,
  zufälliger Dateiname. Der Workflow prüft nach jedem Deploy, dass der Ordner mit 403 antwortet.
- Änderungen nur per POST mit dem Kopf `X-Requested-With: bondarium-konto`; ein fremder Ursprung wird abgewiesen;
  das Cookie ist SameSite=Strict. Passwörter gehen nur im POST-Körper über HTTPS, nie in einer Adresse.
- Passwort: mindestens 10 Zeichen, mindestens fünf verschiedene Zeichen, keine sehr häufigen Passwörter
  (`PW_HAEUFIG`), nicht die eigene Adresse. Keine Pflicht zu Sonderzeichen – Länge zählt.
- Falsche Passwörter (`LOGIN_GRENZEN`): je Adresse und IP-Adresse zusammen 5 in 15 Minuten, je Adresse 30 je Stunde
  und 100 am Tag, je IP-Adresse 30 in 15 Minuten und 200 am Tag. Die enge Grenze hängt an Adresse *und* IP-Adresse,
  damit ein Angreifer den Inhaber nicht aussperren kann.
- Die Antworten verraten nicht, ob es zu einer Adresse ein Konto gibt: Anmelden meldet immer „E-Mail-Adresse oder
  Passwort stimmen nicht“ und rechnet auch ohne Konto einen Hashwert; Registrieren und „Passwort vergessen“ antworten
  immer gleich und schicken in beiden Fällen eine E-Mail (mit passendem Inhalt).
- Verschickte E-Mails (`GRENZEN`): je Adresse 3 in 15 Minuten und 8 am Tag, je IP-Adresse 10 und 30, insgesamt 60 je
  Stunde und 300 am Tag. Dazu ein Honigtopf-Feld. Kein Captcha, keine fremden Dienste.
- Der Deploy fasst `konto-daten/` nicht an (steht nicht im Manifest). Eine Sicherung gibt es nur über die
  Webspace-Sicherung von STRATO.

## E-Mail-Versand

`mail()` von PHP, Absender `info@bondarium.com` – wie das Kontaktformular. Vier E-Mails: Adresse bestätigen, „es gibt
schon ein Konto“, neues Passwort setzen (bzw. „kein Konto zu dieser Adresse“), Passwort geändert. Für beide Domains
gilt DMARC `p=reject`; ein SPF-Eintrag fehlt (Stand 30.09.2026). Fremde Postfächer (Gmail, iCloud, GMX …) nehmen die
E-Mail nur an, wenn STRATO sie für die Domain signiert (DKIM) oder ein SPF-Eintrag den Versand erlaubt. Kommt die
E-Mail nicht an: bei STRATO im Kundenbereich unter Domains → DNS den SPF-Eintrag einschalten (STRATO-Standard,
`v=spf1 redirect=smtp.rzone.de`), für `bondarium.com`. Ohne ankommende E-Mail kann sich niemand registrieren.

## Filter der Merkliste (seit 02.10.2026)

Über der Tabelle der Merkliste stehen der Grundfilter-Schalter und dieselbe Filterleiste wie in der Anleihen-Suche (Art, Land,
Währung, Restlaufzeit, Rendite, Kupon, Bonität; hinter „Weitere Filter“: Zinsart, Kündigung, Volumen, Mindestanlage, Datenprüfung).
Beide Seiten nutzen `filter.js` (`MC.anleihenFilter`) und `filter.css` – Filter, Stufen, Texte und die sechs Grundregeln stehen nur
dort; wer einen Filter ändert, ändert ihn für Suche und Merkliste. `konto.html` baut je gemerkter Anleihe eine Zeile im Format des
Suchindex (`mfZeile`: aus `suchindex.json`, sonst aus den Stammdaten `anleihen/<teil>.json`, dann ohne Rendite) und lässt
`MF.auswerten` die Treffer und die Zahlen je Option bestimmen. Gefiltert wird nur die Tabelle; „Merkliste teilen“ und „Als PDF
speichern“ nehmen die ganze Merkliste. Die Auswahl gilt für den Seitenaufruf und wird nicht gespeichert (keine Adresse, kein
Browser-Speicher). Mit gesetztem Filter heißt die Statuszeile „3 von 13 Anleihen auf deiner Merkliste passen zur Auswahl“.

## Lokal testen

Lokal braucht es PHP (`brew install php`). Der Python-Server der Vorschau führt kein PHP aus.

```bash
php -S 127.0.0.1:8090
```

Unter dem PHP-eigenen Server gilt der lokale Ursprung, die Cookies kommen ohne „Secure“, und die E-Mail landet in
`konto-daten/lokal-mail.txt` statt im Versand. Der Ordner `konto-daten/` ist git-ignoriert.
