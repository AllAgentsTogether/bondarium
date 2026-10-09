#!/usr/bin/env python3
"""frische.py – Alarm bei veralteten oder unvollständigen Daten nach dem Datenabruf (seit 09.10.2026).

    python3 scripts/frische.py [ORDNER] [--heute JJJJ-MM-TT]

Ersetzt die feste Liste im Workflow-Schritt „Frische-Prüfung“ (update-data.yml). Die kannte nur 9 der 22 Datendateien,
kurse/bund gar nicht und maß Tagesreihen in Kalendertagen – am 08.10.2026 meldete sie nur die Zinskurve und übersah
ETF-Register, Realzins, Langläufer, kurse/bund und den leeren Breakeven (Technik-Test 08.10.2026, T-26).
ORDNER: Repo-Wurzel (im Workflow „.“, Standard: der Ordner über scripts/) oder ein Bau-Ordner. Die Zwischenstände
zinstermine/ und bonitaet/ liegen nur im Repo; in einem Ordner ohne scripts/ werden sie nur geprüft, wenn sie dort liegen.

Soll je Reihe = wie aktuell sie nach dem 10-Uhr-Lauf normalerweise ist, gezählt in Handelstagen:
  * Börse (Deutsche Börse, Tagesdateien): letzter Börsentag vor heute (Kalender wie scripts/kurs_luecken.py)
  * Bundesbank und EZB (Tageswerte am Abend): letzter TARGET-Tag vor heute
  * US-Treasury: letzter US-Handelstag vor heute; Fed H.15 erscheint einen Tag später: vorletzter US-Handelstag
  * Japan (MoF, JSDA): drittletzter TARGET-Tag – Golden Week und Silver Week folgen nicht dem TARGET-Kalender
  * China (ChinaBond): höchstens 10 Kalendertage alt (Feiertage wie die Goldene Woche unbekannt) – wie bisher
  * ESMA-Register (wöchentlich, samstags): Samstag der Vorwoche
  * Monatswerte (OECD, HQM, RBA): Soll ist der Monat vor drei Monaten, Verbraucherpreise der vor zwei Monaten –
    entspricht den bisherigen Schwellen von 100 bzw. 75 Tagen
Alarm (Rückgabe 1 = roter Lauf, E-Mail von GitHub) ab 2 Handelstagen Rückstand gegen das Soll; ein Handelstag wird nur
genannt (eine Quelle hat einmal spät geliefert). Monatswerte: Alarm, sobald der Stand älter ist als der Soll-Monat.
Außerdem Alarm, wenn eine Datei fehlt oder unlesbar ist oder ein Pflichtwert fehlt:
  * realzins.json: Breakeven je inflationsindexierter Bundesanleihe (bleibt leer, wenn die Bundesbank-Kurve fehlt)
  * anleihen-kurse.json: mindestens 50 % der Euro-Anleihen mit Rendite vom letzten Kurstag haben einen Aufschlag zu Bund
    (fällt auf 0, wenn keine Bund-Kurve da ist – scripts/update_kurse.py, KURVE_ALTER_TAGE)
Eine Datendatei im Stammordner, die hier nicht vorkommt, ergibt nur eine Warnung (neue Datei: hier aufnehmen).
"""
import argparse
import datetime
import glob
import json
import os
import re
import sys

ALARM_AB = 2                # Handelstage Rückstand gegen das Soll
AUFSCHLAG_ANTEIL_MIN = 0.5  # Anteil der Euro-Kurse mit Aufschlag zu Bund
CHINA_TAGE = 10             # Kalendertage
# Dateien im Stammordner ohne Frische-Prüfung (Handpflege, Bau, Werkzeuge)
OHNE_PRUEFUNG = {"broker.json", "themen.json", "package.json", "package-lock.json"}


