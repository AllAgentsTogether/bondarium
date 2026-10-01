<?php
/**
 * Täglicher Besucherbericht (seit 01.10.2026, docs/STATISTIK.md): liest die Tageswerte von aufruf.php, zeichnet daraus
 * ein PDF (A4, eine Seite, Gestaltung wie der Depot-Auszug: Helvetica, grünes Band mit Logo) und schickt es per E-Mail
 * an BERICHT_AN. Wird nur von aufruf.php geladen; direkt aufgerufen antwortet die Datei mit 404 (zusätzlich per
 * .htaccess gesperrt).
 *
 * Teile: Pdf – kleiner PDF-Schreiber, PHP-Fassung von pdf.js (gleiche Maße: Punkt, Ursprung oben links, Farben 0–1
 * oder „#RRGGBB“, Helvetica in WinAnsi) · bericht_pdf() – die Seite · bericht_daten() – Zahlen aus der Datenbank ·
 * bericht_senden() – E-Mail mit Anhang (lokal: Dateien in statistik-daten/).
 */
declare(strict_types=1);

if (realpath($_SERVER['SCRIPT_FILENAME'] ?? '') === __FILE__) { http_response_code(404); exit; }

// Wortmarke „bondarium“ aus der Kopfzeile der Website (index.html, .brand-w, viewBox 0 330 5362 780)
const BERICHT_WORTMARKE = 'M398 1108Q331 1108 280.0 1079.5Q229 1051 200.0 996.0Q171 941 168 863H189V1090H79V360H218V725L181 782Q185 698 214.5 642.0Q244 586 294.0 558.0Q344 530 407 530Q463 530 509.0 551.0Q555 572 588.0 609.5Q621 647 638.5 697.0Q656 747 656 806V827Q656 886 638.0 937.0Q620 988 586.0 1026.5Q552 1065 504.5 1086.5Q457 1108 398 1108ZM367 991Q412 991 445.5 968.5Q479 946 498.0 907.0Q517 868 517 817Q517 765 498.0 727.0Q479 689 445.5 668.0Q412 647 367 647Q326 647 291.5 665.0Q257 683 235.5 718.0Q214 753 214 802V842Q214 889 236.0 922.0Q258 955 293.0 973.0Q328 991 367 991Z M1009 1109Q937 1109 882.0 1086.0Q827 1063 789.0 1023.5Q751 984 731.5 934.0Q712 884 712 830V809Q712 753 732.5 702.5Q753 652 791.5 612.5Q830 573 885.0 550.5Q940 528 1009 528Q1078 528 1133.0 550.5Q1188 573 1226.5 612.5Q1265 652 1285.0 702.5Q1305 753 1305 809V830Q1305 884 1285.5 934.0Q1266 984 1228.0 1023.5Q1190 1063 1135.0 1086.0Q1080 1109 1009 1109ZM1009 990Q1060 990 1095.0 967.5Q1130 945 1148.0 906.5Q1166 868 1166 819Q1166 769 1147.5 730.5Q1129 692 1093.5 669.5Q1058 647 1009 647Q960 647 924.5 669.5Q889 692 870.0 730.5Q851 769 851 819Q851 868 869.5 906.5Q888 945 923.0 967.5Q958 990 1009 990Z M1397 1090V547H1507V780H1497Q1497 697 1519.0 641.5Q1541 586 1584.5 558.0Q1628 530 1693 530H1699Q1796 530 1846.0 592.5Q1896 655 1896 779V1090H1757V767Q1757 717 1728.5 686.0Q1700 655 1650 655Q1599 655 1567.5 686.5Q1536 718 1536 771V1090Z M2240 1108Q2183 1108 2135.0 1087.0Q2087 1066 2052.0 1028.0Q2017 990 1998.0 939.5Q1979 889 1979 830V809Q1979 751 1997.5 700.0Q2016 649 2049.5 611.0Q2083 573 2130.5 551.5Q2178 530 2236 530Q2300 530 2348.5 557.5Q2397 585 2426.0 640.0Q2455 695 2458 778L2417 730V360H2556V1090H2446V859H2470Q2467 942 2436.0 997.5Q2405 1053 2354.5 1080.5Q2304 1108 2240 1108ZM2271 991Q2312 991 2346.0 972.5Q2380 954 2400.5 918.5Q2421 883 2421 835V795Q2421 747 2400.0 714.5Q2379 682 2345.0 664.5Q2311 647 2271 647Q2226 647 2191.5 668.5Q2157 690 2137.5 729.0Q2118 768 2118 820Q2118 872 2138.0 910.5Q2158 949 2192.5 970.0Q2227 991 2271 991Z M3013 1090V929H2990V750Q2990 703 2967.0 680.0Q2944 657 2896 657Q2871 657 2836.0 658.0Q2801 659 2765.5 660.5Q2730 662 2702 664V546Q2725 544 2754.0 542.0Q2783 540 2813.5 539.5Q2844 539 2871 539Q2955 539 3010.5 561.0Q3066 583 3094.5 630.0Q3123 677 3123 753V1090ZM2838 1104Q2779 1104 2734.5 1083.0Q2690 1062 2665.5 1023.0Q2641 984 2641 929Q2641 869 2670.5 831.0Q2700 793 2753.5 774.0Q2807 755 2879 755H3005V838H2877Q2829 838 2803.5 861.5Q2778 885 2778 922Q2778 959 2803.5 982.0Q2829 1005 2877 1005Q2906 1005 2930.5 994.5Q2955 984 2971.5 958.5Q2988 933 2990 889L3024 928Q3019 985 2996.5 1024.0Q2974 1063 2934.5 1083.5Q2895 1104 2838 1104Z M3242 1090V547H3352V777H3349Q3349 660 3399.0 600.0Q3449 540 3546 540H3566V661H3528Q3458 661 3419.5 698.5Q3381 736 3381 807V1090Z M3655 1090V547H3794V1090ZM3579 651V547H3794V651Z M4109 1107Q4015 1107 3963.5 1045.0Q3912 983 3912 861V546H4051V873Q4051 923 4079.0 952.5Q4107 982 4155 982Q4203 982 4233.5 951.0Q4264 920 4264 867V546H4403V1090H4293V859H4304Q4304 941 4283.0 996.0Q4262 1051 4220.0 1079.0Q4178 1107 4115 1107Z M4533 1090V547H4643V780H4633Q4633 698 4654.0 642.5Q4675 587 4716.5 558.5Q4758 530 4820 530H4826Q4889 530 4930.5 558.5Q4972 587 4992.5 642.5Q5013 698 5013 780H4978Q4978 698 4999.5 642.5Q5021 587 5062.5 558.5Q5104 530 5166 530H5172Q5235 530 5277.0 558.5Q5319 587 5340.5 642.5Q5362 698 5362 780V1090H5223V767Q5223 716 5197.0 685.5Q5171 655 5123 655Q5075 655 5046.0 686.5Q5017 718 5017 771V1090H4878V767Q4878 716 4852.0 685.5Q4826 655 4778 655Q4730 655 4701.0 686.5Q4672 718 4672 771V1090Z';
final class Pdf {
    public float $B; public float $H;
    private array $seiten = []; private ?int $akt = null;
    private static array $W = [];
    private const WIN = [8364 => 128, 8218 => 130, 402 => 131, 8222 => 132, 8230 => 133, 8224 => 134, 8225 => 135, 710 => 136,
        8240 => 137, 352 => 138, 8249 => 139, 338 => 140, 381 => 142, 8216 => 145, 8217 => 146, 8220 => 147, 8221 => 148,
        8226 => 149, 8211 => 150, 8212 => 151, 732 => 152, 8482 => 153, 353 => 154, 8250 => 155, 339 => 156, 382 => 158,
        376 => 159, 8722 => 45, 8201 => 32, 8239 => 32, 160 => 32];

