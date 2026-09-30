#!/usr/bin/env python3
"""Schreibt risikoaufschlaege.json – der Risikoaufschlag (Spread) als Zeitreihe:
Euro-Staaten gegen die Bundesanleihe seit 1991 und US-Unternehmensanleihen gegen
die US-Staatsanleihe seit 1984. Seite: risikoaufschlaege.html (Menü „Zinsen“).

Quellen (amtlich bzw. frei, ohne Schlüssel):
- Euro-Staaten: OECD, Main Economic Indicators, „Long-term interest rates“ (10-jährige
  Staatsanleihen, Monatsdurchschnitte) für Deutschland, Italien, Spanien, Frankreich,
  Portugal, Griechenland, Irland, Belgien, Niederlande, Österreich, Finnland – dieselbe
  Reihe wie auf renditen.html und realzins.html. Aufschlag = Rendite des Landes minus
  Rendite Deutschlands im selben Monat (BERECHNET). Die Charts zeigen Italien, Spanien
  und Frankreich seit 03/1991 (ab da hat Italien eine OECD-Monatsreihe); die übrigen
  Länder stehen nur in der Rangliste „heute“. Die OECD veröffentlicht einen Monat rund
  zwei Wochen nach Monatsende; einen Tageswert gibt es für diese Länder nicht.
- USA: Unternehmensanleihen hoher Bonität (AAA/AA/A), 10 Jahre – HQM-Renditekurve des
  US-Finanzministeriums (Spot-Rendite, monatlich seit 01/1984, gemeinfrei; Abruf über FRED,
  Reihe HQMCB10YR, dort „Public Domain: Citation Requested“) minus 10-jährige
  US-Staatsanleihe aus derselben OECD-Reihe wie die Euro-Staaten (Monatsdurchschnitt).
  Aufschlag BERECHNET. Die HQM-Rendite ist eine Spot-Rendite (Nullkupon), die Staatsanleihe
  eine Kuponrendite – der Aufschlag fällt dadurch meist 0,1 bis 0,2 Punkte höher aus.
  Bis 30.09.2026 standen hier Moody's Aaa/Baa (AAA10YM, BAA10YM, AAA10Y, BAA10Y): gestrichen,
  weil Moody's in den Reihen-Notizen bei FRED jede Weiterverbreitung ohne schriftliche
  Zustimmung untersagt. ICE-BofA-Indizes (Hochzins) sind aus demselben Grund nicht dabei.

Struktur:
  {"updated", "updatedAt", "checkedAt",
   "stand": {"laender": "JJJJ-MM", "us": "JJJJ-MM"},
   "quelle": {...},
   "laender": {"monate": [["1991-03", DE, IT, ES, FR], …],   # Renditen in %, null = kein Wert
               "heute": [{"code": "IT", "name": "Italien", "monat": "2026-08", "rendite": 3.99,
                          "aufschlag": 0.81}, …]},           # alle Länder, nach Aufschlag sortiert
   "us": {"monate": [["1984-01", aufschlag, hqm, staat], …], # Aufschlag in Prozentpunkten, Renditen in %
          "heute": ["JJJJ-MM", aufschlag, hqm, staat]}}       # jüngster Monat mit beiden Werten

Schutz: Bleibt eine Quelle aus, behält ihr Teil den alten Stand. Werte außerhalb
−5…40 Punkte (Aufschlag) bzw. −5…40 % (Rendite) oder eine um mehr als 10 % geschrumpfte
Reihe lassen die Datei unverändert. Zwei Abrufe, ~10 s (OECD-Datei ~1,8 MB).

Aufruf: python scripts/update_risikoaufschlaege.py
"""

import csv
import io
import json
import sys
from collections import defaultdict
from pathlib import Path

from _common import get_with_retry, log_err, now_iso, today_iso, write_atomic

OUT = Path(__file__).resolve().parent.parent / "risikoaufschlaege.json"

# Reihenfolge = Spalten in laender.monate (nach DE); Chart-Länder zuerst
LAENDER = [("DE", "DEU", "Deutschland"), ("IT", "ITA", "Italien"), ("ES", "ESP", "Spanien"), ("FR", "FRA", "Frankreich"),
           ("PT", "PRT", "Portugal"), ("GR", "GRC", "Griechenland"), ("IE", "IRL", "Irland"), ("BE", "BEL", "Belgien"),
           ("NL", "NLD", "Niederlande"), ("AT", "AUT", "Österreich"), ("FI", "FIN", "Finnland")]
