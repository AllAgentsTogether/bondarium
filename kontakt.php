<?php
/**
 * Kontaktformular (ueber-uns.html#kontakt, seit 30.09.2026 – zweiter Kontaktweg neben der E-Mail, § 5 DDG).
 *
 * Nimmt Name (freiwillig), E-Mail-Adresse und Nachricht per POST entgegen und leitet sie als E-Mail an
 * info@bondarium.com weiter. Auf dem Webserver wird nichts gespeichert: keine Datei, keine Datenbank, keine
 * IP-Adresse in der E-Mail. Die Antwort ist JSON ({"status": …}); das Skript der Seite zeigt den passenden Text.
 *
 * Schutz ohne Captcha und ohne fremde Dienste:
 *   - nur POST mit dem Kopf „X-Requested-With: bondarium-kontakt“ – ihn setzt das Skript der eigenen Seite;
 *     fremde Seiten können ihn im Browser nicht mitschicken (CORS), einfache Bots schicken ihn nicht
 *   - ein fremder Ursprung (Origin) wird abgewiesen
 *   - Honigtopf-Feld „website“: für Menschen unsichtbar; ist es ausgefüllt, wird nichts gesendet
 *   - Längen begrenzt, E-Mail-Adresse geprüft, keine Zeilenumbrüche in Kopfzeilen
 *
 * Status: ok · methode (kein POST) · anfrage (Kopf fehlt) · ursprung · email · nachricht · name · versand
 * Ändert sich hier etwas an den verarbeiteten Daten, muss die Datenschutzerklärung (rechtliches.html) mit.
 */
declare(strict_types=1);

const EMPFAENGER = 'info@bondarium.com';
const ABSENDER   = 'info@bondarium.com';   // eigenes Postfach (bondarium.com liegt wie bondarium.de bei STRATO); die Adresse des Besuchers steht in Reply-To
const URSPRUNG   = 'https://www.bondarium.de';

header('Content-Type: application/json; charset=utf-8');
header('Cache-Control: no-store');
header('X-Robots-Tag: noindex');

function antwort(int $code, string $status): void
{
    http_response_code($code);
    echo json_encode(['status' => $status]);
    exit;
}

function laenge(string $s): int
{
    return function_exists('mb_strlen') ? mb_strlen($s, 'UTF-8') : strlen($s);
}

/** Feld aus $_POST als Text; eine Liste („feld[]=…“) zählt wie ein leeres Feld – ohne PHP-Warnung im Fehlerprotokoll (T-132). */
function text(array $q, string $k): string
{
    $v = $q[$k] ?? '';
    return is_string($v) ? $v : '';
}

if (($_SERVER['REQUEST_METHOD'] ?? '') !== 'POST') {
    header('Allow: POST');
    antwort(405, 'methode');
}
if (($_SERVER['HTTP_X_REQUESTED_WITH'] ?? '') !== 'bondarium-kontakt') {
    antwort(400, 'anfrage');
}
$origin = (string)($_SERVER['HTTP_ORIGIN'] ?? '');
if ($origin !== '' && $origin !== URSPRUNG) {
    antwort(403, 'ursprung');
}

$name  = trim(text($_POST, 'name'));
$mail  = trim(text($_POST, 'email'));
$text  = trim(text($_POST, 'nachricht'));
$falle = text($_POST, 'website');

// Honigtopf ausgefüllt: so antworten, als wäre alles gut – gesendet wird nichts
if ($falle !== '') {
    antwort(200, 'ok');
}

if ($mail === '' || strlen($mail) > 254 || preg_match('/[\r\n]/', $mail) || filter_var($mail, FILTER_VALIDATE_EMAIL) === false) {
    antwort(422, 'email');
}
if (laenge($text) < 10 || laenge($text) > 5000) {
    antwort(422, 'nachricht');
}
if (laenge($name) > 100) {
    antwort(422, 'name');
}
$name = trim((string)preg_replace('/[\r\n\t]+/', ' ', $name));
$text = str_replace(["\r\n", "\r"], "\n", $text);

$koerper = "Nachricht über das Kontaktformular von www.bondarium.de\n\n"
    . 'Name: ' . ($name !== '' ? $name : '–') . "\n"
    . 'E-Mail: ' . $mail . "\n\n"
    . $text . "\n";

$kopf = implode("\r\n", [
    'From: Bondarium Kontaktformular <' . ABSENDER . '>',
    'Reply-To: ' . $mail,
    'MIME-Version: 1.0',
    'Content-Type: text/plain; charset=UTF-8',
    'Content-Transfer-Encoding: base64',
]);
$betreff = '=?UTF-8?B?' . base64_encode('Kontaktformular bondarium.de') . '?=';

$ok = mail(EMPFAENGER, $betreff, chunk_split(base64_encode($koerper)), $kopf, '-f ' . ABSENDER);

antwort($ok ? 200 : 500, $ok ? 'ok' : 'versand');
