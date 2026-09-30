# Benutzerbereich „Mein Depot“

Stand 30.09.2026. Besucher können sich anmelden und Anleihen merken. Die Merkliste („Depot“) liegt auf dem Server und
ist auf jedem Gerät da, auf dem man sich anmeldet. Es ist eine Merkliste, kein Wertpapierdepot: keine Bestände, keine
Kaufpreise, keine Orders.

## Bausteine

| Datei | Aufgabe |
| --- | --- |
| `konto.html` | Seite „Mein Depot“: Anmeldeformular oder Merkliste. Für alle gleich, `noindex`. |
| `konto.js` | Spricht mit `konto.php` (`MC.konto`), zeichnet den Merken-Knopf. Geladen auf `konto.html`, `anleihe.html`, `anleihen-suche.html`. |
| `konto.php` | Schnittstelle auf dem Server (PHP bei STRATO), Antwort immer JSON. |
| `konto-daten/` | Entsteht nur auf dem Server: SQLite-Datei mit zufälligem Namen. Nicht im Repository, nicht im Bau. |
| `base.css` | `.merkbtn` (Merken-Knopf). |
| `scripts/nav.py` | Menüpunkt „Mein Depot“ (`LINKS`). |
| `rechtliches.html#konto` | Abschnitt der Datenschutzerklärung. |

## Anmeldung ohne Passwort

1. Adresse eingeben → `konto.php` (`aktion=link`) schickt einen Link per E-Mail. Er gilt 30 Minuten und einmal.
   Ein Konto entsteht dabei noch nicht.
2. Der Link führt auf `konto.html#anmelden=<Kennwort>`. Der Teil hinter `#` geht nicht an den Server und steht in
   keinem Log. Die Seite nimmt ihn sofort aus der Adresse und schickt ihn per POST (`aktion=einloesen`).
3. Erst jetzt entsteht das Konto. Der Browser bekommt zwei Cookies, 90 Tage gültig, bei Nutzung verlängert:
   `__Host-bondarium-sitzung` (zufällige Kennung; HttpOnly, Secure, SameSite=Strict) und `bondarium-angemeldet=1`
   (für `konto.js` lesbar).

Wer nicht angemeldet ist, löst keine Anfrage an `konto.php` aus: `konto.js` fragt den Stand nur ab, wenn der Merker
`bondarium-angemeldet` da ist. Klickt ein nicht angemeldeter Besucher auf „Merken“, führt der Knopf auf
`konto.html?merken=<ISIN>`; die ISIN reist mit dem Anmelde-Link mit und liegt nach dem Anmelden im Depot. Ist jemand
schon angemeldet, legt `?merken=` nichts von selbst ab (ein fremder Link soll nichts ins Depot legen können) – die
Seite zeigt dann einen Knopf.

## Was gespeichert wird

SQLite-Datei `konto-daten/konto-<zufällig>.sqlite`:

| Tabelle | Inhalt | Löschung |
| --- | --- | --- |
| `nutzer` | E-Mail-Adresse, angelegt am, zuletzt angemeldet | „Konto löschen“ sofort; nach zwei Jahren ohne Anmeldung |
| `favoriten` | ISIN und Zeitpunkt je Nutzer, höchstens 200 | „Entfernen“, mit dem Konto |
| `links` | Hashwert des Link-Kennworts, Adresse, vorgemerkte ISIN, Ablauf | beim Einlösen; sonst nach Ablauf |
| `sitzungen` | Hashwert des Cookies, Ablauf | Abmelden; nach Ablauf |
| `zaehler` | verschlüsselte Hashwerte von Adresse und IP-Adresse (Missbrauchsschutz) | nach 24 Stunden |
| `meta` | Schlüssel für diese Hashwerte, Zeitpunkt des letzten Aufräumens | – |

Kennwörter von Links und Cookies stehen nie im Klartext in der Datei. „Nach Ablauf“ heißt: beim nächsten Aufräumen.
Es läuft höchstens einmal je Stunde bei jeder Anfrage, die die Datenbank öffnet – auch bei der Nach-Deploy-Prüfung des
Workflows, also mindestens einmal je Werktag.

Ändert sich etwas an diesen Daten, muss `rechtliches.html#konto` mit.

## Schutz

- Der Ordner `konto-daten/` wird nie ausgeliefert: Regel in der `.htaccess` des Stammordners (vor allen
  Weiterleitungen, auf beiden Domains), eigene `.htaccess` im Ordner (legt `konto.php` an), Sperre für `*.sqlite`,
  zufälliger Dateiname. Der Workflow prüft nach jedem Deploy, dass der Ordner mit 403 antwortet.
- Änderungen nur per POST mit dem Kopf `X-Requested-With: bondarium-konto`; ein fremder Ursprung wird abgewiesen;
  das Cookie ist SameSite=Strict.
- Obergrenzen für Anmelde-Links (`GRENZEN` in `konto.php`): je Adresse 3 in 15 Minuten und 8 am Tag, je IP-Adresse
  10 und 30, insgesamt 60 je Stunde und 300 am Tag. Dazu ein Honigtopf-Feld. Kein Captcha, keine fremden Dienste.
- Der Deploy fasst `konto-daten/` nicht an (steht nicht im Manifest). Eine Sicherung gibt es nur über die
  Webspace-Sicherung von STRATO.

## E-Mail-Versand

`mail()` von PHP, Absender `info@bondarium.com` – wie das Kontaktformular. Für beide Domains gilt DMARC `p=reject`;
ein SPF-Eintrag fehlt (Stand 30.09.2026). Fremde Postfächer (Gmail, iCloud, GMX …) nehmen die E-Mail nur an, wenn
STRATO sie für die Domain signiert (DKIM) oder ein SPF-Eintrag den Versand erlaubt. Kommt der Anmelde-Link nicht an:
bei STRATO im Kundenbereich unter Domains → DNS den SPF-Eintrag einschalten (STRATO-Standard,
`v=spf1 redirect=smtp.rzone.de`), für `bondarium.com`.

## Lokal testen

Lokal braucht es PHP (`brew install php`). Der Python-Server der Vorschau führt kein PHP aus.

```bash
php -S 127.0.0.1:8090
```

Unter dem PHP-eigenen Server gilt der lokale Ursprung, die Cookies kommen ohne „Secure“, und die E-Mail landet in
`konto-daten/lokal-mail.txt` statt im Versand. Der Ordner `konto-daten/` ist git-ignoriert.
