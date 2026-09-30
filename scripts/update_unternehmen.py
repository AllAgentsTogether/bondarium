#!/usr/bin/env python3
"""Aktualisiert unternehmen.json – Renditen von Unternehmensanleihen-Segmenten
(Bonität × Land), zweiter Chart auf renditen.html.

Läuft wie update_renditen.py nur im vollen Lauf (Workflow: VOLL=1). Die
FAST-Selbstdrosselung (höchstens ein Abruf pro Tag, gemessen an checkedAt)
bleibt als Schutz erhalten, falls das Skript doch in einem FAST-Lauf startet.

Sieben Reihen (Schlüssel → Quelle):
- us_hqm   USA, Unternehmensanleihen hoher Bonität (AAA/AA/A), 10 Jahre:
           HQM-Kurve des US-Finanzministeriums (Spot-Rendite), via FRED
           HQMCB10YR – monatlich seit 1984.
- de_corp  Deutschland, Anleihen von Unternehmen (Nicht-MFIs), Umlaufsrendite
           über alle Laufzeiten (Ø Restlaufzeit ≈ 7 J.): Bundesbank BBSIS,
           Monatswerte seit 1957, Tageswerte seit 1979.
- jp_aa    Japan, Unternehmensanleihen mit Rating AA (R&I), Restlaufzeit 10 Jahre:
           JSDA-Rating-Matrix (公社債店頭売買参考統計値 格付マトリクス), börsentäglich
           seit 08/2002. Historie als Monatsendwerte (letzter Handelstag) – siehe unten.
- jp_a     Japan, dito Rating A (R&I) – aus derselben Tagesdatei wie jp_aa.
- cn_aaa   China, Unternehmensanleihen AAA, 10 Jahre: ChinaBond-Renditekurve
           (中债企业债收益率曲线(AAA)), börsentäglich seit 2006. Historie als
           Monatsendwerte.
- au_a     Australien, Anleihen nichtfinanzieller Unternehmen mit Rating A,
           10 Jahre: RBA-Tabelle F3 (FNFYA10M), monatlich seit 2005.
- au_bbb   Australien, dito Rating BBB (FNFYBBB10M).

Nicht aufgenommen (bewusst): ICE-BofA-Indizes über FRED – seit 04/2026 nur
noch drei Jahre Historie, und die Lizenz untersagt die Veröffentlichung.
Gestrichen 30.09.2026: Moody's Baa (FRED BAA/DBAA) – Moody's untersagt in den
Reihen-Notizen bei FRED jede Weiterverbreitung ohne schriftliche Zustimmung.
Gestrichen 09/2026: Moody's Aaa (Dublette zu HQM), Hypothekenpfandbriefe
(gedeckte Bankanleihen) und Bankschuldverschreibungen 9–10 J. (reiner
Finanzsektor – passte nicht zu den übrigen Unternehmenssegmenten).

Struktur von unternehmen.json (analog renditen.json):
    series[<key>].latest  = {"date": "JJJJ-MM-TT" | "JJJJ-MM", "yield": 4.12}
    series[<key>].annual  = {"JJJJ": Jahresdurchschnitt der Monatswerte}
    series[<key>].range   = {"JJJJ": [niedrigstes, höchstes Monatsmittel]}
    series[<key>].monthly = {"JJJJ-MM": Monatsendwert}   (nur jp_aa, jp_a, cn_aaa)
    series[<key>].nodata  = ["JJJJ-MM", …]               (nur jp_aa, jp_a, cn_aaa: Monat ohne Daten)
Zeitstempel checkedAt (jeder Abruf-Lauf) sowie updated/updatedAt (nur bei
Wertänderung) wie in renditen.json.

Monatswerte sind bei der Bundesbank Monatsdurchschnitte, bei HQM, RBA, JSDA
und ChinaBond Monatsend- bzw. Monatspunktwerte. Jahresdurchschnitt =
Mittel der zwölf Monatswerte; Jahresspanne = [min, max] der Monatswerte.

Japan/China werden „gesampelt“: Je Monat wird der Wert des letzten Handelstags
aus der Tagesdatei (JSDA) bzw. der Tageskurve (ChinaBond) geholt und in
series[<key>].monthly festgeschrieben. Fehlende Monate werden bei jedem Lauf
mit begrenztem Budget nachgeholt (neueste zuerst; SAMPLE_BUDGET je Quelle
unten). ChinaBond antwortet zügig (Historie ab 2006 wurde 09/2026 einmalig komplett
geladen); die JSDA sperrt bei mehr als ~7 Abrufen binnen Minuten die IP für eine
Viertelstunde – dort werden je Lauf nur wenige Monate mit 12 s Pause geholt, die
Historie ab 2002 füllt sich über die täglichen Läufe rückwärts auf (Jahresmittel
erscheinen im Chart, sobald ein Jahr zwölf Monatswerte hat).

Einmaliges Nachladen (FRED/Bundesbank/RBA komplett, Japan/China mit großem Budget):

    python3 scripts/update_unternehmen.py --backfill
    SAMPLE_BUDGET_CN=300 SAMPLE_BUDGET_JP=30 python3 scripts/update_unternehmen.py --backfill

SKIP_JP_A=1 bzw. SKIP_CN_AAA=1 lässt eine gesampelte Quelle in einem Lauf aus.
Der Backfill ergänzt nur fehlende Jahre/Monate (ersetzt bestehende nicht).
"""

