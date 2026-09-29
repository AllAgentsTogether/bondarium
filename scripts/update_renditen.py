#!/usr/bin/env python3
"""Aktualisiert renditen.json – 10-Jahres-Staatsanleihenrenditen der acht
größten Volkswirtschaften (Seite renditen.html).

Läuft seit 09/2026 nur noch im vollen Lauf (Workflow: VOLL=1, nächtlich nach
US-Handelsschluss bzw. manueller 'voll'-Start) – die 3-Stunden-Läufe (FAST=1)
committen nicht, dort wäre jeder Lauf ein erneuter Abruf aller Quellen. Die
FAST-Selbstdrosselung (höchstens ein Abruf pro Tag, gemessen an checkedAt)
bleibt als Schutz erhalten, falls das Skript doch einmal in einem FAST-Lauf
gestartet wird.

Zeitstempel in renditen.json:
- checkedAt: ISO-Zeitstempel JEDES Laufs, der die Quellen befragt hat
  (auch ohne Wertänderung) – Grundlage der FAST-Drossel.
- updated/updatedAt: nur, wenn sich mindestens ein Wert geändert hat
  (neuer latest-Wert oder neu festgeschriebenes Jahr) – zeigt also den echten
  Datenstand, nicht das Datum des letzten Abrufversuchs.

Quellen:
- OECD SDMX (monatliche Langfristzinsen, alle acht Länder): Grundversorgung –
  jüngster Monatswert je Land + Festschreiben abgeschlossener Jahre als
  Jahresdurchschnitt in countries[<land>].annual.
- Börsentäglich, wo eine offizielle freie Quelle existiert:
  USA U.S. Treasury (Daily Par Yield Curve), Deutschland Bundesbank
  (Zinsstruktur-Rendite 10 J.), Japan Finanzministerium (JGB-CSV),
  China Eastmoney-Datacenter (spiegelt die ChinaBond-Renditekurve).
- Großbritannien, Frankreich, Italien, Indien: nur monatlich (OECD).

Die eingebetteten historischen Jahresdurchschnitte (1970 ff.) stehen in
renditen.html und bleiben unberührt; renditen.json ergänzt nur "latest" je
Land sowie neu abgeschlossene Jahre.

Jahresspanne (Hoch-Tief-Band im Chart, seit 09/2026): countries[<land>].range
enthält je Jahr [Tief, Hoch] der OECD-MONATSWERTE ("JJJJ": [lo, hi]) – also
das niedrigste und höchste Monatsmittel eines Jahres, keine Tagesextreme.
Abgeschlossene Jahre werden einmal festgeschrieben (12 Monatswerte), das
laufende Jahr wird bei jedem Lauf aus den bisher vorliegenden Monaten neu
gebildet. Länder ohne OECD-Monatsreihe in frühen Jahren (Japan vor 1989,
Italien vor 1992, China/Indien vor ca. 2005/2012) haben dort keine Spanne –
der Chart zeigt dann nur die Durchschnittslinie.

Einmaliges Nachladen der Historie ab 1970 (dauert ein paar Sekunden):

    python3 scripts/update_renditen.py --backfill

Der Backfill ergänzt nur fehlende Jahre (ersetzt bestehende nicht) und
schreibt renditen.json sonst wie ein normaler Lauf.
"""

import csv
import datetime
import io
import json
import os
import re
import sys
from pathlib import Path

from _common import get_with_retry, log_err, now_iso, plausible, today_iso, write_atomic

DATA_FILE = Path(__file__).resolve().parent.parent / "renditen.json"

OECD_URL = (
    "https://sdmx.oecd.org/public/rest/data/OECD.SDD.STES,DSD_STES@DF_FINMARK,4.0/"
    "USA+DEU+FRA+GBR+ITA+JPN+CHN+IND.M.IRLT.PA.....?startPeriod={start}&format=csvfilewithlabels"
)
TREASURY_URL = (
    "https://home.treasury.gov/resource-center/data-chart-center/interest-rates/"
    "daily-treasury-rates.csv/{year}/all"
    "?type=daily_treasury_yield_curve&field_tdr_date_value={year}&page&_format=csv"
)
BUBA_URL = (
    "https://api.statistiken.bundesbank.de/rest/download/BBSIS/"
    "D.I.ZAR.ZI.EUR.S1311.B.A604.R10XX.R.A.A._Z._Z.A?format=csv&lang=de"
)
MOF_URL = "https://www.mof.go.jp/english/policy/jgbs/reference/interest_rate/jgbcme.csv"
EASTMONEY_URL = (
    "https://datacenter.eastmoney.com/api/data/get"
    "?type=RPTA_WEB_TREASURYYIELD&sty=ALL&st=SOLAR_DATE&sr=-1&ps=20&p=1"
)

