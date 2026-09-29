#!/usr/bin/env python3
"""Baut anleihen-index.json – die Datenbasis der Anleihen-Suche (anleihen-suche.html).

Quelle: ESMA FIRDS (Financial Instruments Reference Data System, amtliches
EU-Register), wöchentliche Gesamtdatei der Schuldtitel
FULINS_D_<Datum>_<n>of<m>.zip (erscheint samstags früh, frei abrufbar;
Wiedergabe mit Quellenangabe erlaubt – ESMA-Hinweis steht auf der Suchseite).

Aufgenommen wird jede Anleihe, die
- laut CFI-Code eine Anleihe (DB), Medium-Term-Note (DT) oder Kommunal-
  anleihe (DN) ist – nicht: Zertifikate/strukturierte Produkte (DE/DS),
  Wandelanleihen (DC), ABS/MBS (DA/DG), Geldmarktpapiere (DY),
- an einer deutschen Börse gehandelt wird (Stuttgart, Frankfurt, Xetra,
  München/gettex, Berlin, Düsseldorf, Hamburg, Hannover, Tradegate) und
- weder fällig noch vom Handel genommen ist.

Einstufung (Spalte „Art“) je Emittent, über das LEI-Register GLEIF:
- Staat: Zentralstaat. Erkannt am Namen der Anleihe (beginnt mit dem Land
  des Emittenten, z. B. „Griechenland EO-…“, „Österreich, Republik …“) oder
  an der GLEIF-Kategorie CENTRAL_GOVERNMENT (ohne staatliche Banken/Agenturen).
- Öffentlich: Bundesländer, Regionen, Städte, Förderbanken, staatlich
  garantierte Emittenten und supranationale Institutionen (GLEIF-Kategorie
  Regierungsstelle/internationale Organisation oder überwiegend CFI-Garantie
  „Staat“ bzw. „supranational“).
- Unternehmen: alle übrigen (einschließlich Banken und Versicherer).

Land: Konzernmutter („ultimate parent“, sonst direkte Mutter) aus der Beziehungsdatei des
LEI-Registers (GLEIF Golden Copy, Relationship Records, wöchentlich ~25 MB) – so zählt
etwa die Mercedes-Benz International Finance B.V. zu Deutschland, nicht zu den Niederlanden.

Drossel: Die Gesamtdatei erscheint einmal pro Woche. Das Skript fragt die
Dateiliste erst, wenn der Index-Stand mindestens 7 Tage alt ist, und baut nur
neu, wenn eine neuere Gesamtdatei vorliegt (sonst kein weiterer Abruf).

Ausgabe: anleihen-index.json (eine Zeile je Anleihe, damit Git-Diffs klein
bleiben). Die Suchseite lädt die Datei per fetch – sie wird NICHT per
inline_data.py in die Seite eingebettet (kein MC.load).
Dazu seit 26.09.2026 die Teildateien anleihen/<hh>.json (256 Stück, hh = teil(ISIN) wie in
update_kurse.py und site.js) für die Steckbrief-Seite anleihe.html – je Anleihe dieselben Felder
ohne isin, mit dem Emittentennamen statt des Index: {"stand", "rang", "rueckzahlung", "garantie",
"rows": {ISIN: [name, art, waehrung, kupon, faellig, volumen, stueckelung, boerse, emittent, zinsart, land, extra, mehr, pruef]}}
    rows[i] = [isin, name, art, waehrung, kupon, faellig, volumen, stueckelung, boerse, emittent, zinsart, land, extra, mehr, pruef]
    art: 0 Staat · 1 Öffentlich · 2 Unternehmen; kupon: "var" = variabel, null = unbekannt;
    faellig: "" = ohne Endfälligkeit; boerse (Kurslink): 0 keiner · 1 Stuttgart · 2 Frankfurt;
    zinsart: 0 fest · 1 variabel · 2 Nullkupon (FIRDS-Zinssatz bzw. CFI-Code);
    land: ISO-Code des Konzernsitzes (Konzernmutter laut LEI-Register, sonst Sitz des Emittenten;
    Staaten: der Staat selbst; supranationale Institutionen: "INT");
    emittent: Index in "emittenten" (Name laut LEI-Register, nur für die Suche – die Anleihenamen
    kürzen ab: „Dt.Telekom Intl Finance“, „Kreditanst.f.Wiederaufbau“);
    extra: zusätzliche Suchwörter (nur Staaten, z. B. „USA Vereinigte Staaten Treasury“), sonst "";
    mehr (seit 26.09.2026): ["<rang><rueckzahlung><garantie>", ausgabe, floater?] – drei Buchstaben
      ("-" = unbekannt), der erste Handelstag und nur bei variablem Zins ein drittes Element:
      rang: FIRDS DebtSnrty – "S" erstrangig (SNDB), "U" nachrangig (SBOD), "J" tief nachrangig (JUND),
            "M" Mezzanine (MZZD), "" nicht gemeldet;
      rueckzahlung: 5. Stelle des CFI-Codes – F feste Fälligkeit, G mit Kündigungsrecht des Emittenten,
            C mit Kündigungsrecht des Anlegers, D beides, A Tilgungsplan, B Tilgungsplan + Emittent kündbar,
            T Tilgungsplan + Anleger kündbar, L Tilgungsplan + beides, P unbefristet, Q unbefristet + kündbar,
            R verlängerbar, "" unbekannt;
      garantie: 4. Stelle des CFI-Codes – T staatlich garantiert, G garantiert durch Dritte (z. B. Konzernmutter), S besichert,
            U unbesichert, P Negativklausel, N erstrangig, O nachrangig, Q nachrangig (junior),
            J tief nachrangig, C supranational, "" unbekannt;
      floater: null oder [referenz, einheit, wert, aufschlag_bp] – Referenzzins laut FIRDS (Index-Kürzel wie
            "EURI" oder Name wie "SWAP 5Y", "" = nicht gemeldet), Zinsperiode (Einheit D/W/M/Y und Zahl),
            Aufschlag in Basispunkten;
      ausgabe: erster Handelstag an einer deutschen Börse (FIRDS FrstTradDt, frühester), "" unbekannt.

Prüfung (seit 27.09.2026, Nutzerregel: Registerdaten bleiben unverändert, Widersprüche werden angezeigt):
Das Register enthält vereinzelt Fehler (Vodafone XS3109655293: Kupon 0 %, Fälligkeit 2028 – der Kurzname im
selben Register sagt 3,875 % bis 2038; Fingrid „1125“ = Faktor 10; Libanon 2006(21) ohne Fälligkeit). Statt zu
korrigieren, bekommt jede Anleihe das Feld pruef (Index 14, Teildateien 13): ein Objekt mit Befunden (leer = ohne
Befund) – kuponFisn, faelligFisn (Kurzname nach ISO 18774 gegen Register), faelligName (WM-Name gegen Register,
auch „fällig, nicht zurückgezahlt“), zinsName (FLR im Namen, Register Nullkupon), kuponHoch (siehe pruefung()).
Suche und Steckbrief zeigen den Registerwert mit dem Widerspruch daneben; update_kurse.py rechnet bei einem
Befund keine Rendite (_common.ohne_rendite). Bis 26.09.2026 wurden diese Fälle korrigiert bzw. entfernt (Kupon →
unbekannt, FLR → variabel, überfällige entfernt) – das ist zugunsten der unveränderten Quelle aufgegeben.
Was bleibt, ist keine Korrektur, sondern Auswahl: Anleihen, deren Fälligkeit laut Register vor heute liegt,
stehen nicht im Index (sie sind fällig), Fälligkeiten ab 2200 gelten als unbefristet (leer).

Aufruf: python scripts/update_anleihen_index.py [--force]
        python scripts/update_anleihen_index.py --bereinigen   Prüfung (Feld pruef) auf den vorhandenen Index
                                                                anwenden (ohne Abruf; Kurzname-Befunde bleiben), Teildateien neu schreiben
"""

