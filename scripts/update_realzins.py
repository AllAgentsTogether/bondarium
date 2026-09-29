#!/usr/bin/env python3
"""Schreibt realzins.json – Bundrendite, Inflation und Realzins seit 1970 sowie die Inflationserwartung
des Marktes aus den inflationsindexierten Bundesanleihen. Seite: realzins.html (Menü „Einordnen“).

Quellen (amtlich, kostenlos, ohne Schlüssel):
- Bundrendite 10 Jahre, Monatsdurchschnitte seit 01/1970: OECD, Main Economic Indicators, „Long-term
  interest rates“ Deutschland (SDMX, dieselbe Reihe wie auf renditen.html; Quelle der OECD ist die
  Bundesbank). Laufender Monat und Tageswert: Deutsche Bundesbank, aus der Zinsstruktur abgeleitete
  Rendite einer 10-jährigen Bundesanleihe mit jährlichem Kupon (BBSIS ZAR, täglich) – dieselbe Reihe wie
  der Tageswert auf renditen.html (seit 27.09.2026; vorher Nullkupon-Rendite ZST, meist einige Hundertstel
  höher). Rückfall auf ZST 10 Jahre, falls ZAR ausfällt.
- Inflation (Verbraucherpreisindex, Veränderung gegen Vorjahresmonat bzw. Jahresteuerung):
  ab 1991 Deutschland, Index 2020 = 100, monatlich und jährlich aus der Bundesbank-Datenbank
  (BBDP1, Daten des Statistischen Bundesamts); 1969–1991 früheres Bundesgebiet, „Preisindex für die
  Lebenshaltung aller privaten Haushalte“ (1995 = 100) aus Destatis, Verbraucherpreisindex – Lange
  Reihen ab 1948 – als unveränderliche Konstanten unten im Skript (WEST_INDEX, WEST_JAHR). So ergibt
  sich die amtliche lange Reihe: bis 1991 früheres Bundesgebiet, ab 1992 Deutschland.
- Inflationserwartung: Bundesbank BBSSY – Realrendite der drei börsennotierten inflationsindexierten
  Bundesanleihen (2030, 2033, 2046) – und die nominale Bundrendite gleicher Restlaufzeit aus der
  Svensson-Kurve (BBSIS, Restlaufzeiten 0,5–30 Jahre, linear interpoliert). Breakeven = nominal − real
  (BERECHNET). Die Bundesbank veröffentlicht den Tageswert am Abend, der 10-Uhr-Lauf holt den Vortag.

Struktur realzins.json:
  {"updated", "updatedAt", "checkedAt", "stand": {"zins": "JJJJ-MM-TT", "vpi": "JJJJ-MM", "linker": "JJJJ-MM-TT"},
   "monate": [["1970-01", bund10, inflation], …],   # Monatsdurchschnitt Bund 10 J. in %, Inflation ggü. Vorjahresmonat in %
                                                     # (null, solange der Monat noch nicht veröffentlicht ist)
   "jahre":  [[1970, bund10, inflation], …],         # Jahresdurchschnitt bzw. Jahresteuerung; laufendes Jahr bis zum letzten Monat
   "laufend": {"jahr": 2026, "bis": "2026-09"},       # bis wohin das laufende Jahr reicht
   "heute":  {"zins10": ["JJJJ-MM-TT", wert], "vpi": ["JJJJ-MM", wert],
              "linker": [{"isin", "name", "faellig", "real", "nominal", "breakeven", "datum"}, …]}}
Der Realzins (nominal − Inflation) wird auf der Seite gerechnet. Datei ~25 KB, wird per inline_data.py eingebettet.

Schutz: Bleibt eine Quelle aus, behält ihr Teil den alten Stand; Werte außerhalb −5…25 % (Zins) bzw.
−5…30 % (Inflation) oder eine Reihe kürzer als 90 % des Vorbestands lassen die Datei unverändert.

Aufruf: python scripts/update_realzins.py
"""

import csv
import datetime
import io
import json
import sys
from collections import defaultdict
from pathlib import Path

