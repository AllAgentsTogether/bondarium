<?php
/**
 * E-Mail vor jeder Fälligkeit (seit 02.10.2026, Nutzerentscheid nach PDF-Mockup; Dokumentation: docs/KONTO.md).
 * Wer in „Mein Bondarium“ den Schalter „E-Mail vor jeder Fälligkeit“ einschaltet (konto.php, aktion=erinnern), bekommt eine
 * kurze E-Mail, wenn eine Anleihe aus einem seiner Musterdepots in höchstens ERINNERUNG_TAGE Tagen fällig wird – je
 * Anleihe und Fälligkeit einmal, mehrere in einer E-Mail. Seit 02.10.2026 abends (Nutzerwunsch: „20 Tage bevor sie fällig
 * wird und dann nochmal zum Tag der Fälligkeit, damit man sein Konto überprüfen kann“) sind es 20 statt 30 Tage, und am
 * Fälligkeitstag selbst kommt eine zweite E-Mail. Welche schon verschickt ist, steht in der Tabelle erinnert: die erste
 * unter der Fälligkeit „JJJJ-MM-TT“, die zweite unter „JJJJ-MM-TT#tag“ (keine neue Spalte nötig; beide fallen am Tag danach heraus).
 * Seit 03.10.2026 (Nutzerentscheid „E-Mails an einer Stelle“) auch für die Merkliste: Anleihen in einem Musterdepot stehen mit
 * Depot und Nennwert in der E-Mail, nur gemerkte als „Merkliste“; je Anleihe und Fälligkeit bleibt es bei einer E-Mail (Tabelle
 * erinnert). Die Meldung „Zinstermin steht an“ (konto.php) nennt seitdem keine Fälligkeiten mehr. Nur Tatsachen (Anleihe, ISIN, Tag, Musterdepot, Nennwert), keine
 * Vorschläge für andere Anleihen – sonst wäre es Werbung. Jede E-Mail trägt einen Link, der die Erinnerung mit einem Klick
 * ausschaltet (konto.html#erinnerung-aus=Nummer.Prüfsumme; geprüft in konto.php, aktion=erinnerung-aus).
 *
 * Angestoßen wie der Besucherbericht: aufruf.php ruft erinnerung_faellig() bei jedem gezählten Aufruf; der erste Aufruf ab
 * ERINNERUNG_STUNDE Uhr (Berlin) verschickt nach der Antwort an den Browser (erinnerungen_senden()). Die Fälligkeit jeder
 * Anleihe kommt aus den Stammdaten anleihen/<teil>.json (wie der Steckbrief). Der Name je Anleihe (seit 03.10.2026, Konzept
 * „Einheitliche Anleihen-Angaben“) ist der Titel aus newsletter/anleihen.json („Deutschland 2,60 % 2033“, gebaut von
 * scripts/newsletter.py – derselbe Kurzname wie auf der Website, im Wochenbrief und in den Meldungen); nur wenn die Anleihe dort
 * fehlt (kein Kurs in den letzten 14 Tagen), eine Näherung aus den Stammdaten. Gelesen und geschrieben wird die Datenbank von
 * konto.php (konto-daten/), erst ab deren Fassung 5. Wird nur eingebunden; direkt aufgerufen antwortet die Datei mit 404
 * (zusätzlich per .htaccess gesperrt).
 *
 * Testmail: aufruf.php, aktion=testmail&art=erinnerung mit Kopf X-Trigger-Key (Workflow „Statistik – Testmail“, Auswahl
 * „erinnerung“) – eine Beispiel-Erinnerung an BERICHT_AN. Lokal: php aufruf.php erinnerung – die E-Mails landen in
 * konto-daten/lokal-mail.txt statt im Versand.
 */
declare(strict_types=1);

if (realpath($_SERVER['SCRIPT_FILENAME'] ?? '') === __FILE__) { http_response_code(404); exit; }

