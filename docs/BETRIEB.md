# Betrieb absichern: Wächter, Alarme, Server, Datenbank-Datei

Seit 03.10.2026 (Bewertung in 21 Prüffeldern, Top-1 Technik), zuletzt nachgezogen am 15.10.2026 (Gesamtprüfung 14.10.2026,
F01, F02, F05, F06). Keiner der Teile verändert die Website sichtbar.

**Keine eigene Sicherung mehr (seit 09.10.2026).** Vom 03.10. bis 09.10.2026 gab es eine nächtliche, verschlüsselte Sicherung
der Konto- und Statistik-Datenbank (Workflow `sicherung.yml`, `strato-cron/sicherung.php`, Zertifikat, privates Repo
`AllAgentsTogether/bondarium-sicherung`, Secret `SICHERUNG_DEPLOY_KEY`, Abschnitt „Sicherung“ in der Datenschutzerklärung).
Der Betreiber hat sie am 09.10.2026 vollständig entfernen lassen, samt Schlüsselpaar auf dem Mac. Eine Sicherung der
Datenbanken gibt es seitdem nur über die Webspace-Sicherung von STRATO (`docs/KONTO.md`). Das private Repo
`bondarium-sicherung` mit den verschlüsselten Kopien bestand am 14.10.2026 noch (letzter Push 09.10.); löschen will es der
Betreiber selbst – danach hier als erledigt vermerken.

## 1. Wächter

### Erreichbarkeit (GitHub, alle 15 Minuten)

Workflow `erreichbarkeit.yml`, Zeitplan Minute 7, 22, 37, 52 (nicht zur vollen Stunde): Startseite, Anleihen-Suche,
Suchindex (nur Kopfzeilen), `aufruf.php` (204) und `konto.php?aktion=status` („ok“). Je Abruf bis zu drei Versuche im
Abstand von 20 s; danach rot = E-Mail von GitHub.

GitHub garantiert geplante Läufe nicht. Am 03./04.10.2026 kam der Wächter nur sporadisch (am 04.10. dreimal in 13 Stunden).
Seit 05.10.2026 läuft er regelmäßig: 42 bis 84 Läufe am Tag statt 96, im Mittel alle 22 Minuten, größte Lücke 47 Minuten
(Auswertung 06.–14.10.2026; am 14.10. nur 42 Läufe – GitHub dünnt aus, ein Fehler ist das nicht).

**Rot ohne Ausfall der Seite:** Kann GitHub keinen Runner zuteilen („The job was not acquired by Runner of type hosted even
after multiple attempts“), wird der Lauf ebenfalls rot – so am 05.10.2026 zwischen 21:21 und 23:00 Uhr sechsmal. Im Lauf
steht dann kein einziger Abruf. Ist im Protokoll ein Abruf mit „HTTP …“ gescheitert, ist es ein echter Alarm.

### Datenstand (seit 15.10.2026, Gesamtprüfung F05-02)

Zweiter Schritt im selben Workflow. Bleibt der Datenlauf ganz aus (cron-job.org und der GitHub-Zeitplan fallen zugleich aus,
der Workflow ist abgeschaltet), schickt sonst kein Lauf eine Fehler-E-Mail, und die Seite zeigt still alte Zahlen. Der
Wächter liest deshalb `checkedAt` aus der live ausgelieferten `renditen.json` – den Zeitstempel setzt jeder Datenabruf, auch
ohne neue Werte; Push-Deploys lassen ihn stehen.

- Fällig ist ein Abruf an jedem Börsentag (Montag bis Freitag ohne die Feiertage der Frankfurter Börse wie in
  `scripts/kurs_luecken.py`), ab 14 Uhr Berlin.
- Alarm erst, wenn **zwei** fällige Abrufe fehlen. Einen einzelnen fehlenden Tag meldet schon der nächste Datenlauf
  („Lücken im Kursverlauf“); Wochenende, Feiertag oder ein verspäteter Lauf lösen so keinen Fehlalarm aus.
  Beispiel: letzter Abruf Mittwoch → Alarm ab Freitag 14 Uhr.
- Rot nur in Läufen zwischen 14 und 17 Uhr Berlin (gut fünf am Tag), sonst eine Warnung im Lauf – solange die Daten alt
  sind, kommen so einige E-Mails am Tag statt vier je Stunde. Beim Start von Hand („Run workflow“) immer rot.
- Ist `renditen.json` nicht abrufbar oder ohne gültiges `checkedAt`, gilt dasselbe (Meldung „Datenstand nicht lesbar“).

Was tun: im Workflow „Daten aktualisieren & auf Strato veröffentlichen“ nachsehen, ob er abgeschaltet ist und wann er
zuletzt lief; bei cron-job.org den 10-Uhr-Auslöser prüfen; das Token `GH_DISPATCH_TOKEN` prüfen (Abschnitt 3). Einen
Abruf startet „Run workflow“ mit „voll“.

