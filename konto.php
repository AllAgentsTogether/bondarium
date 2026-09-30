<?php
/**
 * Benutzerbereich „Mein Depot“ (konto.html, seit 30.09.2026): Konto mit Anmelde-Link per E-Mail und eine Merkliste
 * für Anleihen. Dokumentation: docs/KONTO.md. Der Browser spricht über konto.js mit diesem Skript; die Antwort ist
 * immer JSON ({"status": …}).
 *
 * Ablauf ohne Passwort:
 *   1. aktion=link       E-Mail-Adresse → Link per E-Mail (gilt 30 Minuten, einmal). Ein Konto entsteht dabei noch nicht.
 *   2. aktion=einloesen  konto.html liest das Kennwort des Links aus dem Teil hinter „#“ (er erscheint in keinem
 *                        Server-Log) und schickt es per POST. Erst jetzt entsteht das Konto; der Browser bekommt ein
 *                        Anmelde-Cookie (HttpOnly, Secure, SameSite=Strict, 90 Tage, verlängert sich bei Nutzung).
 *   3. aktion=status | merken | entfernen | abmelden | loeschen
 *
 * Gespeichert wird in einer SQLite-Datei im Ordner konto-daten/ (per .htaccess gesperrt, Dateiname zufällig):
 *   nutzer     E-Mail-Adresse, angelegt am, zuletzt angemeldet
 *   favoriten  ISIN und Zeitpunkt je Nutzer
 *   links      offene Anmelde-Links (nur der Hashwert des Kennworts, die Adresse, Ablauf) – nach Ablauf gelöscht
 *   sitzungen  Anmeldungen (nur der Hashwert des Cookies, Ablauf)
 *   zaehler    Schutz vor Missbrauch: verschlüsselte Hashwerte von Adresse und IP-Adresse, nach 24 Stunden gelöscht
 *   meta       zufälliger Schlüssel für diese Hashwerte
 * Kennwörter von Links und Cookies stehen nie im Klartext in der Datei. Konten ohne Anmeldung seit zwei Jahren
 * werden gelöscht. Es gibt keine Passwörter.
 *
 * Schutz ohne Captcha und ohne fremde Dienste (wie kontakt.php):
 *   - Änderungen nur per POST mit dem Kopf „X-Requested-With: bondarium-konto“ – fremde Seiten können ihn im
 *     Browser nicht mitschicken (CORS); ein fremder Ursprung (Origin) wird abgewiesen; das Cookie ist SameSite=Strict
 *   - Honigtopf-Feld „website“ im Anmeldeformular
 *   - Obergrenzen für Anmelde-Links: je Adresse, je IP-Adresse und insgesamt (GRENZEN)
 *
 * Status: ok · methode · anfrage · ursprung · aktion · email · zuviel · versand · link · anmelden · isin · voll ·
 *         speicher (Datenbank nicht nutzbar) · fehler
 * Ändert sich hier etwas an den verarbeiteten Daten, muss die Datenschutzerklärung (rechtliches.html) mit.
 *
 * Lokal testen (PHP-eigener Server, nie auf dem Webserver): php -S 127.0.0.1:8090 – dann gilt der lokale Ursprung,
 * die Cookies kommen ohne „Secure“, und die E-Mail landet in konto-daten/lokal-mail.txt statt im Versand.
 */
declare(strict_types=1);

const LOKAL         = PHP_SAPI === 'cli-server';
const ABSENDER      = 'info@bondarium.com';   // eigenes Postfach bei STRATO, wie kontakt.php
const SEITE         = 'https://www.bondarium.de';
const DATEN         = __DIR__ . '/konto-daten';
const LINK_MINUTEN  = 30;
const SITZUNG_TAGE  = 90;
const RUHE_TAGE     = 730;    // Konto ohne Anmeldung seit so vielen Tagen wird gelöscht
const MAX_FAVORITEN = 200;
const COOKIE        = LOKAL ? 'bondarium-sitzung' : '__Host-bondarium-sitzung';
const COOKIE_MARKE  = 'bondarium-angemeldet';   // für konto.js lesbar: nur „1“ – damit fragt die Seite nur Angemeldete ab
// Obergrenzen für Anmelde-Links: [Schlüssel, Zeitraum in Sekunden, Höchstzahl]
const GRENZEN = [
    ['m', 900, 3], ['m', 86400, 8],       // je E-Mail-Adresse
    ['i', 900, 10], ['i', 86400, 30],     // je IP-Adresse
    ['g', 3600, 60], ['g', 86400, 300],   // insgesamt
];

