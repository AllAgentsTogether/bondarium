<?php
/**
 * Besucherzählung (seit 01.10.2026, Dokumentation: docs/STATISTIK.md). site.js meldet jeden Seitenaufruf per
 * navigator.sendBeacon hierher: Pfad der Seite (p), Herkunft (r = document.referrer) und utm_source (q). Die Antwort
 * ist immer leer (204) – auch bei abgewiesenen Meldungen, damit niemand ausprobieren kann, was gezählt wird.
 *
 * Ohne Cookies und ohne Speicherung im Browser. „Besucher“ = verschiedene Besucher an einem Tag: Aus IP-Adresse und
 * Browser-Kennung entsteht mit einem zufälligen Tages-Schlüssel eine Prüfsumme (HMAC). Der Schlüssel wird jeden Tag
 * neu erzeugt und der alte gelöscht, die Prüfsummen des Vortags ebenso – danach lässt sich kein Besucher mehr
 * wiedererkennen. Die IP-Adresse wird nicht gespeichert.
 *
 * Gespeichert wird in einer SQLite-Datei im Ordner statistik-daten/ (per .htaccess gesperrt, Dateiname zufällig):
 *   tage      je Tag: Besucher, Seitenaufrufe, aussortierte Robot-Abrufe
 *   seiten    je Tag und Seite: Aufrufe
 *   herkunft  je Tag, Gruppe (Suchmaschinen, KI-Assistenten, Andere Websites, Direkt) und Quelle (nur der Name der
 *             Website, nie die volle Adresse): Besucher – gezählt beim ersten Aufruf eines Besuchers am Tag
 *   geraete   je Tag und Geräteart (Handy, Computer, Tablet, aus der Browser-Kennung): Besucher
 *   heute     Prüfsummen der Besucher von heute und ihre Aufrufe (Bremse gegen Massenmeldungen) – täglich gelöscht
 *   meta      Tages-Schlüssel und sein Datum, zuletzt verschickter Bericht
 * Tageswerte älter als AUFBEWAHREN_MONATE werden gelöscht.
 *
 * Täglicher Bericht: Der erste Aufruf ab BERICHT_STUNDE Uhr (Berlin) verschickt den PDF-Bericht des Vortags an
 * BERICHT_AN (statistik-bericht.php) – nach der Antwort an den Browser, der Besucher wartet also nicht darauf.
 *
 * Nicht gezählt: Robots und automatisierte Browser (Browser-Kennung), Browser mit „Global Privacy Control“ oder
 * „Do Not Track“ (prüft site.js), Seiten, die es nicht gibt, fremde Ursprünge.
 * Ändert sich hier etwas an den verarbeiteten Daten, muss die Datenschutzerklärung (rechtliches.html#statistik) mit –
 * und der Betreiber vorher gefragt werden.
 *
 * Testmail: POST aktion=testmail mit Kopf X-Trigger-Key (Workflow „Statistik – Testmail“) – Bericht über den laufenden Tag;
 * mit art=erinnerung stattdessen eine Beispiel-Erinnerung vor einer Fälligkeit (erinnerung.php).
 *
 * Erinnerungen (seit 02.10.2026): Der erste gezählte Aufruf ab ERINNERUNG_STUNDE Uhr stößt auch den täglichen Versand der
 * E-Mails „30 Tage vor jeder Fälligkeit“ an (erinnerung.php, Daten in konto-daten/) – ebenfalls erst nach der Antwort.
 *
 * Lokal testen (PHP-eigener Server): php -S 127.0.0.1:8090 – dann gilt der lokale Ursprung, und der Bericht landet
 * als PDF und E-Mail-Text in statistik-daten/ statt im Versand. Bericht von Hand: php aufruf.php bericht [JJJJ-MM-TT]
 */
declare(strict_types=1);

const LOKAL              = PHP_SAPI === 'cli-server' || PHP_SAPI === 'cli';
const SEITE              = 'https://www.bondarium.de';
const STAT_DATEN         = __DIR__ . '/statistik-daten';
const BERICHT_AN         = 'info@bondarium.com';
const BERICHT_STUNDE     = 6;
const AUFBEWAHREN_MONATE = 25;
const MAX_AUFRUFE        = 300;   // mehr Aufrufe je Besucher und Tag gelten als automatisiert
const ROBOT = '~bot|crawl|spider|slurp|archiver|facebookexternalhit|embedly|preview|headless|phantomjs|selenium|puppeteer|'
    . 'playwright|lighthouse|pagespeed|gtmetrix|pingdom|uptime|monitor|python|curl|wget|java/|go-http|okhttp|axios|'
    . 'node-fetch|scrapy|httpclient|libwww|^mozilla/5\.0$~i';