import csv
import datetime
import io
import json
import os
import re
import sys
import time
from pathlib import Path

from _common import get_with_retry, log_err, now_iso, plausible, today_iso, write_atomic
# Ersetzungsregeln für "latest" (Tages- vs. Monatswert) und Spannen-Pflege
# gemeinsam mit den Staatsanleihen – bewusst importiert statt kopiert.
from update_renditen import darf_ersetzen, month_of, update_ranges

DATA_FILE = Path(__file__).resolve().parent.parent / "unternehmen.json"

RANGE_START = 1970   # Beginn der Chart-Zeitachse (renditen.html, YEAR0)

FRED_CSV = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={sid}&cosd={cosd}"
BUBA_SDMX = "https://api.statistiken.bundesbank.de/rest/data/BBSIS/{key}?detail=dataonly{extra}"
BUBA_ACCEPT = {"Accept": "application/vnd.sdmx.data+csv;version=1.0.0",
               "User-Agent": "Mozilla/5.0 (Datenaktualisierung Unternehmensanleihen)"}
RBA_F3 = "https://www.rba.gov.au/statistics/tables/csv/f3-data.csv"
JSDA_BASE = "https://market.jsda.or.jp/shijyo/saiken/baibai/baisanchi/"
JSDA_INDEX = JSDA_BASE + "index.html"            # jüngste Handelstage: Links auf files/JJJJ/RjjMMTT.csv
JSDA_ARCHIVE = JSDA_BASE + "archive{year}.html"  # ganzes Jahr (auch das laufende): files/JJJJ[/MM]/RjjMMTT.csv
CHINABOND_URL = (
    "https://yield.chinabond.com.cn/cbweb-mn/yc/ycDetail?ycDefIds={cid}&&zblx=txy"
    "&&workTime={date}&&dxbj=0&&qxlx=0,&&yqqxN=N&&yqqxK=K&&wrjxCBFlag=0&locale=zh_CN"
)
CHINABOND_AAA = "2c9081e50a2f9606010a309f4af50111"   # 中债企业债收益率曲线(AAA)
CHINABOND_HEADERS = {"User-Agent": "Mozilla/5.0 (Datenaktualisierung Unternehmensanleihen)",
                     "Referer": "https://yield.chinabond.com.cn/cbweb-mn/yield_main",
                     "X-Requested-With": "XMLHttpRequest"}

UA = {"User-Agent": "Mozilla/5.0 (Datenaktualisierung Unternehmensanleihen)"}
# RBA (Cloudflare) beantwortet browserähnliche Kennungen ohne Browser-Fingerabdruck
# mit 403, die Standardkennung von urllib ("Python-urllib/3.x") dagegen mit 200
# (geprüft 09/2026) – daher dort KEIN User-Agent-Header setzen.
RBA_HEADERS = {"Accept": "text/csv,*/*"}
# FRED bricht Anfragen OHNE Accept-Header häufig ab (Timeout bzw. "Remote end closed
# connection", geprüft 26.09.2026 – mit Accept kam jede Anfrage durch). Folge vorher:
# eine FRED-Tagesreihe fiel still aus und blieb tagelang auf einem alten Stand stehen.
FRED_HEADERS = {**UA, "Accept": "text/csv,*/*"}

