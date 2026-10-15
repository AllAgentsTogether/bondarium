#!/usr/bin/env python3
"""Schreibt zinskurve.json – der Abstand zwischen langen und kurzen Laufzeiten
(10 Jahre minus 2 Jahre) für Deutschland und die USA, als Monatswerte seit 1972 bzw. 1976
(Deutschland: Monatsendwerte der Bundesbank, Stand am Monatsende; USA: Monatsdurchschnitte)
und dazu der jüngste Tageswert. Seite: zinskurve.html (Menü „Markt“).

Quellen (amtlich, kostenlos, ohne Schlüssel):
- Deutschland: Deutsche Bundesbank, Zinsstrukturkurve am Rentenmarkt (Svensson-Methode),
  börsennotierte Bundeswertpapiere, Restlaufzeit 2 und 10 Jahre – Monatswerte seit 09/1972
  (BBSIS.M.…R02XX/R10XX…), Tageswerte seit 08/1997 (BBSIS.D.…). Die Bundesbank
  veröffentlicht den Tageswert am Abend, der 10-Uhr-Lauf holt also den Vortag.
- USA: Federal Reserve, Statistical Release H.15, „Treasury constant maturities“
  2 und 10 Jahre, Tageswerte (2 Jahre seit 06/1976); Monatsdurchschnitte werden hier
  aus den Handelstagen gebildet (so bildet auch die Fed ihre Monatswerte). Abruf über
  das Data Download Program (CSV, ~1 MB, alle Laufzeiten des H.15-Pakets).

Struktur: {"updated", "updatedAt", "checkedAt", "stand": {"DE": …, "US": …}, "quelle": {…},
           "monate": {"DE": [["1972-09", zwei, zehn], …], "US": [["1976-06", zwei, zehn], …]},
           "heute":  {"DE": ["JJJJ-MM-TT", zwei, zehn], "US": [...]}}
Der Abstand (zehn − zwei) wird auf der Seite gerechnet. Der laufende Monat steht als
Teil-Durchschnitt der bisherigen Handelstage mit drin; Deutschland: hat die Bundesbank
den gerade abgeschlossenen Monat noch nicht gemeldet, entsteht auch er aus den
Tageswerten (seit 15.10.2026). Die Datei ist ~35 KB und wird per
inline_data.py in die Seite eingebettet.

Schutz: Bleibt eine Quelle aus, behält das Land seine alten Daten; schrumpft die Reihe
eines Landes unter 90 % des Vorbestands oder liegen Werte außerhalb −5…25 %, bleibt die
Datei unverändert. Seit 15.10.2026 (Gesamtprüfung D10-02) behält ein Land auch dann seinen
alten Stand (Exit 1), wenn der Tageswert um mehr als MAX_SPRUNG Punkte vom bisherigen
abweicht, die 10-jährige mehr als MAX_INVERS Punkte unter der 2-jährigen liegt oder schon
gemeldete Monate um mehr als MAX_REVISION Punkte anders ausfallen (z. B. vertauschte Spalten).

Aufruf: python scripts/update_zinskurve.py
"""

import csv
import datetime
import io
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

from _common import get_with_retry, log_err, now_iso, today_iso, write_atomic

OUT = Path(__file__).resolve().parent.parent / "zinskurve.json"

BUBA = "https://api.statistiken.bundesbank.de/rest/data/BBSIS/{freq}.I.ZST.ZI.EUR.S1311.B.A604.{lz}.R.A.A._Z._Z.A?detail=dataonly{extra}"
BUBA_HEADERS = {"Accept": "application/vnd.sdmx.data+csv;version=1.0.0",
                "User-Agent": "bondarium.de Zinskurve (Datenaufbereitung)"}
FED = ("https://www.federalreserve.gov/datadownload/Output.aspx?rel=H15&series=bf17364827e38702b42a58cf8eaa3f78"
       "&lastobs=&from=&to=&filetype=csv&label=include&layout=seriescolumn")
FED_HEADERS = {"User-Agent": "bondarium.de Zinskurve (Datenaufbereitung)", "Accept": "text/csv,*/*"}
FED_COLS = {"RIFLGFCY02_N.B": 2, "RIFLGFCY10_N.B": 10}   # Spaltenkennungen in der H.15-Datei
LO, HI = -5.0, 25.0                                      # Plausibilität je Wert (in %)
MAX_SPRUNG = 2.5      # Punkte: Tageswert gegen den bisherigen Tageswert (wie renditen)
MAX_INVERS = 3.0      # Punkte: so weit darf die 10-jährige unter der 2-jährigen liegen (Tiefstwert seit 1972: −2,3)
MAX_REVISION = 0.5    # Punkte: Abweichung eines schon gespeicherten Monats (ohne die beiden jüngsten)
US_START = "1976-06"                                     # ab hier gibt es die 2-jährige US-Rendite