date_default_timezone_set('Europe/Berlin');

function stat_db(): PDO
{
    static $db = null;
    if ($db !== null) return $db;
    if (!extension_loaded('pdo_sqlite')) throw new RuntimeException('pdo_sqlite fehlt');
    if (!is_dir(STAT_DATEN) && !@mkdir(STAT_DATEN, 0700, true) && !is_dir(STAT_DATEN)) throw new RuntimeException('Ordner');
    // dreifach geschützt wie konto-daten/: Regel in der .htaccess des Stammordners, eigene .htaccess, zufälliger Dateiname
    if (!is_file(STAT_DATEN . '/.htaccess')) @file_put_contents(STAT_DATEN . '/.htaccess', "Require all denied\n");
    if (!is_file(STAT_DATEN . '/index.html')) @file_put_contents(STAT_DATEN . '/index.html', '');
    $sperre = @fopen(STAT_DATEN . '/.sperre', 'c');   // zwei Aufrufe zugleich sollen nicht zwei Dateien anlegen
    if ($sperre) flock($sperre, LOCK_EX);
    $dateien = glob(STAT_DATEN . '/statistik-*.sqlite') ?: [];
    sort($dateien);
    $pfad = $dateien[0] ?? STAT_DATEN . '/statistik-' . bin2hex(random_bytes(16)) . '.sqlite';
    try {
        $db = new PDO('sqlite:' . $pfad, null, null, [PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION, PDO::ATTR_TIMEOUT => 5]);
        if ((int)$db->query('PRAGMA user_version')->fetchColumn() < 1) {
            $db->exec('BEGIN IMMEDIATE');
            $db->exec('CREATE TABLE IF NOT EXISTS tage (tag TEXT PRIMARY KEY, besucher INTEGER NOT NULL DEFAULT 0, aufrufe INTEGER NOT NULL DEFAULT 0, robots INTEGER NOT NULL DEFAULT 0)');
            $db->exec('CREATE TABLE IF NOT EXISTS seiten (tag TEXT NOT NULL, pfad TEXT NOT NULL, aufrufe INTEGER NOT NULL, PRIMARY KEY (tag, pfad))');
            $db->exec('CREATE TABLE IF NOT EXISTS herkunft (tag TEXT NOT NULL, gruppe TEXT NOT NULL, quelle TEXT NOT NULL, besucher INTEGER NOT NULL, PRIMARY KEY (tag, gruppe, quelle))');
            $db->exec('CREATE TABLE IF NOT EXISTS geraete (tag TEXT NOT NULL, geraet TEXT NOT NULL, besucher INTEGER NOT NULL, PRIMARY KEY (tag, geraet))');
            $db->exec('CREATE TABLE IF NOT EXISTS heute (kennung TEXT PRIMARY KEY, aufrufe INTEGER NOT NULL)');
            $db->exec('CREATE TABLE IF NOT EXISTS meta (k TEXT PRIMARY KEY, v TEXT NOT NULL)');
            $db->exec('PRAGMA user_version = 1');
            $db->exec('COMMIT');
        }
    } finally {
        if ($sperre) { flock($sperre, LOCK_UN); fclose($sperre); }
    }
    return $db;
}

function stat_meta(PDO $db, string $k): ?string
{
    $s = $db->prepare('SELECT v FROM meta WHERE k = ?'); $s->execute([$k]);
    $v = $s->fetchColumn();
    return $v === false ? null : (string)$v;
}

function stat_meta_setzen(PDO $db, string $k, string $v): void
{
    $db->prepare('INSERT INTO meta (k, v) VALUES (?, ?) ON CONFLICT (k) DO UPDATE SET v = excluded.v')->execute([$k, $v]);
}

