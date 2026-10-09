<?php
/**
 * Benutzerbereich (konto.html, seit 30.09.2026): Konto mit E-Mail-Adresse und Passwort, eine Merkliste für Anleihen und
 * – seit 01.10.2026 – Musterdepots („Mein Depot“: Anleihen mit einem gedachten Nennwert, kein echter Bestand; seit
 * 02.10.2026 bis zu MAX_MUSTER Depots mit eigenem Namen). Dokumentation: docs/KONTO.md. Der Browser spricht über konto.js mit diesem Skript; die Antwort ist
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
 *   Angemeldet     aktion=status | merken | entfernen | uebernehmen | depot | muster-neu | muster-name | muster-weg |
 *                  muster-uebernehmen | abmelden | passwort-aendern | loeschen | ablage | besuch | geraete-ab | export |
 *                  email-aendern
 *                  uebernehmen (isins, durch Komma getrennt): setzt eine geteilte Merkliste auf die eigene – der Link im
 *                  PDF-Auszug führt auf konto.html#liste=…, die Seite fragt nach, erst der Klick ruft diese Aktion
 *                  depot (isin, nennwert, muster): legt die Anleihe mit diesem Nennwert in das Musterdepot „muster“
 *                  (Nummer aus „depots“; fehlt sie, das erste) oder ändert ihn; nennwert 0 nimmt sie heraus
 *                  muster-neu (name) legt ein Musterdepot an, muster-name (muster, name) benennt es um, muster-weg
 *                  (muster) löscht es samt Anleihen – das letzte bleibt; muster-uebernehmen (name, liste
 *                  „ISIN~Nennwert,…“) legt ein geteiltes Musterdepot als neues an (Knopf im PDF, konto.html#muster=…)
 *                  erinnern (an = 1 | 0): E-Mail 20 Tage vor und am Tag jeder Fälligkeit ein- oder ausschalten (seit 02.10.2026;
 *                  seit 03.10.2026 für Merkliste und Musterdepots – Schalter „Vor Fälligkeit“ in der Karte „E-Mails an dich“;
 *                  verschickt werden die E-Mails von erinnerung.php, angestoßen von aufruf.php)
 *   Ohne Anmeldung aktion=erinnerung-aus (token „Nummer.Prüfsumme“ aus dem Link in der Erinnerungs-E-Mail,
 *                  konto.html#erinnerung-aus=…) schaltet die Erinnerung aus – ein Klick, ohne Passwort
 *   Newsletter     (seit 02.10.2026, docs/NEWSLETTER.md) wöchentlicher „Wochenbrief“, nur für Konten, nur mit Einwilligung:
 *                  registrieren mit newsletter=1 (Häkchen im Formular, nicht vorab gesetzt) → das Bestätigen der
 *                  Registrierung bestätigt auch den Newsletter; aktion=newsletter (angemeldet, wert=1|0) schaltet ihn
 *                  an oder aus; aktion=newsletter-ab (Kennung aus dem Abmelde-Link, ohne Anmeldung) und ein POST auf
 *                  konto.php?nl=<Kennung> (List-Unsubscribe der E-Mail-Programme) bestellen ihn ab (ein GET dorthin
 *                  bestellt nichts ab, er leitet nur auf konto.html#nl-ab=<Kennung> um);
 *                  aktion=newsletter-senden (Kopf X-Trigger-Key, ruft der Workflow nach dem Datenlauf) verschickt die
 *                  Ausgabe aus newsletter/ausgabe.json an alle Abonnenten, die diese Kalenderwoche noch keine haben.
 *   Mein Bondarium (seit 02.10.2026 abends, Nutzerauftrag „Mockup komplett umsetzen“; docs/KONTO.md, Abschnitt „Mein Bondarium“):
 *                  ablage (art, schluessel, wert als JSON; wert leer = löschen): die persönliche Ablage – Notizen, Listen,
 *                  gelesene Seiten, Lesezeichen, Begriffe, angeheftete Kennzahlen, Einstellung „Zuletzt angesehen“, Meldungen, Checkliste,
 *                  „Zuletzt angesehen“ (ABLAGE nennt Arten und Grenzen)
 *                  besuch: merkt den Beginn dieses Besuchs und liefert den des vorigen („Seit deinem letzten Besuch“), dazu je
 *                  gemerkter Anleihe den nächsten Zinstermin (termine) und welche davon geschätzt sind (termine_geschaetzt)
 *                  geraete-ab: meldet alle anderen Geräte ab; export: alles zum Konto Gespeicherte als JSON
 *                  email-aendern (email, passwort) → E-Mail mit Link an die NEUE Adresse (24 Stunden);
 *                  email-bestaetigen (Kennwort des Links, ohne Anmeldung) stellt das Konto um und meldet andere Geräte ab
 *                  meldungen-senden (Kopf X-Trigger-Key, ruft der Workflow nach dem Datenlauf): prüft die Meldungen aller
 *                  Konten gegen newsletter/anleihen.json und verschickt die ausgelösten als eine E-Mail je Konto;
 *                  meldungen-aus (Kennung aus dem Link der E-Mail, ohne Anmeldung): keine Meldungen mehr per E-Mail
 *   Links          führen auf konto.html#bestaetigen=… bzw. #passwort=… – der Teil hinter „#“ erscheint in keinem
 *                  Server-Log; aktion=link-pruefen sagt der Seite, ob der Link noch gilt und zu welcher Adresse er gehört.
 *
 * Gespeichert wird in einer SQLite-Datei im Ordner konto-daten/ (per .htaccess gesperrt, Dateiname zufällig):
 *   nutzer     E-Mail-Adresse, Hashwert des Passworts, angelegt am, zuletzt angemeldet, Erinnerung per E-Mail an/aus; Newsletter ja/nein,
 *              seit wann, Kalenderwoche der zuletzt erhaltenen Ausgabe
 *   erinnert   verschickte Erinnerungen: Nutzer, ISIN, Fälligkeit, Zeitpunkt – damit keine doppelt kommt; nach der
 *              Fälligkeit gelöscht (erinnerung.php)
 *   newsletter_log  An- und Abmeldungen des Newsletters als Zeitpunkt und Art – ohne Bezug zum Konto, nur zum Zählen
 *              für den täglichen Bericht (25 Monate)
 *   favoriten  ISIN und Zeitpunkt je Nutzer, seit Fassung 7 dazu die Rendite am Tag des Merkens (aus dem Datenlauf)
 *   ablage     persönliche Ablage je Nutzer: Art, Schlüssel, Wert (JSON), Zeitpunkt – nur, was der Nutzer selbst ablegt
 *   musterdepots  Musterdepots je Nutzer: Nummer, Name (vom Nutzer, höchstens NAME_MAX Zeichen), angelegt am
 *   depot      Anleihen der Musterdepots: Nummer des Musterdepots, ISIN, gedachter Nennwert (ganze Zahl in der Währung
 *              der Anleihe) und Zeitpunkt
 *   links      offene Registrierungen und Links zum Zurücksetzen: Hashwert des Link-Kennworts, Adresse, Ablauf, bei
 *              Registrierungen der Hashwert des Passworts und die vorgemerkte ISIN – nach Ablauf gelöscht (aufraeumen)
 *   sitzungen  Anmeldungen (nur der Hashwert des Cookies, Ablauf; seit Fassung 7 eine Gerätebezeichnung wie „Mac (Safari)“
 *              aus der Browser-Kennung, angemeldet am, zuletzt genutzt)
 *   zaehler    Schutz vor Missbrauch: verschlüsselte Hashwerte von Adresse und IP-Adresse für verschickte E-Mails und
 *              falsche Passwörter, gezählt werden 24 Stunden, danach gelöscht (aufraeumen)
 *   meta       zufälliger Schlüssel für diese Hashwerte, Zeitpunkt des letzten Aufräumens, ein Vergleichs-Hashwert, seit
 *              Fassung 9 der Zeitpunkt der Umstellung der Ein-Klick-Links (link_kennung)
 * Daneben die Marke konto-daten/.angelegt (seit 09.10.2026): Es gab hier schon eine Datenbank – fehlt die Datei, legt
 * db() keine neue an (Datei von Hand austauschen: docs/BETRIEB.md).
 * Passwörter, Link-Kennwörter und Cookies stehen nie im Klartext in der Datei. Passwörter werden mit Argon2id gehasht
 * (wo PHP es nicht kann: bcrypt). Konten ohne Anmeldung seit zwei Jahren werden gelöscht.
 *
 * Schutz ohne Captcha und ohne fremde Dienste (wie kontakt.php):
 *   - Änderungen nur per POST mit dem Kopf „X-Requested-With: bondarium-konto“ – fremde Seiten können ihn im
 *     Browser nicht mitschicken (CORS); ein fremder Ursprung (Origin) wird abgewiesen; das Cookie ist SameSite=Strict
 *   - Passwort: mindestens PW_MIN Zeichen, keine sehr häufigen Passwörter (passwort_gut)
 *   - falsche Passwörter werden gezählt und gebremst (LOGIN_GRENZEN; angemeldet beim Bestätigen mit Passwort
 *     LOGIN_GRENZEN_ANGEMELDET); die Antwort verrät nicht, ob es zu einer Adresse ein Konto gibt (anmelden, registrieren und
 *     vergessen antworten in beiden Fällen gleich)
 *   - Obergrenzen für verschickte E-Mails: je Adresse, je IP-Adresse und insgesamt (GRENZEN); Honigtopf-Feld „website“.
 *     „IP-Adresse“ heißt bei IPv6 das ganze /64-Netz eines Anschlusses (ip())
 *   - Passwort ändern oder zurücksetzen meldet alle anderen Geräte ab
 *
 * Status: ok · methode · anfrage · ursprung · aktion · email · passwort (zu schwach) · zugang (E-Mail oder Passwort
 *         falsch) · zuviel (Grenze je Adresse oder Anschluss) · zuviel-gesamt (Gesamtgrenze für E-Mails, seit 09.10.2026) ·
 *         versand · link (abgelaufen oder benutzt) · anmelden (nicht angemeldet) · isin · voll ·
 *         nennwert (keine ganze Zahl von 0 bis NENNWERT_MAX) · muster (kein eigenes Musterdepot) · name (leer) ·
 *         mustervoll (schon MAX_MUSTER Musterdepots) · letztes (das letzte Musterdepot bleibt) · speicher (Datenbank nicht
 *         nutzbar, fehlt nach dem Anlegen oder liegt doppelt da) · art (unbekannte Art der Ablage) · wert (kein gültiger Wert
 *         oder zu lang) · voll (Ablage dieser Art voll) · aus („Zuletzt angesehen“ ist ausgeschaltet) · gleich (neue
 *         E-Mail-Adresse ist die alte) · fehler
 * Ändert sich hier etwas an den verarbeiteten Daten, muss die Datenschutzerklärung (rechtliches.html) mit – und der
 * Betreiber vorher gefragt werden.
 *
 * Lokal testen (PHP-eigener Server, nie auf dem Webserver): php -S 127.0.0.1:8090 – dann gilt der lokale Ursprung,
 * die Cookies kommen ohne „Secure“, und die E-Mail landet in konto-daten/lokal-mail.txt statt im Versand.
 */
declare(strict_types=1);

// Deutsche Zeit für date() und strtotime() – Export, „heute“ der Meldungen, Alter der Wochenbrief-Ausgabe (wie aufruf.php und
// wechselkurse.php; die Voreinstellung des Servers ist von außen nicht erkennbar; Technik-Test 08.10.2026, T-107)
date_default_timezone_set('Europe/Berlin');

