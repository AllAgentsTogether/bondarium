#!/usr/bin/env python3
"""Baut etf-index.json – das Register aller Anleihen-ETFs, die an Xetra gehandelt werden – und daraus
top10-anleihen-etfs.json, die zehn meistgehandelten je Kategorie für anleihen-etf.html (seit 30.09.2026).

Läuft im 10-Uhr-Lauf VOR update_kurse.py: So bekommt ein neu gelisteter ETF am selben Tag einen Kurs.
Strategie und Prüfung der Quellen: docs/ETF-DATENBANK.md.
Nichts wird von Hand gepflegt (Nutzerentscheid 30.09.2026): keine handverlesenen ETF-Listen, keine Korrekturliste,
keine Kennzahlen von Anbieterseiten. Alles hier stammt aus den drei Quellen oder ist daraus nach festen Regeln abgeleitet.

Quellen (alle frei abrufbar, ohne Anmeldung):
  * Deutsche Börse, „List of tradable ETFs & ETPs“ (Excel, ~0,5 MB, börsentäglich neu, Kopfzeile „As of TT/MM/JJJJ“):
    Name, ISIN, Anbieter, Xetra-Kürzel, laufende Kosten, Ertragsverwendung, Nachbildung, Fonds- und Handelswährung, Index.
    Der Link steht auf der Seite …/etf-etp-statistics/etp-list und wird bei jedem Lauf von dort gelesen.
  * Deutsche Börse, Monatsstatistik „ETF & ETP Statistic“ (Excel je Monat, ~1,6 MB, erscheint Anfang des Folgemonats):
    Blatt „New Listings“ mit der Anlageklasse („Asset Class“) jedes Neuzugangs – seit 07/2016; Blatt „Exchange Traded
    Funds“ mit Umsatz im Xetra-Orderbuch, Fondsvermögen der Anteilsklasse und Xetra Liquidity Measure (XLM) je ETF.
  * ESMA FIRDS, wöchentliche Gesamtdatei der Fonds FULINS_C (~4 MB): erster Handelstag an Xetra/Frankfurt und der
    CFI-Code – nur als Gegenprobe (siehe unten).
Nutzungsrechte an Liste und Monatsstatistik sind NICHT geklärt (Stand 30.09.2026, siehe docs/ETF-DATENBANK.md, Risiken).

Was ein Anleihen-ETF ist (Feld klasse):
  B  Die Börse sagt es: Anlageklasse „Fixed Income“ (früher auch „Government Bonds“/„Corporate Bonds“) in der
     Neuzugangs-Liste des Monats, in dem der ETF gelistet wurde. Gilt für jeden ETF seit 07/2016.
  S  Für ältere ETFs und für Neuzugänge, deren Monatsstatistik noch nicht erschienen ist: Stichwörter in Name und
     Index (stichwort()). Gemessen an der Einstufung der Börse finden sie 99,5 % der Anleihen-ETFs ohne Fehltreffer.
Der CFI-Code entscheidet NICHT mit: Er erkennt nur 62 % der Anleihen-ETFs (viele Luxemburger Fonds sind „gemischt/
sonstige“ gemeldet) und ist vereinzelt falsch. Widerspricht er, steht das in pruef („cfi“). Die „pruefliste“ im Kopf
der Datei nennt die Fälle, in denen nur Stichwörter und CFI-Code gegeneinander stehen – zum Ansehen. Stimmt eine
Einstufung nicht, wird die Regel (stichwort(), kategorie() …) verbessert, nicht der einzelne ETF von Hand gesetzt.

Aus Name und Index abgeleitet (Näherung, in „abgeleitet“ benannt):
  kategorie     Geldmarkt (Tagesgeldsätze, Cash) · Staat · Unternehmen · Hochzins · Schwellenländer · Breit gestreut ·
                Inflationsgeschützt · Pfandbriefe · Sonstige (Wandel- und Nachranganleihen, CoCo, CLO, MBS,
                gehebelte/inverse Strategien, Unklares)
  markt         Währung bzw. Raum der Anleihen: EUR, USD, GBP, JPY, CNY, CHF, AUD, INR, Welt, EM oder ""
  laufzeit      [von, bis] in Jahren, nur wenn es ausdrücklich dasteht („1-3“, „10+“, „Ultrashort“/„Money Market“ → 0–1);
                Geldmarkt [0, 0]
  endjahr       Endjahr eines Laufzeit-ETFs (iBonds, Target Maturity, BulletShares …)
  abgesichert   Währung, gegen die die Anteilsklasse abgesichert ist ("" = keine, "?" = Währung nicht erkennbar) – aus
                dem Namen; schweigt er, gilt eine Euro-Klasse eines ETFs auf Dollar-, Pfund- oder Yen-Anleihen als in
                Euro abgesichert (siehe abgesichert())
  gruppe        Tabelle auf anleihen-etf.html (siehe gruppe()) oder "" – jeder ETF steht höchstens in einer

Ausgabe etf-index.json (ein ETF je Zeile, damit Git-Diffs klein bleiben):
  rows[i] = [isin, name, anbieter, kuerzel, aktiv, kosten, ausschuettend, nachbildung, fondswaehrung, handelswaehrung,
             index, klasse, kategorie, markt, laufzeit, endjahr, abgesichert, gruppe, erster_handelstag, vermoegen,
             umsatz12, xlm, pruef]
    aktiv: 1 = aktiv gemanagt (kein Index); kosten: laufende Kosten in % p. a. laut Börsenliste;
    ausschuettend: 1 = ausschüttend, 0 = thesaurierend; nachbildung: "voll" · "optimiert" · "Swap" · "hybrid" · "";
    handelswaehrung: EUR, wenn es an Xetra eine Euro-Handelszeile gibt, sonst die Währung der einzigen Zeile –
      update_kurse.py nimmt nur Kurse in dieser Währung (einige ETFs werden in EUR UND USD gehandelt);
    erster_handelstag: frühester Handelstag an Xetra/Frankfurt laut FIRDS, sonst Listing-Datum der Börse, sonst "";
    vermoegen: Fondsvermögen der ANTEILSKLASSE in Mio. € (Monatsstatistik, Monat „statistik“) – nicht des ganzen Fonds;
    umsatz12: Umsatz im Xetra-Orderbuch in Mio. € über die Monate „umsatz.von“ bis „umsatz.bis“ (höchstens zwölf;
      bei jüngeren ETFs seit dem Listing); xlm: Handelskosten für Kauf und sofortigen Verkauf von 100.000 € in Basispunkten;
    pruef: {} oder Befunde – „ertrag“: CFI-Code meldet die andere Ertragsverwendung; „cfi“: CFI-Code nennt eine
      andere Anlageklasse.
  Quelldaten bleiben unverändert; Widersprüche werden gezeigt, nicht korrigiert (wie bei den Anleihen).

Ausgabe top10-anleihen-etfs.json (klein, wird in anleihen-etf.html eingebettet; update_kurse.py nimmt die ISINs in
kurse-auswahl.json auf): {"stand", "statistik", "umsatz": {"von", "bis"}, "anzahl", "gruppen": {<Anker>: {"anzahl":
ETFs der Kategorie im Register, "etfs": [die zehn mit dem höchsten Umsatz im Xetra-Orderbuch, je ETF ein Objekt mit
den Feldern des Registers und „kurzname“ – dem Namen ohne „UCITS ETF“, Anteilsklasse und Absicherung]}}}.

Ausgabe etf-auswahl.json (klein, wird eingebettet): dieselben Objekte für die ETFs, die eine Seite mit
data-etf="<ISIN>" nennt (die Beispiel-Karten im Guide) – {"stand", "statistik", "etfs": {ISIN: {…, "top10": Anker der
Tabelle, in der der ETF unter den zehn steht, sonst ""}}}. Die Seiten füllen ihre Karten daraus; von Hand steht dort
nur noch die ISIN.

Zwischenstände im Ordner etf/ (werden committet, aber nicht auf den Webserver kopiert):
  etf/klassen.json      {ISIN: [Anlageklasse, Listing-Datum]} aus allen „New Listings“ seit 07/2016, dazu die
                        verarbeiteten Monate. Wächst jeden Monat um die Neuzugänge.
  etf/monate.json       Umsatz der letzten zwölf Monate, Fondsvermögen und XLM des letzten Monats – für ALLE ETFs der
                        Statistik (nicht nur Anleihen), damit eine spätere Umstufung keine Lücke hat.
  etf/firds.json        {ISIN: [CFI-Code, erster Handelstag]} für die ETFs der Börsenliste; wöchentlich.

Drossel: Die Börsenliste wird bei jedem Lauf geholt. Die Statistik-Seite nur, solange der Vormonat noch fehlt.
FIRDS nur, wenn der Stand sieben Tage alt ist. Fällt Statistik oder FIRDS aus, wird der Index mit dem letzten
Zwischenstand gebaut (Rückgabe 1 – der Schritt wird rot, der Lauf geht weiter). Fällt die Börsenliste aus oder
schrumpft das Register auf unter 70 %, bleibt etf-index.json unverändert.

Aufruf:
  python scripts/update_etf_index.py                 normaler Lauf
  python scripts/update_etf_index.py --force         Statistik-Seite und FIRDS ohne Drossel abfragen
  FIXTURE_DIR=<Ordner> python scripts/update_etf_index.py
      ohne Netz: liest Master_DataSheet_Download.xls, *Statisti*.xlsx und FULINS_C_*.zip aus dem Ordner (Tests, Erstaufbau)
"""