# Bundesbank-Zeitreihenschlüssel (BBSIS, 15 Dimensionen). Frequenz D/M wird
# vorn eingesetzt: "{f}.I.UMR.RD.EUR.<Emittent>.B.<Gattung>.<RLZ>.R.A.A._Z._Z.A"
BUBA_KEYS = {
    "de_corp": "I.UMR.RD.EUR.X2000.B.A.A.R.A.A._Z._Z.A",       # Unternehmen (Nicht-MFIs), alle RLZ
}
FRED_MONTHLY = {"us_hqm": "HQMCB10YR"}   # U.S. Treasury, gemeinfrei (FRED: „Public Domain: Citation Requested“)
FRED_DAILY: dict[str, str] = {}             # seit 30.09.2026 leer (Moody's DBAA gestrichen); Mechanik bleibt für freie Tagesreihen
RBA_IDS = {"au_a": "FNFYA10M", "au_bbb": "FNFYBBB10M"}
# Gesampelte Reihen: Beginn der Quelle, Budget fehlender Monate je Lauf, Pause zwischen Abrufen
# Japan: eine JSDA-Datei liefert alle Rating-Klassen – Reihe → Rating-Label in der Matrix (R&I)
JSDA_RATINGS = {"jp_aa": "AA", "jp_a": "A"}
SAMPLED = {
    # JSDA sperrt eine IP nach ~7–8 Abrufen binnen weniger Minuten für rund eine
    # Viertelstunde (beobachtet 09/2026) – daher lange Pause und kleines Budget
    # (Startseite + ggf. Tagesdatei + Archivseite + 3 Monatsdateien ≈ 5–6 Abrufe/Lauf).
    "jp_a":   {"start": "2002-08", "budget": int(os.environ.get("SAMPLE_BUDGET_JP", "3")), "pause": 15.0},
    "cn_aaa": {"start": "2006-03", "budget": int(os.environ.get("SAMPLE_BUDGET_CN", "40")), "pause": 0.3},
}

KEYS = ["us_hqm", "de_corp", "jp_aa", "jp_a", "cn_aaa", "au_a", "au_bbb"]


def _plausibel(key: str, new: float, old) -> bool:
    """Wie bei den Staatsanleihen: Sprung > 2,5 Prozentpunkte gegenüber dem
    letzten Stand ist fast sicher ein Parser-/Quellenfehler."""
    return plausible(new, old, f"unternehmen {key}", max_abs=2.5)


# ---------- Quellen: FRED, Bundesbank, RBA ----------

def fetch_fred(sid: str, start: datetime.date) -> list[tuple[str, float]]:
    """FRED-CSV (observation_date,WERT; "." = fehlend) → [(Datum, Wert), …].
    Monatsreihen liefern den Monatsersten – der Aufrufer kürzt auf "JJJJ-MM"."""
    text = get_with_retry(FRED_CSV.format(sid=sid, cosd=start.isoformat()), headers=FRED_HEADERS, timeout=40,
                          tries=4, backoff=3.0).decode("utf-8", "replace")
    out = []
    for rec in csv.reader(io.StringIO(text)):
        if len(rec) < 2 or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", rec[0]):
            continue
        try:
            out.append((rec[0], float(rec[1])))
        except ValueError:
            continue  # "." = kein Wert
    return out


def fetch_fred_monthly(sid: str, start_year: int) -> dict[str, float]:
    return {d[:7]: v for d, v in fetch_fred(sid, datetime.date(start_year, 1, 1))}


def fetch_fred_daily(sid: str) -> tuple[str, float] | None:
    rows = fetch_fred(sid, datetime.date.today() - datetime.timedelta(days=45))
    return max(rows) if rows else None


def fetch_buba(freq: str, key: str, start_year: int | None) -> list[tuple[str, float]]:
    """Bundesbank SDMX-CSV (Semikolon; TIME_PERIOD/OBS_VALUE; "." = fehlend).
    startPeriod verlangt eine volle Periode ("1970-01" bzw. "2026-01-01");
    ein bloßes Jahr quittiert die API mit HTTP 400."""
    extra = f"&startPeriod={start_year}-01" + ("-01" if freq == "D" else "") if start_year else ""
    url = BUBA_SDMX.format(key=f"{freq}.{key}", extra=extra)
    text = get_with_retry(url, headers=BUBA_ACCEPT, timeout=60).decode("utf-8-sig", "replace")
    out = []
    for rec in csv.DictReader(io.StringIO(text), delimiter=";"):
        per, val = rec.get("TIME_PERIOD", ""), rec.get("OBS_VALUE", "")
        if not per or val in ("", "."):
            continue
        try:
            out.append((per, float(val)))
        except ValueError:
            continue
    return out