    public function __construct(bool $quer = false) {
        $this->B = $quer ? 841.89 : 595.28; $this->H = $quer ? 595.28 : 841.89;
        if (!self::$W) {
            self::$W['F1'] = self::breiten("278 278 355 556 556 889 667 191 333 333 389 584 278 333 278 278 556*10 278 278 584 584 584 556 1015 " .
              "667 667 722 722 667 611 778 722 278 500 667 556 833 722 778 667 778 722 667 611 722 667 944 667 667 611 278 278 278 469 556 333 " .
              "556 556 500 556 556 278 556 556 222 222 500 222 833 556 556 556 556 333 500 278 556 500 722 500 500 500 334 260 334 584 350 " .
              "556 350 222 556 333 1000 556 556 333 1000 667 333 1000 350 611 350 350 222 222 333 333 350 556 1000 333 1000 500 333 944 350 500 667 " .
              "278 333 556 556 556 556 260 556 333 737 370 556 584 333 737 333 400 584 333 333 333 556 537 278 333 333 365 556 834 834 834 611 " .
              "667*6 1000 722 667*4 278*4 722 722 778*5 584 778 722*4 667 667 611 556*6 889 500 556*4 278*4 556 556 556*5 584 611 556*4 500 556 500");
            self::$W['F2'] = self::breiten("278 333 474 556 556 889 722 238 333 333 389 584 278 333 278 278 556*10 333 333 584 584 584 611 975 " .
              "722 722 722 722 667 611 778 722 278 556 722 611 833 722 778 667 778 722 667 611 722 667 944 667 667 611 333 278 333 584 556 333 " .
              "556 611 556 611 556 333 611 611 278 278 556 278 889 611 611 611 611 389 556 333 611 556 778 556 556 500 389 280 389 584 350 " .
              "556 350 278 556 500 1000 556 556 333 1000 667 333 1000 350 611 350 350 278 278 500 500 350 556 1000 333 1000 556 333 944 350 500 667 " .
              "278 333 556 556 556 556 280 556 333 737 370 556 584 333 737 333 400 584 333 333 333 611 556 278 333 333 365 556 834 834 834 611 " .
              "722*6 1000 722 667*4 278*4 722 722 778*5 584 778 722*4 667 667 611 556*6 889 556 556*4 278*4 611 611 611*5 584 611 611*4 556 611 556");
        }
    }
    private static function breiten(string $s): array {
        $aus = [];
        foreach (explode(' ', $s) as $t) { $m = explode('*', $t); $n = isset($m[1]) ? (int)$m[1] : 1; for ($i = 0; $i < $n; $i++) $aus[] = (int)$m[0]; }
        return $aus;
    }
    private static function codes(?string $s): array {
        $aus = [];
        foreach (preg_split('//u', (string)$s, -1, PREG_SPLIT_NO_EMPTY) as $ch) {
            $c = mb_ord($ch, 'UTF-8');
            if (isset(self::WIN[$c])) $aus[] = self::WIN[$c];
            elseif (($c >= 32 && $c < 127) || ($c >= 160 && $c <= 255)) $aus[] = $c;
            else { $z = @iconv('UTF-8', 'ASCII//TRANSLIT', $ch); $aus[] = ($z !== false && $z !== '' && ord($z[0]) >= 32 && ord($z[0]) < 127 && $z[0] !== '?') ? ord($z[0]) : 63; }
        }
        return $aus;
    }
    private static function zahl(float $v): string { $r = round($v, 2); return $r == (int)$r ? (string)(int)$r : rtrim(rtrim(sprintf('%.2f', $r), '0'), '.'); }
    private static function fein(float $v): string { return rtrim(rtrim(sprintf('%.6f', $v), '0'), '.'); }
    private static function rgb($f): array {
        if (is_string($f)) { $n = hexdec(substr($f, 1)); return [($n >> 16 & 255) / 255, ($n >> 8 & 255) / 255, ($n & 255) / 255]; }
        return $f;
    }
    private static function farbe($f, string $op): string { $f = self::rgb($f); return self::zahl($f[0]) . ' ' . self::zahl($f[1]) . ' ' . self::zahl($f[2]) . ' ' . $op; }
    private static function pdfText(?string $s): string {
        $o = '';
        foreach (self::codes($s) as $c) $o .= ($c === 40 || $c === 41 || $c === 92 ? '\\' : '') . chr($c);
        return '(' . $o . ')';
    }
    private function y(float $v): string { return self::zahl($this->H - $v); }

    public function weite(?string $s, float $gr = 10, bool $fett = false): float {
        $w = self::$W[$fett ? 'F2' : 'F1']; $sum = 0;
        foreach (self::codes($s) as $c) $sum += $w[$c - 32] ?? 556;
        return $sum * $gr / 1000;
    }
    public function kuerzen(?string $s, float $max, float $gr = 10, bool $fett = false): string {
        $s = (string)$s;
        if (!$max || $this->weite($s, $gr, $fett) <= $max) return $s;
        $z = preg_split('//u', $s, -1, PREG_SPLIT_NO_EMPTY);
        while ($z && $this->weite(implode('', $z) . '…', $gr, $fett) > $max) array_pop($z);
        return preg_replace('/[\s,.;:·–-]+$/u', '', implode('', $z)) . '…';
    }
    public function umbrechen(string $s, float $max, float $gr = 10, bool $fett = false): array {
        $zeilen = []; $zeile = '';
        foreach (preg_split('/\s+/u', $s) as $wort) {
            $neu = $zeile !== '' ? $zeile . ' ' . $wort : $wort;
            if ($zeile !== '' && $this->weite($neu, $gr, $fett) > $max) { $zeilen[] = $zeile; $zeile = $wort; } else $zeile = $neu;
        }
        if ($zeile !== '') $zeilen[] = $zeile;
        return $zeilen;
    }