import collections
import csv
import datetime
import io
import json
import os
import re
import sys
import tempfile
import unicodedata
import urllib.parse
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

from _common import get_with_retry, log_err, now_iso, today_iso

OUT = Path(__file__).resolve().parent.parent / "anleihen-index.json"
FILES_API = ("https://registers.esma.europa.eu/solr/esma_registers_firds_files/select?"
             "q=*&fq=publication_date:%5B{von}T00:00:00Z+TO+{bis}T23:59:59Z%5D"
             "&wt=json&start=0&rows=500")
GLEIF_API = "https://api.gleif.org/api/v1/lei-records?"
GLEIF_GC = "https://goldencopy.gleif.org/api/v2/golden-copies/publishes/latest"
SUPRANATIONAL = re.compile(r"EUROPEAN (FINANCIAL STABILITY|STABILITY MECHANISM|UNION)|^EUROPEAN UNION$", re.IGNORECASE)
UA = {"User-Agent": "metalconcrete.de Anleihen-Suche (Datenaufbereitung)", "Accept": "*/*"}
NS = "{urn:iso:std:iso:20022:tech:xsd:auth.017.001.02}"

CFI_ANLEIHE = ("DB", "DT", "DN")
# Deutsche Börsen: operative MICs und ihre Segmente (ISO 10383). Keine
# systematischen Internalisierer/Banken-Handelsplätze.
STUTTGART = {"XSTU", "STUA", "STUB", "STUC", "STUD", "STUE", "STUF", "STUH"}
FRANKFURT = {"XFRA", "FRAA", "FRAB", "FRAS"}
BOERSEN_DE = STUTTGART | FRANKFURT | {
    "XETR", "XETA", "XETB", "XETS",                              # Xetra
    "XMUN", "MUNA", "MUNB", "MUNC", "MUND",                      # München, gettex
    "XBER", "BERA", "BERB", "BERC", "EQTA", "EQTB", "EQTC",      # Berlin
    "XDUS", "DUSA", "DUSB", "DUSC", "DUSD", "XQTX",              # Düsseldorf, Quotrix
    "XHAM", "HAMA", "HAMB", "HAMM", "HAMN", "HAMP", "HAMQ", "HAMY", "HAMZ",  # Hamburg
    "XHAN", "HANA", "HANB", "HANC", "HAND",                      # Hannover
    "TGAT", "XGAT", "XGRM",                                      # Tradegate
}
# Welcher Handelsplatz liefert den Anleihenamen? Frankfurt/Düsseldorf/Hamburg/
# Hannover/Berlin führen die WM-Kurzbezeichnung („Bundesrep.Deutschland
# Anl.v.2019 (2050)“), Stuttgart und München teils eigene Kurzformen.
NAME_RANG = [FRANKFURT, {"XDUS", "DUSA", "DUSB", "DUSC", "DUSD", "XQTX"},
             {"XHAM", "HAMA", "HAMB", "HAMM", "HAMN", "HAMP", "HAMQ", "HAMY", "HAMZ"},
             {"XHAN", "HANA", "HANB", "HANC", "HAND"}, {"XBER", "BERA", "BERB", "BERC", "EQTA", "EQTB", "EQTC"},
             {"TGAT", "XGAT", "XGRM"}, STUTTGART]

ART = ["Staat", "Öffentlich", "Unternehmen"]
# FIRDS meldet als „Nennwert je Stück/Mindesthandelswert“ bei manchen Staaten den
# Mindestschluss des Großhandels (Italien 2 Mio. € auf MTS) oder 1/1.000 statt der
# kleinsten Stückelung. Korrigiert auf den kleinsten Nennwert laut Emittent
# (geprüft 09/2026 gegen die Stammdaten der Deutschen Börse):
STUECK_STAAT = {"IT": 1000, "GB": 0.01, "IE": 0.01}
UNBEFRISTET = "2200"   # FIRDS: Ewige Anleihen mit Fälligkeit 9999-12-31 (vereinzelt 30xx)
BOERSE = ["", "Stuttgart", "Frankfurt"]