### cron-job.org (maßgeblich für die Erreichbarkeit)

**Der verlässliche Wächter ist ein Job bei cron-job.org** (Konto des Betreibers, dort wie der 10-Uhr-Auslöser):
`https://www.bondarium.de/konto.php?aktion=status` alle 15 Minuten, Benachrichtigung bei Fehlschlag und bei
Wiederherstellung an. Die Abfrage braucht keinen Schlüssel, prüft Server, PHP und die Konto-Datenbank (Störung = HTTP 503)
und zählt nicht als Besuch (kein JavaScript). Der GitHub-Wächter bleibt die zweite Ebene mit den genaueren Prüfungen.

## 2. Alarme, die etwas bedeuten

Alle melden sich über denselben Weg: Ein roter Lauf schickt eine E-Mail von GitHub an das Konto AllAgentsTogether. Im
Workflow `update-data.yml`:

- **Frische-Prüfung** (`scripts/frische.py`, seit 09.10.2026): jede Datendatei, `kurse/bund` und Pflichtwerte (Breakeven,
  Anteil der Kurse mit Aufschlag zu Bund). Soll in Handelstagen je Quelle, Alarm ab 2 Handelstagen Rückstand; Monatswerte
  (OECD, HQM, RBA – auch der US-Risikoaufschlag ist seit 30.09.2026 ein Monatswert) gegen den Monat vor drei Monaten. Nur
  im Abruf-Lauf, nicht bei Push-Deploys. Regeln im Kopf des Skripts.
- **Lücken im Kursverlauf** (`scripts/kurs_luecken.py`, seit 29.09.2026): Fehlt seit dem 24.09.2026 ein Börsentag in
  `kurse/`, wird der Abruf-Lauf rot. Nicht mehr nachholbare Tage stehen in `BEKANNTE_LUECKEN` und lösen keinen Alarm aus.
  **Stand 15.10.2026:** Der 05.10.2026 fehlt und steht nicht in der Liste (Technik-Test E1, Frage 3: nachtragen – offen).
  Bis das entschieden ist, endet jeder 10-Uhr-Lauf rot; ob ein roter Lauf mehr meldet als „fehlend: 2026-10-05“, zeigt nur
  der Blick in die Schritte (am 07./08.10. ging so ein Frische-Alarm, am 09.10. eine Nach-Deploy-Prüfung unter).
- **Ergebnis der Abruf-Schritte** (seit 09.10.2026): Tabelle in der Zusammenfassung des Laufs; gescheiterte Abrufe als
  Warnung (GitHub zeigt sie wegen `continue-on-error` grün). Selbst kein Alarm – den gibt die Frische-Prüfung.
- **.htaccess-Prüfung** (`scripts/htaccess_test.sh`, seit 02.10.2026): echter Apache im Runner vor dem Upload. Falscher
  Status, falsches Weiterleitungsziel oder offene Sperre → kein Upload, die Seite behält den letzten Stand, der Lauf ist rot.
- **Alarm bei fehlgeschlagener Nach-Deploy-Prüfung**: Seite/Weiterleitung/410, Trigger-Konfiguration nicht abrufbar,
  Benutzerbereich, Besucherzählung, Server-Steckbriefe der Bundeswertpapiere, seit 09.10.2026 auch Wochenbrief (bauen und
  verschicken) und Meldungen. Diese Schritte laufen mit `continue-on-error`, damit Wochenbrief und Meldungen rausgehen; der
  Alarm-Schritt am Ende macht den Lauf dann rot. Scheitert der Bau der Server-Steckbriefe, gilt für alle Bundeswertpapiere
  still die Vorlage mit `noindex` – auch dann schlägt dieser Alarm an.
- **Reserve-Lauf musste selbst abrufen** (seit 09.10.2026): Der GitHub-Zeitplan um 10:15 ruft nur ab, wenn heute noch kein
  Abruf gespeichert ist. Dann ist der 10-Uhr-Auslöser ausgefallen (cron-job.org, `refresh.php`, `GH_DISPATCH_TOKEN`) oder
  `update_renditen.py` hat nichts geschrieben – die Daten sind da, der Lauf wird trotzdem rot.

Dazu die beiden Wächter aus Abschnitt 1.

## 3. Auslöser des 10-Uhr-Laufs und `GH_DISPATCH_TOKEN`

cron-job.org ruft Montag bis Freitag um 10:00 Uhr (Berlin) `https://www.bondarium.de/trigger/refresh.php?mode=voll` auf,
mit dem Schlüssel im Kopf `X-Trigger-Key` (Secret `TRIGGER_KEY`). `refresh.php` startet den Workflow über die GitHub-API
(`workflow_dispatch`) mit dem Token aus dem Secret `GH_DISPATCH_TOKEN` (angelegt 30.09.2026; laut Einrichtungsanleitung
`docs/archiv/GITHUB-REDUKTION.md` ein Fine-grained Token nur für dieses Repository mit „Actions: Read and write“). Beide Werte kommen nur mit einem Deploy auf den Server: Der Schritt
„Trigger bauen & konfigurieren“ schreibt sie in `trigger/refresh-config.php` (per `.htaccess` gesperrt).

