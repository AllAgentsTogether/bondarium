#!/usr/bin/env bash
# scripts/htaccess_test.sh – prüft die .htaccess eines Bau-Ordners mit einem echten Apache (seit 02.10.2026).
#
# Ein Tippfehler in der .htaccess bedeutet Fehler 500 auf der ganzen Seite, und jeder Push veröffentlicht sie sofort.
# Das Skript startet deshalb einen eigenen Apache nur auf 127.0.0.1 mit dem Ordner als Docroot (AllowOverride All)
# und fragt die wichtigsten Adressen ab – so, wie sie bei STRATO ankommen: Host-Kopf www.bondarium.de / bondarium.de /
# bondarium.com, „https“ über X-Forwarded-Proto (STRATO beendet TLS vor dem Apache), „http“ ohne.
#
# Aufruf:  bash scripts/htaccess_test.sh <ordner> [port]          (Standard-Port 8188, belegt → nächster freier)
#          Lokal z. B. auf einen Testbau:  bash scripts/htaccess_test.sh tmp/bau-x
#          (die Ausnahmen /trigger/ und /.well-known/ werden nur geprüft, wenn der Testbau beide Dateien enthält –
#          siehe unten bei „Zweitdomain“)
#          Im Workflow (update-data.yml, Schritt „.htaccess prüfen“) auf _site, vor dem Upload.
# Läuft mit macOS (/usr/sbin/httpd, Module in /usr/libexec/apache2) und Ubuntu/Debian (apt-get install apache2:
# /usr/sbin/apache2, Module in /usr/lib/apache2/modules). Andere Pfade: HTTPD=… und APACHE_MODULE_DIR=… setzen.
# Nicht als root starten. HTACCESS_TEST_TRACE=1 schreibt das mod_rewrite-Protokoll ins Fehlerprotokoll.
#
# Ergebnis (Rückgabewert):
#   0 = alles gut (Warnungen zu Cache-Köpfen oder 304 möglich – die stoppen nichts)
#   1 = harter Fehler: falscher Status (z. B. 500), falsches Weiterleitungsziel, Sperre offen → NICHT hochladen
#   2 = Testumgebung nicht nutzbar (kein Apache, Modul fehlt, Start scheitert) – sagt nichts über die .htaccess
#
# Die erwarteten Antworten stehen unten in „Prüfliste“. Wer in der .htaccess eine Weiterleitung oder Sperre ändert,
# passt die Liste im selben Commit an.

ORDNER="${1:-}"
PORT="${2:-${HTACCESS_TEST_PORT:-8188}}"
if [ -z "$ORDNER" ] || [ ! -d "$ORDNER" ]; then
  echo "Aufruf: bash scripts/htaccess_test.sh <ordner> [port]" >&2
  exit 2
fi
ORDNER="$(cd "$ORDNER" && pwd -P)"
if [ ! -f "$ORDNER/.htaccess" ]; then
  echo "Keine .htaccess in $ORDNER" >&2
  exit 2
fi

IM_WORKFLOW=""
[ "${GITHUB_ACTIONS:-}" = "true" ] && IM_WORKFLOW=1

# ---------- Apache finden ----------
HTTPD="${HTTPD:-}"
if [ -z "$HTTPD" ]; then
  for k in /usr/sbin/apache2 /usr/sbin/httpd /usr/local/sbin/httpd /opt/homebrew/bin/httpd /usr/local/bin/httpd; do
    if [ -x "$k" ]; then HTTPD="$k"; break; fi
  done
fi
[ -z "$HTTPD" ] && HTTPD="$(command -v apache2 2>/dev/null || command -v httpd 2>/dev/null || true)"
if [ -z "$HTTPD" ] || [ ! -x "$HTTPD" ]; then
  echo "Kein ausführbarer Apache gefunden (${HTTPD:-httpd/apache2}). Ubuntu: sudo apt-get install apache2" >&2
  exit 2
fi
MODDIR="${APACHE_MODULE_DIR:-}"
if [ -z "$MODDIR" ]; then
  for k in /usr/lib/apache2/modules /usr/libexec/apache2 /usr/lib64/httpd/modules /usr/lib/httpd/modules \
           /opt/homebrew/lib/httpd/modules /usr/local/lib/httpd/modules; do
    if [ -f "$k/mod_rewrite.so" ]; then MODDIR="$k"; break; fi
  done
fi
if [ -z "$MODDIR" ]; then
  echo "Modulordner von Apache nicht gefunden (APACHE_MODULE_DIR setzen)" >&2
  exit 2