from _common import get_with_retry, log_err, now_iso, today_iso, write_atomic

OUT = Path(__file__).resolve().parent.parent / "realzins.json"

OECD = ("https://sdmx.oecd.org/public/rest/data/OECD.SDD.STES,DSD_STES@DF_FINMARK,4.0/"
        "DEU.M.IRLT.PA.....?startPeriod=1970-01&format=csvfilewithlabels")
OECD_H = {"User-Agent": "bondarium.de Realzins (Datenaufbereitung)", "Accept": "text/csv,*/*"}
BUBA = "https://api.statistiken.bundesbank.de/rest/data/{reihe}?detail=dataonly{extra}"
BUBA_H = {"Accept": "application/vnd.sdmx.data+csv;version=1.0.0",
          "User-Agent": "bondarium.de Realzins (Datenaufbereitung)"}
R_KURVE = "BBSIS/D.I.ZST.ZI.EUR.S1311.B.A604..R.A.A._Z._Z.A"      # alle Restlaufzeiten (R005X, R01XX … R30XX)
R_ZAR10 = "BBSIS/D.I.ZAR.ZI.EUR.S1311.B.A604.R10XX.R.A.A._Z._Z.A"   # 10 Jahre, jährlicher Kupon – wie renditen.html
R_VPI_M = "BBDP1/M.DE.N.VPI.C.A00000.I20.A"
R_VPI_A = "BBDP1/A.DE.N.VPI.C.A00000.I20.A"
R_REAL = "BBSSY/D.REN.EUR..."                                      # Renditen aller Bundeswertpapiere (ISIN in Spalte BBK_SEIS_ISIN)
LINKER = [   # inflationsindexierte Bundesanleihen (Realrendite laut Bundesbank); der Bund gibt seit 2024 keine neuen aus
    ("DE0001030559", "Bund inflationsindexiert 0,50 % 2030", "2030-04-15"),
    ("DE0001030583", "Bund inflationsindexiert 0,10 % 2033", "2033-04-15"),
    ("DE0001030575", "Bund inflationsindexiert 0,10 % 2046", "2046-04-15"),
]
ZINS_LO, ZINS_HI = -5.0, 25.0
INFL_LO, INFL_HI = -5.0, 30.0

