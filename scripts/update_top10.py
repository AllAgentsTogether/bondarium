#!/usr/bin/env python3
"""update_top10.py – die zehn meistgehandelten Anleihen je Gruppe, täglich aus den Börsendaten (seit 26.09.2026).

Nutzerwunsch: „da sollten immer die aktuellen Top 10 stehen“. Bis 26.09.2026 waren die Listen der Seiten
„… nach Laufzeit“ und „… nach Ländern“ eine Handauswahl (Börse Stuttgart 23.09.2025–22.09.2026).

Aufruf (im Website-Ordner, im Workflow nach update_kurse.py und update_anleihen_index.py):
    python3 scripts/update_top10.py

Liest:
  anleihen-index.json        Stammdaten (ESMA FIRDS + GLEIF): Art, Land (Konzernsitz), Währung, Kupon, Zinsart,
                             Fälligkeit, Volumen, Stückelung, Rang
  anleihen-kurse.json        letzter Kurs, Rendite (BERECHNET), Kursdatum
  kurse/<Jahr>/<hh>.json     Umsatz je Tag ("u") – Summe Börse Frankfurt + Tradegate, BERECHNET als Stück × Kurs
Schreibt (je Seite eine Datei, per inline_data.py in die Seite eingebettet):
  top10-staatsanleihen-laufzeit.json, top10-unternehmensanleihen-laufzeit.json,
  top10-staatsanleihen-laender.json,  top10-unternehmensanleihen-laender.json
  {updated, updatedAt, stand, fenster: {von, bis, tage, soll}, aktiv, min_tage, gruppen: {<anker/slug>: [Zeile …]}}
  aktiv = true, sobald mindestens MIN_TAGE Börsentage erfasst sind – erst dann ersetzen die Seiten ihre Handauswahl.
  Zeile = {isin, emittent, art, cur, kupon, zins (Zinszahlungen/Jahr), faellig, kurs, datum, rendite|null,
           vol, stk, ht (Handelstage im Fenster), um (Umsatz im Fenster, Anleihewährung)}

Rangfolge („meistgehandelt“): Zahl der Börsentage mit Umsatz im Fenster der letzten FENSTER Börsentage
(bzw. aller erfassten, solange es weniger sind; erfasst wird seit 24.09.2026), bei Gleichstand der Umsatz.
Nur Anleihen, die im Fenster mindestens einmal gehandelt wurden – eine Gruppe kann also weniger als zehn haben.

Auswahl:
  gemeinsam   fester Kupon oder Nullkupon, Fälligkeit angegeben, aktueller Kurs (≤ 14 Tage alt), nicht nachrangig,
              nicht inflationsindexiert, keine Strips/Zinsscheine, Restlaufzeit ≥ 14 Tage; seit 26.09.2026 außerdem
              keine FLR-/Fix-to-Float-, Stufenzins-, Wandel- oder Tilgungsanleihen (außer kurzer Tilgung erst am Ende;
              _common.ohne_rendite – für sie gibt es keine Rendite bis Fälligkeit)
  Staat       Art „Staat“ (Zentralstaaten; nicht Länder, Kommunen, Förderbanken, Supranationale)
  Unternehmen Art „Unternehmen“ wie in der Anleihen-Suche, also einschließlich Banken und Versicherer; ohne
              Wandel-/Umtauschanleihen und 144A-Tranchen, nicht unbefristet. Bis 01.10.2026 fielen Banken, Versicherer
              und Finanzdienstleister über eine Namensliste heraus (Nutzerentscheid 01.10.2026: einheitlich mit der
              Suche; die Liste war zudem lückenhaft – Gegenprobe mit der EZB-Liste notenbankfähiger Sicherheiten:
              424 von 4.119 Kreditinstituten nicht erkannt, etwa Caixabank, BPCE, Swedbank)
  Länder      zusätzlich Restlaufzeit über einem Jahr; Land = Sitz (bei Unternehmen: des Konzerns, GLEIF)
Schutz: Fehlen Index, Kurse oder Umsätze, bleiben die alten Dateien stehen; ebenso, wenn eine Seite insgesamt
weniger als die Hälfte ihrer bisherigen Zeilen bekäme (Datenfehler).
"""
import datetime
import glob
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import log_err, now_iso, ohne_rendite, today_iso, write_atomic, zins_felder, zinstermine_laden  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
INDEX, KURSE, VERLAUF = ROOT / "anleihen-index.json", ROOT / "anleihen-kurse.json", ROOT / "kurse"

