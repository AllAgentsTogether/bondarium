# Besucherzählung und täglicher Bericht

Seit 01.10.2026. Bondarium zählt seine Besucher selbst, auf dem eigenen Server bei STRATO: ohne Cookies, ohne
Speicherung im Browser und ohne fremden Dienst. Jeden Morgen geht ein PDF-Bericht über den Vortag an
**info@bondarium.com**.

Vom Betreiber gewählt (01.10.2026): eigener Zähler statt Cloudflare, Plausible oder Matomo; die Zahlen kommen nur per
E-Mail, es gibt keine eigene Statistik-Seite; der Bericht kommt täglich. Ändert sich etwas an den verarbeiteten Daten,
muss die Datenschutzerklärung (`rechtliches.html#statistik`) mit, und der Betreiber wird vorher gefragt.

## Dateien

| Datei | Aufgabe |
|---|---|
| `site.js` (Funktion `zaehlen`) | meldet jeden Seitenaufruf per `navigator.sendBeacon` an `/aufruf.php`: Pfad ohne Suchparameter (`p`), Referrer (`r`), `utm_source` (`q`) |
| `aufruf.php` | prüft und zählt, antwortet immer mit 204; verschickt den Bericht beim ersten Aufruf ab 6 Uhr |
| `statistik-bericht.php` | PDF-Schreiber (PHP-Fassung von `pdf.js`), Berichtsseite, Zahlen aus der Datenbank, E-Mail mit Anhang; direkt aufgerufen 404, per `.htaccess` gesperrt |
| `statistik-daten/` | SQLite-Datei mit zufälligem Namen, legt `aufruf.php` auf dem Server an; nie im Repo, nie im Bau, dreifach gesperrt (Stamm-`.htaccess`, eigene `.htaccess`, `*.sqlite`) |

## Was gezählt wird

- **Besucher** = verschiedene Besucher an einem Tag. Aus IP-Adresse und Browser-Kennung wird mit einem zufälligen
  Tages-Schlüssel eine HMAC-Prüfsumme gebildet. Der Schlüssel wird jeden Tag neu erzeugt und der alte gelöscht, die
  Prüfsummen ebenso. Die IP-Adresse wird nicht gespeichert. Über mehrere Tage sind die Besucher deshalb die Summe der
  Tageswerte: Wer an zwei Tagen kommt, zählt zweimal.
- **Seitenaufrufe** je Seite. Gezählt werden nur Seiten, die es gibt (`/` oder `/name.html`). Alle Steckbriefe
  `anleihe.html?isin=…` zählen als eine Seite.
- **Herkunft** beim ersten Aufruf eines Besuchers am Tag, eingeteilt in Suchmaschinen, KI-Assistenten (auch über
  `utm_source`, das ChatGPT & Co. an Links hängen), andere Websites und „direkt oder unbekannt“. Gespeichert wird nur
  der Name der Website, nie Pfad oder Suchbegriff. Die Liste der Muster steht in `stat_herkunft()`.
- **Geräte**: Handy, Computer oder Tablet, abgeleitet aus der Browser-Kennung. iPads melden sich oft als Mac und
  zählen dann als Computer.
- **Nicht gezählt**: Robots und automatisierte Browser (Muster `ROBOT`, `navigator.webdriver`), mehr als 300 Aufrufe
  je Besucher und Tag (die werden als Robot gezählt), Browser mit „Global Privacy Control“ oder „Do Not Track“
  (geprüft in `site.js` und im Kopf der Anfrage), Abrufe ohne JavaScript, fremde Ursprünge, lokale Dateien.
- Tageswerte werden nach 25 Monaten gelöscht (`AUFBEWAHREN_MONATE`).

## Bericht

Seit 02.10.2026 stößt derselbe Weg auch die E-Mails „30 Tage vor jeder Fälligkeit“ an: Der erste gezählte Aufruf ab 7 Uhr ruft
nach der Antwort `erinnerungen_senden()` aus `erinnerung.php` (Beschreibung in docs/KONTO.md). Der Workflow „Statistik –
Testmail“ schickt mit der Auswahl `erinnerung` eine Beispiel-Erinnerung statt des Berichts.

- Der erste Aufruf ab 6:00 Uhr (Berlin) verschickt den Bericht des Vortags. Das passiert erst nach der Antwort an den
  Browser, der Besucher wartet also nicht. Ohne Besucher am Morgen kommt der Bericht später. Tage ohne Zählung werden
  übersprungen. Scheitert der Versand, gibt es frühestens nach einer Stunde einen neuen Versuch.
- Inhalt: vier Kennzahlen mit Vergleich zum Vortag und zum gleichen Wochentag der Vorwoche, Verlauf der letzten 30 Tage
  mit 7-Tage-Durchschnitt, Zeiträume (gestern, 7 und 30 Tage, Monat, Jahr), die zehn meistbesuchten Seiten (Name aus
  dem `<title>`, gekürzt vor dem Doppelpunkt), Herkunft, Geräte, Hinweis zur Zählweise.
- Versand mit PHP `mail()` von und an info@bondarium.com (eigenes STRATO-Postfach, wie `kontakt.php`).

## Lokal testen

```
php -S 127.0.0.1:8090                    # Vorschau-Konfiguration „bondarium-php“
php aufruf.php bericht 2026-10-01        # Bericht für einen Tag → statistik-daten/*.pdf und lokal-mail.txt
```

Lokal gilt der Ursprung `http://127.0.0.1:8090`, und statt einer E-Mail entstehen Dateien in `statistik-daten/`.
Den Ordner nach dem Test löschen.

Testmail sofort: Workflow „Statistik – Testmail“ (`gh workflow run statistik-testmail.yml`) – POST `aktion=testmail` mit
Kopf `X-Trigger-Key` an `aufruf.php`, Bericht über den laufenden Tag, höchstens alle fünf Minuten.

Nach jedem Deploy prüft der Workflow, dass `statistik-daten/` und `statistik-bericht.php` gesperrt sind und
`aufruf.php` mit 204 antwortet. Ein GET wird nicht gezählt.
