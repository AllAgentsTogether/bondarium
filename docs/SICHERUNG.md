# Betrieb absichern: Sicherung, Wächter, Alarme

Seit 03.10.2026 (Bewertung in 21 Prüffeldern, Top-1 Technik). Drei Teile – keiner verändert die Website sichtbar.

## 1. Sicherung der Datenbanken

Jede Nacht um 03:40 Uhr (Sommerzeit; Winterzeit 02:40 Uhr) sichert der Workflow `sicherung.yml` die Datenbank des
Benutzerbereichs (`konto-daten/konto-*.sqlite`: Konten, Merklisten, Musterdepots, Einwilligungen) und die Tagessummen der
Besucherzählung (`statistik-daten/statistik-*.sqlite`).

| Schritt | Wo | Was |
|---|---|---|
| Kopie und Verschlüsselung | `strato-cron/sicherung.php` → Server `/trigger/sicherung.php` | POST mit Kopf `X-Trigger-Key` (derselbe Schlüssel wie `refresh.php`) und `db=konto` bzw. `db=statistik`. `VACUUM INTO` zieht eine in sich stimmige Kopie, gzip, dann S/MIME-Verschlüsselung (AES-256) mit `sicherung-zertifikat.pem`. Zwischendateien nur im gesperrten Datenordner, sofort gelöscht. Ohne POST 405, ohne Schlüssel 403 (prüft der Deploy nach jedem Upload). |
| Ablage | Workflow `sicherung.yml` | Holt die beiden verschlüsselten Dateien, legt nur verschlüsselte Antworten ab (sonst rot) und schreibt sie ins private Repo `AllAgentsTogether/bondarium-sicherung` (`staende/JJJJ-MM-TT-konto.p7m`). |
| Aufbewahrung | Workflow | Tagesstände 30 Tage, der erste Stand jedes Monats 12 Monate. Das Ablage-Repo hat immer nur einen Commit ohne Vorgeschichte (Force-Push), damit Gelöschtes wirklich weg ist – so steht es in der Datenschutzerklärung (`rechtliches.html#sicherung`). |

**Schlüssel.** Öffentliches Zertifikat „Bondarium Sicherung“ (RSA 4096, gültig bis 2126) im Repo:
`strato-cron/sicherung-zertifikat.pem`. Der private Schlüssel liegt NUR beim Betreiber (erzeugt am 03.10.2026 in
`~/Bondarium-Sicherung/` auf dem Mac, Kopie gehört in den Passwortmanager). Ohne ihn ist keine Sicherung lesbar – geht er
verloren, sind alle Sicherungen wertlos: dann neues Schlüsselpaar erzeugen und das Zertifikat hier austauschen.

**Secrets** im Repo `bondarium`: `TRIGGER_KEY` (schon vorhanden) und `SICHERUNG_DEPLOY_KEY` (SSH-Schlüssel, im Ablage-Repo
als Deploy-Key mit Schreibrecht „Workflow Sicherung“ eingetragen; gilt nur für dieses eine Repo).

**Wiederherstellen** (Anleitung auch im Ablage-Repo):

```bash
gh repo clone AllAgentsTogether/bondarium-sicherung && cd bondarium-sicherung
openssl smime -decrypt -binary -in staende/2026-10-04-konto.p7m -inkey ~/Bondarium-Sicherung/bondarium-sicherung-privat.pem -out konto.sqlite.gz
gunzip konto.sqlite.gz && sqlite3 konto.sqlite 'pragma integrity_check'   # „ok“
```

Dann auf dem Server die Datei in `konto-daten/` ersetzen (alte vorher umbenennen, nicht löschen; der Dateiname bleibt der
zufällige der dortigen Datenbank). Entschlüsselte Kopien auf dem Mac danach löschen – sie enthalten E-Mail-Adressen.

## 2. Wächter (Erreichbarkeit)

Workflow `erreichbarkeit.yml`, alle 15 Minuten (Minute 7, 22, 37, 52 – nicht zur vollen Stunde): Startseite,
Anleihen-Suche, Suchindex (nur Kopfzeilen), `aufruf.php` (204) und `konto.php?aktion=status` („ok“). Je Abruf bis zu
drei Versuche im Abstand von 20 s; danach rot = E-Mail von GitHub.
GitHub garantiert geplante Läufe nicht: Sie kommen oft einige Minuten später, und einen neuen Zeitplan übernimmt GitHub
mitunter erst nach Stunden (am 03.10.2026: über drei Stunden kein Lauf mit „*/15“, darum neu eingetragen).

## 3. Alarme, die etwas bedeuten

- Frische-Prüfung (`update-data.yml`): Der US-Risikoaufschlag ist seit 30.09.2026 ein Monatswert (Stand „JJJJ-MM“) –
  Schwelle 100 Tage wie die übrigen Monatswerte. Die alte Schwelle von 7 Tagen machte jeden Datenlauf seit 30.09. rot.
- Nach-Deploy-Prüfungen (Trigger, Benutzerbereich, Besucherzählung) laufen weiter mit `continue-on-error`, damit
  Wochenbrief und Meldungen rausgehen; der Schritt „Alarm bei fehlgeschlagener Nach-Deploy-Prüfung“ am Ende macht den
  Lauf dann rot. Vorher blieb er grün.
- Server-Steckbriefe der Bundeswertpapiere (`scripts/steckbriefe.py`, seit 03.10.2026): Scheitert der Schritt, gilt für
  alle 79 still die Vorlage mit `noindex`. Derselbe Alarm schlägt dann an; zusätzlich prüft die Nach-Deploy-Prüfung live,
  ob ein Bundeswertpapier als fertige Seite vom Server kommt.

Alle drei melden sich über denselben Weg: Ein roter Lauf schickt eine E-Mail von GitHub an das Konto AllAgentsTogether.