# Ländernamen (Deutsch, CLDR) je ISO-Code des Emittenten-Sitzes laut GLEIF –
# für die Erkennung „Name der Anleihe beginnt mit dem Land“.
LAENDER = {
    "AC": "Ascension", "AD": "Andorra", "AE": "Vereinigte Arabische Emirate", "AF": "Afghanistan",
    "AG": "Antigua und Barbuda", "AI": "Anguilla", "AL": "Albanien", "AM": "Armenien",
    "AO": "Angola", "AQ": "Antarktis", "AR": "Argentinien", "AS": "Amerikanisch-Samoa",
    "AT": "Österreich", "AU": "Australien", "AW": "Aruba", "AX": "Ålandinseln",
    "AZ": "Aserbaidschan", "BA": "Bosnien und Herzegowina", "BB": "Barbados", "BD": "Bangladesch",
    "BE": "Belgien", "BF": "Burkina Faso", "BG": "Bulgarien", "BH": "Bahrain", "BI": "Burundi",
    "BJ": "Benin", "BL": "St. Barthélemy", "BM": "Bermuda", "BN": "Brunei Darussalam",
    "BO": "Bolivien", "BQ": "Karibische Niederlande", "BR": "Brasilien", "BS": "Bahamas",
    "BT": "Bhutan", "BV": "Bouvetinsel", "BW": "Botsuana", "BY": "Belarus", "BZ": "Belize",
    "CA": "Kanada", "CC": "Kokosinseln", "CD": "Kongo-Kinshasa",
    "CF": "Zentralafrikanische Republik", "CG": "Kongo-Brazzaville", "CH": "Schweiz",
    "CI": "Côte d’Ivoire", "CK": "Cookinseln", "CL": "Chile", "CM": "Kamerun", "CN": "China",
    "CO": "Kolumbien", "CP": "Clipperton-Insel", "CR": "Costa Rica", "CU": "Kuba",
    "CV": "Cabo Verde", "CW": "Curaçao", "CX": "Weihnachtsinsel", "CY": "Zypern",
    "CZ": "Tschechien", "DE": "Deutschland", "DG": "Diego Garcia", "DJ": "Dschibuti",
    "DK": "Dänemark", "DM": "Dominica", "DO": "Dominikanische Republik", "DZ": "Algerien",
    "EA": "Ceuta und Melilla", "EC": "Ecuador", "EE": "Estland", "EG": "Ägypten",
    "EH": "Westsahara", "ER": "Eritrea", "ES": "Spanien", "ET": "Äthiopien",
    "EU": "Europäische Union", "EZ": "Eurozone", "FI": "Finnland", "FJ": "Fidschi",
    "FK": "Falklandinseln", "FM": "Mikronesien", "FO": "Färöer", "FR": "Frankreich", "GA": "Gabun",
    "GB": "Vereinigtes Königreich", "GD": "Grenada", "GE": "Georgien", "GF": "Französisch-Guayana",
    "GG": "Guernsey", "GH": "Ghana", "GI": "Gibraltar", "GL": "Grönland", "GM": "Gambia",
    "GN": "Guinea", "GP": "Guadeloupe", "GQ": "Äquatorialguinea", "GR": "Griechenland",
    "GS": "Südgeorgien und die Südlichen Sandwichinseln", "GT": "Guatemala", "GU": "Guam",
    "GW": "Guinea-Bissau", "GY": "Guyana", "HK": "Hongkong", "HM": "Heard und McDonaldinseln",
    "HN": "Honduras", "HR": "Kroatien", "HT": "Haiti", "HU": "Ungarn", "IC": "Kanarische Inseln",
    "ID": "Indonesien", "IE": "Irland", "IL": "Israel", "IM": "Isle of Man", "IN": "Indien",
    "IO": "Britisches Territorium im Indischen Ozean", "IQ": "Irak", "IR": "Iran", "IS": "Island",
    "IT": "Italien", "JE": "Jersey", "JM": "Jamaika", "JO": "Jordanien", "JP": "Japan",
    "KE": "Kenia", "KG": "Kirgisistan", "KH": "Kambodscha", "KI": "Kiribati", "KM": "Komoren",
    "KN": "St. Kitts und Nevis", "KP": "Nordkorea", "KR": "Südkorea", "KW": "Kuwait",
    "KY": "Kaimaninseln", "KZ": "Kasachstan", "LA": "Laos", "LB": "Libanon", "LC": "St. Lucia",
    "LI": "Liechtenstein", "LK": "Sri Lanka", "LR": "Liberia", "LS": "Lesotho", "LT": "Litauen",
    "LU": "Luxemburg", "LV": "Lettland", "LY": "Libyen", "MA": "Marokko", "MC": "Monaco",
    "MD": "Republik Moldau", "ME": "Montenegro", "MF": "St. Martin", "MG": "Madagaskar",
    "MH": "Marshallinseln", "MK": "Nordmazedonien", "ML": "Mali", "MM": "Myanmar", "MN": "Mongolei",
    "MO": "Sonderverwaltungsregion Macau", "MP": "Nördliche Marianen", "MQ": "Martinique",
    "MR": "Mauretanien", "MS": "Montserrat", "MT": "Malta", "MU": "Mauritius", "MV": "Malediven",
    "MW": "Malawi", "MX": "Mexiko", "MY": "Malaysia", "MZ": "Mosambik", "NA": "Namibia",
    "NC": "Neukaledonien", "NE": "Niger", "NF": "Norfolkinsel", "NG": "Nigeria", "NI": "Nicaragua",
    "NL": "Niederlande", "NO": "Norwegen", "NP": "Nepal", "NR": "Nauru", "NU": "Niue",
    "NZ": "Neuseeland", "OM": "Oman", "PA": "Panama", "PE": "Peru", "PF": "Französisch-Polynesien",
    "PG": "Papua-Neuguinea", "PH": "Philippinen", "PK": "Pakistan", "PL": "Polen",
    "PM": "St. Pierre und Miquelon", "PN": "Pitcairninseln", "PR": "Puerto Rico",
    "PS": "Palästinensische Autonomiegebiete", "PT": "Portugal", "PW": "Palau", "PY": "Paraguay",
    "QA": "Katar", "QO": "Äußeres Ozeanien", "RE": "Réunion", "RO": "Rumänien", "RS": "Serbien",
    "RU": "Russland", "RW": "Ruanda", "SA": "Saudi-Arabien", "SB": "Salomonen", "SC": "Seychellen",
    "SD": "Sudan", "SE": "Schweden", "SG": "Singapur", "SH": "St. Helena", "SI": "Slowenien",
    "SJ": "Spitzbergen und Jan Mayen", "SK": "Slowakei", "SL": "Sierra Leone", "SM": "San Marino",
    "SN": "Senegal", "SO": "Somalia", "SR": "Suriname", "SS": "Südsudan",
    "ST": "São Tomé und Príncipe", "SV": "El Salvador", "SX": "Sint Maarten", "SY": "Syrien",
    "SZ": "Eswatini", "TA": "Tristan da Cunha", "TC": "Turks- und Caicosinseln", "TD": "Tschad",
    "TF": "Französische Süd- und Antarktisgebiete", "TG": "Togo", "TH": "Thailand",
    "TJ": "Tadschikistan", "TK": "Tokelau", "TL": "Timor-Leste", "TM": "Turkmenistan",
    "TN": "Tunesien", "TO": "Tonga", "TR": "Türkei", "TT": "Trinidad und Tobago", "TV": "Tuvalu",
    "TW": "Taiwan", "TZ": "Tansania", "UA": "Ukraine", "UG": "Uganda",
    "UM": "Amerikanische Überseeinseln", "UN": "Vereinte Nationen", "US": "Vereinigte Staaten",
    "UY": "Uruguay", "UZ": "Usbekistan", "VA": "Vatikanstadt",
    "VC": "St. Vincent und die Grenadinen", "VE": "Venezuela", "VG": "Britische Jungferninseln",
    "VI": "Amerikanische Jungferninseln", "VN": "Vietnam", "VU": "Vanuatu",
    "WF": "Wallis und Futuna", "WS": "Samoa", "XA": "Pseudo-Akzente", "XB": "Pseudo-Bidi",
    "XK": "Kosovo", "YE": "Jemen", "YT": "Mayotte", "ZA": "Südafrika", "ZM": "Sambia",
    "ZW": "Simbabwe", "ZZ": "Unbekannte Region",
}
# Weitere Schreibweisen in den Anleihenamen und Suchbegriffe je Staat
ALIAS = {
    "DE": ["Bundesrep.Deutschland", "Bundesrepublik Deutschland", "Bund"],
    "US": ["United States of America", "USA", "Treasury"],
    "GB": ["Großbritannien", "UK", "Gilt"],
    "FR": ["OAT"], "IT": ["BTP"], "ES": ["Bonos"],
    "AU": ["Australia"], "NZ": ["New Zealand"], "ZA": ["South Africa"],
    "CZ": ["Tschechische Republik"], "HK": ["Hong Kong", "Hongkong"], "KR": ["Korea"],
    "CI": ["Côte d'Ivoire", "Elfenbeinküste"], "CA": ["Canada"], "CG": ["Kongo"], "CD": ["Kongo"],
    "TT": ["Trinidad & Tobago"], "BA": ["Bosnien-Herzegowina"], "RU": ["Russische Föderation"],
}
# Geläufige Kürzel, die weder im Anleihenamen noch im LEI-Register stehen (Suche)
KUERZEL = [(re.compile(p, re.IGNORECASE), w) for p, w in [
    (r"^Kreditanstalt f(ü|ue)r Wiederaufbau", "KfW"), (r"^European Investment Bank", "EIB Europäische Investitionsbank"),
    (r"^International Bank for Reconstruction", "Weltbank World Bank IBRD"), (r"^Volkswagen", "VW"),
    (r"^European Union$", "EU Europäische Union"), (r"^European Stability Mechanism", "ESM"),
    (r"^European Financial Stability Facility", "EFSF"), (r"^Landwirtschaftliche Rentenbank", "Rentenbank"),
]]
# Staatliche Banken/Agenturen, die GLEIF als Zentralstaat führt (→ Öffentlich)
AGENTUR = re.compile(r"BANK|BANCO|BANQUE|INSTITUT|BPIFRANCE|ADIF|COMISI|AGENC|CORPORA|SOCIET|COMPAN|FUND|FONDS",
                     re.IGNORECASE)