const ERINNERUNG_TAGE    = 20;
const ERINNERUNG_STUNDE  = 7;
const ERINNERUNG_MAX     = 300;   // E-Mails je Lauf – was nicht mehr passt, geht beim nächsten Lauf
const ERINNERUNG_ABSENDER = 'info@bondarium.com';
const ERINNERUNG_DATEN   = __DIR__ . '/konto-daten';
const ERINNERUNG_ANLEIHEN = __DIR__ . '/newsletter/anleihen.json';   // Kurzname und Kupon-Text je Anleihe aus dem Datenlauf (scripts/newsletter.py, Felder 0–2)
// Ländernamen für Staatsanleihen im Rückfall (Anleihe fehlt in ERINNERUNG_ANLEIHEN) – wie im Feldkatalog (felder.js, „staaten“);
// andere Länder über Locale::getDisplayRegion, wenn PHP mit intl läuft
const ERINNERUNG_LAENDER = ['DE' => 'Deutschland', 'FR' => 'Frankreich', 'IT' => 'Italien', 'ES' => 'Spanien', 'AT' => 'Österreich',
    'NL' => 'Niederlande', 'BE' => 'Belgien', 'FI' => 'Finnland', 'IE' => 'Irland', 'PT' => 'Portugal', 'GR' => 'Griechenland',
    'LU' => 'Luxemburg', 'SK' => 'Slowakei', 'SI' => 'Slowenien', 'LT' => 'Litauen', 'LV' => 'Lettland', 'EE' => 'Estland',
    'HR' => 'Kroatien', 'CY' => 'Zypern', 'MT' => 'Malta', 'PL' => 'Polen', 'CZ' => 'Tschechien', 'HU' => 'Ungarn', 'RO' => 'Rumänien',
    'BG' => 'Bulgarien', 'SE' => 'Schweden', 'DK' => 'Dänemark', 'NO' => 'Norwegen', 'CH' => 'Schweiz', 'GB' => 'Großbritannien',
    'US' => 'USA', 'CA' => 'Kanada', 'AU' => 'Australien', 'JP' => 'Japan', 'NZ' => 'Neuseeland', 'MX' => 'Mexiko',
    'BR' => 'Brasilien', 'TR' => 'Türkei', 'ZA' => 'Südafrika', 'IS' => 'Island', 'IL' => 'Israel', 'CL' => 'Chile', 'ID' => 'Indonesien'];

/** Datenbank von konto.php – nur, wenn es sie schon gibt und sie mindestens Fassung 5 hat */
function erinnerung_db(): ?PDO
{
    static $db = false;
    if ($db !== false) return $db;
    $db = null;
    if (!extension_loaded('pdo_sqlite')) return null;
    $dateien = glob(ERINNERUNG_DATEN . '/konto-*.sqlite') ?: [];
    sort($dateien);
    if (!$dateien) return null;
    $p = new PDO('sqlite:' . $dateien[0], null, null, [PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION, PDO::ATTR_TIMEOUT => 5]);
    $p->exec('PRAGMA foreign_keys = ON');
    if ((int)$p->query('PRAGMA user_version')->fetchColumn() < 5) return null;
    return $db = $p;
}

function erinnerung_meta(PDO $db, string $k): ?string
{
    $s = $db->prepare('SELECT v FROM meta WHERE k = ?');
    $s->execute([$k]);
    $v = $s->fetchColumn();
    return $v === false ? null : (string)$v;
}

/** Ist der Lauf von heute fällig? Dann vormerken (nur ein Aufruf verschickt) und true. */
function erinnerung_faellig(): bool
{
    if ((int)date('G') < ERINNERUNG_STUNDE) return false;
    $db = erinnerung_db();
    if ($db === null) return false;
    $heute = date('Y-m-d');
    if (erinnerung_meta($db, 'erinnerung') === $heute) return false;   // der übliche Fall: ohne Schreibsperre prüfen
    $db->exec('BEGIN IMMEDIATE');
    $fehler = (int)(erinnerung_meta($db, 'erinnerung_fehler') ?? 0);
    if (erinnerung_meta($db, 'erinnerung') === $heute || time() - $fehler < 3600) { $db->exec('COMMIT'); return false; }   // nach einem Fehler höchstens stündlich
    $db->prepare("INSERT OR REPLACE INTO meta (k, v) VALUES ('erinnerung', ?)")->execute([$heute]);
    $db->exec('COMMIT');
    return true;
}

/** Prüfsumme für den Link „Ausschalten“ – wie schluessel_hash() in konto.php, mit dem Schlüssel aus der Datenbank */
function erinnerung_token(PDO $db, int $id): string
{
    $geheim = (string)erinnerung_meta($db, 'hmac');
    return $id . '.' . substr(hash_hmac('sha256', 'erinnerung-aus:' . $id, $geheim), 0, 32);
}

