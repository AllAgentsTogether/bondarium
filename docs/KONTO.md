# Benutzerbereich „Mein Depot“

Stand 30.09.2026 (abends: Anmeldung mit Passwort statt per E-Mail-Link). Besucher registrieren sich mit E-Mail-Adresse
und Passwort und merken sich Anleihen. Die Merkliste („Depot“) liegt auf dem Server und ist auf jedem Gerät da, auf dem
man sich anmeldet. Es ist eine Merkliste, kein Wertpapierdepot: keine Bestände, keine Kaufpreise, keine Orders.

## Bausteine

| Datei | Aufgabe |
| --- | --- |
| `konto.html` | Seite „Mein Depot“: Anmelden, Registrieren, Passwort vergessen – oder die Merkliste. Für alle gleich, `noindex`. |
| `konto.js` | Spricht mit `konto.php` (`MC.konto`), zeichnet den Merken-Knopf. Geladen auf `konto.html`, `anleihe.html`, `anleihen-suche.html`. |
| `konto.php` | Schnittstelle auf dem Server (PHP bei STRATO), Antwort immer JSON. |
| `konto-daten/` | Entsteht nur auf dem Server: SQLite-Datei mit zufälligem Namen. Nicht im Repository, nicht im Bau. |
| `pdf.js` | Kleiner PDF-Schreiber im Browser (`MC.pdf`: Helvetica, WinAnsi, Linien, Flächen, SVG-Pfade fürs Logo, Links; A4 hoch oder quer) für den Depot-Auszug. Nur auf `konto.html`. |
| `base.css` | `.merkbtn` (Merken-Knopf). |
| `scripts/nav.py` | Menüpunkt „Mein Depot“ (`LINKS`). |
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

**Angemeldet.** Merken, Entfernen, Abmelden, Passwort ändern (mit dem aktuellen Passwort; andere Geräte werden
abgemeldet, eine E-Mail weist darauf hin), Konto löschen (mit Passwort).

Der Teil hinter `#` eines Links geht nicht an den Server und steht in keinem Log; die Seite nimmt ihn sofort aus der
Adresse. Wer nicht angemeldet ist, löst keine Anfrage an `konto.php` aus: `konto.js` fragt den Stand nur ab, wenn der
Merker `bondarium-angemeldet` da ist. Klickt ein nicht angemeldeter Besucher auf „Merken“, führt der Knopf auf
`konto.html?merken=<ISIN>`; die ISIN geht mit der Anmeldung oder Registrierung mit und liegt danach im Depot. Ist jemand
schon angemeldet, legt `?merken=` nichts von selbst ab (ein fremder Link soll nichts ins Depot legen können) – die
Seite zeigt dann einen Knopf.

## Tabelle und Depot-Auszug

„Mein Depot“ und der PDF-Auszug zeigen dieselben Spalten wie die Anleihen-Suche (Nutzerwunsch 30.09.2026): Anleihe (Name,
darunter der Registername), Rendite, Kurs, Kupon, Fälligkeit, Restlaufzeit, Art, ISIN, Währung, Volumen, Stückelung;
„Mein Depot“ dazu „Gemerkt“ und „Entfernen“. Formate und Regeln wie in `anleihen-suche.html` (Rendite ohne Befund und ohne
unplausible Taxe, „?“ bei fraglicher Taxe, „*“ bei Realrendite, „Daten?“ bei Widerspruch im ESMA-Register). Die Tabelle
ist breit; auf schmalen Bildschirmen wischt man quer, am Handy erscheint jede Anleihe als Karte mit allen Werten.

## Depot teilen (PDF)

Über der Tabelle stehen „Depot teilen“ und „Als PDF speichern“. „Depot teilen“ öffnet das Teilen-Menü des Geräts (Web
Share API mit Datei – Handy, Tablet, Safari); wo der Browser keine Dateien teilen kann, wird das PDF heruntergeladen.
Nutzerentscheid: nichts Persönliches im PDF (kein Name, keine E-Mail-Adresse), und das PDF geht nicht über den Server.
Dateiname `Bondarium-Depot-JJJJ-MM-TT.pdf`.

Gestaltung schlicht: A4 quer (elf Spalten), Helvetica, grünes Band mit dem Logo der Website (Bildzeichen „Orbit“ und
Wortmarke als Vektor, die Wortmarke aus der Kopfzeile der Seite gelesen), „Depot-Auszug“ mit Datum, Anzahl und Kursstand,
die Tabelle in der gewählten Sortierung (Name mit Link auf den Steckbrief), unten Erklärungen, „Keine Anlageberatung“ und
die Seitenzahl. Eine Fassung im Design der Startseite (Kacheln, Karte, eingebettete Manrope) war kurz live und ist auf
Wunsch des Nutzers wieder entfernt (Commit 684be7e).

## Was gespeichert wird

SQLite-Datei `konto-daten/konto-<zufällig>.sqlite` (Fassung 2):

| Tabelle | Inhalt | Löschung |
| --- | --- | --- |
| `nutzer` | E-Mail-Adresse, Hashwert des Passworts, angelegt am, zuletzt angemeldet | „Konto löschen“ sofort; nach zwei Jahren ohne Anmeldung |
| `favoriten` | ISIN und Zeitpunkt je Nutzer, höchstens 200 | „Entfernen“, mit dem Konto |
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

## Lokal testen

Lokal braucht es PHP (`brew install php`). Der Python-Server der Vorschau führt kein PHP aus.

```bash
php -S 127.0.0.1:8090
```

Unter dem PHP-eigenen Server gilt der lokale Ursprung, die Cookies kommen ohne „Secure“, und die E-Mail landet in
`konto-daten/lokal-mail.txt` statt im Versand. Der Ordner `konto-daten/` ist git-ignoriert.