# Destatis, Verbraucherpreisindex – Lange Reihen ab 1948 (Tabelle 61111-0001 ff.): Preisindex für die Lebenshaltung
# aller privaten Haushalte, früheres Bundesgebiet, 1995 = 100, Monatswerte (Januar … Dezember). Unveränderlich.
WEST_INDEX = {
    1969: [38.8, 39.0, 39.1, 39.1, 39.1, 39.1, 39.1, 39.1, 39.1, 39.1, 39.2, 39.5],
    1970: [39.9, 40.0, 40.2, 40.4, 40.4, 40.5, 40.5, 40.5, 40.5, 40.7, 40.8, 41.1],
    1971: [41.5, 41.9, 42.1, 42.3, 42.4, 42.6, 42.8, 42.8, 42.9, 43.1, 43.1, 43.3],
    1972: [43.9, 44.0, 44.3, 44.5, 44.5, 44.7, 45.0, 45.0, 45.5, 45.6, 45.9, 46.1],
    1973: [46.6, 46.9, 47.2, 47.5, 47.9, 48.1, 48.3, 48.3, 48.3, 48.7, 49.3, 49.7],
    1974: [50.1, 50.5, 50.6, 51.0, 51.2, 51.4, 51.6, 51.7, 51.8, 52.1, 52.5, 52.6],
    1975: [53.1, 53.4, 53.6, 54.1, 54.4, 54.8, 54.8, 54.7, 55.0, 55.1, 55.2, 55.4],
    1976: [55.9, 56.2, 56.4, 56.7, 56.8, 56.9, 56.8, 56.9, 57.0, 57.1, 57.3, 57.5],
    1977: [58.1, 58.3, 58.5, 58.7, 58.9, 59.2, 59.1, 59.1, 59.2, 59.2, 59.3, 59.4],
    1978: [59.9, 60.1, 60.2, 60.5, 60.6, 60.8, 60.7, 60.6, 60.5, 60.6, 60.8, 60.9],
    1979: [61.6, 61.7, 62.1, 62.4, 62.5, 62.9, 63.3, 63.3, 63.6, 63.7, 64.1, 64.2],
    1980: [64.6, 65.4, 65.7, 66.0, 66.4, 66.5, 66.6, 66.7, 66.7, 66.8, 67.3, 67.8],
    1981: [68.4, 69.0, 69.5, 69.8, 70.2, 70.5, 70.9, 71.1, 71.4, 71.8, 72.2, 72.3],
    1982: [73.0, 73.0, 73.0, 73.3, 73.8, 74.6, 74.7, 74.6, 74.9, 75.3, 75.4, 75.6],
    1983: [76.0, 76.0, 76.0, 76.2, 76.3, 76.6, 76.9, 77.1, 77.3, 77.3, 77.5, 77.7],
    1984: [77.9, 78.2, 78.3, 78.4, 78.5, 78.7, 78.6, 78.5, 78.6, 79.0, 79.1, 79.2],
    1985: [79.6, 80.0, 80.3, 80.3, 80.3, 80.3, 80.3, 80.1, 80.2, 80.3, 80.3, 80.4],
    1986: [80.7, 80.6, 80.3, 80.3, 80.3, 80.3, 80.1, 79.8, 79.9, 79.6, 79.5, 79.6],
    1987: [80.1, 80.2, 80.2, 80.3, 80.3, 80.4, 80.4, 80.3, 80.3, 80.3, 80.3, 80.4],
    1988: [80.8, 81.0, 81.0, 81.1, 81.3, 81.4, 81.4, 81.3, 81.4, 81.5, 81.8, 81.9],
    1989: [82.7, 82.9, 83.0, 83.5, 83.6, 83.7, 83.6, 83.6, 83.7, 84.0, 84.2, 84.4],
    1990: [84.9, 85.2, 85.2, 85.4, 85.6, 85.7, 85.7, 85.9, 86.2, 86.8, 86.7, 86.7],
    1991: [87.3, 87.7, 87.7, 87.9, 88.3, 88.7, 89.9, 89.8, 89.8, 89.9, 90.3, 90.4],
}
# Jahresteuerung früheres Bundesgebiet (Destatis, dieselbe Tabelle), in %
WEST_JAHR = {1970: 3.6, 1971: 5.2, 1972: 5.4, 1973: 7.1, 1974: 6.9, 1975: 6.0, 1976: 4.2, 1977: 3.7, 1978: 2.7,
             1979: 4.1, 1980: 5.4, 1981: 6.3, 1982: 5.2, 1983: 3.2, 1984: 2.5, 1985: 2.0, 1986: -0.1, 1987: 0.2,
             1988: 1.2, 1989: 2.8, 1990: 2.6, 1991: 3.7}


def buba_csv(reihe: str, extra: str = "") -> list[dict]:
    text = get_with_retry(BUBA.format(reihe=reihe, extra=extra), headers=BUBA_H, timeout=90).decode("utf-8-sig", "replace")
    return list(csv.DictReader(io.StringIO(text), delimiter=";"))


def oecd_monate() -> dict[str, float]:
    """OECD: {JJJJ-MM: Bund 10 J. Monatsdurchschnitt} seit 1970."""
    text = get_with_retry(OECD, headers=OECD_H, timeout=120).decode("utf-8", "replace")
    out = {}
    for rec in csv.DictReader(io.StringIO(text)):
        try:
            out[rec["TIME_PERIOD"]] = float(rec["OBS_VALUE"])
        except (KeyError, TypeError, ValueError):
            continue
    if len(out) < 600:
        raise RuntimeError(f"OECD: nur {len(out)} Monatswerte")
    return out