/** Teildatei der Stammdaten wie MC.teil() in site.js */
function erinnerung_teil(string $isin): string
{
    $h = 0;
    for ($i = 0, $n = strlen($isin); $i < $n; $i++) $h = ($h * 31 + ord($isin[$i])) % 65536;
    return sprintf('%02x', $h % 256);
}

/**
 * Titel einer Anleihe aus newsletter/anleihen.json (aus den Feldern 0–2, „Deutschland 2,60 % 2033“) mit normalem Leerzeichen für die
 * Textfassung, oder null, wenn die Anleihe oder die Datei fehlt. Die Datei ist groß; gesucht wird die eine Zeile im Text
 * (wie zeile_heute() in konto.php).
 */
function erinnerung_titel(string $isin): ?string
{
    static $roh = null, $schon = [];
    if (array_key_exists($isin, $schon)) return $schon[$isin];
    if ($roh === null) {
        $roh = @file_get_contents(ERINNERUNG_ANLEIHEN);
        $roh = is_string($roh) ? $roh : '';
    }
    $z = null;
    $p = $roh === '' ? false : strpos($roh, '"' . $isin . '":');
    if ($p !== false) {
        $a = strpos($roh, '[', $p);
        $e = $a === false ? false : strpos($roh, '],', $a);
        if ($e === false && $a !== false) $e = strpos($roh, ']}', $a);   // letzte Zeile der Datei
        $z = $e === false ? null : json_decode(substr($roh, $a, $e - $a + 1), true);
    }
    // Titel wie nl_titel() in konto.php: Kurzname (Feld 0), Kupon-Text (Feld 1), Fälligkeitsjahr (Feld 2)
    $t = is_array($z) && is_string($z[0] ?? null) && $z[0] !== '' ? str_replace("\u{00A0}", ' ', trim($z[0] . ' ' . ($z[1] ?? '')) . ' ' . (!empty($z[2]) ? substr((string)$z[2], 0, 4) : 'unbefristet')) : null;
    return $schon[$isin] = $t;
}

/**
 * Stammdaten einer Anleihe: [Name für die E-Mail (Näherung, siehe erinnerung_titel()), Fälligkeit JJJJ-MM-TT, Währung] oder null.
 * Der Name folgt der Regel der Website (Kurzname, Kupon, Fälligkeitsjahr), nur einfacher: bei Staaten das Land, sonst der
 * Emittent ohne Rechtsform; Kupon „variabel“ bzw. „Nullkupon“ als Wort.
 */
function erinnerung_anleihe(string $isin): ?array
{
    static $teile = [];
    $t = erinnerung_teil($isin);
    if (!array_key_exists($t, $teile)) {
        $roh = @file_get_contents(__DIR__ . '/anleihen/' . $t . '.json');
        $j = $roh === false ? null : json_decode($roh, true);
        $teile[$t] = is_array($j) && isset($j['rows']) && is_array($j['rows']) ? $j['rows'] : [];
    }
    $r = $teile[$t][$isin] ?? null;
    if (!is_array($r) || empty($r[4])) return null;
    [$name, $art, $cur, $kupon, $faellig] = [(string)$r[0], (int)$r[1], (string)$r[2], $r[3], (string)$r[4]];
    $emittent = (string)($r[8] ?? '');
    $land = (string)($r[10] ?? '');
    $zinsart = (int)($r[9] ?? 0);
    // Name wie auf der Website: bei Staaten das Land, sonst der Emittent ohne Rechtsform, notfalls der Registername
    $kurz = '';
    if ($art === 0 && $land !== '' && $land !== 'INT') {
        $kurz = ERINNERUNG_LAENDER[$land] ?? (class_exists('Locale') ? (string)\Locale::getDisplayRegion('-' . $land, 'de') : '');
        if ($kurz === $land) $kurz = '';
    }
    $rf = '/[\s,]+(AG|SE|KGaA|GmbH|mbH|S\.?A\.?|S\.?p\.?A\.?|N\.?V\.?|B\.?V\.?|plc|PLC|p\.l\.c\.|Inc\.?|Corp\.?|Corporation|Ltd\.?|Limited|LLC|A\/S|AB|ASA|Oyj|Aktiengesellschaft)\.?$/u';   // Rechtsform am Ende
    if ($kurz === '' && $emittent !== '') {
        $kurz = trim((string)preg_replace($rf, '', $emittent));
    }
    if ($kurz === '') $kurz = $name;
    // Namen, die das Register nur in Großbuchstaben meldet, in üblicher Schreibung (wie lesbar() auf der Website, nur einfacher) –
    // nicht den Ländernamen („USA“)
    $istLand = $art === 0 && in_array($kurz, ERINNERUNG_LAENDER, true);
    if (!$istLand && function_exists('mb_convert_case') && preg_match('/\p{Lu}{3}/u', $kurz) && mb_strtoupper($kurz, 'UTF-8') === $kurz) {
        $kurz = mb_convert_case(mb_strtolower($kurz, 'UTF-8'), MB_CASE_TITLE, 'UTF-8');
        $kurz = (string)preg_replace_callback('/(?<=\s)(De|Del|La|Le|Les|Of|And|Und|Der|Die|Das|Von|Für|Du|Des|Y|E)(?=\s)/u', fn($m) => mb_strtolower($m[1], 'UTF-8'), $kurz);
        $kurz = trim((string)preg_replace($rf, '', $kurz));   // „… International LTD“ → erst jetzt als „Ltd“ erkennbar
    }
    // Kupon wie kupon_text() in scripts/_common.py: „3,50 %“, „3,625 %“, „variabel“, „Nullkupon“ – nie „0,00 %“
    if ($zinsart === 1 || $kupon === 'var') {
        $kTxt = 'variabel';
    } elseif ($zinsart === 2 || (is_numeric($kupon) && (float)$kupon == 0.0 && $zinsart !== 0)) {
        $kTxt = 'Nullkupon';
    } elseif (is_numeric($kupon)) {
        $kTxt = number_format((float)$kupon, ((int)round((float)$kupon * 1000)) % 10 ? 3 : 2, ',', '.') . ' %';
    } else {
        $kTxt = '–';
    }
    return [$kurz . ' ' . $kTxt . ' ' . substr($faellig, 0, 4), $faellig, $cur];
}

