<?php
/**
 * Sicherung der Datenbanken auf dem Server (seit 03.10.2026, docs/SICHERUNG.md).
 *
 * Der Workflow „Sicherung“ (.github/workflows/sicherung.yml) ruft dieses Skript jede Nacht einmal je Datenbank auf:
 *   POST https://www.bondarium.de/trigger/sicherung.php   Feld db=konto | db=statistik   Kopf X-Trigger-Key: GEHEIM
 *
 * Ablauf: saubere Kopie der SQLite-Datei (VACUUM INTO, auch während Besucher schreiben) → bereinigt (ohne Tages-Schlüssel,
 * Prüfsummen und offene Links) → gzip → Verschlüsselung mit dem
 * öffentlichen Zertifikat sicherung-zertifikat.pem (S/MIME, AES-256) → Antwort. Den privaten Schlüssel zum Öffnen hat nur
 * der Betreiber; den Server verlässt also nie eine lesbare Datenbank – auch nicht, wenn jemand den Schlüssel im Kopf kennt.
 * Zwischendateien entstehen nur im gesperrten Datenordner und werden sofort gelöscht.
 *
 * Antworten: 200 verschlüsselte Datei (application/pkcs7-mime) · 403 falscher Schlüssel · 405 nicht POST · 400 unbekannte
 * Datenbank · 404 Datenbank (noch) nicht angelegt · 500 Fehler beim Kopieren oder Verschlüsseln.
 */
declare(strict_types=1);

/** Feld aus $_POST als Text; eine Liste („feld[]=…“) zählt wie ein leeres Feld – ohne PHP-Warnung im Fehlerprotokoll (T-132). */
function text(array $q, string $k): string
{
    $v = $q[$k] ?? '';
    return is_string($v) ? $v : '';
}

header('Cache-Control: no-store');
header('X-Robots-Tag: noindex');

if (($_SERVER['REQUEST_METHOD'] ?? '') !== 'POST') {
    http_response_code(405);
    header('Allow: POST');
    exit('Method Not Allowed');
}

$cfg = @include __DIR__ . '/refresh-config.php';
$soll = is_array($cfg) && is_string($cfg['secret'] ?? null) ? trim($cfg['secret']) : '';
$ist = $_SERVER['HTTP_X_TRIGGER_KEY'] ?? '';
// Ohne konfigurierten Schlüssel gar nicht erst vergleichen (sonst passte ein leerer Kopf)
if ($soll === '' || !is_string($ist) || !hash_equals($soll, trim($ist))) {
    http_response_code(403);
    exit('Forbidden');
}

// Datenbank → Ordner im Webroot (beide per .htaccess gesperrt) und Namensanfang der Datei (Rest des Namens ist zufällig)
$DATENBANKEN = ['konto' => 'konto-daten', 'statistik' => 'statistik-daten'];
$db = text($_POST, 'db');
if (!isset($DATENBANKEN[$db])) {
    http_response_code(400);
    exit('unbekannte Datenbank');
}
$ordner = dirname(__DIR__) . '/' . $DATENBANKEN[$db];
$dateien = glob($ordner . '/' . $db . '-*.sqlite') ?: [];
if (count($dateien) !== 1) {
    http_response_code(404);
    exit(count($dateien) ? 'mehrere Datenbanken gefunden' : 'keine Datenbank');
}
$zertifikat = @file_get_contents(__DIR__ . '/sicherung-zertifikat.pem');
if (!is_string($zertifikat) || strpos($zertifikat, 'BEGIN CERTIFICATE') === false) {
    http_response_code(500);
    exit('Zertifikat fehlt');
}

$basis = $ordner . '/sicherung-' . bin2hex(random_bytes(8));
$roh = $basis . '.sqlite';
$gz = $basis . '.gz';
$enc = $basis . '.p7m';
try {
    // VACUUM INTO: vollständige, in sich stimmige Kopie, auch wenn gerade jemand schreibt (liest nur)
    $quelle = new SQLite3($dateien[0], SQLITE3_OPEN_READONLY);
    $quelle->busyTimeout(15000);
    if (!@$quelle->exec("VACUUM INTO '" . SQLite3::escapeString($roh) . "'")) {
        // Rückfall für ältere SQLite-Fassungen ohne VACUUM INTO: Online-Backup
        $ziel = new SQLite3($roh);
        if (!$quelle->backup($ziel)) {
            throw new RuntimeException('Kopie fehlgeschlagen');
        }
        $ziel->close();
    }
    $quelle->close();
    // Nur sichern, was die Datenschutzerklärung nennt (rechtliches.html#sicherung): Tages-Schlüssel und Besucher-Prüfsummen
    // der Zählung, Missbrauchs-Prüfsummen und offene Links (Registrierungen mit Adresse und Passwort-Hash) bleiben draußen.
    // VACUUM schreibt die Kopie danach neu, damit auch die gelöschten Zeilen nicht mehr in der Datei stehen.
    $bereinigen = [
        'statistik' => ['DELETE FROM heute', "DELETE FROM meta WHERE k IN ('salz', 'salz_tag')"],
        'konto' => ['DELETE FROM zaehler', 'DELETE FROM links'],
    ];
    $kopie = new SQLite3($roh);
    foreach ($bereinigen[$db] as $sql) {
        if (!$kopie->exec($sql)) {
            throw new RuntimeException('Bereinigen fehlgeschlagen');
        }
    }
    if (!$kopie->exec('VACUUM')) {
        throw new RuntimeException('Bereinigen fehlgeschlagen');
    }
    $kopie->close();
    $daten = file_get_contents($roh);
    @unlink($roh);
    if ($daten === false || strlen($daten) < 512) {
        throw new RuntimeException('Kopie leer');
    }
    if (file_put_contents($gz, gzencode($daten, 9)) === false) {
        throw new RuntimeException('gzip fehlgeschlagen');
    }
    unset($daten);
    if (!openssl_pkcs7_encrypt($gz, $enc, $zertifikat, [], PKCS7_BINARY, OPENSSL_CIPHER_AES_256_CBC)) {
        throw new RuntimeException('Verschlüsseln fehlgeschlagen');
    }
    @unlink($gz);
    header('Content-Type: application/pkcs7-mime');
    header('Content-Length: ' . filesize($enc));
    readfile($enc);
} catch (Throwable $e) {
    http_response_code(500);
    echo 'Fehler: ', $e->getMessage();
} finally {
    foreach ([$roh, $gz, $enc] as $f) {
        if (is_file($f)) {
            @unlink($f);
        }
    }
}