import collections
import datetime
import io
import json
import os
import re
import sys
import time
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

from _common import get_with_retry, log_err, now_iso, today_iso, write_atomic

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "etf-index.json"
OUT_TOP10 = ROOT / "top10-anleihen-etfs.json"
OUT_AUSWAHL = ROOT / "etf-auswahl.json"
ZUSTAND = ROOT / "etf"
KLASSEN, MONATE, FIRDS = (ZUSTAND / n for n in ("klassen.json", "monate.json", "firds.json"))

BASIS = "https://www.cashmarket.deutsche-boerse.com"
SEITE_LISTE = BASIS + "/cash-en/Data-Tech/statistics/etf-etp-statistics/etp-list"
SEITE_STATISTIK = BASIS + "/cash-en/Data-Tech/statistics/etf-etp-statistics"
FILES_API = ("https://registers.esma.europa.eu/solr/esma_registers_firds_files/select?"
             "q=*&fq=publication_date:%5B{von}T00:00:00Z+TO+{bis}T23:59:59Z%5D&wt=json&start=0&rows=500")
UA = {"User-Agent": "bondarium.de ETF-Register (Datenaufbereitung)", "Accept": "*/*"}
NS = "{urn:iso:std:iso:20022:tech:xsd:auth.017.001.02}"

ETF_TYPEN = {"ETF", "Active ETF"}                                            # nicht: ETC, ETN
ANLEIHEN_KLASSEN = {"fixed income", "government bonds", "corporate bonds"}  # „Asset Class“ der Börse
XETRA_FRANKFURT = {"XETR", "XETA", "XETB", "XETS", "XFRA", "FRAA", "FRAB", "FRAS"}
KLASSEN_AB = "2016-07"    # erste Monatsstatistik mit „New Listings“ und Anlageklasse
MONATE_N = 12             # Umsatz über so viele Monate
MIN_ZEILEN = 2000         # Börsenliste mit weniger Zeilen gilt als defekt (30.09.2026: 3.718)
MIN_ANTEIL = 0.7          # Register unter 70 % des bisherigen → Quelle defekt, nichts schreiben
PAUSE = 1.0               # Sekunden zwischen zwei Abrufen bei der Börse
ISIN_RE = re.compile(r"[A-Z]{2}[A-Z0-9]{9}[0-9]")

FELDER = ["isin", "name", "anbieter", "kuerzel", "aktiv", "kosten", "ausschuettend", "nachbildung", "fondswaehrung",
          "handelswaehrung", "index", "klasse", "kategorie", "markt", "laufzeit", "endjahr", "abgesichert", "gruppe",
          "erster_handelstag", "vermoegen", "umsatz12", "xlm", "pruef"]
ABGELEITET = ["kategorie", "markt", "laufzeit", "endjahr", "abgesichert", "gruppe"]
# Tabellen von anleihen-etf.html in der Reihenfolge der Seite
GRUPPEN = ["kurze-laufzeiten", "euro-staatsanleihen", "breit-gestreut", "unternehmensanleihen", "staatsanleihen-weltweit",
           "hochzinsanleihen", "schwellenlaender"]
TOP_N = 10
KURZ_JAHRE = 3            # „Kurze Laufzeiten“: Laufzeitband bis höchstens drei Jahre …
KURZ_ENDE = 2             # … oder Laufzeit-ETF, der spätestens im übernächsten Kalenderjahr endet
KATEGORIEN = ["Geldmarkt", "Staat", "Unternehmen", "Hochzins", "Schwellenländer", "Breit gestreut", "Inflationsgeschützt",
              "Pfandbriefe", "Sonstige"]
NACHBILDUNG = {"full replication": "voll", "optimised": "optimiert", "optimized": "optimiert", "sample": "optimiert",
               "swap-based": "Swap", "swap based": "Swap", "hybrid": "hybrid"}


# ---------------------------------------------------------------- Excel (xlsx) lesen – nur Standardbibliothek
X = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
XR = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"


def _spalte(ref: str) -> int:
    n = 0
    for ch in ref:
        if not ch.isalpha():
            break
        n = n * 26 + ord(ch.upper()) - 64
    return n - 1


def _wert(c, texte: list):
    t, v = c.get("t"), c.find(X + "v")
    if t == "inlineStr":
        return "".join(x.text or "" for x in c.iter(X + "t"))
    if v is None or v.text is None:
        return None
    if t == "s":
        return texte[int(v.text)]
    if t in ("str", "e"):
        return v.text
    if t == "b":
        return v.text == "1"
    try:
        return float(v.text)
    except ValueError:
        return v.text


def xlsx_blaetter(roh: bytes, will=lambda name: True, max_zeilen: int = 60000) -> dict:
    """{Blattname: [[Zelle …] …]} der gewünschten Blätter einer xlsx-Datei. Zahlen als float, Texte als str, leer None.
    Bricht ein Blatt nach 500 leeren Zeilen in Folge ab (eine Monatsdatei von 2016 hat ein Blatt mit 1 Mio. Zeilen)."""
    z = zipfile.ZipFile(io.BytesIO(roh))
    texte = []
    if "xl/sharedStrings.xml" in z.namelist():
        for _, el in ET.iterparse(z.open("xl/sharedStrings.xml")):
            if el.tag == X + "si":
                teile = [el.find(X + "t")] + [r.find(X + "t") for r in el.findall(X + "r")]
                texte.append("".join(t.text or "" for t in teile if t is not None))
                el.clear()
    rels = {r.get("Id"): r.get("Target") for r in ET.parse(z.open("xl/_rels/workbook.xml.rels")).getroot()}
    out = {}
    for s in ET.parse(z.open("xl/workbook.xml")).getroot().iter(X + "sheet"):
        name = s.get("name") or ""
        if not will(name):
            continue
        ziel = rels.get(s.get(XR + "id"), "")
        ziel = ziel.lstrip("/") if ziel.startswith("/") else "xl/" + ziel
        zeilen, leer = [], 0
        for _, el in ET.iterparse(z.open(ziel)):
            if el.tag != X + "row":
                continue
            zellen = []
            for c in el.iter(X + "c"):
                i = _spalte(c.get("r")) if c.get("r") else len(zellen)
                while len(zellen) < i:
                    zellen.append(None)
                zellen.append(_wert(c, texte))
            el.clear()
            leer = 0 if any(x not in (None, "") for x in zellen) else leer + 1
            zeilen.append(zellen)
            if leer >= 500 or len(zeilen) >= max_zeilen:
                break
        out[name] = zeilen[:len(zeilen) - leer] if leer else zeilen
    return out