# Nach dem Ländernamen folgt in Staatsanleihe-Namen: Komma („Österreich, Republik“),
# Währungskürzel („EO-“, „DL-“), eine Zahl („Griechenland 34“) oder eine Gattung.
NACH_LAND = re.compile(r"(?:,|\s+(?:[A-Z]{2}-|\d|perp\b|FLR\b|Anl|Bds?\b|Bonds?\b|Notes?\b|Treasury\b)|$)")
PRAEFIX = re.compile(r"^(?:[$€£]|[A-Z]{3})\s+")   # Stuttgart/München: „$ Mexiko 34“, „IDR Asian …“


def ohne_praefix(name: str, ccy: str) -> str:
    """Währungsvorsatz der Stuttgarter/Münchner Kurznamen entfernen – nur „$ “/„€ “/„£ “
    oder die Währung der Anleihe selbst („PLN Polen 47“), nicht „ANZ New Zealand …“."""
    m = PRAEFIX.match(name or "")
    if m and (m.group(0).strip() in "$€£" or m.group(0).strip() == ccy):
        return name[m.end():]
    return name or ""


def norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "")
    return "".join(c for c in s if not unicodedata.combining(c)).lower()


def land_im_namen(name: str, ccy: str, land: str) -> bool:
    """Beginnt der Anleihename mit dem Land des Emittenten (oder einer Alias-Schreibweise)?"""
    n = ohne_praefix(name, ccy)
    for kandidat in [LAENDER.get(land, "")] + ALIAS.get(land, [])[:2]:
        if kandidat and norm(n).startswith(norm(kandidat)) and NACH_LAND.match(n[len(kandidat):]):
            return True
    return False


# ---------------------------------------------------------------- FIRDS
def neueste_gesamtdatei(bis: datetime.date) -> tuple[str, list[str]] | None:
    """(Datum, Download-Links) der neuesten vollständigen FULINS_D-Serie der letzten 14 Tage."""
    url = FILES_API.format(von=(bis - datetime.timedelta(days=14)).isoformat(), bis=bis.isoformat())
    docs = json.loads(get_with_retry(url, headers=UA, timeout=60))["response"]["docs"]
    serien = collections.defaultdict(dict)
    for d in docs:
        m = re.fullmatch(r"FULINS_D_(\d{8})_(\d+)of(\d+)\.zip", d.get("file_name", ""))
        if m:
            serien[(m.group(1), int(m.group(3)))][int(m.group(2))] = d["download_link"]
    for (datum, teile), links in sorted(serien.items(), reverse=True):
        if len(links) == teile:
            return f"{datum[:4]}-{datum[4:6]}-{datum[6:]}", [links[i] for i in sorted(links)]
    return None


def lies_firds(links: list[str], heute: str) -> dict[str, list[dict]]:
    """Alle Datensätze (je Handelsplatz einer) der Anleihen an deutschen Börsen, nach ISIN."""
    je_isin = collections.defaultdict(list)
    for link in links:
        with tempfile.TemporaryFile() as tmp:
            lokal = os.environ.get("FIXTURE_DIR")   # Tests: Gesamtdatei aus lokalem Ordner
            tmp.write(Path(lokal, link.rsplit("/", 1)[-1]).read_bytes() if lokal
                      else get_with_retry(link, headers=UA, timeout=300))
            tmp.seek(0)
            with zipfile.ZipFile(tmp) as z:
                for _, el in ET.iterparse(z.open(z.namelist()[0]), events=("end",)):
                    if el.tag != NS + "RefData":
                        continue
                    mic = el.findtext(f"{NS}TradgVnRltdAttrbts/{NS}Id")
                    g = el.find(NS + "FinInstrmGnlAttrbts")
                    cfi = g.findtext(NS + "ClssfctnTp") or ""
                    ende = (el.findtext(f"{NS}TradgVnRltdAttrbts/{NS}TermntnDt") or "")[:10]
                    if mic in BOERSEN_DE and cfi[:2] in CFI_ANLEIHE and (not ende or ende >= heute):
                        d = el.find(NS + "DebtInstrmAttrbts")
                        r = {"mic": mic, "name": g.findtext(NS + "FullNm") or "", "cfi": cfi,
                             "fisn": g.findtext(NS + "ShrtNm") or "",   # Kurzname nach ISO 18774: „EMITTENT/KUPON ART JJJJMMTT …“
                             "ccy": g.findtext(NS + "NtnlCcy") or "", "lei": el.findtext(NS + "Issr") or ""}
                        r["ftd"] = (el.findtext(f"{NS}TradgVnRltdAttrbts/{NS}FrstTradDt") or "")[:10]
                        if d is not None:
                            r["vol"] = d.findtext(NS + "TtlIssdNmnlAmt")
                            r["mat"] = d.findtext(NS + "MtrtyDt") or ""
                            r["stk"] = d.findtext(NS + "NmnlValPerUnit")
                            r["fx"] = d.findtext(f"{NS}IntrstRate/{NS}Fxd")
                            fg = d.find(f"{NS}IntrstRate/{NS}Fltg")
                            r["fl"] = fg is not None
                            if fg is not None:
                                ref, term = fg.find(NS + "RefRate"), fg.find(NS + "Term")
                                r["fld"] = [(ref.findtext(NS + "Indx") or ref.findtext(NS + "Nm") or "") if ref is not None else "",
                                            (term.findtext(NS + "Unit") or "")[:1] if term is not None else "",
                                            ganz(term.findtext(NS + "Val")) if term is not None else None,
                                            ganz(fg.findtext(NS + "BsisPtSprd"))]
                            r["snr"] = d.findtext(NS + "DebtSnrty") or ""
                        je_isin[g.findtext(NS + "Id")].append(r)
                    el.clear()
        print(f"FIRDS {link.rsplit('/', 1)[-1]}: {len(je_isin)} Anleihen bisher")
    return je_isin