CHART = ["IT", "ES", "FR"]
START = "1991-03"   # ab hier hat Italien eine OECD-Monatsreihe

US = ("US", "USA")    # 10-jährige US-Staatsanleihe: Vergleichsreihe für die US-Unternehmensanleihen (keine Spalte in laender.monate)
US_START = "1984-01"  # Beginn der HQM-Kurve

OECD = ("https://sdmx.oecd.org/public/rest/data/OECD.SDD.STES,DSD_STES@DF_FINMARK,4.0/"
        + "+".join([a for _, a, _ in LAENDER] + [US[1]]) + ".M.IRLT.PA.....?startPeriod=1970-01&format=csvfilewithlabels")
OECD_H = {"User-Agent": "bondarium.de Risikoaufschlaege (Datenaufbereitung)", "Accept": "text/csv,*/*"}
FRED = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={sid}&cosd={cosd}"
FRED_H = {"User-Agent": "bondarium.de Risikoaufschlaege (Datenaufbereitung)", "Accept": "text/csv,*/*"}
LO, HI = -5.0, 40.0


def oecd() -> dict[str, dict[str, float]]:
    """{Länderkürzel: {JJJJ-MM: Rendite}} aus der OECD-Monatsreihe."""
    text = get_with_retry(OECD, headers=OECD_H, timeout=180).decode("utf-8-sig", "replace")
    iso = {a: k for k, a, _ in LAENDER}
    iso[US[1]] = US[0]
    out: dict[str, dict[str, float]] = defaultdict(dict)
    for rec in csv.DictReader(io.StringIO(text)):
        try:
            k = iso[rec["REF_AREA"]]
            out[k][rec["TIME_PERIOD"]] = round(float(rec["OBS_VALUE"]), 3)
        except (KeyError, TypeError, ValueError):
            continue
    if len(out.get("DE", {})) < 600 or any(len(out.get(k, {})) < 300 for k in CHART):
        raise RuntimeError(f"OECD: Reihen unvollständig ({ {k: len(v) for k, v in out.items()} })")
    return out


def laender(r: dict[str, dict[str, float]]) -> tuple[list, list, str]:
    de = r["DE"]
    monate = []
    for m in sorted(de):
        if m < START:
            continue
        zeile = [m, de[m]] + [r.get(k, {}).get(m) for k, _, _ in LAENDER[1:]]
        monate.append(zeile)
    stand = monate[-1][0]
    heute = []
    for k, _, name in LAENDER[1:]:
        reihe = r.get(k, {})
        # jüngster Monat des Landes, für den auch Deutschland einen Wert hat
        mon = max((m for m in reihe if m in de), default=None)
        if mon is None or mon < monate[-1][0][:4] + "-01":
            continue   # veraltete Reihe: nicht in die Rangliste
        heute.append({"code": k, "name": name, "monat": mon, "rendite": round(reihe[mon], 2),
                      "aufschlag": round(reihe[mon] - de[mon], 2)})
    heute.sort(key=lambda h: -h["aufschlag"])
    return monate, heute, stand


def fred(sid: str, cosd: str) -> dict[str, float]:
    text = get_with_retry(FRED.format(sid=sid, cosd=cosd), headers=FRED_H, timeout=60).decode("utf-8", "replace")
    out = {}
    for rec in csv.DictReader(io.StringIO(text)):
        try:
            out[rec["observation_date"]] = float(rec[sid])
        except (KeyError, TypeError, ValueError):
            continue   # "." = kein Wert
    if not out:
        raise RuntimeError(f"FRED {sid}: keine Werte")
    return out


def usa(staat: dict[str, float]) -> tuple[list, list]:
    """Monate [Monat, Aufschlag, HQM-Rendite, Staatsanleihe] ab 1984 und der jüngste Monat mit beiden Werten."""
    hqm = {d[:7]: v for d, v in fred("HQMCB10YR", US_START + "-01").items()}
    monate = [[m, round(hqm[m] - staat[m], 2), hqm[m], round(staat[m], 2)] for m in sorted(hqm) if m >= US_START and m in staat]
    if len(monate) < 480:
        raise RuntimeError(f"USA: nur {len(monate)} Monate mit HQM- und OECD-Wert")
    return monate, monate[-1]


