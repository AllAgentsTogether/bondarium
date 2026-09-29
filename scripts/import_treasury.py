#!/usr/bin/env python3
"""import_treasury.py – historische Tagespreise der US-Staatsanleihen (Treasuries) vom U.S. Department of the
Treasury holen und als CSV für import_kurshistorie.py schreiben (seit 29.09.2026).

Quelle: TreasuryDirect „FedInvest – Security Price Detail“ (treasurydirect.gov/GA-FI/FedInvest/selectSecurityPriceDate),
Bureau of the Fiscal Service. Je Handelstag alle marktgängigen Treasuries (Bills, Notes, Bonds, TIPS, FRNs) mit CUSIP
und Preisen je 100 Nennwert (Buy, Sell, End of Day), verfügbar seit 2010. Werke der US-Bundesregierung sind gemeinfrei
(17 U.S.C. § 105) – Anzeige mit Quellenangabe.

Verwendet wird der End-of-Day-Preis (sauberer Kurs in % des Nennwerts, ohne Stückzinsen; TIPS ohne Indexfaktor – wie
an der Börse Frankfurt notiert). ISIN = „US“ + CUSIP + Prüfziffer. Nur ISINs, die im Anleihen-Index stehen.

Aufruf:
  python3 scripts/import_treasury.py --ab 2021-01-01 --bis 2026-09-23 --aus treasury.csv
      Ab dem Jahr --taeglich-ab (Standard: laufendes Jahr − 2) jeder US-Handelstag, davor nur Freitage (bzw. der
      letzte Handelstag der Woche) – passend zur Ausdünnung in import_kurshistorie.py.
  danach: python3 scripts/import_kurshistorie.py treasury.csv --pruefen   (Bericht) und ohne --pruefen (einspielen)
"""
import argparse
import csv
import datetime
import http.cookiejar
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
URL = "https://www.treasurydirect.gov/GA-FI/FedInvest/selectSecurityPriceDate"
UA = "Mozilla/5.0 (bondarium.de Kursaufbereitung; historische Treasury-Preise)"


def isin_aus_cusip(cusip: str) -> str:
    s = "US" + cusip.upper()
    ziffern = "".join(str(int(c, 36)) for c in s)          # Buchstaben → 10..35
    summe = 0
    for i, z in enumerate(reversed(ziffern)):               # Luhn von rechts, jede zweite Ziffer ab der ersten verdoppeln
        n = int(z)
        if i % 2 == 0:
            n *= 2
            if n > 9:
                n -= 9
        summe += n
    return s + str((10 - summe % 10) % 10)


class Sitzung:
    def __init__(self):
        self.op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
        self.op.addheaders = [("User-Agent", UA)]

    def tag(self, d: datetime.date) -> list[tuple[str, str, float]]:
        """[(cusip, typ, end_of_day)] für einen Tag; leer, wenn es für den Tag keine Preise gibt."""
        seite = self.op.open(URL, timeout=60).read().decode("utf-8", "ignore")
        m = re.search(r'name="_csrf" value="([^"]+)"', seite)
        if not m:
            raise RuntimeError("Formular-Token nicht gefunden")
        daten = urllib.parse.urlencode({"priceDate": d.isoformat(), "submit": "Show Prices", "_csrf": m.group(1)}).encode()
        html = self.op.open(URL, data=daten, timeout=90).read().decode("utf-8", "ignore")
        # Die Antwortseite nennt das Datum der Preise; weicht es ab (Feiertag), gibt es für den Tag keine Preise
        kopf = re.search(r"Prices For:\s*([A-Za-z]+ \d{1,2}, \d{4})", html)
        if kopf:
            try:
                if datetime.datetime.strptime(kopf.group(1), "%B %d, %Y").date() != d:
                    return []
            except ValueError:
                pass
        out = []
        for zeile in re.findall(r"<tr[^>]*>(.*?)</tr>", html, re.S):
            z = [re.sub(r"<[^>]+>|\s+", " ", c).strip() for c in re.findall(r"<td[^>]*>(.*?)</td>", zeile, re.S)]
            if len(z) >= 8 and re.fullmatch(r"[0-9A-Z]{9}", z[0]):
                try:
                    eod = float(z[7])
                except ValueError:
                    continue
                if eod > 0:
                    out.append((z[0], z[1], eod))
        return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ab", required=True)
    ap.add_argument("--bis", required=True)
    ap.add_argument("--aus", type=Path, required=True)
    ap.add_argument("--taeglich-ab", type=int, default=datetime.date.today().year - 2)
    ap.add_argument("--pause", type=float, default=0.6, help="Sekunden zwischen zwei Abrufen")
    a = ap.parse_args()
    idx = json.loads((ROOT / "anleihen-index.json").read_text(encoding="utf-8"))
    index_isins = {r[0] for r in idx.get("rows", []) if r[0].startswith("US")}
    ab, bis = datetime.date.fromisoformat(a.ab), datetime.date.fromisoformat(a.bis)
    tage, d = [], ab
    while d <= bis:
        if d.weekday() < 5 and (d.year >= a.taeglich_ab or d.weekday() == 4):
            tage.append(d)
        d += datetime.timedelta(days=1)
    # Vor --taeglich-ab: fällt der Freitag aus (Feiertag), den Donnerstag nehmen
    s = Sitzung()
    zeilen, leer, fehler = 0, [], []
    with open(a.aus, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["isin", "datum", "kurs", "boerse"])
        for n, d in enumerate(tage, 1):
            versuche = [d] if d.year >= a.taeglich_ab else [d, d - datetime.timedelta(days=1)]
            for v in versuche:
                try:
                    preise = s.tag(v)
                except Exception as e:  # noqa: BLE001
                    fehler.append(f"{v}: {e}")
                    time.sleep(5)
                    s = Sitzung()
                    preise = []
                time.sleep(a.pause)
                if preise:
                    for cusip, _typ, eod in preise:
                        isin = isin_aus_cusip(cusip)
                        if isin in index_isins:
                            w.writerow([isin, v.isoformat(), f"{eod:.6f}", "TREASURY"])
                            zeilen += 1
                    break
            else:
                leer.append(d.isoformat())
            if n % 50 == 0:
                print(f"{n}/{len(tage)} Tage, {zeilen} Zeilen", flush=True)
    print(f"Fertig: {zeilen} Zeilen aus {len(tage)} Tagen in {a.aus}; ohne Preise: {len(leer)} Tage; Fehler: {len(fehler)}")
    for x in fehler[:10]:
        print("  Fehler", x)
    return 0 if not fehler else 1


if __name__ == "__main__":
    sys.exit(main())