function erinnerung_datum(string $iso): string
{
    return substr($iso, 8, 2) . '.' . substr($iso, 5, 2) . '.' . substr($iso, 0, 4);
}

/**
 * Text einer Erinnerung. $posten: [[Titel, ISIN, Fälligkeit, Tage, Depotname, Nennwert, Währung], …] – Depotname leer = nur auf der
 * Merkliste (ohne Nennwert). $heute = true: die zweite E-Mail am Tag der Fälligkeit (alle Posten sind heute fällig).
 */
function erinnerung_text(array $posten, string $aus, bool $heute = false): array
{
    usort($posten, fn($a, $b) => strcmp($a[2], $b[2]) ?: strcmp($a[4], $b[4]));
    $isins = array_unique(array_column($posten, 1));
    $tage = fn(int $t) => $t === 1 ? 'morgen' : "in $t Tagen";
    // Woher die Anleihen kommen: Musterdepot(s), Merkliste oder beides
    $depots = array_values(array_unique(array_filter(array_column($posten, 4), fn($d) => $d !== '')));
    $merk = count(array_filter($posten, fn($p) => $p[4] === '')) > 0;
    $quelle = !$depots ? 'von deiner Merkliste'
        : (count($depots) === 1 ? 'aus deinem Musterdepot „' . $depots[0] . '“' : 'aus deinen Musterdepots') . ($merk ? ' und von deiner Merkliste' : '');
    $kurz = !$depots ? 'von deiner Merkliste' : ($merk ? 'aus Merkliste und Musterdepots' : (count($depots) === 1 ? 'aus deinem Musterdepot' : 'aus deinen Musterdepots'));
    if ($heute) {
        $eine = count($isins) === 1;
        $betreff = $eine ? "Bondarium: Heute wird eine Anleihe $kurz fällig" : 'Bondarium: Heute werden ' . count($isins) . " Anleihen $kurz fällig";
        $kopf = 'heute ' . ($eine ? 'wird eine Anleihe' : 'werden ' . count($isins) . ' Anleihen') . " $quelle fällig:";
    } elseif (count($isins) === 1) {
        $p = $posten[0];
        $betreff = "Bondarium: Eine Anleihe $kurz wird am " . erinnerung_datum($p[2]) . ' fällig';
        $kopf = $tage($p[3]) . " wird eine Anleihe $quelle fällig:";
    } else {
        $betreff = 'Bondarium: ' . count($isins) . " Anleihen $kurz werden bald fällig";
        $kopf = 'bald werden ' . count($isins) . " Anleihen $quelle fällig:";
    }
    $bloecke = [];
    foreach ($posten as $p) {
        // je Anleihe: Titel · ISIN und Fälligkeit · Musterdepot mit Nennwert (immer mit Währungskürzel: „10.000 EUR“) oder Merkliste
        $w = $p[6] !== '' ? $p[6] : 'EUR';
        $bloecke[] = "  {$p[0]}\n  ISIN {$p[1]} · fällig am " . erinnerung_datum($p[2]) . (count($isins) > 1 && !$heute ? ' (' . $tage($p[3]) . ')' : '') .
            ($p[4] !== '' ? "\n  Musterdepot „{$p[4]}“ · Nennwert " . number_format((float)$p[5], 0, ',', '.') . " $w · Rückzahlung zum Nennwert (100 %)"
                : "\n  Merkliste · Rückzahlung zum Nennwert (100 %)");
    }
    $text = $kopf . "\n\n" . implode("\n\n", $bloecke) . "\n\n" .
        ($heute ? "Hast du die Anleihe auch in deinem echten Depot? Dann sieh in den nächsten Tagen auf deinem Konto nach, ob die Rückzahlung angekommen ist.\n\n" : '') .
        ($depots ? "Deine Musterdepots ansehen:\nhttps://www.bondarium.de/konto.html#depot\n\n" : "Deine Merkliste ansehen:\nhttps://www.bondarium.de/konto.html#merkliste\n\n") .
        "Du bekommst diese E-Mail, weil du in „Mein Bondarium“ unter „E-Mails an dich“ die E-Mail vor Fälligkeit eingeschaltet hast. Ausschalten kannst du sie mit einem Klick:\n" .
        "https://www.bondarium.de/konto.html#$aus\n\n" .
        ($depots ? 'Musterdepots sind ein Planspiel – Bondarium kauft und verkauft nichts und kennt keine echten Bestände. ' : 'Bondarium kauft und verkauft nichts und kennt keine echten Bestände. ') . 'Keine Anlageberatung.';
    return [$betreff, $text];
}