def fetch_buba_monthly(key: str, start_year: int | None) -> dict[str, float]:
    return {p: v for p, v in fetch_buba("M", key, start_year) if re.fullmatch(r"\d{4}-\d{2}", p)}


def fetch_buba_daily(key: str) -> tuple[str, float] | None:
    rows = [(p, v) for p, v in fetch_buba("D", key, datetime.date.today().year)
            if re.fullmatch(r"\d{4}-\d{2}-\d{2}", p)]
    return max(rows) if rows else None


def fetch_rba() -> dict[str, dict[str, float]]:
    """RBA-Tabelle F3: Kopfzeilen (Title, …, Series ID), dann Datenzeilen
    "TT/MM/JJJJ". Rückgabe {'au_a': {'2026-08': 5.64, …}, …}."""
    text = get_with_retry(RBA_F3, headers=RBA_HEADERS, timeout=60).decode("utf-8-sig", "replace")
    rows = list(csv.reader(io.StringIO(text)))
    col = {}
    for r in rows:
        if r and r[0].strip() == "Series ID":
            col = {sid: r.index(sid) for sid in RBA_IDS.values() if sid in r}
            break
    if len(col) != len(RBA_IDS):
        raise ValueError(f"RBA F3: Spalten nicht gefunden ({sorted(col)})")
    out: dict[str, dict[str, float]] = {k: {} for k in RBA_IDS}
    for r in rows:
        m = re.fullmatch(r"(\d{2})/(\d{2})/(\d{4})", (r[0] if r else "").strip())
        if not m:
            continue
        per = f"{m.group(3)}-{m.group(2)}"
        for key, sid in RBA_IDS.items():
            try:
                out[key][per] = float(r[col[sid]])
            except (IndexError, ValueError):
                continue  # leer = kein Wert
    return out


# ---------- Quellen: JSDA (Japan) und ChinaBond (China), gesampelt ----------

_jsda_files_cache: dict[int, dict[str, str]] = {}


def jsda_files_from(url: str, year: int, pause: float) -> dict[str, str]:
    """Links auf Rating-Matrix-Dateien einer JSDA-Seite als {"JJJJ-MM-TT": URL}."""
    html = get_with_retry(url, headers=UA, timeout=40, tries=2).decode("utf-8", "replace")
    time.sleep(pause)
    files = {}
    for href in re.findall(r'href="([^"]*?R(\d{2})(\d{2})(\d{2})\.csv)"', html):
        path, yy, mm, dd = href
        date = f"20{yy}-{mm}-{dd}"
        if not date.startswith(str(year)):
            continue
        if path.startswith("http"):
            files[date] = path
        elif path.startswith("/"):
            files[date] = "https://market.jsda.or.jp" + path
        else:
            files[date] = JSDA_BASE + path.lstrip("./")   # Links sind relativ ("./files/…")
    return files


def jsda_handelstage(files: dict[str, str]) -> dict[str, str]:
    """Die JSDA benennt jede Datei nach dem VERÖFFENTLICHUNGSDATUM, und das ist der
    nächste Geschäftstag nach dem Handelstag („発表日付は翌営業日の日付となります“:
    Datei R260928 = Kurse vom Freitag, 25.09.2026, 15 Uhr). Der Handelstag einer
    Datei ist damit das Datum der vorhergehenden Datei in der Liste (= voriger
    japanischer Geschäftstag, Feiertage inbegriffen). Rückgabe {Handelstag: URL};
    die älteste Datei der Liste entfällt (ihr Handelstag ist nicht bekannt).
    Bis 26.09.2026 wurde das Dateidatum als Stand gespeichert – Folge: ein Datum
    in der Zukunft („Stand 28.09.2026“ am 26.09.)."""
    days = sorted(files)
    return {days[i - 1]: files[days[i]] for i in range(1, len(days))}