/** Herkunft eines Besuchers → [Gruppe, Quelle]. Gespeichert wird nur der Name der Website, nie Pfad oder Suchbegriff. */
function stat_herkunft(string $referrer, string $utm): array
{
    $ki = [
        '~(^|\.)(chatgpt\.com|chat\.openai\.com)$~' => 'ChatGPT', '~(^|\.)perplexity\.ai$~' => 'Perplexity',
        '~^copilot\.microsoft\.com$~' => 'Copilot', '~^gemini\.google\.com$~' => 'Gemini', '~(^|\.)claude\.ai$~' => 'Claude',
        '~^chat\.mistral\.ai$~' => 'Mistral', '~^chat\.deepseek\.com$~' => 'DeepSeek', '~(^|\.)you\.com$~' => 'You.com',
        '~(^|\.)meta\.ai$~' => 'Meta AI', '~(^|\.)grok\.com$~' => 'Grok', '~(^|\.)phind\.com$~' => 'Phind',
    ];
    $suche = [
        '~(^|\.)google\.[a-z.]+$~' => 'Google', '~(^|\.)bing\.com$~' => 'Bing', '~(^|\.)duckduckgo\.com$~' => 'DuckDuckGo',
        '~(^|\.)ecosia\.org$~' => 'Ecosia', '~(^|\.)startpage\.com$~' => 'Startpage', '~(^|\.)yahoo\.[a-z.]+$~' => 'Yahoo',
        '~(^|\.)qwant\.com$~' => 'Qwant', '~^search\.brave\.com$~' => 'Brave', '~(^|\.)yandex\.[a-z.]+$~' => 'Yandex',
        '~(^|\.)baidu\.com$~' => 'Baidu', '~(^|\.)metager\.(de|org)$~' => 'MetaGer', '~^suche\.t-online\.de$~' => 'T-Online',
        '~^suche\.web\.de$~' => 'WEB.DE', '~^suche\.gmx\.[a-z.]+$~' => 'GMX', '~^suche\.aol\.de$~' => 'AOL',
    ];
    $host = strtolower((string)(parse_url($referrer, PHP_URL_HOST) ?? ''));
    $host = preg_replace('~^(www|m|l|lm|out|mobile)\.~', '', $host);
    if ($host === 't.co') $host = 'x.com';
    if ($host === '' || preg_match('~(^|\.)bondarium\.(de|com)$~', $host)) {
        // ohne Herkunft: ChatGPT & Co. hängen utm_source an ihre Links
        $utm = strtolower($utm);
        foreach ($ki as $muster => $name) if ($utm !== '' && preg_match($muster, $utm)) return ['KI-Assistenten', $name];
        return ['Direkt oder unbekannt', ''];
    }
    foreach ($ki as $muster => $name) if (preg_match($muster, $host)) return ['KI-Assistenten', $name];
    foreach ($suche as $muster => $name) if (preg_match($muster, $host)) return ['Suchmaschinen', $name];
    if (!preg_match('~^[a-z0-9.-]{1,80}$~', $host)) return ['Direkt oder unbekannt', ''];
    return ['Andere Websites', $host];
}

function stat_geraet(string $ua): string
{
    if (preg_match('~iPad|Tablet|Kindle|Silk|Android(?!.*Mobile)~i', $ua)) return 'Tablet';
    if (preg_match('~Mobi|iPhone|iPod|Android~i', $ua)) return 'Handy';
    return 'Computer';
}

/** Seitenpfad prüfen: nur Seiten, die es gibt („/“ oder /name.html im Stammordner) */
function stat_pfad(string $p): ?string
{
    if ($p === '/' || $p === '/index.html') return '/';
    if (!preg_match('~^/([a-z0-9-]{1,60})\.html$~', $p, $m) || $m[1] === '404') return null;
    return is_file(__DIR__ . '/' . $m[1] . '.html') ? $p : null;
}