# ---------------------------------------------------------------- GLEIF
def gleif(leis: list[str]) -> dict[str, dict]:
    """LEI → {name, land, kat, sub} (je Anfrage 200 LEIs)."""
    out = {}
    for i in range(0, len(leis), 200):
        q = urllib.parse.urlencode({"filter[lei]": ",".join(leis[i:i + 200]), "page[size]": 200})
        d = json.loads(get_with_retry(GLEIF_API + q, headers={**UA, "Accept": "application/vnd.api+json"}, timeout=60))
        for x in d.get("data", []):
            e = x["attributes"]["entity"]
            out[x["id"]] = {"name": e["legalName"]["name"], "land": e["legalAddress"]["country"],
                            "kat": e.get("category"), "sub": e.get("subCategory")}
    return out


def konzernmuetter(leis: set[str]) -> dict[str, str]:
    """LEI → LEI der Konzernmutter (ultimativ, sonst direkt) aus der GLEIF-Beziehungsdatei."""
    lokal = os.environ.get("FIXTURE_DIR")
    if lokal and Path(lokal, "gleif-rr.csv.zip").exists():
        daten = Path(lokal, "gleif-rr.csv.zip").read_bytes()
    else:
        url = json.loads(get_with_retry(GLEIF_GC, headers=UA, timeout=60))["data"]["rr"]["full_file"]["csv"]["url"]
        daten = get_with_retry(url, headers=UA, timeout=300)
    ult, direkt = {}, {}
    with tempfile.TemporaryFile() as tmp:
        tmp.write(daten)
        tmp.seek(0)
        with zipfile.ZipFile(tmp) as z:
            with z.open(z.namelist()[0]) as f:
                r = csv.reader(io.TextIOWrapper(f, encoding="utf-8"))
                kopf = next(r)
                i_s, i_e = kopf.index("Relationship.StartNode.NodeID"), kopf.index("Relationship.EndNode.NodeID")
                i_t, i_st = kopf.index("Relationship.RelationshipType"), kopf.index("Relationship.RelationshipStatus")
                for row in r:
                    if row[i_st] != "ACTIVE" or row[i_s] not in leis:
                        continue
                    if row[i_t] == "IS_ULTIMATELY_CONSOLIDATED_BY":
                        ult[row[i_s]] = row[i_e]
                    elif row[i_t] == "IS_DIRECTLY_CONSOLIDATED_BY":
                        direkt[row[i_s]] = row[i_e]
    return {lei: ult.get(lei) or direkt[lei] for lei in set(ult) | set(direkt)}


def land(lei: str, k: int, register: dict, mutter: dict, cfi4: collections.Counter) -> str:
    """ISO-Code des Konzernsitzes; Staaten: der Staat; supranationale Institutionen: INT."""
    info = register.get(lei) or {}
    if info.get("kat") == "INTERNATIONAL_ORGANIZATION" or SUPRANATIONAL.search(info.get("name", "")) \
            or cfi4["C"] * 2 > sum(cfi4.values()):
        return "INT"
    if k != 0 and lei in mutter:
        m = register.get(mutter[lei]) or {}
        if m.get("kat") == "INTERNATIONAL_ORGANIZATION":
            return "INT"
        if m.get("land"):
            return m["land"]
    return info.get("land") or ""


def einstufen(lei: str, info: dict | None, namen: list[tuple[str, str]], cfi4: collections.Counter) -> tuple[int, str]:
    """(Art-Index, Zusatz-Suchwörter) für einen Emittenten."""
    info = info or {}
    land = info.get("land", "")
    if any(land_im_namen(n, ccy, land) for n, ccy in namen) or (
            info.get("sub") == "CENTRAL_GOVERNMENT" and not AGENTUR.search(info.get("name", ""))):
        worte = [LAENDER.get(land, "")] + ALIAS.get(land, [])
        return 0, " ".join(w for w in worte if w)
    if info.get("kat") in ("RESIDENT_GOVERNMENT_ENTITY", "INTERNATIONAL_ORGANIZATION"):
        return 1, ""
    if (cfi4["T"] + cfi4["C"]) * 2 > sum(cfi4.values()):
        return 1, ""
    return 2, ""


# ---------------------------------------------------------------- Aufbau
def zahl(s):
    try:
        v = float(s)
    except (TypeError, ValueError):
        return None
    return v if v > 0 else None


def ganz(s):
    """Ganze Zahl (auch 0) oder None."""
    try:
        return int(round(float(s)))
    except (TypeError, ValueError):
        return None


def anleihe(isin: str, rs: list[dict]) -> dict:
    """Eine Zeile aus den Datensätzen aller Handelsplätze."""
    def namenswahl():
        for gruppe in NAME_RANG:
            kandidaten = [r["name"] for r in rs if r["mic"] in gruppe and r["name"]]
            gut = [n for n in kandidaten if n != n.upper() and ohne_praefix(n, rs[0]["ccy"]) == n]
            if gut or kandidaten:
                return collections.Counter(gut or kandidaten).most_common(1)[0][0]
        return collections.Counter(r["name"] for r in rs).most_common(1)[0][0]
    mics = {r["mic"] for r in rs}
    fx = next((r["fx"] for r in rs if r.get("fx") is not None), None)
    stk = collections.Counter(zahl(r.get("stk")) for r in rs if zahl(r.get("stk")))
    vols = [zahl(r.get("vol")) for r in rs if zahl(r.get("vol"))]
    return {"isin": isin, "name": namenswahl(), "ccy": rs[0]["ccy"],
            "kupon": round(float(fx), 4) if fx is not None else ("var" if any(r.get("fl") for r in rs) else None),
            "faellig": max((r.get("mat") or "" for r in rs), default=""),
            "vol": int(max(vols)) if vols else None,
            "stk": stk.most_common(1)[0][0] if stk else None,
            "boerse": 1 if mics & STUTTGART else 2 if mics & FRANKFURT else 0,
            "zins": zinsart(fx, any(r.get("fl") for r in rs), rs[0]["cfi"]),
            "lei": rs[0]["lei"], "cfi4": rs[0]["cfi"][3:4], "mehr": mehr(rs),
            "fisn": collections.Counter(r["fisn"] for r in rs if r.get("fisn")).most_common(1)[0][0] if any(r.get("fisn") for r in rs) else "",
            "belege": belege([r["name"] for r in rs if r.get("name")])}


RANG = {"SNDB": "S", "SBOD": "U", "JUND": "J", "MZZD": "M"}


def mehr(rs: list[dict]) -> list:
    """["<rang><rueckzahlung><garantie>", ausgabe, floater?] – siehe Kopf der Datei."""
    cfi = rs[0]["cfi"]
    snr = collections.Counter(RANG.get(r.get("snr") or "", "") for r in rs)
    snr.pop("", None)
    rang = snr.most_common(1)[0][0] if snr else ""
    rz = cfi[4:5] if cfi[4:5] in "FGCDABTLPQR" and cfi[4:5] else ""
    gar = cfi[3:4] if cfi[3:4] in "TGSUPNOQJC" and cfi[3:4] else ""
    fld = next((r["fld"] for r in rs if r.get("fld")), None)
    if fld:
        fld = list(fld)
    ftd = [r["ftd"] for r in rs if r.get("ftd")]
    return [(rang or "-") + (rz or "-") + (gar or "-"), min(ftd) if ftd else ""] + ([fld] if fld else [])