header('Content-Type: application/json; charset=utf-8');
header('Cache-Control: no-store');
header('X-Robots-Tag: noindex');

function antwort(int $code, string $status, array $mehr = []): void
{
    http_response_code($code);
    echo json_encode(['status' => $status] + $mehr, JSON_UNESCAPED_UNICODE);
    exit;
}

function ursprung(): string
{
    return LOKAL ? 'http://' . ($_SERVER['HTTP_HOST'] ?? 'localhost') : SEITE;
}

function kennwort(): string
{
    return rtrim(strtr(base64_encode(random_bytes(32)), '+/', '-_'), '=');   // 43 Zeichen, URL-tauglich
}

function ist_kennwort($t): bool
{
    return is_string($t) && preg_match('/^[A-Za-z0-9_-]{43}$/', $t) === 1;
}

function ist_isin($s): bool
{
    return is_string($s) && preg_match('/^[A-Z]{2}[A-Z0-9]{9}[0-9]$/', $s) === 1;
}

/** Datenbank öffnen; beim ersten Aufruf Ordner, Schutzdateien und Tabellen anlegen. */
function db(): PDO
{
    static $db = null;
    if ($db !== null) {
        return $db;
    }
    if (!extension_loaded('pdo_sqlite')) {
        antwort(503, 'speicher');
    }
    if (!is_dir(DATEN) && !@mkdir(DATEN, 0700, true) && !is_dir(DATEN)) {
        antwort(503, 'speicher');
    }
    // Der Ordner ist dreifach geschützt: Regel in der .htaccess des Stammordners, eigene .htaccess, zufälliger Dateiname
    if (!is_file(DATEN . '/.htaccess')) {
        @file_put_contents(DATEN . '/.htaccess', "Require all denied\n");
    }
    if (!is_file(DATEN . '/index.html')) {
        @file_put_contents(DATEN . '/index.html', '');
    }
    $sperre = @fopen(DATEN . '/.sperre', 'c');   // zwei erste Aufrufe zugleich sollen nicht zwei Dateien anlegen
    if ($sperre) {
        flock($sperre, LOCK_EX);
    }
    $dateien = glob(DATEN . '/konto-*.sqlite') ?: [];
    sort($dateien);
    $pfad = $dateien[0] ?? DATEN . '/konto-' . bin2hex(random_bytes(16)) . '.sqlite';
    try {
        $db = new PDO('sqlite:' . $pfad, null, null, [PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION, PDO::ATTR_TIMEOUT => 5]);
        $db->exec('PRAGMA foreign_keys = ON');
        if ((int)$db->query('PRAGMA user_version')->fetchColumn() < 1) {
            $db->exec('BEGIN IMMEDIATE');
            $db->exec('CREATE TABLE IF NOT EXISTS nutzer (id INTEGER PRIMARY KEY, email TEXT NOT NULL UNIQUE, erstellt INTEGER NOT NULL, zuletzt INTEGER NOT NULL)');
            $db->exec('CREATE TABLE IF NOT EXISTS favoriten (nutzer INTEGER NOT NULL REFERENCES nutzer(id) ON DELETE CASCADE, isin TEXT NOT NULL, seit INTEGER NOT NULL, PRIMARY KEY (nutzer, isin))');
            $db->exec('CREATE TABLE IF NOT EXISTS links (hash TEXT PRIMARY KEY, email TEXT NOT NULL, isin TEXT, ablauf INTEGER NOT NULL)');
            $db->exec('CREATE TABLE IF NOT EXISTS sitzungen (hash TEXT PRIMARY KEY, nutzer INTEGER NOT NULL REFERENCES nutzer(id) ON DELETE CASCADE, ablauf INTEGER NOT NULL)');
            $db->exec('CREATE TABLE IF NOT EXISTS zaehler (schluessel TEXT NOT NULL, zeit INTEGER NOT NULL)');
            $db->exec('CREATE INDEX IF NOT EXISTS zaehler_i ON zaehler (schluessel, zeit)');
            $db->exec('CREATE TABLE IF NOT EXISTS meta (k TEXT PRIMARY KEY, v TEXT NOT NULL)');
            $db->prepare('INSERT OR IGNORE INTO meta (k, v) VALUES (?, ?)')->execute(['hmac', bin2hex(random_bytes(32))]);
            $db->exec('PRAGMA user_version = 1');
            $db->exec('COMMIT');
        }
    } catch (Throwable $e) {
        error_log('konto.php: Datenbank nicht nutzbar – ' . $e->getMessage());
        antwort(503, 'speicher');
    } finally {
        if ($sperre) {
            flock($sperre, LOCK_UN);
            fclose($sperre);
        }
    }
    return $db;
}