OECD_AREA = {"us": "USA", "cn": "CHN", "de": "DEU", "in": "IND",
             "jp": "JPN", "gb": "GBR", "fr": "FRA", "it": "ITA"}
KEYS = list(OECD_AREA)

UA = {"User-Agent": "Mozilla/5.0 (Datenaktualisierung Anleihenrenditen)"}


def _fetch(url: str, timeout: int = 40) -> bytes:
    return get_with_retry(url, headers=UA, timeout=timeout)


def _plausibel(key: str, new: float, old) -> bool:
    """Renditen bewegen sich um wenige Basispunkte pro Tag; ein Sprung von mehr
    als 2,5 Prozentpunkten gegenüber dem letzten Stand ist fast sicher ein
    Parser-/Quellenfehler. (Relative Prüfung taugt bei Renditen nahe null nicht –
    daher die absolute Schranke max_abs des gemeinsamen Helfers.)"""
    return plausible(new, old, f"renditen {key}", max_abs=2.5)


def _is_day(date_str) -> bool:
    """Tageswert "JJJJ-MM-TT" (Tagesquellen Treasury/Bundesbank/MoF/Eastmoney)."""
    return bool(re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(date_str)))


def _is_month(date_str) -> bool:
    """Monatswert "JJJJ-MM" (OECD)."""
    return bool(re.fullmatch(r"\d{4}-\d{2}", str(date_str)))


def darf_ersetzen(old_date, new_date) -> bool:
    """Darf der gespeicherte latest-Wert (old_date) durch einen neuen Wert mit
    new_date ersetzt werden? Regeln:
    - ohne gespeichertes Datum: immer;
    - ein Tageswert wird NIE durch einen Monatswert desselben (oder eines
      älteren) Monats ersetzt – der Tageswert ist präziser und aktueller
      (typischer Fall: Tagesquelle fällt einen Lauf lang aus, OECD liefert den
      Monat, in dem der Tageswert liegt → früher wurde der Tageswert durch den
      gröberen Monatswert überschrieben und beim nächsten Lauf wieder zurück);
    - ein Monatswert darf durch einen Tageswert desselben Monats ersetzt werden
      (präziser) und durch jeden späteren Wert;
    - sonst nie mit älterem Datum überschreiben (Vergleich auf der gemeinsamen
      Präfixlänge, damit "2026-08" gegen "2026-08-26" sauber vergleichbar ist)."""
    if not old_date:
        return True
    old_s, new_s = str(old_date), str(new_date)
    if _is_month(new_s) and _is_day(old_s):
        return new_s > old_s[:7]          # nur ein SPÄTERER Monat darf den Tageswert ablösen
    return not new_s < old_s[:len(new_s)]


# ---------- Quellen ----------

def fetch_oecd(start_year: int) -> dict[str, dict[str, float]]:
    """Monatswerte {'us': {'2026-06': 4.47, ...}, ...} ab start_year."""
    text = _fetch(OECD_URL.format(start=start_year), timeout=60).decode("utf-8", "replace")
    area_to_key = {v: k for k, v in OECD_AREA.items()}
    out: dict[str, dict[str, float]] = {k: {} for k in KEYS}
    for rec in csv.DictReader(io.StringIO(text)):
        key = area_to_key.get(rec.get("REF_AREA", ""))
        per = rec.get("TIME_PERIOD", "")
        if not key or not re.fullmatch(r"\d{4}-\d{2}", per):
            continue
        try:
            out[key][per] = float(rec["OBS_VALUE"])
        except (KeyError, ValueError, TypeError):
            continue
    return out


def fetch_us() -> tuple[str, float] | None:
    """Jüngste 10-Jahres-Rendite aus der Daily Par Yield Curve des U.S. Treasury."""
    year = datetime.date.today().year
    text = _fetch(TREASURY_URL.format(year=year)).decode("utf-8", "replace")
    rows = []
    for rec in csv.DictReader(io.StringIO(text)):
        try:
            m, d, y = rec["Date"].split("/")
            rows.append((f"{y}-{int(m):02d}-{int(d):02d}", float(rec["10 Yr"])))
        except (KeyError, ValueError, TypeError):
            continue
    return max(rows) if rows else None