# ---------------------------------------------------------------- Texte aufräumen, Einstufung nach Stichwörtern
UNSICHTBAR = re.compile("[​‌‍﻿­]")   # die Börsenliste enthält vereinzelt Zeichen ohne Breite


def sauber(s) -> str:
    return re.sub(r"\s+", " ", UNSICHTBAR.sub("", str(s or "").replace(" ", " "))).strip()


POS = re.compile(
    r"\bbonds?\b|\bgovt\b|\bgov\b|\bgovernment\b|\btreasur(?:y|ies)\b|\bgilts?\b|\bbunds?\b|\bcorp(?:orate)?s?\b|\baggregate\b"
    r"|\bcredits?\b|high[ -]yield|\bhy\b|fallen angels?|floating rate|\bfrn\b|\bibonds\b|inflation|\btips\b|linkers?\b"
    r"|pfandbrief|\bcovered bond|\bsovereigns?\b|rentenindex|\brenten\b|\banleihen?\b|staatsanleihe|fixed income"
    r"|ultra[- ]?short|money market|\bovernight\b|€str|\bestr\b|eur str\b|\beonia\b|\bsonia\b|\bsofr\b|fed funds|\bcash\b"
    r"|liquidity fund|t-bills?\b|treasury bills?|\bmbs\b|mortgage|\bconvertibles?\b|\bcoco\b|\bat1\b|\bclos?\b|\bembi\b"
    r"|gbi-em|\bcembi\b|eurogov|\biboxx\b|bulletshares|target maturity|fixed maturity|short duration|low duration"
    r"|short maturity|\bdebt\b|\bschatz\b|\bbobl\b|\bbuxl\b|\bbtps?\b|\bbonos\b", re.I)
# Gegenanzeigen: Aktien-, Rohstoff- und Optionsstrategien, die eines der Wörter oben im Namen tragen
# („High Yield Dividend Aristocrats“, „Covered Call“, „Constant Maturity Commodity“)
NEG = re.compile(r"dividend|covered call|buy-?write|\bequit(?:y|ies)\b|commodit|\bcmci\b|\bgold\b|precious metals|\bshares\b"
                 r"|autocallable|target income", re.I)
# Aktienindex im PRODUKTNAMEN: dann zählt ein Anleihen-Index in der Spalte „Benchmark“ nicht (Fehler der Börsenliste,
# z. B. „Xtrackers MSCI World Utilities“ mit dem Index „ICE BofA Global Corporate Index“)
AKTIENNAME = re.compile(r"msci (?:world|acwi|usa|europe|emu|japan|pacific|em\b|emerging|china|india)|stoxx|s&p ?500|nasdaq"
                        r"|\bdax\b|russell|nikkei|topix|semiconductor", re.I)


def stichwort(name: str, index: str) -> bool:
    """True, wenn Name oder Index nach einem Anleihen-ETF klingen und nichts dagegen spricht."""
    if NEG.search(name) or NEG.search(index):
        return False
    if POS.search(name):
        return True
    return bool(POS.search(index)) and not AKTIENNAME.search(name)


# ---------------------------------------------------------------- Ableitungen aus Name und Index (Näherung)
WAEHRUNGEN = r"EUR|USD|GBP|CHF|SEK|MXN|AUD|SGD|JPY|CAD|NOK"
ZINS_HEDGE = re.compile(r"interest rate hedged|duration hedged|rate hedged", re.I)   # Zins-, keine Währungsabsicherung
HEDGE = [re.compile(r"\b(" + WAEHRUNGEN + r")[\s-]*\(?(?:hedged|hdg|hgd)\)?", re.I),          # „EUR Hedged“, „EUR Hdg“, „EUR-Hedged“
         re.compile(r"\b(" + WAEHRUNGEN + r")\s?[-(]\s?H\)?(?![A-Za-z])"),                    # „EUR (H)“, „EUR(H)“, „EUR-H“
         re.compile(r"\((" + WAEHRUNGEN + r") hedged\)", re.I),
         re.compile(r"\b(?:hedged|hdg|hgd)\s+(?:to\s+)?\(?(" + WAEHRUNGEN + r")\b", re.I),    # „Hedged EUR“, „Hedged to EUR“
         re.compile(r"\bh(" + WAEHRUNGEN + r")\b"),                                           # „hEUR“ (UBS)
         re.compile(r"\bETF\s+H\s+(" + WAEHRUNGEN + r")\b"),                                  # „UCITS ETF H EUR“ (BNP Paribas)
         re.compile(r"\b(" + WAEHRUNGEN + r")\s+H\b"),                                        # „ACC EUR H“
         re.compile(r"\b(" + WAEHRUNGEN + r")\s+Pf(?:Hdg|Hgd)\b", re.I),                       # „EUR PfHgd“ (Invesco: Portfolio Hedged)
         re.compile(r"\b(" + WAEHRUNGEN + r")\s+(?:Acc|Dist|Inc)\.?\s+Hedged\b", re.I)]        # „EUR Acc Hedged“ (L&G)
HEDGE_WORT = re.compile(r"(?<!un)hedged|(?<!un)hdg\b|hgd\b", re.I)   # auch „PfHdg“/„PfHgd“ (Invesco), nicht „Unhedged“


def absicherung(name: str) -> str:
    n = ZINS_HEDGE.sub("", name)
    for rx in HEDGE:
        m = rx.search(n)
        if m:
            return m.group(1).upper()
    return "?" if HEDGE_WORT.search(n) else ""


def kern(name: str) -> str:
    """Beschreibender Teil des Namens: vor „UCITS ETF“ und ohne Absicherungs-Zusatz. Dahinter steht die Anteilsklasse
    („… UCITS ETF USD (Dist)“) – deren Währung sagt nichts über die Anleihen im Fonds."""
    m = re.search(r"\bUCITS\b", name)
    k = name[:m.start()] if m else re.sub(r"\bETF\b.*$", "", name)
    k = ZINS_HEDGE.sub("", k)
    for rx in HEDGE:
        k = rx.sub(" ", k)
    return re.sub(r"\s+", " ", HEDGE_WORT.sub(" ", k)).strip(" -–")


K_GELD = re.compile(r"\bovernight\b|€str|\bestr\b|eur str\b|\beonia\b|\bsonia\b|\bsofr\b|fed funds|\bfedl\b|\bcash\b"
                    r"|liquidity fund", re.I)
K_GELDMARKT = re.compile(r"money market", re.I)   # Geldmarkt nur ohne Staats-Stichwort (Deka „EUROGOV Germany Money Market“ = Bundespapiere bis 1 Jahr)
K_SONST = re.compile(r"\binverse\b|\(-?\d+x\)|\bleveraged?\b|steepen|flatten|\bfactor fx\b|convertible|\bcoco\b|\bat1\b"
                     r"|contingent|\bclos?\b|mortgage|\bmbs\b|preferred|autocall|\bhybrids?\b|subordinated|nachrang"
                     r"|perpetual|capital securities", re.I)
K_EM = re.compile(r"emerging|\bem\b|\bembi\b|gbi-em|\bcembi\b|\bchina\b|chinese|\bindia\b|\basia\b|\bafrican?\b|frontier"
                  r"|saudi|\bgulf\b|\bgcc\b|latin america|\bbrazil|\bmexic|indonesia|\bturk", re.I)
K_REIHE = [(K_EM, "Schwellenländer"),
           (re.compile(r"high[ -]yield|\bhy\b|fallen angels?|\bjunk\b", re.I), "Hochzins"),
           (re.compile(r"inflation|\btips\b|linkers?\b|breakeven", re.I), "Inflationsgeschützt"),
           (re.compile(r"\bcovered\b|pfandbrief", re.I), "Pfandbriefe"),
           (re.compile(r"\baggregate\b|\bagg\b|\buniversal\b|total bond|multi-sector|core plus", re.I), "Breit gestreut"),
           (re.compile(r"\bgovt\b|\bgov\b|\bgovernment\b|treasur(?:y|ies)|\bgilts?\b|\bbunds?\b|\bsovereigns?\b|staatsanleihe"
                       r"|eurogov|\bbtps?\b|\bbonos\b|\bschatz\b|t-bills?\b|\bbot\b", re.I), "Staat"),
           (re.compile(r"\bcorp(?:orate)?s?\b|\bcorporates\b|\bcredits?\b|financials|investment grade|\big\b", re.I), "Unternehmen")]