/** Einen Seitenaufruf zählen */
function stat_zaehlen(string $pfad, string $referrer, string $utm, string $ip, string $ua): void
{
    $db = stat_db();
    $tag = date('Y-m-d');
    $db->exec('BEGIN IMMEDIATE');
    try {
        $db->prepare('INSERT OR IGNORE INTO tage (tag) VALUES (?)')->execute([$tag]);
        if ($ua === '' || preg_match(ROBOT, $ua)) {
            $db->prepare('UPDATE tage SET robots = robots + 1 WHERE tag = ?')->execute([$tag]);
            $db->exec('COMMIT');
            return;
        }
        // Tages-Schlüssel: neuer Tag → neuer Schlüssel, die Prüfsummen von gestern werden gelöscht
        if (stat_meta($db, 'salz_tag') !== $tag) {
            stat_meta_setzen($db, 'salz', bin2hex(random_bytes(32)));
            stat_meta_setzen($db, 'salz_tag', $tag);
            $db->exec('DELETE FROM heute');
        }
        $kennung = substr(hash_hmac('sha256', $ip . "\n" . $ua, (string)stat_meta($db, 'salz')), 0, 32);
        $s = $db->prepare('SELECT aufrufe FROM heute WHERE kennung = ?'); $s->execute([$kennung]);
        $bisher = $s->fetchColumn();
        if ($bisher !== false && (int)$bisher >= MAX_AUFRUFE) {
            $db->prepare('UPDATE tage SET robots = robots + 1 WHERE tag = ?')->execute([$tag]);
            $db->exec('COMMIT');
            return;
        }
        if ($bisher === false) {
            $db->prepare('INSERT INTO heute (kennung, aufrufe) VALUES (?, 1)')->execute([$kennung]);
            [$gruppe, $quelle] = stat_herkunft($referrer, $utm);
            $db->prepare('UPDATE tage SET besucher = besucher + 1 WHERE tag = ?')->execute([$tag]);
            $db->prepare('INSERT INTO herkunft (tag, gruppe, quelle, besucher) VALUES (?, ?, ?, 1) ON CONFLICT (tag, gruppe, quelle) DO UPDATE SET besucher = besucher + 1')
                ->execute([$tag, $gruppe, $quelle]);
            $db->prepare('INSERT INTO geraete (tag, geraet, besucher) VALUES (?, ?, 1) ON CONFLICT (tag, geraet) DO UPDATE SET besucher = besucher + 1')
                ->execute([$tag, stat_geraet($ua)]);
        } else {
            $db->prepare('UPDATE heute SET aufrufe = aufrufe + 1 WHERE kennung = ?')->execute([$kennung]);
        }
        $db->prepare('UPDATE tage SET aufrufe = aufrufe + 1 WHERE tag = ?')->execute([$tag]);
        $db->prepare('INSERT INTO seiten (tag, pfad, aufrufe) VALUES (?, ?, 1) ON CONFLICT (tag, pfad) DO UPDATE SET aufrufe = aufrufe + 1')->execute([$tag, $pfad]);
        $db->exec('COMMIT');
    } catch (Throwable $e) {
        if ($db->inTransaction()) $db->rollBack();
        throw $e;
    }
}

/** Ist der Bericht von gestern fällig? Dann vormerken (nur ein Aufruf verschickt ihn) und den Tag zurückgeben. */
function stat_bericht_faellig(): ?string
{
    if ((int)date('G') < BERICHT_STUNDE) return null;
    $db = stat_db();
    $gestern = date('Y-m-d', strtotime('yesterday'));
    $db->exec('BEGIN IMMEDIATE');
    $fehler = (int)(stat_meta($db, 'bericht_fehler') ?? 0);
    if (stat_meta($db, 'bericht') === $gestern || time() - $fehler < 3600) { $db->exec('COMMIT'); return null; }   // nach einem Fehler höchstens stündlich
    stat_meta_setzen($db, 'bericht', $gestern);
    $db->exec('COMMIT');
    return $gestern;
}

// ---------- Kommandozeile (nur lokal): Bericht oder Erinnerungen von Hand ----------
if (PHP_SAPI === 'cli') {
    if (($argv[1] ?? '') === 'erinnerung') {
        require __DIR__ . '/erinnerung.php';
        [$ok, $fehl] = erinnerungen_senden();
        echo "Erinnerungen: $ok verschickt, $fehl fehlgeschlagen (konto-daten/lokal-mail.txt)\n";
        exit;
    }
    if (($argv[1] ?? '') !== 'bericht') { fwrite(STDERR, "Aufruf: php aufruf.php bericht [JJJJ-MM-TT] | erinnerung\n"); exit(1); }
    require __DIR__ . '/statistik-bericht.php';
    $tag = $argv[2] ?? date('Y-m-d', strtotime('yesterday'));
    echo bericht_senden(stat_db(), $tag) ? "Bericht für $tag geschrieben (statistik-daten/)\n" : "Fehler\n";
    exit;
}

