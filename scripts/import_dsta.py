#!/usr/bin/env python3
"""import_dsta.py – historische Tageskurse der niederländischen Staatsanleihen (DSLs) von der niederländischen
Schuldenagentur (Dutch State Treasury Agency, DSTA) holen und als CSV für import_kurshistorie.py schreiben
(seit 02.10.2026).

Quelle: DSTA, „Yields on DSLs from 2010 onwards“ (english.dsta.nl/latest/statistical-information/yields-on-dsls),
eine ODS-Datei mit einem Blatt je Jahr („Daily_fixing_<Jahr>“): je Handelstag und DSL das Tagesfixing von MTS Netherlands
mit Mittelkurs (sauberer Kurs in % des Nennwerts, ohne Stückzinsen), Rendite und Duration. Monatlich aktualisiert.
Lizenz: CC0 (Inhalte der DSTA-Website, english.dsta.nl/service/copyright); die Datei verlangt die Quellenangabe
„MTS Netherlands“.

Verwendet wird „Mid Price“. Werte 0 (kein Fixing, etwa an Feiertagen oder nach der Fälligkeit) fallen weg.
Nur ISINs, die im Anleihen-Index stehen.

Aufruf:
  python3 scripts/import_dsta.py --ab 2021-01-01 --bis 2026-09-23 --aus dsta.csv [--datei mts-fixings-publicatie.ods]
      Ohne --datei wird die aktuelle Datei von der DSTA-Seite gesucht und geladen.
  danach: python3 scripts/import_kurshistorie.py dsta.csv --pruefen   (Bericht) und ohne --pruefen (einspielen)
"""
import argparse
import csv
import datetime
import io
import json
import re
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SEITE = "https://english.dsta.nl/latest/statistical-information/yields-on-dsls"
UA = "Mozilla/5.0 (bondarium.de Kursaufbereitung; historische DSL-Kurse)"
TAB = "{urn:oasis:names:tc:opendocument:xmlns:table:1.0}"
OFF = "{urn:oasis:names:tc:opendocument:xmlns:office:1.0}"


def laden(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read()


def datei_suchen():
    """Seite → Dokumentseite „from 2010 onwards“ → ODS-Datei (der Pfad enthält das Datum der Monatsfassung)."""
    html = laden(SEITE).decode("utf-8", "ignore")
    m = re.search(r'href="(/documents/[^"]*yields-on-dsls-from-2010-onwards)"', html)
    if not m:
        raise RuntimeError("Link „from 2010 onwards“ auf der DSTA-Seite nicht gefunden")
    doku = laden(urllib.parse.urljoin(SEITE, m.group(1))).decode("utf-8", "ignore")
    m = re.search(r'(https://english\.dsta\.nl/site/binaries/[^"\\\s]+?\.ods)', doku)
    if not m:
        raise RuntimeError("ODS-Datei auf der Dokumentseite nicht gefunden")
    print("Datei:", m.group(1))
    return laden(m.group(1))


def zeilen(ods, ab, bis):
    """(isin, datum, mid) aus den Jahresblättern ab..bis; liest content.xml stückweise (rund 125 MB entpackt)."""
    z = zipfile.ZipFile(io.BytesIO(ods))
    jahr, kopf = None, None
    for ev, el in ET.iterparse(z.open("content.xml"), events=("start", "end")):
        if ev == "start":
            if el.tag == TAB + "table":
                m = re.fullmatch(r"Daily_fixing_(\d{4})", el.get(TAB + "name") or "")
                jahr = int(m.group(1)) if m and ab.year <= int(m.group(1)) <= bis.year else None
                kopf = None
            continue
        if el.tag != TAB + "table-row":
            continue
        if jahr is not None:
            werte = []
            for c in el:
                n = min(int(c.get(TAB + "number-columns-repeated", "1")), 20)
                werte.extend([c.get(OFF + "date-value") or c.get(OFF + "value") or "".join(c.itertext()).strip()] * n)
            if kopf is None:
                if "ISIN Code" in werte and "Mid Price" in werte:
                    kopf = (werte.index("RefDate"), werte.index("ISIN Code"), werte.index("Mid Price"))
            else:
                try:
                    tag = datetime.date.fromisoformat(werte[kopf[0]][:10])
                    mid = float(werte[kopf[2]])
                except (ValueError, IndexError):
                    tag = mid = None
                if tag and mid and ab <= tag <= bis:
                    yield werte[kopf[1]].strip().upper(), tag, mid
        el.clear()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ab", required=True)
    ap.add_argument("--bis", required=True)
    ap.add_argument("--aus", type=Path, required=True)
    ap.add_argument("--datei", type=Path, help="schon geladene ODS-Datei statt Abruf")
    a = ap.parse_args()
    idx = json.loads((ROOT / "anleihen-index.json").read_text(encoding="utf-8"))
    index_isins = {r[0] for r in idx.get("rows", []) if r[0].startswith("NL")}
    ab, bis = datetime.date.fromisoformat(a.ab), datetime.date.fromisoformat(a.bis)
    ods = a.datei.read_bytes() if a.datei else datei_suchen()
    n, isins, fremd = 0, set(), set()
    with open(a.aus, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["isin", "datum", "kurs", "boerse"])
        for isin, tag, mid in zeilen(ods, ab, bis):
            if isin not in index_isins:
                fremd.add(isin)
                continue
            w.writerow([isin, tag.isoformat(), f"{mid:.6f}", "MTS"])
            n += 1
            isins.add(isin)
    print(f"Fertig: {n} Zeilen für {len(isins)} DSLs in {a.aus}; nicht im Index (meist schon fällig): {len(fremd)}")
    return 0 if n else 1


if __name__ == "__main__":
    sys.exit(main())
