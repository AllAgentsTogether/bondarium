#!/usr/bin/env python3
"""Historische Schlusskurse (z. B. eine Lieferung von Deutsche Börse Market Data + Services) rückwirkend in den
Kursverlauf kurse/<Jahr>/<hh>.json einspielen – ohne vorhandene Werte zu überschreiben.

Aufruf (im Repo-Wurzelverzeichnis):
  python3 scripts/import_kurshistorie.py lieferung.csv --pruefen        # nur Bericht, schreibt nichts
  python3 scripts/import_kurshistorie.py lieferung.csv                   # einspielen
  python3 scripts/import_kurshistorie.py lieferung.csv --site-js         # dazu VERLAUF_AB in site.js auf das früheste Jahr setzen

Eingabe (auch .gz):
  * CSV/TSV mit Kopfzeile. Spalten werden am Namen erkannt (ISIN, Datum, Schlusskurs, Umsatz, Stück, Notierung, Währung,
    Handelsplatz); abweichende Namen mit --spalten isin=…,datum=…,kurs=…[,umsatz=…,stueck=…,notiz=…,waehrung=…,boerse=…].
  * JSON-Zeilen im Format der MiFIR-Tagesdateien (instrumentIdentificationCode, tradingDateAndTime, price, quantity,
    priceNotation, mmtTradingMode, mmtModificationInd) – etwa ein Archiv der DFRA-posttrade-Dateien; je Tag zählt die
    letzte Kursfeststellung, Umsatz = Summe Stück × Kurs.
Regeln:
  * Nur ISINs aus anleihen-index.json (Option --alle nimmt jede gültige ISIN). Kurse in % des Nennwerts; Stücknotiz
    (Notierung 1 / UNIT) wird über die Stückelung des Index umgerechnet. Plausibilität 1–400 %.
  * Liegen je ISIN und Tag mehrere Zeilen vor, gewinnt Börse Frankfurt (FRAA/FRAB/XFRA) vor Tradegate vor anderen,
    sonst die letzte Zeile.
  * Vorhandene Werte in kurse/ bleiben unangetastet; Tage werden nur ergänzt. „stand“ und „aktuell“ bleiben.
  * Ältere Jahre werden auf Wochenschluss ausgedünnt (--taeglich-ab JAHR, Standard: laufendes Jahr − 2 – wie der
    Bund-Verlauf der Bundesbank: zwei Jahre täglich, davor ein Wert je Woche). --taeglich-ab 0 = alles täglich.
  * --ab / --bis (ISO-Datum) begrenzen den Zeitraum.
Danach: site.js VERLAUF_AB muss dem frühesten Jahr im Ordner kurse/ entsprechen (Option --site-js erledigt das),
Ordner kurse/ committen. Bundeswertpapiere zeigen weiterhin den Bundesbank-Verlauf (kurse/bund/), die Börsenkurse
werden für sie nur als Rückfall gespeichert.
"""

import argparse
import csv
import datetime
import gzip
import io
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import write_atomic  # noqa: E402
from update_kurse import DIR_VERLAUF, INDEX, KURS_GRENZEN, ROOT, isin_ok, lade_json, teil  # noqa: E402

SITE_JS = ROOT / "site.js"

# Spaltennamen (klein, ohne Sonderzeichen), die erkannt werden
NAMEN = {
    "isin": ("isin", "instrumentidentificationcode", "isincode", "instrument"),
    "datum": ("date", "datum", "tradedate", "tradingdate", "tradingday", "handelstag", "tag", "day", "tradingdateandtime", "businessdate"),
    "kurs": ("close", "closeprice", "closingprice", "last", "lastprice", "schlusskurs", "kurs", "price", "settlement", "pxlast", "endofdayprice"),
    "umsatz": ("turnover", "umsatz", "tradedvalue", "value", "turnovereur", "umsatzeur", "geldumsatz"),
    "stueck": ("quantity", "volume", "stueck", "stück", "nominal", "tradedquantity", "shares"),
    "notiz": ("pricenotation", "notation", "notierung", "quotetype", "quotationtype", "pricetype"),
    "waehrung": ("currency", "pricecurrency", "waehrung", "währung", "ccy"),
    "boerse": ("mic", "venue", "venueofexecution", "exchange", "boerse", "börse", "market", "handelsplatz"),
}
RANG_BOERSE = {"FRAA": 0, "FRAB": 0, "XFRA": 0, "F": 0, "FRANKFURT": 0, "TGAT": 1, "XGAT": 1, "T": 1, "TRADEGATE": 1}
DATUMSFORMATE = ("%Y-%m-%d", "%d.%m.%Y", "%Y%m%d", "%d/%m/%Y", "%Y/%m/%d")


def norm(s: str) -> str:
    return re.sub(r"[^a-z0-9äöü]", "", (s or "").strip().lower())