# Beginn der eigenen Umsatz-Sammlung (Deutsche Börse, update_kurse.py). Ältere Tage in kurse/ stammen aus
# rückwirkend eingespielten Quellen ohne Umsatz (seit 29.09.2026: U.S. Treasury ab 2021) und zählen hier nicht –
# sonst füllten sie das Fenster, und die Rangliste würde „aktiv“, bevor genug Handelstage erfasst sind.
SAMMLUNG_AB = "2026-09-24"
FENSTER = 60          # Börsentage (rund drei Monate)
MIN_TAGE = 20         # erst ab so vielen erfassten Börsentagen gilt die Rangliste („aktiv“); vorher zeigen die Seiten
                      # ihre bisherige Handauswahl – mit zwei, drei Tagen wäre die Reihenfolge Zufall
TOP = 10
AKTUELL_TAGE = 14     # Kurs höchstens so alt wie in der Suche
# Zinszahlungen je Jahr, Zinstage und „Rendite sinnvoll?“: _common.zins_felder / _common.ohne_rendite (wie update_kurse.py)
INFLATION = re.compile(r"infl|inflat|linker|\blkd\b|i/l|\btips\b|hicp|hvpi|\bcpi\b|\brpi\b|index", re.I)
STRIPS = re.compile(r"strip|kupons? per|kapital per|zinsschein|principal|\bcoupon\b|\bcpn\b", re.I)
WANDEL = re.compile(r"wandel|umtausch|conv|exch\.?|\b144a\b|options?anl|optionsschein", re.I)
GRUPPEN = [("sehr-kurzfristig", 1), ("kurzfristig", 3), ("mittelfristig", 7), ("langfristig", 30), ("sehr-langfristig", 1e9)]
# Seit 30.09.2026 zusätzlich Australien, Belgien, Finnland, Irland, Kanada, Niederlande, Ungarn: in den ersten drei
# Börsentagen 6 bis 14 gehandelte Anleihen je Land (Polen 9, Türkei und Südafrika 6). Für sie gibt es keine Handauswahl –
# anleihen-laender.html zeigt ihre Liste schon vor „aktiv“ (LAENDER[…].auto). Ein neues Land braucht außerdem einen Knopf
# und einen LAENDER-Eintrag in der Seite sowie eine Fläche mit data-land in weltkarte.svg.
STAAT_LAENDER = {"australien": "AU", "belgien": "BE", "deutschland": "DE", "finnland": "FI", "frankreich": "FR",
                 "griechenland": "GR", "grossbritannien": "GB", "irland": "IE", "italien": "IT", "kanada": "CA",
                 "niederlande": "NL", "norwegen": "NO", "oesterreich": "AT", "polen": "PL", "rumaenien": "RO",
                 "spanien": "ES", "suedafrika": "ZA", "tuerkei": "TR", "ungarn": "HU", "usa": "US"}
FIRMEN_LAENDER = {"deutschland": "DE", "frankreich": "FR", "grossbritannien": "GB", "oesterreich": "AT",
                  "schweiz": "CH", "usa": "US"}
STAATSNAME = {
    "DE": "Bundesrepublik Deutschland", "FR": "Republik Frankreich", "IT": "Republik Italien", "ES": "Königreich Spanien",
    "AT": "Republik Österreich", "NO": "Königreich Norwegen", "BE": "Königreich Belgien",
    "NL": "Königreich der Niederlande", "GB": "Vereinigtes Königreich", "US": "Vereinigte Staaten",
    "PL": "Republik Polen", "RO": "Rumänien", "GR": "Hellenische Republik", "ZA": "Republik Südafrika",
    "TR": "Republik Türkei", "IE": "Irland", "FI": "Republik Finnland", "PT": "Portugiesische Republik",
    "CZ": "Tschechische Republik", "SK": "Slowakische Republik", "SI": "Republik Slowenien", "HU": "Ungarn",
    "CA": "Kanada", "AU": "Australien", "NZ": "Neuseeland", "SE": "Königreich Schweden", "DK": "Königreich Dänemark",
    "CH": "Schweizerische Eidgenossenschaft", "MX": "Mexiko", "BR": "Brasilien", "CN": "Volksrepublik China",
    "JP": "Japan", "LU": "Großherzogtum Luxemburg", "LT": "Republik Litauen", "LV": "Republik Lettland",
    "EE": "Republik Estland", "HR": "Republik Kroatien", "BG": "Republik Bulgarien", "CY": "Republik Zypern",
    "IS": "Island", "IL": "Staat Israel", "CL": "Republik Chile", "CO": "Republik Kolumbien", "PE": "Republik Peru",
    "ID": "Republik Indonesien", "AR": "Argentinien", "UA": "Ukraine", "EG": "Ägypten", "SA": "Saudi-Arabien",
    "AE": "Vereinigte Arabische Emirate", "PH": "Philippinen", "UY": "Uruguay", "PA": "Panama", "KZ": "Kasachstan",
    "RS": "Serbien", "MA": "Marokko", "CI": "Elfenbeinküste", "NG": "Nigeria", "KR": "Republik Korea"}