    public function seite(): int { $this->seiten[] = ['inhalt' => [], 'links' => []]; $this->akt = count($this->seiten) - 1; return $this->akt; }
    public function auf(int $n): void { $this->akt = $n; }
    public function anzahl(): int { return count($this->seiten); }
    private function zu(string $s): void { $this->seiten[$this->akt]['inhalt'][] = $s; }

    /** o: gr, fett, farbe, rechts (x = rechter Rand), mitte (x = Mitte), max */
    public function text(float $x, float $y, ?string $s, array $o = []): float {
        $gr = $o['gr'] ?? 10; $fett = !empty($o['fett']);
        $t = !empty($o['max']) ? $this->kuerzen($s, $o['max'], $gr, $fett) : (string)$s; $w = $this->weite($t, $gr, $fett);
        if (!empty($o['rechts'])) $x -= $w; elseif (!empty($o['mitte'])) $x -= $w / 2;
        $this->zu('BT /' . ($fett ? 'F2' : 'F1') . ' ' . self::zahl($gr) . ' Tf ' . self::farbe($o['farbe'] ?? [0.102, 0.102, 0.098], 'rg') .
            ' ' . self::zahl($x) . ' ' . $this->y($y) . ' Td ' . self::pdfText($t) . ' Tj ET');
        return $w;
    }
    private function rundPfad(float $x, float $yy, float $b, float $h, float $r): string {
        $r = min($r, $b / 2, $h / 2); $k = $r * 0.5523; $x2 = $x + $b; $y2 = $yy + $h; $z = fn($v) => self::zahl($v); $y = fn($v) => $this->y($v);
        return implode(' ', [$z($x + $r) . ' ' . $y($yy) . ' m', $z($x2 - $r) . ' ' . $y($yy) . ' l',
            $z($x2 - $r + $k) . ' ' . $y($yy) . ' ' . $z($x2) . ' ' . $y($yy + $r - $k) . ' ' . $z($x2) . ' ' . $y($yy + $r) . ' c',
            $z($x2) . ' ' . $y($y2 - $r) . ' l',
            $z($x2) . ' ' . $y($y2 - $r + $k) . ' ' . $z($x2 - $r + $k) . ' ' . $y($y2) . ' ' . $z($x2 - $r) . ' ' . $y($y2) . ' c',
            $z($x + $r) . ' ' . $y($y2) . ' l',
            $z($x + $r - $k) . ' ' . $y($y2) . ' ' . $z($x) . ' ' . $y($y2 - $r + $k) . ' ' . $z($x) . ' ' . $y($y2 - $r) . ' c',
            $z($x) . ' ' . $y($yy + $r) . ' l',
            $z($x) . ' ' . $y($yy + $r - $k) . ' ' . $z($x + $r - $k) . ' ' . $y($yy) . ' ' . $z($x + $r) . ' ' . $y($yy) . ' c h']);
    }
    public function rechteck(float $x, float $y, float $b, float $h, $f, float $radius = 0, $rand = null, float $staerke = 0.75): void {
        $pfad = $radius ? $this->rundPfad($x, $y, $b, $h, $radius) : self::zahl($x) . ' ' . $this->y($y + $h) . ' ' . self::zahl($b) . ' ' . self::zahl($h) . ' re';
        if ($f && $rand) $this->zu(self::farbe($f, 'rg') . ' ' . self::farbe($rand, 'RG') . ' ' . self::zahl($staerke) . ' w ' . $pfad . ' B');
        elseif ($f) $this->zu(self::farbe($f, 'rg') . ' ' . $pfad . ' f');
        elseif ($rand) $this->zu(self::farbe($rand, 'RG') . ' ' . self::zahl($staerke) . ' w ' . $pfad . ' S');
    }
    public function kreis(float $x, float $y, float $r, $f): void { $this->rechteck($x - $r, $y - $r, 2 * $r, 2 * $r, $f, $r); }
    public function linie(float $x1, float $y1, float $x2, float $y2, $f = [0.8, 0.8, 0.78], float $st = 0.5): void {
        $this->zu('0 J ' . self::farbe($f, 'RG') . ' ' . self::zahl($st) . ' w ' . self::zahl($x1) . ' ' . $this->y($y1) . ' m ' . self::zahl($x2) . ' ' . $this->y($y2) . ' l S');
    }
    /** Linienzug durch Punkte [[x, y], …] */
    public function zug(array $pkt, $f, float $st = 1): void {
        $s = '1 J 1 j ' . self::farbe($f, 'RG') . ' ' . self::zahl($st) . ' w';
        foreach ($pkt as $i => [$x, $y]) $s .= ' ' . self::zahl($x) . ' ' . $this->y($y) . ($i ? ' l' : ' m');
        $this->zu($s . ' S');
    }
    private static function svgPfad(string $d): string {
        preg_match_all('/[MLHVQCZ]|-?\d*\.?\d+(?:e-?\d+)?/i', $d, $m); $t = $m[0]; $i = 0; $out = []; $cx = $cy = $sx = $sy = 0; $cmd = '';
        $n = function () use (&$t, &$i) { return (float)$t[$i++]; }; $z = fn($v) => self::zahl($v);
        while ($i < count($t)) {
            if (ctype_alpha($t[$i])) $cmd = $t[$i++];
            switch ($cmd) {
                case 'M': $cx = $sx = $n(); $cy = $sy = $n(); $out[] = $z($cx) . ' ' . $z($cy) . ' m'; $cmd = 'L'; break;
                case 'L': $cx = $n(); $cy = $n(); $out[] = $z($cx) . ' ' . $z($cy) . ' l'; break;
                case 'H': $cx = $n(); $out[] = $z($cx) . ' ' . $z($cy) . ' l'; break;
                case 'V': $cy = $n(); $out[] = $z($cx) . ' ' . $z($cy) . ' l'; break;
                case 'C': $a = [$n(), $n(), $n(), $n(), $n(), $n()]; $out[] = implode(' ', array_map($z, $a)) . ' c'; $cx = $a[4]; $cy = $a[5]; break;
                case 'Q': $qx = $n(); $qy = $n(); $ex = $n(); $ey = $n();
                    $out[] = implode(' ', array_map($z, [$cx + 2 / 3 * ($qx - $cx), $cy + 2 / 3 * ($qy - $cy), $ex + 2 / 3 * ($qx - $ex), $ey + 2 / 3 * ($qy - $ey), $ex, $ey])) . ' c';
                    $cx = $ex; $cy = $ey; break;
                case 'Z': case 'z': $out[] = 'h'; $cx = $sx; $cy = $sy; if ($i < count($t) && !ctype_alpha($t[$i])) $i++; break;
                default: $i++;
            }
        }
        return implode(' ', $out);
    }
    public function svg(string $d, float $x, float $y, float $m, $f, array $o = []): void {
        $mat = 'q ' . self::fein($m) . ' 0 0 ' . self::fein(-$m) . ' ' . self::zahl($x) . ' ' . $this->y($y) . ' cm ';
        $this->zu($mat . (!empty($o['strich']) ? '1 J 1 j ' . self::farbe($f, 'RG') . ' ' . self::zahl($o['strich']) . ' w ' . self::svgPfad($d) . ' S'
            : self::farbe($f, 'rg') . ' ' . self::svgPfad($d) . ' f') . ' Q');
    }
    public function link(float $x, float $y, float $b, float $h, string $url): void { $this->seiten[$this->akt]['links'][] = [$x, $y, $b, $h, $url]; }