def jsda_year_files(year: int, pause: float) -> dict[str, str]:
    """Alle Dateien eines Jahres (Archivseite archiveJJJJ.html – existiert auch für
    das laufende Jahr; die Startseite listet nur die jüngsten Handelstage). Ein Abruf je Jahr."""
    if year not in _jsda_files_cache:
        _jsda_files_cache[year] = jsda_files_from(JSDA_ARCHIVE.format(year=year), year, pause)
    return _jsda_files_cache[year]


def jsda_values(url: str, agency: str = "1", bucket: str = "10") -> dict[str, float]:
    """Renditen (Durchschnitt) aus einer Rating-Matrix-Datei für alle Rating-
    Klassen einer Zeile: Agentur (1 = R&I), Restlaufzeit-Klasse (10 = 10 Jahre);
    je Rating-Block Label, Rendite, Standardabweichung, Anzahl Emissionen, Anzahl
    Meldungen. Shift-JIS. Rückgabe {"AA": 3.52, "A": 3.78, …} (leer, wenn ohne Wert)."""
    text = get_with_retry(url, headers=UA, timeout=40, tries=2).decode("shift_jis", "replace")
    out: dict[str, float] = {}
    # zeilenweise füttern: die Dateien enthalten \r-Zeilenumbrüche, an denen csv.reader
    # auf einem StringIO stolpert ("new-line character seen in unquoted field")
    for rec in csv.reader(text.splitlines()):
        if len(rec) < 6 or rec[1].strip() != agency or rec[3].strip().lstrip("0") != bucket.lstrip("0"):
            continue
        for i in range(4, len(rec) - 1, 5):
            label = rec[i].strip()
            if label:
                try:
                    out[label] = round(float(rec[i + 1]), 3)
                except ValueError:
                    pass
        break
    return out


def chinabond_value(date: str) -> float | None:
    """10-Jahres-Punkt der ChinaBond-Kurve am Handelstag date ("JJJJ-MM-TT");
    None an Nicht-Handelstagen (die Antwort enthält dann keine Tabelle)."""
    url = CHINABOND_URL.format(cid=CHINABOND_AAA, date=date)
    # Der Endpunkt nimmt nur POST an (GET → 405); Parameter stehen in der URL
    html = get_with_retry(url, headers=CHINABOND_HEADERS, timeout=40, data=b"").decode("utf-8", "replace")
    cells = [re.sub(r"<[^>]+>", "", c).strip() for c in re.findall(r"<td[^>]*>(.*?)</td>", html, flags=re.S)]
    for i, c in enumerate(cells[:-1]):
        if c == "10.0y":
            try:
                return round(float(cells[i + 1]), 3)
            except ValueError:
                return None
    return None


def month_ends(start: str, end: str) -> list[str]:
    """Monate "JJJJ-MM" von start bis end (einschließlich), aufsteigend."""
    y, m = int(start[:4]), int(start[5:7])
    ey, em = int(end[:4]), int(end[5:7])
    out = []
    while (y, m) <= (ey, em):
        out.append(f"{y}-{m:02d}")
        m += 1
        if m > 12:
            y, m = y + 1, 1
    return out


