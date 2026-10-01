<?php
/**
 * Euro-Referenzkurse der EZB – immer der zuletzt veröffentlichte Stand (seit 01.10.2026, Nutzerwunsch: „die EZB-Kurse
 * sollen auch immer aktuell sein“). „Mein Depot“ (konto.html) rechnet damit Anleihen in fremder Währung in Euro um.
 *
 * Der tägliche Datenlauf um 10 Uhr schreibt wechselkurse.json (scripts/update_wechselkurse.py) – die EZB veröffentlicht
 * ihre Kurse aber erst gegen 16 Uhr. Deshalb fragt dieses Skript selbst bei der EZB nach: höchstens alle 30 Minuten,
 * und gar nicht mehr, sobald der Kurs von heute da ist. Der Stand liegt in wechselkurs-daten/kurse.json. Scheitert der
 * Abruf, gilt der bisherige Stand weiter (neuer Versuch nach 5 Minuten); gibt es noch keinen, die Datei aus dem Datenlauf.
 *
 * Antwort wie wechselkurse.json: {"stand": "JJJJ-MM-TT", "quelle": …, "kurse": {"USD": 1.1355, …}} (1 Euro = x Einheiten).
 * Keine Eingaben, keine Cookies, nichts über den Besucher wird gespeichert; der Browser spricht nur mit bondarium.de.
 *
 * Lokal testen: php -S 127.0.0.1:8091 – dann /wechselkurse.php aufrufen.
 */
declare(strict_types=1);

const FX_QUELLE       = 'https://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml';
const FX_ORDNER       = __DIR__ . '/wechselkurs-daten';
const FX_DATEI        = FX_ORDNER . '/kurse.json';
const FX_PAUSE        = 1800;   // frühestens nach 30 Minuten wieder bei der EZB nachsehen
const FX_PAUSE_FEHLER = 300;    // nach einem gescheiterten Abruf: neuer Versuch nach 5 Minuten

date_default_timezone_set('Europe/Berlin');

/** Kursdatei lesen; null, wenn sie fehlt oder nicht wie erwartet aussieht */
function fx_lesen(string $pfad): ?array
{
    $text = @file_get_contents($pfad);
    $d = is_string($text) ? json_decode($text, true) : null;
    if (!is_array($d) || !isset($d['stand'], $d['kurse']) || !is_array($d['kurse'])) return null;
    if (!preg_match('/^\d{4}-\d{2}-\d{2}$/', (string) $d['stand']) || count($d['kurse']) < 20) return null;
    return $d;
}

/** Tageskurse bei der EZB holen; null, wenn der Abruf scheitert oder die Antwort unplausibel ist */
function fx_holen(): ?array
{
    if (!function_exists('curl_init')) return null;
    $ch = curl_init(FX_QUELLE);
    curl_setopt_array($ch, [
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_CONNECTTIMEOUT => 4,
        CURLOPT_TIMEOUT        => 6,
        CURLOPT_FOLLOWLOCATION => false,
        CURLOPT_PROTOCOLS      => CURLPROTO_HTTPS,
        CURLOPT_USERAGENT      => 'bondarium-datenabruf',
    ]);
    $xml = curl_exec($ch);
    $code = (int) curl_getinfo($ch, CURLINFO_HTTP_CODE);
    if (!is_string($xml) || $code !== 200 || strlen($xml) > 100000) return null;
    if (!preg_match('/<Cube\s+time=[\'"](\d{4}-\d{2}-\d{2})[\'"]/', $xml, $tag)) return null;
    preg_match_all('/<Cube\s+currency=[\'"]([A-Z]{3})[\'"]\s+rate=[\'"]([0-9.]+)[\'"]/', $xml, $treffer, PREG_SET_ORDER);
    $kurse = [];
    foreach ($treffer as $t) {
        $v = (float) $t[2];
        if ($v > 0) $kurse[$t[1]] = $v;
    }
    // Plausibilität wie im Datenlauf: genug Währungen, Dollar in einer glaubhaften Spanne
    if (count($kurse) < 20 || !isset($kurse['USD']) || $kurse['USD'] <= 0.5 || $kurse['USD'] >= 2) return null;
    ksort($kurse);
    return ['stand' => $tag[1], 'kurse' => $kurse];
}

header('Content-Type: application/json; charset=utf-8');
header('Cache-Control: max-age=900');
header('X-Robots-Tag: noindex');
header('X-Content-Type-Options: nosniff');
if (($_SERVER['REQUEST_METHOD'] ?? 'GET') !== 'GET') {
    http_response_code(405);
    echo '{"status":"methode"}';
    exit;
}

$jetzt = time();
$fest  = fx_lesen(__DIR__ . '/wechselkurse.json');   // Stand des letzten Datenlaufs – Rückfall
$lager = fx_lesen(FX_DATEI);
$faellig = $lager === null || $jetzt - (int) ($lager['geprueft'] ?? 0) >= FX_PAUSE;
if ($lager !== null && $lager['stand'] === date('Y-m-d')) $faellig = false;   // Kurs von heute ist da – bis morgen kommt kein neuer

if ($faellig) {
    if (!is_dir(FX_ORDNER)) @mkdir(FX_ORDNER, 0700, true);
    if (is_dir(FX_ORDNER) && !is_file(FX_ORDNER . '/.htaccess')) @file_put_contents(FX_ORDNER . '/.htaccess', "Require all denied\n");
    $sperre = is_dir(FX_ORDNER) ? @fopen(FX_ORDNER . '/.sperre', 'c') : false;
    // nur ein Abruf zugleich: Wer die Sperre nicht bekommt, liefert den bisherigen Stand
    if ($sperre && flock($sperre, LOCK_EX | LOCK_NB)) {
        $neu = fx_holen();
        if ($neu !== null) {
            $lager = $neu + ['geprueft' => $jetzt];
        } else {
            $lager = $lager ?? $fest;
            if ($lager !== null) $lager['geprueft'] = $jetzt - FX_PAUSE + FX_PAUSE_FEHLER;
        }
        if ($lager !== null) {
            $tmp = FX_DATEI . '.' . bin2hex(random_bytes(4)) . '.tmp';
            $inhalt = json_encode(['stand' => $lager['stand'], 'geprueft' => $lager['geprueft'], 'kurse' => $lager['kurse']]);
            if (@file_put_contents($tmp, $inhalt) !== false) {
                if (!@rename($tmp, FX_DATEI)) @unlink($tmp);
            }
        }
        flock($sperre, LOCK_UN);
    }
    if ($sperre) fclose($sperre);
}

// der neuere von beiden: eigener Abruf oder Datei aus dem Datenlauf
$aus = $lager;
if ($fest !== null && ($aus === null || $fest['stand'] > $aus['stand'])) $aus = $fest;
if ($aus === null) {
    http_response_code(503);
    echo '{"status":"fehler"}';
    exit;
}
echo json_encode(
    ['stand' => $aus['stand'], 'quelle' => 'Europäische Zentralbank, Euro-Referenzkurse', 'kurse' => $aus['kurse']],
    JSON_UNESCAPED_UNICODE
);