fi
if [ "$(id -u)" = "0" ]; then
  echo "Bitte nicht als root starten (Apache würde den Benutzer wechseln und den Ordner evtl. nicht lesen)." >&2
  exit 2
fi
command -v curl >/dev/null 2>&1 || { echo "curl fehlt" >&2; exit 2; }

ARBEIT="$(mktemp -d "${TMPDIR:-/tmp}/htaccess-test.XXXXXX")"
KOPF="$ARBEIT/kopf.txt"
KOERPER="$ARBEIT/koerper.txt"
CONF="$ARBEIT/httpd.conf"
FEHLERLOG="$ARBEIT/error_log"

aufraeumen() {
  if [ -f "$ARBEIT/httpd.pid" ]; then
    "$HTTPD" -f "$CONF" -k stop >/dev/null 2>&1 || kill "$(cat "$ARBEIT/httpd.pid")" 2>/dev/null || true
    for _ in 1 2 3 4 5 6 7 8 9 10; do [ -f "$ARBEIT/httpd.pid" ] || break; sleep 0.3; done
  fi
  rm -rf "$ARBEIT"
}
trap aufraeumen EXIT

# ---------- Freien Port suchen ----------
belegt() { curl -s -o /dev/null --max-time 2 "http://127.0.0.1:$1/" ; }
versuche=0
while belegt "$PORT"; do
  PORT=$((PORT + 1)); versuche=$((versuche + 1))
  if [ "$versuche" -gt 20 ]; then echo "Kein freier Port gefunden" >&2; exit 2; fi
done

# ---------- Minimal-Konfiguration ----------
STATISCH="$("$HTTPD" -l 2>/dev/null || true)"
lade() {  # lade <name> <datei>: LoadModule, außer das Modul ist fest eingebaut
  local name="$1" datei="$2" quelle="${2%.so}.c"
  if printf '%s\n' "$STATISCH" | grep -q "^ *${quelle}$"; then return 0; fi
  if [ ! -f "$MODDIR/$datei" ]; then
    echo "Apache-Modul fehlt: $MODDIR/$datei" >&2
    return 1
  fi
  echo "LoadModule ${name}_module $MODDIR/$datei"
}
{
  echo "ServerRoot \"$ARBEIT\""
  echo "DefaultRuntimeDir \"$ARBEIT\""
  echo "PidFile \"$ARBEIT/httpd.pid\""
  echo "Listen 127.0.0.1:$PORT"
  echo "ServerName localhost"
  if ! printf '%s\n' "$STATISCH" | grep -q 'prefork.c\|event.c\|worker.c'; then
    lade mpm_prefork mod_mpm_prefork.so || exit 2
  fi
  # wie bei STRATO: Umschreiben, Kopfzeilen, Kompression, MIME, Umgebung, Zugriffsregeln, Verzeichnisindex
  for m in authz_core:mod_authz_core.so authz_host:mod_authz_host.so unixd:mod_unixd.so dir:mod_dir.so \
           log_config:mod_log_config.so alias:mod_alias.so mime:mod_mime.so rewrite:mod_rewrite.so \
           headers:mod_headers.so filter:mod_filter.so deflate:mod_deflate.so env:mod_env.so \
           setenvif:mod_setenvif.so expires:mod_expires.so; do
    lade "${m%%:*}" "${m#*:}" || exit 2
  done
} > "$CONF.module" || { cat "$CONF.module" >&2; exit 2; }

MIMETYPES=""
for k in /etc/mime.types /private/etc/apache2/mime.types /etc/apache2/mime.types /etc/httpd/conf/mime.types; do
  if [ -f "$k" ]; then MIMETYPES="$k"; break; fi
done

{
  cat "$CONF.module"
  echo "ErrorLog \"$FEHLERLOG\""
  if [ -n "${HTACCESS_TEST_TRACE:-}" ]; then echo "LogLevel warn rewrite:trace3"; else echo "LogLevel warn"; fi
  echo "TypesConfig \"${MIMETYPES:-/dev/null}\""
  # feste Grundtypen, falls die Typenliste fehlt oder anders zuordnet
  echo "AddType text/html .html"
  echo "AddType text/css .css"
  echo "AddType application/javascript .js"
  echo "AddType application/json .json"
  echo "AddType image/svg+xml .svg"
  echo "AddType text/plain .txt"
  echo "AddType application/xml .xml"
  echo "DirectoryIndex index.html"
  echo "<Directory />"
  echo "  AllowOverride None"
  echo "  Require all denied"
  echo "</Directory>"
  echo "DocumentRoot \"$ORDNER\""
  echo "<Directory \"$ORDNER\">"
  echo "  Options FollowSymLinks"
  echo "  AllowOverride All"
  echo "  Require all granted"
  echo "</Directory>"
} > "$CONF"