def sample_jp(series: dict, cfg: dict, today: datetime.date, save=None) -> bool:
    """Japan: jüngster Tageswert + fehlende Monatsendwerte (Budget) aus der JSDA-
    Matrix – EINE Tagesdatei liefert alle Rating-Klassen, daher werden die Japan-
    Reihen (JSDA_RATINGS) gemeinsam befüllt; das Budget zählt Dateien.
    save: optionaler Callback, der den Zwischenstand nach jeder Datei wegschreibt
    (ein abgebrochener Lauf verliert so keine bereits geholten Werte)."""
    changed = False
    pause = cfg["pause"]
    ser = {k: series.setdefault(k, {}) for k in JSDA_RATINGS}
    for s in ser.values():
        s.setdefault("monthly", {})
        s.setdefault("nodata", [])

    def apply(date_or_month: str, vals: dict[str, float], latest: bool) -> bool:
        ch = False
        for key, rating in JSDA_RATINGS.items():
            s = ser[key]
            v = vals.get(rating)
            if latest:
                old = s.get("latest") or {}
                if v is not None and _plausibel(key, v, old.get("yield")) and darf_ersetzen(old.get("date"), date_or_month) \
                        and (date_or_month, round(v, 2)) != (old.get("date"), old.get("yield")):
                    s["latest"] = {"date": date_or_month, "yield": round(v, 2)}
                    print(f"{key}: {v} % (Stand {date_or_month}).")
                    ch = True
            else:
                if v is None:
                    if date_or_month not in s["nodata"]:
                        s["nodata"] = sorted(set(s["nodata"]) | {date_or_month})
                        ch = True
                elif s["monthly"].get(date_or_month) != v:
                    s["monthly"][date_or_month] = v
                    s["monthly"] = dict(sorted(s["monthly"].items()))
                    ch = True
        return ch

    # 1) jüngster Handelstag (Startseite; die Datei eines Tages erscheint gegen 18:30 JST)
    files = jsda_handelstage(jsda_files_from(JSDA_INDEX, today.year, pause))
    if files:
        newest = max(files)   # jüngster HANDELSTAG (nicht Dateidatum, siehe jsda_handelstage)
        # Alt-Stände mit Dateidatum (nach dem jüngsten Handelstag bzw. in der Zukunft)
        # verwerfen, sonst ließe darf_ersetzen() den korrekten, älteren Handelstag nie zu
        backup = {k: s.get("latest") for k, s in ser.items()}
        for s in ser.values():
            d = (s.get("latest") or {}).get("date")
            if d and (d > newest or d > today.isoformat()):
                print(f"Japan: gespeicherter Stand {d} liegt nach dem jüngsten Handelstag {newest} – wird ersetzt.")
                s.pop("latest", None)
        if any((s.get("latest") or {}).get("date") != newest for s in ser.values()):
            try:
                vals = jsda_values(files[newest])
            finally:
                # Abruf gescheitert oder ohne Wert: alten Stand behalten statt die Reihe ohne Stand zu lassen
                for k, s in ser.items():
                    if not s.get("latest") and backup.get(k):
                        s["latest"] = backup[k]
            time.sleep(pause)
            for k, s in ser.items():
                if (s.get("latest") or {}).get("date", "") > newest:
                    s.pop("latest", None)   # nur hier verwerfen – apply() setzt den korrekten Handelstag
            if apply(newest, vals, latest=True):
                changed = True
            for k, s in ser.items():
                if not s.get("latest") and backup.get(k):
                    s["latest"] = backup[k]   # kein Wert für diese Klasse: alten Stand behalten
    # 2) fehlende Monatsendwerte (in irgendeiner Japan-Reihe), neueste zuerst
    last_full = (today.replace(day=1) - datetime.timedelta(days=1)).strftime("%Y-%m")
    def missing_in_any(m):
        return any(m not in s["monthly"] and m not in s["nodata"] for s in ser.values())
    missing = [m for m in reversed(month_ends(cfg["start"], last_full)) if missing_in_any(m)]
    for m in missing[: cfg["budget"]]:
        yr = int(m[:4])
        try:
            yfiles = jsda_handelstage(jsda_year_files(yr, pause))
        except Exception as e:
            log_err(f"Japan: Archivseite {yr} nicht abrufbar: {e}")
            break
        days = [d for d in yfiles if d.startswith(m)]
        if not days:
            if apply(m, {}, latest=False):
                changed = True
            continue
        try:
            vals = jsda_values(yfiles[max(days)])
        except Exception as e:
            log_err(f"Japan: Datei {max(days)} nicht abrufbar: {e} – Rest im nächsten Lauf.")
            break
        time.sleep(pause)
        if apply(m, vals, latest=False):
            changed = True
        if save:
            save()
    return changed


