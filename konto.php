<?php
/**
 * Benutzerbereich (konto.html, seit 30.09.2026): Konto mit E-Mail-Adresse und Passwort, eine Merkliste für Anleihen und
 * – seit 01.10.2026 – ein Beispieldepot („Mein Depot“: gemerkte Anleihen mit einem gedachten Nennwert, kein echter
 * Bestand). Dokumentation: docs/KONTO.md. Der Browser spricht über konto.js mit diesem Skript; die Antwort ist
 * immer JSON ({"status": …}).
 *
 * Abläufe (seit 30.09.2026 abends mit Passwort; vorher Anmeldung nur per E-Mail-Link):
 *   Registrieren   aktion=registrieren (E-Mail, Passwort) → E-Mail mit Link (24 Stunden). Ein Konto entsteht noch nicht;
 *                  gespeichert wird nur die offene Registrierung mit dem Hashwert des Passworts.
 *                  aktion=bestaetigen (Kennwort des Links, Passwort) → erst jetzt entsteht das Konto. Das Passwort wird
 *                  noch einmal verlangt: Wer nur die E-Mail bekommt, aber das Passwort nicht kennt, kann kein Konto
 *                  anlegen – so lässt sich niemandem ein Konto mit fremdem Passwort unterschieben.
 *   Anmelden       aktion=anmelden (E-Mail, Passwort) → Anmelde-Cookie (HttpOnly, Secure, SameSite=Strict, 90 Tage,
 *                  verlängert sich bei Nutzung).
 *   Vergessen      aktion=vergessen (E-Mail) → E-Mail mit Link (30 Minuten, einmal); aktion=passwort-neu (Kennwort des
 *                  Links, neues Passwort) setzt es, meldet alle Geräte ab und das aktuelle an.
 *   Angemeldet     aktion=status | merken | entfernen | uebernehmen | depot | abmelden | passwort-aendern | loeschen
 *                  uebernehmen (isins, durch Komma getrennt): setzt eine geteilte Merkliste auf die eigene – der Link im
 *                  PDF-Auszug führt auf konto.html#liste=…, die Seite fragt nach, erst der Klick ruft diese Aktion
 *                  depot (isin, nennwert): legt die Anleihe mit diesem Nennwert ins Beispieldepot oder ändert ihn;
 *                  nennwert 0 nimmt sie heraus
 *   Links          führen auf konto.html#bestaetigen=… bzw. #passwort=… – der Teil hinter „#“ erscheint in keinem
 *                  Server-Log; aktion=link-pruefen sagt der Seite, ob der Link noch gilt und zu welcher Adresse er gehört.
 *
 * Gespeichert wird in einer SQLite-Datei im Ordner konto-daten/ (per .htaccess gesperrt, Dateiname zufällig):
 *   nutzer     E-Mail-Adresse, Hashwert des Passworts, angelegt am, zuletzt angemeldet
 *   favoriten  ISIN und Zeitpunkt je Nutzer
 *   depot      Beispieldepot: ISIN, gedachter Nennwert (ganze Zahl in der Währung der Anleihe) und Zeitpunkt je Nutzer
 *   links      offene Registrierungen und Links zum Zurücksetzen: Hashwert des Link-Kennworts, Adresse, Ablauf, bei
 *              Registrierungen der Hashwert des Passworts und die vorgemerkte ISIN – nach Ablauf gelöscht (aufraeumen)
 *   sitzungen  Anmeldungen (nur der Hashwert des Cookies, Ablauf)
 *   zaehler    Schutz vor Missbrauch: verschlüsselte Hashwerte von Adresse und IP-Adresse für verschickte E-Mails und
 *              falsche Passwörter, gezählt werden 24 Stunden, danach gelöscht (aufraeumen)
 *   meta       zufälliger Schlüssel für diese Hashwerte, Zeitpunkt des letzten Aufräumens, ein Vergleichs-Hashwert
 * Passwörter, Link-Kennwörter und Cookies stehen nie im Klartext in der Datei. Passwörter werden mit Argon2id gehasht
 * (wo PHP es nicht kann: bcrypt). Konten ohne Anmeldung seit zwei Jahren werden gelöscht.
 *
 * Schutz ohne Captcha und ohne fremde Dienste (wie kontakt.php):
 *   - Änderungen nur per POST mit dem Kopf „X-Requested-With: bondarium-konto“ – fremde Seiten können ihn im
 *     Browser nicht mitschicken (CORS); ein fremder Ursprung (Origin) wird abgewiesen; das Cookie ist SameSite=Strict
 *   - Passwort: mindestens PW_MIN Zeichen, keine sehr häufigen Passwörter (passwort_gut)
 *   - falsche Passwörter werden gezählt und gebremst (LOGIN_GRENZEN); die Antwort verrät nicht, ob es zu einer
 *     Adresse ein Konto gibt (anmelden, registrieren und vergessen antworten in beiden Fällen gleich)
 *   - Obergrenzen für verschickte E-Mails: je Adresse, je IP-Adresse und insgesamt (GRENZEN); Honigtopf-Feld „website“
 *   - Passwort ändern oder zurücksetzen meldet alle anderen Geräte ab
 *
 * Status: ok · methode · anfrage · ursprung · aktion · email · passwort (zu schwach) · zugang (E-Mail oder Passwort
 *         falsch) · zuviel · versand · link (abgelaufen oder benutzt) · anmelden (nicht angemeldet) · isin · voll ·
 *         nennwert (keine ganze Zahl von 0 bis NENNWERT_MAX) · speicher (Datenbank nicht nutzbar) · fehler
 * Ändert sich hier etwas an den verarbeiteten Daten, muss die Datenschutzerklärung (rechtliches.html) mit – und der
 * Betreiber vorher gefragt werden.
 *
 * Lokal testen (PHP-eigener Server, nie auf dem Webserver): php -S 127.0.0.1:8090 – dann gilt der lokale Ursprung,
 * die Cookies kommen ohne „Secure“, und die E-Mail landet in konto-daten/lokal-mail.txt statt im Versand.
 */