if ! "$HTTPD" -t -f "$CONF" >"$ARBEIT/syntax.txt" 2>&1; then
  echo "Apache-Grundkonfiguration ungültig (Testumgebung, nicht die .htaccess):" >&2
  cat "$ARBEIT/syntax.txt" >&2
  exit 2
fi
if ! "$HTTPD" -f "$CONF" -k start >"$ARBEIT/start.txt" 2>&1; then
  echo "Apache startet nicht:" >&2
  cat "$ARBEIT/start.txt" "$FEHLERLOG" 2>/dev/null >&2
  exit 2
fi
bereit=""
for _ in $(seq 1 40); do
  if curl -s -o /dev/null --max-time 2 "http://127.0.0.1:$PORT/"; then bereit=1; break; fi
  sleep 0.25
done
if [ -z "$bereit" ]; then
  echo "Apache antwortet nicht auf Port $PORT:" >&2
  cat "$ARBEIT/start.txt" "$FEHLERLOG" 2>/dev/null >&2
  exit 2
fi
echo "Apache: $("$HTTPD" -v 2>/dev/null | head -1 | sed 's/^Server version: //') · Port $PORT · Docroot $ORDNER"

# ---------- Abfrage-Helfer ----------
HARTE_FEHLER=0
WARNUNGEN=0
CODE=""
LOCATION=""

# anfrage <schema> <host> <pfad> [weitere curl-Argumente…] → setzt CODE, LOCATION; Kopfzeilen in $KOPF
anfrage() {
  local schema="$1" host="$2" pfad="$3"; shift 3
  if [ "$schema" = "https" ]; then
    CODE="$(curl -s -o "$KOERPER" -D "$KOPF" --max-time 15 -H "Host: $host" -H "X-Forwarded-Proto: https" "$@" \
            -w '%{http_code}' "http://127.0.0.1:$PORT$pfad" 2>/dev/null)"
  else
    CODE="$(curl -s -o "$KOERPER" -D "$KOPF" --max-time 15 -H "Host: $host" "$@" \
            -w '%{http_code}' "http://127.0.0.1:$PORT$pfad" 2>/dev/null)"
  fi
  [ -z "$CODE" ] && CODE="000"
  LOCATION="$(kopfwert Location)"
}
# kopfwert <name> → Wert der (ersten) Kopfzeile aus der letzten Antwort
kopfwert() {
  grep -i "^$1:" "$KOPF" 2>/dev/null | head -1 | sed 's/^[^:]*:[[:space:]]*//' | tr -d '\r'
}
fehler() {
  HARTE_FEHLER=$((HARTE_FEHLER + 1))
  echo "  FEHLER  $1"
  [ -n "$IM_WORKFLOW" ] && echo "::error::.htaccess-Test: $1"
  return 0
}
warnung() {
  WARNUNGEN=$((WARNUNGEN + 1))
  echo "  WARNUNG $1"
  [ -n "$IM_WORKFLOW" ] && echo "::warning::.htaccess-Test: $1"
  return 0
}
ok() { echo "  ok      $1"; }

# pruefe <beschreibung> <schema> <host> <pfad> <status> [ziel]
# Bei 301 muss Location genau <ziel> sein, und das Ziel selbst darf nicht weiterleiten (= genau ein Sprung).
pruefe() {
  local text="$1" schema="$2" host="$3" pfad="$4" soll="$5" ziel="${6:-}"
  anfrage "$schema" "$host" "$pfad"
  local ist="$CODE" ort="$LOCATION"
  local was="$schema://$host$pfad"
  if [ "$ist" != "$soll" ]; then
    fehler "$text: $was → $ist ${ort:+($ort) }statt $soll${ziel:+ → $ziel}"
    return 0
  fi
  if [ -n "$ziel" ]; then
    if [ "$ort" != "$ziel" ]; then
      fehler "$text: $was → $ist nach „$ort“ statt nach „$ziel“"
      return 0
    fi
    # Ziel abfragen: es darf nicht noch einmal weiterleiten (Ketten kosten Zeit und Crawl-Budget)
    local zschema="${ziel%%://*}" rest="${ziel#*://}"
    local zhost="${rest%%/*}" zpfad="/${rest#*/}"
    [ "$rest" = "$zhost" ] && zpfad="/"
    zpfad="${zpfad%%#*}"
    anfrage "$zschema" "$zhost" "$zpfad"
    case "$CODE" in
      3*) fehler "$text: Kette – $was → $ziel → $CODE ${LOCATION}"; return 0 ;;
      200|410) ;;
      *) fehler "$text: Ziel $ziel antwortet mit $CODE"; return 0 ;;
    esac
    ok "$text: $was → $soll $ziel (Ziel $CODE)"
  else
    if [ -n "$ort" ] && [ "${soll#3}" = "$soll" ]; then
      fehler "$text: $was → $ist, aber mit Weiterleitung nach $ort"
      return 0
    fi
    ok "$text: $was → $ist"
  fi
}