def zahl(s) -> float | None:
    if s is None:
        return None
    if isinstance(s, (int, float)):
        return float(s)
    t = str(s).strip().replace(" ", "")
    if not t or t in ("-", "–", "n/a", "NA", "null"):
        return None
    if "," in t and "." in t:
        t = t.replace(",", "") if t.rfind(".") > t.rfind(",") else t.replace(".", "").replace(",", ".")
    elif "," in t:
        t = t.replace(",", ".")
    try:
        return float(t)
    except ValueError:
        return None


def datum(s, fmt: str | None) -> str | None:
    t = (s or "").strip()
    if not t:
        return None
    if fmt:
        formate = (fmt,)
    else:
        formate = DATUMSFORMATE
        if re.match(r"^\d{4}-\d{2}-\d{2}", t):
            t = t[:10]
    for f in formate:
        try:
            return datetime.datetime.strptime(t, f).date().isoformat()
        except ValueError:
            continue
    return None


def oeffnen(pfad: Path):
    roh = pfad.read_bytes()
    if pfad.suffix == ".gz" or roh[:2] == b"\x1f\x8b":
        roh = gzip.decompress(roh)
    return roh.decode("utf-8-sig", "replace")


# ---------- Eingabe lesen: {(isin, tag): (kurs_roh, notiz, umsatz, stueck, rang)} ----------
def lese_jsonl(text: str):
    """MiFIR-Tagesdatei(en): letzte Kursfeststellung je ISIN und Tag, Umsatz = Σ Stück × Kurs."""
    letzte, umsatz = {}, defaultdict(float)
    n = 0
    for zeile in text.splitlines():
        zeile = zeile.strip()
        if not zeile:
            continue
        try:
            d = json.loads(zeile)
            isin, zeit = d["instrumentIdentificationCode"], d["tradingDateAndTime"]
            if d.get("mmtTradingMode") == "I" or d.get("mmtModificationInd") == "C":
                continue
            preis, menge, notiz = float(d["price"]), float(d.get("quantity") or 0), int(d.get("priceNotation") or 2)
            # Satz ohne Zeitstempel oder Preis überspringen – wie update_kurse.auswerten (Tradegate 05.10.2026: Zeit null,
            # Preis 0; Technik-Test 08.10.2026, T-03)
            if not isinstance(zeit, str) or not re.match(r"\d{4}-\d{2}-\d{2}", zeit) or preis <= 0:
                continue
        except (KeyError, TypeError, ValueError, AttributeError):
            continue
        n += 1
        k = (isin, zeit[:10])
        if k not in letzte or zeit >= letzte[k][0]:
            letzte[k] = (zeit, preis, notiz)
        if menge > 0:
            umsatz[k] += menge * preis / 100 if notiz == 2 else menge * preis
    out = {k: (v[1], v[2], umsatz.get(k, 0.0), None, 0) for k, v in letzte.items()}
    return out, n


def lese_csv(text: str, spalten: dict, trenner: str | None, datumsformat: str | None, fehler: dict):
    probe = text[:5000]
    if trenner is None:
        try:
            trenner = csv.Sniffer().sniff(probe, delimiters=";,\t|").delimiter
        except csv.Error:
            trenner = ";" if probe.count(";") > probe.count(",") else ","
    leser = csv.reader(io.StringIO(text), delimiter=trenner)
    kopf = next(leser)
    kopf_n = [norm(h) for h in kopf]
    idx = {}
    for feld, namen in NAMEN.items():
        wunsch = spalten.get(feld)
        if wunsch:
            if norm(wunsch) not in kopf_n:
                sys.exit(f"Spalte {wunsch!r} für {feld} nicht in der Kopfzeile: {kopf}")
            idx[feld] = kopf_n.index(norm(wunsch))
        else:
            for i, h in enumerate(kopf_n):
                if h in namen:
                    idx[feld] = i
                    break
    for pflicht in ("isin", "datum", "kurs"):
        if pflicht not in idx:
            sys.exit(f"Spalte für {pflicht} nicht erkannt. Kopfzeile: {kopf}\n  → mit --spalten {pflicht}=<Name> angeben.")
    print(f"Spalten: " + ", ".join(f"{f}={kopf[i]!r}" for f, i in idx.items()) + f"; Trenner {trenner!r}")
    out, n = {}, 0
    for zeile in leser:
        if not zeile or len(zeile) <= max(idx.values()):
            continue
        n += 1
        isin = zeile[idx["isin"]].strip().upper()
        tag = datum(zeile[idx["datum"]], datumsformat)
        kurs = zahl(zeile[idx["kurs"]])
        if not tag:
            fehler["Datum unlesbar"] += 1
            continue
        if kurs is None:
            fehler["Kurs leer/unlesbar"] += 1
            continue
        notiz_roh = zeile[idx["notiz"]].strip().upper() if "notiz" in idx else ""
        notiz = 1 if notiz_roh in ("1", "UNIT", "UNITS", "PIEC", "PIECE", "STUECK", "STÜCK", "STK") else 2
        umsatz = zahl(zeile[idx["umsatz"]]) if "umsatz" in idx else None
        stueck = zahl(zeile[idx["stueck"]]) if "stueck" in idx else None
        rang = RANG_BOERSE.get(zeile[idx["boerse"]].strip().upper(), 2) if "boerse" in idx else 0
        k = (isin, tag)
        if k in out and out[k][4] < rang:   # bessere Börse schon da
            continue
        out[k] = (kurs, notiz, umsatz, stueck, rang)
    return out, n