    /** fertiges PDF als Bytes */
    public function bytes(string $titel = 'Bondarium'): string {
        $obj = []; $kids = []; $n = 6;
        $obj[3] = '<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>';
        $obj[4] = '<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>';
        $obj[5] = '<< /Title ' . self::pdfText($titel) . ' /Producer (Bondarium) /CreationDate (D:' . date('YmdHis') . ') >>';
        foreach ($this->seiten as $s) {
            $seite = $n++; $inhalt = $n++; $annots = [];
            foreach ($s['links'] as $l) {
                $annots[] = $n;
                $obj[$n++] = '<< /Type /Annot /Subtype /Link /Rect [' . self::zahl($l[0]) . ' ' . $this->y($l[1] + $l[3]) . ' ' . self::zahl($l[0] + $l[2]) . ' ' .
                    $this->y($l[1]) . '] /Border [0 0 0] /A << /S /URI /URI ' . self::pdfText($l[4]) . ' >> >>';
            }
            $strom = implode("\n", $s['inhalt']);
            $obj[$inhalt] = '<< /Length ' . strlen($strom) . " >>\nstream\n" . $strom . "\nendstream";
            $obj[$seite] = '<< /Type /Page /Parent 2 0 R /MediaBox [0 0 ' . self::zahl($this->B) . ' ' . self::zahl($this->H) .
                '] /Resources << /Font << /F1 3 0 R /F2 4 0 R >> >> /Contents ' . $inhalt . ' 0 R' .
                ($annots ? ' /Annots [' . implode(' ', array_map(fn($a) => $a . ' 0 R', $annots)) . ']' : '') . ' >>';
            $kids[] = $seite . ' 0 R';
        }
        $obj[1] = '<< /Type /Catalog /Pages 2 0 R >>';
        $obj[2] = '<< /Type /Pages /Kids [' . implode(' ', $kids) . '] /Count ' . count($kids) . ' >>';
        $out = "%PDF-1.4\n%\xE2\xE3\xCF\xD3\n"; $lagen = [];
        for ($i = 1; $i < $n; $i++) { $lagen[$i] = strlen($out); $out .= $i . " 0 obj\n" . $obj[$i] . "\nendobj\n"; }
        $xref = strlen($out);
        $out .= "xref\n0 " . $n . "\n0000000000 65535 f \n";
        for ($i = 1; $i < $n; $i++) $out .= sprintf('%010d', $lagen[$i]) . " 00000 n \n";
        return $out . "trailer\n<< /Size " . $n . " /Root 1 0 R /Info 5 0 R >>\nstartxref\n" . $xref . "\n%%EOF\n";
    }
}


const B_INK = [0.102, 0.102, 0.098], B_GRAU = [0.333, 0.329, 0.31], B_GRUEN = [0.224, 1, 0.078], B_LINIE = [0.86, 0.86, 0.84];
const B_DUNKEL = '#157C00', B_ROT = '#B3261E', B_FLAECHE = '#F3F2EC', B_BALKEN = '#CFCEC6';

function b_zahl(float $n, int $st = 0): string { return number_format($n, $st, ',', '.'); }
function b_tag(string $iso): string { return substr($iso, 8, 2) . '.' . substr($iso, 5, 2) . '.'; }
/** Veränderung in Prozent: [Text, Farbe]; ohne Vergleichswert „–“ */
function b_delta(?float $jetzt, ?float $vorher): array {
    if ($vorher === null || $jetzt === null) return ['–', B_GRAU];
    if ($vorher == 0) return [$jetzt > 0 ? 'neu' : '–', B_GRAU];
    $p = round(($jetzt - $vorher) / $vorher * 100);
    if ($p == 0) return ['±0 %', B_GRAU];
    return [($p > 0 ? '+' : '–') . b_zahl(abs($p)) . ' %', $p > 0 ? B_DUNKEL : B_ROT];
}
/** Summe der Tageswerte von $bis zurück über $n Tage; null, wenn kein einziger Tag gezählt wurde */
function b_summe(array $verlauf, string $bis, int $n, string $feld): ?float {
    $s = 0; $da = false;
    for ($i = 0; $i < $n; $i++) {
        $t = date('Y-m-d', strtotime("$bis -$i day"));
        if (isset($verlauf[$t])) { $s += $verlauf[$t][$feld]; $da = true; }
    }
    return $da ? $s : null;
}

function bericht_logo(Pdf $P, float $x, float $yo, string $wortPfad): void {
    $m = 28 / 100;
    $P->rechteck($x, $yo, 28, 28, B_INK, 24 * $m);
    $P->svg('M29 20V78', $x, $yo, $m, '#FBFAF7', ['strich' => 12]);
    $P->rechteck($x + 33 * $m, $yo + 42 * $m, 38 * $m, 38 * $m, null, 19 * $m, '#FBFAF7', 12 * $m);
    $P->kreis($x + 65.4 * $m, $yo + 47.6 * $m, 11.5 * $m, B_INK);
    $P->kreis($x + 65.4 * $m, $yo + 47.6 * $m, 7.5 * $m, B_GRUEN);
    $s = 19.5 / 780; $wx = $x + 37; $wy = $yo + 14 - 19.5 / 2 - 330 * $s;
    $P->svg($wortPfad, $wx, $wy, $s, B_INK);
    $P->kreis($wx + 3705.5 * $s, $wy + 406.5 * $s, 85 * $s, B_DUNKEL);
}

/**
 * $d: tag (Y-m-d, der berichtete Tag), erstellt (Y-m-d H:i), beginn (Y-m-d, erster Zähltag),
 *     verlauf [Y-m-d => [b => Besucher, a => Aufrufe]], monat/jahr [b, a] (bis einschließlich tag),
 *     seiten [[pfad, titel, aufrufe]], herkunft [Gruppe => [Name => Besucher] | Besucher], geraete [Name => Besucher],
 *     bots (ausgefilterte Abrufe), vorschau (bool)
 */