def bundesbank_kurve(seit: str) -> dict[str, dict[float, float]]:
    """{Datum: {Restlaufzeit in Jahren: Rendite}} aus der Svensson-Kurve (alle Laufzeiten)."""
    out: dict[str, dict[float, float]] = defaultdict(dict)
    for rec in buba_csv(R_KURVE, f"&startPeriod={seit}"):
        try:
            code, datum, wert = rec["BBK_SEIS_MATURITY"], rec["TIME_PERIOD"], float(rec["OBS_VALUE"])
        except (KeyError, TypeError, ValueError):
            continue
        lz = 0.5 if code == "R005X" else float(code[1:3]) if code[1:3].isdigit() else None
        if lz:
            out[datum][lz] = wert
    if not out:
        raise RuntimeError("Bundesbank BBSIS: keine Tageswerte")
    return out


def bundesbank_zar10(seit: str) -> dict[str, float]:
    """{Datum: Rendite} der 10-jährigen Bundesanleihe mit jährlichem Kupon (ZAR) – dieselbe Reihe wie renditen.html."""
    out: dict[str, float] = {}
    for rec in buba_csv(R_ZAR10, f"&startPeriod={seit}"):
        try:
            out[rec["TIME_PERIOD"]] = float(rec["OBS_VALUE"])
        except (KeyError, TypeError, ValueError):
            continue
    if not out:
        raise RuntimeError("Bundesbank BBSIS ZAR: keine Tageswerte")
    return out


def bundesbank_vpi() -> tuple[dict[str, float], dict[int, float]]:
    """Monatsindex {JJJJ-MM: Index} und Jahresindex {JJJJ: Index}, Deutschland 2020 = 100, ab 1991."""
    m = {r["TIME_PERIOD"]: float(r["OBS_VALUE"]) for r in buba_csv(R_VPI_M) if r.get("OBS_VALUE") not in (None, "", ".")}
    a = {int(r["TIME_PERIOD"]): float(r["OBS_VALUE"]) for r in buba_csv(R_VPI_A) if r.get("OBS_VALUE") not in (None, "", ".")}
    if len(m) < 400 or len(a) < 30:
        raise RuntimeError(f"Bundesbank VPI: Reihe zu kurz ({len(m)} Monate, {len(a)} Jahre)")
    return m, a


def realrenditen() -> dict[str, tuple[str, float]]:
    """{ISIN: (Datum, Realrendite)} der inflationsindexierten Bundesanleihen (jüngster Wert)."""
    out = {}
    for rec in buba_csv(R_REAL, "&lastNObservations=1"):
        try:
            isin, datum, wert = rec["BBK_SEIS_ISIN"], rec["TIME_PERIOD"], float(rec["OBS_VALUE"])
        except (KeyError, TypeError, ValueError):
            continue
        if any(isin == l[0] for l in LINKER):
            out[isin] = (datum, wert)
    return out


def inflation_monate(vpi_m: dict[str, float]) -> dict[str, float]:
    """Veränderung gegen Vorjahresmonat in %: 1970–1991 früheres Bundesgebiet, ab 1992 Deutschland."""
    idx = {f"{j}-{i + 1:02d}": v for j, werte in WEST_INDEX.items() for i, v in enumerate(werte)}
    out = {}
    for j in range(1970, 1992):
        for mo in range(1, 13):
            k, v = f"{j}-{mo:02d}", f"{j - 1}-{mo:02d}"
            out[k] = round((idx[k] / idx[v] - 1) * 100, 1)
    for k, wert in vpi_m.items():
        v = f"{int(k[:4]) - 1}{k[4:]}"
        if k >= "1992-01" and v in vpi_m:
            out[k] = round((wert / vpi_m[v] - 1) * 100, 1)
    return out


def inflation_jahre(vpi_a: dict[int, float]) -> dict[int, float]:
    out = dict(WEST_JAHR)
    for j, wert in vpi_a.items():
        if j >= 1992 and (j - 1) in vpi_a:
            out[j] = round((wert / vpi_a[j - 1] - 1) * 100, 1)
    return out


def interpoliert(kurve: dict[float, float], jahre: float) -> float | None:
    pts = sorted(kurve.items())
    if not pts or jahre < pts[0][0] or jahre > pts[-1][0]:
        return None
    for (a, ra), (b, rb) in zip(pts, pts[1:]):
        if a <= jahre <= b:
            return ra if b == a else ra + (rb - ra) * (jahre - a) / (b - a)
    return None