K_STAAT = K_REIHE[-2][0]


def kategorie(name: str, index: str) -> str:
    teile = (kern(name), index)   # erst der Name, dann der Index
    for t in teile:
        if K_GELD.search(t):
            return "Geldmarkt"
    if any(K_GELDMARKT.search(t) for t in teile) and not any(K_STAAT.search(t) for t in teile):
        return "Geldmarkt"
    for t in teile:
        if K_SONST.search(t):
            return "Sonstige"
    for t in teile:
        for rx, kat in K_REIHE:
            if rx.search(t):
                return kat
    return "Sonstige"


M_WELT = re.compile(r"\bglobal\b|\bworld\b|international|\bintl\b|\bg7\b", re.I)
# ausdrückliche Währungs-/Raumangabe – geht vor …
M_FEST = [(re.compile(r"\beur\b|\beuro\b|€|eurozone|euro area|\bemu\b", re.I), "EUR"),
          (re.compile(r"\busd\b|\$|\bus\b|u\.s\.|\busa\b", re.I), "USD"),
          (re.compile(r"\bgbp\b|sterling|£|\buk\b", re.I), "GBP")]
# … Hinweisen aus der Gattung („Treasury“, „Gilt“, „Bund“)
M_WEICH = [(re.compile(r"german|\bbunds?\b|eurogov|\bitaly\b|\bspain\b|\bfrance\b|pfandbrief|eb\.rexx|\bestr\b|\beuropean?\b", re.I), "EUR"),
           (re.compile(r"treasur(?:y|ies)|\btips\b|fed funds|\bfedl\b|\bsofr\b", re.I), "USD"),
           (re.compile(r"\bgilts?\b|\bsonia\b", re.I), "GBP")]
M_REST = [(re.compile(r"\bjapan", re.I), "JPY"), (re.compile(r"\bchin(?:a|ese)\b", re.I), "CNY"),
          (re.compile(r"\bswiss\b|\bsbi\b|\bchf\b", re.I), "CHF"), (re.compile(r"australia", re.I), "AUD"),
          (re.compile(r"\bindia", re.I), "INR")]


def markt(name: str, index: str) -> str:
    for t in (kern(name), index):
        if M_WELT.search(t):
            return "Welt"
        fest = [w for rx, w in M_FEST if rx.search(t)]
        if len(fest) == 1:
            return fest[0]
        if fest:
            continue            # widersprüchlich („Euro … USD“): nächste Quelle fragen
        for rx, w in M_REST:    # ein Land geht vor der Gattung: „Japan Treasury“ ist kein US-Papier
            if rx.search(t):
                return w
        weich = [w for rx, w in M_WEICH if rx.search(t)]
        if len(weich) == 1:
            return weich[0]
        if not weich and K_EM.search(t):
            return "EM"
    return ""


L_SPANNE = re.compile(r"(?<![\d.])(\d{1,2}(?:\.\d)?)\s?[-–]\s?(\d{1,2}(?:\.\d)?)(?![\d.])\s?(months?|monate|m\b)?", re.I)
L_PLUS = re.compile(r"(?<![\d.\w])(\d{1,2}(?:\.\d)?)\s?\+(?!\d)")
L_MONATE = re.compile(r"(?<![\d.-])(\d{1,2})\s?-?\s?months?\b", re.I)
L_ULTRA = re.compile(r"ultra[- ]?short|money market", re.I)
L_HEBEL = re.compile(r"\(-?\d+x\)")


def _zahl(x: float):
    return int(x) if float(x).is_integer() else x


def laufzeit(name: str, index: str, kat: str):
    k = kern(name)
    if kat == "Geldmarkt" and not L_SPANNE.search(k) and not L_MONATE.search(k):
        return [0, 0]
    for t in (k, index):
        t = L_HEBEL.sub(" ", t)
        m = L_SPANNE.search(t)
        if m:
            a, b = float(m.group(1)), float(m.group(2))
            if m.group(3):
                a, b = round(a / 12, 2), round(b / 12, 2)
            if a < b <= 60:
                return [_zahl(a), _zahl(b)]
        m = L_PLUS.search(t)
        if m and float(m.group(1)) <= 40:
            return [_zahl(float(m.group(1))), None]
        m = L_MONATE.search(t)
        if m:
            return [0, round(int(m.group(1)) / 12, 2)]
        if L_ULTRA.search(t):
            return [0, 1]
    return None


E_WORT = re.compile(r"\bibonds\b|bulletshares|target maturity|fixed maturity|\bmaturity\b|\bterm\b", re.I)
E_JAHR = re.compile(r"(?<!\d)(20[2-5]\d)(?!\d)")


def endjahr(name: str, index: str, jahr_heute: int):
    k = kern(name)
    if not (E_WORT.search(k) or E_WORT.search(index)):
        return None
    for t in (k, index):
        for m in E_JAHR.finditer(t):
            if jahr_heute - 1 <= int(m.group(1)) <= jahr_heute + 30:
                return int(m.group(1))
    return None