function bericht_pdf(array $d, string $wortPfad = BERICHT_WORTMARKE): string {
    $P = new Pdf(); $B = $P->B; $H = $P->H; $R = 40; $W = $B - 2 * $R;
    $WT = ['Sonntag', 'Montag', 'Dienstag', 'Mittwoch', 'Donnerstag', 'Freitag', 'Samstag'];
    $MO = ['', 'Januar', 'Februar', 'März', 'April', 'Mai', 'Juni', 'Juli', 'August', 'September', 'Oktober', 'November', 'Dezember'];
    $tag = $d['tag']; $ts = strtotime($tag); $v = $d['verlauf'];
    $heute = $v[$tag] ?? ['b' => 0, 'a' => 0];
    $vortag = $v[date('Y-m-d', strtotime("$tag -1 day"))] ?? null;
    $vorwoche = $v[date('Y-m-d', strtotime("$tag -7 day"))] ?? null;
    $LINK = 'https://www.bondarium.de/';
    $wann = $tag === date('Y-m-d') ? 'heute' : 'gestern';   // Testmail über den laufenden Tag

    $P->seite();
    $P->rechteck(0, 0, $B, 56, B_GRUEN);
    bericht_logo($P, $R, 14, $wortPfad);
    $P->text($B - $R, 35, 'www.bondarium.de', ['gr' => 9, 'rechts' => true]);
    $P->link($B - $R - $P->weite('www.bondarium.de', 9), 24, $P->weite('www.bondarium.de', 9), 14, $LINK);

    $P->text($R, 94, 'Besucherbericht', ['gr' => 24, 'fett' => true]);
    $erst = strtotime($d['erstellt']);
    $P->text($R, 114, $WT[date('w', $ts)] . ', ' . date('j', $ts) . '. ' . $MO[date('n', $ts)] . ' ' . date('Y', $ts) .
        ' · erstellt am ' . date('d.m.Y', $erst) . ' um ' . date('H:i', $erst) . ' Uhr', ['gr' => 9.5, 'farbe' => B_GRAU]);
    if (!empty($d['vorschau'])) {
        $t = 'VORSCHAU MIT BEISPIELDATEN'; $w = $P->weite($t, 7, true) + 16;
        $P->rechteck($B - $R - $w, 80, $w, 17, '#FFF4CC', 8.5, '#E0B000', 0.6);
        $P->text($B - $R - $w / 2, 91.5, $t, ['gr' => 7, 'fett' => true, 'mitte' => true, 'farbe' => '#6B5200']);
    }

    // ---- Kennzahlen: vier Kacheln ----
    $kw = ($W - 30) / 4; $ky = 134; $kh = 76;
    // Durchschnitt nur über Tage seit Beginn der Zählung – sonst zöge die erste Woche den Wert nach unten
    $schnitt = function ($bis) use ($v, $d) {
        $s = b_summe($v, $bis, 7, 'b'); if ($s === null) return null;
        $n = 0; for ($i = 0; $i < 7; $i++) if (date('Y-m-d', strtotime("$bis -$i day")) >= $d['beginn']) $n++;
        return $s / max(1, $n);
    };
    $s7 = $schnitt($tag); $s7v = $schnitt(date('Y-m-d', strtotime("$tag -7 day")));
    $wtk = ['So.', 'Mo.', 'Di.', 'Mi.', 'Do.', 'Fr.', 'Sa.'][date('w', $ts)];
    $kacheln = [
        ['Besucher', b_zahl($heute['b']), b_delta($heute['b'], $vortag['b'] ?? null), 'zum Vortag', b_delta($heute['b'], $vorwoche['b'] ?? null), "zum $wtk der Vorwoche"],
        ['Seitenaufrufe', b_zahl($heute['a']), b_delta($heute['a'], $vortag['a'] ?? null), 'zum Vortag', b_delta($heute['a'], $vorwoche['a'] ?? null), "zum $wtk der Vorwoche"],
        ['Seiten je Besucher', $heute['b'] ? b_zahl($heute['a'] / $heute['b'], 1) : '–',
            b_delta($heute['b'] ? $heute['a'] / $heute['b'] : null, $vortag && $vortag['b'] ? $vortag['a'] / $vortag['b'] : null), 'zum Vortag', null, ''],
        ['Ø Besucher 7 Tage', $s7 === null ? '–' : b_zahl($s7), b_delta($s7, $s7v), 'zur Vorwoche', null, $s7v === null ? '' : 'Vorwoche: ' . b_zahl($s7v)],
    ];
    foreach ($kacheln as $i => [$titel, $wert, $d1, $t1, $d2, $t2]) {
        $x = $R + $i * ($kw + 10);
        $P->rechteck($x, $ky, $kw, $kh, B_FLAECHE, 6);
        $P->text($x + 12, $ky + 17, mb_strtoupper($titel), ['gr' => 6.5, 'fett' => true, 'farbe' => B_GRAU]);
        $P->text($x + 12, $ky + 44, $wert, ['gr' => 22, 'fett' => true]);
        $w = $P->text($x + 12, $ky + 58, $d1[0], ['gr' => 7.5, 'fett' => true, 'farbe' => $d1[1]]);
        $P->text($x + 12 + $w + 3, $ky + 58, $t1, ['gr' => 7.5, 'farbe' => B_GRAU]);
        if ($d2) { $w = $P->text($x + 12, $ky + 68, $d2[0], ['gr' => 7.5, 'fett' => true, 'farbe' => $d2[1]]); $P->text($x + 12 + $w + 3, $ky + 68, $t2, ['gr' => 7.5, 'farbe' => B_GRAU]); }
        elseif ($t2) $P->text($x + 12, $ky + 68, $t2, ['gr' => 7.5, 'farbe' => B_GRAU]);
    }

    // ---- Verlauf: Besucher der letzten 30 Tage (Balken) und 7-Tage-Durchschnitt (Linie) ----
    $y = 240;
    $P->text($R, $y, 'Besucher der letzten 30 Tage', ['gr' => 11, 'fett' => true]);
    $lx = $B - $R; $lx -= $P->text($lx, $y, 'Durchschnitt der letzten 7 Tage', ['gr' => 7, 'farbe' => B_GRAU, 'rechts' => true]) + 4;
    $P->linie($lx - 14, $y - 2.5, $lx, $y - 2.5, B_DUNKEL, 1.4); $lx -= 26;
    $lx -= $P->text($lx, $y, 'Besucher je Tag', ['gr' => 7, 'farbe' => B_GRAU, 'rechts' => true]) + 4;
    $P->rechteck($lx - 7, $y - 6.5, 7, 7, B_BALKEN, 1);
    $tage = []; for ($i = 29; $i >= 0; $i--) $tage[] = date('Y-m-d', strtotime("$tag -$i day"));
    $max = max([1, ...array_map(fn($t) => $v[$t]['b'] ?? 0, $tage)]);
    $schritt = 1; foreach ([1, 2, 5, 10, 20, 25, 50, 100, 200, 250, 500, 1000, 2000, 2500, 5000, 10000, 20000, 50000] as $s) { $schritt = $s; if ($max / $s <= 4) break; }
    $oben = ceil($max * 1.08 / $schritt) * $schritt;
    $cx = $R + 30; $cw = $B - $R - $cx; $c0 = $y + 18; $ch = 104; $cu = $c0 + $ch;
    for ($g = 0; $g <= $oben; $g += $schritt) {
        $gy = $cu - $g / $oben * $ch;
        $P->linie($cx, $gy, $B - $R, $gy, $g ? B_LINIE : B_GRAU, $g ? 0.4 : 0.6);
        $P->text($cx - 6, $gy + 2.5, b_zahl($g), ['gr' => 6.5, 'farbe' => B_GRAU, 'rechts' => true]);
    }
    $bw = $cw / 30; $linie = [];
    foreach ($tage as $i => $t) {
        $bx = $cx + $i * $bw; $wert = $v[$t]['b'] ?? null; $letzter = $i === 29;
        if ($wert) {
            $h = $wert / $oben * $ch;
            $P->rechteck($bx + $bw * 0.16, $cu - $h, $bw * 0.68, $h, $letzter ? B_INK : B_BALKEN);
            if ($letzter) $P->text($bx + $bw / 2, $cu - $h - 4, b_zahl($wert), ['gr' => 7, 'fett' => true, 'mitte' => true]);
        }
        if (($m = b_summe($v, $t, 7, 'b')) !== null && isset($v[date('Y-m-d', strtotime("$t -6 day"))])) $linie[] = [$bx + $bw / 2, $cu - $m / 7 / $oben * $ch];
        if ((29 - $i) % 7 === 0) $P->text($bx + $bw / 2, $cu + 11, b_tag($t), ['gr' => 6.5, 'farbe' => $letzter ? B_INK : B_GRAU, 'fett' => $letzter, 'mitte' => true]);
    }
    if (count($linie) > 1) $P->zug($linie, B_DUNKEL, 1.4);

    // ---- Zeiträume ----
    $y = $cu + 40;
    $P->text($R, $y, 'Zeiträume', ['gr' => 11, 'fett' => true]);
    $vm = date('Y-m-d', strtotime("$tag -1 day"));
    $spalten = [
        [ucfirst($wann), $heute['b'], $heute['a'], b_delta($heute['b'], $vortag['b'] ?? null), 'zum Vortag'],
        ['Letzte 7 Tage', b_summe($v, $tag, 7, 'b'), b_summe($v, $tag, 7, 'a'), b_delta(b_summe($v, $tag, 7, 'b'), b_summe($v, date('Y-m-d', strtotime("$tag -7 day")), 7, 'b')), 'zu den 7 Tagen davor'],
        ['Letzte 30 Tage', b_summe($v, $tag, 30, 'b'), b_summe($v, $tag, 30, 'a'), b_delta(b_summe($v, $tag, 30, 'b'), b_summe($v, date('Y-m-d', strtotime("$tag -30 day")), 30, 'b')), 'zu den 30 Tagen davor'],
        [$MO[date('n', $ts)] . (date('j', strtotime("$tag +1 day")) == 1 ? '' : ' bisher'), $d['monat'][0], $d['monat'][1], null, ''],
        [date('Y', $ts) . ' bisher', $d['jahr'][0], $d['jahr'][1], null, 'seit ' . date('d.m.Y', strtotime($d['beginn']))],
    ];
    $tx = $R + 92; $sw = ($B - $R - $tx) / count($spalten); $y += 18;
    $P->text($R, $y + 15, 'Besucher', ['gr' => 8.5, 'farbe' => B_GRAU]);
    $P->text($R, $y + 31, 'Seitenaufrufe', ['gr' => 8.5, 'farbe' => B_GRAU]);
    $P->text($R, $y + 46, 'Veränderung', ['gr' => 7.5, 'farbe' => B_GRAU]);
    foreach ($spalten as $i => [$titel, $b, $a, $dl, $hint]) {
        $rx = $tx + ($i + 1) * $sw - 4;
        $P->text($rx, $y, mb_strtoupper($titel), ['gr' => 6.5, 'fett' => true, 'farbe' => B_GRAU, 'rechts' => true]);
        $P->text($rx, $y + 15, $b === null ? '–' : b_zahl($b), ['gr' => 10, 'fett' => true, 'rechts' => true]);
        $P->text($rx, $y + 31, $a === null ? '–' : b_zahl($a), ['gr' => 9, 'rechts' => true]);
        if ($dl) $P->text($rx, $y + 46, $dl[0], ['gr' => 7.5, 'fett' => true, 'farbe' => $dl[1], 'rechts' => true]);
        $P->text($rx, $y + 56, $hint, ['gr' => 6, 'farbe' => B_GRAU, 'rechts' => true]);
    }
    $P->linie($R, $y + 5, $B - $R, $y + 5, B_INK, 0.8);
    $P->linie($R, $y + 20, $B - $R, $y + 20, B_LINIE, 0.4);
    $P->linie($R, $y + 36, $B - $R, $y + 36, B_LINIE, 0.4);

    // ---- unten links: meistbesuchte Seiten ----
    $y += 92; $lw = 255; $rx0 = $R + $lw + 25; $rw = $B - $R - $rx0;
    $P->text($R, $y, 'Meistbesuchte Seiten ' . $wann, ['gr' => 11, 'fett' => true]);
    $P->text($R, $y + 16, 'SEITE', ['gr' => 6.5, 'fett' => true, 'farbe' => B_GRAU]);
    $P->text($R + $lw, $y + 16, 'AUFRUFE', ['gr' => 6.5, 'fett' => true, 'farbe' => B_GRAU, 'rechts' => true]);
    $P->linie($R, $y + 21, $R + $lw, $y + 21, B_INK, 0.8);
    $smax = max([1, ...array_map(fn($s) => $s[2], $d['seiten'])]); $sy = $y + 21;
    foreach (array_slice($d['seiten'], 0, 10) as $s) {
        [$pfad, $titel, $n] = $s;
        $P->text($R, $sy + 13, $titel, ['gr' => 8.5, 'max' => 172]);
        $P->link($R, $sy + 3, min(172, $P->weite($titel, 8.5)), 13, $LINK . ltrim($pfad, '/'));
        $P->rechteck($R + 180, $sy + 6.5, max(1.5, 42 * $n / $smax), 8, B_BALKEN, 1);
        $P->text($R + $lw, $sy + 13, b_zahl($n), ['gr' => 8.5, 'rechts' => true]);
        $sy += 18; $P->linie($R, $sy, $R + $lw, $sy, B_LINIE, 0.4);
    }
    $rest = ($d['seiten_anzahl'] ?? count($d['seiten'])) - min(10, count($d['seiten']));
    if ($rest > 0) $P->text($R, $sy + 12, 'und ' . b_zahl($rest) . ' weitere Seiten mit zusammen ' . b_zahl($heute['a'] - array_sum(array_map(fn($s) => $s[2], array_slice($d['seiten'], 0, 10)))) . ' Aufrufen', ['gr' => 7, 'farbe' => B_GRAU]);

    // ---- unten rechts: Herkunft und Geräte ----
    $P->text($rx0, $y, 'Woher die Besucher kamen', ['gr' => 11, 'fett' => true]);
    $P->text($rx0, $y + 16, 'HERKUNFT', ['gr' => 6.5, 'fett' => true, 'farbe' => B_GRAU]);
    $P->text($B - $R, $y + 16, 'BESUCHER', ['gr' => 6.5, 'fett' => true, 'farbe' => B_GRAU, 'rechts' => true]);
    $P->linie($rx0, $y + 21, $B - $R, $y + 21, B_INK, 0.8);
    $gesamt = 0; foreach ($d['herkunft'] as $g) $gesamt += is_array($g) ? array_sum($g) : $g;
    $hy = $y + 21;
    foreach ($d['herkunft'] as $gruppe => $g) {
        $n = is_array($g) ? array_sum($g) : $g;
        $P->text($rx0, $hy + 13, $gruppe, ['gr' => 8.5, 'fett' => true]);
        $P->text($B - $R - 34, $hy + 13, b_zahl($n), ['gr' => 8.5, 'fett' => true, 'rechts' => true]);
        $P->text($B - $R, $hy + 13, $gesamt ? b_zahl($n / $gesamt * 100) . ' %' : '–', ['gr' => 8, 'farbe' => B_GRAU, 'rechts' => true]);
        $hy += 16;
        if (is_array($g)) {
            arsort($g); $teile = []; $k = 0; $sonst = 0;
            foreach ($g as $name => $z) { if ($k++ < 4) $teile[] = $name . ' ' . b_zahl($z); else $sonst += $z; }
            if ($sonst) $teile[] = 'weitere ' . b_zahl($sonst);
            foreach ($P->umbrechen(implode(' · ', $teile), $rw - 10, 7.5) as $zeile) { $P->text($rx0 + 10, $hy + 6, $zeile, ['gr' => 7.5, 'farbe' => B_GRAU]); $hy += 10; }
            $hy += 4;
        }
        $P->linie($rx0, $hy, $B - $R, $hy, B_LINIE, 0.4);
    }

    $gy = $hy + 26;
    $P->text($rx0, $gy, 'Geräte', ['gr' => 11, 'fett' => true]);
    $gsum = array_sum($d['geraete']); $gx = $rx0; $farben = [B_INK, '#8C8B84', B_BALKEN]; $i = 0;
    foreach ($d['geraete'] as $n) { $w = $gsum ? $rw * $n / $gsum : 0; $P->rechteck($gx, $gy + 9, $w, 10, $farben[$i++ % 3]); $gx += $w; }
    $gx = $rx0; $i = 0;
    foreach ($d['geraete'] as $name => $n) {
        $P->rechteck($gx, $gy + 28, 7, 7, $farben[$i++ % 3], 1);
        $gx += 10 + $P->text($gx + 10, $gy + 34.5, $name . ' ' . ($gsum ? b_zahl($n / $gsum * 100) : '0') . ' %', ['gr' => 7.5]) + 14;
    }

    // ---- Fuß: so wird gezählt ----
    $noten = [
        'So wird gezählt: ohne Cookies und ohne Speicherung im Browser. „Besucher“ heißt: verschiedene Besucher an einem Tag. Dafür bildet der Server aus IP-Adresse und Browser-Kennung ' .
        'eine Prüfsumme, die jeden Tag neu verschlüsselt wird; die IP-Adresse selbst wird nicht gespeichert. Über mehrere Tage sind die Besucher deshalb die Summe der Tageswerte – wer an zwei Tagen kommt, zählt zweimal.',
        'Robots und automatisierte Browser werden aussortiert (' . $wann . ' ' . b_zahl($d['bots']) . ' Abrufe); Robots, die kein JavaScript ausführen – die meisten Suchmaschinen –, kommen gar nicht erst an. ' .
        'Nicht gezählt werden auch Besucher mit abgeschaltetem JavaScript oder mit „Global Privacy Control“ bzw. „Do Not Track“ im Browser. ' .
        'Herkunft: die Website, von der ein Besucher an diesem Tag zuerst kam; Suchbegriffe übermitteln die Suchmaschinen nicht.',
    ];
    $fuss = []; foreach ($noten as $t) $fuss = array_merge($fuss, $P->umbrechen($t, $W, 7));
    $fy = $H - 34 - count($fuss) * 9;
    $P->linie($R, $fy - 12, $B - $R, $fy - 12, B_LINIE, 0.5);
    foreach ($fuss as $z) { $P->text($R, $fy, $z, ['gr' => 7, 'farbe' => B_GRAU]); $fy += 9; }
    $P->text($R, $H - 22, 'Bondarium – Besucherbericht · automatisch erstellt, nur für den internen Gebrauch', ['gr' => 7, 'farbe' => B_GRAU]);
    $P->text($B - $R, $H - 22, 'Seite 1 von 1', ['gr' => 7, 'farbe' => B_GRAU, 'rechts' => true]);
    return $P->bytes('Besucherbericht ' . date('d.m.Y', $ts) . ' – Bondarium');
}