/** E-Mail wie mail_senden() in konto.php (Kopf, Fuß, Absender); lokal in konto-daten/lokal-mail.txt */
function erinnerung_mail(string $an, string $betreff, string $text): bool
{
    $text = "Hallo,\n\n" . $text . "\n\nBondarium – ein Angebot der urbanelo GmbH\nhttps://www.bondarium.de/rechtliches.html\n";
    if (PHP_SAPI === 'cli-server' || PHP_SAPI === 'cli') {
        return file_put_contents(ERINNERUNG_DATEN . '/lokal-mail.txt', "An: $an\nBetreff: $betreff\n\n$text\n----\n", FILE_APPEND) !== false;
    }
    $kopf = implode("\r\n", [
        'From: Bondarium <' . ERINNERUNG_ABSENDER . '>',
        'MIME-Version: 1.0',
        'Content-Type: text/plain; charset=UTF-8',
        'Content-Transfer-Encoding: base64',
        'Auto-Submitted: auto-generated',
    ]);
    return mail($an, '=?UTF-8?B?' . base64_encode($betreff) . '?=', chunk_split(base64_encode($text)), $kopf, '-f ' . ERINNERUNG_ABSENDER);
}

/** Der tägliche Lauf: alle fälligen Erinnerungen verschicken. Gibt [verschickt, fehlgeschlagen] zurück. */
function erinnerungen_senden(): array
{
    $db = erinnerung_db();
    if ($db === null) return [0, 0];
    $heute = date('Y-m-d');
    $db->prepare('DELETE FROM erinnert WHERE faellig < ?')->execute([$heute]);   // „JJJJ-MM-TT#tag“ (zweite E-Mail) fällt wie die erste am Tag nach der Fälligkeit heraus
    $s = $db->query('SELECT n.id, n.email, m.name, d.isin, d.nennwert FROM nutzer n JOIN musterdepots m ON m.nutzer = n.id JOIN depot d ON d.muster = m.id WHERE n.erinnern = 1 ORDER BY n.id, m.id, d.seit');
    $je = [];
    foreach ($s->fetchAll(PDO::FETCH_NUM) as [$id, $email, $depot, $isin, $nenn]) {
        $je[(int)$id]['email'] = (string)$email;
        $je[(int)$id]['posten'][] = [(string)$depot, (string)$isin, (int)$nenn];
    }
    // Seit 03.10.2026 auch die Merkliste – Anleihen, die schon in einem Musterdepot liegen, stehen dort mit Depot und Nennwert
    $f = $db->query('SELECT n.id, n.email, f.isin FROM nutzer n JOIN favoriten f ON f.nutzer = n.id WHERE n.erinnern = 1 ORDER BY n.id, f.seit');
    foreach ($f->fetchAll(PDO::FETCH_NUM) as [$id, $email, $isin]) {
        $id = (int)$id;
        $je[$id]['email'] = (string)$email;
        if (in_array((string)$isin, array_column($je[$id]['posten'] ?? [], 1), true)) continue;
        $je[$id]['posten'][] = ['', (string)$isin, 0];
    }
    $schon = $db->prepare('SELECT 1 FROM erinnert WHERE nutzer = ? AND isin = ? AND faellig = ?');
    $merke = $db->prepare('INSERT OR IGNORE INTO erinnert (nutzer, isin, faellig, gesendet) VALUES (?, ?, ?, ?)');
    $null = new DateTimeImmutable($heute);
    $ok = 0;
    $fehl = 0;
    foreach ($je as $id => $u) {
        if ($ok + $fehl >= ERINNERUNG_MAX) break;
        $vorab = [];   // in 1 bis ERINNERUNG_TAGE Tagen fällig, noch nicht gemeldet
        $amTag = [];   // heute fällig, zweite E-Mail noch nicht verschickt
        foreach ($u['posten'] as [$depot, $isin, $nenn]) {
            $a = erinnerung_anleihe($isin);
            if ($a === null) continue;
            $tage = (int)$null->diff(new DateTimeImmutable($a[1]))->format('%r%a');
            if ($tage < 0 || $tage > ERINNERUNG_TAGE) continue;
            $marke = $tage === 0 ? $a[1] . '#tag' : $a[1];
            $schon->execute([$id, $isin, $marke]);
            if ($schon->fetchColumn()) continue;
            $p = [erinnerung_titel($isin) ?? $a[0], $isin, $a[1], $tage, $depot, $nenn, $a[2], $marke];   // Titel erst hier: nur für fällige Anleihen suchen
            if ($tage === 0) $amTag[] = $p; else $vorab[] = $p;
        }
        foreach ([[$vorab, false], [$amTag, true]] as [$posten, $heuteFaellig]) {
            if (!$posten) continue;
            [$betreff, $text] = erinnerung_text($posten, 'erinnerung-aus=' . erinnerung_token($db, $id), $heuteFaellig);
            if (erinnerung_mail($u['email'], $betreff, $text)) {
                foreach ($posten as $p) $merke->execute([$id, $p[1], $p[7], time()]);
                $ok++;
            } else {
                $fehl++;
            }
        }
    }
    if ($fehl && !$ok) {
        $db->prepare("INSERT OR REPLACE INTO meta (k, v) VALUES ('erinnerung', '')")->execute();   // in einer Stunde noch einmal versuchen
        $db->prepare("INSERT OR REPLACE INTO meta (k, v) VALUES ('erinnerung_fehler', ?)")->execute([(string)time()]);
    }
    return [$ok, $fehl];
}

