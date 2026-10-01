#!/usr/bin/env python3
"""update_top10_kupon.py – die 30 Anleihen mit dem höchsten Kupon auf der EZB-Liste (seit 01.10.2026).

Nutzerwunsch 01.10.2026: „TOP 10 nach Coupon. Voraussetzung: in der EZB-Liste. Mindestens zwei Jahre Restlaufzeit.
Unternehmensanleihen.“ Am selben Tag erweitert: „da sollen jetzt alle Anleihen rein, auch Staatsanleihen – mach daraus
eine Top 30“. Seite: anleihen-kupon.html (Menü „Anleihen“, Gruppe „Top 30 nach Kupon“; bis dahin
unternehmensanleihen-kupon.html, per .htaccess weitergeleitet). Der Dateiname behält „top10“, weil der Datenlauf
top10-*.json committet.

Aufruf (im Website-Ordner, im Workflow nach update_kurse.py, update_anleihen_index.py und update_top10.py):
    python3 scripts/update_top10_kupon.py

Liest:
  anleihen-index.json   Stammdaten (ESMA FIRDS + GLEIF)
  anleihen-kurse.json   letzter Kurs, Rendite (berechnet), Kursdatum
  EZB                   Liste der notenbankfähigen marktfähigen Sicherheiten („eligible marketable assets“), Tagesdatei
                        https://www.ecb.europa.eu/paym/coll/assets/html/dla/ea_MID/ea_csv_<JJMMTT>.csv.gz
                        (rund 1,1 MB, UTF-16, Tabulator-getrennt; erscheint montags bis freitags um 18:15 Uhr, nicht an
                        TARGET-Feiertagen – deshalb vom heutigen Tag rückwärts die jüngste vorhandene Datei).
                        Nutzung laut EZB frei, wenn die EZB als Quelle genannt und eine Bearbeitung kenntlich gemacht
                        wird (ecb.europa.eu → Disclaimer & Copyright, gelesen am 01.10.2026) – steht so auf der Seite.
Schreibt:
  top10-anleihen-kupon.json
  {updated, updatedAt, stand (Kursstand), ezb: {stand, anzahl}, regeln: {min_jahre, max_stueckelung, waehrungen}, kandidaten,
   gruppen: {"kupon": [Zeile …]}}
  Zeile wie in update_top10.py, ohne Handelstage und Umsatz:
  {isin, emittent, art, cur, kupon, zins (Zinszahlungen/Jahr), faellig, kurs, datum, rendite|null, vol, stk}

Auswahl:
  Vorgabe     alle drei Arten des Index – Staat, Öffentlich (Bundesländer, Förderbanken, Supranationale) und
              Unternehmen (wie in der Suche: einschließlich Banken und Versicherer) –, ISIN auf der EZB-Liste,
              Restlaufzeit ab Valuta mindestens MIN_JAHRE Jahre
  Währung     Euro oder US-Dollar (WAEHRUNGEN) – so hatte der Nutzer die Liste zuletzt angesehen („nur Dollar und Euro“)
  Stückelung  höchstens MAX_STUECKELUNG in der Währung der Anleihe (Nutzerwunsch 01.10.2026, „Stückelung bis 1.000“):
              In der ersten Fassung hatten vier der zehn eine Stückelung von 100.000 oder 200.000. Ohne Angabe im
              Register zählt eine Anleihe nicht mit.
  Grundregeln wie update_top10.py: fester Kupon, Fälligkeit angegeben, aktueller Kurs (≤ 14 Tage alt), nicht nachrangig,
              nicht unbefristet, keine Inflations-, Stufenzins-, Wandel-, Tilgungs- oder 144A-Anleihen, keine Strips
  Datenprüfung ohne Befund (Feld pruef des Index) – ein Kupon, der im Register um den Faktor 10 zu hoch steht, stünde
              sonst auf Platz 1
Rang: Kupon absteigend; bei gleichem Kupon das größere Volumen, dann die ISIN. Kein Umsatzkriterium, keine Grenze je
Emittent (beides nicht verlangt).

Schutz: Fehlen Index oder Kurse, ist die EZB-Datei nicht abrufbar oder unplausibel klein, oder bliebe keine Anleihe
übrig, bleibt die alte Datei stehen (Rückgabewert 1; der Workflow-Schritt läuft mit continue-on-error).
"""
import datetime
import gzip
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import get_with_retry, log_err, now_iso, ohne_rendite, today_iso, write_atomic, zinsfrequenz  # noqa: E402
from update_top10 import AKTUELL_TAGE, INFLATION, STAATSNAME, STRIPS, WANDEL, emittent_wm, lade, plus_boersentage  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
INDEX, KURSE = ROOT / "anleihen-index.json", ROOT / "anleihen-kurse.json"
OUT = ROOT / "top10-anleihen-kupon.json"