def sample_cn(s: dict, cfg: dict, today: datetime.date, save=None) -> bool:
    """China: jüngster Handelstag (rückwärts suchen) + fehlende Monatsendwerte (Budget)."""
    changed = False
    pause = cfg["pause"]
    monthly = s.setdefault("monthly", {})
    nodata = set(s.get("nodata", []))

    def last_trading_value(end: datetime.date, back: int = 7) -> tuple[str, float] | None:
        """Wert des letzten Handelstags bis end: Wochenenden werden übersprungen
        (kein Abruf), an Feiertagen liefert die Kurve keine Tabelle → Vortag versuchen."""
        d, tries = end, 0
        while tries < back:
            if d.weekday() >= 5:
                d -= datetime.timedelta(days=1)
                continue
            v = chinabond_value(d.isoformat())
            time.sleep(pause)
            tries += 1
            if v is not None:
                return d.isoformat(), v
            d -= datetime.timedelta(days=1)
        return None

    old = s.get("latest") or {}
    if old.get("date") != today.isoformat():
        lt = last_trading_value(today)
        if lt and _plausibel("cn_aaa", lt[1], old.get("yield")) and darf_ersetzen(old.get("date"), lt[0]):
            if (lt[0], round(lt[1], 2)) != (old.get("date"), old.get("yield")):
                s["latest"] = {"date": lt[0], "yield": round(lt[1], 2)}
                print(f"cn_aaa: {lt[1]} % (Stand {lt[0]}).")
                changed = True
    last_full = (today.replace(day=1) - datetime.timedelta(days=1)).strftime("%Y-%m")
    missing = [m for m in reversed(month_ends(cfg["start"], last_full)) if m not in monthly and m not in nodata]
    for m in missing[: cfg["budget"]]:
        y, mo = int(m[:4]), int(m[5:7])
        end = (datetime.date(y + (mo == 12), (mo % 12) + 1, 1) - datetime.timedelta(days=1))
        try:
            lt = last_trading_value(end)
        except Exception as e:
            log_err(f"cn_aaa: {m} nicht abrufbar: {e} – Rest im nächsten Lauf.")
            break
        if lt is None:
            nodata.add(m)
        else:
            monthly[m] = lt[1]
        changed = True
        s["monthly"] = dict(sorted(monthly.items()))
        s["nodata"] = sorted(nodata)
        if save:
            save()
    if changed:
        s["monthly"] = dict(sorted(monthly.items()))
        s["nodata"] = sorted(nodata)
    return changed


# ---------- Zusammenführen ----------