def zinsart(fx, floating: bool, cfi: str):
    """0 fest · 1 variabel · 2 Nullkupon – aus dem gemeldeten Zinssatz, sonst dem CFI-Code
    (3. Stelle: F fest, Z null, V variabel)."""
    if fx is not None:
        try:
            return 2 if float(fx) == 0 else 0
        except ValueError:
            pass
    if floating:
        return 1
    return {"F": 0, "Z": 2, "V": 1}.get(cfi[2:3], 1)


def zahl_json(v):
    if v is None or isinstance(v, str):
        return v
    return int(v) if float(v).is_integer() else v


def schreiben(meta: dict, rows: list[list]) -> None:
    """Eine Anleihe je Zeile (kleine Git-Diffs), atomar."""
    kopf = json.dumps(meta, ensure_ascii=False, separators=(",", ":"))[:-1]
    text = kopf + ',"rows":[\n' + ",\n".join(json.dumps(r, ensure_ascii=False, separators=(",", ":")) for r in rows) + "\n]}\n"
    tmp = OUT.with_name(OUT.name + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, OUT)


def teil(isin: str) -> str:
    """Teildatei einer ISIN (zwei Hex-Ziffern) – identisch in update_kurse.py und site.js (MC.teil)."""
    h = 0
    for ch in isin:
        h = (h * 31 + ord(ch)) % 65536
    return f"{h % 256:02x}"