EZB_URL = "https://www.ecb.europa.eu/paym/coll/assets/html/dla/ea_MID/ea_csv_{:%y%m%d}.csv.gz"
EZB_TAGE_ZURUECK = 7      # Wochenende plus Feiertage (Ostern, Weihnachten) – älter soll die Liste nicht sein
EZB_MIN_ZEILEN = 20000    # die Liste hat rund 31.000 Zeilen; deutlich weniger = abgeschnittene oder falsche Datei
MIN_JAHRE = 2
MAX_STUECKELUNG = 1000
WAEHRUNGEN = ("EUR", "USD")
TOP = 30
ART = ("Staat", "Öffentlich", "Unternehmen")
# Im WM-Kurznamen klebt das Währungskürzel teils ohne Leerzeichen am Emittenten („… International asEO-Medium-Term“) –
# emittent_wm schneidet nur an einer Wortgrenze. Hier nachschneiden, statt die gemeinsame Regel der Top-10-Seiten zu ändern.
GEKLEBT = re.compile(r"(?<=[a-z.)])[A-Z]{2}-[A-Z0-9].*$")
# Bundesländer und Förderbanken: Der Kurzname hängt die Wertpapierbezeichnung ohne das übliche Kürzel an
# („HESSEN, LAND SCHATZANW.V.1998(2029)SER.9802“) – ab der Bezeichnung abschneiden, Versalien in Normalschrift.
BEZEICHNUNG = re.compile(r"\s*(?:Landessch|Schatzanw|Landesobl|Kassenobl|Inh\.-Schv|Öff\.?\s?Pfdbr)\S*.*$", re.I)


def ezb_liste(heute: datetime.date):
    """Jüngste Tagesdatei der EZB: (Datum der Datei, Menge der ISINs) oder (None, set())."""
    for n in range(EZB_TAGE_ZURUECK + 1):
        tag = heute - datetime.timedelta(days=n)
        if tag.weekday() > 4:
            continue
        try:
            roh = get_with_retry(EZB_URL.format(tag), timeout=60)
        except Exception as e:   # 404 = Datei des Tages gibt es (noch) nicht – den Vortag versuchen
            print(f"EZB-Liste vom {tag.isoformat()}: nicht abrufbar ({e})")
            continue
        try:
            zeilen = gzip.decompress(roh).decode("utf-16").splitlines()
        except Exception as e:
            log_err(f"EZB-Liste vom {tag.isoformat()}: nicht lesbar ({e})")
            continue
        kopf = zeilen[0].split("\t") if zeilen else []
        if "ISIN_CODE" not in kopf or len(zeilen) < EZB_MIN_ZEILEN:
            log_err(f"EZB-Liste vom {tag.isoformat()}: unerwartetes Format ({len(zeilen)} Zeilen, Kopf {kopf[:3]})")
            continue
        i = kopf.index("ISIN_CODE")
        isins = {f[i] for f in (z.split("\t") for z in zeilen[1:]) if len(f) > i and len(f[i]) == 12}
        return tag, isins
    return None, set()