/**
 * Beispiel-Erinnerungen an $an (Testmail): beide E-Mails – die erste (ERINNERUNG_TAGE Tage vorher) und die zweite (am Tag der
 * Fälligkeit). Eine Anleihe aus den Stammdaten; Musterdepot, Nennwert und Fälligkeitstag sind erfunden, der Link ist ohne Wirkung.
 */
function erinnerung_testmail(string $an): bool
{
    $a = erinnerung_anleihe('DE000BU22072');
    if ($a === null) return false;
    $ok = true;
    foreach ([[ERINNERUNG_TAGE, false, 'die erste Erinnerung, ' . ERINNERUNG_TAGE . ' Tage vor einer Fälligkeit'], [0, true, 'die zweite Erinnerung, am Tag der Fälligkeit']] as [$tage, $heute, $was]) {
        $posten = [[erinnerung_titel('DE000BU22072') ?? $a[0], 'DE000BU22072', date('Y-m-d', time() + $tage * 86400), $tage, 'Sicherheit (Beispiel)', 10000, $a[2]]];
        [$betreff, $text] = erinnerung_text($posten, 'erinnerung', $heute);
        $ok = erinnerung_mail($an, '[Test] ' . $betreff, $text . "\n\n(Test-E-Mail: So sieht $was aus. Musterdepot, Nennwert und Fälligkeitstag sind erfunden.)") && $ok;
    }
    return $ok;
}