def plausibel(werte, was: str) -> bool:
    schlecht = [v for v in werte if v is not None and not (LO < v < HI)]
    if schlecht:
        log_err(f"Risikoaufschläge {was}: {len(schlecht)} Werte außerhalb {LO}…{HI} (z. B. {schlecht[0]}) – Datei bleibt.")
        return False
    return True


def main() -> int:
    alt = {}
    if OUT.exists():
        try:
            alt = json.loads(OUT.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            alt = {}
    neu = {"laender": dict(alt.get("laender", {})), "us": dict(alt.get("us", {})), "stand": dict(alt.get("stand", {}))}
    fehler = 0

    try:
        renditen = oecd()
    except Exception as e:  # noqa: BLE001
        log_err(f"Risikoaufschläge: OECD nicht abrufbar ({e}) – risikoaufschlaege.json bleibt.")
        return 1

    try:
        monate, heute, stand = laender(renditen)
        if not plausibel([v for z in monate for v in z[1:]], "Länder (Renditen)"):
            return 1
        vor = (alt.get("laender") or {}).get("monate") or []
        if vor and len(monate) < 0.9 * len(vor):
            log_err(f"Risikoaufschläge Länder: nur {len(monate)} Monate statt zuvor {len(vor)} – Datei bleibt.")
            return 1
        neu["laender"] = {"monate": monate, "heute": heute}
        neu["stand"]["laender"] = stand
    except Exception as e:  # noqa: BLE001
        log_err(f"Risikoaufschläge Länder: OECD-Reihen unbrauchbar ({e}) – Länder behalten den alten Stand.")
        fehler += 1

    try:
        monate, heute = usa(renditen.get(US[0], {}))
        if not plausibel([v for z in monate for v in z[1:]], "USA (Aufschlag, Renditen)"):
            return 1
        vor = [z for z in (alt.get("us") or {}).get("monate") or [] if len(z) == 4]   # nur Zeilen im heutigen Format (bis 30.09.2026: [Monat, Aaa, Baa] seit 1953)
        if vor and len(monate) < 0.9 * len(vor):
            log_err(f"Risikoaufschläge USA: nur {len(monate)} Monate statt zuvor {len(vor)} – Datei bleibt.")
            return 1
        neu["us"] = {"monate": monate, "heute": heute}
        neu["stand"]["us"] = heute[0]
    except Exception as e:  # noqa: BLE001
        log_err(f"Risikoaufschläge USA: HQM-Kurve (FRED) nicht abrufbar oder unvollständig ({e}) – USA behält den alten Stand.")
        fehler += 1

    if fehler == 2 or not (neu["laender"] or neu["us"]):
        log_err("Risikoaufschläge: keine Quelle erreichbar – risikoaufschlaege.json bleibt.")
        return 1

    data = {"updated": today_iso(), "updatedAt": now_iso(), "checkedAt": now_iso(), "stand": neu["stand"],
            "quelle": {"laender": "OECD, Main Economic Indicators, Long-term interest rates (10-jährige Staatsanleihen, Monatsdurchschnitte); Aufschlag gegen Deutschland berechnet",
                       "us": "U.S. Department of the Treasury, HQM Corporate Bond Yield Curve (Spot-Rendite 10 Jahre, AAA/AA/A, monatlich; über FRED, HQMCB10YR) minus 10-jährige US-Staatsanleihe (OECD, Long-term interest rates, Monatsdurchschnitt); Aufschlag berechnet"},
            "laender": neu["laender"], "us": neu["us"]}
    write_atomic(OUT, data, indent=None)
    lm = data["laender"].get("monate") or []
    if lm:
        z = lm[-1]
        print(f"risikoaufschlaege.json Länder: {len(lm)} Monate {lm[0][0]}…{z[0]}; {z[0]}: " +
              ", ".join(f"{h['name']} {h['aufschlag']:+.2f}" for h in data["laender"]["heute"][:4]))
    um = data["us"].get("monate") or []
    if um and len(data["us"].get("heute") or []) >= 4:
        h = data["us"]["heute"]
        print(f"risikoaufschlaege.json USA: {len(um)} Monate {um[0][0]}…{um[-1][0]}, {h[0]}: HQM {h[2]:.2f} % − Staat {h[3]:.2f} % = {h[1]:+.2f}")
    return 0 if fehler == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
