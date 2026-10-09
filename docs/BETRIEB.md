# Betrieb absichern: Wächter, Alarme, Datenbank-Datei

Seit 03.10.2026 (Bewertung in 21 Prüffeldern, Top-1 Technik). Keiner der Teile verändert die Website sichtbar.

**Keine eigene Sicherung mehr (seit 09.10.2026).** Vom 03.10. bis 09.10.2026 gab es eine nächtliche, verschlüsselte Sicherung
der Konto- und Statistik-Datenbank (Workflow `sicherung.yml`, `strato-cron/sicherung.php`, Zertifikat, privates Repo
`AllAgentsTogether/bondarium-sicherung`, Secret `SICHERUNG_DEPLOY_KEY`, Abschnitt „Sicherung“ in der Datenschutzerklärung).
Der Betreiber hat sie am 09.10.2026 vollständig entfernen lassen, samt Schlüsselpaar auf dem Mac. Eine Sicherung der
Datenbanken gibt es seitdem nur über die Webspace-Sicherung von STRATO (`docs/KONTO.md`).

## 1. Wächter (Erreichbarkeit)

Workflow `erreichbarkeit.yml`, alle 15 Minuten (Minute 7, 22, 37, 52 – nicht zur vollen Stunde): Startseite,
Anleihen-Suche, Suchindex (nur Kopfzeilen), `aufruf.php` (204) und `konto.php?aktion=status` („ok“). Je Abruf bis zu
drei Versuche im Abstand von 20 s; danach rot = E-Mail von GitHub.
GitHub garantiert geplante Läufe nicht: Sie kommen oft einige Minuten später, und einen neuen Zeitplan übernimmt GitHub
mitunter erst nach Stunden (am 03.10.2026: über drei Stunden kein Lauf mit „*/15“, darum neu eingetragen).

**In diesem Repository läuft der Wächter bei GitHub nur sporadisch** – am 04.10.2026 dreimal in 13 Stunden statt rund
fünfzigmal (02:55, 05:12, 11:04 UTC); schon der Datenlauf kam im September täglich Stunden zu spät (darum stößt ihn
cron-job.org an, `strato-cron/refresh.php`). Der GitHub-Wächter bleibt als zweite Ebene mit den genaueren Prüfungen.
**Der verlässliche Wächter ist ein Job bei cron-job.org** (Konto des Betreibers, dort wie der 10-Uhr-Auslöser):
`https://www.bondarium.de/konto.php?aktion=status` alle 15 Minuten, Benachrichtigung bei Fehlschlag und bei
Wiederherstellung an. Die Abfrage braucht keinen Schlüssel, prüft Server, PHP und die Konto-Datenbank (Störung = HTTP 503)
und zählt nicht als Besuch (kein JavaScript).

## 2. Alarme, die etwas bedeuten

- Frische-Prüfung (`update-data.yml`): Der US-Risikoaufschlag ist seit 30.09.2026 ein Monatswert (Stand „JJJJ-MM“) –
  Schwelle 100 Tage wie die übrigen Monatswerte. Die alte Schwelle von 7 Tagen machte jeden Datenlauf seit 30.09. rot.
- Nach-Deploy-Prüfungen (Trigger, Benutzerbereich, Besucherzählung) laufen weiter mit `continue-on-error`, damit
  Wochenbrief und Meldungen rausgehen; der Schritt „Alarm bei fehlgeschlagener Nach-Deploy-Prüfung“ am Ende macht den
  Lauf dann rot. Vorher blieb er grün.
- Server-Steckbriefe der Bundeswertpapiere (`scripts/steckbriefe.py`, seit 03.10.2026): Scheitert der Schritt, gilt für
  alle 79 still die Vorlage mit `noindex`. Derselbe Alarm schlägt dann an; zusätzlich prüft die Nach-Deploy-Prüfung live,
  ob ein Bundeswertpapier als fertige Seite vom Server kommt.

Alle melden sich über denselben Weg: Ein roter Lauf schickt eine E-Mail von GitHub an das Konto AllAgentsTogether.

## 3. Konto-Datenbank von Hand austauschen

Wer die Datei in `konto-daten/` ersetzt (zum Beispiel aus der Webspace-Sicherung von STRATO): alte vorher umbenennen, nicht
löschen; der Dateiname bleibt der zufällige der dortigen Datenbank. Entschlüsselte oder heruntergeladene Kopien auf dem Mac
danach löschen – sie enthalten E-Mail-Adressen.

**Während des Austauschs meldet `konto.php` 503 („speicher“); der Wächter-Alarm ist dann erwartet.** Seit 09.10.2026
(Technik-Test 08.10.2026, T-22) legt `konto.php` neben die Datenbank die Marke `konto-daten/.angelegt`. Gibt es die Marke,
aber keine `konto-*.sqlite`, oder liegen zwei solche Dateien da, legt `konto.php` nichts an und antwortet 503 – vorher
entstand in dieser Lücke still eine leere Datenbank (auch durch den Wächter alle 15 Minuten), und danach entschied der
zufällige Dateiname, welche gilt. `erinnerung.php` verschickt bei zwei Dateien nichts. Darum:

- Die alte Datei so umbenennen, dass der Name nicht mehr auf `.sqlite` endet (z. B. `konto-….sqlite.alt`) – sonst liegen zwei
  Datenbanken da, und es bleibt bei 503.
- Sobald wieder genau eine `konto-*.sqlite` da ist, läuft alles weiter; `konto.php?aktion=status` muss wieder „ok“ melden.
- Die Marke nicht löschen. Nur wer bewusst mit einer leeren Datenbank neu anfangen will, löscht sie zusammen mit der Datei.