def fetch_de() -> tuple[str, float] | None:
    """Jüngste Rendite 10-jähriger Bundesanleihen (Bundesbank-Zinsstruktur, täglich)."""
    text = _fetch(BUBA_URL).decode("utf-8-sig", "replace")
    rows = []
    for line in text.splitlines():
        parts = line.split(";")
        if len(parts) < 2 or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", parts[0]):
            continue
        try:
            rows.append((parts[0], float(parts[1].replace(",", "."))))
        except ValueError:
            continue  # "." = kein Wert (Wochenende/Feiertag)
    return max(rows) if rows else None


def fetch_jp() -> tuple[str, float] | None:
    """Jüngste 10-Jahres-JGB-Rendite (Finanzministerium Japan, Spalte '10Y')."""
    text = _fetch(MOF_URL).decode("shift_jis", "replace")
    rows = []
    for rec in csv.reader(io.StringIO(text)):
        if not rec or not re.fullmatch(r"\d{4}/\d{1,2}/\d{1,2}", rec[0] or ""):
            continue
        if len(rec) > 10 and rec[10] not in ("-", ""):
            try:
                y, m, d = rec[0].split("/")
                rows.append((f"{y}-{int(m):02d}-{int(d):02d}", float(rec[10])))
            except ValueError:
                continue
    return max(rows) if rows else None


def fetch_cn() -> tuple[str, float] | None:
    """Jüngste 10-Jahres-Rendite chinesischer Staatsanleihen (Feld EMM00166466 =
    ChinaBond-Renditekurve 10 J. im Eastmoney-Datacenter)."""
    raw = json.loads(_fetch(EASTMONEY_URL).decode("utf-8", "replace"))
    rows = []
    for rec in (raw.get("result") or {}).get("data") or []:
        v = rec.get("EMM00166466")
        date = str(rec.get("SOLAR_DATE", ""))[:10]
        if v is None or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", date):
            continue
        rows.append((date, round(float(v), 2)))
    return max(rows) if rows else None


# ---------- Zusammenführen ----------

def month_of(date_str: str) -> str:
    return date_str[:7]


RANGE_START = 1970   # Beginn der Chart-Zeitachse (renditen.html, YEAR0)


def update_ranges(key: str, c: dict, monthly: dict[str, float], today: datetime.date) -> bool:
    """Jahresspanne [Tief, Hoch] aus Monatswerten in c["range"] pflegen.
    Abgeschlossene Jahre nur ergänzen (12 Monatswerte nötig, nie überschreiben),
    das laufende Jahr bei jedem Lauf neu aus den vorliegenden Monaten bilden.
    Rückgabe: True, wenn sich etwas geändert hat."""
    rng = c.setdefault("range", {})
    by_year: dict[str, list[float]] = {}
    for per, v in monthly.items():
        if int(per[:4]) >= RANGE_START:
            by_year.setdefault(per[:4], []).append(v)
    changed = False
    for yr, vals in sorted(by_year.items()):
        current = int(yr) == today.year
        if not current and (len(vals) < 12 or yr in rng):
            continue
        span = [round(min(vals), 2), round(max(vals), 2)]
        if rng.get(yr) == span:
            continue
        rng[yr] = span
        changed = True
        if not current:
            print(f"{key}: Spanne {yr} festgeschrieben ({span[0]}–{span[1]} %).")
    # laufendes Jahr ohne Monatswert (Jahresanfang, OECD noch leer): alten Stand behalten
    if changed:
        c["range"] = dict(sorted(rng.items()))
    return changed