# ---------- Zusammenführen ----------
def wochenschluss(tage: set[str]) -> set[str]:
    """Aus allen Tagen je ISO-Woche den letzten behalten."""
    letzter = {}
    for t in tage:
        d = datetime.date.fromisoformat(t)
        w = d.isocalendar()[:2]
        if w not in letzter or t > letzter[w]:
            letzter[w] = t
    return set(letzter.values())


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("datei", type=Path, help="CSV/TSV oder JSON-Zeilen, auch .gz")
    ap.add_argument("--pruefen", action="store_true", help="nur Bericht, nichts schreiben")
    ap.add_argument("--spalten", default="", help="feld=Spaltenname,… (isin, datum, kurs, umsatz, stueck, notiz, waehrung, boerse)")
    ap.add_argument("--trenner", default=None, help="Feldtrenner der CSV (Standard: erkennen)")
    ap.add_argument("--datumsformat", default=None, help="strptime-Format, z. B. %%d.%%m.%%Y (Standard: erkennen)")
    ap.add_argument("--ab", default=None, help="frühester Tag (ISO)")
    ap.add_argument("--bis", default=None, help="spätester Tag (ISO)")
    ap.add_argument("--taeglich-ab", type=int, default=datetime.date.today().year - 2, help="ab diesem Jahr täglich, davor Wochenschluss (0 = alles täglich)")
    ap.add_argument("--alle", action="store_true", help="auch ISINs, die nicht im Anleihen-Index stehen")
    ap.add_argument("--site-js", action="store_true", help="VERLAUF_AB in site.js auf das früheste Jahr setzen")
    a = ap.parse_args()

    spalten = dict(p.split("=", 1) for p in a.spalten.split(",") if "=" in p)
    idx = lade_json(INDEX, {})
    zeilen = {r[0]: r for r in idx.get("rows", [])}
    if not zeilen and not a.alle:
        sys.exit("anleihen-index.json fehlt – ohne Index keine Stückelung und keine ISIN-Auswahl (oder --alle).")

    text = oeffnen(a.datei)
    fehler = defaultdict(int)
    if text.lstrip().startswith("{"):
        roh, n = lese_jsonl(text)
        print(f"JSON-Zeilen gelesen: {n}")
    else:
        roh, n = lese_csv(text, spalten, a.trenner, a.datumsformat, fehler)
        print(f"CSV-Zeilen gelesen: {n}")

    # Normieren: Kurs in % des Nennwerts, Plausibilität, Auswahl
    werte = {}      # (isin, tag) -> (kurs, umsatz)
    for (isin, tag), (kurs, notiz, umsatz, stueck, _rang) in roh.items():
        if not isin_ok(isin):
            fehler["ISIN ungültig"] += 1
            continue
        z = zeilen.get(isin)
        if z is None and not a.alle:
            fehler["ISIN nicht im Index"] += 1
            continue
        if (a.ab and tag < a.ab) or (a.bis and tag > a.bis):
            fehler["außerhalb --ab/--bis"] += 1
            continue
        if notiz == 1:
            stk = z[7] if z and isinstance(z[7], (int, float)) and z[7] > 0 else None
            if not stk:
                fehler["Stücknotiz ohne Stückelung"] += 1
                continue
            kurs = kurs * 100 / stk
        if not KURS_GRENZEN[0] < kurs < KURS_GRENZEN[1]:
            fehler["Kurs außerhalb 1–400 %"] += 1
            continue
        if umsatz is None and stueck:
            umsatz = stueck * kurs / 100
        werte[(isin, tag)] = (round(kurs, 4 if kurs < 10 else 3), round(umsatz) if umsatz and umsatz > 0 else 0)

    if not werte:
        print("Keine verwertbaren Kurse.", dict(fehler))
        return 1
    tage_alle = {t for _, t in werte}
    if a.taeglich_ab:
        alt = {t for t in tage_alle if int(t[:4]) < a.taeglich_ab}
        behalten = wochenschluss(alt) | (tage_alle - alt)
        weg = len(tage_alle) - len(behalten)
        werte = {k: v for k, v in werte.items() if k[1] in behalten}
        tage_alle = behalten
        if weg:
            print(f"Ausgedünnt: vor {a.taeglich_ab} nur Wochenschluss ({weg} Tage weniger)")
    isins = {i for i, _ in werte}
    jahre = sorted({int(t[:4]) for t in tage_alle})
    print(f"Verwertbar: {len(werte)} Kurse, {len(isins)} ISINs, {len(tage_alle)} Handelstage {min(tage_alle)} … {max(tage_alle)}, Jahre {jahre[0]}–{jahre[-1]}")
    if fehler:
        print("Übersprungen: " + ", ".join(f"{k}: {v}" for k, v in sorted(fehler.items(), key=lambda x: -x[1])))

    # Je Jahr und Teildatei zusammenführen
    je_datei = defaultdict(dict)     # (jahr, teil) -> {isin: {tag: (kurs, umsatz)}}
    for (isin, tag), v in werte.items():
        je_datei[(int(tag[:4]), teil(isin))].setdefault(isin, {})[tag] = v
    dazu = vorhanden = dateien = 0
    for (jahr, t), neu in sorted(je_datei.items()):
        pfad = DIR_VERLAUF / str(jahr) / f"{t}.json"
        v = lade_json(pfad, {"tage": [], "k": {}, "u": {}})
        alt_tage = list(v.get("tage") or [])
        neue_tage = sorted(set(alt_tage) | {tag for reihe in neu.values() for tag in reihe})
        pos = {tag: i for i, tag in enumerate(neue_tage)}
        alt_pos = [pos[tag] for tag in alt_tage]
        k_neu, u_neu, h_neu = {}, {}, {}
        for isin in sorted(set(v.get("k", {})) | set(neu)):
            reihe = [None] * len(neue_tage)
            alt_reihe = v.get("k", {}).get(isin) or []
            for i, wert in enumerate(alt_reihe):
                if i < len(alt_pos):
                    reihe[alt_pos[i]] = wert
            um = {}
            for i_alt, wert in (v.get("u", {}).get(isin) or {}).items():
                try:
                    um[str(alt_pos[int(i_alt)])] = wert
                except (ValueError, IndexError):
                    pass
            # Handelsdaten ("h", seit 26.09.2026) behalten und nur auf die neuen Tag-Positionen umschreiben
            ha = {}
            for i_alt, wert in (v.get("h", {}).get(isin) or {}).items():
                try:
                    ha[str(alt_pos[int(i_alt)])] = wert
                except (ValueError, IndexError):
                    pass
            if ha:
                h_neu[isin] = dict(sorted(ha.items(), key=lambda x: int(x[0])))
            for tag, (kurs, umsatz) in neu.get(isin, {}).items():
                p = pos[tag]
                if reihe[p] is None:
                    reihe[p] = kurs
                    dazu += 1
                    if umsatz > 0:
                        um[str(p)] = umsatz
                else:
                    vorhanden += 1
            if any(x is not None for x in reihe):
                k_neu[isin] = reihe
            if um:
                u_neu[isin] = dict(sorted(um.items(), key=lambda x: int(x[0])))
        if neue_tage == alt_tage and k_neu == v.get("k") and u_neu == v.get("u", {}):
            continue
        v["tage"], v["k"], v["u"] = neue_tage, k_neu, u_neu
        if h_neu or "h" in v:
            v["h"] = h_neu
        dateien += 1
        if not a.pruefen:
            pfad.parent.mkdir(parents=True, exist_ok=True)
            write_atomic(pfad, v, indent=None)
    print(f"{'Würde ergänzen' if a.pruefen else 'Ergänzt'}: {dazu} Kurse in {dateien} Teildateien; {vorhanden} schon vorhanden (unverändert gelassen)")

    # site.js: frühestes Jahr
    fruehestes = min([jahre[0]] + [int(p.name) for p in DIR_VERLAUF.iterdir() if p.is_dir() and p.name.isdigit()])
    js = SITE_JS.read_text(encoding="utf-8") if SITE_JS.exists() else ""
    m = re.search(r"var VERLAUF_AB = (\d{4});", js)
    if m and int(m.group(1)) > fruehestes:
        if a.site_js and not a.pruefen:
            SITE_JS.write_text(js.replace(m.group(0), f"var VERLAUF_AB = {fruehestes};"), encoding="utf-8")
            print(f"site.js: VERLAUF_AB {m.group(1)} → {fruehestes}")
        else:
            print(f"HINWEIS: site.js hat VERLAUF_AB = {m.group(1)}, die Daten reichen bis {fruehestes} zurück – mit --site-js setzen "
                  f"(sonst zeigt die Seite die älteren Jahre nicht).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