// ---------- Meldung aus dem Browser ----------
header('Cache-Control: no-store');
header('X-Robots-Tag: noindex');
http_response_code(204);
if (($_SERVER['REQUEST_METHOD'] ?? '') !== 'POST') exit;
// Testmail (seit 01.10.2026): POST aktion=testmail mit dem Kopf X-Trigger-Key (derselbe Schlüssel wie trigger/refresh.php)
// schickt sofort einen Bericht über den laufenden Tag. Ausgelöst über den Workflow „Statistik – Testmail“; höchstens
// einmal in fünf Minuten.
if (($_POST['aktion'] ?? '') === 'testmail') {
    $cfg = is_file(__DIR__ . '/trigger/refresh-config.php') ? require __DIR__ . '/trigger/refresh-config.php' : [];
    $soll = trim((string)($cfg['secret'] ?? ''));
    if ($soll === '' || !hash_equals($soll, trim((string)($_SERVER['HTTP_X_TRIGGER_KEY'] ?? '')))) { http_response_code(403); exit; }
    $db = stat_db();
    if (time() - (int)(stat_meta($db, 'testmail') ?? 0) < 300) { http_response_code(429); exit; }
    stat_meta_setzen($db, 'testmail', (string)time());
    try {
        if (($_POST['art'] ?? '') === 'erinnerung') {
            require __DIR__ . '/erinnerung.php';
            $ok = erinnerung_testmail(BERICHT_AN);
        } else {
            require __DIR__ . '/statistik-bericht.php';
            $ok = bericht_senden($db, date('Y-m-d'), true);
        }
        $meldung = $ok ? 'gesendet' : 'Versand fehlgeschlagen (mail)';
    } catch (Throwable $e) {
        error_log('aufruf.php Testmail: ' . $e->getMessage());
        $ok = false; $meldung = 'Fehler beim Bauen des Berichts';
    }
    http_response_code($ok ? 200 : 500);
    echo $meldung;
    exit;
}
$ursprung = LOKAL ? 'http://' . ($_SERVER['HTTP_HOST'] ?? '') : SEITE;
$origin = $_SERVER['HTTP_ORIGIN'] ?? '';
$fetchSite = $_SERVER['HTTP_SEC_FETCH_SITE'] ?? '';
if (($origin !== '' && $origin !== $ursprung) || ($fetchSite !== '' && $fetchSite !== 'same-origin')) exit;
$widerspruch = ($_SERVER['HTTP_SEC_GPC'] ?? '') === '1' || ($_SERVER['HTTP_DNT'] ?? '') === '1';   // site.js prüft das auch

$pfad = stat_pfad(substr((string)($_POST['p'] ?? ''), 0, 100));
$bericht = null;
try {
    if ($pfad !== null && !$widerspruch) {
        stat_zaehlen($pfad, substr((string)($_POST['r'] ?? ''), 0, 500), substr((string)($_POST['q'] ?? ''), 0, 100),
            (string)($_SERVER['REMOTE_ADDR'] ?? ''), substr((string)($_SERVER['HTTP_USER_AGENT'] ?? ''), 0, 400));
    }
    $bericht = stat_bericht_faellig();
} catch (Throwable $e) {
    error_log('aufruf.php: ' . $e->getMessage());
}
$erinnerung = false;
if ($pfad !== null) {
    try {
        require __DIR__ . '/erinnerung.php';
        $erinnerung = erinnerung_faellig();
    } catch (Throwable $e) {
        error_log('aufruf.php Erinnerung: ' . $e->getMessage());
    }
}
if ($bericht === null && !$erinnerung) exit;

// Antwort abschließen, dann den Bericht bauen und verschicken bzw. die Erinnerungen
ignore_user_abort(true);
if (function_exists('fastcgi_finish_request')) fastcgi_finish_request();
if ($bericht !== null) {
    try {
        require __DIR__ . '/statistik-bericht.php';
        $ok = bericht_senden(stat_db(), $bericht);
    } catch (Throwable $e) {
        error_log('aufruf.php Bericht: ' . $e->getMessage());
        $ok = false;
    }
    if (!$ok) {
        // beim nächsten Aufruf frühestens in einer Stunde noch einmal versuchen
        $db = stat_db();
        stat_meta_setzen($db, 'bericht', '');
        stat_meta_setzen($db, 'bericht_fehler', (string)time());
    }
}
if ($erinnerung) {
    try {
        erinnerungen_senden();
    } catch (Throwable $e) {
        error_log('aufruf.php Erinnerungen: ' . $e->getMessage());
    }
}