// ---------- Zahlen aus der Datenbank ----------

/** Kurzer Seitenname aus dem <title> der Datei („Zinskurve seit 1972: Deutschland und USA – Bondarium“ → „Zinskurve seit 1972“) */
function bericht_seitenname(string $pfad): string
{
    if ($pfad === '/') return 'Startseite';
    if ($pfad === '/anleihe.html') return 'Anleihe-Steckbriefe (alle)';
    $html = @file_get_contents(__DIR__ . $pfad, false, null, 0, 20000);
    if ($html && preg_match('~<title>(.*?)</title>~si', $html, $m)) {
        $t = trim(html_entity_decode($m[1], ENT_QUOTES | ENT_HTML5, 'UTF-8'));
        $t = trim(preg_replace('~\s*[–-]\s*Bondarium$~u', '', $t));
        $t = trim(explode(':', $t)[0]);
        if ($t !== '') return $t;
    }
    return ltrim($pfad, '/');
}

function bericht_daten(PDO $db, string $tag): array
{
    $ts = strtotime($tag);
    $s = $db->prepare('SELECT tag, besucher, aufrufe FROM tage WHERE tag BETWEEN ? AND ? AND (besucher > 0 OR aufrufe > 0)');
    $s->execute([date('Y-m-d', strtotime("$tag -70 day")), $tag]);
    $verlauf = [];
    foreach ($s->fetchAll(PDO::FETCH_NUM) as [$t, $b, $a]) $verlauf[$t] = ['b' => (int)$b, 'a' => (int)$a];
    $summe = function (string $von) use ($db, $tag): array {
        $s = $db->prepare('SELECT COALESCE(SUM(besucher), 0), COALESCE(SUM(aufrufe), 0) FROM tage WHERE tag BETWEEN ? AND ?');
        $s->execute([$von, $tag]);
        return array_map('intval', $s->fetch(PDO::FETCH_NUM));
    };
    $beginn = (string)($db->query('SELECT MIN(tag) FROM tage WHERE besucher > 0')->fetchColumn() ?: $tag);

    $s = $db->prepare('SELECT pfad, aufrufe FROM seiten WHERE tag = ? ORDER BY aufrufe DESC, pfad');
    $s->execute([$tag]);
    $alle = $s->fetchAll(PDO::FETCH_NUM);
    $seiten = array_map(fn($z) => [$z[0], bericht_seitenname($z[0]), (int)$z[1]], array_slice($alle, 0, 10));

    $herkunft = ['Suchmaschinen' => [], 'KI-Assistenten' => [], 'Andere Websites' => [], 'Direkt oder unbekannt' => 0];
    $s = $db->prepare('SELECT gruppe, quelle, besucher FROM herkunft WHERE tag = ?');
    $s->execute([$tag]);
    foreach ($s->fetchAll(PDO::FETCH_NUM) as [$g, $q, $n]) {
        if (!array_key_exists($g, $herkunft)) continue;
        if (is_array($herkunft[$g])) $herkunft[$g][$q] = (int)$n; else $herkunft[$g] += (int)$n;
    }
    $geraete = ['Handy' => 0, 'Computer' => 0, 'Tablet' => 0];
    $s = $db->prepare('SELECT geraet, besucher FROM geraete WHERE tag = ?');
    $s->execute([$tag]);
    foreach ($s->fetchAll(PDO::FETCH_NUM) as [$g, $n]) if (isset($geraete[$g])) $geraete[$g] = (int)$n;
    $s = $db->prepare('SELECT robots FROM tage WHERE tag = ?');
    $s->execute([$tag]);

    return [
        'tag' => $tag, 'erstellt' => date('Y-m-d H:i'), 'beginn' => $beginn, 'verlauf' => $verlauf,
        'monat' => $summe(date('Y-m-01', $ts)), 'jahr' => $summe(date('Y-01-01', $ts)),
        'seiten' => $seiten, 'seiten_anzahl' => count($alle), 'herkunft' => $herkunft, 'geraete' => $geraete,
        'bots' => (int)($s->fetchColumn() ?: 0),
    ];
}