/** Hashwert mit dem Schlüssel aus der Datenbank – ohne ihn lässt sich aus dem Wert nicht auf Adresse oder IP schließen. */
function schluessel_hash(string $wert): string
{
    static $geheim = null;
    if ($geheim === null) {
        $geheim = (string)db()->query("SELECT v FROM meta WHERE k = 'hmac'")->fetchColumn();
    }
    return substr(hash_hmac('sha256', $wert, $geheim), 0, 32);
}

function cookies_setzen(string $wert, int $ablauf): void
{
    $o = ['expires' => $ablauf, 'path' => '/', 'secure' => !LOKAL, 'samesite' => 'Strict'];
    setcookie(COOKIE, $wert, $o + ['httponly' => true]);
    setcookie(COOKIE_MARKE, $wert === '' ? '' : '1', $o + ['httponly' => false]);
}

function cookies_loeschen(): void
{
    cookies_setzen('', 1);
}

/** Angemeldeter Nutzer ['id' => …, 'email' => …] oder null. Verlängert die Anmeldung höchstens einmal je Woche. */
function nutzer(): ?array
{
    $t = $_COOKIE[COOKIE] ?? '';
    if (!ist_kennwort($t)) {
        if (isset($_COOKIE[COOKIE_MARKE])) {
            cookies_loeschen();   // Merker ohne gültiges Cookie: aufräumen, damit die Seite nicht jedes Mal nachfragt
        }
        return null;
    }
    $db = db();
    $jetzt = time();
    $hash = hash('sha256', $t);
    $s = $db->prepare('SELECT s.nutzer AS id, s.ablauf, n.email, n.zuletzt FROM sitzungen s JOIN nutzer n ON n.id = s.nutzer WHERE s.hash = ? AND s.ablauf > ?');
    $s->execute([$hash, $jetzt]);
    $z = $s->fetch(PDO::FETCH_ASSOC);
    if (!$z) {
        cookies_loeschen();
        return null;
    }
    if ((int)$z['ablauf'] - $jetzt < (SITZUNG_TAGE - 7) * 86400) {
        $ablauf = $jetzt + SITZUNG_TAGE * 86400;
        $db->prepare('UPDATE sitzungen SET ablauf = ? WHERE hash = ?')->execute([$ablauf, $hash]);
        cookies_setzen($t, $ablauf);
    }
    if ($jetzt - (int)$z['zuletzt'] > 86400) {
        $db->prepare('UPDATE nutzer SET zuletzt = ? WHERE id = ?')->execute([$jetzt, $z['id']]);
    }
    return ['id' => (int)$z['id'], 'email' => (string)$z['email']];
}

function angemeldet(): array
{
    $n = nutzer();
    if ($n === null) {
        antwort(401, 'anmelden');
    }
    return $n;
}

/** Merkliste, zuletzt Gemerktes zuerst: [[ISIN, Zeitpunkt], …] */
function favoriten(int $id): array
{
    $s = db()->prepare('SELECT isin, seit FROM favoriten WHERE nutzer = ? ORDER BY seit DESC, isin');
    $s->execute([$id]);
    $aus = [];
    foreach ($s->fetchAll(PDO::FETCH_NUM) as $z) {
        $aus[] = [(string)$z[0], (int)$z[1]];
    }
    return $aus;
}

function merke(int $id, string $isin): bool
{
    $db = db();
    $s = $db->prepare('SELECT COUNT(*) FROM favoriten WHERE nutzer = ?');
    $s->execute([$id]);
    if ((int)$s->fetchColumn() >= MAX_FAVORITEN) {
        $s = $db->prepare('SELECT 1 FROM favoriten WHERE nutzer = ? AND isin = ?');
        $s->execute([$id, $isin]);
        return (bool)$s->fetchColumn();
    }
    $db->prepare('INSERT OR IGNORE INTO favoriten (nutzer, isin, seit) VALUES (?, ?, ?)')->execute([$id, $isin, time()]);
    return true;
}

/** Abgelaufenes löschen: Links, Anmeldungen, Zähler; Konten ohne Anmeldung seit RUHE_TAGE. */
function aufraeumen(): void
{
    $db = db();
    $jetzt = time();
    $db->prepare('DELETE FROM links WHERE ablauf < ?')->execute([$jetzt]);
    $db->prepare('DELETE FROM sitzungen WHERE ablauf < ?')->execute([$jetzt]);
    $db->prepare('DELETE FROM zaehler WHERE zeit < ?')->execute([$jetzt - 86400]);
    $db->prepare('DELETE FROM nutzer WHERE zuletzt < ?')->execute([$jetzt - RUHE_TAGE * 86400]);
}

