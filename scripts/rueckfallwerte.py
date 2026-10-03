#!/usr/bin/env python3
"""rueckfallwerte.py – schreibt die Zahlen der sechs Zinsen-Datenseiten beim Deploy aus den Daten-JSONs ins HTML
(seit 02.10.2026).

Läuft im GitHub-Workflow auf dem Veröffentlichungsordner, NACH statische_tabellen.py und VOR seo.py, llms.py,
inline_data.py und dem Minify (eigener Schritt mit continue-on-error):

    python3 scripts/rueckfallwerte.py _site

Warum: Die Zinsen-Datenseiten tragen im Quell-HTML die Zahlen der letzten Handpflege (z. B. renditen.html
„Daten-Stand: 25.09.2026“, „Deutschland liegt heute bei 3,60 %“). Aktuell werden sie erst, wenn das Seitenskript die
JSON geladen hat. KI-Crawler und Bing führen oft kein JavaScript aus und sahen die alten Zahlen. Dieses Skript setzt
in genau die Elemente, die das Seitenskript überschreibt, genau die Werte, die es aus derselben JSON berechnet:
gleiche Rechnung, Rundung und Schreibweise (deutsches Komma, &nbsp;, echtes Minus, Monatsnamen, „über/unter“,
„steil/flach/invers“). Im Browser ersetzt das Seitenskript sie wie bisher, es springt nichts. Die Quell-HTML im
Repository bleiben unverändert.

  renditen.html              ← renditen.json (+ Jahreswerte bis 2023 aus dem Seitenskript): Kopfzeile, Tabelle,
                               Einordnung Deutschland, Daten-Stand
  unternehmensanleihen.html  ← unternehmen.json: Kopfzeile, Tabelle der Renditereihen, Daten-Stand
  zinskurve.html             ← zinskurve.json: Kacheln, Kopfzeile, Textzahlen, Inversionstabelle, Daten-Stand
  realzins.html              ← realzins.json: Kacheln, Steuer-Rechnung, Jahrzehnte, Breakeven-Tabelle, Textzahlen,
                               Kopfzeile, Hinweis unter dem Schaubild, Daten-Stand
  risikoaufschlaege.html     ← risikoaufschlaege.json: Kacheln, Rangliste, Textzahlen, Kopfzeile, Daten-Stand
  langlaeufer.html           ← langlaeufer.json, kurse-auswahl.json und kurse/<Jahr>/<teil>.json (dazu die Wochenreihen
                               aus dem Seitenskript): Kennzahlen-Tabelle, Kursspannen, Textzahlen, Kopfzeile, Daten-Stand

Regeln:
- Zahlen und Stand nur zusammen: Passt auf einer Seite etwas nicht, bleibt die ganze Seite, wie sie ist (Warnung).
- ANKER: Je Seite stehen unten die Zeilen des Seitenskripts, die hier nachgebaut sind (wörtlich). Fehlt eine davon,
  wurde das Seitenskript geändert – die Seite bleibt dann unverändert, bis die Rechnung hier nachgezogen ist.
  Texte, Farben, Reihen und eingebettete Daten liest das Skript direkt aus dem Seitenskript.
- Was das Seitenskript nur im Browser zeichnet (Schaubilder, Legenden, Auswahlfelder), bleibt außen vor.
- „heute“ ist der Tag des Laufs in deutscher Zeit (wie beim Besucher: Zukunftsdaten verwerfen, „veraltet“, „(älter)“).
"""
import datetime
import json
import math
import os
import re
import sys
from decimal import ROUND_HALF_UP, Decimal

try:   # Ortszeit des Besuchers: Deutschland (Zoneninfo gibt es ab Python 3.9; ohne Zeitzonendaten gilt UTC)
    from zoneinfo import ZoneInfo
    BERLIN = ZoneInfo("Europe/Berlin")
except Exception:
    BERLIN = None

NBSP = "\u00a0"    # geschütztes Leerzeichen (im HTML als &nbsp;)
MINUS = "\u2212"   # echtes Minus wie MC.zahl
DAY = 86400000
MONATE = ["Januar", "Februar", "März", "April", "Mai", "Juni", "Juli", "August", "September", "Oktober",
          "November", "Dezember"]


def warn(text):
    print(f"::warning::rueckfallwerte.py: {text}")


def lade(site, name):
    with open(os.path.join(site, name), encoding="utf-8") as f:
        return json.load(f)


def lies_text(site, name):
    with open(os.path.join(site, name), encoding="utf-8") as f:
        return f.read()


# ---------- Zahlen und Daten wie site.js (MC.zahl, MC.datum, MC.veraltet) ----------
def ist_zahl(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)


def zahl(v, nk=0):
    """MC.zahl: Intl.NumberFormat de-DE – kürzeste Dezimaldarstellung der Zahl, halbe Stellen weg von null gerundet
    (104,095 → 104,10), Tausenderpunkt, echtes Minus (wie der Browser auch vor „0,00“); keine Zahl → „–“."""
    if not ist_zahl(v):
        return "–"
    q = Decimal(repr(float(abs(v)))).quantize(Decimal(1).scaleb(-nk), rounding=ROUND_HALF_UP)
    s = f"{q:,.{nk}f}".replace(",", "\u0000").replace(".", ",").replace("\u0000", ".")
    negativ = v < 0 or (v == 0 and math.copysign(1.0, v) < 0)
    return (MINUS if negativ else "") + s


def vz(v, nk):
    """Vorzeichen wie in den Seitenskripten: „+0,35“, „−0,20“, „±0,00“."""
    return ("+" if v > 0 else MINUS if v < 0 else "±") + zahl(abs(v), nk)


def js_round(x):
    """Math.round: halbe Stellen nach oben (−2,5 → −2)."""
    f = math.floor(x)
    return f + 1 if x - f >= 0.5 else f


def datum(iso):
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", str(iso or ""))
    return f"{m.group(3)}.{m.group(2)}.{m.group(1)}" if m else "–"