declare(strict_types=1);

const LOKAL              = PHP_SAPI === 'cli-server';
const ABSENDER           = 'info@bondarium.com';   // eigenes Postfach bei STRATO, wie kontakt.php
const SEITE              = 'https://www.bondarium.de';
const DATEN              = __DIR__ . '/konto-daten';
const BESTAETIGEN_STUNDEN = 24;   // Link in der Registrierungs-E-Mail
const RESET_MINUTEN      = 30;    // Link „Passwort vergessen“
const SITZUNG_TAGE       = 90;
const RUHE_TAGE          = 730;   // Konto ohne Anmeldung seit so vielen Tagen wird gelöscht
const MAX_FAVORITEN      = 200;
const MAX_DEPOT          = 10;          // Anleihen im Beispieldepot (Nutzerentscheid 01.10.2026; je Anleihe eine Farbe im Schaubild)
const NENNWERT_MAX       = 100000000;   // gedachter Nennwert je Anleihe, in der Währung der Anleihe
const PW_MIN             = 10;
const PW_MAX             = 200;
const COOKIE             = LOKAL ? 'bondarium-sitzung' : '__Host-bondarium-sitzung';
const COOKIE_MARKE       = 'bondarium-angemeldet';   // für konto.js lesbar: nur „1“ – damit fragt die Seite nur Angemeldete ab
// Obergrenzen für verschickte E-Mails: [Schlüssel, Zeitraum in Sekunden, Höchstzahl]
const GRENZEN = [
    ['m', 900, 3], ['m', 86400, 8],       // je E-Mail-Adresse
    ['i', 900, 10], ['i', 86400, 30],     // je IP-Adresse
    ['g', 3600, 60], ['g', 86400, 300],   // insgesamt
];
// Obergrenzen für falsche Passwörter. „le“ (Adresse und IP-Adresse zusammen) bremst den einzelnen Angreifer, ohne dass
// er den Inhaber des Kontos aussperren kann; „lm“ (Adresse) begrenzt verteiltes Raten, „li“ (IP-Adresse) das Durchprobieren
// vieler Adressen.
const LOGIN_GRENZEN = [
    ['le', 900, 5],
    ['lm', 3600, 30], ['lm', 86400, 100],
    ['li', 900, 30], ['li', 86400, 200],
];
// Sehr häufige Passwörter ab zehn Zeichen (Vergleich in Kleinbuchstaben). Kein Ersatz für ein gutes Passwort, aber die
// ersten Versuche jedes Angreifers scheitern.
const PW_HAEUFIG = [
    '1234567890', '12345678910', '0123456789', '0987654321', '1234567891', '123456789a', '1234567890a', '123456789abc',
    '1234512345', '1q2w3e4r5t', '1q2w3e4r5t6y', '1qaz2wsx3edc', 'qazwsxedcrfv', 'zaq12wsxcde3', 'qwertyuiop', 'qwertzuiop',
    'qwertzuiopü', 'qwerty12345', 'qwertz12345', 'qwerty123456', 'asdfghjkl1', 'asdfghjklö', 'abcdefghij', 'abcdefghijk',
    'abc1234567', 'a123456789', 'password123', 'password1234', 'password12345', 'passwort123', 'passwort1234',
    'passwort12345', 'passw0rd123', 'p@ssw0rd123', 'iloveyou123', 'ichliebedich', 'hallohallo', 'hallo12345',
    'hallo123456', 'willkommen1', 'willkommen123', 'letmein12345', 'welcome12345', 'changeme123', 'geheim12345',
    'geheimgeheim', 'test1234567', 'testtest123', 'administrator', 'admin123456', 'adminadmin1', 'superman123',
    'football123', 'baseball123', 'dragon12345', 'monkey12345', 'sunshine123', 'princess123', 'fcbayern123',
    'dortmund09!', 'schalke04!!', 'sommer2024!', 'sommer2025!', 'sommer2026!', 'winter2025!', 'winter2026!',
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

function laenge(string $s): int
{
    return function_exists('mb_strlen') ? mb_strlen($s, 'UTF-8') : strlen($s);
}

/** E-Mail-Adresse aus dem Formular, klein geschrieben; ungültig → Antwort „email“. */
function email_lesen(): string
{
    $mail = strtolower(trim((string)($_POST['email'] ?? '')));
    if ($mail === '' || strlen($mail) > 254 || preg_match('/[\r\n]/', $mail) || filter_var($mail, FILTER_VALIDATE_EMAIL) === false) {
        antwort(422, 'email');
    }
    return $mail;
}

/** Anleihe, die nach dem Anmelden gleich gemerkt wird (vom Merken-Knopf), oder null. */
function isin_lesen(): ?string
{
    $isin = strtoupper(trim((string)($_POST['isin'] ?? '')));
    return ist_isin($isin) ? $isin : null;
}

/** Mindestanforderung an ein neues Passwort: Länge, mindestens fünf verschiedene Zeichen, nicht häufig, nicht die Adresse. */
function passwort_gut(string $pw, string $mail): bool
{
    $n = laenge($pw);
    if ($n < PW_MIN || $n > PW_MAX) {
        return false;
    }
    $klein = function_exists('mb_strtolower') ? mb_strtolower($pw, 'UTF-8') : strtolower($pw);
    $zeichen = preg_split('//u', $klein, -1, PREG_SPLIT_NO_EMPTY) ?: str_split($klein);
    if (count(array_unique($zeichen)) < 5) {
        return false;   // „aaaaaaaaaa“, „1212121212“
    }
    if (in_array($klein, PW_HAEUFIG, true) || strpos($klein, 'bondarium') !== false) {
        return false;
    }
    $vorn = strstr($mail, '@', true);
    return $klein !== $mail && !($vorn !== false && strlen($vorn) >= 4 && strpos($klein, $vorn) === 0 && $n - laenge($vorn) < 4);
}

/**
 * Passwort für den Hash vorbereiten: SHA-384, Base64 (64 Zeichen). bcrypt wertet nur die ersten 72 Bytes aus und
 * bricht bei einem Nullbyte ab – so zählt jedes Zeichen eines langen Passworts, bei beiden Verfahren gleich.
 */
function pw_vor(string $pw): string
{
    return base64_encode(hash('sha384', $pw, true));
}

function pw_hash(string $pw): string
{
    if (defined('PASSWORD_ARGON2ID')) {
        try {
            $h = password_hash(pw_vor($pw), PASSWORD_ARGON2ID);
            if (is_string($h) && $h !== '') {
                return $h;
            }
        } catch (Throwable $e) {
            error_log('konto.php: Argon2id nicht nutzbar, bcrypt – ' . $e->getMessage());
        }
    }
    return (string)password_hash(pw_vor($pw), PASSWORD_BCRYPT, ['cost' => 12]);
}

/**
 * Passwort gegen den gespeicherten Hashwert prüfen. Ohne Hashwert (kein Konto, Konto ohne Passwort) wird gegen einen
 * Vergleichswert gerechnet, damit die Antwort gleich lange dauert – die Dauer soll nicht verraten, ob es ein Konto gibt.
 */
function pw_stimmt(string $pw, ?string $hash): bool
{
    if ($hash === null || $hash === '') {
        $db = db();
        $leer = $db->query("SELECT v FROM meta WHERE k = 'vergleich'")->fetchColumn();
        if (!is_string($leer) || $leer === '') {
            $leer = pw_hash(bin2hex(random_bytes(16)));
            $db->prepare("INSERT OR REPLACE INTO meta (k, v) VALUES ('vergleich', ?)")->execute([$leer]);
        }
        password_verify(pw_vor($pw), $leer);
        return false;
    }
    return password_verify(pw_vor($pw), $hash);
}

/** Datenbank öffnen; beim ersten Aufruf Ordner, Schutzdateien und Tabellen anlegen, ältere Fassungen nachziehen. */
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
    $sperre = @fopen(DATEN . '/.sperre', 'c');   // zwei Aufrufe zugleich sollen nicht zwei Dateien anlegen oder doppelt umbauen
    if ($sperre) {
        flock($sperre, LOCK_EX);
    }
    $dateien = glob(DATEN . '/konto-*.sqlite') ?: [];
    sort($dateien);
    $pfad = $dateien[0] ?? DATEN . '/konto-' . bin2hex(random_bytes(16)) . '.sqlite';
    try {
        $db = new PDO('sqlite:' . $pfad, null, null, [PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION, PDO::ATTR_TIMEOUT => 5]);
        $db->exec('PRAGMA foreign_keys = ON');
        $fassung = (int)$db->query('PRAGMA user_version')->fetchColumn();
        if ($fassung < 1) {
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
        if ($fassung < 2) {
            // Fassung 2 (30.09.2026): Passwort je Konto; Links tragen ihre Art („neu“ = Registrierung, „passwort“ =
            // Zurücksetzen) und bei Registrierungen den Hashwert des Passworts. Offene Links der Fassung 1 (Anmeldung
            // per Link, 30 Minuten gültig) entfallen. Konten der Fassung 1 haben noch kein Passwort – „Passwort
            // vergessen“ setzt eines.
            $db->exec('BEGIN IMMEDIATE');
            $db->exec('ALTER TABLE nutzer ADD COLUMN pw TEXT');
            $db->exec("ALTER TABLE links ADD COLUMN art TEXT NOT NULL DEFAULT 'neu'");
            $db->exec('ALTER TABLE links ADD COLUMN pw TEXT');
            $db->exec('DELETE FROM links');
            $db->exec('PRAGMA user_version = 2');
            $db->exec('COMMIT');
        }
        if ($fassung < 3) {
            // Fassung 3 (01.10.2026): Beispieldepot – je Nutzer Anleihen mit einem gedachten Nennwert
            $db->exec('BEGIN IMMEDIATE');
            $db->exec('CREATE TABLE IF NOT EXISTS depot (nutzer INTEGER NOT NULL REFERENCES nutzer(id) ON DELETE CASCADE, isin TEXT NOT NULL, nennwert INTEGER NOT NULL, seit INTEGER NOT NULL, PRIMARY KEY (nutzer, isin))');
            $db->exec('PRAGMA user_version = 3');
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

function ip(): string
{
    return (string)($_SERVER['REMOTE_ADDR'] ?? '');
}

/** true, wenn eine der Obergrenzen erreicht ist. $schl: Art → Schlüssel in der Tabelle zaehler. */
function gebremst(array $grenzen, array $schl): bool
{
    $zahl = db()->prepare('SELECT COUNT(*) FROM zaehler WHERE schluessel = ? AND zeit > ?');
    $jetzt = time();
    foreach ($grenzen as [$art, $zeitraum, $max]) {
        $zahl->execute([$schl[$art], $jetzt - $zeitraum]);
        if ((int)$zahl->fetchColumn() >= $max) {
            return true;
        }
    }
    return false;
}

function zaehle(array $schl): void
{
    $neu = db()->prepare('INSERT INTO zaehler (schluessel, zeit) VALUES (?, ?)');
    $jetzt = time();
    foreach ($schl as $s) {
        $neu->execute([$s, $jetzt]);
    }
}

/** Obergrenze für verschickte E-Mails prüfen und den Versand zählen; erreicht → Antwort „zuviel“. */
function versand_zaehlen(string $mail): void
{
    $schl = ['m' => 'm:' . schluessel_hash($mail), 'i' => 'i:' . schluessel_hash(ip()), 'g' => 'g'];
    if (gebremst(GRENZEN, $schl)) {
        antwort(429, 'zuviel');
    }
    zaehle($schl);
}

/** Schlüssel für falsche Passwörter zu einem Bezug (E-Mail-Adresse oder Hashwert eines Links). */
function login_schluessel(string $bezug): array
{
    return ['le' => 'le:' . schluessel_hash($bezug . '|' . ip()), 'lm' => 'lm:' . schluessel_hash($bezug), 'li' => 'li:' . schluessel_hash(ip())];
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

/** Neue Anmeldung für das Konto: frisches Cookie, eine ältere Anmeldung dieses Browsers endet. */
function sitzung_starten(int $id): void
{
    $db = db();
    $alt = $_COOKIE[COOKIE] ?? '';
    if (ist_kennwort($alt)) {
        $db->prepare('DELETE FROM sitzungen WHERE hash = ?')->execute([hash('sha256', $alt)]);
    }
    $t = kennwort();
    $ablauf = time() + SITZUNG_TAGE * 86400;
    $db->prepare('INSERT INTO sitzungen (hash, nutzer, ablauf) VALUES (?, ?, ?)')->execute([hash('sha256', $t), $id, $ablauf]);
    $db->prepare('UPDATE nutzer SET zuletzt = ? WHERE id = ?')->execute([time(), $id]);
    cookies_setzen($t, $ablauf);
}

/** Angemeldeter Nutzer ['id' => …, 'email' => …, 'pw' => Hashwert oder null] oder null. Verlängert die Anmeldung höchstens einmal je Woche. */
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
    $s = $db->prepare('SELECT s.nutzer AS id, s.ablauf, n.email, n.zuletzt, n.pw FROM sitzungen s JOIN nutzer n ON n.id = s.nutzer WHERE s.hash = ? AND s.ablauf > ?');
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
    return ['id' => (int)$z['id'], 'email' => (string)$z['email'], 'pw' => $z['pw'] === null ? null : (string)$z['pw']];
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

/** Beispieldepot in der Reihenfolge des Hineinlegens: [[ISIN, Nennwert, Zeitpunkt], …] */
function depot(int $id): array
{
    $s = db()->prepare('SELECT isin, nennwert, seit FROM depot WHERE nutzer = ? ORDER BY seit, isin');
    $s->execute([$id]);
    $aus = [];
    foreach ($s->fetchAll(PDO::FETCH_NUM) as $z) {
        $aus[] = [(string)$z[0], (int)$z[1], (int)$z[2]];
    }
    return $aus;
}

/** Was die Seite über ein angemeldetes Konto wissen muss */
function konto_stand(int $id, string $email): array
{
    return ['angemeldet' => true, 'email' => $email, 'favoriten' => favoriten($id), 'depot' => depot($id)];
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

/** Stand für die Seite nach Anmelden, Bestätigen oder neuem Passwort; legt die vorgemerkte Anleihe ab. */
function stand(int $id, string $email, ?string $isin): array
{
    $gemerkt = $isin !== null && merke($id, $isin) ? $isin : null;
    return konto_stand($id, $email) + ['gemerkt' => $gemerkt];
}

/**
 * Abgelaufenes löschen: Links, Anmeldungen, Zähler; Konten ohne Anmeldung seit RUHE_TAGE. Läuft höchstens einmal je
 * Stunde – bei jeder Anfrage, die die Datenbank öffnet. Dazu gehört die Nach-Deploy-Prüfung des Workflows (mindestens
 * einmal je Werktag), sodass auch ohne Besucher nichts Abgelaufenes länger als ein Wochenende liegen bleibt.
 */
function aufraeumen(): void
{
    $db = db();
    $jetzt = time();
    $zuletzt = (int)$db->query("SELECT v FROM meta WHERE k = 'aufgeraeumt'")->fetchColumn();
    if ($jetzt - $zuletzt < 3600) {
        return;
    }
    $db->prepare("INSERT OR REPLACE INTO meta (k, v) VALUES ('aufgeraeumt', ?)")->execute([(string)$jetzt]);
    $db->prepare('DELETE FROM links WHERE ablauf < ?')->execute([$jetzt]);
    $db->prepare('DELETE FROM sitzungen WHERE ablauf < ?')->execute([$jetzt]);
    $db->prepare('DELETE FROM zaehler WHERE zeit < ?')->execute([$jetzt - 86400]);
    $db->prepare('DELETE FROM nutzer WHERE zuletzt < ?')->execute([$jetzt - RUHE_TAGE * 86400]);
}

/** Gültigen Link lesen (ohne ihn zu verbrauchen) oder Antwort „link“. */
function link_lesen(string $art): array
{
    $t = $_POST['token'] ?? '';
    if (!ist_kennwort($t)) {
        antwort(410, 'link');
    }
    $hash = hash('sha256', $t);
    $s = db()->prepare('SELECT hash, email, isin, pw, art FROM links WHERE hash = ? AND ablauf > ?' . ($art !== '' ? ' AND art = ?' : ''));
    $s->execute($art !== '' ? [$hash, time(), $art] : [$hash, time()]);
    $l = $s->fetch(PDO::FETCH_ASSOC);
    if (!$l) {
        antwort(410, 'link');
    }
    return $l;
}

function mail_senden(string $an, string $betreff, string $text): bool
{
    $text = "Hallo,\n\n" . $text . "\n\nBondarium – ein Angebot der urbanelo GmbH\n" . SEITE . "/rechtliches.html\n";
    if (LOKAL) {
        return file_put_contents(DATEN . '/lokal-mail.txt', "An: $an\nBetreff: $betreff\n\n$text") !== false;
    }
    $kopf = implode("\r\n", [
        'From: Bondarium <' . ABSENDER . '>',
        'MIME-Version: 1.0',
        'Content-Type: text/plain; charset=UTF-8',
        'Content-Transfer-Encoding: base64',
        'Auto-Submitted: auto-generated',
    ]);
    return mail($an, '=?UTF-8?B?' . base64_encode($betreff) . '?=', chunk_split(base64_encode($text)), $kopf, '-f ' . ABSENDER);
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
            aufraeumen();   // öffnet die Datenbank auch ohne Anmeldung: So meldet die Nach-Deploy-Prüfung eine Störung (503 „speicher“)
            $n = nutzer();
            antwort(200, 'ok', $n === null ? ['angemeldet' => false] : konto_stand($n['id'], $n['email']));
            // no break – antwort() beendet das Skript

        case 'registrieren':
            if ((string)($_POST['website'] ?? '') !== '') {
                antwort(200, 'ok', ['stunden' => BESTAETIGEN_STUNDEN]);   // Honigtopf ausgefüllt: so antworten, als wäre alles gut
            }
            $mail = email_lesen();
            $pw = (string)($_POST['passwort'] ?? '');
            if (!passwort_gut($pw, $mail)) {
                antwort(422, 'passwort', ['min' => PW_MIN]);
            }
            $isin = isin_lesen();
            $db = db();
            aufraeumen();
            versand_zaehlen($mail);
            $pwHash = pw_hash($pw);   // immer rechnen – auch wenn es das Konto schon gibt (gleiche Dauer, gleiche Antwort)
            $s = $db->prepare('SELECT 1 FROM nutzer WHERE email = ?');
            $s->execute([$mail]);
            if ($s->fetchColumn()) {
                $ok = mail_senden($mail, 'Dein Konto bei Bondarium', "für diese E-Mail-Adresse gibt es schon ein Konto bei Bondarium. Melde dich mit deinem Passwort an:\n\n"
                    . ursprung() . "/konto.html\n\n"
                    . "Passwort vergessen? Auf derselben Seite kannst du ein neues setzen.\n\n"
                    . 'Du wolltest dich gar nicht registrieren? Dann hat jemand deine Adresse eingegeben. Du musst nichts tun; an deinem Konto ändert sich nichts.');
            } else {
                $t = kennwort();
                $db->prepare("INSERT INTO links (hash, email, isin, ablauf, art, pw) VALUES (?, ?, ?, ?, 'neu', ?)")
                   ->execute([hash('sha256', $t), $mail, $isin, time() + BESTAETIGEN_STUNDEN * 3600, $pwHash]);
                // Kennwort hinter „#“: Dieser Teil der Adresse wird nicht an den Server geschickt und steht in keinem Log
                $ok = mail_senden($mail, 'Bestätige deine E-Mail-Adresse für Bondarium', "bitte bestätige deine E-Mail-Adresse, damit dein Konto bei Bondarium entsteht:\n\n"
                    . ursprung() . '/konto.html#bestaetigen=' . $t . "\n\n"
                    . 'Der Link gilt ' . BESTAETIGEN_STUNDEN . " Stunden. Auf der Seite gibst du dein Passwort noch einmal ein.\n\n"
                    . "Du hast dich nicht registriert? Dann hat jemand deine Adresse eingegeben. Du musst nichts tun:\n"
                    . 'Ohne den Link und das Passwort entsteht kein Konto, und die Angaben werden nach Ablauf gelöscht.');
                if (!$ok) {
                    $db->prepare('DELETE FROM links WHERE hash = ?')->execute([hash('sha256', $t)]);
                }
            }
            if (!$ok) {
                antwort(500, 'versand');
            }
            antwort(200, 'ok', ['stunden' => BESTAETIGEN_STUNDEN]);

        case 'link-pruefen':
            $l = link_lesen('');
            antwort(200, 'ok', ['art' => $l['art'], 'email' => $l['email']]);

        case 'bestaetigen':
            $l = link_lesen('neu');
            $pw = (string)($_POST['passwort'] ?? '');
            $db = db();
            $schl = login_schluessel($l['hash']);
            if (gebremst(LOGIN_GRENZEN, $schl)) {
                antwort(429, 'zuviel');
            }
            if (!pw_stimmt($pw, $l['pw'])) {
                zaehle($schl);
                antwort(401, 'zugang');
            }
            $db->exec('BEGIN IMMEDIATE');
            $db->prepare("DELETE FROM links WHERE email = ? AND art = 'neu'")->execute([$l['email']]);   // gilt nur einmal; ältere Registrierungen derselben Adresse entfallen
            $s = $db->prepare('SELECT 1 FROM nutzer WHERE email = ?');
            $s->execute([$l['email']]);
            if ($s->fetchColumn()) {
                $db->exec('COMMIT');
                antwort(410, 'link');   // Konto ist inzwischen auf anderem Weg entstanden – normal anmelden
            }
            $jetzt = time();
            $db->prepare('INSERT INTO nutzer (email, erstellt, zuletzt, pw) VALUES (?, ?, ?, ?)')->execute([$l['email'], $jetzt, $jetzt, $l['pw']]);
            $id = (int)$db->lastInsertId();
            sitzung_starten($id);
            $aus = stand($id, $l['email'], ist_isin($l['isin']) ? $l['isin'] : null);
            $db->exec('COMMIT');
            antwort(200, 'ok', $aus);

        case 'anmelden':
            $mail = email_lesen();
            $pw = (string)($_POST['passwort'] ?? '');
            $db = db();
            aufraeumen();
            $schl = login_schluessel($mail);
            if (gebremst(LOGIN_GRENZEN, $schl)) {
                antwort(429, 'zuviel');
            }
            $s = $db->prepare('SELECT id, pw FROM nutzer WHERE email = ?');
            $s->execute([$mail]);
            $z = $s->fetch(PDO::FETCH_ASSOC);
            $hash = $z && $z['pw'] !== null ? (string)$z['pw'] : null;
            if (strlen($pw) > 4 * PW_MAX || !pw_stimmt($pw, $hash)) {
                zaehle($schl);
                antwort(401, 'zugang');
            }
            $id = (int)$z['id'];
            if (password_needs_rehash($hash, defined('PASSWORD_ARGON2ID') ? PASSWORD_ARGON2ID : PASSWORD_BCRYPT, defined('PASSWORD_ARGON2ID') ? [] : ['cost' => 12])) {
                $db->prepare('UPDATE nutzer SET pw = ? WHERE id = ?')->execute([pw_hash($pw), $id]);
            }
            $db->prepare('DELETE FROM zaehler WHERE schluessel = ?')->execute([$schl['le']]);
            sitzung_starten($id);
            antwort(200, 'ok', stand($id, $mail, isin_lesen()));

        case 'vergessen':
            if ((string)($_POST['website'] ?? '') !== '') {
                antwort(200, 'ok', ['minuten' => RESET_MINUTEN]);
            }
            $mail = email_lesen();
            $db = db();
            aufraeumen();
            versand_zaehlen($mail);
            $s = $db->prepare('SELECT 1 FROM nutzer WHERE email = ?');
            $s->execute([$mail]);
            if ($s->fetchColumn()) {
                $t = kennwort();
                $db->prepare("INSERT INTO links (hash, email, ablauf, art) VALUES (?, ?, ?, 'passwort')")
                   ->execute([hash('sha256', $t), $mail, time() + RESET_MINUTEN * 60]);
                $ok = mail_senden($mail, 'Neues Passwort für Bondarium', "mit diesem Link setzt du ein neues Passwort für dein Konto bei Bondarium:\n\n"
                    . ursprung() . '/konto.html#passwort=' . $t . "\n\n"
                    . 'Der Link gilt ' . RESET_MINUTEN . " Minuten und nur einmal.\n\n"
                    . 'Du hast das nicht angefordert? Dann musst du nichts tun; dein Passwort bleibt, wie es ist.');
                if (!$ok) {
                    $db->prepare('DELETE FROM links WHERE hash = ?')->execute([hash('sha256', $t)]);
                }
            } else {
                // Auch ohne Konto eine E-Mail: Die Antwort der Seite ist in beiden Fällen gleich, und wer sich in der
                // Adresse geirrt hat, erfährt es hier.
                $ok = mail_senden($mail, 'Kein Konto bei Bondarium', "für diese E-Mail-Adresse gibt es kein Konto bei Bondarium – vielleicht hast du dich mit einer anderen Adresse registriert.\n\n"
                    . "Ein neues Konto legst du hier an:\n\n" . ursprung() . "/konto.html\n\n"
                    . 'Du hast das nicht angefordert? Dann hat jemand deine Adresse eingegeben. Du musst nichts tun.');
            }
            if (!$ok) {
                antwort(500, 'versand');
            }
            antwort(200, 'ok', ['minuten' => RESET_MINUTEN]);

        case 'passwort-neu':
            $l = link_lesen('passwort');
            $pw = (string)($_POST['passwort'] ?? '');
            if (!passwort_gut($pw, $l['email'])) {
                antwort(422, 'passwort', ['min' => PW_MIN]);
            }
            $db = db();
            $pwHash = pw_hash($pw);
            $db->exec('BEGIN IMMEDIATE');
            $db->prepare("DELETE FROM links WHERE email = ? AND art = 'passwort'")->execute([$l['email']]);   // gilt nur einmal
            $s = $db->prepare('SELECT id FROM nutzer WHERE email = ?');
            $s->execute([$l['email']]);
            $id = $s->fetchColumn();
            if ($id === false) {
                $db->exec('COMMIT');
                antwort(410, 'link');   // Konto inzwischen gelöscht
            }
            $id = (int)$id;
            $db->prepare('UPDATE nutzer SET pw = ? WHERE id = ?')->execute([$pwHash, $id]);
            $db->prepare('DELETE FROM sitzungen WHERE nutzer = ?')->execute([$id]);   // alle Geräte abmelden
            $db->prepare('DELETE FROM zaehler WHERE schluessel = ?')->execute(['lm:' . schluessel_hash($l['email'])]);
            sitzung_starten($id);
            $aus = stand($id, $l['email'], null);
            $db->exec('COMMIT');
            antwort(200, 'ok', $aus);

        case 'passwort-aendern':
            $n = angemeldet();
            $alt = (string)($_POST['alt'] ?? '');
            $pw = (string)($_POST['passwort'] ?? '');
            $db = db();
            $schl = login_schluessel($n['email']);
            if (gebremst(LOGIN_GRENZEN, $schl)) {
                antwort(429, 'zuviel');
            }
            if (!pw_stimmt($alt, $n['pw'])) {
                zaehle($schl);
                antwort(403, 'zugang');
            }
            if (!passwort_gut($pw, $n['email'])) {
                antwort(422, 'passwort', ['min' => PW_MIN]);
            }
            $db->prepare('UPDATE nutzer SET pw = ? WHERE id = ?')->execute([pw_hash($pw), $n['id']]);
            $db->prepare('DELETE FROM sitzungen WHERE nutzer = ? AND hash <> ?')->execute([$n['id'], hash('sha256', (string)$_COOKIE[COOKIE])]);   // andere Geräte abmelden
            $db->prepare("DELETE FROM links WHERE email = ? AND art = 'passwort'")->execute([$n['email']]);
            mail_senden($n['email'], 'Dein Passwort bei Bondarium wurde geändert', "das Passwort deines Kontos bei Bondarium wurde soeben geändert. Alle anderen Geräte sind abgemeldet.\n\n"
                . "Das warst nicht du? Dann setze sofort ein neues Passwort – auf dieser Seite über „Passwort vergessen“:\n\n" . ursprung() . '/konto.html');
            antwort(200, 'ok');

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
            antwort(200, 'ok', konto_stand($n['id'], $n['email']));

        case 'uebernehmen':
            // Geteilte Merkliste (Link im PDF-Auszug, seit 01.10.2026): alle gültigen ISINs, die noch fehlen, bis die Merkliste voll ist
            $n = angemeldet();
            $isins = [];
            foreach (explode(',', strtoupper((string)($_POST['isins'] ?? ''))) as $i) {
                $i = trim($i);
                if (ist_isin($i)) {
                    $isins[$i] = true;
                }
                if (count($isins) >= MAX_FAVORITEN) {
                    break;
                }
            }
            if (!$isins) {
                antwort(422, 'isin');
            }
            $db = db();
            $db->exec('BEGIN IMMEDIATE');
            $s = $db->prepare('SELECT isin FROM favoriten WHERE nutzer = ?');
            $s->execute([$n['id']]);
            $da = array_flip($s->fetchAll(PDO::FETCH_COLUMN));
            $neu = 0;
            $uebrig = 0;
            $jetzt = time();
            $ein = $db->prepare('INSERT OR IGNORE INTO favoriten (nutzer, isin, seit) VALUES (?, ?, ?)');
            foreach (array_keys($isins) as $i) {
                if (isset($da[$i])) {
                    continue;
                }
                if (count($da) + $neu >= MAX_FAVORITEN) {
                    $uebrig++;
                    continue;
                }
                $ein->execute([$n['id'], $i, $jetzt]);
                $neu++;
            }
            $db->exec('COMMIT');
            antwort(200, 'ok', konto_stand($n['id'], $n['email']) + ['neu' => $neu, 'uebrig' => $uebrig, 'max' => MAX_FAVORITEN]);

        case 'depot':
            $n = angemeldet();
            $isin = strtoupper(trim((string)($_POST['isin'] ?? '')));
            if (!ist_isin($isin)) {
                antwort(422, 'isin');
            }
            $roh = trim((string)($_POST['nennwert'] ?? ''));
            if (!preg_match('/^\d{1,9}$/', $roh) || (int)$roh > NENNWERT_MAX) {
                antwort(422, 'nennwert', ['max' => NENNWERT_MAX]);
            }
            $db = db();
            if ((int)$roh === 0) {
                $db->prepare('DELETE FROM depot WHERE nutzer = ? AND isin = ?')->execute([$n['id'], $isin]);
            } else {
                $db->exec('BEGIN IMMEDIATE');
                $s = $db->prepare('SELECT 1 FROM depot WHERE nutzer = ? AND isin = ?');
                $s->execute([$n['id'], $isin]);
                if ($s->fetchColumn()) {
                    $db->prepare('UPDATE depot SET nennwert = ? WHERE nutzer = ? AND isin = ?')->execute([(int)$roh, $n['id'], $isin]);
                } else {
                    $s = $db->prepare('SELECT COUNT(*) FROM depot WHERE nutzer = ?');
                    $s->execute([$n['id']]);
                    if ((int)$s->fetchColumn() >= MAX_DEPOT) {
                        $db->exec('COMMIT');
                        antwort(409, 'voll', ['max' => MAX_DEPOT]);
                    }
                    $db->prepare('INSERT INTO depot (nutzer, isin, nennwert, seit) VALUES (?, ?, ?, ?)')->execute([$n['id'], $isin, (int)$roh, time()]);
                }
                $db->exec('COMMIT');
            }
            antwort(200, 'ok', konto_stand($n['id'], $n['email']));

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
            if ($n['pw'] !== null) {   // Konten aus der Zeit der Link-Anmeldung haben noch kein Passwort
                $schl = login_schluessel($n['email']);
                if (gebremst(LOGIN_GRENZEN, $schl)) {
                    antwort(429, 'zuviel');
                }
                if (!pw_stimmt((string)($_POST['passwort'] ?? ''), $n['pw'])) {
                    zaehle($schl);
                    antwort(403, 'zugang');
                }
            }
            $db->exec('BEGIN IMMEDIATE');
            $db->prepare('DELETE FROM favoriten WHERE nutzer = ?')->execute([$n['id']]);
            $db->prepare('DELETE FROM depot WHERE nutzer = ?')->execute([$n['id']]);
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