function mail_senden(string $an, string $link): bool
{
    $text = "Hallo,\n\n"
        . "mit diesem Link meldest du dich bei Bondarium an:\n\n"
        . $link . "\n\n"
        . 'Der Link gilt ' . LINK_MINUTEN . " Minuten und nur einmal. Beim ersten Anmelden entsteht dein Konto.\n\n"
        . "Du hast keinen Link angefordert? Dann hat jemand deine Adresse eingegeben. Du musst nichts tun:\n"
        . "Ohne Klick auf den Link entsteht kein Konto.\n\n"
        . "Bondarium – ein Angebot der urbanelo GmbH\n"
        . SEITE . "/rechtliches.html\n";
    if (LOKAL) {
        return file_put_contents(DATEN . '/lokal-mail.txt', "An: $an\n\n$text") !== false;
    }
    $kopf = implode("\r\n", [
        'From: Bondarium <' . ABSENDER . '>',
        'MIME-Version: 1.0',
        'Content-Type: text/plain; charset=UTF-8',
        'Content-Transfer-Encoding: base64',
        'Auto-Submitted: auto-generated',
    ]);
    $betreff = '=?UTF-8?B?' . base64_encode('Dein Anmelde-Link für Bondarium') . '?=';
    return mail($an, $betreff, chunk_split(base64_encode($text)), $kopf, '-f ' . ABSENDER);
}

// ---------- Anfrage prüfen ----------
$methode = $_SERVER['REQUEST_METHOD'] ?? '';
$aktion  = (string)($methode === 'POST' ? ($_POST['aktion'] ?? '') : ($_GET['aktion'] ?? ''));

if ($methode === 'GET') {
    if ($aktion !== 'status') {
        antwort(400, 'aktion');
    }
} elseif ($methode === 'POST') {
    if (($_SERVER['HTTP_X_REQUESTED_WITH'] ?? '') !== 'bondarium-konto') {
        antwort(400, 'anfrage');
    }
    $origin = (string)($_SERVER['HTTP_ORIGIN'] ?? '');
    if ($origin !== '' && $origin !== ursprung()) {
        antwort(403, 'ursprung');
    }
} else {
    header('Allow: GET, POST');
    antwort(405, 'methode');
}

