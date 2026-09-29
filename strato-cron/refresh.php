<?php
/**
 * Auslöser für den täglichen 10-Uhr-Datenabruf: stößt den GitHub-Actions-
 * Workflow per workflow_dispatch an, der die Marktdaten holt und auf Strato
 * veröffentlicht. Ein Dispatch startet binnen Sekunden – GitHubs eigener
 * Zeitplan lief 09/2026 täglich rund 4–5 Stunden zu spät.
 *
 * Aufruf durch einen externen Cron (z. B. cron-job.org: Di–Sa 10:00 Uhr,
 * Zeitzone Europe/Berlin) – zwei Varianten werden unterstützt:
 *   1) als URL:     https://www.metalconcrete.de/trigger/refresh.php?key=GEHEIM&mode=voll
 *   2) per PHP-CLI: php refresh.php voll
 *
 * mode=voll     Daten abrufen – höchstens einmal am Tag: Der Workflow prüft
 *               zuerst, ob heute schon abgefragt wurde, und endet dann ohne Abruf.
 * mode=schnell  nur veröffentlichen, kein Datenabruf (Standard ohne mode).
 *
 * GitHub gibt bei Erfolg HTTP 204 zurück (kein Inhalt).
 */

$cfg = require __DIR__ . '/refresh-config.php';

$isCli = (php_sapi_name() === 'cli');

if ($isCli) {
    // Aufruf über die Kommandozeile (php refresh.php [schnell|voll])
    $mode = $argv[1] ?? 'schnell';
} else {
    // Aufruf über das Web: nur mit korrektem Schlüssel auslösbar.
    // Ohne konfiguriertes Secret (leer/fehlend) gar nicht erst vergleichen –
    // sonst wäre der Trigger mit ?key= (leer) für jedermann auslösbar.
    if (!is_string($cfg['secret']) || $cfg['secret'] === '') {
        http_response_code(503);
        exit('not configured');
    }
    if (!hash_equals($cfg['secret'], (string)($_GET['key'] ?? ''))) {
        http_response_code(403);
        exit('Forbidden');
    }
    $mode = $_GET['mode'] ?? 'schnell';
}

if (!in_array($mode, ['schnell', 'voll'], true)) {
    $mode = 'schnell';
}

$url = sprintf(
    'https://api.github.com/repos/%s/actions/workflows/%s/dispatches',
    $cfg['repo'],
    $cfg['workflow']
);

$payload = json_encode([
    'ref'    => $cfg['branch'],
    'inputs' => ['lauf' => $mode],
]);

$ch = curl_init($url);
curl_setopt_array($ch, [
    CURLOPT_POST           => true,
    CURLOPT_POSTFIELDS     => $payload,
    CURLOPT_RETURNTRANSFER => true,
    CURLOPT_TIMEOUT        => 20,
    CURLOPT_HTTPHEADER     => [
        'Accept: application/vnd.github+json',
        'Authorization: Bearer ' . $cfg['token'],
        'User-Agent: strato-cron-trigger',
        'X-GitHub-Api-Version: 2022-11-28',
        'Content-Type: application/json',
    ],
]);

$resp = curl_exec($ch);
$code = curl_getinfo($ch, CURLINFO_HTTP_CODE);
$err  = curl_error($ch);
curl_close($ch);

if ($code === 204) {
    http_response_code(200);
    echo "OK – Workflow ausgelöst (Modus: $mode)";
} else {
    http_response_code(502);
    echo "Fehler: HTTP $code" . ($err ? " ($err)" : '') . ' ' . substr((string)$resp, 0, 300);
}