def buba(freq: str, lz: str, extra: str = "") -> dict[str, float]:
    """Bundesbank-Reihe → {Periode: Wert}; Periode „JJJJ-MM“ (M) oder „JJJJ-MM-TT“ (D)."""
    text = get_with_retry(BUBA.format(freq=freq, lz=lz, extra=extra), headers=BUBA_HEADERS, timeout=60).decode("utf-8-sig", "replace")
    out = {}
    for rec in csv.DictReader(io.StringIO(text), delimiter=";"):
        try:
            out[rec["TIME_PERIOD"]] = float(rec["OBS_VALUE"])
        except (KeyError, TypeError, ValueError):
            continue   # "." = kein Wert
    return out


def deutschland() -> tuple[list, list]:
    """Monatsreihe seit 1972 (amtliche Monatsendwerte, Stand am Monatsende) plus laufender Monat als
    Teil-Durchschnitt der Tageswerte; dazu der jüngste Tageswert."""
    m2, m10 = buba("M", "R02XX"), buba("M", "R10XX")
    seit = (datetime.date.today() - datetime.timedelta(days=70)).replace(day=1).isoformat()
    d2, d10 = buba("D", "R02XX", f"&startPeriod={seit}"), buba("D", "R10XX", f"&startPeriod={seit}")
    monate = [[p, m2[p], m10[p]] for p in sorted(m2) if p in m10]
    tage = sorted(d for d in d2 if d in d10)
    if not monate or not tage:
        raise RuntimeError("Bundesbank: Monats- oder Tagesreihe leer")
    letzter = tage[-1]
    heute = [letzter, d2[letzter], d10[letzter]]
    # Monate nach dem letzten amtlichen Monat: Durchschnitt der Handelstage – der laufende und, solange die Bundesbank
    # ihn noch nicht gemeldet hat, auch der abgeschlossene Vormonat (die Tagesreihe reicht ab dem Ersten des Monats
    # vor 70 Tagen; bis 15.10.2026 nur der laufende Monat – dazwischen fehlte am Monatsanfang ein Monat)
    for lm in sorted({d[:7] for d in tage if d[:7] > monate[-1][0]}):
        tm = [d for d in tage if d.startswith(lm)]
        monate.append([lm, round(sum(d2[d] for d in tm) / len(tm), 2), round(sum(d10[d] for d in tm) / len(tm), 2)])
    return monate, heute


def usa() -> tuple[list, list]:
    """H.15-Tageswerte → Monatsdurchschnitte seit 06/1976 und jüngster Tageswert."""
    text = get_with_retry(FED, headers=FED_HEADERS, timeout=120).decode("utf-8", "replace")
    rows = list(csv.reader(io.StringIO(text)))
    kopf = next((r for r in rows if r and r[0] == "Time Period"), None)
    if not kopf:
        raise RuntimeError("H.15: Kopfzeile „Time Period“ fehlt")
    idx = {FED_COLS[k]: i for i, k in enumerate(kopf) if k in FED_COLS}
    if len(idx) != 2:
        raise RuntimeError(f"H.15: Spalten 2/10 Jahre nicht gefunden ({kopf[:12]})")
    tage = {}
    for r in rows:
        if not r or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", r[0]) or len(r) <= max(idx.values()):
            continue
        try:
            tage[r[0]] = (float(r[idx[2]]), float(r[idx[10]]))
        except ValueError:
            continue   # ND = kein Handelstag / kein Wert
    if not tage:
        raise RuntimeError("H.15: keine Tageswerte")
    summe = defaultdict(lambda: [0.0, 0.0, 0])
    for d, (z, zehn) in tage.items():
        if d[:7] < US_START:
            continue
        s = summe[d[:7]]
        s[0] += z; s[1] += zehn; s[2] += 1
    monate = [[m, round(s[0] / s[2], 2), round(s[1] / s[2], 2)] for m, s in sorted(summe.items())]
    letzter = max(tage)
    return monate, [letzter, tage[letzter][0], tage[letzter][1]]