try {
    switch ($aktion) {
        case 'status':
            db();   // auch ohne Anmeldung öffnen: So meldet die Nach-Deploy-Prüfung eine gestörte Datenbank (503 „speicher“)
            $n = nutzer();
            antwort(200, 'ok', $n === null ? ['angemeldet' => false] : ['angemeldet' => true, 'email' => $n['email'], 'favoriten' => favoriten($n['id'])]);
            // no break – antwort() beendet das Skript

        case 'link':
            if ((string)($_POST['website'] ?? '') !== '') {
                antwort(200, 'ok');   // Honigtopf ausgefüllt: so antworten, als wäre alles gut – gesendet wird nichts
            }
            $mail = strtolower(trim((string)($_POST['email'] ?? '')));
            if ($mail === '' || strlen($mail) > 254 || preg_match('/[\r\n]/', $mail) || filter_var($mail, FILTER_VALIDATE_EMAIL) === false) {
                antwort(422, 'email');
            }
            $isin = strtoupper(trim((string)($_POST['isin'] ?? '')));   // Anleihe, die nach dem Anmelden gleich gemerkt wird
            if (!ist_isin($isin)) {
                $isin = null;
            }
            $db = db();
            aufraeumen();
            $jetzt = time();
            $schl = ['m' => 'm:' . schluessel_hash($mail), 'i' => 'i:' . schluessel_hash((string)($_SERVER['REMOTE_ADDR'] ?? '')), 'g' => 'g'];
            $zahl = $db->prepare('SELECT COUNT(*) FROM zaehler WHERE schluessel = ? AND zeit > ?');
            foreach (GRENZEN as [$art, $zeitraum, $max]) {
                $zahl->execute([$schl[$art], $jetzt - $zeitraum]);
                if ((int)$zahl->fetchColumn() >= $max) {
                    antwort(429, 'zuviel');
                }
            }
            $neu = $db->prepare('INSERT INTO zaehler (schluessel, zeit) VALUES (?, ?)');
            foreach ($schl as $s) {
                $neu->execute([$s, $jetzt]);
            }
            $t = kennwort();
            $db->prepare('INSERT INTO links (hash, email, isin, ablauf) VALUES (?, ?, ?, ?)')
               ->execute([hash('sha256', $t), $mail, $isin, $jetzt + LINK_MINUTEN * 60]);
            // Kennwort hinter „#“: Dieser Teil der Adresse wird nicht an den Server geschickt und steht in keinem Log
            if (!mail_senden($mail, ursprung() . '/konto.html#anmelden=' . $t)) {
                $db->prepare('DELETE FROM links WHERE hash = ?')->execute([hash('sha256', $t)]);
                antwort(500, 'versand');
            }
            antwort(200, 'ok', ['minuten' => LINK_MINUTEN]);

        case 'einloesen':
            $t = $_POST['token'] ?? '';
            if (!ist_kennwort($t)) {
                antwort(410, 'link');
            }
            $db = db();
            $jetzt = time();
            $hash = hash('sha256', $t);
            $db->exec('BEGIN IMMEDIATE');
            $s = $db->prepare('SELECT email, isin FROM links WHERE hash = ? AND ablauf > ?');
            $s->execute([$hash, $jetzt]);
            $l = $s->fetch(PDO::FETCH_ASSOC);
            if (!$l) {
                $db->exec('COMMIT');
                antwort(410, 'link');
            }
            $db->prepare('DELETE FROM links WHERE hash = ?')->execute([$hash]);   // gilt nur einmal
            $s = $db->prepare('SELECT id FROM nutzer WHERE email = ?');
            $s->execute([$l['email']]);
            $id = $s->fetchColumn();
            if ($id === false) {
                $db->prepare('INSERT INTO nutzer (email, erstellt, zuletzt) VALUES (?, ?, ?)')->execute([$l['email'], $jetzt, $jetzt]);
                $id = $db->lastInsertId();
            } else {
                $db->prepare('UPDATE nutzer SET zuletzt = ? WHERE id = ?')->execute([$jetzt, $id]);
            }
            $id = (int)$id;
            $sitzung = kennwort();
            $ablauf = $jetzt + SITZUNG_TAGE * 86400;
            $db->prepare('INSERT INTO sitzungen (hash, nutzer, ablauf) VALUES (?, ?, ?)')->execute([hash('sha256', $sitzung), $id, $ablauf]);
            $gemerkt = null;
            if (ist_isin($l['isin']) && merke($id, $l['isin'])) {
                $gemerkt = $l['isin'];
            }
            $db->exec('COMMIT');
            cookies_setzen($sitzung, $ablauf);
            antwort(200, 'ok', ['angemeldet' => true, 'email' => $l['email'], 'favoriten' => favoriten($id), 'gemerkt' => $gemerkt]);

        case 'merken':
        case 'entfernen':
            $n = angemeldet();
            $isin = strtoupper(trim((string)($_POST['isin'] ?? '')));
            if (!ist_isin($isin)) {
                antwort(422, 'isin');
            }
            if ($aktion === 'merken') {
                if (!merke($n['id'], $isin)) {
                    antwort(409, 'voll', ['max' => MAX_FAVORITEN]);
                }
            } else {
                db()->prepare('DELETE FROM favoriten WHERE nutzer = ? AND isin = ?')->execute([$n['id'], $isin]);
            }
            antwort(200, 'ok', ['angemeldet' => true, 'email' => $n['email'], 'favoriten' => favoriten($n['id'])]);

        case 'abmelden':
            $t = $_COOKIE[COOKIE] ?? '';
            if (ist_kennwort($t)) {
                db()->prepare('DELETE FROM sitzungen WHERE hash = ?')->execute([hash('sha256', $t)]);
            }
            cookies_loeschen();
            antwort(200, 'ok', ['angemeldet' => false]);

        case 'loeschen':
            $n = angemeldet();
            $db = db();
            $db->exec('BEGIN IMMEDIATE');
            $db->prepare('DELETE FROM favoriten WHERE nutzer = ?')->execute([$n['id']]);
            $db->prepare('DELETE FROM sitzungen WHERE nutzer = ?')->execute([$n['id']]);
            $db->prepare('DELETE FROM links WHERE email = ?')->execute([$n['email']]);
            $db->prepare('DELETE FROM nutzer WHERE id = ?')->execute([$n['id']]);
            $db->exec('COMMIT');
            cookies_loeschen();
            antwort(200, 'ok', ['angemeldet' => false]);

        default:
            antwort(400, 'aktion');
    }
} catch (Throwable $e) {
    error_log('konto.php: ' . $e->getMessage());
    antwort(500, 'fehler');
}