# ---------------------------------------------------------------- Kalender
def ostern(j):
    a, b, c = j % 19, j // 100, j % 100
    d, e = b // 4, b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = c // 4, c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7  # noqa: E741
    m = (a + 11 * h + 22 * l) // 451
    return datetime.date(j, (h + l - 7 * m + 114) // 31, (h + l - 7 * m + 114) % 31 + 1)


def _feiertage_boerse(j):
    """Handelsfreie Tage der Frankfurter Börse (wie scripts/kurs_luecken.py)."""
    o = ostern(j)
    return {datetime.date(j, 1, 1), o - datetime.timedelta(days=2), o + datetime.timedelta(days=1), datetime.date(j, 5, 1),
            datetime.date(j, 12, 24), datetime.date(j, 12, 25), datetime.date(j, 12, 26), datetime.date(j, 12, 31)}


def _feiertage_target(j):
    """TARGET-Feiertage (EZB-Referenzkurse, Bundesbank-Tagesreihen)."""
    o = ostern(j)
    return {datetime.date(j, 1, 1), o - datetime.timedelta(days=2), o + datetime.timedelta(days=1), datetime.date(j, 5, 1),
            datetime.date(j, 12, 25), datetime.date(j, 12, 26)}


def _feiertage_us(j):
    """US-Anleihemarkt (SIFMA, vereinfacht): Neujahr, MLK, Presidents, Memorial, Juneteenth, Independence, Labor, Columbus,
    Veterans, Thanksgiving, Weihnachten."""
    def nter(monat, wtag, n):
        d = datetime.date(j, monat, 1)
        while d.weekday() != wtag:
            d += datetime.timedelta(days=1)
        return d + datetime.timedelta(days=7 * (n - 1))
    memorial = datetime.date(j, 5, 31)
    while memorial.weekday() != 0:
        memorial -= datetime.timedelta(days=1)
    return {datetime.date(j, 1, 1), nter(1, 0, 3), nter(2, 0, 3), memorial, datetime.date(j, 6, 19), datetime.date(j, 7, 4),
            nter(9, 0, 1), nter(10, 0, 2), datetime.date(j, 11, 11), nter(11, 3, 4), datetime.date(j, 12, 25)}


FEIERTAGE = {"boerse": _feiertage_boerse, "target": _feiertage_target, "us": _feiertage_us}
KALENDER_NAME = {"boerse": "Börsentage", "target": "TARGET-Tage", "us": "US-Handelstage"}


def handelstag(d, kalender):
    return d.weekday() < 5 and d not in FEIERTAGE[kalender](d.year)


def handelstag_vor(heute, kalender, n=1):
    """n-ter Handelstag vor heute (n=1: der letzte)."""
    d = heute
    for _ in range(n):
        d -= datetime.timedelta(days=1)
        while not handelstag(d, kalender):
            d -= datetime.timedelta(days=1)
    return d


def handelstage_zwischen(von, bis, kalender):
    """Zahl der Handelstage d mit von < d <= bis."""
    n, d = 0, von
    while d < bis:
        d += datetime.timedelta(days=1)
        if handelstag(d, kalender):
            n += 1
    return n


def heute_berlin():
    try:
        from zoneinfo import ZoneInfo
        return datetime.datetime.now(ZoneInfo("Europe/Berlin")).date()
    except Exception:  # noqa: BLE001 – ohne Zeitzonendaten: Datum des Rechners
        return datetime.date.today()


def monat_minus(d, n):
    j, m = d.year, d.month - n
    while m <= 0:
        m += 12
        j -= 1
    return f"{j:04d}-{m:02d}"


def prozent(x):
    return f"{x * 100:.1f}".replace(".", ",") + " %"


def als_tag(wert):
    try:
        return datetime.date.fromisoformat(str(wert)[:10])
    except ValueError:
        return None


# ---------------------------------------------------------------- Prüfung
class Pruefung:
    def __init__(self, ordner, heute):
        self.ordner, self.heute = ordner, heute
        self.alarme, self.hinweise, self.zeilen = [], [], []
        self.geladen = {}

    def lade(self, name, pflicht=True):
        """JSON-Datei relativ zum Ordner; fehlt/unlesbar → Alarm (pflicht) und {}."""
        if name in self.geladen:
            return self.geladen[name]
        pfad = os.path.join(self.ordner, name)
        daten = {}
        if not os.path.isfile(pfad):
            if pflicht:
                self.alarme.append(f"{name}: Datei fehlt")
        else:
            try:
                with open(pfad, encoding="utf-8") as f:
                    daten = json.load(f)
            except (OSError, ValueError) as e:
                self.alarme.append(f"{name}: unlesbar ({e})")
                daten = {}
        self.geladen[name] = daten if isinstance(daten, dict) else {}
        return self.geladen[name]

    def tag(self, datei, reihe, stand, kalender, verzug, quelle):
        """Tagesreihe: Soll = verzug-ter Handelstag vor heute; Alarm ab ALARM_AB Handelstagen Rückstand."""
        soll = handelstag_vor(self.heute, kalender, verzug)
        ist = als_tag(stand) if stand else None
        if ist is None:
            self.alarme.append(f"{datei} → {reihe}: Stand fehlt oder unlesbar ({stand!r}) – {quelle}")
            return
        n = handelstage_zwischen(ist, soll, kalender)
        text = f"{datei} → {reihe}: {ist} (Soll {soll}, {quelle})"
        if n >= ALARM_AB:
            self.alarme.append(f"{datei} → {reihe} veraltet: Stand {ist}, {n} {KALENDER_NAME[kalender]} hinter dem Soll {soll} – {quelle}")
        elif n:
            self.zeilen.append(text + f" – {n} Handelstag Rückstand, noch kein Alarm")
        else:
            self.zeilen.append(text)

    def kalendertage(self, datei, reihe, stand, hoechstens, quelle):
        ist = als_tag(stand) if stand else None
        if ist is None:
            self.alarme.append(f"{datei} → {reihe}: Stand fehlt oder unlesbar ({stand!r}) – {quelle}")
            return
        alter = (self.heute - ist).days
        if alter > hoechstens:
            self.alarme.append(f"{datei} → {reihe} veraltet: Stand {ist}, {alter} Tage alt (höchstens {hoechstens}) – {quelle}")
        else:
            self.zeilen.append(f"{datei} → {reihe}: {ist} ({alter} Tage alt, höchstens {hoechstens}, {quelle})")

    def register(self, datei, reihe, stand):
        """ESMA-Register (wöchentlich, samstags): Soll ist der Samstag der Vorwoche."""
        letzter_sa = self.heute - datetime.timedelta(days=(self.heute.weekday() - 5) % 7)
        soll = letzter_sa - datetime.timedelta(days=7)
        ist = als_tag(stand) if stand else None
        if ist is None:
            self.alarme.append(f"{datei} → {reihe}: Stand fehlt oder unlesbar ({stand!r}) – ESMA-Register")
            return
        n = handelstage_zwischen(ist, soll, "target")
        if n >= ALARM_AB:
            self.alarme.append(f"{datei} → {reihe} veraltet: Stand {ist}, älter als die Gesamtdatei vom {soll} – ESMA-Register (wöchentlich)")
        else:
            self.zeilen.append(f"{datei} → {reihe}: {ist} (Soll ab {soll}, ESMA-Register)")

    def monat(self, datei, reihe, stand, zurueck, quelle):
        """Monatsreihe: Soll = Monat vor `zurueck` Monaten; Alarm, sobald der Stand älter ist."""
        soll = monat_minus(self.heute, zurueck)
        s = str(stand or "")[:7]
        if not re.fullmatch(r"\d{4}-\d{2}", s):
            self.alarme.append(f"{datei} → {reihe}: Stand fehlt oder unlesbar ({stand!r}) – {quelle}")
        elif s < soll:
            self.alarme.append(f"{datei} → {reihe} veraltet: Stand {s}, Soll ab {soll} – {quelle} (Monatswert)")
        else:
            self.zeilen.append(f"{datei} → {reihe}: {s} (Soll ab {soll}, {quelle})")

    def pflicht(self, ok, text_ok, text_alarm):
        if ok:
            self.zeilen.append(text_ok)
        else:
            self.alarme.append(text_alarm)


def pruefen(p, im_repo):
    J = p.lade
    # ---- Börse (Deutsche Börse, Tagesdateien): letzter Börsentag vor heute
    for name in ("anleihen-kurse.json", "kurse-auswahl.json", "etf-kurse.json"):
        p.tag(name, "stand", J(name).get("stand"), "boerse", 1, "Deutsche Börse")
    p.tag("suchindex.json", "kstand (Kurse der Suche)", J("suchindex.json").get("kstand"), "boerse", 1, "Deutsche Börse")
    jahre = sorted(glob.glob(os.path.join(p.ordner, "kurse", "[0-9][0-9][0-9][0-9]", "00.json")))
    if not jahre:
        p.alarme.append("kurse/<Jahr>/00.json: Kursverlauf fehlt")
    else:
        k00name = os.path.relpath(jahre[-1], p.ordner).replace(os.sep, "/")
        k00 = J(k00name)
        p.tag(k00name, "stand (Steckbrief)", k00.get("stand"), "boerse", 1, "Deutsche Börse")
        p.tag(k00name, "letzter Tag im Verlauf", (k00.get("tage") or [""])[-1], "boerse", 1, "Deutsche Börse")
    for name in ("top10-staatsanleihen-laender.json", "top10-staatsanleihen-laufzeit.json",
                 "top10-unternehmensanleihen-laender.json", "top10-unternehmensanleihen-laufzeit.json",
                 "top10-anleihen-kupon.json"):
        p.tag(name, "stand", J(name).get("stand"), "boerse", 1, "Kursverlauf")
    p.tag("top10-anleihen-kupon.json", "ezb.stand (EZB-Sicherheitenliste)",
          (J("top10-anleihen-kupon.json").get("ezb") or {}).get("stand"), "target", 1, "EZB")
    for name in ("etf-index.json", "etf-auswahl.json", "top10-anleihen-etfs.json"):
        p.tag(name, "stand (ETF-Liste der Börse)", J(name).get("stand"), "boerse", 1, "Deutsche Börse, ETF-Register")
    # ---- ESMA-Register (wöchentlich)
    p.register("anleihen-index.json", "stand", J("anleihen-index.json").get("stand"))
    p.register("anleihen/00.json", "stand (Stammdaten)", J("anleihen/00.json").get("stand"))
    p.register("suchindex.json", "stand (Register der Suche)", J("suchindex.json").get("stand"))
    p.register("anleihen-auswahl.json", "stand", J("anleihen-auswahl.json").get("stand"))
    # ---- EZB
    p.tag("suchindex.json", "ezb (Bonitätsstufe)", J("suchindex.json").get("ezb"), "target", 1, "EZB-Sicherheitenliste")
    p.tag("anleihen/00.json", "ezb (Bonitätsstufe)", J("anleihen/00.json").get("ezb"), "target", 1, "EZB-Sicherheitenliste")
    p.tag("wechselkurse.json", "stand", J("wechselkurse.json").get("stand"), "target", 1, "EZB-Referenzkurse")
    p.tag("ezb.json", "stand", J("ezb.json").get("stand"), "target", 1, "EZB Data Portal")
    # ---- Zwischenstände (nur im Repo, werden committet, nicht veröffentlicht): dort Pflicht, sonst nur, wenn vorhanden
    for name, kal, quelle in (("zinstermine/zinstermine.json", "boerse", "Instrumentenliste der Börse"),
                              ("bonitaet/ezb-stufen.json", "target", "EZB-Sicherheitenliste")):
        if im_repo or os.path.isfile(os.path.join(p.ordner, name)):
            p.tag(name, "stand", J(name).get("stand"), kal, 1, quelle)
        else:
            p.zeilen.append(f"{name} übersprungen (Bau-Ordner – die Datei liegt nur im Repo)")
    # ---- Staatsanleihen-Renditen
    laender = J("renditen.json").get("countries") or {}
    if not laender:
        p.alarme.append("renditen.json: keine Länder")

    def latest(reihen, k):
        return ((reihen.get(k) or {}).get("latest") or {}).get("date")
    p.tag("renditen.json", "us latest.date", latest(laender, "us"), "us", 1, "US-Treasury")
    p.tag("renditen.json", "de latest.date", latest(laender, "de"), "target", 1, "Bundesbank")
    p.tag("renditen.json", "jp latest.date", latest(laender, "jp"), "target", 3, "MoF Japan")
    p.kalendertage("renditen.json", "cn latest.date", latest(laender, "cn"), CHINA_TAGE, "ChinaBond")
    for land in ("in", "gb", "fr", "it"):
        p.monat("renditen.json", f"{land} latest.date", latest(laender, land), 3, "OECD")
    # ---- Unternehmensanleihen je Reihe
    reihen = J("unternehmen.json").get("series") or {}
    if not reihen:
        p.alarme.append("unternehmen.json: keine Reihen")
    for s in ("jp_aa", "jp_a"):
        p.tag("unternehmen.json", f"{s} latest.date", latest(reihen, s), "target", 3, "JSDA Japan")
    p.kalendertage("unternehmen.json", "cn_aaa latest.date", latest(reihen, "cn_aaa"), CHINA_TAGE, "ChinaBond")
    for s, quelle in (("us_hqm", "US-Treasury HQM"), ("au_a", "RBA"), ("au_bbb", "RBA")):
        p.monat("unternehmen.json", f"{s} latest.date", latest(reihen, s), 3, quelle)
    for s in sorted(set(reihen) - {"jp_aa", "jp_a", "cn_aaa", "us_hqm", "au_a", "au_bbb"}):
        p.hinweise.append(f"unternehmen.json → {s}: neue Reihe ohne Frische-Regel – in scripts/frische.py aufnehmen")
    # ---- Zinskurve, Realzins, Risikoaufschläge
    zk = J("zinskurve.json").get("stand") or {}
    p.tag("zinskurve.json", "stand.DE", zk.get("DE"), "target", 1, "Bundesbank")
    p.tag("zinskurve.json", "stand.US", zk.get("US"), "us", 2, "Fed H.15")
    rz = J("realzins.json")
    p.tag("realzins.json", "stand.zins (Bund 10 J.)", (rz.get("stand") or {}).get("zins"), "target", 1, "Bundesbank")
    p.tag("realzins.json", "stand.linker (Realrenditen)", (rz.get("stand") or {}).get("linker"), "target", 1, "Bundesbank")
    p.monat("realzins.json", "stand.vpi (Verbraucherpreise)", (rz.get("stand") or {}).get("vpi"), 2, "Bundesbank")
    linker = (rz.get("heute") or {}).get("linker") or []
    ohne = [str(x.get("isin")) for x in linker if not isinstance(x, dict) or x.get("breakeven") is None]
    p.pflicht(linker and not ohne, f"realzins.json → Breakeven: {len(linker)} von {len(linker)} Bundesanleihen",
              "realzins.json → Breakeven fehlt" + (f" bei {', '.join(ohne)}" if linker else " (keine inflationsindexierte Anleihe)")
              + " – Bund nominal aus der Bundesbank-Kurve fehlt (realzins.html zeigt „Bund nominal“ und „Breakeven“ leer)")
    ra = J("risikoaufschlaege.json")
    p.monat("risikoaufschlaege.json", "stand.laender", (ra.get("stand") or {}).get("laender"), 3, "OECD")
    p.monat("risikoaufschlaege.json", "stand.us", (ra.get("stand") or {}).get("us"), 3, "US-Treasury HQM")
    for e in (ra.get("laender") or {}).get("heute") or []:
        if isinstance(e, dict):
            p.monat("risikoaufschlaege.json", f"heute {e.get('code')}", e.get("monat"), 3, "OECD")
    # ---- Bundesbank: Langläufer und Bund-Kursverlauf
    bonds = J("langlaeufer.json").get("bonds") or {}
    if not bonds:
        p.alarme.append("langlaeufer.json: keine Anleihen")
    for b, c in sorted(bonds.items()):
        p.tag("langlaeufer.json", f"{b} latest.date", ((c or {}).get("latest") or {}).get("date"), "target", 1, "Bundesbank BBSSY")
    bund = sorted(glob.glob(os.path.join(p.ordner, "kurse", "bund", "*.json")))
    if not bund:
        p.alarme.append("kurse/bund: keine Kursverläufe der Bundeswertpapiere")
    else:
        letzte = ""
        for pfad in bund:
            t = (p.lade(os.path.relpath(pfad, p.ordner).replace(os.sep, "/")).get("t") or [""])
            letzte = max(letzte, str(t[-1]) if t else "")
        p.tag("kurse/bund", f"jüngster Kurs der {len(bund)} Bundeswertpapiere", letzte, "target", 1, "Bundesbank BBSSY")
    # ---- Aufschlag zu Bund: Anteil der Euro-Kurse vom letzten Kurstag
    ak, ix = J("anleihen-kurse.json"), J("anleihen-index.json")
    waehrung = {r[0]: r[3] for r in ix.get("rows") or [] if isinstance(r, list) and len(r) > 3}
    tage, stand = ak.get("tage") or [], ak.get("stand")
    n = mit = 0
    for isin, e in (ak.get("kurse") or {}).items():
        try:
            if waehrung.get(isin) != "EUR" or e[3] == "B" or e[1] is None or tage[e[2]] != stand:
                continue
            n += 1
            mit += e[7] is not None
        except (IndexError, TypeError):
            continue
    anteil = mit / n if n else 0.0
    p.pflicht(n and anteil >= AUFSCHLAG_ANTEIL_MIN,
              f"anleihen-kurse.json → Aufschlag zu Bund: {mit} von {n} Euro-Kursen ({prozent(anteil)})",
              f"anleihen-kurse.json → Aufschlag zu Bund nur bei {mit} von {n} Euro-Kursen mit Rendite ({prozent(anteil)}, mindestens "
              f"{prozent(AUFSCHLAG_ANTEIL_MIN)}) – Bund-Kurve fehlt oder ist zu alt (kurse/bund, Bundesbank BBSSY)")
    # ---- Datendateien ohne Regel
    for pfad in sorted(glob.glob(os.path.join(p.ordner, "*.json"))):
        name = os.path.basename(pfad)
        if name not in p.geladen and name not in OHNE_PRUEFUNG:
            p.hinweise.append(f"{name}: keine Frische-Regel – in scripts/frische.py aufnehmen")


def main():
    ap = argparse.ArgumentParser(description="Frische der Datendateien (Alarm im Datenlauf)")
    ap.add_argument("ordner", nargs="?", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
    ap.add_argument("--heute", help="Prüfdatum JJJJ-MM-TT (Standard: heute in Berlin)")
    a = ap.parse_args()
    heute = datetime.date.fromisoformat(a.heute) if a.heute else heute_berlin()
    ordner = os.path.abspath(a.ordner)
    p = Pruefung(ordner, heute)
    pruefen(p, os.path.isdir(os.path.join(ordner, "scripts")))
    print(f"Frische-Prüfung {heute} in {ordner}: {len(p.zeilen)} Werte in Ordnung, {len(p.alarme)} Alarm(e)")
    for z in p.zeilen:
        print("  " + z)
    for h in p.hinweise:
        print(f"::warning::{h}")
    for x in p.alarme:
        print(f"::error::{x}")
    if p.alarme:
        return 1
    print("Alles frisch und gültig. ✓")
    return 0


if __name__ == "__main__":
    sys.exit(main())