def main() -> int:
    alt = {}
    if OUT.exists():
        try:
            alt = json.loads(OUT.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            alt = {}
    heute = dict(alt.get("heute", {}))
    stand = dict(alt.get("stand", {}))
    monate, jahre, laufend = alt.get("monate"), alt.get("jahre"), alt.get("laufend")
    fehler = 0

    # 1) Bund 10 Jahre: OECD-Monate + Bundesbank-Tage (laufender Monat, Tageswert)
    seit = (datetime.date.today() - datetime.timedelta(days=100)).replace(day=1).isoformat()
    try:
        kurve = bundesbank_kurve(seit)   # Svensson-Kurve: für die Breakeven-Rechnung (nominal gleicher Restlaufzeit)
    except Exception as e:  # noqa: BLE001
        log_err(f"Realzins: Bundesbank-Zinskurve nicht abrufbar ({e}) – Breakeven bleibt alt.")
        kurve = {}
        fehler += 1
    # Tageswert und laufender Monat: ZAR 10 Jahre (wie renditen.html); Rückfall: ZST 10 Jahre aus der Kurve
    try:
        zins10 = bundesbank_zar10(seit)
    except Exception as e:  # noqa: BLE001
        log_err(f"Realzins: Bundesbank ZAR 10 J. nicht abrufbar ({e}) – Rückfall auf die Svensson-Kurve.")
        zins10 = {d: w[10.0] for d, w in kurve.items() if 10.0 in w}
    tage = sorted(zins10)
    if tage:
        letzter = tage[-1]
        heute["zins10"] = [letzter, round(zins10[letzter], 2)]
        stand["zins"] = letzter
    else:
        log_err("Realzins: kein Tageswert Bund 10 J. – Tageswert bleibt alt.")
        fehler += 1
    try:
        oecd = oecd_monate()
    except Exception as e:  # noqa: BLE001
        log_err(f"Realzins: OECD nicht abrufbar ({e}) – Monatsreihe bleibt alt.")
        oecd = {m[0]: m[1] for m in (monate or []) if m[1] is not None}
        fehler += 1
    # fehlende jüngste Monate (OECD hinkt 1–2 Monate nach) und laufender Monat aus den Bundesbank-Tagen
    je_monat = defaultdict(list)
    for d in tage:
        je_monat[d[:7]].append(zins10[d])
    zins_m = dict(oecd)
    for m, werte in je_monat.items():
        if m not in zins_m:
            zins_m[m] = round(sum(werte) / len(werte), 2)

    # 2) Inflation
    try:
        vpi_m, vpi_a = bundesbank_vpi()
        infl_m, infl_a = inflation_monate(vpi_m), inflation_jahre(vpi_a)
        letzter_vpi = max(vpi_m)
        heute["vpi"] = [letzter_vpi, infl_m[letzter_vpi]]
        stand["vpi"] = letzter_vpi
    except Exception as e:  # noqa: BLE001
        log_err(f"Realzins: Bundesbank-VPI nicht abrufbar ({e}) – Inflation bleibt alt.")
        infl_m = {m[0]: m[2] for m in (monate or []) if m[2] is not None}
        infl_a = {j[0]: j[2] for j in (jahre or []) if j[2] is not None}
        fehler += 1

    # 3) Reihen zusammensetzen
    neu_monate = [[m, round(zins_m[m], 2), infl_m.get(m)] for m in sorted(zins_m) if m >= "1970-01"]
    summe = defaultdict(list)
    for m, z, _ in neu_monate:
        summe[int(m[:4])].append(z)
    dieses = int(neu_monate[-1][0][:4]) if neu_monate else datetime.date.today().year
    neu_jahre = []
    for j in sorted(summe):
        infl = infl_a.get(j)
        if j == dieses and infl is None:   # laufendes Jahr: Durchschnitt der bisher veröffentlichten Monatsraten
            raten = [r for m, _, r in neu_monate if int(m[:4]) == j and r is not None]
            infl = round(sum(raten) / len(raten), 1) if raten else None
        neu_jahre.append([j, round(sum(summe[j]) / len(summe[j]), 2), infl])
    neu_laufend = {"jahr": dieses, "bis": neu_monate[-1][0]} if neu_monate else laufend

    # 4) Inflationserwartung aus den inflationsindexierten Bundesanleihen
    try:
        real = realrenditen()
        linker = []
        for isin, name, faellig in LINKER:
            if isin not in real:
                continue
            datum, r = real[isin]
            k = kurve.get(datum) or (kurve[max(kurve)] if kurve else None)
            jahre_rest = (datetime.date.fromisoformat(faellig) - datetime.date.fromisoformat(datum)).days / 365.25
            nominal = interpoliert(k, jahre_rest) if k else None
            linker.append({"isin": isin, "name": name, "faellig": faellig, "datum": datum, "real": round(r, 2),
                           "nominal": None if nominal is None else round(nominal, 2),
                           "breakeven": None if nominal is None else round(nominal - r, 2)})
        if linker:
            heute["linker"] = linker
            stand["linker"] = max(l["datum"] for l in linker)
        else:
            raise RuntimeError("keine Realrenditen gefunden")
    except Exception as e:  # noqa: BLE001
        log_err(f"Realzins: Realrenditen nicht abrufbar ({e}) – Inflationserwartung bleibt alt.")
        fehler += 1

    # 5) Plausibilität und Schutz
    schlecht = [m for m in neu_monate if not (ZINS_LO < m[1] < ZINS_HI) or (m[2] is not None and not (INFL_LO < m[2] < INFL_HI))]
    if schlecht:
        log_err(f"Realzins: {len(schlecht)} Monatswerte außerhalb der Grenzen (z. B. {schlecht[0]}) – Datei bleibt.")
        return 1
    if monate and len(neu_monate) < 0.9 * len(monate):
        log_err(f"Realzins: Monatsreihe schrumpft ({len(monate)} → {len(neu_monate)}) – Datei bleibt.")
        return 1
    if not neu_monate or len(neu_jahre) < 50:
        log_err("Realzins: Reihen leer oder zu kurz – Datei bleibt.")
        return 1

    geaendert = (neu_monate != monate or neu_jahre != jahre or heute != alt.get("heute"))
    neu = {
        "updated": today_iso() if geaendert else alt.get("updated", today_iso()),
        "updatedAt": now_iso() if geaendert else alt.get("updatedAt", now_iso()),
        "checkedAt": now_iso(),
        "stand": stand,
        "quelle": {
            "zins": "Bund 10 Jahre: OECD Main Economic Indicators (Monatsdurchschnitte, Daten der Bundesbank); Tageswert und laufender Monat: Deutsche Bundesbank, aus der Zinsstruktur abgeleitete Rendite einer 10-jährigen Bundesanleihe mit jährlichem Kupon (wie Staatsanleihen seit 1970)",
            "vpi": "Verbraucherpreisindex: bis 1991 früheres Bundesgebiet (Destatis, Lange Reihen ab 1948), ab 1992 Deutschland (Destatis über Bundesbank BBDP1, 2020 = 100)",
            "linker": "Realrendite inflationsindexierter Bundesanleihen: Deutsche Bundesbank (BBSSY); nominale Vergleichsrendite gleicher Restlaufzeit aus der Svensson-Kurve; Breakeven = nominal − real (berechnet)",
        },
        "monate": neu_monate, "jahre": neu_jahre, "laufend": neu_laufend, "heute": heute,
    }
    write_atomic(OUT, neu, indent=None)
    print(f"realzins.json: {len(neu_monate)} Monate ({neu_monate[0][0]} … {neu_monate[-1][0]}), {len(neu_jahre)} Jahre, "
          f"Bund 10 J. {heute.get('zins10')}, Inflation {heute.get('vpi')}, "
          f"Linker {[(l['isin'][-4:], l['real'], l['breakeven']) for l in heute.get('linker', [])]}"
          + (f" – {fehler} Quelle(n) ausgefallen" if fehler else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