- **Ablaufdatum: noch nicht notiert.** Nachsehen unter GitHub → Settings → Developer settings → Personal access tokens →
  Fine-grained tokens und hier eintragen; zwei Wochen vorher eine Erinnerung setzen. GitHub schlägt beim Anlegen 30 Tage
  vor – blieb es dabei, läuft das Token um den 30.10.2026 ab.
- Läuft es ab, antwortet GitHub `refresh.php` mit 401, `refresh.php` meldet 502 (cron-job.org zeigt den Fehlschlag), der
  10-Uhr-Lauf startet nicht. Der Reserve-Lauf um 10:15 holt die Daten und wird rot („Reserve-Lauf musste selbst abrufen“).
- Erneuern: neues Token mit denselben Rechten anlegen, Secret `GH_DISPATCH_TOKEN` ersetzen, dann einen Deploy starten
  (Push oder „Run workflow“ mit „schnell“), damit `refresh-config.php` neu geschrieben wird. Am nächsten Werktag prüfen, dass
  der 10-Uhr-Lauf als `workflow_dispatch` kam.

## 4. Server bei STRATO

- **PHP-Version:** nirgends festgehalten (die Kopfzeilen verraten sie richtigerweise nicht). Im Kundenbereich ablesen und
  hier eintragen – offen. Die Syntaxprüfung im Datenlauf nutzt das PHP des Runners (Ubuntu 24.04), lokal läuft 8.5. Nach
  jedem PHP-Wechsel bei STRATO einmal prüfen: `konto.php?aktion=status` („ok“), Anmelden und das Kontaktformular.
- **Webspace-Sicherung:** die einzige Sicherung der Konto-Datenbank. Ob sie eingeschaltet ist, wie weit sie zurückreicht und
  wie man eine einzelne Datei daraus holt, ist noch nicht nachgesehen (Kundenbereich) – offen; Austausch der Datei siehe
  Abschnitt 5.
- **Datenordner ohne eigene Fehlerseite (gewollt, seit 15.10.2026 festgehalten):** `konto.php`, `aufruf.php` und
  `wechselkurse.php` legen `konto-daten/`, `statistik-daten/` und `wechselkurs-daten/` mit den Rechten 0700 an. Apache kann
  die Ordner dann nicht einmal lesen („Server unable to read htaccess file“) und antwortet mit der nackten 403-Seite statt
  mit `404.html`. Gesperrt ist alles – durch die Regeln in der `.htaccess` des Stammordners und die Ordnerrechte. Die nackte
  Seite sieht nur, wer gezielt nach den Ordnern sucht. Der offene Punkt aus dem Technik-Test 08.10.2026 („eigene 403-Seite
  greift nicht in konto-daten/ und statistik-daten/“) ist damit geschlossen.
- Die beiden Datenbanken liegen im Docroot (`/bondarium`); geschützt nur durch `.htaccess`-Regeln, Ordnerrechte und
  zufällige Dateinamen. Ob der Webspace oberhalb von `/bondarium` beschreibbar ist (dann könnten die Ordner dorthin), ist
  ungeprüft.

## 5. Konto-Datenbank von Hand austauschen

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

## 6. Repository beobachten

- **Größe:** Jeder Datenlauf committet `suchindex.json` (5,4 MB), `anleihen-kurse.json` (2,4 MB) und die Kursdateien; die
  Geschichte wächst so um rund 4 MB am Tag (Pack 62,7 MB am 15.10.2026). Einmal im Monat `git count-objects -vH` ansehen;
  bevor es auf 1 GB zugeht, große erzeugte Dateien wie `suchindex.json` nur noch im Deploy bauen statt sie zu committen.
- `anleihen-kurse 2.json` im Stammordner ist eine Finder-Kopie vom 27.09.2026, nur per `.gitignore` ausgeblendet. Löschen
  entscheidet der Betreiber; danach die Zeile in `.gitignore` streichen.

## 7. Offen beim Betreiber (Stand 15.10.2026)

- Technik-Test E1, Frage 3: Börsentag 05.10.2026 nachtragen – bis dahin ist jeder 10-Uhr-Lauf rot (Abschnitt 2).
- Ablaufdatum von `GH_DISPATCH_TOKEN` nachsehen und eintragen (Abschnitt 3).
- PHP-Version und Webspace-Sicherung im STRATO-Kundenbereich nachsehen (Abschnitt 4).
- DMARC ohne Berichtsadresse (`rua`); CAA und DNSSEC fehlen (Technik-Test E4, Frage 20) – beides bei STRATO.
- Privates Repo `bondarium-sicherung` löschen (Einleitung).