# Emittent aus dem WM-Kurznamen der Börse: alles vor der Wertpapierbezeichnung („BMW Internat. Investment B.V.
# EO-Medium-Term Notes 2024(28)“ → „BMW Internat. Investment B.V.“) – lesbarer als die GLEIF-Namen in Versalien.
WM_SCHNITT = re.compile(
    r"(?:\b[A-Z]{2}-(?=[A-Z0-9])|\s(?:Medium|Med\.|MTN|Anl\b|Anl\.|Anleihe|Inh\.|Notes|Nts|Bonds|Bds|FLR|Obl|Schv|IHS|"
    r"Sub|Nachr|Hyp|Pfbr|Zero|Nullk|Debt|Loan|Tr\.|Treas|Senior|Sen\.|Fix|Reg\.|Ser\.|Serie|S\.\d|v\.\s?\d|\d{2,4}\s?\())")


def emittent_wm(name, fallback):
    m = WM_SCHNITT.search(name)
    e = (name[:m.start()] if m else name).strip().rstrip(" ,-(/").strip()
    if len(e) < 2:
        return fallback
    return re.sub(r"\s{2,}", " ", e)


def plus_boersentage(d, n):
    while n:
        d += datetime.timedelta(days=1)
        if d.weekday() < 5:
            n -= 1
    return d


def lade(p, leer=None):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return leer