# kopf <beschreibung> <pfad> <kopfzeile> <regex> [curl-Argumente…] – nur Warnung (Cache, Sicherheit: stoppt nichts)
kopf() {
  local text="$1" pfad="$2" name="$3" muster="$4"; shift 4
  anfrage https www.bondarium.de "$pfad" "$@"
  local wert; wert="$(kopfwert "$name")"
  if [ "$CODE" != "200" ]; then
    warnung "$text: $pfad → $CODE (Kopfzeile $name nicht prüfbar)"
  elif printf '%s' "$wert" | grep -Eq "$muster"; then
    ok "$text: $name: $wert"
  else
    warnung "$text: $pfad – $name ist „$wert“, erwartet /$muster/"
  fi
}

# revalidierung <pfad>: gleiches ETag + Last-Modified → 304; anderes ETag + altes Datum (= Datei geändert) → 200
revalidierung() {
  local pfad="$1"
  anfrage https www.bondarium.de "$pfad" -H "Accept-Encoding: gzip"
  local etag lm enc
  etag="$(kopfwert ETag)"; lm="$(kopfwert Last-Modified)"; enc="$(kopfwert Content-Encoding)"
  if [ "$CODE" != "200" ] || [ -z "$etag" ] || [ -z "$lm" ]; then
    warnung "304-Prüfung $pfad: Status $CODE, ETag „$etag“, Last-Modified „$lm“"
    return 0
  fi
  anfrage https www.bondarium.de "$pfad" -H "Accept-Encoding: gzip" -H "If-None-Match: $etag" -H "If-Modified-Since: $lm"
  if [ "$CODE" = "304" ]; then
    ok "304 bei unveränderter Datei: $pfad (ETag $etag${enc:+, $enc})"
  else
    warnung "Revalidierung $pfad liefert $CODE statt 304 (ETag $etag${enc:+, $enc}) – Browser laden die Datei jedes Mal neu"
  fi
  anfrage https www.bondarium.de "$pfad" -H "Accept-Encoding: gzip" -H 'If-None-Match: "0-0-gzip"' \
          -H "If-Modified-Since: Thu, 01 Jan 2015 00:00:00 GMT"
  if [ "$CODE" = "200" ]; then
    ok "200 bei geänderter Datei (anderes ETag, älteres Datum): $pfad"
  else
    fehler "Geänderte Datei $pfad liefert $CODE statt 200 – Besucher bekämen den alten Stand"
  fi
}

W=www.bondarium.de
D=https://www.bondarium.de

# ====================================================================================================================
# Prüfliste
# ====================================================================================================================
echo "== Seiten antworten (https, www) =="
pruefe "Startseite" https $W / 200
pruefe "Grundlagen" https $W /grundlagen.html 200
pruefe "Fehlerseite" https $W /gibt-es-nicht.html 404