def teildateien_schreiben(meta: dict, rows: list[list]) -> None:
    """anleihen/<hh>.json für die Steckbrief-Seite: Emittentenname statt Index, ohne ISIN in der Zeile."""
    ordner = OUT.parent / "anleihen"
    ordner.mkdir(exist_ok=True)
    emi = meta["emittenten"]
    teile = collections.defaultdict(dict)
    for r in rows:
        teile[teil(r[0])][r[0]] = r[1:9] + [emi[r[9]] if r[9] < len(emi) else ""] + r[10:]
    kopf = {k: meta[k] for k in ("stand", "rang", "rueckzahlung", "garantie")}
    for t in (f"{i:02x}" for i in range(256)):
        d = {**kopf, "rows": dict(sorted(teile.get(t, {}).items()))}
        pfad = ordner / f"{t}.json"
        tmp = pfad.with_name(pfad.name + ".tmp")
        tmp.write_text(json.dumps(d, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
        os.replace(tmp, pfad)


# ---------------------------------------------------------------- Plausibilität
# Währungen mit zweistelligen Leitzinsen: dort sind Kupons über 20 % echt (türkische Lira 30–45 %)
HOCHZINS = {"TRY", "ARS", "RUB", "EGP", "NGN", "KZT", "UAH", "GHS", "ZMW", "UZS", "ETB", "KES", "UGX", "VES", "IRR", "BRL"}
KUPON_MAX = 20.0
FLR_NAME = re.compile(r"FLR\b|floating|\bFRN\b|variab|\bvar\.", re.IGNORECASE)
UNBEFRISTET_NAME = re.compile(r"\b(?:und\w*|unb\w*|unl\w*|un|perp\w*|open end|ewig)\b", re.IGNORECASE)   # Und., Undated, unb., Unl., perp
KLAMMER = re.compile(r"(?:(?<!\d)(\d{4}|\d{2}))?\s*\(([^()]*)\)")


def jahre_im_namen(name: str, reg_jahr: int | None) -> tuple[int | None, int | None]:
    """(Ausgabejahr, Fälligkeitsjahr) laut WM-Name: „… 2019(24/29)“ → (2019, 2029), „v.21(26)“ → (2021, 2026).
    Fälligkeitsjahr None, wenn unbefristet („Und.“, „unb.“, „perp“) oder ohne Klammer mit Jahreszahl.
    Zweistellige Jahre gelten als 20xx (ab 70: 19xx); passt die Endung zum Registerjahr („1997(97)“ und
    Register 2097), gilt das Registerjahr."""
    def jahr(t: str, faelligkeit: bool = False) -> int:
        v = int(t)
        if len(t) == 4:
            return v
        if faelligkeit and reg_jahr and reg_jahr % 100 == v:
            return reg_jahr
        return 2000 + v if v < 70 else 1900 + v
    for m in reversed(list(KLAMMER.finditer(name or ""))):
        innen = m.group(2)
        if UNBEFRISTET_NAME.search(innen):
            return None, None
        ys = re.findall(r"(?<!\d)(\d{4}|\d{2})(?!\d)", innen)
        if ys:
            return (jahr(m.group(1)) if m.group(1) else None), jahr(ys[-1], True)
    return None, None


def ueberfaellig(row: list, heute: datetime.date) -> bool:
    """Fällig, aber nicht zurückgezahlt: Register ohne echte Fälligkeit (leer bzw. Platzhalter ab 2090), der
    Name nennt ein vergangenes Fälligkeitsjahr, das nach dem Ausgabejahr liegt."""
    reg = int(row[5][:4]) if row[5] else None
    if reg is not None and reg < 2090:
        return False
    ausgabe, faellig = jahre_im_namen(row[1], reg)
    if faellig is None or faellig >= heute.year:
        return False
    if ausgabe is not None and faellig <= ausgabe:
        return False      # z. B. „21(21/21)“: Fälligkeit 3021, im Namen nur zweistellig – unklar, bleibt
    return reg is None or reg != faellig


FISN_RE = re.compile(r"/\s*(\d+(?:\.\d+)?)?\s*(?:[A-Z]+\s+)*?(\d{8})(?!\d)")
# Kupon und Jahre in den Namen der übrigen Handelsplätze (Bloomberg-Stil „VOD 3 7/8 07/03/38“, „HESSEN 0 09/22/27“,
# „EBKG 5.25 23/01/84“, „EnergieBadWurtt 5 25% 23 01 2084“, „… 3.875 per cent. Notes due 3 July 2038“)
KUPON_BRUCH = re.compile(r"(?<![\d./])(\d{1,2})\s+(\d)/(\d)(?![\d/])")
KUPON_DEZ = re.compile(r"(?<![\d.,/-])(\d{1,2})[.,](\d{1,4})(?![\d/])")
KUPON_GANZ = re.compile(r"(?<![\d.,/-])(\d{1,2})\s(?=\d{1,2}/\d{1,2}/\d{2,4}\b)")
KUPON_PROZENT = re.compile(r"(?<![\d.,/-])(\d{1,2})\s(\d{1,3})%")
JAHR_DATUM = re.compile(r"\b\d{1,2}/\d{1,2}/(\d{2}|\d{4})\b")
JAHR_4 = re.compile(r"(?<!\d)((?:19|20|21)\d{2})(?!\d)")


def belege(namen: list[str]) -> dict:
    """{"kupons": [...], "jahre": [...]} – alles, was die Handelsplatz-Namen an Kupons und Jahren nennen."""
    kupons, jahre = set(), set()
    for n in namen:
        for m in KUPON_BRUCH.finditer(n):
            kupons.add(round(int(m.group(1)) + int(m.group(2)) / int(m.group(3)), 4))
        for m in KUPON_PROZENT.finditer(n):
            kupons.add(round(float(f"{m.group(1)}.{m.group(2)}"), 4))
        for m in KUPON_DEZ.finditer(n):
            kupons.add(round(float(f"{m.group(1)}.{m.group(2)}"), 4))
        for m in KUPON_GANZ.finditer(n):
            kupons.add(float(m.group(1)))
        for m in JAHR_DATUM.finditer(n):
            j = int(m.group(1))
            jahre.add(j if j > 99 else 2000 + j)   # zweistellig immer 20xx: keine laufende Anleihe ist vor 2000 fällig („84“ = 2084)
        for m in JAHR_4.finditer(n):
            jahre.add(int(m.group(1)))
    return {"kupons": sorted(kupons), "jahre": sorted(jahre)}


def fisn_werte(fisn: str) -> tuple[float | None, str | None]:
    """(Kupon, Fälligkeit) aus dem Kurznamen nach ISO 18774 („VODAFONE INTER/3.875 MTN 20380703“ → (3.875, "2038-07-03");
    „HESSEN, LAND/ LSA 20270922 S.2008“ → (None, "2027-09-22") – Nullkupons und Floater nennen keinen Satz)."""
    m = FISN_RE.search(fisn or "")
    if not m:
        return None, None
    kupon = float(m.group(1)) if m.group(1) else None
    try:
        d = datetime.date(int(m.group(2)[:4]), int(m.group(2)[4:6]), int(m.group(2)[6:]))
        faellig = d.isoformat() if d.year < int(UNBEFRISTET) else None
    except ValueError:
        faellig = None
    return kupon, faellig


def pruefung(row: list, fisn: str | None, heute: datetime.date, alt: dict | None = None, beleg: dict | None = None) -> dict:
    """Befunde je Anleihe (Feld pruef) – die Registerwerte bleiben, die Anzeige weist auf den Widerspruch hin und
    die Kursdatei rechnet keine Rendite (_common.ohne_rendite). Ein Befund braucht zwei Quellen gegen das
    Registerfeld (Kurzname nach ISO 18774 UND ein Handelsplatz-Name bzw. der WM-Name), weil der Kurzname allein
    nicht zuverlässig ist (Euronext meldet für viele französische Anleihen „0.0“ oder „1.0“ als Kupon). Schlüssel:
      kuponFisn    Kupon laut Kurzname, wenn er vom Register abweicht und ein Handelsplatz-Name ihn bestätigt –
                   oder das Register 0 meldet und der Kurzname einen Satz nennt (Nullkupons nennen keinen)
      faelligFisn  Fälligkeit laut Kurzname, mehr als 31 Tage vom Register entfernt und von einem Namen bestätigt
      faelligName  Fälligkeitsjahr laut WM-Name, wenn es vom Registerjahr abweicht und Kurzname oder ein anderer
                   Name es bestätigt – auch: Register ohne Fälligkeit, Name nennt ein vergangenes Jahr (fällig,
                   nicht zurückgezahlt – Libanon 2006(21)), sofern der Kurzname nicht widerspricht
      zinsName     "var": Name sagt FLR/variabel, Register meldet Nullkupon (Satz 0 – der Satz eines Floaters ist unbekannt)
      kuponHoch    true: Kupon über 100 % oder über 20 % außerhalb von Hochzinswährungen (Faktor 10/1000)
    fisn None (--bereinigen ohne Abruf): die Kurzname-Befunde aus alt bleiben."""
    p = {}
    kupon, reg = row[4], row[5]
    reg_jahr = int(reg[:4]) if reg else None
    ausgabe, name_jahr = jahre_im_namen(row[1], reg_jahr)
    kupons = set((beleg or {}).get("kupons", []))
    jahre = set((beleg or {}).get("jahre", []))
    fk = ff = None
    if fisn is None:
        p.update({k: v for k, v in (alt or {}).items() if k in ("kuponFisn", "faelligFisn")})
        if alt and alt.get("faelligFisn"):
            ff = alt["faelligFisn"]
    else:
        fk, ff = fisn_werte(fisn)
        if fk is not None and isinstance(kupon, (int, float)) and round(kupon, 2) != round(fk, 2):
            if (kupon == 0 and fk > 0) or any(abs(c - fk) < 0.006 for c in kupons):
                p["kuponFisn"] = fk
        if ff is not None:
            ff_jahr = int(ff[:4])
            tage = abs((datetime.date.fromisoformat(ff) - datetime.date.fromisoformat(reg)).days) if reg else None
            if (tage is None or tage > 31) and ff_jahr != reg_jahr and (ff_jahr in jahre or ff_jahr == name_jahr):
                p["faelligFisn"] = ff
    ff_jahr = int(ff[:4]) if ff else None
    if name_jahr is not None and (ausgabe is None or name_jahr > ausgabe):
        if reg_jahr is None and name_jahr < heute.year and (ff_jahr is None or ff_jahr == name_jahr):
            p["faelligName"] = name_jahr
        elif reg_jahr is not None and name_jahr != reg_jahr and (ff_jahr == name_jahr or (ff_jahr is None and name_jahr in jahre)):
            p["faelligName"] = name_jahr
    if row[10] == 2 and FLR_NAME.search(row[1]):
        p["zinsName"] = "var"   # nur bei gemeldetem Nullkupon: ein fester Anfangssatz (Fix-to-Float) ist kein Widerspruch
    if isinstance(kupon, (int, float)) and (kupon > 100 or (kupon > KUPON_MAX and row[3] not in HOCHZINS)):
        p["kuponHoch"] = True
    return p


def pruefen(rows: list[list], fisns: dict[str, str] | None, heute: datetime.date, belege: dict[str, dict] | None = None) -> tuple[list[list], collections.Counter]:
    """Feld pruef (Index 14) für alle Zeilen setzen; fisns None = ohne Abruf (Kurzname-Befunde bleiben)."""
    n = collections.Counter()
    for r in rows:
        alt = r[14] if len(r) > 14 and isinstance(r[14], dict) else None
        p = pruefung(r, fisns.get(r[0], "") if fisns is not None else None, heute, alt, (belege or {}).get(r[0]))
        for k in p:
            n[k] += 1
        if len(r) > 14:
            r[14] = p
        else:
            r.append(p)
    n["Anleihen mit Befund"] = sum(1 for r in rows if r[14])
    return rows, n


def bereinigen(heute: datetime.date) -> int:
    """--bereinigen: Plausibilitätsregeln auf den vorhandenen Index anwenden (ohne Abruf) und Teildateien neu schreiben."""
    try:
        alt = json.loads(OUT.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        log_err(f"anleihen-index.json unlesbar ({e}) – nichts bereinigt.")
        return 1
    rows, n = pruefen(alt.get("rows", []), None, heute)
    meta = {k: v for k, v in alt.items() if k != "rows"}
    meta.update({"updated": today_iso(), "updatedAt": now_iso(), "anzahl": len(rows)})
    schreiben(meta, rows)
    teildateien_schreiben(meta, rows)
    print(f"anleihen-index.json geprüft: {len(rows)} Anleihen – " + (", ".join(f"{k} {v}" for k, v in n.items()) or "kein Befund"))
    return 0


def main() -> int:
    heute = datetime.date.today()
    if "--bereinigen" in sys.argv:
        return bereinigen(heute)
    alt = {}
    if OUT.exists():
        try:
            alt = json.loads(OUT.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as e:
            log_err(f"anleihen-index.json unlesbar ({e}) – wird neu aufgebaut.")
    stand_alt = alt.get("stand", "1970-01-01")
    if "--force" not in sys.argv and (heute - datetime.date.fromisoformat(stand_alt)).days < 7:
        print(f"Index vom {stand_alt} ist jünger als 7 Tage – kein Abruf.")
        return 0

    serie = neueste_gesamtdatei(heute)
    if not serie:
        log_err("FIRDS: keine vollständige Gesamtdatei (FULINS_D) der letzten 14 Tage gefunden.")
        return 1
    stand, links = serie
    if stand <= stand_alt and "--force" not in sys.argv:
        print(f"Keine neuere Gesamtdatei als {stand_alt} – Index bleibt.")
        return 0

    je_isin = lies_firds(links, heute.isoformat())
    zeilen = [a for a in (anleihe(i, rs) for i, rs in je_isin.items())
              if not a["faellig"] or a["faellig"] >= heute.isoformat()]
    for a in zeilen:
        if a["faellig"] >= UNBEFRISTET:
            a["faellig"] = ""

    leis = sorted({a["lei"] for a in zeilen if a["lei"]})
    try:
        register = gleif(leis)
    except Exception as e:  # noqa: BLE001 – ohne Einstufung kein neuer Index
        log_err(f"GLEIF nicht erreichbar ({e}) – Index bleibt auf dem Stand {stand_alt}.")
        return 1
    namen = collections.defaultdict(list)
    cfi4 = collections.defaultdict(collections.Counter)
    for a in zeilen:
        namen[a["lei"]].append((a["name"], a["ccy"]))
        cfi4[a["lei"]][a["cfi4"]] += 1
    art = {lei: einstufen(lei, register.get(lei), namen[lei], cfi4[lei]) for lei in namen}

    try:
        mutter = konzernmuetter(set(namen))
        fehlend = sorted(set(mutter.values()) - set(register))
        register.update(gleif(fehlend))
    except Exception as e:  # noqa: BLE001 – ohne Mütter gilt der Sitz des Emittenten
        log_err(f"GLEIF-Beziehungsdatei nicht verfügbar ({e}) – Land = Sitz des Emittenten.")
        mutter = {}
    laender = {lei: land(lei, art[lei][0], register, mutter, cfi4[lei]) for lei in namen}

    # Plausibilität: ein kaputter Abruf darf den Index nicht leeren
    n_alt = len(alt.get("rows", []))
    if n_alt and len(zeilen) < 0.7 * n_alt:
        log_err(f"Nur {len(zeilen)} Anleihen statt zuvor {n_alt} – Index bleibt unverändert.")
        return 1

    emittenten = [""]
    emi_idx = {}
    for lei in sorted(namen):
        n = (register.get(lei) or {}).get("name", "")
        if n:
            n = " ".join([n] + [w for rx, w in KUERZEL if rx.search(n)])
            emi_idx[lei] = len(emittenten)
            emittenten.append(n)
    rows = []
    for a in sorted(zeilen, key=lambda a: a["isin"]):
        k, extra = art.get(a["lei"], (2, ""))
        if k == 0 and a["isin"][:2] in STUECK_STAAT:
            a["stk"] = STUECK_STAAT[a["isin"][:2]]
        row = [a["isin"], a["name"], k, a["ccy"], zahl_json(a["kupon"]), a["faellig"],
               zahl_json(a["vol"]), zahl_json(a["stk"]), a["boerse"], emi_idx.get(a["lei"], 0),
               a["zins"], laender.get(a["lei"], "")]
        extra = " ".join(w for w in extra.split(" ") if w and norm(w) not in norm(a["name"])) if extra else ""
        row.append(extra)
        row.append(a["mehr"])
        rows.append(row)
    rows, bereinigt = pruefen(rows, {a["isin"]: a.get("fisn", "") for a in zeilen}, heute, {a["isin"]: a.get("belege", {}) for a in zeilen})
    zaehler = collections.Counter(r[2] for r in rows)
    meta = {"stand": stand, "updated": today_iso(), "updatedAt": now_iso(),
            "quelle": "ESMA FIRDS (Gesamtdatei Schuldtitel), gefiltert: Anleihen an deutschen Börsen; Einstufung und Konzernsitz über GLEIF",
            "felder": ["isin", "name", "art", "waehrung", "kupon", "faellig", "volumen", "stueckelung", "boerse", "emittent",
                       "zinsart", "land", "extra", "mehr", "pruef"],
            "pruef": {"kuponFisn": "Kupon laut Kurzname (ISO 18774), weicht vom Register ab", "faelligFisn": "Fälligkeit laut Kurzname, weicht vom Register ab",
                      "faelligName": "Fälligkeitsjahr laut Name, weicht vom Register ab (Register ohne Fälligkeit: vermutlich fällig, nicht zurückgezahlt)",
                      "zinsName": "Name sagt variabel (FLR), Register meldet Nullkupon", "kuponHoch": "Kupon unplausibel hoch (Faktor 10/1000)"},
            "mehr": ["rang+rueckzahlung+garantie (je ein Buchstabe, - = unbekannt)", "ausgabe (erster Handelstag)", "floater [referenz, einheit, wert, aufschlag_bp] – nur bei variablem Zins"],
            "rang": {"S": "erstrangig", "U": "nachrangig", "J": "tief nachrangig", "M": "Mezzanine"},
            "rueckzahlung": {"F": "feste Fälligkeit", "G": "feste Fälligkeit, vom Emittenten kündbar", "C": "feste Fälligkeit, vom Anleger kündbar",
                             "D": "feste Fälligkeit, von beiden Seiten kündbar", "A": "Tilgung in Raten", "B": "Tilgung in Raten, vom Emittenten kündbar",
                             "T": "Tilgung in Raten, vom Anleger kündbar", "L": "Tilgung in Raten, von beiden Seiten kündbar",
                             "P": "unbefristet", "Q": "unbefristet, vom Emittenten kündbar", "R": "verlängerbar"},
            "garantie": {"T": "staatlich garantiert", "G": "garantiert durch Dritte (z. B. Konzernmutter)", "S": "besichert", "U": "unbesichert", "P": "mit Negativklausel",
                         "N": "erstrangig", "O": "nachrangig", "Q": "nachrangig (junior)", "J": "tief nachrangig", "C": "supranational"},
            "zinsart": ["fest", "variabel", "Nullkupon"],
            "art": ART, "boerse": BOERSE, "anzahl": len(rows), "emittenten": emittenten}
    schreiben(meta, rows)
    teildateien_schreiben(meta, rows)
    print(f"anleihen-index.json: {len(rows)} Anleihen (Stand {stand}) – "
          + ", ".join(f"{ART[k]} {zaehler[k]}" for k in range(3))
          + (" · Prüfung: " + ", ".join(f"{k} {v}" for k, v in bereinigt.items()) if bereinigt else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
