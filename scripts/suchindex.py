#!/usr/bin/env python3
"""suchindex.py – baut suchindex.json, den schlanken Datensatz der Anleihen-Suche (anleihen-suche.html). Seit 30.09.2026.

Aufruf (im Stammordner, NACH scripts/update_anleihen_index.py und scripts/update_kurse.py):

    python3 scripts/suchindex.py

Liest  anleihen-index.json (Stammdaten, ESMA FIRDS + GLEIF), anleihen-kurse.json (Tageskurse, Deutsche Börse/Bundesbank) und
bonitaet/ezb-stufen.json (Bonitätsstufe laut EZB, seit 02.10.2026), schreibt suchindex.json. Vorher lud die Suche beide Dateien vollständig (~8,8 MB, gzip ~1,5 MB), obwohl sie nur Anleihen mit
aktuellem Kurs zeigt und die Tagesdaten (Eröffnung, Hoch, Tief …) nur der Steckbrief anleihe.html braucht.

suchindex.json enthält nur, was die Suche zeigt, filtert und sortiert:
  * nur Anleihen mit Kurs höchstens AKTUELL_TAGE vor dem Kursstand und nicht fällig (wie bisher im Browser gefiltert),
  * Stammdaten wie in anleihen-index.json (Felder 0–12 unverändert, damit die Suche sie gleich liest), aus „mehr“ nur Rückzahlungsart
    und Jahr des ersten Handelstags (Kündigungs-Einordnung), Datenprüfung als Objekt oder 0,
  * je Anleihe der Tageskurs ohne Tagesdaten: Kurs, Rendite, Tag (Index in „tage“), Börse, Umsatz, Vortag, Aufschlag zu Bund,
  * Emittenten in lesbarer Schreibweise (GLEIF meldet viele Namen in Versalien; gleiche Regel wie lesbar() in anleihe.html),
    nur die tatsächlich vorkommenden.

Zeile: [isin, name, art, waehrung, kupon, faellig, volumen, stueckelung, boerse, emittent (Index), zinsart, land, extra,
        "<Rückzahlungsart><Jahr erster Handelstag>", pruef (Objekt oder 0),
        kurs, rendite, tag, boerse_kurs, umsatz, vortag, aufschlag,
        bonitaet (nur bei Anleihen der EZB-Liste: 1 = Bonitätsstufen 1 und 2, 3 = Stufe 3, 0 = Stufe offen)]
"""
import json
import re
import sys
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INDEX, KURSE, OUT = ROOT / "anleihen-index.json", ROOT / "anleihen-kurse.json", ROOT / "suchindex.json"
BONITAET = ROOT / "bonitaet" / "ezb-stufen.json"   # Bonitätsstufe laut EZB (scripts/update_bonitaet.py); fehlt die Datei: ohne Angabe
AKTUELL_TAGE = 14   # wie anleihen-suche.html: Kurs höchstens so viele Kalendertage vor dem Kursstand

# Emittent lesbar: gemeinsame Regel in _common.py (lesbar, wie MC.felder.lesbar in felder.js)
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import bonitaet_stufen, lesbar, stamm_felder  # noqa: E402

AUSWAHL = ROOT / "anleihen-auswahl.json"   # Kurzname, Art, Währung, Bonität der Anleihen auf den übrigen Seiten (seit 03.10.2026)
ISIN_RE = re.compile(r"\b([A-Z]{2}[A-Z0-9]{9}[0-9])\b")


