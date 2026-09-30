#!/usr/bin/env python3
"""suchindex.py – baut suchindex.json, den schlanken Datensatz der Anleihen-Suche (anleihen-suche.html). Seit 30.09.2026.

Aufruf (im Stammordner, NACH scripts/update_anleihen_index.py und scripts/update_kurse.py):

    python3 scripts/suchindex.py

Liest  anleihen-index.json (Stammdaten, ESMA FIRDS + GLEIF) und anleihen-kurse.json (Tageskurse, Deutsche Börse/Bundesbank),
schreibt suchindex.json. Vorher lud die Suche beide Dateien vollständig (~8,8 MB, gzip ~1,5 MB), obwohl sie nur Anleihen mit
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
        kurs, rendite, tag, boerse_kurs, umsatz, vortag, aufschlag]
"""
import json
import re
import sys
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INDEX, KURSE, OUT = ROOT / "anleihen-index.json", ROOT / "anleihen-kurse.json", ROOT / "suchindex.json"
AKTUELL_TAGE = 14   # wie anleihen-suche.html: Kurs höchstens so viele Kalendertage vor dem Kursstand

# ---------- Emittent lesbar (gleiche Regel wie lesbar() in anleihe.html – bei Änderungen beide anpassen) ----------
RF_SCHREIB = {"AG": "AG", "SE": "SE", "KG": "KG", "KGAA": "KGaA", "GMBH": "GmbH", "MBH": "mbH", "N.V.": "N.V.", "B.V.": "B.V.", "S.A.": "S.A.", "S.A": "S.A.",
              "S.P.A.": "S.p.A.", "SPA": "S.p.A.", "S.A.S.": "S.A.S.", "S.À": "S.à", "R.L.": "r.l.", "S.R.L.": "S.r.l.", "SRL": "S.r.l.", "S.L.": "S.L.", "SARL": "S.à r.l.",
              "INC.": "Inc.", "INC": "Inc.", "LTD.": "Ltd.", "LTD": "Ltd", "CORP.": "Corp.", "CORP": "Corp.", "CO.": "Co.", "CO": "Co.", "PTE.": "Pte.", "PTE": "Pte.", "PTY": "Pty",
              "OYJ": "Oyj", "P.L.C.": "p.l.c.", "L.P.": "L.P.", "LLP": "LLP", "LLC": "LLC", "PLC": "PLC", "A/S": "A/S", "ASA": "ASA", "AB": "AB", "AS": "AS", "SA": "SA",
              "NV": "NV", "BV": "BV", "SAS": "SAS", "C.V.": "C.V.", "S.A.B.": "S.A.B.", "KFW": "KfW", "ENBW": "EnBW", "E.ON": "E.ON", "AT&T": "AT&T"}
RF_IMMER = {"KFW", "ENBW", "E.ON", "AT&T"}
KLEINWORT = set("OF AND THE FOR DE DI DEL DELLA DES DU LA LE LES Y E ET EN IN FÜR UND DER DIE DAS DEN VON VAN ZU AM IM AUF PER DA DO DOS".split())
KUERZEL = set("BASF BBVA AMRO BAWAG NIBC RATP SICAV SOFOM HSBC LBBW NRW USA UK US EU".split())
WORT3 = set("OIL GAS NEW AIR SEA SUN BAY CAR ONE TWO TEN BIG RED OWL TOP WAY KEY AID ART BIO BOX CAP FIN LAB LAW MAX NET PAY PRO RIO SKY SOL TEA TEL WEB BAU".split())
VOKAL = re.compile(r"[AEIOUYÄÖÜÉÈÀÁÍÓÚÂÊÎÔÛİ]")
BUCHST = re.compile(r"([A-Za-zÀ-ÖØ-öø-ÿİŞĞÇ]+)")
RAND = re.compile(r"^[,;()\"']+|[,;()\"']+$")


def lesbar_wort(w, erstes, nach_apostroph):
    u = w.upper()
    if len(w) == 1:
        return w.lower() if nach_apostroph else w
    if not erstes and u in KLEINWORT:
        return w.lower()
    if u in KUERZEL or not VOKAL.search(u):
        return w
    if len(w) <= 3 and u not in WORT3 and u not in KLEINWORT:
        return w
    return w[0] + w[1:].replace("İ", "i").lower()


def lesbar(name):
    s = str(name or "").strip()
    if not s or re.search(r"[a-zß-ÿ]", s) or not re.search(r"[A-Z]", s):
        return s   # schon gemischt geschrieben oder keine lateinische Schrift
    out = []
    for i, tok in enumerate(s.split()):
        kern = RAND.sub("", tok)
        vor = tok[:tok.index(kern)] if kern else tok
        nach = tok[len(vor) + len(kern):] if kern else ""
        k = kern.upper()
        if k in RF_SCHREIB and (i > 0 or k in RF_IMMER):
            out.append(vor + RF_SCHREIB[k] + nach)
            continue
        teile = BUCHST.split(tok)
        out.append("".join(lesbar_wort(t, i == 0 and j == 1, (teile[j - 1] if j else "").endswith("'")) if j % 2 else t
                           for j, t in enumerate(teile)))
    return " ".join(out)


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
                              k[6] if len(k) > 6 else None, k[7] if len(k) > 7 else None])
    liste = [""] + [n for n, _ in sorted(emi_idx.items(), key=lambda x: x[1])]
    out = {
        "stand": ix.get("stand"), "kstand": kstand, "tage": tage, "boersen": ku.get("boersen") or {},
        "art": ix.get("art"), "anzahl": len(ix.get("rows") or []), "aktuellTage": AKTUELL_TAGE,
        "quelle": "scripts/suchindex.py aus anleihen-index.json und anleihen-kurse.json",
        "emittenten": liste, "rows": rows,
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"suchindex.json: {len(rows)} Anleihen mit Kurs (von {out['anzahl']} im Register), {len(liste) - 1} Emittenten, "
          f"{OUT.stat().st_size / 1e6:.1f} MB (Kurse {kstand}, Stammdaten {out['stand']})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
