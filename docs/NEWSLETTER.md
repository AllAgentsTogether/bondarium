# Wochenbrief (Newsletter)

Seit 02.10.2026. Ein wöchentlicher Newsletter per E-Mail, der **vollautomatisch** entsteht und verschickt wird – keine
Ausgabe braucht Handarbeit, niemand liest sie vor dem Versand (Vorgabe des Betreibers: „der muss vollautomatisch erstellt
werden“).

Vom Betreiber entschieden (02.10.2026): wöchentlich (erst monatlich gewählt, am selben Tag geändert); nur für Konten, kein
Anmeldefeld für Besucher ohne Konto; das Häkchen im Registrierungsformular ist **nicht vorab gesetzt** (ein vorangekreuztes
Kästchen ist keine wirksame Einwilligung); Versand ohne Freigabe je Ausgabe; die Zahl der Abonnenten steht im täglichen
Besucherbericht.

## Dateien

| Datei | Zweck |
|---|---|
| `scripts/newsletter.py` | baut in jedem Lauf die Ausgabe: `newsletter/ausgabe.json` (Text, HTML, Freigabe), `newsletter/anleihen.json` (Zahlen je Anleihe), `newsletter/seiten.json` (Gedächtnis für „Neue Seiten“, wird committet) |
| `konto.php` | Einwilligung je Konto, Abbestellen, Versand (`aktion=newsletter-senden`) |
| `konto.html`, `konto.js` | Häkchen im Registrierungsformular, Schalter „Wochenbrief per E-Mail“ in der Ansicht „Meldungen und Konto“ (bis 02.10.2026 abends unter der Merkliste), Abmelde-Link `konto.html#nl-ab=<Kennung>` |
| `statistik-bericht.php` | Band „Wochenbrief“ im täglichen Bericht: Abonnenten, An-/Abmeldungen, Konten, letzte Ausgabe |
| `.github/workflows/update-data.yml` | Schritte „Wochenbrief bauen“ und „Wochenbrief verschicken (nur am Versandtag)“ |
| `.github/workflows/newsletter-probe.yml` | von Hand auslösbar: schickt die aktuelle Ausgabe mit Muster-Merkliste an info@bondarium.com |

## Inhalt – woher jeder Abschnitt kommt

| Abschnitt | Quelle (automatisch) |
|---|---|
| Überschrift, Einleitung | Regel: Rendite des Bundeswertpapiers mit rund zehn Jahren Restlaufzeit gegen fünf Börsentage zuvor – ab 0,03 Prozentpunkten „gestiegen“/„gefallen“, sonst „kaum verändert“ |
| Zinsen der Woche | `kurse/bund/` (Tagesrenditen der Bundesbank, rund 2 und rund 10 Jahre), `ezb.json`, `renditen.json` (USA 10 Jahre, nur Stand – Tageswerte der Vorwoche speichert der Datenlauf nicht) |
| Meistgehandelt | `top10-staatsanleihen-laufzeit.json`, `top10-unternehmensanleihen-laufzeit.json`: je drei nach Umsatz |
| Deine Merkliste | Merkliste des Kontos (höchstens 8, zuletzt Gemerktes zuerst): Titel, dann Rendite · Restlaufzeit (fällig …) · Kurs, Veränderung zur Vorwoche in Pkt. und nächster Zinstermin aus `newsletter/anleihen.json` (Schreibweisen wie auf der Website, siehe docs/ANLEIHEN-ANGABEN.md); leere Merkliste: Hinweis auf den Knopf „Merken“ |
| Aus der Akademie | reihum durch das Akademie-Menü in `scripts/nav.py`, eine Seite je Kalenderwoche; Titel = `h1`, Text = `meta description` |
| Neue Seiten | Seiten, die `newsletter/seiten.json` in den letzten sieben Tagen zum ersten Mal gesehen hat; ohne neue Seite entfällt der Abschnitt |

Eine Rubrik mit neuen Funktionen gibt es nicht – dafür gibt es keine automatische Quelle. Der Wochenbrief wirbt für keinen
Anbieter und gibt keine Kaufempfehlung.

## Ablauf

1. **Bauen** – in jedem Lauf des Workflows (auch bei Push-Deploys, weil der Upload fehlende Dateien auf dem Server löscht):
   `python3 scripts/newsletter.py`. Die Ausgabe trägt `versand: true` nur freitags (Zeit Berlin) und nur, wenn die Daten
   vollständig und frisch sind (Kurse höchstens 4 Tage alt, Bundrenditen höchstens 6, EZB-Satz, Listen und Akademie-Seite
   vorhanden). Sonst steht der Grund in `grund`; am Versandtag setzt `warnen` eine E-Mail an den Betreiber in Gang.
2. **Hochladen** – `newsletter/ausgabe.json` und `newsletter/anleihen.json` liegen auf dem Server im Ordner `newsletter/`,
   der per `.htaccess` nie ausgeliefert wird. Der Versandschritt prüft das vor jedem Versand.