def plausibel(monate: list, land: str) -> bool:
    schlecht = [m for m in monate if not (LO < m[1] < HI and LO < m[2] < HI)]
    if schlecht:
        log_err(f"{land}: {len(schlecht)} Monatswerte außerhalb {LO}…{HI} % (z. B. {schlecht[0]}) – Datei bleibt.")
        return False
    return True


def stimmig(land: str, monate: list, heute: list, alt: dict) -> bool:
    """Neuer Stand gegen den gespeicherten: Tageswert-Sprung, Abstand 10 J. − 2 J., Revision schon gemeldeter Monate."""
    vorher = (alt.get("heute") or {}).get(land)
    if isinstance(vorher, list) and len(vorher) == 3:
        for i, lz in ((1, "2 J."), (2, "10 J.")):
            if isinstance(vorher[i], (int, float)) and abs(heute[i] - vorher[i]) > MAX_SPRUNG:
                log_err(f"Zinskurve {land}: Tageswert {lz} {heute[i]} % weicht um mehr als {MAX_SPRUNG} Punkte vom bisherigen "
                        f"{vorher[i]} % ab – {land} behält den alten Stand.")
                return False
    if heute[2] < heute[1] - MAX_INVERS:
        log_err(f"Zinskurve {land}: 10 J. {heute[2]} % liegt mehr als {MAX_INVERS} Punkte unter 2 J. {heute[1]} % "
                f"– Spalten vertauscht? {land} behält den alten Stand.")
        return False
    gespeichert = {z[0]: z for z in (alt.get("monate") or {}).get(land) or [] if isinstance(z, list) and len(z) == 3}
    for z in monate[:-2]:
        a = gespeichert.get(z[0])
        if a and any(isinstance(a[i], (int, float)) and abs(z[i] - a[i]) > MAX_REVISION for i in (1, 2)):
            log_err(f"Zinskurve {land}: Monat {z[0]} neu {z[1:]} statt bisher {a[1:]} – mehr als {MAX_REVISION} Punkte "
                    f"Unterschied; {land} behält den alten Stand.")
            return False
    return True


def main() -> int:
    alt = {}
    if OUT.exists():
        try:
            alt = json.loads(OUT.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            alt = {}
    neu = {"monate": dict(alt.get("monate", {})), "heute": dict(alt.get("heute", {})), "stand": dict(alt.get("stand", {}))}
    fehler = 0
    for land, holen in (("DE", deutschland), ("US", usa)):
        try:
            monate, heute = holen()
        except Exception as e:  # noqa: BLE001
            log_err(f"Zinskurve {land}: Quelle nicht abrufbar ({e}) – {land} behält den alten Stand.")
            fehler += 1
            continue
        if not plausibel(monate, land):
            return 1
        if not stimmig(land, monate, heute, alt):
            fehler += 1
            continue
        vor = alt.get("monate", {}).get(land) or []
        if vor and len(monate) < 0.9 * len(vor):
            log_err(f"Zinskurve {land}: nur {len(monate)} Monate statt zuvor {len(vor)} – Datei bleibt.")
            return 1
        neu["monate"][land] = monate
        neu["heute"][land] = heute
        neu["stand"][land] = heute[0]
    if fehler == 2 or not neu["monate"]:
        log_err("Zinskurve: keine Quelle erreichbar – zinskurve.json bleibt.")
        return 1
    data = {"updated": today_iso(), "updatedAt": now_iso(), "checkedAt": now_iso(), "stand": neu["stand"],
            "quelle": {"DE": "Deutsche Bundesbank, Zinsstrukturkurve am Rentenmarkt (Svensson), börsennotierte Bundeswertpapiere, Restlaufzeit 2 und 10 Jahre (BBSIS)",
                       "US": "Federal Reserve, Statistical Release H.15, Treasury constant maturities 2 und 10 Jahre (Data Download Program)"},
            "monate": neu["monate"], "heute": neu["heute"]}
    write_atomic(OUT, data, indent=None)
    for land in ("DE", "US"):
        m = data["monate"].get(land, []); h = data["heute"].get(land)
        if m and h:
            print(f"zinskurve.json {land}: {len(m)} Monate {m[0][0]}…{m[-1][0]}, heute {h[0]}: 2 J. {h[1]} %, 10 J. {h[2]} %, Abstand {h[2] - h[1]:+.2f}")
    return 0 if fehler == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
