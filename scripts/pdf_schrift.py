#!/usr/bin/env python3
"""pdf_schrift.py – erzeugt pdf-schrift.json: die Schrift Manrope für PDF-Dateien, die der Browser selbst schreibt (seit 30.09.2026).

Der Depot-Auszug auf konto.html („Depot teilen“) entsteht mit pdf.js im Browser. Damit er aussieht wie die Website, bettet
er Manrope ein – dieselben Dateien, die base.css lädt (manrope-400/600/700.woff2, Teilmenge Latein). Ein PDF kann WOFF2 nicht
lesen und der Browser WOFF2 nicht entpacken; deshalb liegt die Schrift hier fertig vorbereitet:

  * Teilmenge auf die Zeichen von Windows-1252 (WinAnsi) – alles, was pdf.js schreibt; Layout-Tabellen (GSUB/GPOS) entfallen
  * TrueType (glyf), mit zlib gepackt (PDF-Filter FlateDecode), Base64
  * Zeichenbreiten für die Codes 32–255 in Tausendstel der Schriftgröße, dazu die Werte für den FontDescriptor

    python3 scripts/pdf_schrift.py            # schreibt pdf-schrift.json im Stammordner

Braucht fontTools und brotli (pip install fonttools brotli) – nur beim Erzeugen, nicht im Deploy. Neu erzeugen nur, wenn sich
die Schriftdateien ändern. Lizenz: Manrope steht unter der SIL Open Font License 1.1 – Einbetten in PDF ist erlaubt.
"""
import base64
import io
import json
import zlib
from pathlib import Path

from fontTools import subset
from fontTools.ttLib import TTFont

ROOT = Path(__file__).resolve().parent.parent
SCHNITTE = {"r": (400, "Regular", 80), "s": (600, "SemiBold", 120), "b": (700, "Bold", 140)}   # Schlüssel in pdf.js: r, s, b
WINANSI = list(range(32, 127)) + list(range(160, 256)) + [
    0x20AC, 0x201A, 0x0192, 0x201E, 0x2026, 0x2020, 0x2021, 0x02C6, 0x2030, 0x0160, 0x2039, 0x0152, 0x017D,
    0x2018, 0x2019, 0x201C, 0x201D, 0x2022, 0x2013, 0x2014, 0x02DC, 0x2122, 0x0161, 0x203A, 0x0153, 0x017E, 0x0178]
# Code 128–159 in WinAnsi → Unicode (für die Breitentabelle)
CP1252 = {i: bytes([i]).decode("cp1252", errors="ignore") for i in range(128, 160)}


def schnitt(gewicht, name, stamm):
    f = TTFont(ROOT / f"manrope-{gewicht}.woff2")
    opt = subset.Options()
    opt.layout_features = []
    opt.drop_tables += ["GSUB", "GPOS", "GDEF", "STAT"]
    opt.name_IDs = [1, 2, 3, 4, 6]
    opt.notdef_outline = True
    opt.recalc_bounds = True
    sub = subset.Subsetter(opt)
    sub.populate(unicodes=WINANSI)
    sub.subset(f)
    f.flavor = None
    puffer = io.BytesIO()
    f.save(puffer)
    ttf = puffer.getvalue()
    upm = f["head"].unitsPerEm
    cmap, hmtx = f.getBestCmap(), f["hmtx"]
    em = lambda v: round(v * 1000 / upm)
    breiten = []
    for code in range(32, 256):
        ch = CP1252.get(code, chr(code)) if code >= 128 else chr(code)
        glyph = cmap.get(ord(ch)) if ch else None
        breiten.append(em(hmtx[glyph][0]) if glyph else em(hmtx[cmap[32]][0]))
    kopf, os2, hhea = f["head"], f["OS/2"], f["hhea"]
    return {
        "name": f"Manrope-{name}",
        "breiten": breiten,
        "box": [em(kopf.xMin), em(kopf.yMin), em(kopf.xMax), em(kopf.yMax)],
        "aufstieg": em(hhea.ascent), "abstieg": em(hhea.descent), "versal": em(getattr(os2, "sCapHeight", 0) or 700),
        "stamm": stamm,
        "laenge": len(ttf),
        "daten": base64.b64encode(zlib.compress(ttf, 9)).decode("ascii"),
    }


def main():
    aus = {"quelle": "Manrope (SIL Open Font License 1.1), aus manrope-400/600/700.woff2 – erzeugt mit scripts/pdf_schrift.py"}
    for k, (gewicht, name, stamm) in SCHNITTE.items():
        aus[k] = schnitt(gewicht, name, stamm)
        print(f"{k}: Manrope-{name}, TTF {aus[k]['laenge']} Bytes, gepackt+Base64 {len(aus[k]['daten'])} Zeichen")
    (ROOT / "pdf-schrift.json").write_text(json.dumps(aus, separators=(",", ":")) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