def ist_tag(d):
    return isinstance(d, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", d) is not None


def ist_monat(d):
    return isinstance(d, str) and re.fullmatch(r"\d{4}-\d{2}", d) is not None


def mon_lang(m):
    return f"{MONATE[int(m[5:7]) - 1]} {m[:4]}"


def heute():
    return datetime.datetime.now(BERLIN or datetime.timezone.utc).date()


def ist_zukunft(d):
    """isFuture der Seitenskripte: Stand nach dem heutigen Tag bzw. Monat."""
    t = heute().isoformat()
    return d > t[:7] if ist_monat(d) else str(d) > t


def lokal_ms(iso):
    """new Date("JJJJ-MM-TTT00:00:00").getTime() – Mitternacht Ortszeit."""
    y, m, d = (int(x) for x in iso[:10].split("-"))
    return datetime.datetime(y, m, d, tzinfo=BERLIN or datetime.timezone.utc).timestamp() * 1000


STALE_TAGE = 5   # wird aus site.js gelesen (MC.STALE_TAGE)


def boersentage(iso):
    """MC.boersentage: Werktage (Mo–Fr) NACH dem Datum bis heute einschließlich."""
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", str(iso or ""))
    if not m:
        return None
    d, ende, n = datetime.date(int(m.group(1)), int(m.group(2)), int(m.group(3))), heute(), 0
    while d < ende:
        d += datetime.timedelta(days=1)
        if d <= ende and d.weekday() < 5:
            n += 1
    return n


def veraltet(iso):
    n = boersentage(iso)
    return n is not None and n >= STALE_TAGE


# ---------- Anleihen-Mathematik wie bond.js (MC.bond): jährliche Verzinsung, Zeit taggenau ----------
EPOCHE = datetime.date(1970, 1, 1).toordinal()


def utc(iso):
    y, m, d = (int(x) for x in iso[:10].split("-"))
    return (datetime.date(y, m, d).toordinal() - EPOCHE) * DAY + 12 * 3600000


def iso_von(t):
    return datetime.date.fromordinal(t // DAY + EPOCHE).isoformat()


def add_days(iso, n):
    return iso_von(utc(iso) + n * DAY)


def months_back(t, m):
    d = datetime.date.fromordinal(t // DAY + EPOCHE)
    y, mo = divmod(d.month - 1 - m, 12)
    jahr, monat = d.year + y, mo + 1
    letzter = (datetime.date(jahr + monat // 12, monat % 12 + 1, 1) - datetime.timedelta(days=1)).day
    return (datetime.date(jahr, monat, min(d.day, letzter)).toordinal() - EPOCHE) * DAY + 12 * 3600000


def years_to(maturity, von):
    return (utc(maturity) - utc(von)) / DAY / 365.25


_FOLGE = {}


def coupon_dates(b, settle_iso):
    """Kupontermine ohne Zinstage (b.days): vom Fälligkeitstag rückwärts in Schritten von 12/freq Monaten."""
    s, mat, step = utc(settle_iso), utc(b["maturity"]), 12 / b["freq"]
    if s <= 0:
        out, k, t = [], 0, mat
        while t > s:
            out.insert(0, t)
            k += 1
            t = months_back(mat, int(k * step))
        return out, t
    key = f"{b['maturity']}/{b['freq']}"
    if key not in _FOLGE:
        seq, k, t = [], 0, mat
        while t > 0:
            seq.append(t)
            k += 1
            t = months_back(mat, int(k * step))
        seq.append(t)
        _FOLGE[key] = seq[::-1]
    seq = _FOLGE[key]
    lo, hi = 1, len(seq)
    while lo < hi:
        m = (lo + hi) >> 1
        if seq[m] > s:
            hi = m
        else:
            lo = m + 1
    return seq[lo:], seq[lo - 1]


def _pow(a, b):
    try:
        return math.pow(a, b)
    except (ValueError, OverflowError):
        return float("nan")


class Pricer:
    def __init__(self, b, settle_iso):
        s = utc(settle_iso)
        dates, prev = coupon_dates(b, settle_iso)
        n, c = len(dates), b["coupon"] / b["freq"]
        self.tau = [(t - s) / DAY / 365.25 for t in dates]
        self.cf = [c * 1 + 100 if i == n - 1 else c for i in range(n)]   # letzter Kupon voll (ohne Zinstage: cd.last = 1)
        self.acc = c * (s - prev) / (dates[0] - prev) if n else 0

    def price(self, y):
        pv = 0
        for t, c in zip(self.tau, self.cf):
            pv += c / _pow(1 + y, t)
        return pv - self.acc

    def slope(self, y):
        d = 0
        for t, c in zip(self.tau, self.cf):
            d -= t * c / _pow(1 + y, t + 1)
        return d


def yield_from_price(b, p, settle_iso, start=None):
    """MC.bond.yieldFromPrice: Newton, Rückfall Halbierung im Bereich −2 … 30 %; Ergebnis dezimal."""
    f = Pricer(b, settle_iso)
    y = start if start is not None and math.isfinite(start) else 0.03
    for _ in range(40):
        try:
            step = (f.price(y) - p) / f.slope(y)
        except ZeroDivisionError:
            break
        if not math.isfinite(step):
            break
        y -= step
        if not (-0.02 < y < 0.30):
            break
        if abs(step) < 1e-12:
            return y
    lo, hi = -0.02, 0.30
    for _ in range(80):
        mid = (lo + hi) / 2
        if f.price(mid) > p:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def mod_duration(b, y, settle_iso):
    f = Pricer(b, settle_iso)
    pv = t = 0
    for tau, c in zip(f.tau, f.cf):
        x = c / _pow(1 + y, tau)
        pv += x
        t += tau * x
    mac = t / pv if pv else 0
    return mac / (1 + y)


def fmt_coupon(c):
    return zahl(c, 3 if js_round(c * 1000) % 10 else 2)


# ---------- Seitenskript lesen: Konstanten (Texte, Reihen, eingebettete Daten) ----------
def js_str(s):
    def ersetze(m):
        e = m.group(1)
        if e[0] == "u" and len(e) == 5:
            return chr(int(e[1:], 16))
        return {"n": "\n", "t": "\t"}.get(e, e)
    return re.sub(r"\\(u[0-9a-fA-F]{4}|.)", ersetze, s)


def js_block(js, marke):
    """Inhalt der Klammer, mit der `marke` endet (z. B. "const T = {"), ohne die äußeren Klammern."""
    i = js.find(marke)
    if i < 0:
        raise ValueError(f"im Seitenskript fehlt „{marke}“")
    start = i + len(marke) - 1
    auf = js[start]
    zu = {"{": "}", "[": "]", "(": ")"}[auf]
    tiefe, j, q = 0, start, None
    while j < len(js):
        ch = js[j]
        if q:
            if ch == "\\":
                j += 2
                continue
            if ch == q:
                q = None
        elif js.startswith("//", j):
            j = js.find("\n", j)
            if j < 0:
                break
            continue
        elif js.startswith("/*", j):
            j = js.find("*/", j) + 2
            continue
        elif ch in "\"'`":
            q = ch
        elif ch == auf:
            tiefe += 1
        elif ch == zu:
            tiefe -= 1
            if tiefe == 0:
                return js[start + 1:j]
        j += 1
    raise ValueError(f"Klammer nach „{marke}“ nicht geschlossen")


_JS_WERT = r'("(?:[^"\\\n]|\\.)*"|true|false|null|-?\d+(?:\.\d+)?)'


def js_wert(t):
    if t.startswith('"'):
        return js_str(t[1:-1])
    if t in ("true", "false", "null"):
        return {"true": True, "false": False, "null": None}[t]
    return float(t) if "." in t else int(t)


def js_texte(block):
    """Schlüssel: "Text" eines Objekt-Literals (nur Texte in doppelten Anführungszeichen)."""
    return {k: js_str(v) for k, v in re.findall(r'(\w+)\s*:\s*"((?:[^"\\\n]|\\.)*)"', block)}


def js_objekte(block):
    """Liste flacher Objekt-Literale { key: "…", coupon: 2.15, … } in einem Array-Block."""
    out = []
    for m in re.finditer(r"\{([^{}]*)\}", block):
        out.append({k: js_wert(v) for k, v in re.findall(r"(\w+)\s*:\s*" + _JS_WERT, m.group(1))})
    return out


def js_punkt(block, name):
    """name: { date: "…", price: 40.07, yield: 3.90 } → dict."""
    m = re.search(name + r":\s*\{([^{}]*)\}", block)
    if not m:
        raise ValueError(f"im Seitenskript fehlt „{name}: {{…}}“")
    return {k: js_wert(v) for k, v in re.findall(r"(\w+)\s*:\s*" + _JS_WERT, m.group(1))}


# ---------- HTML: Elemente wie querySelector finden und ihren Inhalt ersetzen ----------
_START = re.compile(r"<([a-zA-Z][a-zA-Z0-9-]*)((?:\s+[^\s=>/\"']+(?:\s*=\s*(?:\"[^\"]*\"|'[^']*'|[^\s>\"']+))?)*)\s*(/?)>")
_ATTR = re.compile(r"([^\s=>/\"']+)(?:\s*=\s*(?:\"([^\"]*)\"|'([^']*)'|([^\s>\"']+)))?")
_SEL = re.compile(r"^([a-z][a-z0-9]*)?(#[\w-]+)?((?:\.[\w-]+)*)((?:\[[\w-]+(?:=\"[^\"]*\")?\])*)$")


def esc(s):
    """MC.esc: & < > \" ' maskieren."""
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            .replace('"', "&quot;").replace("'", "&#39;"))


def text_html(t):
    """textContent als HTML: maskiert, geschütztes Leerzeichen als &nbsp; (wie im übrigen Quell-HTML)."""
    return str(t).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace(NBSP, "&nbsp;")


class Element:
    def __init__(self, tag, attrs, a, b, ia, ib):
        self.tag, self.attrs, self.a, self.b, self.ia, self.ib = tag, attrs, a, b, ia, ib


class Seite:
    """Eine HTML-Datei in _site. Gesucht wird nur in <main> – dort stehen alle Elemente, die die Seitenskripte füllen."""

    def __init__(self, pfad):
        self.pfad = pfad
        with open(pfad, encoding="utf-8") as f:
            self.html = self.original = f.read()
        self.js = "\n".join(m.group(1) for m in re.finditer(r"<script>(.*?)</script>", self.html, re.S))
        self.gesetzt = self.geaendert = 0

    def anker(self, zeilen):
        fehlt = [z for z in zeilen if z not in self.js]
        if fehlt:
            raise ValueError("Seitenskript geändert, Rechnung hier nachziehen – fehlt: " + " | ".join(z[:90] for z in fehlt))

    def _main(self):
        a = self.html.find("<main")
        b = self.html.find("</main>", a)
        if a < 0 or b < 0:
            raise ValueError("kein <main>")
        return a, b

    def _schluss(self, tag, pos):
        tiefe = 1
        for m in re.finditer(r"<(/?)" + tag + r"\b[^>]*>", self.html[pos:], re.I):
            if m.group(1):
                tiefe -= 1
                if tiefe == 0:
                    return pos + m.start()
            elif not m.group(0).endswith("/>"):
                tiefe += 1
        raise ValueError(f"</{tag}> fehlt")

    @staticmethod
    def _passt(tok, tag, attrs):
        m = _SEL.match(tok)
        if not m:
            raise ValueError(f"Selektor „{tok}“ nicht unterstützt")
        t, i, k, at = m.groups()
        if t and t != tag:
            return False
        if i and attrs.get("id") != i[1:]:
            return False
        klassen = (attrs.get("class") or "").split()
        if any(c not in klassen for c in k.split(".")[1:]):
            return False
        for name, gleich, wert in re.findall(r"\[([\w-]+)(=)?(?:\"([^\"]*)\")?\]", at):
            if name not in attrs or (gleich and attrs[name] != wert):
                return False
        return True

    def finde(self, sel):
        """Alle Treffer des letzten Selektor-Teils innerhalb des ersten Treffers der vorderen Teile."""
        a, b = self._main()
        toks = sel.split()
        for n, tok in enumerate(toks):
            treffer = []
            for m in _START.finditer(self.html, a, b):
                tag = m.group(1).lower()
                attrs = {}
                for am in _ATTR.finditer(m.group(2) or ""):
                    attrs[am.group(1).lower()] = next((g for g in am.groups()[1:] if g is not None), "")
                if self._passt(tok, tag, attrs):
                    ib = m.end() if m.group(3) else self._schluss(tag, m.end())
                    treffer.append(Element(tag, attrs, m.start(), m.end(), m.end(), ib))
            if "#" in tok and len(treffer) > 1:
                raise ValueError(f"{tok} mehrfach")
            if not treffer:
                return []
            if n < len(toks) - 1:
                a, b = treffer[0].ia, treffer[0].ib
            else:
                return treffer
        return []

    def _ersetze(self, a, b, neu):
        alt = self.html[a:b]
        self.html = self.html[:a] + neu + self.html[b:]
        self.gesetzt += 1
        if alt != neu:
            self.geaendert += 1

    def _inhalt(self, sel, neu, alle, muss):
        els = self.finde(sel)
        if not els:
            if muss:
                raise ValueError(f"Element {sel} fehlt")
            return
        for el in reversed(els if alle else els[:1]):   # von hinten: vordere Positionen bleiben gültig
            self._ersetze(el.ia, el.ib, neu)

    def text(self, sel, t, alle=False, muss=True):
        """el.textContent = t"""
        self._inhalt(sel, text_html(t), alle, muss)

    def inner(self, sel, h, muss=True):
        """el.innerHTML = h"""
        self._inhalt(sel, h.replace(NBSP, "&nbsp;"), False, muss)

    def attr(self, sel, name, wert, muss=True):
        """el.setAttribute(name, wert) bzw. el.className = wert (name „class“)"""
        els = self.finde(sel)
        if not els:
            if muss:
                raise ValueError(f"Element {sel} fehlt")
            return
        el = els[0]
        tag = self.html[el.a:el.b]
        neu_attr = f'{name}="{esc(wert)}"'
        m = re.search(r"\s" + re.escape(name) + r"=(\"[^\"]*\"|'[^']*'|[^\s>]+)", tag)
        if m:
            neu = tag[:m.start() + 1] + neu_attr + tag[m.end():]
        else:
            ende = len(tag) - (2 if tag.endswith("/>") else 1)
            neu = tag[:ende].rstrip() + " " + neu_attr + tag[ende:]
        self._ersetze(el.a, el.b, neu)

    def klasse(self, sel, name, an):
        """el.classList.toggle(name, an)"""
        els = self.finde(sel)
        if not els:
            raise ValueError(f"Element {sel} fehlt")
        klassen = (els[0].attrs.get("class") or "").split()
        if an and name not in klassen:
            klassen.append(name)
        elif not an and name in klassen:
            klassen.remove(name)
        elif "class" not in els[0].attrs:
            return
        self.attr(sel, "class", " ".join(klassen))

    def stil(self, sel, prop, wert):
        """el.style.setProperty(prop, wert) – nur eine Eigenschaft im style-Attribut ersetzen"""
        el = self.finde(sel)
        if not el:
            raise ValueError(f"Element {sel} fehlt")
        alt = el[0].attrs.get("style") or ""
        if re.search(re.escape(prop) + r"\s*:", alt):
            neu = re.sub(re.escape(prop) + r"\s*:\s*[^;]*", f"{prop}:{wert}", alt, count=1)
        else:
            neu = (alt.rstrip("; ") + ";" if alt.strip() else "") + f"{prop}:{wert}"
        self.attr(sel, "style", neu)

    def speichern(self):
        if self.html != self.original:
            with open(self.pfad, "w", encoding="utf-8") as f:
                f.write(self.html)


# ---------- Gemeinsam: Renditereihen mit Hoch/Tief/Ø (renditen.html, unternehmensanleihen.html) ----------
def dez_jahr(d):
    if ist_monat(d):
        return int(d[:4]) + (int(d[5:7]) - 0.5) / 12
    y = int(d[:4])
    ms = (datetime.date.fromisoformat(d) - datetime.date(y, 1, 1)).days * DAY + 43200000
    return y + ms / DAY / 365.25


def fmt_stand(d):
    if ist_monat(d):
        return d[5:7] + "." + d[:4]
    return datum(d) if ist_tag(d) else "–"


def juengstes(defs, latest):
    best = None
    for c in defs:
        l = latest.get(c["key"])
        if l and (ist_tag(l.get("date")) or ist_monat(l.get("date"))) and (best is None or dez_jahr(l["date"]) > dez_jahr(best)):
            best = l["date"]
    return best


def juengstes_taeglich(defs, latest, daily):
    best = None
    for k in daily:
        l = latest.get(k)
        if l and ist_tag(l.get("date")) and (best is None or l["date"] > best):
            best = l["date"]
    return best or juengstes(defs, latest)


def alter_tage(d, ref):
    iso = d + "-15" if ist_monat(d) else d
    bis = lokal_ms(ref) if ist_tag(ref) else datetime.datetime.now(datetime.timezone.utc).timestamp() * 1000
    return (bis - lokal_ms(iso)) / 864e5


def reihen_mischen(defs, latest, annual, items, naechster_tag=False):
    """mergeData: nur plausible Werte; Stände nach heute verwerfen (Japan: auf den vorigen Werktag zurückführen)."""
    if not isinstance(items, dict):
        return
    for c in defs:
        src = items.get(c["key"])
        if not isinstance(src, dict):
            continue
        l = src.get("latest")
        if naechster_tag and c.get("pubNextDay") and isinstance(l, dict) and ist_tag(l.get("date")) and ist_zukunft(l["date"]):
            t = datetime.date.fromisoformat(l["date"]) - datetime.timedelta(days=1)
            while t.weekday() >= 5:
                t -= datetime.timedelta(days=1)
            l = {"date": t.isoformat(), "yield": l.get("yield")}
        if (isinstance(l, dict) and (ist_tag(l.get("date")) or ist_monat(l.get("date"))) and not ist_zukunft(l["date"])
                and ist_zahl(l.get("yield"))):
            latest[c["key"]] = {"date": l["date"], "yield": l["yield"]}
        if isinstance(src.get("annual"), dict):
            an = annual.setdefault(c["key"], {})
            for yr, v in src["annual"].items():
                if re.fullmatch(r"\d{4}", str(yr)) and ist_zahl(v):
                    an[int(yr)] = v


def reihen_kennzahlen(c, latest, annual, ref, old_day, old_month, T):
    """rowStats: aktueller Wert, Stand (+ „älter“), Hoch/Tief/Ø der Jahresdurchschnitte."""
    ann = annual.get(c["key"]) or {}
    l = latest.get(c["key"]) or {}
    hi = lo = None
    summe = 0
    for yr in sorted(ann):
        v = ann[yr]
        summe += v
        if hi is None or v > ann[hi]:
            hi = yr
        if lo is None or v < ann[lo]:
            lo = yr
    has_date = ist_tag(l.get("date")) or ist_monat(l.get("date"))
    return {
        "c": c, "name": T.get(c.get("tblKey") or c["nameKey"], c.get("tblKey") or c["nameKey"]),
        "current": l["yield"] if ist_zahl(l.get("yield")) else None,
        "standTxt": fmt_stand(l["date"]) if has_date else None,
        "old": has_date and alter_tage(l["date"], ref) > (old_month if ist_monat(l["date"]) else old_day),
        "high": ann[hi] if hi is not None else None, "hiYr": hi,
        "low": ann[lo] if lo is not None else None, "loYr": lo,
        "avg": summe / len(ann) if ann else None,
    }


def zelle_stand(r, T, klasse):
    if r["standTxt"] is None:
        stand = "–"
    elif r["old"]:
        stand = f'<span class="old">{esc(r["standTxt"])} {T["standOld"]}</span>'
    else:
        stand = esc(r["standTxt"])
    hoch = f'{zahl(r["high"], 2)}{NBSP}% ({r["hiYr"]})' if r["high"] is not None else "–"
    tief = f'{zahl(r["low"], 2)}{NBSP}% ({r["loYr"]})' if r["low"] is not None else "–"
    schnitt = zahl(r["avg"], 2) + NBSP + "%" if r["avg"] is not None else "–"
    return (f'<td class="{klasse}">{stand}</td>\n      <td class="num">{hoch}</td>\n'
            f'      <td class="num">{tief}</td>\n      <td class="num">{schnitt}</td>')


def daten_stand_veraltet(s, text, iso):
    """Fußzeile „Daten-Stand: …“ samt Klasse „stale“ (MC.veraltet, gezählt bis heute)."""
    s.text("#datastand", text)
    s.klasse("#datastand", "stale", bool(iso) and ist_tag(iso) and veraltet(iso))


# ---------- renditen.html ----------
ANKER_RENDITEN = [
    'if (l && (isDay(l.date) || isMonth(l.date)) && !isFuture(l.date) && typeof l.yield === "number" && isFinite(l.yield)) D.latest[c.key] = { date: l.date, yield: l.yield };',
    'if (/^\\d{4}$/.test(yr) && typeof v === "number" && isFinite(v)) an[yr] = v;',
    '.then(d => { if (d) mergeData(CHARTS.renditen, d.countries); rerender("renditen.json"); })',
    'if (l && isDay(l.date) && (best === null || l.date > best)) best = l.date;',
    'return best || newestDate(ch);',
    'if (isMonth(d)) return d.slice(5, 7) + "." + d.slice(0, 4);',
    'const iso = isMonth(d) ? d + "-15" : d;',
    'if (hi === null || v > ann[hi]) hi = yr;',
    'if (lo === null || v < ann[lo]) lo = yr;',
    'const avg = years.length ? sum / years.length : null;',
    'const old = hasDate && ageDays(latest.date, ref) > (isMonth(latest.date) ? OLD_MONTH : OLD_DAY);',
    'c, name: L(c.tblKey || c.nameKey),',
    'const ch = CHARTS.renditen, ref = newestDaily(ch);',
    'function curYieldCell(r) { return `<td class="num">${r.current !== null ? fmt(r.current, 2) + "\\u00A0%" : "–"}${r.standTxt !== null ? `<small class="cur-m">${MC.esc(r.standTxt)}</small>` : ""}</td>`; }',
    'const stand = r.standTxt !== null ? (r.old ? `<span class="old">${MC.esc(r.standTxt)} ${L("standOld")}</span>` : MC.esc(r.standTxt)) : "–";',
    'return `<td class="num stand">${stand}</td>',
    '<td class="num">${r.high !== null ? `${fmt(r.high, 2)}\\u00A0% (${r.hiYr})` : "–"}</td>',
    '<td class="num">${r.low !== null ? `${fmt(r.low, 2)}\\u00A0% (${r.loYr})` : "–"}</td>',
    '<td class="num">${r.avg !== null ? fmt(r.avg, 2) + "\\u00A0%" : "–"}</td>`;',
    'const sym = CUR_SYM[r.cur] ? ` <span class="sym">${CUR_SYM[r.cur]}</span>` : "";',
    '<th scope="row"><i class="tag" style="background:${r.c.color}"></i>${MC.esc(r.name)}<small class="cur-m">${r.cur}</small></th>${curYieldCell(r)}',
    '<td class="cur">${r.cur}${sym}</td>',
    'el.textContent = `${L(titleKey)} · ${YEAR0} – ${Number(String(nd).slice(0, 4))} · ${L("asOf")} ${fmtStand(nd)}`;',
    'setEyebrow("eyebrow-renditen", "eyebrow", CHARTS.renditen);',
    'if (r.current !== null) { set("e-de", fmt(r.current, 2)); set("e-akt", fmt(r.current, 2) + "\\u00A0%"); set("e-akt-d", (isDay(l.date) ? "Tageswert " : "Monatswert ") + fmtStand(l.date)); }',
    'if (r.avg !== null) { set("e-avg", fmt(r.avg, 2) + "\\u00A0%"); set("e-avg2", fmt(r.avg, 2)); }',
    'if (r.high !== null) set("e-hoch", `${fmt(r.high, 2)}\\u00A0% (${r.hiYr})`);',
    'if (r.low !== null) set("e-tief", `${fmt(r.low, 2)}\\u00A0% (${r.loYr})`);',
    'if (r.current !== null && r.avg !== null) set("e-lage", r.current < r.avg ? "unter" : "über");',
    'const alt = isDay(d) && !!(MC.veraltet && MC.veraltet(d));',
    'el.textContent = L("dataAsOf") + " " + fmtStand(d) + (alt ? " · " + L("outdated") : "");',
]


def renditen(site, s):
    s.anker(ANKER_RENDITEN)
    js = s.js
    T = js_texte(js_block(js, "const T = {"))
    defs = js_objekte(js_block(js, "const COUNTRIES = ["))
    cur_sym = js_texte(js_block(js, "const CUR_SYM = {"))
    daily = re.findall(r'"(\w+)"', js_block(js, "const DAILY = ["))
    year0 = int(re.search(r"\bYEAR0 = (\d{4})", js).group(1))
    old_day, old_month = (int(x) for x in re.search(r"const OLD_DAY = (\d+), OLD_MONTH = (\d+);", js).groups())
    ry = js_block(js, "const RY = {")
    latest = {k: {"date": d_, "yield": float(y)} for k, d_, y in
              re.findall(r'(\w+):\s*\{\s*date:\s*"([^"]+)",\s*yield:\s*(-?[\d.]+)\s*\}', js_block(ry, "latest: {"))}
    annual = {k: {int(y): js_wert(v) for y, v in re.findall(r"(\d{4}):\s*(-?\d+(?:\.\d+)?)", body)}
              for k, body in re.findall(r"(\w+):\s*\{([^{}]*)\}", js_block(ry, "annual: {"))}
    if len(defs) < 2 or not annual:
        raise ValueError("Länder oder Jahreswerte im Seitenskript nicht gefunden")
    D = lade(site, "renditen.json")
    reihen_mischen(defs, latest, annual, D.get("countries"))
    ref = juengstes_taeglich(defs, latest, daily)
    if not ref:
        raise ValueError("kein Stand in renditen.json")

    zeilen = []
    for c in defs:
        r = reihen_kennzahlen(c, latest, annual, ref, old_day, old_month, T)
        cur = c["cur"]
        sym = f' <span class="sym">{cur_sym[cur]}</span>' if cur_sym.get(cur) else ""
        akt = (zahl(r["current"], 2) + NBSP + "%" if r["current"] is not None else "–") + \
            (f'<small class="cur-m">{esc(r["standTxt"])}</small>' if r["standTxt"] is not None else "")
        zeilen.append(f'<tr>\n      <th scope="row"><i class="tag" style="background:{c["color"]}"></i>{esc(r["name"])}'
                      f'<small class="cur-m">{cur}</small></th><td class="num">{akt}</td>\n'
                      f'      <td class="cur">{cur}{sym}</td>\n      {zelle_stand(r, T, "num stand")}\n    </tr>')
    s.inner("#rtable", "".join(zeilen))

    # Einordnung „Was das für deine Anleihe heißt“: Deutschland gegen die eigene Geschichte
    de = next((c for c in defs if c["key"] == "de"), None)
    if de:
        r, l = reihen_kennzahlen(de, latest, annual, ref, old_day, old_month, T), latest.get("de") or {}
        if r["current"] is not None:
            s.text("#e-de", zahl(r["current"], 2), muss=False)
            s.text("#e-akt", zahl(r["current"], 2) + NBSP + "%", muss=False)
            s.text("#e-akt-d", ("Tageswert " if ist_tag(l.get("date")) else "Monatswert ") + fmt_stand(l.get("date")), muss=False)
        if r["avg"] is not None:
            s.text("#e-avg", zahl(r["avg"], 2) + NBSP + "%", muss=False)
            s.text("#e-avg2", zahl(r["avg"], 2), muss=False)
        if r["high"] is not None:
            s.text("#e-hoch", f'{zahl(r["high"], 2)}{NBSP}% ({r["hiYr"]})', muss=False)
        if r["low"] is not None:
            s.text("#e-tief", f'{zahl(r["low"], 2)}{NBSP}% ({r["loYr"]})', muss=False)
        if r["current"] is not None and r["avg"] is not None:
            s.text("#e-lage", "unter" if r["current"] < r["avg"] else "über", muss=False)

    s.text("#eyebrow-renditen", f'{T["eyebrow"]} · {year0} – {int(ref[:4])} · {T["asOf"]} {fmt_stand(ref)}')
    alt = ist_tag(ref) and veraltet(ref)
    daten_stand_veraltet(s, f'{T["dataAsOf"]} {fmt_stand(ref)}' + (f' · {T["outdated"]}' if alt else ""), ref)
    return fmt_stand(ref)


# ---------- unternehmensanleihen.html ----------
ANKER_UNTERNEHMEN = [
    'if (c.pubNextDay && l && isDay(l.date) && isFuture(l.date)) l = { date: prevWeekday(l.date), yield: l.yield };',
    'if (l && (isDay(l.date) || isMonth(l.date)) && !isFuture(l.date) && typeof l.yield === "number" && isFinite(l.yield)) D.latest[c.key] = { date: l.date, yield: l.yield };',
    'if (/^\\d{4}$/.test(yr) && typeof v === "number" && isFinite(v)) an[yr] = v;',
    '.then(d => { if (d) mergeData(CHARTS.unternehmen, d.series); rerender("unternehmen.json"); })',
    'const RC = { range: {}, monthly: {}, latest: {}, annual: {} };',
    'do { t.setUTCDate(t.getUTCDate() - 1); } while (t.getUTCDay() === 0 || t.getUTCDay() === 6);',
    'if (l && isDay(l.date) && (best === null || l.date > best)) best = l.date;',
    'return best || newestDate(ch);',
    'if (isMonth(d)) return d.slice(5, 7) + "." + d.slice(0, 4);',
    'const iso = isMonth(d) ? d + "-15" : d;',
    'if (hi === null || v > ann[hi]) hi = yr;',
    'if (lo === null || v < ann[lo]) lo = yr;',
    'const avg = years.length ? sum / years.length : null;',
    'const old = hasDate && ageDays(latest.date, ref) > (isMonth(latest.date) ? OLD_MONTH : OLD_DAY);',
    'c, name: L(c.tblKey || c.nameKey),',
    'cur: c.cur, rating: c.rating || L(c.ratingKey), mat: L(c.matKey)',
    'function curYieldCell(r) { return `<td class="num">${r.current !== null ? fmt(r.current, 2) + "\\u00A0%" : "–"}</td>`; }',
    'const stand = r.standTxt !== null ? (r.old ? `<span class="old">${MC.esc(r.standTxt)} ${L("standOld")}</span>` : MC.esc(r.standTxt)) : "–";',
    'return `<td class="num">${stand}</td>',
    '<td class="num">${r.high !== null ? `${fmt(r.high, 2)}\\u00A0% (${r.hiYr})` : "–"}</td>',
    '<td class="num">${r.low !== null ? `${fmt(r.low, 2)}\\u00A0% (${r.loYr})` : "–"}</td>',
    '<td class="num">${r.avg !== null ? fmt(r.avg, 2) + "\\u00A0%" : "–"}</td>`;',
    '<th scope="row"><i class="tag" style="background:${r.c.color}"></i>${MC.esc(r.name)}</th>${curYieldCell(r)}',
    '<td class="cur">${r.cur}${CUR_SYM[r.cur] ? ` <span class="sym">${CUR_SYM[r.cur]}</span>` : ""}</td>',
    '<td class="txt">${MC.esc(r.rating)}</td>',
    '<td class="txt">${MC.esc(r.mat)}</td>',
    'el.textContent = `${L(titleKey)} · ${YEAR0} – ${Number(String(nd).slice(0, 4))} · ${L("asOf")} ${fmtStand(nd)}`;',
    'setEyebrow("eyebrow-unternehmen", "corpEyebrow", CHARTS.unternehmen);',
    'const alt = isDay(d) && MC.veraltet ? MC.veraltet(d) : false;',
    'el.textContent = L("dataAsOf") + " " + fmtStand(d) + (alt ? " · " + L("outdated") : "");',
]


def unternehmensanleihen(site, s):
    s.anker(ANKER_UNTERNEHMEN)
    js = s.js
    T = js_texte(js_block(js, "const T = {"))
    defs = js_objekte(js_block(js, "const CORP = ["))
    cur_sym = js_texte(js_block(js, "const CUR_SYM = {"))
    daily = re.findall(r'"(\w+)"', js_block(js, "const CORP_DAILY = ["))
    year0 = int(re.search(r"\bYEAR0 = (\d{4})", js).group(1))
    old_day, old_month = (int(x) for x in re.search(r"const OLD_DAY = (\d+), OLD_MONTH = (\d+);", js).groups())
    if len(defs) < 2:
        raise ValueError("Renditereihen im Seitenskript nicht gefunden")
    latest, annual = {}, {}
    D = lade(site, "unternehmen.json")
    reihen_mischen(defs, latest, annual, D.get("series"), naechster_tag=True)
    ref = juengstes_taeglich(defs, latest, daily)
    if not ref:
        raise ValueError("kein Stand in unternehmen.json")

    zeilen = []
    for c in defs:
        r = reihen_kennzahlen(c, latest, annual, ref, old_day, old_month, T)
        cur = c["cur"]
        sym = f' <span class="sym">{cur_sym[cur]}</span>' if cur_sym.get(cur) else ""
        rating = c.get("rating") or T.get(c.get("ratingKey"), c.get("ratingKey"))
        akt = zahl(r["current"], 2) + NBSP + "%" if r["current"] is not None else "–"
        zeilen.append(f'<tr>\n      <th scope="row"><i class="tag" style="background:{c["color"]}"></i>{esc(r["name"])}</th>'
                      f'<td class="num">{akt}</td>\n'
                      f'      <td class="cur">{cur}{sym}</td>\n'
                      f'      <td class="txt">{esc(rating)}</td>\n'
                      f'      <td class="txt">{esc(T.get(c["matKey"], c["matKey"]))}</td>\n'
                      f'      {zelle_stand(r, T, "num")}\n    </tr>')
    s.inner("#ctable", "".join(zeilen))
    s.text("#eyebrow-unternehmen", f'{T["corpEyebrow"]} · {year0} – {int(ref[:4])} · {T["asOf"]} {fmt_stand(ref)}')
    alt = ist_tag(ref) and veraltet(ref)
    daten_stand_veraltet(s, f'{T["dataAsOf"]} {fmt_stand(ref)}' + (f' · {T["outdated"]}' if alt else ""), ref)
    return fmt_stand(ref)


# ---------- zinskurve.html ----------
ANKER_ZINSKURVE = [
    'const vz = v => (v > 0 ? "+" : v < 0 ? "−" : "±") + fmt(Math.abs(v), 2);',
    'const stufe = v => v < 0 ? ["invers", "invers"] : v < 0.3 ? ["flach", "flach"] : v <= 1 ? ["normal", "normal"] : ["steil", "steil"];',
    'const ab = h[2] - h[1], st = stufe(ab);',
    'el.querySelector(".v").textContent = vz(ab);',
    'const s = el.querySelector(".s"); s.textContent = st[0]; s.className = "hk-s s " + st[1];',
    'el.querySelector(".d").textContent = `10 Jahre ${fmt(h[2], 2)}\\u00A0% · 2 Jahre ${fmt(h[1], 2)}\\u00A0% · Stand ${deDatum(h[0])}`;',
    'const reihen = ["DE", "US"].filter(l => d.monate && d.monate[l] && d.monate[l].length);',
    'const staende = reihen.map(l => d.stand && d.stand[l]).filter(Boolean).sort();',
    'document.getElementById("eyebrow-zk").textContent = `10 Jahre minus 2 Jahre · Monatsdurchschnitte · ${m0.slice(0, 4)} – ${m1.slice(0, 4)} · Stand: ${deDatum(st)}`;',
    'if (el) { el.textContent = "Daten-Stand: " + deDatum(st); el.classList.toggle("stale", !!(MC.veraltet && MC.veraltet(st))); }',
    "reihe.forEach(m => { if (m[2] - m[1] < 0) { if (cur) { cur[1] = m[0]; cur[2]++; } else cur = [m[0], m[0], 1]; } else if (cur) { out.push(cur); cur = null; } });",
    'return out.filter(p => p[2] >= 3);',
    'if (de && de.length) setText("t-invers", fmt(Math.round(100 * de.filter(m => m[2] - m[1] < 0).length / de.length), 0));',
    'const lang = ph.reduce((a, p) => Math.max(a, p[2]), 0);',
    'if (lang) setText("t-lang", String(lang));',
    'const drin = NBER.find(r => p[0] >= r[0] && p[0] <= r[1]);',
    'const nach = NBER.find(r => r[0] > p[0]);',
    'const t = drin ? [`mitten in der Rezession ab ${mmjj(drin[0])}`, "ja"] : nach ? [`ja – ab ${mmjj(nach[0])}`, "ja"] : ["bisher nein", "nein"];',
    'return `<tr><td>${mmjj(p[0])} – ${mmjj(p[1])}</td><td class="${t[1]}">${t[0]}</td></tr>`;',
    'const mmjj = m => `${m.slice(5, 7)}/${m.slice(0, 4)}`;',
    'MC.load("zinskurve.json").then(function (d) { kacheln(d); chart(d); texte(d); })',
]


def zinskurve(site, s):
    s.anker(ANKER_ZINSKURVE)
    nber = re.findall(r'\["(\d{4}-\d{2})",\s*"(\d{4}-\d{2})"\]', js_block(s.js, "const NBER = ["))
    if not nber:
        raise ValueError("NBER-Liste im Seitenskript nicht gefunden")
    d = lade(site, "zinskurve.json")
    heute_ = d.get("heute") or {}
    for land in ("DE", "US"):
        h = heute_.get(land)
        sel = f'.hk[data-land="{land}"]'
        if not h or not s.finde(sel):
            continue
        ab = h[2] - h[1]
        st = "invers" if ab < 0 else "flach" if ab < 0.3 else "normal" if ab <= 1 else "steil"
        s.text(sel + " .v", vz(ab, 2))
        s.text(sel + " .s", st)
        s.attr(sel + " .s", "class", "hk-s s " + st)
        s.text(sel + " .d", f"10 Jahre {zahl(h[2], 2)}{NBSP}% · 2 Jahre {zahl(h[1], 2)}{NBSP}% · Stand {datum(h[0])}")

    monate = d.get("monate") or {}
    reihen = [l for l in ("DE", "US") if monate.get(l)]
    if not reihen:
        raise ValueError("keine Monatswerte in zinskurve.json")
    alle = [m[0] for l in reihen for m in monate[l]]
    m0, m1 = min(alle), max(alle)
    staende = sorted(x for x in ((d.get("stand") or {}).get(l) for l in reihen) if x)
    stand = None
    if staende:
        stand = staende[-1]
        s.text("#eyebrow-zk", f"10 Jahre minus 2 Jahre · Monatsdurchschnitte · {m0[:4]} – {m1[:4]} · Stand: {datum(stand)}")
        daten_stand_veraltet(s, "Daten-Stand: " + datum(stand), stand)

    de, us = monate.get("DE"), monate.get("US")
    if de:
        s.text("#t-invers", zahl(js_round(100 * sum(1 for m in de if m[2] - m[1] < 0) / len(de)), 0), muss=False)
    if us:
        phasen, cur = [], None
        for m in us:
            if m[2] - m[1] < 0:
                if cur:
                    cur[1] = m[0]
                    cur[2] += 1
                else:
                    cur = [m[0], m[0], 1]
            elif cur:
                phasen.append(cur)
                cur = None
        if cur:
            phasen.append(cur)
        phasen = [p for p in phasen if p[2] >= 3]
        lang = max([p[2] for p in phasen] + [0])
        if lang:
            s.text("#t-lang", str(lang), muss=False)
        if phasen and s.finde("#rz-tab tbody"):
            def mmjj(m):
                return f"{m[5:7]}/{m[:4]}"
            zeilen = []
            for p in phasen:
                drin = next((r for r in nber if r[0] <= p[0] <= r[1]), None)
                nach = next((r for r in nber if r[0] > p[0]), None)
                t = ([f"mitten in der Rezession ab {mmjj(drin[0])}", "ja"] if drin else
                     [f"ja – ab {mmjj(nach[0])}", "ja"] if nach else ["bisher nein", "nein"])
                zeilen.append(f'<tr><td>{mmjj(p[0])} – {mmjj(p[1])}</td><td class="{t[1]}">{t[0]}</td></tr>')
            s.inner("#rz-tab tbody", "".join(zeilen))
    if not stand:
        raise ValueError("kein Stand in zinskurve.json")
    return datum(stand)


# ---------- realzins.html ----------
ANKER_REALZINS = [
    'const C = { zins: "#157C00", infl: "#CF7430", plus: "#157C00", minus: "#A2561C",',
    'const STEUER = 0.26375;',
    'const MON = ["Januar", "Februar", "März", "April", "Mai", "Juni", "Juli", "August", "September", "Oktober", "November", "Dezember"];',
    'const vz = (v, d) => (v > 0 ? "+" : v < 0 ? "−" : "±") + fmt(Math.abs(v), d);',
    'const monLang = m => `${MON[+m.slice(5, 7) - 1]} ${m.slice(0, 4)}`;',
    'setT("h-zins", ""); document.getElementById("h-zins").innerHTML = `${fmt(z, 2)}<small>%</small>`;',
    'setT("h-zins-d", `Rendite, nominal · Tageswert ${deDatum(h.zins10[0])}`);',
    '["s-zins", "s-zins2"].forEach(id => setT(id, fmt(z, 2)));',
    'setT("s-netto", fmt(z * (1 - STEUER), 2)); setT("st-z", `${fmt(z, 2)}\u00a0%`); setT("st-st", `−${fmt(z * STEUER, 2)}`);',
    'const brutto = 50000 * z / 100, steuer = Math.max(0, brutto - 1000) * STEUER;',
    'setT("s-brutto", fmt(brutto, 0)); setT("s-steuer", fmt(steuer, 0)); setT("s-netto-eur", fmt(brutto - steuer, 0));',
    'document.getElementById("h-vpi").innerHTML = `${fmt(i, 1)}<small>%</small>`;',
    'setT("h-vpi-d", `Verbraucherpreise Deutschland, ${monLang(h.vpi[0])} gegen Vorjahr`);',
    'setT("s-vpi", fmt(i, 1)); setT("st-i", `−${fmt(i, 2)}`); setT("s-verlust", fmt(50000 * i / 100, 0));',
    'setT("m-vpi", fmt(i, 1)); setT("m-noetig", fmt(Math.max(0, i) / (1 - STEUER), 2));',
    'const real = h.zins10[1] - h.vpi[1], netto = h.zins10[1] * (1 - STEUER) - h.vpi[1];',
    'el.innerHTML = `${vz(real, 1)}<small>Prozentpunkte</small>`; el.className = "hk-v " + (real > 0 ? "plus" : real < 0 ? "minus" : "");',
    'const kk = document.getElementById("h-real-k"); if (kk) kk.style.setProperty("--c", real < 0 ? C.minus : C.plus);',
    'document.getElementById("h-real-d").innerHTML = `Zins minus Inflation · nach Abgeltungsteuer <b>${vz(netto, 1)}</b>`;',
    'const st = document.getElementById("st-r"); st.textContent = vz(netto, 2); st.className = "num " + (netto > 0 ? "plus" : netto < 0 ? "minus" : "");',
    'const l = h.linker.find(x => x.faellig.startsWith("2033")) || h.linker[0];',
    'document.getElementById("h-be").innerHTML = `${fmt(l.breakeven, 1)}<small>% Inflation</small>`;',
    'setT("h-be-d", `pro Jahr bis ${l.faellig.slice(0, 4)} im Euroraum, abgeleitet aus der inflationsindexierten Bundesanleihe`);',
    'setT("e-nom", fmt(l.nominal, 2)); setT("e-real", fmt(l.real, 2)); setT("e-be", fmt(l.breakeven, 2));',
    'if (tb) tb.innerHTML = h.linker.map(x => `<tr><td>${x.faellig.slice(0, 4)}<small>${(k => k ? "Kupon " + MC.esc(k[1].replace(/\\s/, "\\u00A0")) : "")(x.name.match(/(\\d+,\\d+\\s%)/))}</small></td><td class="num">${fmt(x.real, 2)}\u00a0%</td>` +',
    '`<td class="num">${x.nominal == null ? "–" : fmt(x.nominal, 2) + "\u00a0%"}</td><td class="num${x.breakeven == null ? "" : x.breakeven >= 0 ? " plus" : " minus"}">${x.breakeven == null ? "–" : fmt(x.breakeven, 2) + "\u00a0%"}</td></tr>`).join("");',
    'const J = (d.jahre || []).filter(j => j[2] != null);',
    'J.forEach(j => { const k = Math.floor(j[0] / 10) * 10; (dek[k] = dek[k] || []).push(j); });',
    'const r = dek[k], n = r.length, z = r.reduce((a, j) => a + j[1], 0) / n, i = r.reduce((a, j) => a + j[2], 0) / n, re = z - i;',
    'const offen = lauf && r[r.length - 1][0] === lauf && n < 10;',
    'return `<tr><td>${k}er${offen ? `<small>bis ${lauf}</small>` : ""}</td><td class="num">${fmt(z, 1)}\u00a0%</td><td class="num">${fmt(i, 1)}\u00a0%</td><td class="num${re >= 0 ? " plus" : " minus"}">${vz(re, 1)}</td></tr>`;',
    'document.querySelectorAll("[data-dek]").forEach(el => { const r = dek[+el.dataset.dek]; if (r) el.textContent = fmt(r.reduce((a, j) => a + j[1] - j[2], 0) / r.length, 1); });',
    'const min = J.reduce((a, j) => (j[1] - j[2] < a[1] - a[2] ? j : a));',
    'setT("t-min", vz(min[1] - min[2], 1));',
    'setT("t-schnitt", vz(J.reduce((a, j) => a + j[1] - j[2], 0) / J.length, 1));',
    'let DATA = null, MODUS = "jahre", BREITE = 0;',
    'const P = jahre ? (d.jahre || []).map(j => ({ k: String(j[0]), z: j[1], i: j[2] }))',
    'setT("eyebrow-rz", `10-jährige Bundesanleihe und Verbraucherpreise · ${jahre ? "Jahreswerte" : "Monatsdurchschnitte"} · ${jahr(P[0].k)} – ${jahr(P[n - 1].k)}${stand ? ` · Stand: ${deDatum(stand)}` : ""}`);',
    'const tagHinweis = jahre && hz && d.laufend && +lz.k === d.laufend.jahr ? ` Die Kachel „Bund 10 Jahre“ oben zeigt den Tageswert (${fmt(hz[1], 2)} % am ${deDatum(hz[0])}), das Schaubild den Jahresdurchschnitt (${lz.k} bisher ${fmt(lz.z, 2)} %).` : "";',
    '? "Bund 10 Jahre: Jahresdurchschnitt der Rendite; Inflation: Jahresteuerung des Verbraucherpreisindex (bis 1991 früheres Bundesgebiet); das laufende Jahr bis zum letzten veröffentlichten Monat. Realzins = Differenz beider Werte in Prozentpunkten." + tagHinweis',
    'if (el) { el.textContent = "Daten-Stand: " + deDatum(stand) + (st.vpi ? ` · Preise ${monLang(st.vpi)}` : ""); el.classList.toggle("stale", !!(MC.veraltet && MC.veraltet(stand))); }',
    'MC.load("realzins.json").then(function (d) { DATA = d; kacheln(d); charts(d); })',
]
REALZINS_HINWEIS = ("Bund 10 Jahre: Jahresdurchschnitt der Rendite; Inflation: Jahresteuerung des Verbraucherpreisindex "
                    "(bis 1991 früheres Bundesgebiet); das laufende Jahr bis zum letzten veröffentlichten Monat. "
                    "Realzins = Differenz beider Werte in Prozentpunkten.")


def realzins(site, s):
    s.anker(ANKER_REALZINS)
    steuer = 0.26375
    d = lade(site, "realzins.json")
    h = d.get("heute") or {}
    z = i = None
    if h.get("zins10"):
        z = h["zins10"][1]
        s.inner("#h-zins", f"{zahl(z, 2)}<small>%</small>")
        s.text("#h-zins-d", f"Rendite, nominal · Tageswert {datum(h['zins10'][0])}", muss=False)
        for id_ in ("s-zins", "s-zins2"):
            s.text("#" + id_, zahl(z, 2), muss=False)
        s.text("#s-netto", zahl(z * (1 - steuer), 2), muss=False)
        s.text("#st-z", f"{zahl(z, 2)}{NBSP}%", muss=False)
        s.text("#st-st", f"{MINUS}{zahl(z * steuer, 2)}", muss=False)
        brutto = 50000 * z / 100
        st_ = max(0, brutto - 1000) * steuer
        s.text("#s-brutto", zahl(brutto, 0), muss=False)
        s.text("#s-steuer", zahl(st_, 0), muss=False)
        s.text("#s-netto-eur", zahl(brutto - st_, 0), muss=False)
    if h.get("vpi"):
        i = h["vpi"][1]
        s.inner("#h-vpi", f"{zahl(i, 1)}<small>%</small>")
        s.text("#h-vpi-d", f"Verbraucherpreise Deutschland, {mon_lang(h['vpi'][0])} gegen Vorjahr", muss=False)
        s.text("#s-vpi", zahl(i, 1), muss=False)
        s.text("#st-i", f"{MINUS}{zahl(i, 2)}", muss=False)
        s.text("#s-verlust", zahl(50000 * i / 100, 0), muss=False)
        s.text("#m-vpi", zahl(i, 1), muss=False)
        s.text("#m-noetig", zahl(max(0, i) / (1 - steuer), 2), muss=False)
    if h.get("zins10") and h.get("vpi"):
        real, netto = z - i, z * (1 - steuer) - i
        s.inner("#h-real", f"{vz(real, 1)}<small>Prozentpunkte</small>")
        s.attr("#h-real", "class", "hk-v " + ("plus" if real > 0 else "minus" if real < 0 else ""))
        if s.finde("#h-real-k"):
            s.stil("#h-real-k", "--c", "#A2561C" if real < 0 else "#157C00")
        s.inner("#h-real-d", f"Zins minus Inflation · nach Abgeltungsteuer <b>{vz(netto, 1)}</b>")
        s.text("#st-r", vz(netto, 2))
        s.attr("#st-r", "class", "num " + ("plus" if netto > 0 else "minus" if netto < 0 else ""))
    linker = h.get("linker") or []
    if linker:
        l = next((x for x in linker if str(x.get("faellig", "")).startswith("2033")), linker[0])
        if l.get("breakeven") is not None:
            s.inner("#h-be", f"{zahl(l['breakeven'], 1)}<small>% Inflation</small>")
            s.text("#h-be-d", f"pro Jahr bis {l['faellig'][:4]} im Euroraum, abgeleitet aus der inflationsindexierten Bundesanleihe", muss=False)
            s.text("#e-nom", zahl(l.get("nominal"), 2), muss=False)
            s.text("#e-real", zahl(l.get("real"), 2), muss=False)
            s.text("#e-be", zahl(l["breakeven"], 2), muss=False)
        if s.finde("#linker-tab tbody"):
            zeilen = []
            for x in linker:
                k = re.search(r"(\d+,\d+\s%)", x["name"])
                kupon = "Kupon " + esc(re.sub(r"\s", NBSP, k.group(1), count=1)) if k else ""
                be = x.get("breakeven")
                zeilen.append(f'<tr><td>{x["faellig"][:4]}<small>{kupon}</small></td><td class="num">{zahl(x.get("real"), 2)}{NBSP}%</td>'
                              f'<td class="num">{"–" if x.get("nominal") is None else zahl(x["nominal"], 2) + NBSP + "%"}</td>'
                              f'<td class="num{"" if be is None else " plus" if be >= 0 else " minus"}">'
                              f'{"–" if be is None else zahl(be, 2) + NBSP + "%"}</td></tr>')
            s.inner("#linker-tab tbody", "".join(zeilen))

    def n0(v):   # JavaScript rechnet „a + null“ als a + 0
        return 0 if v is None else v

    J = [j for j in (d.get("jahre") or []) if j[2] is not None]
    if J:
        dek = {}
        for j in J:
            dek.setdefault(math.floor(j[0] / 10) * 10, []).append(j)
        lauf = (d.get("laufend") or {}).get("jahr")
        if s.finde("#dekaden tbody"):
            zeilen = []
            for k in sorted(dek, key=str):
                r = dek[k]
                n = len(r)
                sz = si = 0
                for j in r:
                    sz += n0(j[1])
                for j in r:
                    si += j[2]
                zz, ii = sz / n, si / n
                re_ = zz - ii
                offen = bool(lauf) and r[-1][0] == lauf and n < 10
                zeilen.append(f'<tr><td>{k}er{f"<small>bis {lauf}</small>" if offen else ""}</td>'
                              f'<td class="num">{zahl(zz, 1)}{NBSP}%</td><td class="num">{zahl(ii, 1)}{NBSP}%</td>'
                              f'<td class="num{" plus" if re_ >= 0 else " minus"}">{vz(re_, 1)}</td></tr>')
            s.inner("#dekaden tbody", "".join(zeilen))
        for el in s.finde("[data-dek]"):
            r = dek.get(int(el.attrs["data-dek"])) if re.fullmatch(r"\d+", el.attrs.get("data-dek", "")) else None
            if r:
                summe = 0
                for j in r:
                    summe = summe + n0(j[1]) - j[2]
                s.text(f'[data-dek="{el.attrs["data-dek"]}"]', zahl(summe / len(r), 1), alle=True)
        mn = J[0]
        for j in J[1:]:
            if n0(j[1]) - j[2] < n0(mn[1]) - mn[2]:
                mn = j
        s.text("#t-min", vz(n0(mn[1]) - mn[2], 1), muss=False)
        summe = 0
        for j in J:
            summe = summe + n0(j[1]) - j[2]
        s.text("#t-schnitt", vz(summe / len(J), 1), muss=False)

    # charts(): Kopfzeile, Hinweis unter dem Schaubild, Fußzeile (Zeitraster „Jahre“ wie beim Laden der Seite)
    P = [(str(j[0]), j[1], j[2]) for j in (d.get("jahre") or [])]
    if not P:
        raise ValueError("keine Jahreswerte in realzins.json")
    st = d.get("stand") or {}
    stand = st.get("zins") or ""
    s.text("#eyebrow-rz", f"10-jährige Bundesanleihe und Verbraucherpreise · Jahreswerte · {int(P[0][0][:4])} – {int(P[-1][0][:4])}"
           + (f" · Stand: {datum(stand)}" if stand else ""))
    hz, lz, lauf = h.get("zins10"), P[-1], (d.get("laufend") or {}).get("jahr")
    hinweis = (f" Die Kachel „Bund 10 Jahre“ oben zeigt den Tageswert ({zahl(hz[1], 2)} % am {datum(hz[0])}), "
               f"das Schaubild den Jahresdurchschnitt ({lz[0]} bisher {zahl(lz[1], 2)} %).") \
        if hz and d.get("laufend") and int(lz[0]) == lauf else ""
    s.text("#note-rz", REALZINS_HINWEIS + hinweis)
    if not stand:
        raise ValueError("kein Stand in realzins.json")
    daten_stand_veraltet(s, "Daten-Stand: " + datum(stand) + (f" · Preise {mon_lang(st['vpi'])}" if st.get("vpi") else ""), stand)
    return datum(stand) + (f", Preise {mon_lang(st['vpi'])}" if st.get("vpi") else "")


# ---------- risikoaufschlaege.html ----------
ANKER_RISIKO = [
    'const EU = { IT: { name: "Italien", color: "#CF7430" }, ES: { name: "Spanien", color: "#A9A7A0" }, FR: { name: "Frankreich", color: "#157C00" } };',
    'const MON = ["Januar", "Februar", "März", "April", "Mai", "Juni", "Juli", "August", "September", "Oktober", "November", "Dezember"];',
    'const vz = (v, d) => (v > 0 ? "+" : v < 0 ? "−" : "±") + fmt(Math.abs(v), d);',
    'const monLang = m => `${MON[+m.slice(5, 7) - 1]} ${m.slice(0, 4)}`;',
    'if (!h || !el || !letzte) continue;',
    'const de = h.rendite - h.aufschlag;',
    'el.querySelector(".v").textContent = vz(h.aufschlag, 2);',
    'el.querySelector(".d").innerHTML = `<b>${fmt(h.rendite, 2)}&nbsp;%</b> gegen Bund ${fmt(de, 2)}&nbsp;% · Monatsdurchschnitt ${monLang(h.monat)}`;',
    'setT("k-it", fmt(it.aufschlag, 2));',
    'setT("bsp-it", `Italien ${fmt(it.rendite, 2)}\\u00A0%, Deutschland ${fmt(it.rendite - it.aufschlag, 2)}\\u00A0%: 10.000\\u00A0€ bringen in Italien ${fmt(Math.round(it.aufschlag * 100), 0)}\\u00A0€ im Jahr mehr.`);',
    'const ok = (m, a, b) => m[a] != null && m[b] != null && m[a] > m[b];',
    'for (let i = monate.length - 1; i >= 0 && ok(monate[i], 4, 3); i--) seit = monate[i][0];',
    'const grIt = ok(letzte, 2, 6), teile = [];',
    'if (seit) teile.push(`<strong>Frankreich zahlt seit ${monLang(seit)} mehr als Spanien</strong>`);',
    'if (grIt) teile.push("Griechenland weniger als Italien");',
    'if (el) el.innerHTML = teile.length ? `Stand ${monLang(letzte[0])}: ${teile.join(", ")}. 2012 war es umgekehrt.` : `Stand ${monLang(letzte[0])}: Die Rangliste rechts zeigt die Reihenfolge von heute – 2012 lagen Griechenland, Portugal, Spanien und Italien vorn.`;',
    'const max = Math.max(...heute.map(h => h.aufschlag), 0.01), stand = L.monate && letzte ? letzte[0] : heute[0].monat;',
    'const w = Math.max(2, Math.round(Math.max(0, h.aufschlag) / max * 88)), c = EU[h.code] ? `;--c:${EU[h.code].color}` : "";',
    'return `<span class="rl-l">${MC.esc(h.name)}${h.monat !== stand ? `<small>${monLang(h.monat)}</small>` : ""}</span><span class="rl-bahn"><span class="rl-bar" style="--w:${w}%${c}"></span><span class="rl-w" style="--w:${w}%">${vz(h.aufschlag, 2)}</span></span>`;',
    '}).join("") + `<span class="rl-null">Deutschland = 0, der Maßstab</span>`;',
    'rl.setAttribute("aria-label", `Rangliste der Euro-Staaten nach Aufschlag gegen Deutschland, ${monLang(stand)}: ` + heute.map(h => `${h.name} ${fmt(h.aufschlag, 2)} Prozentpunkte`).join(", ") + ".");',
    'document.getElementById("rl-f").innerHTML = `10-jährige Staatsanleihen, ${monLang(stand)}, Prozentpunkte über Deutschland. ',
    'const schnitt = um.reduce((a, m) => a + m[1], 0) / um.length;',
    'setT("us-v", vz(uh[1], 2)); setT("k-us", fmt(uh[1], 2));',
    'document.getElementById("us-d").innerHTML = `<b>${fmt(uh[2], 2)}&nbsp;%</b> gegen US-Staatsanleihe ${fmt(uh[3], 2)}&nbsp;% · ${monLang(uh[0])} · Durchschnitt seit ${um[0][0].slice(0, 4)}: <b>${fmt(schnitt, 1)}</b>`;',
    'setT("eyebrow-eu", `Staatsanleihen 10 Jahre gegen Deutschland · Monatswerte · ${M[0][0].slice(0, 4)} – ${M[M.length - 1][0].slice(0, 4)}${st ? ` · Stand: ${monLang(st)}` : ""}`);',
    'el.textContent = "Daten-Stand: " + [st.us ? `USA ${monLang(st.us)}` : "", st.laender ? `Länder ${monLang(st.laender)}` : ""].filter(Boolean).join(" · ");',
    'MC.load("risikoaufschlaege.json").then(function (d) { DATA = d; kacheln(d); charts(d); })',
]


def risikoaufschlaege(site, s):
    s.anker(ANKER_RISIKO)
    eu = {"IT": "#CF7430", "ES": "#A9A7A0", "FR": "#157C00"}
    d = lade(site, "risikoaufschlaege.json")
    L = d.get("laender") or {}
    heute_, monate = L.get("heute") or [], L.get("monate") or []
    by_code = {h["code"]: h for h in heute_}
    letzte = monate[-1] if monate else None
    for k in eu:
        h, sel = by_code.get(k), f'.hk[data-land="{k}"]'
        if not h or not letzte or not s.finde(sel):
            continue
        de = h["rendite"] - h["aufschlag"]
        s.text(sel + " .v", vz(h["aufschlag"], 2))
        s.inner(sel + " .d", f"<b>{zahl(h['rendite'], 2)}&nbsp;%</b> gegen Bund {zahl(de, 2)}&nbsp;% · Monatsdurchschnitt {mon_lang(h['monat'])}")
    it = by_code.get("IT")
    if it:
        s.text("#k-it", zahl(it["aufschlag"], 2), muss=False)
        s.text("#bsp-it", f"Italien {zahl(it['rendite'], 2)}{NBSP}%, Deutschland {zahl(it['rendite'] - it['aufschlag'], 2)}{NBSP}%: "
               f"10.000{NBSP}€ bringen in Italien {zahl(js_round(it['aufschlag'] * 100), 0)}{NBSP}€ im Jahr mehr.", muss=False)
    if monate and letzte:
        def ok(m, a, b):
            return m[a] is not None and m[b] is not None and m[a] > m[b]
        seit = None
        i = len(monate) - 1
        while i >= 0 and ok(monate[i], 4, 3):
            seit = monate[i][0]
            i -= 1
        teile = []
        if seit:
            teile.append(f"<strong>Frankreich zahlt seit {mon_lang(seit)} mehr als Spanien</strong>")
        if ok(letzte, 2, 6):
            teile.append("Griechenland weniger als Italien")
        if s.finde("#rl-neu"):
            s.inner("#rl-neu", f"Stand {mon_lang(letzte[0])}: {', '.join(teile)}. 2012 war es umgekehrt." if teile else
                    f"Stand {mon_lang(letzte[0])}: Die Rangliste rechts zeigt die Reihenfolge von heute – 2012 lagen "
                    f"Griechenland, Portugal, Spanien und Italien vorn.")
    if heute_:
        mx = max([h["aufschlag"] for h in heute_] + [0.01])
        stand = letzte[0] if (L.get("monate") and letzte) else heute_[0]["monat"]
        teile = []
        for h in heute_:
            w = max(2, js_round(max(0, h["aufschlag"]) / mx * 88))
            c = f";--c:{eu[h['code']]}" if h["code"] in eu else ""
            klein = f"<small>{mon_lang(h['monat'])}</small>" if h["monat"] != stand else ""
            teile.append(f'<span class="rl-l">{esc(h["name"])}{klein}</span><span class="rl-bahn"><span class="rl-bar" '
                         f'style="--w:{w}%{c}"></span><span class="rl-w" style="--w:{w}%">{vz(h["aufschlag"], 2)}</span></span>')
        s.inner("#rangliste", "".join(teile) + '<span class="rl-null">Deutschland = 0, der Maßstab</span>')
        s.attr("#rangliste", "aria-label", f"Rangliste der Euro-Staaten nach Aufschlag gegen Deutschland, {mon_lang(stand)}: "
               + ", ".join(f"{h['name']} {zahl(h['aufschlag'], 2)} Prozentpunkte" for h in heute_) + ".")
        # Fußnote: nur den Monat ersetzen – der Linktext dahinter bleibt, wie er im Quell-HTML steht
        rl = s.finde("#rl-f")
        if not rl:
            raise ValueError("Element #rl-f fehlt")
        alt = s.html[rl[0].ia:rl[0].ib]
        m = re.match(r"10-jährige Staatsanleihen, [^,<]+, Prozentpunkte über Deutschland\. ", alt)
        if not m:
            raise ValueError("#rl-f hat einen unerwarteten Anfang")
        s.inner("#rl-f", f"10-jährige Staatsanleihen, {mon_lang(stand)}, Prozentpunkte über Deutschland. " + alt[m.end():])
    u = d.get("us") or {}
    um, uh = u.get("monate") or [], u.get("heute") or []
    if len(uh) >= 4 and um:
        summe = 0
        for m in um:
            summe += m[1]
        s.text("#us-v", vz(uh[1], 2), muss=False)
        s.text("#k-us", zahl(uh[1], 2), muss=False)
        s.inner("#us-d", f"<b>{zahl(uh[2], 2)}&nbsp;%</b> gegen US-Staatsanleihe {zahl(uh[3], 2)}&nbsp;% · {mon_lang(uh[0])} · "
                f"Durchschnitt seit {um[0][0][:4]}: <b>{zahl(summe / len(um), 1)}</b>")
    st = d.get("stand") or {}
    if monate:
        s.text("#eyebrow-eu", f"Staatsanleihen 10 Jahre gegen Deutschland · Monatswerte · {monate[0][0][:4]} – {monate[-1][0][:4]}"
               + (f" · Stand: {mon_lang(st['laender'])}" if st.get("laender") else ""), muss=False)
    if not (st.get("us") or st.get("laender")):
        raise ValueError("kein Stand in risikoaufschlaege.json")
    text = " · ".join(x for x in (f"USA {mon_lang(st['us'])}" if st.get("us") else "",
                                  f"Länder {mon_lang(st['laender'])}" if st.get("laender") else "") if x)
    s.text("#datastand", "Daten-Stand: " + text)
    return text


# ---------- langlaeufer.html ----------
ANKER_LANGLAEUFER = [
    'function parseWeekly(rawStr) { return rawStr.split(/\\s+/).filter(Boolean).map(t => { const [d, p] = t.split(":"); return ["20" + d, parseFloat(p)]; }); }',
    'o.weekly = w; o.priceDate = w[w.length - 1][0]; o.price = w[w.length - 1][1];',
    'const settle = addDays(b.priceDate, b.settleDays);',
    'return { settle, yld: yieldFromPrice(b, b.price, settle), years: MC.bond.yearsTo(b.maturity, settle) };',
    '{ key: "bund", isin: b.isin, coupon: 0, maturity: b.maturity, price: b.latest.price, yld: b.latest.yield, years: yearsTo(b.maturity, b.latest.date), high: b.high, low: b.low },',
    '{ key: "bund2", isin: c.isin, coupon: c.coupon, maturity: c.maturity, price: c.latest.price, yld: c.latest.yield, years: yearsTo(c.maturity, c.latest.date), high: c.high, low: c.low }',
    '["btp", "fr", "at", "us", "ms"].forEach(k => {',
    'rows.push({ key: k, isin: bd.isin, coupon: bd.coupon, maturity: bd.maturity, price: bd.price, yld: st.yld * 100, years: st.years, high: bd.high, low: bd.low });',
    'return rows.map(r => { Object.assign(r, KPI_META[r.key]); r.label = L(r.key); r.sinceHigh = (r.price / r.high.price - 1) * 100; return r; });',
    '`<tr><th scope="row"><i class="tag" style="background:${COLORS[r.key]}"></i>${MC.esc(r.label)}</th><td class="num">${fmt(r.yld, 2)}\\u00A0%</td>` +',
    '`<td class="num">${fmt(r.price, 2)}</td>` +',
    '`<td class="num">${fmt(r.sinceHigh, 0)}\\u00A0%<small>Hoch ${fmt(r.high.price, 2)} (${fmtDate(r.high.date).slice(3)})</small></td>` +',
    '`<td class="num">${fmt(r.years, 1)} ${L("years")}</td><td class="num">${fmtCoupon(r.coupon)}\\u00A0%</td><td class="num">${fmtDate(r.maturity)}</td>` +',
    '`<td class="emi" title="${MC.esc(r.art === "Staat" ? "Staatsanleihe" : "Unternehmensanleihe")}">${MC.esc(r.name)}</td>` +',
    '`<td class="isin"><a href="anleihe.html?isin=${r.isin}" title="Steckbrief: Kurs, Rendite, Kursverlauf, Handel und Stammdaten">${r.isin}</a></td><td class="txt">${r.cur}</td></tr>`);',
    'const ids = { bund: "b-spanne", bund2: "b2-spanne", btp: "t-spanne", fr: "fr-spanne", at: "at-spanne", us: "us-spanne", ms: "ms-spanne" };',
    'if (sp) sp.textContent = `Hoch ${fmt(r.high.price, 2)} (${fmtDate(r.high.date)}) · Tief ${fmt(r.low.price, 2)} (${fmtDate(r.low.date)})`;',
    'const alt = MC.veraltet ? MC.veraltet(BUND.latest.date) : false;',
    'el.textContent = `${L("dataAsOf")} ${fmtDate(BUND.latest.date)}${alt ? " · " + L("outdated") : ""}`;',
    'const neu = [BUND.latest.date, BUND2.latest && BUND2.latest.date, ...COUPON_BONDS.map(b => b.priceDate)].filter(Boolean).sort().pop();',
    'if (eb && neu) eb.textContent = `Kurse in % des Nennwerts · 2019 – ${neu.slice(0, 4)} · Stand: ${fmtDate(neu)}`;',
    'const pct = v => `${fmt(v, 1)}\\u00A0%`;',
    'const modDur = (b, price, date, yld) => { const st = addDays(date, b.settleDays || 2); return MC.bond.duration(b, yld != null ? yld / 100 : yieldFromPrice(b, price, st), st).modified; };',
    'if (typeof BUND.latest.yield === "number") set("bund-y", pct(BUND.latest.yield));',
    'set("bund-p", fmt(BUND.latest.price, 0));',
    'set("bund-d", fmt(modDur({ coupon: 0, freq: 1, maturity: BUND.maturity, settleDays: 2 }, BUND.latest.price, BUND.latest.date, BUND.latest.yield), 0));',
    'set("bund-minus", `${fmt((1 - BUND.latest.price / BUND.high.price) * 100, 0)}\\u00A0%`);',
    'set("bund2-hoch", fmt(BUND2.high.price, 0));',
    'set("bund2-minus", `${fmt((1 - BUND2.latest.price / BUND2.high.price) * 100, 0)}\\u00A0%`);',
    'set("btp-d", fmt(modDur(BTP, BTP.price, BTP.priceDate), 0));',
    'set("btp-p", fmt(BTP.price, 0));',
    'set("fr-p", fmt(FR.price, 0));',
    'const atY = yieldFromPrice(AT, AT.price, addDays(AT.priceDate, AT.settleDays)) * 100;',
    'set("at-y", pct(atY));',
    'set("at-d", fmt(modDur(AT, AT.price, AT.priceDate), 0)); set("at-d2", fmt(modDur(AT, AT.price, AT.priceDate), 0));',
    'const okPt = p => p && /^\\d{4}-\\d{2}-\\d{2}$/.test(p.date) && typeof p.price === "number" && isFinite(p.price);',
    'if (okPt(b.latest)) BUND.latest = { date: b.latest.date, price: b.latest.price, yield: typeof b.latest.yield === "number" ? b.latest.yield : null };',
    'if (okPt(b.high)) BUND.high = b.high;',
    'if (okPt(b.low)) BUND.low = b.low;',
    'if (okPt(c.latest)) BUND2.latest = { date: c.latest.date, price: c.latest.price, yield: typeof c.latest.yield === "number" ? c.latest.yield : null };',
    'if (okPt(c.high)) BUND2.high = c.high;',
    'if (okPt(c.low)) BUND2.low = c.low;',
    'if (!k || tage[k[2]] <= bd.priceDate) return null;',
    'return MC.verlauf(bd.isin, { ab: bd.priceDate }).catch(() => ({ t: [], k: [] })).then(v => {',
    'v.t.forEach((t, i) => { if (t > bd.priceDate && typeof v.k[i] === "number") neu.push([t, v.k[i]]); });',
    'if (!neu.length || neu[neu.length - 1][0] < tage[k[2]]) neu.push([tage[k[2]], k[0]]);',
    'bd.weekly = bd.weekly.concat(neu.filter(p => p[0] > bd.priceDate));',
    'bd.priceDate = e[0]; bd.price = e[1]; delete bd._yl;',
    'for (const p of neu) { if (p[1] < bd.low.price) bd.low = { date: p[0], price: p[1] }; if (p[1] > bd.high.price) bd.high = { date: p[0], price: p[1] }; }',
]


def _teil(isin):
    h = 0
    for ch in isin:
        h = (h * 31 + ord(ch)) % 65536
    return f"{h % 256:02x}"


def verlauf(site, isin, ab, verlauf_ab):
    """MC.verlauf(isin, {ab}) für Börsenkurse: kurse/<Jahr>/<teil>.json (nur gelistete Jahre), Punkte ab dem Tag `ab`."""
    try:
        liste = lade(site, "kurse/jahre.json")
        liste = liste if isinstance(liste, dict) and liste.get("jahre") else None
    except (OSError, ValueError):
        liste = None
    t, jetzt, jahre = _teil(isin), heute().year, []
    if liste:
        letztes = 0
        for y, kette in liste["jahre"].items():
            n = int(y)
            letztes = max(letztes, n)
            if any(kette[i:i + 2] == t for i in range(0, len(kette), 2)):
                jahre.append(n)
        jahre += list(range(letztes + 1, jetzt + 1))
    else:
        jahre = list(range(verlauf_ab, jetzt + 1))
    out = []
    for y in sorted(j for j in jahre if j >= int(ab[:4])):
        try:
            f = lade(site, f"kurse/{y}/{t}.json")
        except (OSError, ValueError):
            continue
        reihe = (f.get("k") or {}).get(isin) if isinstance(f, dict) else None
        if not reihe:
            continue
        for i, tag in enumerate(f.get("tage") or []):
            if i < len(reihe) and reihe[i] is not None:
                out.append((tag, reihe[i]))
    return [(tag, k) for tag, k in out if tag >= ab]


def langlaeufer(site, s):
    s.anker(ANKER_LANGLAEUFER)
    js = s.js
    T = js_texte(js_block(js, "const T = {"))
    farben = js_texte(js_block(js, "const COLORS = {"))
    meta = {k: {"name": js_str(n), "art": js_str(a), "cur": js_str(c)} for k, n, a, c in re.findall(
        r'(\w+):\s*\{\s*name:\s*"((?:[^"\\]|\\.)*)",\s*art:\s*"([^"]*)",\s*cur:\s*"([^"]*)"\s*\}', js_block(js, "const KPI_META = {"))}
    roh = {}
    for name in re.findall(r"const (\w+_WEEKLY_RAW) =", js):
        m = re.search(r"const " + name + r' =\s*((?:"[^"]*"\s*\+?\s*)+);', js)
        roh[name] = "".join(re.findall(r'"([^"]*)"', m.group(1)))
    anleihen = {}
    for var, body in re.findall(r"const (\w+) = mkBond\(\{(.*?)\}\);", js, re.S):
        b = {k: js_wert(v) for k, v in re.findall(r"(\w+)\s*:\s*" + _JS_WERT, re.sub(r"\{[^{}]*\}", "", body))}
        b["high"], b["low"] = js_punkt(body, "high"), js_punkt(body, "low")
        raw = re.search(r"raw:\s*(\w+)", body).group(1)
        b["weekly"] = [["20" + t.split(":")[0], float(t.split(":")[1])] for t in roh[raw].split()]
        b["priceDate"], b["price"] = b["weekly"][-1]
        anleihen[var] = b
    reihenfolge = re.findall(r"\w+", re.search(r"const COUPON_BONDS = \[([^\]]*)\];", js).group(1))
    kupon = [anleihen[v] for v in reihenfolge]
    bund_js, bund2_js = js_block(js, "const BUND = {"), js_block(js, "const BUND2 = {")
    bund = {"isin": js_texte(bund_js)["isin"], "maturity": js_texte(bund_js)["maturity"],
            "latest": js_punkt(bund_js, "latest"), "high": js_punkt(bund_js, "high"), "low": js_punkt(bund_js, "low")}
    bund2 = {"isin": js_texte(bund2_js)["isin"], "maturity": js_texte(bund2_js)["maturity"],
             "coupon": js_wert(re.search(r"coupon:\s*(-?[\d.]+)", bund2_js).group(1)),
             "latest": js_punkt(bund2_js, "latest"), "high": js_punkt(bund2_js, "high"), "low": js_punkt(bund2_js, "low")}
    if len(kupon) != 5 or any(k not in meta or k not in farben for k in ("bund", "bund2", "btp", "fr", "at", "us", "ms")):
        raise ValueError("Anleihen, Farben oder Emittenten im Seitenskript nicht vollständig gefunden")

    # langlaeufer.json: Kurse, Hoch und Tief beider Bundesanleihen (Bundesbank)
    def ok_pt(p):
        return isinstance(p, dict) and ist_tag(p.get("date")) and ist_zahl(p.get("price"))
    D = lade(site, "langlaeufer.json")
    for ziel, quelle in ((bund, (D.get("bonds") or {}).get("bund2050")), (bund2, (D.get("bonds") or {}).get("bund2040"))):
        if not quelle:
            continue
        if ok_pt(quelle.get("latest")):
            l = quelle["latest"]
            ziel["latest"] = {"date": l["date"], "price": l["price"], "yield": l.get("yield") if ist_zahl(l.get("yield")) else None}
        for k in ("high", "low"):
            if ok_pt(quelle.get(k)):
                ziel[k] = quelle[k]

    # kurse-auswahl.json + kurse/<Jahr>/: Tageskurse der fünf übrigen verlängern die eingebetteten Wochenreihen
    m = re.search(r"var VERLAUF_AB = (\d{4});", lies_text(site, "site.js"))
    verlauf_ab = int(m.group(1)) if m else 2021
    K = lade(site, "kurse-auswahl.json")
    kurse, tage = K.get("kurse") or {}, K.get("tage") or []
    for bd in kupon:
        k = kurse.get(bd["isin"])
        if not k:
            continue
        if not (isinstance(k[2], int) and 0 <= k[2] < len(tage)):
            raise ValueError(f"kurse-auswahl.json: Tag zu {bd['isin']} fehlt")
        tag = tage[k[2]]
        if tag <= bd["priceDate"]:
            continue
        neu = [(t, kurs) for t, kurs in verlauf(site, bd["isin"], bd["priceDate"], verlauf_ab)
               if t > bd["priceDate"] and ist_zahl(kurs)]
        if not neu or neu[-1][0] < tag:
            neu.append((tag, k[0]))
        bd["weekly"] = bd["weekly"] + [list(p) for p in neu if p[0] > bd["priceDate"]]
        bd["priceDate"], bd["price"] = bd["weekly"][-1]
        for t, kurs in neu:
            if kurs < bd["low"]["price"]:
                bd["low"] = {"date": t, "price": kurs}
            if kurs > bd["high"]["price"]:
                bd["high"] = {"date": t, "price": kurs}

    # Kennzahlen-Tabelle (alle sieben, Reihenfolge wie im Schaubild) und Kursspannen
    zeilen = [
        {"key": "bund", "isin": bund["isin"], "coupon": 0, "maturity": bund["maturity"], "price": bund["latest"]["price"],
         "yld": bund["latest"].get("yield"), "years": years_to(bund["maturity"], bund["latest"]["date"]),
         "high": bund["high"], "low": bund["low"]},
        {"key": "bund2", "isin": bund2["isin"], "coupon": bund2["coupon"], "maturity": bund2["maturity"],
         "price": bund2["latest"]["price"], "yld": bund2["latest"].get("yield"),
         "years": years_to(bund2["maturity"], bund2["latest"]["date"]), "high": bund2["high"], "low": bund2["low"]},
    ]
    nach_key = {b["key"]: b for b in kupon}
    for k in ("btp", "fr", "at", "us", "ms"):
        bd = nach_key[k]
        settle = add_days(bd["priceDate"], bd["settleDays"])
        zeilen.append({"key": k, "isin": bd["isin"], "coupon": bd["coupon"], "maturity": bd["maturity"], "price": bd["price"],
                       "yld": yield_from_price(bd, bd["price"], settle) * 100, "years": years_to(bd["maturity"], settle),
                       "high": bd["high"], "low": bd["low"]})
    html_ = []
    for r in zeilen:
        r.update(meta[r["key"]])
        seit_hoch = (r["price"] / r["high"]["price"] - 1) * 100
        art = "Staatsanleihe" if r["art"] == "Staat" else "Unternehmensanleihe"
        html_.append(
            f'<tr><th scope="row"><i class="tag" style="background:{farben[r["key"]]}"></i>{esc(T[r["key"]])}</th>'
            f'<td class="num">{zahl(r["yld"], 2)}{NBSP}%</td>'
            f'<td class="num">{zahl(r["price"], 2)}</td>'
            f'<td class="num">{zahl(seit_hoch, 0)}{NBSP}%<small>Hoch {zahl(r["high"]["price"], 2)} ({datum(r["high"]["date"])[3:]})</small></td>'
            f'<td class="num">{zahl(r["years"], 1)} {T["years"]}</td><td class="num">{fmt_coupon(r["coupon"])}{NBSP}%</td>'
            f'<td class="num">{datum(r["maturity"])}</td>'
            f'<td class="emi" title="{esc(art)}">{esc(r["name"])}</td>'
            f'<td class="isin"><a href="anleihe.html?isin={r["isin"]}" title="Steckbrief: Kurs, Rendite, Kursverlauf, Handel und '
            f'Stammdaten">{r["isin"]}</a></td><td class="txt">{r["cur"]}</td></tr>')
    s.inner("#kpis-body", "".join(html_))
    ids = {"bund": "b-spanne", "bund2": "b2-spanne", "btp": "t-spanne", "fr": "fr-spanne", "at": "at-spanne",
           "us": "us-spanne", "ms": "ms-spanne"}
    for r in zeilen:
        s.text("#" + ids[r["key"]], f'Hoch {zahl(r["high"]["price"], 2)} ({datum(r["high"]["date"])}) · '
                                    f'Tief {zahl(r["low"]["price"], 2)} ({datum(r["low"]["date"])})', muss=False)

    # Fußzeile (Stand der Bundesbank-Kurse) und Kopfzeile (jüngster Kurs aller sieben)
    alt = veraltet(bund["latest"]["date"])
    daten_stand_veraltet(s, f'{T["dataAsOf"]} {datum(bund["latest"]["date"])}' + (f' · {T["outdated"]}' if alt else ""),
                         bund["latest"]["date"])
    neu = sorted(x for x in [bund["latest"]["date"], bund2["latest"]["date"]] + [b["priceDate"] for b in kupon] if x)[-1]
    s.text("#eyebrow-ll", f"Kurse in % des Nennwerts · 2019 – {neu[:4]} · Stand: {datum(neu)}", muss=False)

    # Zahlen im Fließtext (prosa): Kurse, Renditen, Verlust seit dem Hoch, modifizierte Duration
    def setze(k, t):
        if s.finde(f'[data-ll="{k}"]'):
            s.text(f'[data-ll="{k}"]', t, alle=True)

    def pct(v):
        return f"{zahl(v, 1)}{NBSP}%"

    def mod_dur(b, price, date, yld=None):
        st = add_days(date, b.get("settleDays") or 2)
        return mod_duration(b, yld / 100 if yld is not None else yield_from_price(b, price, st), st)
    bl = bund["latest"]
    if ist_zahl(bl.get("price")):
        if ist_zahl(bl.get("yield")):
            setze("bund-y", pct(bl["yield"]))
        setze("bund-p", zahl(bl["price"], 0))
        setze("bund-d", zahl(mod_dur({"coupon": 0, "freq": 1, "maturity": bund["maturity"], "settleDays": 2},
                                     bl["price"], bl["date"], bl.get("yield")), 0))
        setze("bund-minus", f'{zahl((1 - bl["price"] / bund["high"]["price"]) * 100, 0)}{NBSP}%')
    if ist_zahl(bund2["latest"].get("price")):
        setze("bund2-hoch", zahl(bund2["high"]["price"], 0))
        setze("bund2-minus", f'{zahl((1 - bund2["latest"]["price"] / bund2["high"]["price"]) * 100, 0)}{NBSP}%')
    btp, fr, at = anleihen["BTP"], anleihen["FR"], anleihen["AT"]
    setze("btp-d", zahl(mod_dur(btp, btp["price"], btp["priceDate"]), 0))
    setze("btp-p", zahl(btp["price"], 0))
    setze("fr-p", zahl(fr["price"], 0))
    setze("at-y", pct(yield_from_price(at, at["price"], add_days(at["priceDate"], at["settleDays"])) * 100))
    setze("at-d", zahl(mod_dur(at, at["price"], at["priceDate"]), 0))
    setze("at-d2", zahl(mod_dur(at, at["price"], at["priceDate"]), 0))
    return f'{datum(bund["latest"]["date"])} (Bundesbank), Kurse bis {datum(neu)}'


SEITEN = (("renditen.html", renditen), ("unternehmensanleihen.html", unternehmensanleihen), ("zinskurve.html", zinskurve),
          ("realzins.html", realzins), ("risikoaufschlaege.html", risikoaufschlaege), ("langlaeufer.html", langlaeufer))


def main():
    global STALE_TAGE
    site = sys.argv[1] if len(sys.argv) > 1 else "_site"
    if not os.path.isdir(site):
        raise SystemExit(f"Ordner nicht gefunden: {site}")
    try:
        m = re.search(r"var STALE_TAGE = (\d+);", lies_text(site, "site.js"))
        STALE_TAGE = int(m.group(1))
    except (OSError, AttributeError):
        warn("MC.STALE_TAGE nicht in site.js gefunden – „veraltet“ ab 5 Börsentagen")
    for name, schritt in SEITEN:
        pfad = os.path.join(site, name)
        if not os.path.isfile(pfad):
            warn(f"{name} fehlt")
            continue
        try:
            s = Seite(pfad)
            stand = schritt(site, s)
            s.speichern()
            print(f"{name}: {s.gesetzt} Werte gesetzt, davon {s.geaendert} geändert – Stand {stand}")
        except Exception as e:   # Daten oder Seite anders als erwartet: Seite bleibt, wie sie ist
            warn(f"{name}: unverändert ({type(e).__name__}: {e})")


if __name__ == "__main__":
    main()