echo "== Jede Datei im Hauptordner antwortet mit 200 (keine Weiterleitung, keine Sperre, kein Fehler 500) =="
anzahl=0
for f in "$ORDNER"/*.html "$ORDNER"/*.css "$ORDNER"/*.js "$ORDNER"/*.json "$ORDNER"/*.svg "$ORDNER"/*.woff2 \
         "$ORDNER"/*.png "$ORDNER"/*.webp "$ORDNER"/*.ico "$ORDNER"/*.txt "$ORDNER"/*.xml; do
  [ -f "$f" ] || continue
  n="$(basename "$f")"
  [ "$n" = "index.html" ] && continue   # /index.html leitet absichtlich auf / um (unten geprüft)
  anfrage https $W "/$(printf '%s' "$n" | sed 's/ /%20/g')"
  if [ "$CODE" != "200" ]; then
    fehler "/$n → $CODE${LOCATION:+ ($LOCATION)} statt 200"
  fi
  anzahl=$((anzahl + 1))
done
echo "  ok      $anzahl Dateien abgefragt"

echo "== Kanonische Adresse: genau ein Sprung auf https://www.bondarium.de/… =="
pruefe "http → https" http $W /grundlagen.html 301 "$D/grundlagen.html"
pruefe "http → https (Startseite)" http $W / 301 "$D/"
pruefe "ohne www" https bondarium.de /grundlagen.html 301 "$D/grundlagen.html"
pruefe "ohne www, http" http bondarium.de /grundlagen.html 301 "$D/grundlagen.html"
pruefe "Zweitdomain .com" https www.bondarium.com /grundlagen.html 301 "$D/grundlagen.html"
pruefe "Zweitdomain .com ohne www, http" http bondarium.com / 301 "$D/"
pruefe "Abfrage bleibt erhalten" http bondarium.de "/anleihe.html?isin=DE0001102580" 301 "$D/anleihe.html?isin=DE0001102580"

echo "== Frühere Adressen: ein Sprung auf das endgültige Ziel =="
pruefe "index.html" https $W /index.html 301 "$D/"
pruefe "index.html, http ohne www" http bondarium.de /index.html 301 "$D/"
pruefe "index.html, .com" https bondarium.com /index.html 301 "$D/"
pruefe "englische Kopie" https $W /en/ 301 "$D/"
pruefe "englische Kopie, http" http bondarium.de /en 301 "$D/"
pruefe "englische Kopie einer Seite" http $W /en/grundlagen.html 301 "$D/grundlagen.html"
pruefe "englische Startseite" http $W /en/index.html 301 "$D/"
pruefe "Laufzeit (alt)" http bondarium.de /anleihen-laufzeit.html 301 "$D/staatsanleihen-laufzeit.html"
pruefe "Laufzeit-Einzelseite (alt)" https $W /anleihen-kurzfristig.html 301 "$D/staatsanleihen-laufzeit.html#kurzfristig"
pruefe "Optimierung (alt)" http $W /optimierung.html 301 "$D/wissen.html"
pruefe "Entscheiden (alt)" http $W /entscheiden.html 301 "$D/wissen.html#auswaehlen"
pruefe "Vertiefen (alt)" https bondarium.com /vertiefen.html 301 "$D/wissen.html#fortgeschrittene"
pruefe "Unternehmensanleihen nach Kupon (alt)" https $W /unternehmensanleihen-kupon.html 301 "$D/anleihen-kupon.html"
pruefe "Zinsen (alt) → Zinsen-Übersicht" http bondarium.de /zinsen.html 301 "$D/beobachten.html"
pruefe "Zinsen (alt, englisch)" https $W /en/zinsen.html 301 "$D/beobachten.html"
pruefe "Steuer (Aktien-Teil)" http $W /steuer.html 301 "$D/steuern-handelskosten.html"

echo "== Frühere Aktien-Seiten: 410 (gibt es nicht mehr); http/ohne www/englisch erst ein Sprung auf https://www… =="
pruefe "KGV (Aktien-Teil)" https $W /kgv.html 410
pruefe "KGV, http ohne www" http bondarium.de /kgv.html 301 "$D/kgv.html"
pruefe "KGV, englisch" https $W /en/kgv.html 301 "$D/kgv.html"
pruefe "Krisen, Zweitdomain" https bondarium.com /krisen.html 301 "$D/krisen.html"
pruefe "Krisen (Aktien-Teil)" https $W /krisen.html 410
pruefe "BIP (Aktien-Teil)" https $W /bip.html 410
pruefe "Daten (Aktien-Teil)" https $W /data.json 410

echo "== Sperren (vor allen Weiterleitungen) =="
pruefe "Benutzerdaten" https $W /konto-daten/ 403
pruefe "Benutzerdaten, http, .com" http bondarium.com /konto-daten/x.sqlite 403
pruefe "Statistik-Daten" http bondarium.de /statistik-daten/tag.json 403
pruefe "Statistik-Bericht" https $W /statistik-bericht.php 403
pruefe "Deploy-Manifest" https $W /.deploy-manifest 403
pruefe "Datenbank-Datei" https $W /beispiel.sqlite 403
if [ -f "$ORDNER/trigger/refresh-config.php" ]; then
  pruefe "Trigger-Konfiguration (Token)" https $W /trigger/refresh-config.php 403
fi
# Zweitdomain: /trigger/ und /.well-known/ werden NICHT umgeleitet (Kopf-Schlüssel, Zertifikatsprüfung)
# Nur prüfbar, wenn die Datei im Ordner liegt: Fehlt sie, antwortet Apache mit 404, und ErrorDocument /404.html leitet
# auf .com wie jede Adresse auf www.bondarium.de um – das wäre ein falscher Fehler. Im Workflow legen
# security_txt.py und „Trigger bauen“ beide Dateien an; lokal vorher: python3 scripts/security_txt.py <ordner> und
# mkdir -p <ordner>/trigger && cp strato-cron/refresh.php strato-cron/.htaccess <ordner>/trigger/
for pfad in /trigger/refresh.php /.well-known/security.txt; do
  if [ ! -f "$ORDNER$pfad" ]; then
    if [ -n "$IM_WORKFLOW" ]; then
      warnung "Ausnahme .com: $pfad fehlt im Ordner – Ausnahme nicht geprüft"
    else
      echo "  --      Ausnahme .com: $pfad übersprungen (Datei fehlt im Ordner)"
    fi
    continue
  fi
  anfrage https bondarium.com "$pfad"
  case "$CODE" in
    3*) fehler "Ausnahme .com: https://bondarium.com$pfad wird umgeleitet ($CODE $LOCATION)" ;;
    500) fehler "Ausnahme .com: https://bondarium.com$pfad → 500" ;;
    *) ok "Ausnahme .com: https://bondarium.com$pfad → $CODE (keine Weiterleitung)" ;;
  esac
done

echo "== Cache und Kopfzeilen (nur Warnung) =="
kopf "HTML immer nachfragen" /grundlagen.html Cache-Control '^no-cache$'
kopf "HTML gzip" /grundlagen.html Content-Encoding '^gzip$' -H "Accept-Encoding: gzip"
kopf "CSS ein Jahr (Versions-URL)" "/base.css?v=test" Cache-Control 'max-age=31536000.*immutable'
kopf "JS ein Jahr (Versions-URL)" "/site.js?v=test" Cache-Control 'max-age=31536000.*immutable'
kopf "CSS gzip" /base.css Content-Encoding '^gzip$' -H "Accept-Encoding: gzip"
kopf "Schrift ein Jahr" /manrope-400.woff2 Cache-Control 'max-age=31536000'
kopf "Bilder einen Tag" /logo.svg Cache-Control 'max-age=86400'
kopf "Daten-JSON 15 Minuten" /renditen.json Cache-Control 'max-age=900'
kopf "Daten-JSON nicht im Suchindex" /renditen.json X-Robots-Tag 'noindex'
kopf "Such-Index lange (Versions-URL)" "/anleihen-index.json?v=test" Cache-Control 'max-age=2592000'
kopf "Suchindex lange (Versions-URL)" "/suchindex.json?v=test" Cache-Control 'max-age=2592000'
kopf "Sicherheit: nosniff" /grundlagen.html X-Content-Type-Options '^nosniff$'
kopf "Sicherheit: CSP" /grundlagen.html Content-Security-Policy "default-src 'self'"
kopf "Sicherheit: HSTS" /grundlagen.html Strict-Transport-Security 'max-age='

echo "== Revalidierung (ETag mit „-gzip“) =="
revalidierung /grundlagen.html
revalidierung /base.css

# Meldungen der .htaccess im Fehlerprotokoll (unbekannte Anweisung, Syntax) – bei 500 der Grund
if grep -Eq 'Invalid command|Syntax error|not allowed here|cannot compile|RewriteRule: bad|Expected </' "$FEHLERLOG" 2>/dev/null; then
  fehler "Fehlerprotokoll meldet Probleme mit der .htaccess:"
  grep -E 'Invalid command|Syntax error|not allowed here|cannot compile|RewriteRule: bad|Expected </' "$FEHLERLOG" | sort -u | head -10
fi

echo
if [ "$HARTE_FEHLER" -gt 0 ]; then
  echo "Ergebnis: $HARTE_FEHLER Fehler, $WARNUNGEN Warnungen – diese .htaccess NICHT veröffentlichen."
  echo "--- Fehlerprotokoll (Ende) ---"
  tail -20 "$FEHLERLOG" 2>/dev/null
  exit 1
fi
echo "Ergebnis: keine Fehler, $WARNUNGEN Warnungen."
exit 0