def main() -> int:
    idx, kd = lade(INDEX), lade(KURSE)
    if not idx or not idx.get("rows") or not kd or not isinstance(kd.get("kurse"), dict):
        log_err("Top 10 nach Kupon: Index oder Kurse fehlen – Datei bleibt unverändert.")
        return 1
    ezb_tag, ezb = ezb_liste(datetime.date.fromisoformat(today_iso()))
    if not ezb:
        log_err("Top 10 nach Kupon: keine EZB-Liste der letzten Tage abrufbar – Datei bleibt unverändert.")
        return 1

    emi, stand = idx.get("emittenten") or [], kd.get("stand")
    ktage, kurse = kd.get("tage") or [], kd["kurse"]
    d_stand = datetime.date.fromisoformat(stand)
    grenze = (d_stand - datetime.timedelta(days=AKTUELL_TAGE)).isoformat()

    zeilen = []
    for r in idx["rows"]:
        isin, name = r[0], r[1]
        if r[2] not in (0, 1, 2) or r[3] not in WAEHRUNGEN or isin not in ezb:
            continue
        if not isinstance(r[7], (int, float)) or r[7] > MAX_STUECKELUNG:
            continue
        k = kurse.get(isin)
        if not k or r[10] != 0 or not isinstance(r[4], (int, float)) or r[4] <= 0 or not r[5]:
            continue
        if ohne_rendite(r) or INFLATION.search(name) or STRIPS.search(name) or WANDEL.search(name):
            continue
        if len(r) > 14 and isinstance(r[14], dict) and r[14]:   # Widerspruch Kurzname/Register (z. B. Kupon Faktor 10)
            continue
        try:
            datum = ktage[k[2]]
        except (IndexError, TypeError):
            continue
        if datum < grenze:
            continue
        mehr = r[13] if len(r) > 13 and r[13] else ["---"]
        if (mehr[0] or "-")[0] in "UJM" or (mehr[0] + "--")[1] in "PQ":   # nachrangig bzw. unbefristet
            continue
        valuta = plus_boersentage(d_stand, 1 if r[3] == "USD" else 2)
        if (datetime.date.fromisoformat(r[5]) - valuta).days / 365.25 < MIN_JAHRE:
            continue
        em = (STAATSNAME.get(r[11]) if r[2] == 0 else None) or GEKLEBT.sub("", emittent_wm(name, emi[r[9]] if r[9] < len(emi) else "")).strip()
        if r[2] == 1:
            em = BEZEICHNUNG.sub("", em).strip() or em
            em = em.title() if em.isupper() else em
        zeilen.append({"isin": isin, "emittent": em,
                       "art": ART[r[2]], "cur": r[3], "kupon": r[4], "zins": zinsfrequenz(r), "faellig": r[5],
                       "kurs": k[0], "datum": datum, "rendite": k[1] if isinstance(k[1], (int, float)) else None,
                       "vol": r[6], "stk": r[7]})
    if not zeilen:
        log_err("Top 10 nach Kupon: keine Anleihe erfüllt die Regeln – Datei bleibt unverändert.")
        return 1

    top = sorted(zeilen, key=lambda x: (-x["kupon"], -(x["vol"] or 0), x["isin"]))[:TOP]
    write_atomic(OUT, {"updated": today_iso(), "updatedAt": now_iso(), "stand": stand,
                       "ezb": {"stand": ezb_tag.isoformat(), "anzahl": len(ezb)},
                       "regeln": {"min_jahre": MIN_JAHRE, "max_stueckelung": MAX_STUECKELUNG, "waehrungen": list(WAEHRUNGEN)},
                       "kandidaten": len(zeilen), "gruppen": {"kupon": top}}, indent=None)
    print(f"{OUT.name}: {len(top)} von {len(zeilen)} Anleihen (Kurse {stand}, EZB-Liste {ezb_tag.isoformat()} mit {len(ezb)} Papieren); "
          f"Kupon {top[0]['kupon']} % bis {top[-1]['kupon']} %")
    return 0


if __name__ == "__main__":
    sys.exit(main())