# ---------------------------------------------------------------- Abrufe
def lade(pfad: Path, leer):
    try:
        return json.loads(pfad.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return leer


def _fixture():
    f = os.environ.get("FIXTURE_DIR")
    return Path(f) if f else None


def boersenliste() -> bytes:
    """Excel-Datei „List of tradable ETFs & ETPs“ (Endung .xls, Inhalt xlsx). Der Link enthält eine Prüfsumme und
    ändert sich mit jeder Fassung – deshalb jedes Mal von der Seite lesen."""
    fix = _fixture()
    if fix:
        return (fix / "Master_DataSheet_Download.xls").read_bytes()
    html = get_with_retry(SEITE_LISTE, headers=UA, timeout=60).decode("utf-8", "replace")
    m = re.search(r'href="' + PRAEFIX + r'(/resource/blob/[^"]+/Master_DataSheet[^"]*\.xlsx?)"', html)
    if not m:
        raise ValueError(f"Link zur ETF-Liste auf der Seite der Börse nicht gefunden ({seite_kurz(html)})")
    time.sleep(PAUSE)
    return get_with_retry(BASIS + m.group(1), headers=UA, timeout=120)


# Die Börse schreibt ihre Links je nach Server mal relativ („/resource/…“), mal absolut („https://www.cashmarket…/resource/…“;
# 08.10.2026: 8 von 9 Abrufen) – beide Formen zählen, die Gruppe bleibt der Pfad (Technik-Test 08.10.2026, T-08).
PRAEFIX = r'(?:https?://(?:www\.)?cashmarket\.deutsche-boerse\.com)?'
MONATSLINK = re.compile(r'href="' + PRAEFIX + r'(/resource/blob/[^"]+/(\d{4})(\d{2})\d{2}[-_][^"/]*Statisti[^"/]*\.xlsx)"')


def seite_kurz(html: str) -> str:
    """Länge und <title> einer Börsen-Seite für die Fehlermeldung (zeigt, ob eine Sperr- oder Umleitungsseite kam)."""
    t = re.search(r"<title[^>]*>(.*?)</title>", html, re.S | re.I)
    return f"{len(html)} Zeichen, Titel „{' '.join(t.group(1).split())[:120] if t else '–'}“"


def statistik_links(ab: str) -> dict:
    """{"2026-08": Link} der Monatsdateien, mindestens zurück bis zum Monat `ab`. Die Seite zeigt die zehn neuesten;
    ältere kommen über die Suche der Seite (…/<Nummer>!search?hitsPerPage=50&pageNum=N)."""
    fix = _fixture()
    if fix:
        out = {}
        for p in sorted(fix.glob("*Statisti*.xlsx")):
            m = re.match(r"(\d{4})(\d{2})\d{2}", p.name)
            if m:
                out[f"{m.group(1)}-{m.group(2)}"] = str(p)
        return out
    html = get_with_retry(SEITE_STATISTIK, headers=UA, timeout=60).decode("utf-8", "replace")
    out = {f"{j}-{mo}": BASIS + href for href, j, mo in MONATSLINK.findall(html)}
    if not out:
        log_err(f"ETF-Register: keine Monatsstatistik auf der Seite der Börse gefunden ({seite_kurz(html)})")
    suche = re.search(r'data-js-search-filter-link="' + PRAEFIX + r'([^"?]+!search)', html)
    seite = 0
    while suche and (not out or min(out) > ab) and seite < 12:
        time.sleep(PAUSE)
        mehr = get_with_retry(f"{BASIS}{suche.group(1)}?hitsPerPage=50&pageNum={seite}", headers=UA, timeout=60).decode("utf-8", "replace")
        neu = {f"{j}-{mo}": BASIS + href for href, j, mo in MONATSLINK.findall(mehr)}
        if not set(neu) - set(out) and seite > 0:
            break
        out.update(neu)
        seite += 1
    return out


def monatsdatei(link: str) -> bytes:
    if _fixture():
        return Path(link).read_bytes()
    time.sleep(PAUSE)
    return get_with_retry(link, headers=UA, timeout=180)


def firds_neueste(bis: datetime.date):
    """(Datum, Link oder Pfad) der neuesten Fonds-Gesamtdatei FULINS_C der letzten 14 Tage; None, wenn keine gelistet ist."""
    fix = _fixture()
    if fix:
        dateien = sorted(fix.glob("FULINS_C_*.zip"))
        if not dateien:
            return None
        d = re.search(r"FULINS_C_(\d{4})(\d{2})(\d{2})", dateien[-1].name)
        return "-".join(d.groups()), str(dateien[-1])
    url = FILES_API.format(von=(bis - datetime.timedelta(days=14)).isoformat(), bis=bis.isoformat())
    docs = json.loads(get_with_retry(url, headers=UA, timeout=60))["response"]["docs"]
    serien = collections.defaultdict(dict)
    for d in docs:
        m = re.fullmatch(r"FULINS_C_(\d{8})_(\d+)of(\d+)\.zip", d.get("file_name", ""))
        if m:
            serien[(m.group(1), int(m.group(3)))][int(m.group(2))] = d["download_link"]
    for (datum, teile), links in sorted(serien.items(), reverse=True):
        if len(links) == teile == 1:     # Fonds-Datei: bisher immer ein Teil
            return f"{datum[:4]}-{datum[4:6]}-{datum[6:]}", links[1]
    return None


# ---------------------------------------------------------------- Quellen lesen
def lies_liste(roh: bytes):
    """(Stand JJJJ-MM-TT, [Zeile als dict mit den Spaltennamen der Börse]) – eine Zeile je Handelszeile (ISIN × Währung)."""
    for zeilen in xlsx_blaetter(roh).values():
        k = next((i for i, r in enumerate(zeilen[:20]) if r and "ISIN" in r and "PRODUCT NAME" in r), None)
        if k is None:
            continue
        stand = ""
        for r in zeilen[:k]:
            for x in r:
                m = re.search(r"As of\s+(\d{2})/(\d{2})/(\d{4})", str(x or ""))
                if m:
                    stand = f"{m.group(3)}-{m.group(2)}-{m.group(1)}"
        kopf = [str(x).strip() if x else "" for x in zeilen[k]]
        fehlt = {"PRODUCT TYPE", "PRODUCT FAMILY", "XETRA SYMBOL", "ONGOING CHARGES", "USE OF PROFITS", "REPLICATION METHOD",
                 "FUND CURRENCY", "TRADING CURRENCY", "BENCHMARK"} - set(kopf)
        if fehlt:
            raise ValueError(f"Börsenliste: Spalten fehlen ({', '.join(sorted(fehlt))})")
        out = []
        for r in zeilen[k + 1:]:
            d = {name: (r[i] if i < len(r) else None) for i, name in enumerate(kopf) if name}
            d["ISIN"] = str(d.get("ISIN") or "").strip()
            if ISIN_RE.fullmatch(d["ISIN"]):
                out.append(d)
        return stand, out
    raise ValueError("Börsenliste: Kopfzeile mit ISIN und PRODUCT NAME nicht gefunden")


def _kopf(zeilen: list, muss: str):
    """(Zeilennummer, {Spaltenname kleingeschrieben: Spalte}) der ersten Kopfzeile mit ISIN und `muss`."""
    for i, r in enumerate(zeilen[:15]):
        namen = {re.sub(r"\s+", " ", str(x)).strip().lower(): j for j, x in enumerate(r) if isinstance(x, str) and x.strip()}
        if "isin" in namen and any(muss in n for n in namen):
            return i, namen
    return None, {}


def _datum(x) -> str:
    """Excel-Tageszahl → JJJJ-MM-TT ("" wenn unlesbar)."""
    try:
        return (datetime.date(1899, 12, 30) + datetime.timedelta(days=int(float(x)))).isoformat()
    except (TypeError, ValueError, OverflowError):
        return ""


def lies_monat(roh: bytes, mit_werten: bool):
    """(Neuzugänge {ISIN: [Anlageklasse, Listing-Datum]}, Werte {ISIN: [Umsatz Mio. €, Fondsvermögen Mio. €, XLM bp]}).
    Neuzugänge: nur ETFs und aktive ETFs. Werte: Umsatz über alle Handelszeilen summiert, Vermögen und XLM von der Zeile
    mit Vermögen (die Euro-Zeile – bei weiteren Handelswährungen bleibt die Spalte leer)."""
    blaetter = xlsx_blaetter(roh, lambda n: "new" in n.lower() or (mit_werten and n.lower().strip().endswith("exchange traded funds")))
    neu, werte = {}, {}
    for name, zeilen in blaetter.items():
        if "new" in name.lower():
            k, sp = _kopf(zeilen, "asset class")
            if k is None:
                continue
            ci, ca = sp["isin"], sp["asset class"]
            ct, cd = sp.get("product type", sp.get("product")), sp.get("listing date")
            for r in zeilen[k + 1:]:
                r = r + [None] * (max(sp.values()) + 1 - len(r))
                isin = str(r[ci] or "").strip()
                if ISIN_RE.fullmatch(isin) and (ct is None or str(r[ct] or "").strip() in ETF_TYPEN):
                    neu[isin] = [sauber(r[ca]), _datum(r[cd]) if cd is not None else ""]
        else:
            k, sp = _kopf(zeilen, "turnover")
            if k is None:
                raise ValueError(f"Monatsstatistik: Kopfzeile im Blatt „{name}“ nicht erkannt")
            ci = sp["isin"]
            cu = next(j for n, j in sp.items() if "turnover" in n)
            cv = next((j for n, j in sp.items() if "assets under management" in n or n == "aum"), None)
            cx = next((j for n, j in sp.items() if "xlm" in n), None)
            zahl = lambda x: float(x) if isinstance(x, (int, float)) and not isinstance(x, bool) else None
            for r in zeilen[k + 1:]:
                r = r + [None] * (max(sp.values()) + 1 - len(r))
                isin = str(r[ci] or "").strip()
                if not ISIN_RE.fullmatch(isin):
                    continue
                u, v, x = zahl(r[cu]) or 0.0, zahl(r[cv]) if cv is not None else None, zahl(r[cx]) if cx is not None else None
                w = werte.setdefault(isin, [0.0, None, None])
                w[0] += u
                if w[1] is None and v is not None:
                    w[1], w[2] = v, x
                elif w[1] is None and w[2] is None:
                    w[2] = x
    return neu, werte


def lies_firds(roh: bytes, isins: set) -> dict:
    """{ISIN: [CFI-Code, erster Handelstag an Xetra/Frankfurt]} für die gesuchten ISINs."""
    je = {}
    with zipfile.ZipFile(io.BytesIO(roh)) as z:
        for _, el in ET.iterparse(z.open(z.namelist()[0]), events=("end",)):
            if el.tag != NS + "RefData":
                continue
            g = el.find(NS + "FinInstrmGnlAttrbts")
            isin = g.findtext(NS + "Id") if g is not None else None
            if isin in isins:
                e = je.setdefault(isin, [collections.Counter(), ""])
                e[0][g.findtext(NS + "ClssfctnTp") or ""] += 1
                if el.findtext(f"{NS}TradgVnRltdAttrbts/{NS}Id") in XETRA_FRANKFURT:
                    t = (el.findtext(f"{NS}TradgVnRltdAttrbts/{NS}FrstTradDt") or "")[:10]
                    if re.fullmatch(r"(19|20)\d\d-\d\d-\d\d", t) and (not e[1] or t < e[1]):
                        e[1] = t
            el.clear()
    return {i: [c.most_common(1)[0][0], t] for i, (c, t) in je.items()}


# ---------------------------------------------------------------- Zwischenstände fortschreiben
def vormonat(d: datetime.date) -> str:
    erster = d.replace(day=1) - datetime.timedelta(days=1)
    return f"{erster.year}-{erster.month:02d}"


def statistik_aktualisieren(klassen: dict, monate: dict, heute: datetime.date, erzwingen: bool) -> bool:
    """Neue Monatsdateien einarbeiten: Anlageklassen der Neuzugänge (klassen) und Monatswerte (monate).
    Gibt True zurück, wenn etwas dazugekommen ist. Fragt die Seite der Börse nur, solange der Vormonat fehlt."""
    fertig = set(klassen.get("monate") or [])
    if not erzwingen and not _fixture() and klassen.get("stand", "") >= vormonat(heute):
        return False
    links = statistik_links(max(fertig) if fertig else KLASSEN_AB)
    if not links:
        raise ValueError("auf der Statistik-Seite der Börse keine Monatsdatei gefunden")
    neu = sorted(m for m in links if m >= KLASSEN_AB and m not in fertig)
    if not neu:
        print(f"Monatsstatistik: nichts Neues (Stand {klassen.get('stand') or '–'}).")
        return False
    fenster = sorted(set(monate.get("monate") or []) | set(neu))[-MONATE_N:]
    je_monat = {}
    for m in neu:
        zugang, werte = lies_monat(monatsdatei(links[m]), m in fenster)
        for isin, v in zugang.items():
            bisher = klassen.setdefault("klassen", {}).get(isin)
            if not bisher or not bisher[0]:                       # die erste Meldung mit Anlageklasse gilt (Listing-Monat)
                klassen["klassen"][isin] = v
        if m in fenster:
            if len(werte) < 1000:
                raise ValueError(f"Monatsstatistik {m}: nur {len(werte)} ETFs gelesen – Datei oder Aufbau defekt")
            je_monat[m] = werte
        fertig.add(m)
        print(f"Monatsstatistik {m}: {len(zugang)} Neuzugänge" + (f", Werte für {len(werte)} ETFs" if m in fenster else ""))
    klassen["monate"] = sorted(fertig)
    klassen["stand"] = klassen["monate"][-1]
    # Monatswerte auf das neue Zwölf-Monats-Fenster umstellen
    alt_monate, alt_werte = monate.get("monate") or [], monate.get("werte") or {}
    pos = {m: i for i, m in enumerate(alt_monate)}
    werte = {}
    for isin in set(alt_werte) | {i for w in je_monat.values() for i in w}:
        u = []
        for m in fenster:
            if m in je_monat:
                u.append(round(je_monat[m][isin][0], 3) if isin in je_monat[m] else None)
            else:
                u.append(alt_werte[isin][0][pos[m]] if isin in alt_werte and m in pos else None)
        if fenster[-1] in je_monat:
            letzter = je_monat[fenster[-1]].get(isin)
            v, x = (letzter[1], letzter[2]) if letzter else (None, None)
        else:
            v, x = (alt_werte[isin][1], alt_werte[isin][2]) if isin in alt_werte else (None, None)
        if any(w is not None for w in u):
            werte[isin] = [u, v, None if x is None else round(x, 1)]
    monate.clear()
    monate.update({"stand": fenster[-1], "monate": fenster, "werte": dict(sorted(werte.items()))})
    return True


def firds_aktualisieren(firds: dict, isins: set, heute: datetime.date, erzwingen: bool) -> bool:
    """CFI-Code und erster Handelstag aus der neuesten Fonds-Gesamtdatei – höchstens einmal pro Woche."""
    stand = firds.get("stand", "1970-01-01")
    if not erzwingen and not _fixture() and (heute - datetime.date.fromisoformat(stand)).days < 7:
        return False
    neueste = firds_neueste(heute)
    if not neueste:
        log_err("FIRDS: keine Fonds-Gesamtdatei (FULINS_C) der letzten 14 Tage gefunden.")
        return False
    datum, link = neueste
    if datum <= stand and not erzwingen:
        return False
    roh = Path(link).read_bytes() if _fixture() else get_with_retry(link, headers=UA, timeout=300)
    gelesen = lies_firds(roh, isins)
    if len(gelesen) < 0.8 * len(isins):
        raise ValueError(f"FIRDS: nur {len(gelesen)} von {len(isins)} ETFs gefunden – Datei defekt?")
    firds.clear()
    firds.update({"stand": datum, "etf": dict(sorted(gelesen.items()))})
    print(f"FIRDS {datum}: {len(gelesen)} von {len(isins)} ETFs mit CFI-Code")
    return True


def zustand_schreiben(pfad: Path, obj: dict, kopf: dict) -> None:
    """Zwischenstand als JSON mit einem Eintrag je Zeile (kleine Git-Diffs)."""
    ZUSTAND.mkdir(exist_ok=True)
    haupt = next(k for k, v in obj.items() if isinstance(v, dict))
    text = json.dumps({**kopf, **{k: v for k, v in obj.items() if k != haupt}}, ensure_ascii=False, separators=(",", ":"))[:-1]
    text += f',"{haupt}":{{\n' + ",\n".join(f"{json.dumps(k)}:{json.dumps(v, ensure_ascii=False, separators=(',', ':'))}"
                                           for k, v in obj[haupt].items()) + "\n}}\n"
    tmp = pfad.with_name(pfad.name + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, pfad)


# ---------------------------------------------------------------- Register bauen
def einstufung(isin: str, name: str, index: str, klassen: dict):
    """Klasse "B" (Börse) oder "S" (Stichwörter), wenn der ETF ein Anleihen-ETF ist, sonst None."""
    amtlich = (klassen.get(isin) or [""])[0]
    if amtlich:
        return "B" if amtlich.lower() in ANLEIHEN_KLASSEN else None
    return "S" if stichwort(name, index) else None


def abgesichert(name: str, markt_: str, fondswaehrung: str) -> str:
    """Währung der Absicherung. Aus dem Namen; nennt er nur „Hedged“ ohne Währung, gilt die Währung der Anteilsklasse.
    Schweigt der Name, zählt ein einziger, belegter Fall: eine Euro-Anteilsklasse eines ETFs auf Dollar-, Pfund- oder
    Yen-Anleihen gilt als in Euro abgesichert – am 30.09.2026 traf das auf alle 85 solchen Klassen zu, bei dreien
    (Invesco US Treasury) nennt die Börsenliste die Absicherung nur nicht im Namen. Umgekehrt gilt es NICHT: Die
    Dollar-Klasse eines China- oder Indien-ETFs ist nur die Fondswährung, keine Absicherung."""
    a = absicherung(name)
    if a == "?" and re.fullmatch(WAEHRUNGEN, fondswaehrung or ""):
        return fondswaehrung
    if not a and markt_ in ("USD", "GBP", "JPY") and fondswaehrung == "EUR":
        return "EUR"
    return a


def gruppe(kat: str, markt_: str, lz, ende, hedge: str, jahr_heute: int) -> str:
    """Tabelle auf anleihen-etf.html, in die der ETF gehört ("" = keine). Jeder ETF steht höchstens in einer:
    erst nach dem Risiko (Schwellenländer, Hochzins), dann nach der Laufzeit, dann nach dem Schuldner.
    Ohne Tabelle bleiben Geldmarkt-ETFs, Pfandbriefe und „Sonstige“ (Wandel- und Nachranganleihen, CLO, MBS, Strategien).
    Kurze Laufzeiten: Laufzeitband bis höchstens drei Jahre oder Laufzeit-ETF mit Ende bis zum übernächsten Jahr –
    nur Euro-Anleihen oder in Euro abgesichert (ein Dollar-Kurzläufer schwankt für Euro-Anleger mit dem Wechselkurs)."""
    if kat in ("Geldmarkt", "Pfandbriefe", "Sonstige"):
        return ""
    if kat == "Schwellenländer":
        return "schwellenlaender"
    if kat == "Hochzins":
        return "hochzinsanleihen"
    kurz = (lz and lz[1] is not None and lz[1] <= KURZ_JAHRE) or (ende and ende - jahr_heute <= KURZ_ENDE)
    if kurz and (markt_ == "EUR" or hedge == "EUR"):
        return "kurze-laufzeiten"
    if kat == "Breit gestreut":
        return "breit-gestreut"
    if kat == "Unternehmen":
        return "unternehmensanleihen"
    if kat in ("Staat", "Inflationsgeschützt"):
        return "euro-staatsanleihen" if markt_ == "EUR" else "staatsanleihen-weltweit"
    return ""


def zahl_json(v, stellen: int):
    if v is None:
        return None
    v = round(float(v), stellen)
    return int(v) if v.is_integer() else v


def bauen(zeilen: list, klassen: dict, monate: dict, firds: dict, heute: datetime.date):
    """(rows, pruefliste) aus den Zeilen der Börsenliste und den Zwischenständen."""
    je_isin = collections.defaultdict(list)
    for d in zeilen:
        if str(d.get("PRODUCT TYPE") or "").strip() in ETF_TYPEN:
            je_isin[d["ISIN"]].append(d)
    kl, cfis, mw = klassen.get("klassen") or {}, firds.get("etf") or {}, monate.get("werte") or {}
    rows, pruefliste = [], []
    for isin in sorted(je_isin):
        linien = je_isin[isin]
        d = next((x for x in linien if str(x.get("TRADING CURRENCY") or "").strip() == "EUR"), linien[0])
        name, index = sauber(d.get("PRODUCT NAME")), sauber(d.get("BENCHMARK"))
        cfi, erster = (cfis.get(isin) or ["", ""])[:2]
        c5 = cfi[4:5]
        klasse = einstufung(isin, name, index, kl)
        if klasse is None:
            # nur der CFI-Code spricht für Anleihen – zur Ansicht auf die Prüfliste, nicht ins Register
            if c5 == "B" and not (kl.get(isin) or [""])[0]:
                pruefliste.append([isin, name, f"nicht im Register, aber CFI-Code {cfi} nennt Anleihen"])
            continue
        kat, mkt = kategorie(name, index), markt(name, index)
        lz, ende = laufzeit(name, index, kat), endjahr(name, index, heute.year)
        fw = sauber(d.get("FUND CURRENCY"))
        hedge = abgesichert(name, mkt, fw)
        pruef = {}
        if c5 in ("E", "C", "R", "D", "F", "K"):
            pruef["cfi"] = cfi
            if klasse == "S":    # nur nach Stichwörtern eingestuft UND der CFI-Code widerspricht – zur Ansicht
                pruefliste.append([isin, name, f"im Register nach Stichwörtern, CFI-Code {cfi} nennt eine andere Anlageklasse"])
        aus = str(d.get("USE OF PROFITS") or "").strip().lower().startswith("dist")
        if (cfi[3:4] == "I" and not aus) or (cfi[3:4] == "G" and aus):
            pruef["ertrag"] = "CFI: ausschüttend" if cfi[3:4] == "I" else "CFI: thesaurierend"
        try:
            kosten = zahl_json(float(d.get("ONGOING CHARGES")) * 100, 4)
        except (TypeError, ValueError):
            kosten = None
        w = mw.get(isin)
        umsatz = [u for u in w[0] if u is not None] if w else []
        rows.append([
            isin, name, sauber(d.get("PRODUCT FAMILY")), sauber(d.get("XETRA SYMBOL")),
            1 if str(d.get("PRODUCT TYPE")).strip() == "Active ETF" else 0, kosten, 1 if aus else 0,
            NACHBILDUNG.get(sauber(d.get("REPLICATION METHOD")).lower(), ""), fw,
            sauber(d.get("TRADING CURRENCY")), index, klasse, kat, mkt, lz, ende, hedge,
            gruppe(kat, mkt, lz, ende, hedge, heute.year),
            erster or (kl.get(isin) or ["", ""])[1],
            zahl_json(w[1], 2) if w else None, zahl_json(sum(umsatz), 2) if umsatz else None, zahl_json(w[2], 1) if w else None,
            pruef])
    return rows, pruefliste


def objekt(r: list) -> dict:
    """Registerzeile als Objekt für die Seiten – mit „kurzname“, ohne die Prüffelder. Die Börsenliste schreibt mal „€“
    und „$“, mal „EUR“ und „USD“ (iShares iBonds … Term € Corp / … Term EUR Corp); der Kurzname schreibt einheitlich
    die Kürzel."""
    d = {f: v for f, v in zip(FELDER, r) if f not in ("klasse", "pruef")}
    d["kurzname"] = (kern(d["name"]) or d["name"]).replace("€", "EUR").replace("$", "USD")
    return d


def top10(rows: list) -> dict:
    """{Anker: {"anzahl": ETFs der Kategorie, "etfs": [die TOP_N mit dem höchsten Umsatz der letzten zwölf Monate]}}."""
    g, u = FELDER.index("gruppe"), FELDER.index("umsatz12")
    out = {}
    for key in GRUPPEN:
        alle = [r for r in rows if r[g] == key]
        beste = sorted((r for r in alle if r[u]), key=lambda r: (-r[u], r[0]))[:TOP_N]
        out[key] = {"anzahl": len(alle), "etfs": [objekt(r) for r in beste]}
    return out


SEITEN_ETF = re.compile(r'data-etf="([A-Z]{2}[A-Z0-9]{9}[0-9])"')


def seiten_auswahl(rows: list, beste: dict) -> tuple[dict, list]:
    """({ISIN: Objekt}, [fehlende ISINs]) der ETFs, die eine HTML-Seite mit data-etf="<ISIN>" nennt (Beispiel-Karten
    im Guide). Fehlend = auf einer Seite genannt, aber nicht (mehr) im Register – die Karte bliebe dort ohne Daten."""
    isins = set()
    for html in ROOT.glob("*.html"):
        isins |= set(SEITEN_ETF.findall(html.read_text(encoding="utf-8")))
    in_top = {e["isin"]: key for key, v in beste.items() for e in v["etfs"]}
    auswahl = {r[0]: {**objekt(r), "top10": in_top.get(r[0], "")} for r in rows if r[0] in isins}
    return auswahl, sorted(isins - set(auswahl))


def schreiben(meta: dict, rows: list) -> None:
    """Ein ETF je Zeile (kleine Git-Diffs), atomar."""
    kopf = json.dumps(meta, ensure_ascii=False, separators=(",", ":"))[:-1]
    text = kopf + ',"rows":[\n' + ",\n".join(json.dumps(r, ensure_ascii=False, separators=(",", ":")) for r in rows) + "\n]}\n"
    tmp = OUT.with_name(OUT.name + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, OUT)


def main() -> int:
    heute = datetime.date.today()
    erzwingen = "--force" in sys.argv
    alt = lade(OUT, {})
    rc = 0

    # 1) Börsenliste – ohne sie kein neues Register
    try:
        stand, zeilen = lies_liste(boersenliste())
    except Exception as e:  # noqa: BLE001
        log_err(f"ETF-Liste der Deutschen Börse nicht lesbar ({e}) – etf-index.json bleibt auf dem Stand {alt.get('stand') or '–'}.")
        return 1
    if len(zeilen) < MIN_ZEILEN:
        log_err(f"ETF-Liste: nur {len(zeilen)} Zeilen (erwartet über {MIN_ZEILEN}) – etf-index.json bleibt unverändert.")
        return 1
    etf_isins = {d["ISIN"] for d in zeilen if str(d.get("PRODUCT TYPE") or "").strip() in ETF_TYPEN}

    # 2) Monatsstatistik: Anlageklassen der Neuzugänge, Umsatz, Fondsvermögen, XLM
    klassen, monate = lade(KLASSEN, {}), lade(MONATE, {})
    try:
        if statistik_aktualisieren(klassen, monate, heute, erzwingen):
            zustand_schreiben(KLASSEN, {"klassen": dict(sorted(klassen["klassen"].items()))},
                              {"stand": klassen["stand"], "quelle": "Deutsche Börse, Monatsstatistik ETFs & ETPs, Blatt „New Listings“: [Anlageklasse, Listing-Datum] je ETF",
                               "monate": klassen["monate"]})
            zustand_schreiben(MONATE, {"werte": monate["werte"]},
                              {"stand": monate["stand"], "quelle": "Deutsche Börse, Monatsstatistik ETFs & ETPs: [[Umsatz im Xetra-Orderbuch je Monat in Mio. €], Fondsvermögen der Anteilsklasse in Mio. €, XLM in Basispunkten]",
                               "monate": monate["monate"]})
    except Exception as e:  # noqa: BLE001
        log_err(f"Monatsstatistik der Deutschen Börse nicht verarbeitet ({e}) – Register mit dem Stand {klassen.get('stand') or '–'}.")
        klassen, monate, rc = lade(KLASSEN, {}), lade(MONATE, {}), 1

    # 3) FIRDS: CFI-Code und erster Handelstag (Gegenprobe)
    firds = lade(FIRDS, {})
    try:
        if firds_aktualisieren(firds, etf_isins, heute, erzwingen):
            zustand_schreiben(FIRDS, {"etf": firds["etf"]},
                              {"stand": firds["stand"], "quelle": "ESMA FIRDS (FULINS_C): [CFI-Code, erster Handelstag an Xetra/Frankfurt] je ETF der Börsenliste"})
    except Exception as e:  # noqa: BLE001
        log_err(f"FIRDS (Fonds) nicht verarbeitet ({e}) – Register mit dem Stand {firds.get('stand') or '–'}.")
        firds, rc = lade(FIRDS, {}), 1

    # 4) Register
    rows, pruefliste = bauen(zeilen, klassen, monate, firds, heute)
    n_alt = len(alt.get("rows") or [])
    if n_alt and len(rows) < MIN_ANTEIL * n_alt:
        log_err(f"Nur {len(rows)} Anleihen-ETFs statt zuvor {n_alt} – etf-index.json bleibt unverändert.")
        return 1
    if not rows:
        log_err("Kein einziger Anleihen-ETF erkannt – etf-index.json bleibt unverändert.")
        return 1

    fenster = monate.get("monate") or []
    meta = {"stand": stand or today_iso(), "updated": today_iso(), "updatedAt": now_iso(), "checkedAt": now_iso(),
            "quelle": "Deutsche Börse (Liste der handelbaren ETFs & ETPs; Monatsstatistik ETFs & ETPs) und ESMA FIRDS "
                      "(erster Handelstag, CFI-Code als Gegenprobe); Kategorie, Markt, Laufzeit, Endjahr und Absicherung aus Name und Index abgeleitet",
            "statistik": monate.get("stand") or "", "umsatz": {"von": fenster[0], "bis": fenster[-1]} if fenster else None,
            "firds": firds.get("stand") or "",
            "felder": FELDER, "abgeleitet": ABGELEITET, "kategorien": KATEGORIEN,
            "klasse": {"B": "Anlageklasse „Fixed Income“ laut Deutscher Börse (Neuzugangs-Liste)",
                       "S": "nach Stichwörtern in Name und Index (vor 07/2016 gelistet oder Monatsstatistik noch nicht erschienen)"},
            "gruppen": GRUPPEN,
            "pruef": {"ertrag": "CFI-Code (ESMA) meldet die andere Ertragsverwendung",
                      "cfi": "CFI-Code (ESMA) nennt eine andere Anlageklasse als Anleihen"},
            "einheiten": {"kosten": "% p. a.", "vermoegen": "Mio. € (Anteilsklasse)", "umsatz12": "Mio. € (Xetra-Orderbuch)", "xlm": "Basispunkte (100.000 € hin und zurück)"},
            "anzahl": len(rows), "pruefliste": pruefliste}
    schreiben(meta, rows)

    # 5) Die zehn meistgehandelten je Kategorie (anleihen-etf.html)
    beste = top10(rows)
    write_atomic(OUT_TOP10, {"stand": meta["stand"], "updated": meta["updated"], "updatedAt": meta["updatedAt"],
                             "quelle": "Deutsche Börse: Liste der handelbaren ETFs & ETPs (Stammdaten, Kosten) und Monatsstatistik ETFs & ETPs "
                                       "(Umsatz im Xetra-Orderbuch, Fondsvermögen der Anteilsklasse, XLM); Kategorie, Laufzeit und Absicherung aus Name und Index abgeleitet",
                             "statistik": meta["statistik"], "umsatz": meta["umsatz"], "anzahl": len(rows), "gruppen": beste})
    auswahl, fehlend = seiten_auswahl(rows, beste)
    write_atomic(OUT_AUSWAHL, {"stand": meta["stand"], "updated": meta["updated"], "updatedAt": meta["updatedAt"],
                               "quelle": "Deutsche Börse (Liste der handelbaren ETFs & ETPs, Monatsstatistik ETFs & ETPs)",
                               "statistik": meta["statistik"], "umsatz": meta["umsatz"], "etfs": auswahl})
    if fehlend:   # niemand pflegt die Karten von Hand – ein ETF, der aus der Börsenliste fällt, muss auffallen
        log_err("ETF-Karte ohne Daten: " + ", ".join(fehlend) + " steht auf einer Seite (data-etf), aber nicht im Register – "
                "die ISIN im HTML ersetzen.")
        rc = 1

    # 6) Bericht
    spalte = {f: i for i, f in enumerate(FELDER)}
    kl = collections.Counter(r[spalte["klasse"]] for r in rows)
    kat = collections.Counter(r[spalte["kategorie"]] for r in rows)
    print(f"etf-index.json: {len(rows)} Anleihen-ETFs (Stand {meta['stand']}) – Börse {kl['B']}, Stichwort {kl['S']}; "
          + ", ".join(f"{k} {kat[k]}" for k in KATEGORIEN if kat[k])
          + f"; mit Fondsvermögen {sum(1 for r in rows if r[spalte['vermoegen']] is not None)}, Prüfliste {len(pruefliste)}")
    print("top10-anleihen-etfs.json: " + ", ".join(f"{k} {len(v['etfs'])} von {v['anzahl']}" for k, v in beste.items())
          + f"; etf-auswahl.json: {len(auswahl)} ETFs der Seiten")
    if n_alt:
        vorher, jetzt = {r[0]: r[1] for r in alt["rows"]}, {r[0]: r[1] for r in rows}
        for titel, isins, namen in (("Neu im Register", sorted(set(jetzt) - set(vorher)), jetzt),
                                    ("Nicht mehr im Register", sorted(set(vorher) - set(jetzt)), vorher)):
            if isins:
                print(f"{titel} ({len(isins)}): " + "; ".join(f"{i} {namen[i]}" for i in isins[:25]) + (" …" if len(isins) > 25 else ""))
    return rc


if __name__ == "__main__":
    sys.exit(main())