// ---------- Versand ----------

/** Bericht für $tag bauen und verschicken; Tage ohne Zählung werden übersprungen (true). Räumt alte Tageswerte auf.
 *  $test: Testmail über den laufenden Tag – wird auch ohne Zählung verschickt und im Betreff markiert. */
function bericht_senden(PDO $db, string $tag, bool $test = false): bool
{
    $grenze = date('Y-m-d', strtotime('-' . AUFBEWAHREN_MONATE . ' months'));
    foreach (['tage', 'seiten', 'herkunft', 'geraete'] as $t) $db->prepare("DELETE FROM $t WHERE tag < ?")->execute([$grenze]);

    $d = bericht_daten($db, $tag);
    if (!isset($d['verlauf'][$tag]) && !$test) return true;   // an diesem Tag wurde (noch) nicht gezählt
    $pdf = bericht_pdf($d);
    $h = $d['verlauf'][$tag] ?? ['b' => 0, 'a' => 0];
    $vortag = $d['verlauf'][date('Y-m-d', strtotime("$tag -1 day"))] ?? null;
    [$delta] = b_delta($h['b'], $vortag['b'] ?? null);
    $WT = ['Sonntag', 'Montag', 'Dienstag', 'Mittwoch', 'Donnerstag', 'Freitag', 'Samstag'];
    $MO = ['', 'Januar', 'Februar', 'März', 'April', 'Mai', 'Juni', 'Juli', 'August', 'September', 'Oktober', 'November', 'Dezember'];
    $ts = strtotime($tag);
    $betreff = ($test ? 'Testmail – ' : '') . 'Bondarium: ' . b_zahl($h['b']) . ' Besucher am ' . b_tag($tag) . ($delta !== '–' && $delta !== 'neu' ? " ($delta zum Vortag)" : '');
    $top = $d['seiten'][0] ?? null;
    $text = ($test ? 'Testmail: Bericht über den laufenden Tag, Stand ' . date('H:i') . " Uhr. Der echte Bericht kommt jeden Morgen ab 6 Uhr für den Vortag.\n\n" : '') .
        'Besucherbericht für ' . $WT[date('w', $ts)] . ', ' . date('j', $ts) . '. ' . $MO[date('n', $ts)] . ' ' . date('Y', $ts) . "\n\n" .
        'Besucher: ' . b_zahl($h['b']) . ($delta !== '–' ? " ($delta zum Vortag)" : '') . "\n" .
        'Seitenaufrufe: ' . b_zahl($h['a']) . "\n" .
        ($top ? 'Meistbesuchte Seite: ' . $top[1] . ' (' . b_zahl($top[2]) . ' Aufrufe)' . "\n" : '') .
        "\nDer ausführliche Bericht hängt als PDF an.\n\n– automatisch erstellt von " . SEITE . "\n";
    $datei = 'Bondarium-Besucherbericht-' . $tag . '.pdf';

    if (LOKAL) {
        return file_put_contents(STAT_DATEN . '/' . $datei, $pdf) !== false
            && file_put_contents(STAT_DATEN . '/lokal-mail.txt', "An: " . BERICHT_AN . "\nBetreff: $betreff\nAnhang: $datei\n\n$text") !== false;
    }
    $grenzeMime = 'b-' . bin2hex(random_bytes(12));
    $kopf = implode("\r\n", [
        'From: Bondarium <' . BERICHT_AN . '>',
        'MIME-Version: 1.0',
        'Content-Type: multipart/mixed; boundary="' . $grenzeMime . '"',
        'Auto-Submitted: auto-generated',
    ]);
    $koerper = "--$grenzeMime\r\nContent-Type: text/plain; charset=UTF-8\r\nContent-Transfer-Encoding: base64\r\n\r\n" .
        chunk_split(base64_encode($text)) .
        "--$grenzeMime\r\nContent-Type: application/pdf; name=\"$datei\"\r\nContent-Transfer-Encoding: base64\r\n" .
        "Content-Disposition: attachment; filename=\"$datei\"\r\n\r\n" . chunk_split(base64_encode($pdf)) . "--$grenzeMime--\r\n";
    return mail(BERICHT_AN, '=?UTF-8?B?' . base64_encode($betreff) . '?=', $koerper, $kopf, '-f ' . BERICHT_AN);
}