def update(data: dict, backfill: bool = False) -> tuple[bool, int]:
    """Rückgabe (changed, delivered): changed = mindestens ein Wert geändert;
    delivered = Anzahl Reihen, für die eine Quelle Daten lieferte."""
    today = datetime.date.today()
    series = data.setdefault("series", {})
    changed = False
    delivered = 0
    start_year = RANGE_START if backfill else today.year - 2

    # Monatsreihen je Schlüssel einsammeln (Quellenfehler einzeln protokollieren)
    monthly_all: dict[str, dict[str, float]] = {}
    for key, sid in FRED_MONTHLY.items():
        try:
            monthly_all[key] = fetch_fred_monthly(sid, start_year)
        except Exception as e:
            log_err(f"FRED {sid} ({key}) nicht abrufbar: {e}")
    for key, bkey in BUBA_KEYS.items():
        try:
            monthly_all[key] = fetch_buba_monthly(bkey, start_year)
        except Exception as e:
            log_err(f"Bundesbank {key} nicht abrufbar: {e}")
    try:
        monthly_all.update(fetch_rba())
    except Exception as e:
        log_err(f"RBA F3 nicht abrufbar: {e}")
    # Gesampelte Reihen: Monatsendwerte liegen persistent in series[key].monthly
    for key, cfg in SAMPLED.items():
        if os.environ.get("SKIP_" + key.upper()):   # manuell: z. B. SKIP_JP_A=1 (Quelle gerade gesperrt)
            print(f"{key}: Sampling übersprungen (SKIP_{key.upper()}).")
        else:
            try:
                # Zwischenstand nach jedem Monat sichern (nur monthly/nodata/latest der Reihe)
                save = lambda: write_atomic(DATA_FILE, data)  # noqa: E731
                if key == "jp_a":
                    ok = sample_jp(series, cfg, today, save=save)      # befüllt jp_aa und jp_a zugleich
                else:
                    ok = sample_cn(series.setdefault(key, {}), cfg, today, save=save)
                if ok:
                    changed = True
            except Exception as e:
                log_err(f"{key}: Sampling fehlgeschlagen: {e}")
    for key in list(JSDA_RATINGS) + [k for k in SAMPLED if k != "jp_a"]:
        s = series.setdefault(key, {})
        monthly_all[key] = dict(s.get("monthly", {}))
        if s.get("latest"):
            delivered += 1   # Reihe hat einen Stand (auch wenn dieser Lauf nichts Neues brachte)

    for key in KEYS:
        s = series.setdefault(key, {})
        old_latest = s.get("latest") or {}
        monthly = monthly_all.get(key, {})

        # 1) Abgeschlossene Jahre als Jahresdurchschnitt festschreiben (12 Monatswerte);
        #    normaler Lauf: nur die jüngsten Jahre, Backfill: alle ab RANGE_START
        #    (gesampelte Reihen: immer alle, sobald ein Jahr vollständig ist)
        annual = s.setdefault("annual", {})
        by_year: dict[str, list[float]] = {}
        for per, v in monthly.items():
            by_year.setdefault(per[:4], []).append(v)
        first_year = RANGE_START if (backfill or key in SAMPLED or key in JSDA_RATINGS) else start_year
        for yr, vals in sorted(by_year.items()):
            if first_year <= int(yr) < today.year and len(vals) == 12 and yr not in annual:
                annual[yr] = round(sum(vals) / len(vals), 2)
                if not backfill:
                    print(f"{key}: Jahresdurchschnitt {yr} festgeschrieben ({annual[yr]} %).")
                changed = True
        s["annual"] = dict(sorted(annual.items()))
        # 1b) Jahresspanne [Tief, Hoch] der Monatswerte
        if update_ranges(key, s, monthly, today):
            changed = True

        if key in SAMPLED or key in JSDA_RATINGS:
            continue   # latest bereits im Sampling gesetzt

        # 2) Jüngster Wert: Tagesquelle, sonst jüngster Monatswert
        best = None
        if monthly:
            per = max(monthly)
            best = (per, round(monthly[per], 2))
        daily = None
        try:
            if key in FRED_DAILY:
                daily = fetch_fred_daily(FRED_DAILY[key])
            elif key in BUBA_KEYS:
                daily = fetch_buba_daily(BUBA_KEYS[key])
        except Exception as e:
            log_err(f"Tagesquelle {key} nicht abrufbar: {e}")
        if daily and (best is None or month_of(daily[0]) >= best[0][:7]):
            best = daily
        if best is None:
            log_err(f"{key}: keine Quelle lieferte Daten – Stand bleibt unverändert.")
            continue
        delivered += 1

        date, value = best
        value = round(value, 2)
        if (date, value) == (old_latest.get("date"), old_latest.get("yield")):
            continue
        if not _plausibel(key, value, old_latest.get("yield")):
            continue
        if not darf_ersetzen(old_latest.get("date"), date):
            print(f"{key}: {value} % (Stand {date}) ersetzt den gespeicherten Stand "
                  f"{old_latest.get('date')} nicht (älter/gröber).")
            continue
        s["latest"] = {"date": date, "yield": value}
        print(f"{key}: {value} % (Stand {date}).")
        changed = True

    # Reihen, die nicht mehr angezeigt werden (z. B. us_aaa, de_pfand seit 09/2026), entfernen
    for stale in [k for k in series if k not in KEYS]:
        del series[stale]
        print(f"{stale}: nicht mehr Teil der Auswahl – aus unternehmen.json entfernt.")
        changed = True

    return changed, delivered


def main() -> int:
    try:
        data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    except FileNotFoundError:
        data = {"series": {}}
    except Exception as e:
        log_err(f"unternehmen.json unlesbar – Abbruch, Datei bleibt unangetastet: {e}")
        return 1

    heute = today_iso()
    if os.environ.get("FAST") and str(data.get("checkedAt", ""))[:10] == heute:
        print(f"Quellen heute bereits abgefragt (checkedAt {data['checkedAt']}) "
              "– übersprungen (FAST-Lauf).")
        return 0

    backfill = "--backfill" in sys.argv[1:] or bool(os.environ.get("BACKFILL"))
    if backfill:
        print(f"Backfill: Monatswerte ab {RANGE_START} für Jahresdurchschnitte und -spannen.")
    changed, delivered = update(data, backfill=backfill)
    if delivered == 0:
        log_err("unternehmen: keine Quelle lieferte Daten – unternehmen.json bleibt unverändert.")
        return 1
    data["checkedAt"] = now_iso()
    if changed:
        data["updated"] = heute
        data["updatedAt"] = now_iso()
    write_atomic(DATA_FILE, data)
    print("unternehmen.json geschrieben." + ("" if changed else " (keine Wertänderungen – nur checkedAt)"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