def update(data: dict, backfill: bool = False) -> tuple[bool, int]:
    """Führt OECD- und Tagesquellen zusammen. Rückgabe (changed, delivered):
    changed = mindestens ein Wert in data geändert; delivered = Anzahl Länder,
    für die überhaupt eine Quelle Daten lieferte (0 = Totalausfall).
    backfill: OECD-Monatswerte ab 1970 statt der letzten zwei Jahre abrufen
    (einmalig, für die Jahresspannen der Historie)."""
    today = datetime.date.today()
    countries = data.setdefault("countries", {})
    changed = False
    delivered = 0

    try:
        oecd = fetch_oecd(RANGE_START if backfill else today.year - 2)
    except Exception as e:
        log_err(f"OECD nicht abrufbar: {e}")
        oecd = {k: {} for k in KEYS}

    daily_fetchers = {"us": fetch_us, "de": fetch_de, "jp": fetch_jp, "cn": fetch_cn}

    for key in KEYS:
        c = countries.setdefault(key, {})
        old_latest = c.get("latest") or {}

        # 1) Abgeschlossene Jahre als Jahresdurchschnitt festschreiben (12 Monatswerte)
        annual = c.setdefault("annual", {})
        monthly = oecd.get(key, {})
        by_year: dict[str, list[float]] = {}
        for per, v in monthly.items():
            by_year.setdefault(per[:4], []).append(v)
        for yr, vals in sorted(by_year.items()):
            # nur jüngst abgeschlossene Jahre – die Historie steht in renditen.html
            # (teils andere Quellen als OECD) und wird auch im Backfill nicht ersetzt
            if today.year - 2 <= int(yr) < today.year and len(vals) == 12 and yr not in annual:
                annual[yr] = round(sum(vals) / len(vals), 2)
                print(f"{key}: Jahresdurchschnitt {yr} festgeschrieben ({annual[yr]} %).")
                changed = True
        # 1b) Jahresspanne [Tief, Hoch] der Monatswerte (Hoch-Tief-Band im Chart)
        if update_ranges(key, c, monthly, today):
            changed = True

        # 2) Jüngster Wert: Tagesquelle, sonst jüngster OECD-Monatswert
        best = None  # (datum, wert); Monatsangaben "JJJJ-MM" sortieren vor jedem Tag des Monats
        if monthly:
            per = max(monthly)
            best = (per, round(monthly[per], 2))
        fetcher = daily_fetchers.get(key)
        if fetcher:
            try:
                daily = fetcher()
            except Exception as e:
                log_err(f"Tagesquelle {key} nicht abrufbar: {e}")
                daily = None
            # Tageswert gewinnt, wenn er mindestens so aktuell ist wie der Monatswert
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
        # Nie mit älterem Datum überschreiben – und einen Tageswert nie durch
        # den OECD-Monatswert desselben Monats ersetzen (siehe darf_ersetzen).
        if not darf_ersetzen(old_latest.get("date"), date):
            print(f"{key}: {value} % (Stand {date}) ersetzt den gespeicherten Stand "
                  f"{old_latest.get('date')} nicht (älter/gröber).")
            continue
        c["latest"] = {"date": date, "yield": value}
        print(f"{key}: {value} % (Stand {date}).")
        changed = True

    return changed, delivered


def main() -> int:
    try:
        data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    except FileNotFoundError:
        data = {"countries": {}}
    except Exception as e:
        log_err(f"renditen.json unlesbar – Abbruch, Datei bleibt unangetastet: {e}")
        return 1

    heute = today_iso()
    # Selbstdrosselung (Schutz): In einem FAST-Lauf reicht ein Abruf pro Tag –
    # gemessen an checkedAt (Datum des letzten Quellen-Abrufs), NICHT an
    # updated, das seit 09/2026 nur noch bei echten Wertänderungen wandert.
    # Der volle Lauf (ohne FAST) fragt die Quellen immer ab.
    if os.environ.get("FAST") and str(data.get("checkedAt", ""))[:10] == heute:
        print(f"Quellen heute bereits abgefragt (checkedAt {data['checkedAt']}) "
              "– übersprungen (FAST-Lauf).")
        return 0

    backfill = "--backfill" in sys.argv[1:] or bool(os.environ.get("BACKFILL"))
    if backfill:
        print("Backfill: OECD-Monatswerte ab 1970 für die Jahresspannen.")
    changed, delivered = update(data, backfill=backfill)
    if delivered == 0:
        # Totalausfall (OECD und alle Tagesquellen): nichts schreiben – kein
        # checkedAt, damit ein späterer Lauf am selben Tag erneut versucht;
        # Exit 1 macht den Ausfall im Workflow-Schritt sichtbar.
        log_err("renditen: keine Quelle lieferte Daten – renditen.json bleibt unverändert.")
        return 1
    data["checkedAt"] = now_iso()  # jeder Abruf-Lauf, auch ohne Wertänderung
    if changed:
        data["updated"] = heute    # echter Datenstand: nur bei Wertänderung
        data["updatedAt"] = now_iso()
    write_atomic(DATA_FILE, data)
    print("renditen.json geschrieben." + ("" if changed else " (keine Wertänderungen – nur checkedAt)"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