3. **Verschicken** – nur im Abruf-Lauf (10 Uhr): Der Workflow ruft `konto.php` mit `aktion=newsletter-senden` und dem
   Schlüssel des Auslösers (`X-Trigger-Key`, GitHub-Secret `TRIGGER_KEY`). `konto.php` schickt die Ausgabe an alle Konten
   mit Newsletter, die diese Kalenderwoche noch keine bekommen haben – höchstens 40 E-Mails je Aufruf; der Workflow
   wiederholt, bis nichts mehr offen ist (höchstens 25 Aufrufe = 1.000 E-Mails; darüber braucht es einen Versanddienst).
   Ausgaben, die älter als zwei Tage sind, gehen nicht mehr raus. Fällt der Freitagslauf aus, gibt es in der Woche keine Ausgabe.
4. **Zählen** – der tägliche Besucherbericht nennt Abonnenten, An- und Abmeldungen des Tages, Konten und die letzte Ausgabe.

Die E-Mail hat eine Text- und eine HTML-Fassung, keine Bilder, keine Zählpixel, keine Verfolgungs-Links. Im Kopf stehen
`List-Unsubscribe` und `List-Unsubscribe-Post` (Abbestellen aus dem E-Mail-Programm, RFC 8058).

## Einwilligung und Abbestellen

- **Bestellen:** Häkchen bei der Registrierung (gilt erst, wenn der Link in der Bestätigungs-E-Mail geöffnet und das Konto
  angelegt ist) oder der Schalter „Wochenbrief per E-Mail“ in „Mein Bondarium“. Bestehende Konten haben ihn nicht.
- **Abbestellen:** Link in jeder Ausgabe (`konto.html#nl-ab=<Kontonummer>.<Hashwert>` – ein Klick, ohne Anmeldung; der Teil
  hinter „#“ steht in keinem Server-Log, die Seite schickt ihn per POST), der Knopf des E-Mail-Programms
  (POST auf `konto.php?nl=<Kennung>`; ein GET dorthin bestellt nichts ab, er leitet auf den Link der Seite um) oder der Schalter. Konto löschen beendet ihn ebenfalls.
- **Gespeichert:** am Konto `newsletter` (ja/nein), `newsletter_seit`, `newsletter_kw` (zuletzt erhaltene Ausgabe); in
  `newsletter_log` An- und Abmeldungen als Zeitpunkt und Art, ohne Kontobezug, 25 Monate. Datenschutztext:
  `rechtliches.html#newsletter`.

## Lokal testen

```bash
python3 scripts/newsletter.py --vorschau        # newsletter/vorschau.html und vorschau.txt mit Muster-Merkliste
NEWSLETTER_VERSAND=1 python3 scripts/newsletter.py   # Versand unabhängig vom Wochentag freigeben
php -S 127.0.0.1:8090
curl -s -H "X-Requested-With: bondarium-konto" -H "X-Trigger-Key: lokal" --data "aktion=newsletter-senden" http://127.0.0.1:8090/konto.php
```

Lokal wird nichts verschickt: Jede E-Mail landet als `konto-daten/lokal-newsletter-<Kontonummer>.txt` und `.html`
(Probe an den Betreiber: Nummer 0). Der Schlüssel heißt lokal `lokal`. Lokal gibt es nur Python 3.9 – die Skripte brauchen
den Starter mit `from __future__ import annotations`.

## Offen

- **Zustellung:** Versand über PHP `mail()` bei STRATO mit Absender info@bondarium.com. Ohne SPF-Eintrag kann der
  Wochenbrief im Spam landen (siehe docs/KONTO.md).
- **USA im Wochenvergleich:** bräuchte Tageswerte im Datenlauf.
- **Rechtstexte** (Einwilligung, Datenschutzabsatz) sind nicht juristisch geprüft.


## Datensatz `newsletter/anleihen.json` (seit 03.10.2026)

`{ISIN: [Name, Kupon-Text, Fälligkeit, Kurs, Rendite, Veränderung zur Vorwoche, nächster Zinstermin, Zinsart, geschätzt]}` – gebaut in
`scripts/newsletter.py` (`anleihen_daten`), gelesen von `konto.php` (Meldungen, Wochenbrief-Merkliste, Termine in „Mein Bondarium“) und
`erinnerung.php` (Titel der E-Mail vor Fälligkeit). Name = Kurzname nach der Regel der Website (`_common.kurz_name`), Kupon-Text
„3,50 %“ · „variabel“ · „Nullkupon“; der nächste Zinstermin ist laut Deutscher Börse oder – Feld 8 = 1 – geschätzt (dieselbe Rechnung
wie der Steckbrief). Titel („Deutschland 2,60 % 2033“) und Restlaufzeit werden beim Versand aus den Feldern 0–2 gebildet
(`titel_aus` in newsletter.py, `nl_titel`/`nl_restlaufzeit` in konto.php) – gespeichert wären sie 1,5 MB zusätzlich. Neue Felder nur
hinten anhängen: die PHP-Dateien lesen nach Stelle. `konto.php` liefert die geschätzten Termine an die Seite als `termine_geschaetzt`
({ISIN: 1}) neben `termine`.