const LOKAL              = PHP_SAPI === 'cli-server';
const ABSENDER           = 'info@bondarium.com';   // eigenes Postfach bei STRATO, wie kontakt.php
const SEITE              = 'https://www.bondarium.de';
const DATEN              = __DIR__ . '/konto-daten';
const BESTAETIGEN_STUNDEN = 24;   // Link in der Registrierungs-E-Mail
const RESET_MINUTEN      = 30;    // Link „Passwort vergessen“
const SITZUNG_TAGE       = 90;
const RUHE_TAGE          = 730;   // Konto ohne Anmeldung seit so vielen Tagen wird gelöscht
const MAX_FAVORITEN      = 200;
const MAX_DEPOT          = 10;          // Anleihen je Musterdepot (Nutzerentscheid 01.10.2026; je Anleihe eine Farbe im Schaubild)
const MAX_MUSTER         = 5;           // Musterdepots je Konto (Nutzerentscheid 02.10.2026)
const NAME_MAX           = 40;          // Zeichen im Namen eines Musterdepots
const NOTIZ_MAX          = 200;         // Zeichen einer Notiz (wie das Feld in bereich.js); die Grenze in Byte steht in ABLAGE
const NENNWERT_MAX       = 100000000;   // gedachter Nennwert je Anleihe, in der Währung der Anleihe
const PW_MIN             = 10;
const PW_MAX             = 200;
const COOKIE             = LOKAL ? 'bondarium-sitzung' : '__Host-bondarium-sitzung';
const NL_ORDNER          = __DIR__ . '/newsletter';   // ausgabe.json und anleihen.json aus dem Datenlauf (scripts/newsletter.py)
const NL_NBSP            = "\u{00A0}";   // geschütztes Leerzeichen vor „%“ und „Pkt.“ (wie die Website); Textfassungen setzen ein normales
const NL_JE_AUFRUF       = 40;    // E-Mails je Aufruf von newsletter-senden; der Workflow ruft so oft, bis nichts mehr offen ist
const NL_MERK_MAX        = 8;     // so viele gemerkte Anleihen zeigt eine Ausgabe (zuletzt gemerkte zuerst)
const NL_FRISCH_TAGE     = 2;     // ältere Ausgaben werden nicht mehr verschickt
const BESUCH_PAUSE        = 3 * 3600;   // nach so vielen Sekunden ohne Aufruf beginnt ein neuer Besuch
const MELDUNG_TAGE        = 7;          // „Zinstermin steht an“: so viele Tage vorher (Fälligkeiten: erinnerung.php, 20 Tage und am Tag)
const MELDUNG_MAILS       = 200;        // E-Mails je Aufruf von meldungen-senden
// Persönliche Ablage (seit 02.10.2026): Art → [Höchstzahl der Einträge, Höchstlänge des Werts in Bytes (JSON)].
// Der Schlüssel ist je Art eine ISIN, ein Seitenname, eine kurze Kennung – Muster siehe ablage_schluessel().
// Die Arten „suche“ und „rechnung“ gab es nur am 02.10.2026 (auf Nutzerwunsch am selben Abend entfernt); aufraeumen() löscht ihre Reste.
const ABLAGE = [
    'notiz'       => [200, 1000],   // Schlüssel ISIN: private Notiz zur gemerkten Anleihe – höchstens NOTIZ_MAX Zeichen; 1000 Byte, damit auch „€“, „“ und Emoji passen (T-109)
    'liste'       => [12, 3400],    // eigene Liste der Merkliste: {n: Name, i: [ISIN, …]}
    'gelesen'     => [120, 8],      // Schlüssel Seitenname: „Als gelesen markieren“
    'lesezeichen' => [40, 400],     // Schlüssel Seite oder Seite#Abschnitt: {t: Titel, a: Abschnitt}
    'begriff'     => [80, 160],     // Schlüssel Kennung im Glossar: Titel des Begriffs
    'kennzahl'    => [12, 8],       // Schlüssel Kennzahl für „Mein Zins-Blick“
    'einstellung' => [12, 300],     // Einstellungen: nur noch „Zuletzt angesehen“ an/aus (EINSTELLUNGEN)
    'meldung'     => [20, 500],     // Meldung: {i: ISIN oder „*“, b: Bedingung, w: Wert, m: per E-Mail, an: eingeschaltet, a/aw: ausgelöst am/mit, bis: …}
    'check'       => [20, 8],       // Schlüssel Schritt der Checkliste „Deine erste Anleihe“
    'angesehen'   => [8, 200],      // „Zuletzt angesehen“ – nur wenn unter „Konto“ eingeschaltet; der älteste Eintrag fällt heraus
];
// Erlaubte Einstellungen. Die Voreinstellungen Ordergebühr, Anlagebetrag, Freistellungsauftrag und Startfilter gab es nur am 02.10.2026
// (auf Nutzerwunsch entfernt); aufraeumen() löscht ihre Reste. Die Kirchensteuer wurde nie gespeichert (Art. 9 DSGVO).
const EINSTELLUNGEN = ['zuletzt'];
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
// Dieselben Grenzen ohne „lm“ für Aktionen, bei denen die Inhaberin schon angemeldet ist und ihr Passwort bestätigt (Passwort
// ändern, E-Mail ändern, Konto löschen): Fremde Fehlversuche auf ihre Adresse sperren sie dort nicht aus. Ihre eigenen falschen
// Eingaben bremst weiter „le“, und gezählt wird weiter auch „lm“ (Technik-Test 08.10.2026, T-24 Teil a). Bei der Anmeldung
// bleibt „lm“ (offene Entscheidung des Betreibers).
const LOGIN_GRENZEN_ANGEMELDET = [
    ['le', 900, 5],
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

/** Feld aus $_POST/$_GET als Text; eine Liste („feld[]=…“) zählt wie ein leeres Feld – ohne PHP-Warnung im Fehlerprotokoll (T-132). */
function text(array $q, string $k): string
{
    $v = $q[$k] ?? '';
    return is_string($v) ? $v : '';
}

/** E-Mail-Adresse aus dem Formular, klein geschrieben; ungültig → Antwort „email“. */
function email_lesen(): string
{
    $mail = strtolower(trim(text($_POST, 'email')));
    if ($mail === '' || strlen($mail) > 254 || preg_match('/[\r\n]/', $mail) || filter_var($mail, FILTER_VALIDATE_EMAIL) === false) {
        antwort(422, 'email');
    }
    return $mail;
}

/** Anleihe, die nach dem Anmelden gleich gemerkt wird (vom Merken-Knopf), oder null. */
function isin_lesen(): ?string
{
    $isin = strtoupper(trim(text($_POST, 'isin')));
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
    // Marke „.angelegt“ (seit 09.10.2026, Technik-Test T-22): Gibt es sie, gab es hier schon eine Datenbank. Fehlt dann die Datei
    // (Datei wird gerade von Hand ausgetauscht, docs/BETRIEB.md) oder liegen zwei da, wird nichts angelegt und nichts geraten –
    // Antwort 503 „speicher“, bis wieder genau eine Datei da ist. Sonst entstünde still eine leere Datenbank, und danach
    // entschiede der zufällige Dateiname, welche gilt.
    $marke = DATEN . '/.angelegt';
    if (count($dateien) > 1 || (!$dateien && is_file($marke))) {
        error_log('konto.php: ' . (count($dateien) > 1 ? count($dateien) . ' Datenbank-Dateien in konto-daten/' : 'Datenbank-Datei fehlt, konto-daten/.angelegt ist da')
            . ' – keine neue angelegt (docs/BETRIEB.md)');
        if ($sperre) {
            flock($sperre, LOCK_UN);
            fclose($sperre);
        }
        antwort(503, 'speicher');
    }
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
            // Fassung 3 (01.10.2026): Musterdepot – je Nutzer Anleihen mit einem gedachten Nennwert
            $db->exec('BEGIN IMMEDIATE');
            $db->exec('CREATE TABLE IF NOT EXISTS depot (nutzer INTEGER NOT NULL REFERENCES nutzer(id) ON DELETE CASCADE, isin TEXT NOT NULL, nennwert INTEGER NOT NULL, seit INTEGER NOT NULL, PRIMARY KEY (nutzer, isin))');
            $db->exec('PRAGMA user_version = 3');
            $db->exec('COMMIT');
        }
        if ($fassung < 4) {
            // Fassung 4 (02.10.2026): mehrere Musterdepots je Nutzer mit eigenem Namen. Das bisherige Depot jedes Nutzers wird
            // „Musterdepot 1“; die Anleihen hängen jetzt am Musterdepot statt am Nutzer.
            $db->exec('BEGIN IMMEDIATE');
            $db->exec('CREATE TABLE IF NOT EXISTS musterdepots (id INTEGER PRIMARY KEY, nutzer INTEGER NOT NULL REFERENCES nutzer(id) ON DELETE CASCADE, name TEXT NOT NULL, erstellt INTEGER NOT NULL)');
            $db->exec('CREATE INDEX IF NOT EXISTS musterdepots_n ON musterdepots (nutzer)');
            $db->exec('CREATE TABLE depot_neu (muster INTEGER NOT NULL REFERENCES musterdepots(id) ON DELETE CASCADE, isin TEXT NOT NULL, nennwert INTEGER NOT NULL, seit INTEGER NOT NULL, PRIMARY KEY (muster, isin))');
            $db->exec("INSERT INTO musterdepots (nutzer, name, erstellt) SELECT nutzer, 'Musterdepot 1', MIN(seit) FROM depot GROUP BY nutzer ORDER BY nutzer");
            $db->exec('INSERT INTO depot_neu (muster, isin, nennwert, seit) SELECT m.id, d.isin, d.nennwert, d.seit FROM depot d JOIN musterdepots m ON m.nutzer = d.nutzer');
            $db->exec('DROP TABLE depot');
            $db->exec('ALTER TABLE depot_neu RENAME TO depot');
            $db->exec('PRAGMA user_version = 4');
            $db->exec('COMMIT');
        }
        if ($fassung < 5) {
            // Fassung 5 (02.10.2026): E-Mail 30 Tage vor jeder Fälligkeit – Schalter je Konto (anfangs aus) und die verschickten
            // Erinnerungen (erinnerung.php trägt sie ein und löscht sie nach der Fälligkeit)
            $db->exec('BEGIN IMMEDIATE');
            $db->exec('ALTER TABLE nutzer ADD COLUMN erinnern INTEGER NOT NULL DEFAULT 0');
            $db->exec('CREATE TABLE IF NOT EXISTS erinnert (nutzer INTEGER NOT NULL REFERENCES nutzer(id) ON DELETE CASCADE, isin TEXT NOT NULL, faellig TEXT NOT NULL, gesendet INTEGER NOT NULL, PRIMARY KEY (nutzer, isin, faellig))');
            $db->exec('PRAGMA user_version = 5');
            $db->exec('COMMIT');
        }
        if ($fassung < 6) {
            // Fassung 6 (02.10.2026): Newsletter – Einwilligung je Konto (und je offener Registrierung), Kalenderwoche der
            // zuletzt erhaltenen Ausgabe, An-/Abmeldungen ohne Kontobezug zum Zählen
            $db->exec('BEGIN IMMEDIATE');
            $db->exec('ALTER TABLE nutzer ADD COLUMN newsletter INTEGER NOT NULL DEFAULT 0');
            $db->exec('ALTER TABLE nutzer ADD COLUMN newsletter_seit INTEGER');
            $db->exec("ALTER TABLE nutzer ADD COLUMN newsletter_kw TEXT NOT NULL DEFAULT ''");
            $db->exec('ALTER TABLE links ADD COLUMN newsletter INTEGER NOT NULL DEFAULT 0');
            $db->exec('CREATE TABLE IF NOT EXISTS newsletter_log (zeit INTEGER NOT NULL, art TEXT NOT NULL)');
            $db->exec('PRAGMA user_version = 6');
            $db->exec('COMMIT');
        }
        if ($fassung < 7) {
            // Fassung 7 (02.10.2026 abends): „Mein Bondarium“ – persönliche Ablage, Rendite am Tag des Merkens, Beginn des
            // laufenden und des vorigen Besuchs, Gerätebezeichnung je Anmeldung, Links zum Ändern der E-Mail-Adresse
            $db->exec('BEGIN IMMEDIATE');
            $db->exec('CREATE TABLE IF NOT EXISTS ablage (nutzer INTEGER NOT NULL REFERENCES nutzer(id) ON DELETE CASCADE, art TEXT NOT NULL, schluessel TEXT NOT NULL, wert TEXT NOT NULL, zeit INTEGER NOT NULL, PRIMARY KEY (nutzer, art, schluessel))');
            $db->exec('ALTER TABLE favoriten ADD COLUMN rendite REAL');
            $db->exec('ALTER TABLE nutzer ADD COLUMN besuch INTEGER NOT NULL DEFAULT 0');
            $db->exec('ALTER TABLE nutzer ADD COLUMN besuch_vor INTEGER NOT NULL DEFAULT 0');
            $db->exec("ALTER TABLE sitzungen ADD COLUMN geraet TEXT NOT NULL DEFAULT ''");
            $db->exec('ALTER TABLE sitzungen ADD COLUMN erstellt INTEGER NOT NULL DEFAULT 0');
            $db->exec('ALTER TABLE sitzungen ADD COLUMN zuletzt INTEGER NOT NULL DEFAULT 0');
            $db->exec('ALTER TABLE links ADD COLUMN nutzer INTEGER');
            $db->exec('PRAGMA user_version = 7');
            $db->exec('COMMIT');
        }
        if ($fassung < 8) {
            // Fassung 8 (03.10.2026, Nutzerentscheid „E-Mails an einer Stelle“): Fälligkeiten kommen nur noch über „Vor Fälligkeit“
            // (Spalte erinnern, jetzt für Merkliste und Musterdepots); die Meldung „termin“ nennt nur noch Zinstermine. Wer diese
            // Meldung bisher per E-Mail hatte, bekäme Fälligkeiten sonst nicht mehr – für diese Konten wird erinnern einmal gesetzt.
            $db->exec('BEGIN IMMEDIATE');
            $setze = $db->prepare('UPDATE nutzer SET erinnern = 1 WHERE id = ?');
            foreach ($db->query("SELECT nutzer, wert FROM ablage WHERE art = 'meldung'")->fetchAll(PDO::FETCH_NUM) as [$nutzer, $wert]) {
                $w = json_decode((string)$wert, true);
                if (is_array($w) && ($w['b'] ?? '') === 'termin' && !empty($w['an']) && !empty($w['m'])) {
                    $setze->execute([(int)$nutzer]);
                }
            }
            $db->exec('PRAGMA user_version = 8');
            $db->exec('COMMIT');
        }
        if ($fassung < 9) {
            // Fassung 9 (09.10.2026, Technik-Test 08.10.2026): Indizes für die häufigen Abfragen je Konto und je Adresse (T-111) und
            // der Zeitpunkt, ab dem die Ein-Klick-Links an Kontonummer und Anlagezeitpunkt hängen (T-103, siehe link_kennung()) –
            // die alte Form gilt nur noch für Konten, die vorher angelegt wurden.
            $db->exec('BEGIN IMMEDIATE');
            $db->exec('CREATE INDEX IF NOT EXISTS sitzungen_n ON sitzungen (nutzer)');
            $db->exec('CREATE INDEX IF NOT EXISTS links_e ON links (email)');
            $db->exec('CREATE INDEX IF NOT EXISTS links_n ON links (nutzer)');
            $db->prepare("INSERT OR IGNORE INTO meta (k, v) VALUES ('kennung_neu_ab', ?)")->execute([(string)time()]);
            $db->exec('PRAGMA user_version = 9');
            $db->exec('COMMIT');
        }
        if (!is_file($marke)) {
            @file_put_contents($marke, "Hier gab es eine Datenbank (konto.php, docs/BETRIEB.md). Nicht löschen.\n");
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

/**
 * Anschluss für die Bremsen: IPv4 wie sie ist, IPv6 als ganzes /64-Netz (ein Anschluss bekommt meist ein ganzes /64 und kann die
 * Adresse darin frei wechseln), IPv4 in IPv6-Schreibweise (::ffff:a.b.c.d) als IPv4 – sonst teilten sich alle diese Adressen
 * das Netz „::/64“. Gespeichert wird davon nur der Hashwert (schluessel_hash). Technik-Test 08.10.2026, T-23.
 */
function ip(): string
{
    $ip = (string)($_SERVER['REMOTE_ADDR'] ?? '');
    $b = @inet_pton($ip);
    if ($b === false || strlen($b) !== 16) {
        return $ip;
    }
    if (substr($b, 0, 12) === str_repeat("\0", 10) . "\xff\xff") {
        return (string)inet_ntop(substr($b, 12));
    }
    return inet_ntop(substr($b, 0, 8) . str_repeat("\0", 8)) . '/64';
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

/**
 * Obergrenze für verschickte E-Mails prüfen und den Versand zählen. Erreicht je Adresse oder Anschluss → Antwort „zuviel“;
 * erreicht nur die Gesamtgrenze → „zuviel-gesamt“: Dann liegt es nicht an dieser Adresse, und die Seite sagt das so
 * (Technik-Test 08.10.2026, T-25; die Höhe der Grenzen ist eine offene Entscheidung des Betreibers).
 */
function versand_zaehlen(string $mail): void
{
    $schl = ['m' => 'm:' . schluessel_hash($mail), 'i' => 'i:' . schluessel_hash(ip()), 'g' => 'g'];
    if (gebremst(array_filter(GRENZEN, fn($g) => $g[0] !== 'g'), $schl)) {
        antwort(429, 'zuviel');
    }
    if (gebremst(array_filter(GRENZEN, fn($g) => $g[0] === 'g'), $schl)) {
        antwort(429, 'zuviel-gesamt');
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

/** Gerätebezeichnung für die Liste „Angemeldete Geräte“: nur Geräteart und Browser, z. B. „Mac (Safari)“ – nicht die ganze Kennung. */
function geraet(): string
{
    $ua = (string)($_SERVER['HTTP_USER_AGENT'] ?? '');
    $g = 'Gerät';
    foreach (['iPhone' => 'iPhone', 'iPad' => 'iPad', 'Android' => 'Android', 'Macintosh' => 'Mac', 'Windows' => 'Windows', 'CrOS' => 'Chromebook', 'Linux' => 'Linux'] as $muster => $name) {
        if (strpos($ua, $muster) !== false) { $g = $name; break; }
    }
    $b = '';
    foreach (['Edg' => 'Edge', 'OPR' => 'Opera', 'Firefox' => 'Firefox', 'FxiOS' => 'Firefox', 'CriOS' => 'Chrome', 'Chrome' => 'Chrome', 'Safari' => 'Safari'] as $muster => $name) {
        if (strpos($ua, $muster) !== false) { $b = $name; break; }
    }
    return $b === '' ? $g : "$g ($b)";
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
    $db->prepare('INSERT INTO sitzungen (hash, nutzer, ablauf, geraet, erstellt, zuletzt) VALUES (?, ?, ?, ?, ?, ?)')
       ->execute([hash('sha256', $t), $id, $ablauf, geraet(), time(), time()]);
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
    $s = $db->prepare('SELECT s.nutzer AS id, s.ablauf, s.zuletzt AS szuletzt, n.email, n.zuletzt, n.pw FROM sitzungen s JOIN nutzer n ON n.id = s.nutzer WHERE s.hash = ? AND s.ablauf > ?');
    $s->execute([$hash, $jetzt]);
    $z = $s->fetch(PDO::FETCH_ASSOC);
    // Leseanweisung schließen, bevor dieselbe Verbindung schreibt: Eine offene Anweisung hält die Lesesperre, und SQLite
    // bricht das Schreiben bei gleichzeitigen Anfragen sofort mit „database is locked“ ab (Technik-Test 08.10.2026, T-20)
    $s->closeCursor();
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
    if ($jetzt - (int)$z['szuletzt'] > 86400) {
        $db->prepare('UPDATE sitzungen SET zuletzt = ? WHERE hash = ?')->execute([$jetzt, $hash]);   // „zuletzt genutzt“ je Gerät, höchstens einmal am Tag
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

/** Merkliste, zuletzt Gemerktes zuerst: [[ISIN, Zeitpunkt, Rendite am Tag des Merkens oder null], …] */
function favoriten(int $id): array
{
    $s = db()->prepare('SELECT isin, seit, rendite FROM favoriten WHERE nutzer = ? ORDER BY seit DESC, isin');
    $s->execute([$id]);
    $aus = [];
    foreach ($s->fetchAll(PDO::FETCH_NUM) as $z) {
        $aus[] = [(string)$z[0], (int)$z[1], $z[2] === null ? null : (float)$z[2]];
    }
    return $aus;
}

/**
 * Zeile einer Anleihe aus dem letzten Datenlauf (newsletter/anleihen.json: ISIN → [0 Name, 1 Kupon-Text, 2 Fälligkeit, 3 Kurs,
 * 4 Rendite|null, 5 Veränderung zur Vorwoche|null, 6 nächster Zinstermin|null, 7 Zinsart, 8 Titel, 9 Restlaufzeit,
 * 10 Zinstermin geschätzt 1|0] – Felder 7 bis 10 seit 03.10.2026, Beschreibung im Kopf von scripts/newsletter.py) oder null.
 * Die Datei ist groß; gesucht wird die eine Zeile im Text, ohne alles zu entpacken.
 */
function zeile_heute(string $isin): ?array
{
    static $roh = null;
    if ($roh === null) {
        $roh = @file_get_contents(NL_ORDNER . '/anleihen.json');
        $roh = is_string($roh) ? $roh : '';
    }
    $p = $roh === '' ? false : strpos($roh, '"' . $isin . '":');
    if ($p === false) {
        return null;
    }
    $a = strpos($roh, '[', $p);
    $e = $a === false ? false : strpos($roh, '],', $a);
    if ($e === false && $a !== false) {
        $e = strpos($roh, ']}', $a);   // letzte Zeile der Datei
    }
    $z = $e === false ? null : json_decode(substr($roh, $a, $e - $a + 1), true);
    return is_array($z) && count($z) >= 7 ? $z : null;
}

/** Rendite am Tag des Merkens (aus dem letzten Datenlauf) oder null */
function rendite_heute(string $isin): ?float
{
    $z = zeile_heute($isin);
    return $z !== null && is_numeric($z[4]) ? (float)$z[4] : null;
}

/** Persönliche Ablage: Art → { Schlüssel: [Wert, Zeitpunkt] } (leere Arten fehlen) */
function ablage(int $id, ?string $art = null): array
{
    $s = db()->prepare('SELECT art, schluessel, wert, zeit FROM ablage WHERE nutzer = ?' . ($art !== null ? ' AND art = ?' : '') . ' ORDER BY zeit, schluessel');
    $s->execute($art !== null ? [$id, $art] : [$id]);
    $aus = [];
    foreach ($s->fetchAll(PDO::FETCH_NUM) as $z) {
        $aus[(string)$z[0]][(string)$z[1]] = [json_decode((string)$z[2], true), (int)$z[3]];
    }
    return $art !== null ? ($aus[$art] ?? []) : $aus;
}

/** Schlüssel der Ablage prüfen: je Art eine ISIN, ein Seitenname (mit Abschnitt) oder eine kurze Kennung */
function ablage_schluessel(string $art, string $k): bool
{
    switch ($art) {
        case 'notiz':
            return ist_isin($k);
        case 'gelesen':
            return preg_match('/^[a-z0-9-]{1,60}$/', $k) === 1;
        case 'lesezeichen':
            return preg_match('/^[a-z0-9-]{1,60}(#[A-Za-z0-9_-]{1,60})?$/', $k) === 1;
        case 'angesehen':
            return ist_isin($k) || preg_match('/^[a-z0-9-]{1,60}$/', $k) === 1;
        case 'einstellung':
            return in_array($k, EINSTELLUNGEN, true);
        default:
            return preg_match('/^[a-z0-9-]{1,40}$/', $k) === 1;
    }
}

/** Angemeldete Geräte: [[Bezeichnung, zuletzt genutzt, dieses Gerät?], …], zuletzt genutzte zuerst */
function geraete(int $id): array
{
    $t = $_COOKIE[COOKIE] ?? '';
    $hier = ist_kennwort($t) ? hash('sha256', $t) : '';
    $s = db()->prepare('SELECT hash, geraet, zuletzt, erstellt FROM sitzungen WHERE nutzer = ? AND ablauf > ? ORDER BY zuletzt DESC, erstellt DESC');
    $s->execute([$id, time()]);
    $aus = [];
    foreach ($s->fetchAll(PDO::FETCH_NUM) as $z) {
        $aus[] = [(string)$z[1] !== '' ? (string)$z[1] : 'Gerät', max((int)$z[2], (int)$z[3]), hash_equals((string)$z[0], $hier)];
    }
    return $aus;
}

/**
 * Musterdepots in der Reihenfolge des Anlegens, je mit ihren Anleihen in der Reihenfolge des Hineinlegens:
 * [[Nummer, Name, [[ISIN, Nennwert, Zeitpunkt], …]], …]. Wer noch keines hat, bekommt ein leeres „Musterdepot 1“ mit der
 * Nummer 0 – angelegt wird es erst, wenn etwas hineinkommt (muster_erstes).
 */
function musterdepots(int $id): array
{
    $db = db();
    $s = $db->prepare('SELECT id, name FROM musterdepots WHERE nutzer = ? ORDER BY id');
    $s->execute([$id]);
    $aus = [];
    $nr = [];
    foreach ($s->fetchAll(PDO::FETCH_NUM) as $z) {
        $nr[(int)$z[0]] = count($aus);
        $aus[] = [(int)$z[0], (string)$z[1], []];
    }
    if (!$aus) {
        return [[0, 'Musterdepot 1', []]];
    }
    $s = $db->prepare('SELECT d.muster, d.isin, d.nennwert, d.seit FROM depot d JOIN musterdepots m ON m.id = d.muster WHERE m.nutzer = ? ORDER BY d.seit, d.isin');
    $s->execute([$id]);
    foreach ($s->fetchAll(PDO::FETCH_NUM) as $z) {
        $aus[$nr[(int)$z[0]]][2][] = [(string)$z[1], (int)$z[2], (int)$z[3]];
    }
    return $aus;
}

/** Nummer eines eigenen Musterdepots aus dem Formular (fehlt sie oder ist sie 0: das erste, notfalls neu angelegt) */
function muster_lesen(int $id): int
{
    $m = (int)text($_POST, 'muster');
    if ($m <= 0) {
        return muster_erstes($id);
    }
    $s = db()->prepare('SELECT 1 FROM musterdepots WHERE id = ? AND nutzer = ?');
    $s->execute([$m, $id]);
    if (!$s->fetchColumn()) {
        antwort(404, 'muster');
    }
    return $m;
}

function muster_erstes(int $id): int
{
    $db = db();
    $s = $db->prepare('SELECT MIN(id) FROM musterdepots WHERE nutzer = ?');
    $s->execute([$id]);
    $m = (int)$s->fetchColumn();
    if ($m > 0) {
        return $m;
    }
    $db->prepare('INSERT INTO musterdepots (nutzer, name, erstellt) VALUES (?, ?, ?)')->execute([$id, 'Musterdepot 1', time()]);
    return (int)$db->lastInsertId();
}

function muster_anzahl(int $id): int
{
    $s = db()->prepare('SELECT COUNT(*) FROM musterdepots WHERE nutzer = ?');
    $s->execute([$id]);
    return (int)$s->fetchColumn();
}

/**
 * Name eines Musterdepots: Leerraum (auch Tabulator und Zeilenumbruch) wird ein Leerzeichen – erst danach fallen Steuer- und
 * unsichtbare Format-Zeichen weg (Schreibrichtung U+202E, Breite null U+200B …; Technik-Test 08.10.2026, T-108), sonst klebten
 * „Rente⇥2030“ zu „Rente2030“ zusammen. Der Verbinder U+200D bleibt, er hält Emoji wie 👨‍👩‍👧 zusammen. Höchstens NAME_MAX
 * Zeichen; leer → $ersatz
 */
function name_lesen(string $roh, string $ersatz): string
{
    $n = (string)preg_replace('/\s+/u', ' ', $roh);
    $n = trim((string)preg_replace('/ {2,}/', ' ', (string)preg_replace('/[\p{Cc}]|(?!\x{200D})\p{Cf}/u', '', $n)));
    if ($n === '') {
        return $ersatz;
    }
    return function_exists('mb_substr') ? mb_substr($n, 0, NAME_MAX, 'UTF-8') : substr($n, 0, NAME_MAX);
}

/** Was die Seite über ein angemeldetes Konto wissen muss. „depot“ (das erste Musterdepot) bleibt für ältere Seiten im Browser. */
function konto_stand(int $id, string $email): array
{
    $m = musterdepots($id);
    $s = db()->prepare('SELECT erinnern, newsletter, besuch_vor FROM nutzer WHERE id = ?');
    $s->execute([$id]);
    $z = $s->fetch(PDO::FETCH_NUM) ?: [0, 0, 0];
    return ['angemeldet' => true, 'email' => $email, 'favoriten' => favoriten($id), 'depots' => $m, 'depot' => $m[0][2], 'erinnern' => (int)$z[0] === 1,
        'newsletter' => (int)$z[1] === 1, 'ablage' => (object)ablage($id), 'besuch' => (int)$z[2], 'geraete' => geraete($id)];
}

function merke(int $id, string $isin): bool
{
    $db = db();
    // Zählen und Einfügen in EINER Anweisung (Technik-Test 08.10.2026, T-20): Vorher lief erst ein COUNT, dessen offene
    // Leseanweisung bei gleichzeitigem Merken „database is locked“ auslöste – und zwei Anfragen zugleich konnten beide
    // unter MAX_FAVORITEN zählen. So bleibt die Grenze auch bei gleichzeitigen Anfragen, und vor dem Schreiben ist nichts offen.
    $s = $db->prepare('INSERT OR IGNORE INTO favoriten (nutzer, isin, seit, rendite) SELECT ?, ?, ?, ? WHERE (SELECT COUNT(*) FROM favoriten WHERE nutzer = ?) < ' . MAX_FAVORITEN);
    $s->execute([$id, $isin, time(), rendite_heute($isin), $id]);
    if ($s->rowCount() > 0) {
        return true;
    }
    // nichts eingefügt: schon gemerkt (true) oder die Merkliste ist voll (false)
    $s = $db->prepare('SELECT 1 FROM favoriten WHERE nutzer = ? AND isin = ?');
    $s->execute([$id, $isin]);
    $da = (bool)$s->fetchColumn();
    $s->closeCursor();
    return $da;
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
    $db->prepare('DELETE FROM newsletter_log WHERE zeit < ?')->execute([$jetzt - 25 * 31 * 86400]);
    $db->exec("DELETE FROM ablage WHERE art IN ('suche', 'rechnung')");   // entfernte Arten (siehe ABLAGE)
    $db->exec("DELETE FROM ablage WHERE art = 'einstellung' AND schluessel <> 'zuletzt'");   // entfernte Voreinstellungen (siehe EINSTELLUNGEN)
    // „Zuletzt angesehen“ nur bei eingeschalteter Einstellung (Datenschutzerklärung: „schaltest du es wieder aus, löschen wir sie“) –
    // räumt auch Reste aus der Zeit auf, als nur die Seite gelöscht hat (Technik-Test 08.10.2026, T-18)
    $db->exec("DELETE FROM ablage WHERE art = 'angesehen' AND nutzer NOT IN (SELECT nutzer FROM ablage WHERE art = 'einstellung' AND schluessel = 'zuletzt' AND wert = '1')");
    // Notizen zu Anleihen, die seit 30 Tagen nicht mehr auf der Merkliste stehen
    $db->prepare("DELETE FROM ablage WHERE art = 'notiz' AND zeit < ? AND NOT EXISTS (SELECT 1 FROM favoriten f WHERE f.nutzer = ablage.nutzer AND f.isin = ablage.schluessel)")
       ->execute([$jetzt - 30 * 86400]);
}

/** Gültigen Link lesen (ohne ihn zu verbrauchen) oder Antwort „link“. */
function link_lesen(string $art): array
{
    $t = text($_POST, 'token');
    if (!ist_kennwort($t)) {
        antwort(410, 'link');
    }
    $hash = hash('sha256', $t);
    $s = db()->prepare('SELECT hash, email, isin, pw, art, newsletter, nutzer FROM links WHERE hash = ? AND ablauf > ?' . ($art !== '' ? ' AND art = ?' : ''));
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

/** Aufrufe des Workflows (Wochenbrief, Meldungen): nur mit dem Schlüssel des Auslösers im Kopf X-Trigger-Key, sonst Antwort „zugang“. */
function ausloeser_pruefen(): void
{
    $cfg = is_file(__DIR__ . '/trigger/refresh-config.php') ? require __DIR__ . '/trigger/refresh-config.php' : [];
    $soll = LOKAL ? 'lokal' : trim((string)($cfg['secret'] ?? ''));
    if ($soll === '' || !hash_equals($soll, trim((string)($_SERVER['HTTP_X_TRIGGER_KEY'] ?? '')))) {
        antwort(403, 'zugang');
    }
}

// ---------- Newsletter (seit 02.10.2026, docs/NEWSLETTER.md) ----------

/**
 * Kennung der Ein-Klick-Links in E-Mails – Wochenbrief abbestellen („nl“), keine Meldungen per E-Mail („meldungen-aus“),
 * Erinnerung vor Fälligkeit aus („erinnerung-aus“, dieselbe Formel in erinnerung_token(), erinnerung.php): „Nummer.Prüfsumme“,
 * die Prüfsumme über Zweck, Kontonummer und Anlagezeitpunkt mit dem Schlüssel der Datenbank. Seit 09.10.2026 (Technik-Test
 * 08.10.2026, T-103): vorher hing sie an der Adresse (ein Abmelde-Link wirkte nach einem Adresswechsel nicht mehr) bzw. nur an der
 * Nummer (die Nummer eines gelöschten Kontos wird wieder vergeben – sein alter Link traf dann das neue Konto).
 */
function link_kennung(string $zweck, int $id, int $erstellt): string
{
    return $id . '.' . schluessel_hash($zweck . '|' . $id . '|' . $erstellt);
}

/**
 * Wurde das Konto vor der Umstellung der Kennungen (Fassung 9) angelegt? Nur dann gilt die alte Form noch – seine E-Mails tragen
 * sie. Ein Konto aus derselben Sekunde wie die Umstellung zählt als neu: E-Mails mit Ein-Klick-Links bekam es noch keine.
 */
function kennung_alt_erlaubt(int $erstellt): bool
{
    static $ab = null;
    if ($ab === null) {
        $ab = (int)db()->query("SELECT v FROM meta WHERE k = 'kennung_neu_ab'")->fetchColumn();
    }
    return $erstellt < $ab;
}

/** Kennung eines Ein-Klick-Links prüfen → Kontonummer, oder null: kein Konto mit dieser Nummer, oder die Kennung passt nicht */
function link_kennung_pruefen(string $zweck, string $kennung): ?int
{
    if (!preg_match('/^(\d{1,12})\.[0-9a-f]{32}$/D', $kennung, $m)) {
        return null;
    }
    $id = (int)$m[1];
    $s = db()->prepare('SELECT email, erstellt FROM nutzer WHERE id = ?');
    $s->execute([$id]);
    $z = $s->fetch(PDO::FETCH_NUM);
    $s->closeCursor();   // vor dem Schreiben des Aufrufers schließen (T-20, siehe nutzer())
    if (!$z) {
        return null;
    }
    if (hash_equals(link_kennung($zweck, $id, (int)$z[1]), $kennung)) {
        return $id;
    }
    // alte Form (bis 09.10.2026): Wochenbrief über Nummer und Adresse, Meldungen und Erinnerung nur über die Nummer
    $alt = ['nl' => 'nl|' . $id . '|' . $z[0], 'meldungen-aus' => 'meldungen-aus:' . $id, 'erinnerung-aus' => 'erinnerung-aus:' . $id][$zweck] ?? null;
    if ($alt !== null && kennung_alt_erlaubt((int)$z[1]) && hash_equals($id . '.' . schluessel_hash($alt), $kennung)) {
        return $id;
    }
    return null;
}

/** Newsletter an- oder abschalten; zählt die Änderung (ohne Kontobezug). Gibt true zurück, wenn sich etwas geändert hat. */
function nl_setzen(int $id, bool $an): bool
{
    $db = db();
    $s = $db->prepare('UPDATE nutzer SET newsletter = ?, newsletter_seit = ? WHERE id = ? AND newsletter <> ?');
    $s->execute([$an ? 1 : 0, $an ? time() : null, $id, $an ? 1 : 0]);
    if ($s->rowCount() === 0) {
        return false;
    }
    $db->prepare('INSERT INTO newsletter_log (zeit, art) VALUES (?, ?)')->execute([time(), $an ? 'an' : 'ab']);
    return true;
}

/** Abbestellen über die Kennung des Abmelde-Links (ohne Anmeldung). false: Kennung passt zu keinem Konto. */
function nl_abbestellen(string $kennung): bool
{
    $id = link_kennung_pruefen('nl', $kennung);
    if ($id === null) {
        return false;
    }
    nl_setzen($id, false);
    return true;
}

/** Zahl mit Dezimalkomma, Tausenderpunkt und echtem Minus (wie zahl_de in scripts/_common.py) */
function nl_zahl(float $v, int $st = 2): string
{
    $s = number_format(abs($v), $st, ',', '.');
    return ($v < 0 && round(abs($v), $st) > 0 ? '−' : '') . $s;
}

function nl_datum(string $iso): string
{
    return substr($iso, 8, 2) . '.' . substr($iso, 5, 2) . '.' . substr($iso, 0, 4);
}

// Schreibweisen der Anleihen-Angaben in E-Mails – dieselben Regeln wie scripts/_common.py (pct_text, kurs_text, pkt_text) und
// felder.js auf der Website (Konzept „Einheitliche Anleihen-Angaben“, docs/ANLEIHEN-ANGABEN.md). Mit geschütztem Leerzeichen;
// Textfassungen gehen durch nl_text().

/** „3,85 %“ (Rendite) */
function nl_pct(float $v): string
{
    return nl_zahl($v) . NL_NBSP . '%';
}

/** „98,50 %“, „99,885 %“ (Kurs: zwei Stellen, drei nur wenn nötig) */
function nl_kurs(float $v): string
{
    return nl_zahl($v, abs($v * 100 - round($v * 100)) > 1e-6 ? 3 : 2) . NL_NBSP . '%';
}

/** „+0,12 Pkt.“, „−0,26 Pkt.“, „0,00 Pkt.“ (Veränderung in Prozentpunkten, mit Vorzeichen) */
function nl_pkt(float $v): string
{
    $r = round($v, 2);
    return ($r > 0 ? '+' : '') . nl_zahl($r) . NL_NBSP . 'Pkt.';
}

/** Textfassung: normales statt geschütztes Leerzeichen */
function nl_text(string $s): string
{
    return str_replace(NL_NBSP, ' ', $s);
}

/** Titel einer Zeile aus anleihen.json: Kurzname (Feld 0, in scripts/newsletter.py nach der Regel der Website), Kupon-Text (Feld 1),
 *  Fälligkeitsjahr – „Deutschland 2,60 % 2033“ (wie titel_aus() in newsletter.py und MC.felder.titel) */
function nl_titel(array $b): string
{
    return trim($b[0] . ' ' . $b[1]) . ' ' . ($b[2] !== '' ? substr((string)$b[2], 0, 4) : 'unbefristet');
}

/** Restlaufzeit ab heute wie MC.restlaufzeit und _common.restlaufzeit_text: unter einem Monat Tage, unter einem Jahr Monate, sonst Jahre */
function nl_restlaufzeit(string $faellig): string
{
    if ($faellig === '') {
        return 'unbefristet';
    }
    $j = (strtotime($faellig . ' 12:00:00 UTC') - strtotime(gmdate('Y-m-d') . ' 12:00:00 UTC')) / 86400 / 365.25;
    $tage = (int)floor($j * 365.25 + 0.5);
    if ($tage <= 0) return 'fällig';
    if ($tage < 31) return $tage . ($tage === 1 ? ' Tag' : ' Tage');
    $monate = (int)floor($tage / 30.44 + 0.5);
    if ($monate < 12) return $monate . ($monate === 1 ? ' Monat' : ' Monate');
    return nl_zahl($j, 1) . ' Jahre';
}

/**
 * Zweite Zeile je Anleihe: Kernzahlen in der Reihenfolge der Website-Tabellen, nur vorhandene Angaben – „Rendite 3,85 % ·
 * Restlaufzeit 4,2 Jahre (fällig 15.08.2033) · Kurs 98,50 %“. Gleiche Regel wie kern() in scripts/newsletter.py.
 */
function nl_kern(array $b): string
{
    $teile = is_numeric($b[4]) ? ['Rendite ' . nl_pct((float)$b[4])] : [];
    $rlz = (string)$b[2] !== '' ? nl_restlaufzeit((string)$b[2]) : '';
    $f = (string)$b[2] !== '' ? nl_datum((string)$b[2]) : '';
    if ($rlz !== '') {
        $teile[] = 'Restlaufzeit ' . $rlz . ($f !== '' ? ' (fällig ' . $f . ')' : '');
    } elseif ($f !== '') {
        $teile[] = 'fällig ' . $f;
    }
    if (is_numeric($b[3])) {
        $teile[] = 'Kurs ' . nl_kurs((float)$b[3]);
    }
    return implode(' · ', $teile);
}

/** „Nächster Zinstermin 20.05.2027“ mit „(geschätzt)“ oder „(mit Rückzahlung)“ wie in der Spalte der Website; "" ohne Termin */
function nl_zinstermin(array $b): string
{
    if (!is_string($b[6]) || $b[6] === '') {
        return '';
    }
    return 'Nächster Zinstermin ' . nl_datum($b[6]) . (!empty($b[8]) ? ' (geschätzt)' : ($b[6] === (string)$b[2] ? ' (mit Rückzahlung)' : ''));
}

/** Platzhalter {{NAME}} in einer Vorlage ersetzen. */
function nl_fuellen(string $vorlage, array $werte): string
{
    $paare = [];
    foreach ($werte as $k => $v) {
        $paare['{{' . $k . '}}'] = (string)$v;
    }
    return strtr($vorlage, $paare);
}

/**
 * Abschnitt „Deine Merkliste“ für eine Ausgabe: [Text, HTML]. $isins: Merkliste, zuletzt Gemerktes zuerst.
 * $anleihen: newsletter/anleihen.json (Felder siehe zeile_heute()). Die Vorlagen (Zeile, Rahmen, leer) und die Platzhalter je
 * Anleihe stehen in der Ausgabe ($a['merk'], scripts/newsletter.py MERK; dort baut vorschau() dieselben Werte): erste Zeile der
 * Titel, zweite die Kernzahlen (nl_kern), dritte – nur wenn es etwas gibt – Kurs zur Vorwoche und nächster Zinstermin.
 */
function nl_merkliste(array $a, array $anleihen, array $isins): array
{
    $v = $a['merk'];
    $text = '';
    $html = '';
    $n = 0;
    $mehr = 0;
    foreach ($isins as $isin) {
        $b = $anleihen[$isin] ?? null;
        if (!is_array($b) || count($b) < 7) {
            continue;   // ohne aktuellen Kurs steht die Anleihe nicht in der Ausgabe
        }
        if ($n >= NL_MERK_MAX) {
            $mehr++;
            continue;
        }
        $n++;
        $diff = is_numeric($b[5]) ? round((float)$b[5], 2) : null;   // Kurs zur Vorwoche, Prozentpunkte des Nennwerts
        $pkt = $diff === null ? '' : nl_pkt($diff);
        $zt = nl_zinstermin($b);
        $zusatz = implode(' · ', array_filter([$pkt !== '' ? 'Kurs ' . $pkt . ' zur Vorwoche' : '', $zt], fn($x) => $x !== ''));
        $w = [
            'TITEL' => nl_titel($b), 'LINK' => SEITE . '/anleihe.html?isin=' . $isin, 'KERN' => nl_kern($b),
            'ZUSATZ' => $zusatz !== '' ? '  ' . $zusatz . "\n" : '',   // dritte Zeile der Textfassung samt Einzug, sonst nichts
            'RENDITE' => is_numeric($b[4]) ? nl_pct((float)$b[4]) : '–', 'RESTLAUFZEIT' => nl_restlaufzeit((string)$b[2]),
            'FAELLIG' => (string)$b[2] !== '' ? nl_datum((string)$b[2]) : '', 'KURS' => nl_kurs((float)$b[3]), 'DIFF' => $pkt,
            'DIFF_FARBE' => $diff === null || $diff == 0 ? ($v['farbe_null'] ?? $v['farbe_plus']) : ($diff > 0 ? $v['farbe_plus'] : $v['farbe_minus']),
            'ZT' => $zt,
        ];
        $text .= nl_text(nl_fuellen($v['text_zeile'], $w));
        $html .= nl_fuellen($v['html_zeile'], array_map(fn($x) => htmlspecialchars((string)$x, ENT_QUOTES, 'UTF-8'), $w));
    }
    if ($n === 0) {
        return [$v['text_leer'], $v['html_leer']];
    }
    $weitere = $mehr > 0 ? 'und ' . $mehr . ($mehr === 1 ? ' weitere Anleihe' : ' weitere Anleihen') . ' auf deiner Merkliste' : '';
    return [
        nl_fuellen($v['text_rahmen'], ['ZEILEN' => $text, 'WEITERE' => $weitere === '' ? '' : $weitere . "\n"]),
        nl_fuellen($v['html_rahmen'], ['ZEILEN' => $html, 'WEITERE' => $weitere]),
    ];
}

/** Eine Ausgabe an eine Adresse schicken: Text- und HTML-Fassung, Abmelde-Link im Text und im Kopf der E-Mail. */
function nl_mail(array $a, string $an, string $kennung, array $merk, int $nr): bool
{
    $ab = SEITE . '/konto.html#nl-ab=' . $kennung;
    $text = nl_fuellen((string)$a['text'], ['MERKLISTE' => $merk[0], 'ABMELDEN' => $ab]);
    $html = nl_fuellen((string)$a['html'], ['MERKLISTE' => $merk[1], 'ABMELDEN' => htmlspecialchars($ab, ENT_QUOTES, 'UTF-8')]);
    $betreff = (string)$a['betreff'];
    if (LOKAL) {
        // lokal kein Versand: Text und HTML je E-Mail als Datei, zum Ansehen
        return file_put_contents(DATEN . "/lokal-newsletter-$nr.txt", "An: $an\nBetreff: $betreff\nAbmelden: $ab\n\n$text") !== false
            && file_put_contents(DATEN . "/lokal-newsletter-$nr.html", $html) !== false;
    }
    $grenze = 'nl-' . bin2hex(random_bytes(12));
    $kopf = implode("\r\n", [
        'From: Bondarium <' . ABSENDER . '>',
        'MIME-Version: 1.0',
        'Content-Type: multipart/alternative; boundary="' . $grenze . '"',
        'List-Unsubscribe: <' . SEITE . '/konto.php?nl=' . $kennung . '>',
        'List-Unsubscribe-Post: List-Unsubscribe=One-Click',
        'Precedence: bulk',
    ]);
    $koerper = "--$grenze\r\nContent-Type: text/plain; charset=UTF-8\r\nContent-Transfer-Encoding: base64\r\n\r\n" . chunk_split(base64_encode($text))
        . "--$grenze\r\nContent-Type: text/html; charset=UTF-8\r\nContent-Transfer-Encoding: base64\r\n\r\n" . chunk_split(base64_encode($html))
        . "--$grenze--\r\n";
    return mail($an, '=?UTF-8?B?' . base64_encode($betreff) . '?=', $koerper, $kopf, '-f ' . ABSENDER);
}

/** JSON-Datei aus dem Ordner newsletter/ lesen (vom Datenlauf geschrieben); null, wenn sie fehlt oder unlesbar ist. */
function nl_datei(string $name): ?array
{
    $roh = @file_get_contents(NL_ORDNER . '/' . $name);
    $d = is_string($roh) ? json_decode($roh, true) : null;
    return is_array($d) ? $d : null;
}

/**
 * Ausgabe verschicken (aktion=newsletter-senden, nur mit dem Schlüssel des Auslösers). Jeder Abonnent bekommt je
 * Kalenderwoche höchstens eine Ausgabe; je Aufruf gehen höchstens NL_JE_AUFRUF E-Mails raus. Verschickt wird nur,
 * wenn der Datenlauf die Ausgabe freigibt (versand = true: Versandtag und Daten vollständig) und sie frisch ist.
 * an=betreiber schickt stattdessen eine Probe mit Muster-Merkliste an die Betreiber-Adresse.
 */
function nl_senden(): array
{
    ausloeser_pruefen();
    $a = nl_datei('ausgabe.json');
    if ($a === null || !isset($a['kw'], $a['erstellt'], $a['betreff'], $a['text'], $a['html'], $a['merk'])) {
        return ['gesendet' => 0, 'offen' => 0, 'grund' => 'keine Ausgabe'];
    }
    $anleihen = nl_datei('anleihen.json') ?? [];
    $db = db();
    if (text($_POST, 'an') === 'betreiber') {
        $ok = nl_mail($a, ABSENDER, '0.' . str_repeat('0', 32), nl_merkliste($a, $anleihen, (array)($a['muster'] ?? [])), 0);
        return ['gesendet' => $ok ? 1 : 0, 'offen' => 0, 'kw' => $a['kw'], 'grund' => 'Probe an den Betreiber'];
    }
    $alter = (strtotime(date('Y-m-d')) - (int)strtotime((string)$a['erstellt'])) / 86400;
    if (empty($a['versand']) || $alter > NL_FRISCH_TAGE) {
        $grund = $alter > NL_FRISCH_TAGE ? 'Ausgabe veraltet' : (string)($a['grund'] ?? 'kein Versand');
        // Fällt der Versand am Versandtag wegen fehlender Daten aus: einmal je Woche den Betreiber benachrichtigen
        if (!empty($a['warnen']) && $alter <= NL_FRISCH_TAGE) {
            $s = $db->query("SELECT v FROM meta WHERE k = 'newsletter_warnung'")->fetchColumn();
            if ($s !== (string)$a['kw']) {
                $db->prepare("INSERT OR REPLACE INTO meta (k, v) VALUES ('newsletter_warnung', ?)")->execute([(string)$a['kw']]);
                mail_senden(ABSENDER, 'Bondarium: Wochenbrief nicht verschickt', 'der Wochenbrief ' . $a['kw'] . " wurde nicht verschickt.\n\nGrund: " . $grund);
            }
        }
        return ['gesendet' => 0, 'offen' => 0, 'kw' => $a['kw'], 'grund' => $grund];
    }
    $kw = (string)$a['kw'];
    $s = $db->prepare('SELECT id, email, erstellt FROM nutzer WHERE newsletter = 1 AND newsletter_kw <> ? ORDER BY id LIMIT ' . NL_JE_AUFRUF);
    $s->execute([$kw]);
    $fav = $db->prepare('SELECT isin FROM favoriten WHERE nutzer = ? ORDER BY seit DESC, isin');
    $merke = $db->prepare('UPDATE nutzer SET newsletter_kw = ? WHERE id = ?');
    $gesendet = 0;
    $fehler = 0;
    foreach ($s->fetchAll(PDO::FETCH_ASSOC) as $n) {
        $fav->execute([(int)$n['id']]);
        $merk = nl_merkliste($a, $anleihen, $fav->fetchAll(PDO::FETCH_COLUMN));
        if (nl_mail($a, (string)$n['email'], link_kennung('nl', (int)$n['id'], (int)$n['erstellt']), $merk, (int)$n['id'])) {
            $merke->execute([$kw, (int)$n['id']]);   // erst nach dem Versand – ein Abbruch verschickt beim nächsten Aufruf nichts doppelt
            $gesendet++;
        } else {
            $fehler++;
        }
    }
    $s = $db->prepare('SELECT COUNT(*) FROM nutzer WHERE newsletter = 1 AND newsletter_kw <> ?');
    $s->execute([$kw]);
    $offen = (int)$s->fetchColumn();
    $s->closeCursor();
    $s = $db->prepare('SELECT COUNT(*) FROM nutzer WHERE newsletter_kw = ?');
    $s->execute([$kw]);
    $empfaenger = (int)$s->fetchColumn();
    $s->closeCursor();   // vor dem Schreiben schließen (T-20, siehe nutzer())
    $db->prepare("INSERT OR REPLACE INTO meta (k, v) VALUES ('newsletter_letzte', ?)")
       ->execute([json_encode(['kw' => $kw, 'zeit' => time(), 'empfaenger' => $empfaenger])]);
    return ['gesendet' => $gesendet, 'offen' => $fehler > 0 && $gesendet === 0 ? 0 : $offen, 'fehler' => $fehler, 'kw' => $kw];
}

// ---------- Mein Bondarium: Ablage und Meldungen (seit 02.10.2026 abends) ----------

/** Wert für die Ablage säubern: Steuerzeichen aus Texten entfernen, höchstens vier Ebenen tief, nur einfache Werte */
function ablage_sauber($w, int $tiefe = 0)
{
    if (is_string($w)) {
        return trim((string)preg_replace('/[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]/u', '', $w));
    }
    if (is_int($w) || is_float($w) || is_bool($w)) {
        return $w;
    }
    if (is_array($w) && $tiefe < 4) {
        $aus = [];
        foreach ($w as $k => $v) {
            if (count($aus) >= 250) {
                break;
            }
            $aus[is_int($k) ? $k : ablage_sauber((string)$k)] = ablage_sauber($v, $tiefe + 1);
        }
        return $aus;
    }
    return '';
}

/**
 * Meldungen prüfen und verschicken (aktion=meldungen-senden, nur mit dem Schlüssel des Auslösers; der Workflow ruft nach
 * dem täglichen Datenlauf). Geprüft wird gegen newsletter/anleihen.json (Felder siehe zeile_heute(); der Name in der E-Mail ist
 * der Titel aus Feld 8). Regeln je Meldung (Ablage, Art „meldung“):
 *   rendite-ueber | rendite-unter | kurs-ueber | kurs-unter   Schwelle w zur Anleihe i. Ausgelöst wird einmal: Die Meldung
 *       trägt danach „a“ (Tag) und „aw“ (Wert) und wird erst wieder scharf, wenn die Bedingung nicht mehr gilt.
 *   termin   Zinstermin einer gemerkten Anleihe in höchstens MELDUNG_TAGE Tagen; „bis“ merkt den spätesten schon gemeldeten
 *       Tag, damit jeder Termin nur einmal kommt. Seit 03.10.2026 ohne Fälligkeiten und ohne den letzten Zinstermin am
 *       Fälligkeitstag – beides kommt über „Vor Fälligkeit“ (erinnerung.php), sonst gäbe es zwei Regeln für dieselbe Fälligkeit.
 *   kurslos   prüft die Seite beim Besuch – hier übergangen.
 * Eine E-Mail je Konto mit allen neu ausgelösten Meldungen, die „per E-Mail“ (m) gewählt haben; die anderen stehen nur im
 * Bereich. Nur Tatsachen, keine Vorschläge. Jede E-Mail trägt einen Link, der alle Meldungen auf „nur im Bereich“ stellt.
 */
function meldungen_senden(): array
{
    ausloeser_pruefen();
    $anl = nl_datei('anleihen.json');
    if ($anl === null) {
        return ['gesendet' => 0, 'ausgeloest' => 0, 'grund' => 'keine Daten'];
    }
    $db = db();
    $heute = date('Y-m-d');
    $bis = date('Y-m-d', time() + MELDUNG_TAGE * 86400);
    $s = $db->query("SELECT a.nutzer, a.schluessel, a.wert, n.email, n.erstellt FROM ablage a JOIN nutzer n ON n.id = a.nutzer WHERE a.art = 'meldung' ORDER BY a.nutzer, a.zeit");
    $je = [];
    foreach ($s->fetchAll(PDO::FETCH_ASSOC) as $z) {
        $je[(int)$z['nutzer']]['email'] = (string)$z['email'];
        $je[(int)$z['nutzer']]['erstellt'] = (int)$z['erstellt'];
        $je[(int)$z['nutzer']]['regeln'][(string)$z['schluessel']] = json_decode((string)$z['wert'], true);
    }
    $fav = $db->prepare('SELECT isin FROM favoriten WHERE nutzer = ?');
    $sichern = $db->prepare("UPDATE ablage SET wert = ? WHERE nutzer = ? AND art = 'meldung' AND schluessel = ?");
    // Titel aus anleihen.json („Deutschland 2,60 % 2033“, gebaut in scripts/newsletter.py) – derselbe Name wie im Wochenbrief und auf der Website
    $titel = fn(array $a): string => nl_text(nl_titel($a));
    $gesendet = 0;
    $ausgeloest = 0;
    $fehler = 0;
    foreach ($je as $id => $k) {
        $zeilen = [];
        foreach ($k['regeln'] as $schl => $w) {
            if (!is_array($w) || empty($w['an'])) {
                continue;
            }
            $b = (string)($w['b'] ?? '');
            $vorher = $w;
            if (in_array($b, ['rendite-ueber', 'rendite-unter', 'kurs-ueber', 'kurs-unter'], true)) {
                $a = $anl[(string)($w['i'] ?? '')] ?? null;
                if (!is_array($a) || count($a) < 7 || !is_numeric($w['w'] ?? null)) {
                    continue;
                }
                $rend = strpos($b, 'rendite') === 0;
                $v = $rend ? $a[4] : $a[3];
                if (!is_numeric($v)) {
                    continue;
                }
                $ueber = substr($b, -5) === 'ueber';
                $erfuellt = $ueber ? (float)$v > (float)$w['w'] : (float)$v < (float)$w['w'];
                if ($erfuellt && empty($w['a'])) {
                    $w['a'] = $heute;
                    $w['aw'] = round((float)$v, 2);
                    $ausgeloest++;
                    if (!empty($w['m'])) {
                        // „Deutschland 2,60 % 2033: Rendite 3,47 % – über deiner Schwelle von 3,40 %.“ – Kurs ebenso mit „%“
                        $zeilen[] = $titel($a) . ': ' . nl_text($rend ? 'Rendite ' . nl_pct((float)$v) : 'Kurs ' . nl_kurs((float)$v))
                            . ' – ' . ($ueber ? 'über' : 'unter') . ' deiner Schwelle von ' . nl_zahl((float)$w['w']) . ' %' . ".\n  " . SEITE . '/anleihe.html?isin=' . $w['i'];
                    }
                } elseif (!$erfuellt && !empty($w['a'])) {
                    unset($w['a'], $w['aw']);
                }
            } elseif ($b === 'termin') {
                $fav->execute([$id]);
                $neu = [];
                foreach ($fav->fetchAll(PDO::FETCH_COLUMN) as $isin) {
                    $a = $anl[$isin] ?? null;
                    if (!is_array($a) || count($a) < 7) {
                        continue;
                    }
                    // nächster Zinstermin; am Fälligkeitstag meldet „Vor Fälligkeit“. Seit 03.10.2026 stehen in Feld 6 auch geschätzte
                    // Termine (Feld 10 = 1, für die Merkliste) – gemeldet werden wie bisher nur Termine laut Deutscher Börse (Tatsachen).
                    $d = $a[6];
                    if (is_string($d) && empty($a[8]) && $d !== (string)$a[2] && $d > $heute && $d <= $bis && $d > (string)($w['bis'] ?? '')) {
                        $neu[] = [$d, $titel($a) . ' zahlt Zinsen am ' . nl_datum($d) . '.'];
                    }
                }
                if ($neu) {
                    sort($neu);
                    $w['bis'] = $neu[count($neu) - 1][0];
                    $w['a'] = $heute;
                    $w['aw'] = $neu[0][1];
                    $ausgeloest++;
                    if (!empty($w['m'])) {
                        foreach ($neu as $x) {
                            $zeilen[] = $x[1];
                        }
                    }
                }
            }
            if ($w !== $vorher) {
                $sichern->execute([json_encode($w, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES), $id, $schl]);
            }
        }
        if ($zeilen && $gesendet < MELDUNG_MAILS) {
            $n = count($zeilen);
            $ok = mail_senden($k['email'], $n === 1 ? 'Bondarium: eine Meldung aus deinem Bereich' : "Bondarium: $n Meldungen aus deinem Bereich",
                "du hast in „Mein Bondarium“ Meldungen eingerichtet. Nach den Schlusskursen vom letzten Börsentag gilt:\n\n- " . implode("\n- ", $zeilen)
                . "\n\nAlle Meldungen ansehen oder ändern:\n" . SEITE . "/konto.html#meldungen\n\n"
                . "Keine E-Mails mehr zu Meldungen (sie stehen dann nur noch in deinem Bereich) – ein Klick:\n" . SEITE . '/konto.html#meldungen-aus=' . link_kennung('meldungen-aus', $id, $k['erstellt']) . "\n\n"
                . 'Das sind Tatsachen aus den Kursdaten, keine Empfehlung zum Kauf oder Verkauf. Keine Anlageberatung.');
            $ok ? $gesendet++ : $fehler++;
        }
    }
    return ['gesendet' => $gesendet, 'ausgeloest' => $ausgeloest, 'konten' => count($je), 'fehler' => $fehler];
}

// ---------- Anfrage prüfen ----------
$methode = $_SERVER['REQUEST_METHOD'] ?? '';
$aktion  = $methode === 'POST' ? text($_POST, 'aktion') : text($_GET, 'aktion');

// Abmelden aus dem E-Mail-Programm (RFC 8058): POST auf konto.php?nl=<Kennung> – ohne unseren Kopf, ohne Cookie.
// Die Kennung ist der Nachweis; sie steht nur in der E-Mail des Abonnenten.
if ($methode === 'POST' && isset($_GET['nl'])) {
    try {
        nl_abbestellen(text($_GET, 'nl'));
    } catch (Throwable $e) {
        error_log('konto.php: ' . $e->getMessage());
        antwort(500, 'fehler');
    }
    antwort(200, 'ok');   // auch bei unbekannter Kennung: nichts verraten
}
// Dieselbe Adresse im Browser geöffnet (E-Mail-Programme ohne RFC 8058) oder von einer Link-Vorschau abgerufen: Der GET
// bestellt nichts ab, er leitet nur auf konto.html#nl-ab=<Kennung> um – dort bestellt das Seitenskript ab wie beim Link im Text.
if (($methode === 'GET' || $methode === 'HEAD') && isset($_GET['nl'])) {
    $k = text($_GET, 'nl');
    header('Location: ' . ursprung() . '/konto.html' . (preg_match('/^\d{1,12}\.[0-9a-f]{32}$/D', $k) ? '#nl-ab=' . $k : ''), true, 303);
    exit;
}

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
            if (text($_POST, 'website') !== '') {
                antwort(200, 'ok', ['stunden' => BESTAETIGEN_STUNDEN]);   // Honigtopf ausgefüllt: so antworten, als wäre alles gut
            }
            $mail = email_lesen();
            $pw = text($_POST, 'passwort');
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
                $nl = text($_POST, 'newsletter') === '1' ? 1 : 0;   // Häkchen im Formular – gilt erst mit dem Bestätigen
                $db->prepare("INSERT INTO links (hash, email, isin, ablauf, art, pw, newsletter) VALUES (?, ?, ?, ?, 'neu', ?, ?)")
                   ->execute([hash('sha256', $t), $mail, $isin, time() + BESTAETIGEN_STUNDEN * 3600, $pwHash, $nl]);
                // Kennwort hinter „#“: Dieser Teil der Adresse wird nicht an den Server geschickt und steht in keinem Log
                $ok = mail_senden($mail, 'Bestätige deine E-Mail-Adresse für Bondarium', "bitte bestätige deine E-Mail-Adresse, damit dein Konto bei Bondarium entsteht:\n\n"
                    . ursprung() . '/konto.html#bestaetigen=' . $t . "\n\n"
                    . 'Der Link gilt ' . BESTAETIGEN_STUNDEN . " Stunden. Auf der Seite gibst du dein Passwort noch einmal ein.\n\n"
                    . ($nl ? "Du hast den Wochenbrief angekreuzt: Mit dem Bestätigen bestellst du auch ihn – einmal pro Woche per E-Mail. Abbestellen kannst du ihn jederzeit – über den Link in jeder Ausgabe oder in „Mein Bondarium“.\n\n" : '')
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
            $pw = text($_POST, 'passwort');
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
            if ((int)$l['newsletter'] === 1) {
                nl_setzen($id, true);   // Einwilligung aus dem Formular, bestätigt durch den Link in der E-Mail
            }
            sitzung_starten($id);
            $aus = stand($id, $l['email'], ist_isin($l['isin']) ? $l['isin'] : null);
            $db->exec('COMMIT');
            antwort(200, 'ok', $aus);

        case 'anmelden':
            $mail = email_lesen();
            $pw = text($_POST, 'passwort');
            $db = db();
            aufraeumen();
            $schl = login_schluessel($mail);
            if (gebremst(LOGIN_GRENZEN, $schl)) {
                antwort(429, 'zuviel');
            }
            $s = $db->prepare('SELECT id, pw FROM nutzer WHERE email = ?');
            $s->execute([$mail]);
            $z = $s->fetch(PDO::FETCH_ASSOC);
            $s->closeCursor();   // vor dem Schreiben schließen (T-20, siehe nutzer())
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
            if (text($_POST, 'website') !== '') {
                antwort(200, 'ok', ['minuten' => RESET_MINUTEN]);
            }
            $mail = email_lesen();
            $db = db();
            aufraeumen();
            versand_zaehlen($mail);
            $s = $db->prepare('SELECT 1 FROM nutzer WHERE email = ?');
            $s->execute([$mail]);
            $da = $s->fetchColumn();
            $s->closeCursor();   // vor dem Schreiben schließen (T-20, siehe nutzer())
            if ($da) {
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
            $pw = text($_POST, 'passwort');
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
            // Eine offene Adressänderung verfällt mit dem neuen Passwort: Wer das alte kannte, hätte sonst noch 24 Stunden lang die
            // Adresse des Kontos auf seine eigene umstellen können (Technik-Test 08.10.2026, T-19)
            $db->prepare("DELETE FROM links WHERE art = 'email' AND nutzer = ?")->execute([$id]);
            $db->prepare('DELETE FROM zaehler WHERE schluessel = ?')->execute(['lm:' . schluessel_hash($l['email'])]);
            sitzung_starten($id);
            $aus = stand($id, $l['email'], null);
            $db->exec('COMMIT');
            antwort(200, 'ok', $aus);

        case 'passwort-aendern':
            $n = angemeldet();
            $alt = text($_POST, 'alt');
            $pw = text($_POST, 'passwort');
            $db = db();
            $schl = login_schluessel($n['email']);
            if (gebremst(LOGIN_GRENZEN_ANGEMELDET, $schl)) {   // ohne „lm“: fremde Fehlversuche sperren die Angemeldete nicht aus (T-24)
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
            $db->prepare("DELETE FROM links WHERE art = 'email' AND nutzer = ?")->execute([$n['id']]);   // offene Adressänderung verfällt (T-19, wie passwort-neu)
            mail_senden($n['email'], 'Dein Passwort bei Bondarium wurde geändert', "das Passwort deines Kontos bei Bondarium wurde soeben geändert. Alle anderen Geräte sind abgemeldet.\n\n"
                . "Das warst nicht du? Dann setze sofort ein neues Passwort – auf dieser Seite über „Passwort vergessen“:\n\n" . ursprung() . '/konto.html');
            antwort(200, 'ok');

        case 'merken':
        case 'entfernen':
            $n = angemeldet();
            $isin = strtoupper(trim(text($_POST, 'isin')));
            if (!ist_isin($isin)) {
                antwort(422, 'isin');
            }
            if ($aktion === 'merken') {
                if (!merke($n['id'], $isin)) {
                    antwort(409, 'voll', ['max' => MAX_FAVORITEN]);
                }
            } else {
                db()->prepare('DELETE FROM favoriten WHERE nutzer = ? AND isin = ?')->execute([$n['id'], $isin]);
                db()->prepare("UPDATE ablage SET zeit = ? WHERE nutzer = ? AND art = 'notiz' AND schluessel = ?")->execute([time(), $n['id'], $isin]);
                // Die Notiz zur Anleihe bleibt noch 30 Tage in der Ablage (aufraeumen) – „Rückgängig“ in der Merkliste bringt sie
                // so unverändert zurück. Aus eigenen Listen nimmt die Seite die Anleihe selbst heraus.
            }
            antwort(200, 'ok', konto_stand($n['id'], $n['email']));

        case 'uebernehmen':
            // Geteilte Merkliste (Link im PDF-Auszug, seit 01.10.2026): alle gültigen ISINs, die noch fehlen, bis die Merkliste voll ist
            $n = angemeldet();
            $isins = [];
            foreach (explode(',', strtoupper(text($_POST, 'isins'))) as $i) {
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
            $ein = $db->prepare('INSERT OR IGNORE INTO favoriten (nutzer, isin, seit, rendite) VALUES (?, ?, ?, ?)');
            foreach (array_keys($isins) as $i) {
                if (isset($da[$i])) {
                    continue;
                }
                if (count($da) + $neu >= MAX_FAVORITEN) {
                    $uebrig++;
                    continue;
                }
                $ein->execute([$n['id'], $i, $jetzt, rendite_heute($i)]);
                $neu++;
            }
            $db->exec('COMMIT');
            antwort(200, 'ok', konto_stand($n['id'], $n['email']) + ['neu' => $neu, 'uebrig' => $uebrig, 'max' => MAX_FAVORITEN]);

        case 'depot':
            $n = angemeldet();
            $isin = strtoupper(trim(text($_POST, 'isin')));
            if (!ist_isin($isin)) {
                antwort(422, 'isin');
            }
            $roh = trim(text($_POST, 'nennwert'));
            if (!preg_match('/^\d{1,9}$/', $roh) || (int)$roh > NENNWERT_MAX) {
                antwort(422, 'nennwert', ['max' => NENNWERT_MAX]);
            }
            $db = db();
            $db->exec('BEGIN IMMEDIATE');
            $m = muster_lesen($n['id']);
            if ((int)$roh === 0) {
                $db->prepare('DELETE FROM depot WHERE muster = ? AND isin = ?')->execute([$m, $isin]);
            } else {
                $s = $db->prepare('SELECT 1 FROM depot WHERE muster = ? AND isin = ?');
                $s->execute([$m, $isin]);
                if ($s->fetchColumn()) {
                    $db->prepare('UPDATE depot SET nennwert = ? WHERE muster = ? AND isin = ?')->execute([(int)$roh, $m, $isin]);
                } else {
                    $s = $db->prepare('SELECT COUNT(*) FROM depot WHERE muster = ?');
                    $s->execute([$m]);
                    if ((int)$s->fetchColumn() >= MAX_DEPOT) {
                        $db->exec('COMMIT');
                        antwort(409, 'voll', ['max' => MAX_DEPOT]);
                    }
                    $db->prepare('INSERT INTO depot (muster, isin, nennwert, seit) VALUES (?, ?, ?, ?)')->execute([$m, $isin, (int)$roh, time()]);
                }
            }
            $db->exec('COMMIT');
            antwort(200, 'ok', konto_stand($n['id'], $n['email']) + ['muster' => $m]);

        case 'muster-neu':
        case 'muster-uebernehmen':
            // Neues Musterdepot (Knopf „+ Neues Musterdepot“) oder ein geteiltes übernehmen (Knopf im PDF, konto.html#muster=…)
            $n = angemeldet();
            $liste = [];
            if ($aktion === 'muster-uebernehmen') {
                foreach (explode(',', strtoupper(text($_POST, 'liste'))) as $teil) {
                    $t = explode('~', trim($teil));
                    if (count($t) === 2 && ist_isin($t[0]) && preg_match('/^\d{1,9}$/', $t[1]) && (int)$t[1] >= 1 && (int)$t[1] <= NENNWERT_MAX) {
                        $liste[$t[0]] = (int)$t[1];
                    }
                    if (count($liste) >= MAX_DEPOT) {
                        break;
                    }
                }
                if (!$liste) {
                    antwort(422, 'isin');
                }
            }
            $db = db();
            $db->exec('BEGIN IMMEDIATE');
            $zahl = muster_anzahl($n['id']);
            if ($zahl >= MAX_MUSTER) {
                $db->exec('COMMIT');
                antwort(409, 'mustervoll', ['max' => MAX_MUSTER]);
            }
            $jetzt = time();
            if ($zahl === 0 && $aktion === 'muster-neu') {
                muster_erstes($n['id']);   // das bisher nur gedachte „Musterdepot 1“ zuerst anlegen, damit das neue das zweite ist
                $zahl = 1;
            }
            $name = name_lesen(text($_POST, 'name'), 'Musterdepot ' . ($zahl + 1));
            $db->prepare('INSERT INTO musterdepots (nutzer, name, erstellt) VALUES (?, ?, ?)')->execute([$n['id'], $name, $jetzt]);
            $m = (int)$db->lastInsertId();
            $ein = $db->prepare('INSERT INTO depot (muster, isin, nennwert, seit) VALUES (?, ?, ?, ?)');
            $i = 0;
            foreach ($liste as $isin => $nenn) {
                $ein->execute([$m, $isin, $nenn, $jetzt + $i++]);   // Reihenfolge wie im PDF
            }
            $db->exec('COMMIT');
            antwort(200, 'ok', konto_stand($n['id'], $n['email']) + ['muster' => $m, 'neu' => count($liste)]);

        case 'muster-name':
            $n = angemeldet();
            $db = db();
            $db->exec('BEGIN IMMEDIATE');
            $m = muster_lesen($n['id']);
            $name = name_lesen(text($_POST, 'name'), '');
            if ($name === '') {
                $db->exec('COMMIT');
                antwort(422, 'name', ['max' => NAME_MAX]);
            }
            $db->prepare('UPDATE musterdepots SET name = ? WHERE id = ?')->execute([$name, $m]);
            $db->exec('COMMIT');
            antwort(200, 'ok', konto_stand($n['id'], $n['email']) + ['muster' => $m]);

        case 'muster-weg':
            $n = angemeldet();
            $db = db();
            $db->exec('BEGIN IMMEDIATE');
            $m = muster_lesen($n['id']);
            if (muster_anzahl($n['id']) <= 1) {
                $db->exec('COMMIT');
                antwort(409, 'letztes');
            }
            $db->prepare('DELETE FROM depot WHERE muster = ?')->execute([$m]);
            $db->prepare('DELETE FROM musterdepots WHERE id = ?')->execute([$m]);
            $db->exec('COMMIT');
            antwort(200, 'ok', konto_stand($n['id'], $n['email']));

        case 'erinnern':
            // E-Mail 20 Tage vor und am Tag jeder Fälligkeit (seit 02.10.2026, Nutzerentscheid): an = 1 einschalten, 0 ausschalten
            $n = angemeldet();
            db()->prepare('UPDATE nutzer SET erinnern = ? WHERE id = ?')->execute([text($_POST, 'an') === '1' ? 1 : 0, $n['id']]);
            antwort(200, 'ok', konto_stand($n['id'], $n['email']));

        case 'erinnerung-aus':
            // Link „Ausschalten“ aus der Erinnerungs-E-Mail: „Nummer.Prüfsumme“ (link_kennung(); dieselbe Prüfsumme bildet erinnerung.php).
            // Schaltet nur aus – mehr kann der Link nicht. Ist dasselbe Konto hier angemeldet, kommt der neue Stand mit.
            $id = link_kennung_pruefen('erinnerung-aus', text($_POST, 'token'));
            if ($id === null) {
                antwort(410, 'link');
            }
            $s = db()->prepare('UPDATE nutzer SET erinnern = 0 WHERE id = ?');
            $s->execute([$id]);
            if ($s->rowCount() === 0) {
                antwort(410, 'link');
            }
            $n = nutzer();
            antwort(200, 'ok', $n !== null && $n['id'] === $id ? konto_stand($n['id'], $n['email']) : ['angemeldet' => $n !== null]);

        case 'newsletter':
            $n = angemeldet();
            $wert = text($_POST, 'wert');
            if ($wert !== '1' && $wert !== '0') {
                antwort(400, 'aktion');
            }
            nl_setzen($n['id'], $wert === '1');
            antwort(200, 'ok', konto_stand($n['id'], $n['email']));

        case 'newsletter-ab':
            // Abmelde-Link der Ausgabe (konto.html#nl-ab=…): ohne Anmeldung, die Kennung ist der Nachweis
            if (!nl_abbestellen(text($_POST, 'token'))) {
                antwort(410, 'link');
            }
            antwort(200, 'ok');

        case 'newsletter-senden':
            antwort(200, 'ok', nl_senden());

        case 'ablage':
            // Persönliche Ablage (seit 02.10.2026 abends): einen Eintrag setzen oder – mit leerem Wert – löschen. Antwort: alle
            // Einträge dieser Art, die Seite übernimmt sie in ihren Stand.
            $n = angemeldet();
            $art = text($_POST, 'art');
            $k = text($_POST, 'schluessel');
            if (!isset(ABLAGE[$art])) {
                antwort(422, 'art');
            }
            if (!ablage_schluessel($art, $k)) {
                antwort(422, 'wert');
            }
            [$max, $lang] = ABLAGE[$art];
            $roh = text($_POST, 'wert');
            $db = db();
            // „Zuletzt angesehen“ (Technik-Test 08.10.2026, T-18, Zusage der Datenschutzerklärung „schaltest du es wieder aus, löschen
            // wir sie“): Ausschalten löscht im selben Schritt alle gemerkten Seiten und Anleihen – nicht erst die Seite, Eintrag für
            // Eintrag –, und solange es aus ist, nimmt der Server keine neuen an. Eingeschaltet heißt: einstellung/zuletzt = 1 (wie bereich.js).
            $zuletzt = $art === 'einstellung' && $k === 'zuletzt';
            if ($roh === '') {
                if ($zuletzt) {
                    $db->exec('BEGIN IMMEDIATE');
                }
                $db->prepare('DELETE FROM ablage WHERE nutzer = ? AND art = ? AND schluessel = ?')->execute([$n['id'], $art, $k]);
                if ($zuletzt) {
                    $db->prepare("DELETE FROM ablage WHERE nutzer = ? AND art = 'angesehen'")->execute([$n['id']]);
                    $db->exec('COMMIT');
                }
            } else {
                $w = strlen($roh) <= 4 * $lang ? json_decode($roh, true) : null;
                if ($w === null) {
                    antwort(422, 'wert', ['max' => $lang]);
                }
                $w = ablage_sauber($w);
                if ($art === 'notiz' && is_string($w) && laenge($w) > NOTIZ_MAX) {
                    antwort(422, 'wert', ['max' => NOTIZ_MAX]);   // Zeichen statt Byte (T-109): „€“ zählt wie „e“
                }
                $json = json_encode($w, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
                if (!is_string($json) || strlen($json) > $lang) {
                    antwort(422, 'wert', ['max' => $lang]);
                }
                $db->exec('BEGIN IMMEDIATE');
                if ($art === 'angesehen') {
                    $s = $db->prepare("SELECT 1 FROM ablage WHERE nutzer = ? AND art = 'einstellung' AND schluessel = 'zuletzt' AND wert = '1'");
                    $s->execute([$n['id']]);
                    $an = $s->fetchColumn();
                    $s->closeCursor();
                    if (!$an) {
                        $db->exec('COMMIT');
                        antwort(409, 'aus');   // „Zuletzt angesehen“ ist ausgeschaltet – mein.js fängt das still ab
                    }
                }
                if ($zuletzt && $json !== '1') {
                    $db->prepare("DELETE FROM ablage WHERE nutzer = ? AND art = 'angesehen'")->execute([$n['id']]);   // jeder andere Wert heißt „aus“
                }
                $s = $db->prepare('SELECT 1 FROM ablage WHERE nutzer = ? AND art = ? AND schluessel = ?');
                $s->execute([$n['id'], $art, $k]);
                if ($s->fetchColumn()) {
                    // Meldungen, Listen und Notizen behalten ihren Platz in der Reihenfolge; alles andere rückt nach vorn
                    $zeit = in_array($art, ['meldung', 'liste', 'notiz'], true) ? '' : ', zeit = ' . time();
                    $db->prepare("UPDATE ablage SET wert = ?$zeit WHERE nutzer = ? AND art = ? AND schluessel = ?")->execute([$json, $n['id'], $art, $k]);
                } else {
                    $s = $db->prepare('SELECT COUNT(*) FROM ablage WHERE nutzer = ? AND art = ?');
                    $s->execute([$n['id'], $art]);
                    if ((int)$s->fetchColumn() >= $max) {
                        if ($art !== 'angesehen') {
                            $db->exec('COMMIT');
                            antwort(409, 'voll', ['max' => $max]);
                        }
                        // „Zuletzt angesehen“: der älteste Eintrag macht Platz
                        $db->prepare("DELETE FROM ablage WHERE nutzer = ? AND art = 'angesehen' AND schluessel = (SELECT schluessel FROM ablage WHERE nutzer = ? AND art = 'angesehen' ORDER BY zeit, schluessel LIMIT 1)")
                           ->execute([$n['id'], $n['id']]);
                    }
                    $db->prepare('INSERT INTO ablage (nutzer, art, schluessel, wert, zeit) VALUES (?, ?, ?, ?, ?)')->execute([$n['id'], $art, $k, $json, time()]);
                }
                $db->exec('COMMIT');
            }
            antwort(200, 'ok', ['art' => $art, 'eintraege' => (object)ablage($n['id'], $art)]);

        case 'besuch':
            // „Seit deinem letzten Besuch“: konto.html ruft das einmal je Seitenaufruf. Nach BESUCH_PAUSE ohne Aufruf beginnt ein
            // neuer Besuch – der Beginn des vorigen bleibt als besuch_vor stehen. Dazu die Seiten, die neu auf der Website sind
            // (newsletter/seiten.json aus dem Datenlauf: Datei → erster Tag).
            $n = angemeldet();
            $db = db();
            $jetzt = time();
            $db->prepare('UPDATE nutzer SET besuch_vor = besuch, besuch = ? WHERE id = ? AND besuch < ?')->execute([$jetzt, $n['id'], $jetzt - BESUCH_PAUSE]);
            $neu = [];
            foreach ((array)((nl_datei('seiten.json') ?? [])['seiten'] ?? []) as $datei => $tag) {
                if (is_string($tag) && $tag !== '') {
                    $neu[(string)$datei] = $tag;
                }
            }
            // Nächster Zinstermin je gemerkter Anleihe (aus dem Datenlauf) – die Merkliste zeigt ihn, ohne je Anleihe eine Datei zu laden.
            // termine: ISIN → JJJJ-MM-TT; seit 03.10.2026 auch geschätzte Termine (Börsenliste ohne Zinstage), die zusätzlich in
            // termine_geschaetzt stehen (ISIN → 1, nur diese) – dieselbe Quelle wie Wochenbrief und Meldungen (scripts/newsletter.py).
            $st = konto_stand($n['id'], $n['email']);
            $termine = [];
            $geschaetzt = [];
            foreach ($st['favoriten'] as $f) {
                $z = zeile_heute($f[0]);
                if ($z !== null && is_string($z[6]) && $z[6] !== '') {
                    $termine[$f[0]] = $z[6];
                    if (!empty($z[8])) {
                        $geschaetzt[$f[0]] = 1;
                    }
                }
            }
            antwort(200, 'ok', $st + ['neue_seiten' => (object)$neu, 'termine' => (object)$termine, 'termine_geschaetzt' => (object)$geschaetzt]);

        case 'geraete-ab':
            $n = angemeldet();
            db()->prepare('DELETE FROM sitzungen WHERE nutzer = ? AND hash <> ?')->execute([$n['id'], hash('sha256', (string)$_COOKIE[COOKIE])]);
            antwort(200, 'ok', konto_stand($n['id'], $n['email']));

        case 'export':
            // „Meine Daten herunterladen“: alles, was zu diesem Konto gespeichert ist – ohne Passwort-Hashwert und Cookies. Seit
            // 09.10.2026 vollständig (Technik-Test 08.10.2026, T-105): auch die verschickten Erinnerungen vor Fälligkeit, eine offene
            // Adressänderung, die zuletzt erhaltene Wochenbrief-Ausgabe und der Beginn des laufenden Besuchs
            $n = angemeldet();
            $db = db();
            $s = $db->prepare('SELECT erstellt, zuletzt, newsletter_seit, newsletter_kw, besuch FROM nutzer WHERE id = ?');
            $s->execute([$n['id']]);
            $z = $s->fetch(PDO::FETCH_NUM) ?: [0, 0, null, '', 0];
            $s->closeCursor();
            // [ISIN, Fälligkeit, welche E-Mail („vorher“: 20 Tage vorher, „am Tag“: am Fälligkeitstag; erinnerung.php), verschickt am]
            $s = $db->prepare('SELECT isin, faellig, gesendet FROM erinnert WHERE nutzer = ? ORDER BY faellig, isin');
            $s->execute([$n['id']]);
            $erinnerungen = [];
            foreach ($s->fetchAll(PDO::FETCH_NUM) as [$isin, $faellig, $gesendet]) {
                $erinnerungen[] = [(string)$isin, substr((string)$faellig, 0, 10), substr((string)$faellig, -4) === '#tag' ? 'am Tag' : 'vorher', date('c', (int)$gesendet)];
            }
            $s = $db->prepare("SELECT email, ablauf FROM links WHERE art = 'email' AND nutzer = ? AND ablauf > ? ORDER BY ablauf DESC LIMIT 1");
            $s->execute([$n['id'], time()]);
            $l = $s->fetch(PDO::FETCH_NUM);
            $s->closeCursor();
            $st = konto_stand($n['id'], $n['email']);
            unset($st['angemeldet'], $st['depot']);
            antwort(200, 'ok', ['daten' => ['erstellt_am' => date('c'), 'konto_angelegt' => date('c', (int)$z[0]), 'zuletzt_angemeldet' => date('c', (int)$z[1]),
                'wochenbrief_seit' => $z[2] === null ? null : date('c', (int)$z[2]),
                'wochenbrief_letzte_ausgabe' => (string)$z[3] !== '' ? (string)$z[3] : null,
                'besuch_beginn' => (int)$z[4] > 0 ? date('c', (int)$z[4]) : null,
                'erinnerungen' => $erinnerungen,
                'offene_adressaenderung' => $l ? ['email' => (string)$l[0], 'gueltig_bis' => date('c', (int)$l[1])] : null] + $st]);

        case 'email-aendern':
            // Neue E-Mail-Adresse: Passwort zur Bestätigung, dann ein Link an die NEUE Adresse – erst der Klick stellt um
            $n = angemeldet();
            $neu = email_lesen();
            $db = db();
            $schl = login_schluessel($n['email']);
            if (gebremst(LOGIN_GRENZEN_ANGEMELDET, $schl)) {   // ohne „lm“ (T-24, siehe passwort-aendern)
                antwort(429, 'zuviel');
            }
            if (!pw_stimmt(text($_POST, 'passwort'), $n['pw'])) {
                zaehle($schl);
                antwort(403, 'zugang');
            }
            if ($neu === $n['email']) {
                antwort(422, 'gleich');
            }
            aufraeumen();
            versand_zaehlen($neu);
            $s = $db->prepare('SELECT 1 FROM nutzer WHERE email = ?');
            $s->execute([$neu]);
            if ($s->fetchColumn()) {
                // Die Seite antwortet gleich – ob es zu der Adresse schon ein Konto gibt, erfährt nur ihr Inhaber
                $ok = mail_senden($neu, 'Dein Konto bei Bondarium', "jemand wollte die E-Mail-Adresse seines Kontos bei Bondarium auf diese Adresse ändern. Für diese Adresse gibt es aber schon ein Konto – es ändert sich nichts.\n\n"
                    . 'Das warst du selbst? Dann melde dich mit dieser Adresse an oder lösche eines der beiden Konten: ' . ursprung() . '/konto.html');
            } else {
                $t = kennwort();
                $db->prepare("DELETE FROM links WHERE art = 'email' AND nutzer = ?")->execute([$n['id']]);
                $db->prepare("INSERT INTO links (hash, email, ablauf, art, nutzer) VALUES (?, ?, ?, 'email', ?)")
                   ->execute([hash('sha256', $t), $neu, time() + BESTAETIGEN_STUNDEN * 3600, $n['id']]);
                $ok = mail_senden($neu, 'Bestätige deine neue E-Mail-Adresse für Bondarium', "mit diesem Link wird diese Adresse die E-Mail-Adresse deines Kontos bei Bondarium:\n\n"
                    . ursprung() . '/konto.html#email=' . $t . "\n\n"
                    . 'Der Link gilt ' . BESTAETIGEN_STUNDEN . " Stunden. Bis dahin bleibt die bisherige Adresse gültig.\n\n"
                    . 'Du hast das nicht angefordert? Dann musst du nichts tun – ohne den Klick ändert sich nichts.');
                if (!$ok) {
                    $db->prepare('DELETE FROM links WHERE hash = ?')->execute([hash('sha256', $t)]);
                }
            }
            if (!$ok) {
                antwort(500, 'versand');
            }
            antwort(200, 'ok', ['stunden' => BESTAETIGEN_STUNDEN]);

        case 'email-bestaetigen':
            // Link aus der E-Mail an die neue Adresse (konto.html#email=…): stellt das Konto um. Ohne Anmeldung – der Link ist
            // der Nachweis, angefordert wurde er angemeldet und mit Passwort. Andere Geräte werden abgemeldet.
            $l = link_lesen('email');
            $db = db();
            $db->exec('BEGIN IMMEDIATE');
            $db->prepare('DELETE FROM links WHERE hash = ?')->execute([$l['hash']]);
            $s = $db->prepare('SELECT email FROM nutzer WHERE id = ?');
            $s->execute([(int)$l['nutzer']]);
            $alt = $s->fetchColumn();
            $s = $db->prepare('SELECT 1 FROM nutzer WHERE email = ?');
            $s->execute([$l['email']]);
            if (!is_string($alt) || $s->fetchColumn()) {
                $db->exec('COMMIT');
                antwort(410, 'link');   // Konto gelöscht oder die Adresse inzwischen vergeben
            }
            $id = (int)$l['nutzer'];
            $db->prepare('UPDATE nutzer SET email = ? WHERE id = ?')->execute([$l['email'], $id]);
            $db->prepare('DELETE FROM links WHERE email = ?')->execute([$alt]);
            $hier = $_COOKIE[COOKIE] ?? '';
            $db->prepare('DELETE FROM sitzungen WHERE nutzer = ? AND hash <> ?')->execute([$id, ist_kennwort($hier) ? hash('sha256', $hier) : '']);
            $db->exec('COMMIT');
            $teile = explode('@', (string)$l['email']);
            mail_senden($alt, 'Die E-Mail-Adresse deines Kontos bei Bondarium wurde geändert', 'die E-Mail-Adresse deines Kontos bei Bondarium wurde soeben geändert – auf ' . substr($teile[0], 0, 2) . '…@' . ($teile[1] ?? '')
                . ". Anmelden kannst du dich ab jetzt nur noch mit der neuen Adresse; alle anderen Geräte sind abgemeldet.\n\n"
                . 'Das warst nicht du? Dann antworte bitte sofort auf diese E-Mail.');
            $n = nutzer();
            antwort(200, 'ok', $n !== null && $n['id'] === $id ? konto_stand($id, (string)$l['email']) : ['angemeldet' => $n !== null, 'neu' => (string)$l['email']]);

        case 'meldungen-senden':
            antwort(200, 'ok', meldungen_senden());

        case 'meldungen-aus':
            // Link aus einer Meldungs-E-Mail: alle Meldungen des Kontos auf „nur im Bereich“ – ein Klick, ohne Anmeldung.
            // Passt die Kennung zu keinem Konto (gelöscht, Nummer neu vergeben), 410 wie die anderen Ein-Klick-Links (T-103).
            $id = link_kennung_pruefen('meldungen-aus', text($_POST, 'token'));
            if ($id === null) {
                antwort(410, 'link');
            }
            $db = db();
            $s = $db->prepare("SELECT schluessel, wert FROM ablage WHERE nutzer = ? AND art = 'meldung'");
            $s->execute([$id]);
            $sichern = $db->prepare("UPDATE ablage SET wert = ? WHERE nutzer = ? AND art = 'meldung' AND schluessel = ?");
            foreach ($s->fetchAll(PDO::FETCH_NUM) as $z) {
                $w = json_decode((string)$z[1], true);
                if (is_array($w) && !empty($w['m'])) {
                    $w['m'] = 0;
                    $sichern->execute([json_encode($w, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES), $id, (string)$z[0]]);
                }
            }
            antwort(200, 'ok');

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
                if (gebremst(LOGIN_GRENZEN_ANGEMELDET, $schl)) {   // ohne „lm“ (T-24, siehe passwort-aendern)
                    antwort(429, 'zuviel');
                }
                if (!pw_stimmt(text($_POST, 'passwort'), $n['pw'])) {
                    zaehle($schl);
                    antwort(403, 'zugang');
                }
            }
            nl_setzen($n['id'], false);   // zählt als Abmeldung vom Newsletter, falls bestellt
            $db->exec('BEGIN IMMEDIATE');
            $db->prepare('DELETE FROM favoriten WHERE nutzer = ?')->execute([$n['id']]);
            $db->prepare('DELETE FROM depot WHERE muster IN (SELECT id FROM musterdepots WHERE nutzer = ?)')->execute([$n['id']]);
            $db->prepare('DELETE FROM musterdepots WHERE nutzer = ?')->execute([$n['id']]);
            $db->prepare('DELETE FROM erinnert WHERE nutzer = ?')->execute([$n['id']]);
            $db->prepare('DELETE FROM ablage WHERE nutzer = ?')->execute([$n['id']]);
            $db->prepare('DELETE FROM sitzungen WHERE nutzer = ?')->execute([$n['id']]);
            $db->prepare('DELETE FROM links WHERE email = ? OR nutzer = ?')->execute([$n['email'], $n['id']]);
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