def auswahl_schreiben(ix: dict) -> int:
    """anleihen-auswahl.json: für jede ISIN, die in einer HTML-Seite steht (Ranglisten-Handauswahl, Startseite, Langläufer, Realzins …),
    die Angaben, die jede Anleihen-Tabelle zum Namen braucht – {ISIN: [kurz, art, waehrung, bon|null, registername]}. Klein genug zum
    Einbetten (scripts/inline_data.py kürzt je Seite auf deren ISINs). Die automatischen Ranglisten tragen dieselben Felder selbst."""
    isins = set()
    for html in ROOT.glob("*.html"):
        if html.name not in ("anleihen-suche.html", "404.html"):
            isins |= set(ISIN_RE.findall(html.read_text(encoding="utf-8")))
    try:
        rz = json.loads((ROOT / "realzins.json").read_text(encoding="utf-8"))
        isins |= set(ISIN_RE.findall(json.dumps(rz)))
    except (OSError, ValueError):
        pass
    emis, stufen, a = ix.get("emittenten") or [], bonitaet_stufen(), {}
    for r in ix.get("rows") or []:
        if r[0] in isins:
            f = stamm_felder(r, emis, stufen)
            a[r[0]] = [f["kurz"], r[2], r[3], f.get("bon"), r[1]]
    AUSWAHL.write_text(json.dumps({"stand": ix.get("stand"), "felder": ["kurz", "art", "waehrung", "bon", "registername"], "a": dict(sorted(a.items()))},
                                  ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    return len(a)


def main():
    try:
        ix = json.loads(INDEX.read_text(encoding="utf-8"))
        ku = json.loads(KURSE.read_text(encoding="utf-8"))
    except Exception as e:  # ohne beide Dateien kein Suchindex – der alte bleibt stehen
        print(f"::error::suchindex.py: Eingabe unlesbar ({e}) – suchindex.json unverändert", file=sys.stderr)
        return 1
    kurse, tage, kstand = ku.get("kurse") or {}, ku.get("tage") or [], ku.get("stand") or ""
    if not kstand or not kurse:
        print("::error::suchindex.py: anleihen-kurse.json ohne Stand oder Kurse – suchindex.json unverändert", file=sys.stderr)
        return 1
    grenze = (date.fromisoformat(kstand) - timedelta(days=AKTUELL_TAGE)).isoformat()
    try:
        bon = json.loads(BONITAET.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001 – ohne die Datei zeigt die Suche keine Bonitätsstufe, sonst ändert sich nichts
        bon = {}
    stufen = bon.get("stufen") or {}
    emis, emi_idx, rows = ix.get("emittenten") or [], {}, []
    for r in ix.get("rows") or []:
        k = kurse.get(r[0])
        if not k or not isinstance(k, list) or len(k) < 5:
            continue
        tag = tage[k[2]] if isinstance(k[2], int) and 0 <= k[2] < len(tage) else ""
        if tag < grenze or (r[5] and r[5] <= kstand):
            continue
        e = emis[r[9]] if isinstance(r[9], int) and 0 <= r[9] < len(emis) else ""
        ei = emi_idx.setdefault(lesbar(e), len(emi_idx) + 1) if e else 0   # 0 = kein Emittent (wie in anleihen-index.json)
        mehr = r[13] if len(r) > 13 and isinstance(r[13], list) else []
        rz = mehr[0][1] if mehr and isinstance(mehr[0], str) and len(mehr[0]) > 1 else "-"
        ab = mehr[1][:4] if len(mehr) > 1 and isinstance(mehr[1], str) else ""
        pruef = r[14] if len(r) > 14 and isinstance(r[14], dict) and r[14] else 0
        rows.append(r[:9] + [ei] + r[10:13] + [rz + ab, pruef, k[0], k[1], k[2], k[3], k[4],
                              k[6] if len(k) > 6 else None, k[7] if len(k) > 7 else None]
                    + ([stufen[r[0]]] if r[0] in stufen else []))
    liste = [""] + [n for n, _ in sorted(emi_idx.items(), key=lambda x: x[1])]
    out = {
        "stand": ix.get("stand"), "kstand": kstand, "tage": tage, "boersen": ku.get("boersen") or {},
        "art": ix.get("art"), "anzahl": len(ix.get("rows") or []), "aktuellTage": AKTUELL_TAGE,
        "ezb": bon.get("stand") or "",   # Stand der EZB-Liste hinter der Bonitätsstufe
        "quelle": "scripts/suchindex.py aus anleihen-index.json und anleihen-kurse.json",
        "emittenten": liste, "rows": rows,
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    n_auswahl = auswahl_schreiben(ix)
    print(f"suchindex.json: {len(rows)} Anleihen mit Kurs (von {out['anzahl']} im Register), {len(liste) - 1} Emittenten, "
          f"{OUT.stat().st_size / 1e6:.1f} MB (Kurse {kstand}, Stammdaten {out['stand']}); "
          f"{sum(1 for r in rows if len(r) > 22)} mit Bonitätsstufe laut EZB ({out['ezb'] or 'keine Datei'}); anleihen-auswahl.json: {n_auswahl} Anleihen")
    return 0


if __name__ == "__main__":
    sys.exit(main())