def main() -> int:
    idx, kd = lade(INDEX), lade(KURSE)
    if not idx or not idx.get("rows") or not kd or not isinstance(kd.get("kurse"), dict):
        log_err("Top 10: Index oder Kurse fehlen – Dateien bleiben unverändert.")
        return 1
    emi, stand = idx.get("emittenten") or [], kd.get("stand")
    termine = zinstermine_laden()   # Zinstage laut Börsenliste (update_zinstermine.py)
    ktage, kurse = kd.get("tage") or [], kd["kurse"]
    d_stand = datetime.date.fromisoformat(stand)
    grenze = (d_stand - datetime.timedelta(days=AKTUELL_TAGE)).isoformat()

    # Umsatz je Tag aus dem Kursverlauf (laufendes und voriges Jahr genügen für 60 Börsentage)
    alle_tage, umsatz = set(), {}
    for jahr in (d_stand.year - 1, d_stand.year):
        for f in glob.glob(str(VERLAUF / str(jahr) / "*.json")):
            v = lade(f, {}) or {}
            t = v.get("tage") or []
            alle_tage.update(x for x in t if SAMMLUNG_AB <= x <= stand)
            for isin, u in (v.get("u") or {}).items():
                ziel = umsatz.setdefault(isin, {})
                for n, wert in u.items():
                    try:
                        ziel[t[int(n)]] = wert
                    except (ValueError, IndexError):
                        pass
    fenster = sorted(alle_tage)[-FENSTER:]
    if not fenster or not umsatz:
        log_err("Top 10: kein Kursverlauf mit Umsätzen – Dateien bleiben unverändert.")
        return 1
    fset = set(fenster)

    def kandidat(r):
        """Gemeinsame Regeln; gibt (Restlaufzeit in Jahren, Kurszeile) oder None zurück."""
        isin, name = r[0], r[1]
        k = kurse.get(isin)
        if not k or r[10] not in (0, 2) or not isinstance(r[4], (int, float)) or not r[5]:
            return None
        if ohne_rendite(r):   # nur fester Kupon mit Rückzahlung am Ende – keine FLR-, Stufenzins-, Wandel-, Tilgungs-
            return None       # oder Inflationsanleihen (dieselbe Regel wie die Rendite in update_kurse.py, seit 26.09.2026)
        try:
            datum = ktage[k[2]]
        except (IndexError, TypeError):
            return None
        if datum < grenze or INFLATION.search(name) or STRIPS.search(name):
            return None
        mehr = r[13] if len(r) > 13 and r[13] else ["---"]
        if (mehr[0] or "-")[0] in "UJM":
            return None
        # Restlaufzeit ab Valuta wie auf den Seiten (USD/GBP ein, sonst zwei Börsentage nach dem Kursstand)
        valuta = plus_boersentage(d_stand, 1 if r[3] in ("USD", "GBP") else 2)
        jahre = (datetime.date.fromisoformat(r[5]) - valuta).days / 365.25
        if jahre < 14 / 365.25:
            return None
        return jahre, k, datum, mehr

    def zeile(r, k, datum, art):
        isin, cur = r[0], r[3]
        u = umsatz.get(isin, {})
        ht = sum(1 for t, w in u.items() if t in fset and w > 0)
        um = sum(w for t, w in u.items() if t in fset)
        if art == "Staat":
            em = STAATSNAME.get(r[11]) or emittent_wm(r[1], emi[r[9]] if r[9] < len(emi) else "")
        else:
            em = emittent_wm(r[1], emi[r[9]] if r[9] < len(emi) else "")
        return {"isin": isin, "emittent": em, "art": art, "cur": cur, "kupon": r[4],
                **zins_felder(r, termine), "faellig": r[5], "kurs": k[0], "datum": datum,
                "rendite": k[1] if isinstance(k[1], (int, float)) else None,
                "vol": r[6], "stk": r[7], "ht": ht, "um": round(um)}

    listen = {"top10-staatsanleihen-laufzeit.json": {}, "top10-unternehmensanleihen-laufzeit.json": {},
              "top10-staatsanleihen-laender.json": {}, "top10-unternehmensanleihen-laender.json": {}}
    staat_lz, firma_lz, staat_ld, firma_ld = listen.values()
    for r in idx["rows"]:
        if r[2] not in (0, 2):
            continue
        c = kandidat(r)
        if not c:
            continue
        jahre, k, datum, mehr = c
        if r[2] == 0:
            z = zeile(r, k, datum, "Staat")
            if not z["ht"]:
                continue
            anker = next(a for a, bis in GRUPPEN if round(jahre, 1) <= bis)
            staat_lz.setdefault(anker, []).append(z)
            slug = next((s for s, code in STAAT_LAENDER.items() if code == r[11]), None)
            if slug and jahre > 1:
                staat_ld.setdefault(slug, []).append(z)
        else:
            if WANDEL.search(r[1]) or (len(mehr) and (mehr[0] + "--")[1] in "PQ"):
                continue
            z = zeile(r, k, datum, "Unternehmen")
            if not z["ht"]:
                continue
            anker = next(a for a, bis in GRUPPEN if round(jahre, 1) <= bis)
            firma_lz.setdefault(anker, []).append(z)
            slug = next((s for s, code in FIRMEN_LAENDER.items() if code == r[11]), None)
            if slug and jahre > 1:
                firma_ld.setdefault(slug, []).append(z)

    kopf = {"updated": today_iso(), "updatedAt": now_iso(), "stand": stand,
            "fenster": {"von": fenster[0], "bis": fenster[-1], "tage": len(fenster), "soll": FENSTER},
            "aktiv": len(fenster) >= MIN_TAGE, "min_tage": MIN_TAGE}
    rc = 0
    # Hinweis (30.09.2026): Länder ohne gehandelte Anleihe im Fenster fehlen in der Liste; die Seiten blenden sie dann aus.
    # Die Schweiz fehlte bei Unternehmensanleihen bis zum Index-Lauf nach dem 30.09.2026 nur, weil Nestlé Finance
    # International GLEIF keine Mutter meldet (stand unter LU) – seitdem Konzernmutter über Namensverwandte, siehe
    # update_anleihen_index.namensverwandte().
    for datei, slugs in (("top10-staatsanleihen-laender.json", STAAT_LAENDER), ("top10-unternehmensanleihen-laender.json", FIRMEN_LAENDER)):
        leer = [s for s in slugs if not listen[datei].get(s)]
        if leer:
            print(f"{datei}: ohne gehandelte Anleihe im Fenster: {', '.join(leer)}")
    for datei, gruppen in listen.items():
        top = {g: sorted(z, key=lambda x: (-x["ht"], -x["um"], -(x["vol"] or 0), x["isin"]))[:TOP]
               for g, z in gruppen.items()}
        n_neu = sum(len(v) for v in top.values())
        alt = lade(ROOT / datei, {}) or {}
        n_alt = sum(len(v) for v in (alt.get("gruppen") or {}).values())
        if n_alt and n_neu < 0.5 * n_alt:
            log_err(f"Top 10: {datei} hätte nur {n_neu} statt {n_alt} Zeilen – bleibt unverändert.")
            rc = 1
            continue
        write_atomic(ROOT / datei, {**kopf, "gruppen": top}, indent=None)
        print(f"{datei}: {n_neu} Anleihen in {len(top)} Gruppen (Fenster {fenster[0]} … {fenster[-1]}, {len(fenster)} Börsentage)")
    return rc


if __name__ == "__main__":
    sys.exit(main())
