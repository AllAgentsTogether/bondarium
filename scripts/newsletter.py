#!/usr/bin/env python3
"""newsletter.py – baut die Ausgabe des wöchentlichen „Wochenbriefs“ aus den Daten des Datenlaufs (seit 02.10.2026).

Vorgabe des Betreibers: Der Newsletter entsteht vollautomatisch – keine Ausgabe braucht Handarbeit, kein Text wird von Hand
geschrieben. Jeder Abschnitt kommt aus einer Datei des Datenlaufs oder aus einer festen Regel (docs/NEWSLETTER.md):

  Überschrift, Einleitung   Regel aus der Rendite der Bundesanleihe mit rund zehn Jahren Restlaufzeit: ab SCHWELLE Prozentpunkten
                            Veränderung zur Vorwoche „gestiegen“ bzw. „gefallen“, sonst „kaum verändert“
  Zinsen der Woche          kurse/bund/<ISIN>.json (Tagesrenditen der Bundesbank: Papier mit rund 2 und rund 10 Jahren Restlaufzeit,
                            heute und fünf Börsentage zuvor), ezb.json (Einlagesatz), renditen.json (USA 10 Jahre)
  Meistgehandelt            top10-staatsanleihen-laufzeit.json, top10-unternehmensanleihen-laufzeit.json: je drei nach Umsatz
  Deine Merkliste           je Abonnent – das setzt konto.php beim Versand ein (Platzhalter {{MERKLISTE}}); die Zahlen je Anleihe
                            stehen in newsletter/anleihen.json
  Aus der Akademie          reihum durch die Seiten des Akademie-Menüs (scripts/nav.py), eine je Kalenderwoche; Titel = h1,
                            Text = meta description der Seite
  Neue Seiten               Seiten, die in den letzten sieben Tagen zum ersten Mal da waren (newsletter/seiten.json merkt sich je
                            Seite den ersten Tag); ohne neue Seite entfällt der Abschnitt

Schreibweise je Anleihe (seit 03.10.2026, Konzept „Einheitliche Anleihen-Angaben“, docs/ANLEIHEN-ANGABEN.md): erste Zeile der Titel
(„Deutschland 2,60 % 2033“ – Kurzname, Kupon, Fälligkeitsjahr wie auf der Website), zweite Zeile die Kernzahlen in der Reihenfolge der
Website-Tabellen („Rendite 3,85 % · Restlaufzeit 4,2 Jahre (fällig 15.08.2033) · Kurs 98,50 %“, nur vorhandene Angaben), danach, was
der Abschnitt meldet. Veränderungen mit Vorzeichen in Prozentpunkten („+0,12 Pkt. zur Vorwoche“), Kupon „variabel“/„Nullkupon“ als
Wort. Namen und Schreibweisen kommen aus scripts/_common.py (kurz_name, titel_text, pct_text, kurs_text, pkt_text …), Spaltenköpfe
aus dem Feldkatalog in felder.js. Die HTML-Fassung behält das geschützte Leerzeichen vor „%“ und „Pkt.“, die Textfassung nicht.

Schreibt in den Ordner newsletter/ (konto.php liest ihn auf dem Server; per .htaccess nicht abrufbar):
  ausgabe.json    {"kw": "2026-W40", "erstellt": Datum, "versand": true|false, "grund": …, "warnen": true|false, "betreff", "text",
                   "html", "merk": Vorlagen für den Abschnitt „Deine Merkliste“, "muster": drei ISINs für die Probe an den Betreiber}
                  – Text und HTML mit den Platzhaltern {{MERKLISTE}} und {{ABMELDEN}}. Wird nicht committet.
  anleihen.json   {ISIN: [Feld 0 … 10]} für alle Anleihen mit aktuellem Kurs (suchindex.json). Die eine Quelle für Namen und Zahlen
                  der E-Mails (Wochenbrief-Merkliste und Meldungen in konto.php, Erinnerung vor der Fälligkeit in erinnerung.php)
                  und für den nächsten Zinstermin in „Mein Bondarium“ (konto.php, aktion=besuch). Wird nicht committet (~5 MB).
                     0  Name          Kurzname wie auf der Website (_common.kurz_name: Staat → Land laut Katalog, sonst Emittent
                                      ohne Rechtsform)
                     1  Kupon-Text    „3,50 %“, „3,625 %“, „variabel“, „Nullkupon“ (_common.kupon_text)
                     2  Fälligkeit    JJJJ-MM-TT, "" = unbefristet
                     3  Kurs          Schlusskurs in % des Nennwerts
                     4  Rendite       % p. a. oder null (Anzeige-Schutz wie auf der Website)
                     5  Veränderung   Kurs minus Kurs fünf Börsentage zuvor, in Prozentpunkten des Nennwerts, oder null
                     6  Zinstermin    nächster Zinstermin JJJJ-MM-TT (ab heute, höchstens die Fälligkeit – sie zählt mit, der letzte
                                      Zins kommt mit der Rückzahlung) oder null; Rechnung wie im Steckbrief (_common.zinszahlungen)
                     7  Zinsart       0 fest, 1 variabel, 2 Nullkupon                                            (seit 03.10.2026)
                     8  geschätzt     1 = Zinstermin nach der Schätzregel (_common.zinsfrequenz – die Börsenliste nennt für die
                                      Anleihe keine Zinstage), 0 = laut Deutscher Börse oder kein Zinstermin
                  Texte mit geschütztem Leerzeichen (U+00A0) vor „%“ wie auf der Website; Textfassungen setzen ein normales.
                  Titel („Deutschland 2,60 % 2033“) und Restlaufzeit („4,2 Jahre“) stehen bewusst nicht in der Datei (sie wäre 1,5 MB
                  größer): titel_aus() hier und nl_titel()/nl_restlaufzeit() in konto.php bilden sie aus den Feldern 0–2.
                  Neue Felder nur hinten anhängen – konto.php und erinnerung.php lesen nach Stelle.
  seiten.json     {"seiten": {Datei: erster Tag oder ""}} – wird committet (Gedächtnis für „Neue Seiten“).

Versand: nur am VERSANDTAG (Freitag, Zeit Berlin) und nur, wenn die Daten vollständig und frisch sind (pruefen()). Sonst steht
"versand": false mit Grund in der Ausgabe; fällt der Versand am Versandtag wegen der Daten aus, setzt "warnen" eine E-Mail an den
Betreiber in Gang (konto.php). Verschickt wird von konto.php (aktion=newsletter-senden), aufgerufen vom Workflow nach dem Upload.

Aufruf:
  python scripts/newsletter.py                  Ausgabe bauen
  python scripts/newsletter.py --vorschau       zusätzlich newsletter/vorschau.html und vorschau.txt mit Muster-Merkliste
  NEWSLETTER_HEUTE=JJJJ-MM-TT …                 Datum vorgeben (Tests)
  NEWSLETTER_VERSAND=1 …                        Versand unabhängig vom Wochentag freigeben (Tests)
"""
import datetime
import glob
import html
import json
import os
import re
import sys
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import (NBSP, datum_text, felder_katalog, kupon_text, kurs_text, kurz_name, log_err, pct_text, pkt_text,  # noqa: E402
                     restlaufzeit_text, titel_text, write_atomic, zahl_de, zinsplan, zinstermine_laden, zinszahlungen)

ROOT = Path(__file__).resolve().parent.parent
AUS = ROOT / "newsletter"
SEITE = "https://www.bondarium.de/"
VERSANDTAG = 4            # Freitag (Montag = 0)
SCHWELLE = 0.03           # Prozentpunkte: darunter gilt die Bundrendite als „kaum verändert“
KURS_MAX_TAGE = 4         # Kurse älter als so viele Tage → kein Versand
NEU_TAGE = 7              # „Neue Seiten“: erster Tag höchstens so lange her
NEU_MAX = 4
MON = ["Januar", "Februar", "März", "April", "Mai", "Juni", "Juli", "August", "September", "Oktober", "November", "Dezember"]
INK, TXT, GRUEN, TIEF, LINIE, MINUS = "#1A1A19", "#55544F", "#39FF14", "#157C00", "#E7E5DF", "#A2561C"
F = "font-family:Helvetica,Arial,sans-serif;"
FELD = felder_katalog()["felder"]   # Bezeichnungen wie auf der Website („Rendite“, „Restlaufzeit“, „Nächster Zinstermin“ …)


def lade(name, leer=None):
    try:
        return json.loads((ROOT / name).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return leer


def zahl(v, d=2):
    return zahl_de(v, d)


def datum(iso):
    return datum_text(iso)


def jahre_bis(iso, heute):
    """Restlaufzeit in Jahren bis zum Fälligkeitstag (None = unbefristet) – wie MC.felder.jahre auf der Website."""
    return (datetime.date.fromisoformat(iso) - heute).days / 365.25 if iso else None


def kern(rendite, faellig, restlaufzeit, kurs):
    """Zweite Zeile je Anleihe: Kernzahlen in der Reihenfolge der Website-Tabellen, nur vorhandene Angaben –
    „Rendite 3,85 % · Restlaufzeit 4,2 Jahre (fällig 15.08.2033) · Kurs 98,50 %“. Gleiche Regel in konto.php (nl_kern)."""
    teile = [FELD["rendite"]["kurz"] + " " + pct_text(rendite)] if isinstance(rendite, (int, float)) else []
    if restlaufzeit:
        teile.append(FELD["restlaufzeit"]["kurz"] + " " + restlaufzeit + (f" (fällig {datum(faellig)})" if faellig else ""))
    elif faellig:
        teile.append("fällig " + datum(faellig))
    if isinstance(kurs, (int, float)):
        teile.append(FELD["kurs"]["kurz"] + " " + kurs_text(kurs))
    return " · ".join(teile)


def titel_aus(b):
    """Titel aus einer Zeile von anleihen.json: Kurzname, Kupon-Text, Fälligkeitsjahr („Deutschland 2,60 % 2033“) – wie
    _common.titel_text und nl_titel() in konto.php."""
    return f"{b[0]} {b[1]} {b[2][:4] if b[2] else 'unbefristet'}"


def zinstermin_text(b):
    """„Nächster Zinstermin 20.05.2027“ einer Zeile aus anleihen.json, mit „(geschätzt)“ oder „(mit Rückzahlung)“ wie in der
    Spalte der Website; "" ohne Termin. Gleiche Regel in konto.php (nl_zinstermin)."""
    if not b[6]:
        return ""
    zusatz = " (geschätzt)" if len(b) > 8 and b[8] else " (mit Rückzahlung)" if b[6] == b[2] else ""
    return FELD["zinstermin"]["kurz"] + " " + datum(b[6]) + zusatz


def nur_text(s):
    """Textfassung: normales statt geschütztes Leerzeichen."""
    return s.replace(NBSP, " ")


def seite(datei):
    """Titel (h1), Kurzbeschreibung (meta description) und Adresse einer Seite – so, wie sie auf der Website stehen."""
    quelle = (ROOT / datei).read_text(encoding="utf-8")
    h1 = re.search(r"<h1[^>]*>(.*?)</h1>", quelle, re.S)
    d = re.search(r'<meta name="description" content="([^"]*)"', quelle)
    titel = html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", h1.group(1)))).strip() if h1 else ""
    return {"datei": datei, "titel": titel, "text": html.unescape(d.group(1)) if d else "", "link": SEITE + datei,
            "noindex": bool(re.search(r'name="robots" content="[^"]*noindex', quelle))}


# ---------------------------------------------------------------- Daten
def naechster_zinstermin(r, termine, heute):
    """(nächster Zinstermin JJJJ-MM-TT | None, geschätzt 1 | 0) einer Zeile aus suchindex.json (Felder 0–12 wie anleihen-index.json):
    erster Termin ab heute bis zur Fälligkeit; die Fälligkeit selbst zählt (letzter Zins mit der Rückzahlung). Zinstage laut
    Börsenliste (zinstermine.json); fehlen sie, bei festem Kupon über 0 geschätzt (zinsfrequenz, vom Fälligkeitstag rückwärts) –
    dieselbe Rechnung wie im Steckbrief (_common.zinsplan und zinszahlungen, bond.js couponDates). Nullkupon: kein Zinstermin."""
    if not r[5] or r[10] == 2:
        return None, 0
    faellig = datetime.date.fromisoformat(r[5])
    if faellig < heute:
        return None, 0
    freq, tage = zinsplan(r, termine)
    fest = r[10] == 0 and isinstance(r[4], (int, float)) and r[4] > 0
    if not tage and not fest:
        return None, 0   # variabel oder Kupon unbekannt: ohne Börsenliste kein Termin
    try:
        # Valutatag gestern: Ein Termin heute zählt noch als nächster
        _, zahlungen = zinszahlungen(r[4] if fest else 0.0, faellig, heute - datetime.timedelta(days=1), freq, tage)
    except (ValueError, ZeroDivisionError):
        return None, 0
    return (zahlungen[0][0].isoformat(), 0 if tage else 1) if zahlungen else (None, 0)


def anleihen_daten(heute):
    """newsletter/anleihen.json: {ISIN: [Name, Kupon-Text, Fälligkeit, Kurs, Rendite|None, Veränderung zur Vorwoche|None,
    nächster Zinstermin|None, Zinsart, Titel, Restlaufzeit, Zinstermin geschätzt 1|0]} – Felder im Kopf der Datei."""
    si = lade("suchindex.json", {}) or {}
    emi, termine = si.get("emittenten") or [], zinstermine_laden()
    # Kurs vor fünf Börsentagen je Anleihe aus dem Kursverlauf des laufenden Jahres
    vorwoche = {}
    for f in glob.glob(str(ROOT / "kurse" / str(heute.year) / "*.json")):
        try:
            v = json.loads(Path(f).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        n = len(v.get("tage") or [])
        if n < 6:
            continue
        for isin, k in (v.get("k") or {}).items():
            if len(k) == n and k[n - 6] is not None:
                vorwoche[isin] = k[n - 6]
    aus = {}
    for r in si.get("rows") or []:
        isin, kurs, rend = r[0], r[15], r[16]
        if not isinstance(kurs, (int, float)):
            continue
        jahre = (datetime.date.fromisoformat(r[5]) - heute).days / 365.25 if r[5] else 99
        # Anzeige-Schutz wie auf der Website: Kurs ohne Umsatz mit unplausibler Rendite, Datenprüfung mit Befund → keine Rendite
        taxe = not r[19] and r[18] != "B"
        if not isinstance(rend, (int, float)) or r[14] or (taxe and (rend < 0 or rend > 15 or (isinstance(r[21], (int, float)) and r[21] < -1) or (jahre < 0.25 and rend > 8))):
            rend = None
        # Kurzname und Titel wie auf der Website; die Emittenten im Suchindex sind schon lesbar geschrieben
        name = kurz_name(emi[r[9]] if isinstance(r[9], int) and 0 <= r[9] < len(emi) else "", r[2], r[11], r[1])
        zt, geschaetzt = naechster_zinstermin(r, termine, heute)
        diff = round(kurs - vorwoche[isin], 3) if isin in vorwoche else None
        aus[isin] = [name, kupon_text(r[4], r[10]), r[5] or "", kurs, None if rend is None else round(rend, 2), diff, zt, r[10], geschaetzt]
    return aus, si.get("kstand") or ""


def bund(heute):
    """Bundeswertpapier mit rund 2 und rund 10 Jahren Restlaufzeit: Rendite laut Bundesbank heute und fünf Börsentage davor."""
    idx = {r[0]: r for r in (lade("anleihen-index.json", {}) or {}).get("rows", [])}
    kand = []
    for f in glob.glob(str(ROOT / "kurse" / "bund" / "*.json")):
        try:
            v = json.loads(Path(f).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        r = idx.get(v.get("isin") or Path(f).stem)
        if not r or not r[5] or re.search(r"infl|index", r[1], re.I) or len(v.get("r") or []) < 6 or v["r"][-1] is None or v["r"][-6] is None:
            continue
        kand.append(((datetime.date.fromisoformat(r[5]) - heute).days / 365.25, r, v))
    aus = {}
    for ziel in (2, 10):
        nah = [k for k in kand if abs(k[0] - ziel) <= 1.5]
        if not nah:
            return None
        _, r, v = min(nah, key=lambda k: abs(k[0] - ziel))
        aus[ziel] = {"r": v["r"][-1], "d": v["r"][-1] - v["r"][-6], "tag": v["t"][-1], "vor": v["t"][-6], "kupon": r[4], "zinsart": r[10], "jahr": r[5][:4],
                     "art": "Bundesobligation" if "obl" in r[1].lower() else "Bundesschatzanweisung" if "schatz" in r[1].lower() else "Bundesanleihe"}
    return aus


def meist(datei, n=3):
    """Fenster und die n meistgehandelten Anleihen mit Rendite einer Top-10-Datei (Zeilen mit Kurzname „kurz“, update_top10.py)."""
    t = lade(datei, {}) or {}
    alle = [x for l in (t.get("gruppen") or {}).values() for x in l if isinstance(x.get("rendite"), (int, float))]
    return t.get("fenster") or {}, sorted(alle, key=lambda x: -x.get("um", 0))[:n]


def akademie(kw):
    """Seite des Akademie-Menüs für diese Kalenderwoche (reihum); None, wenn das Menü nicht lesbar ist."""
    nav = (ROOT / "scripts" / "nav.py").read_text(encoding="utf-8")
    try:
        block = nav[nav.index("AKADEMIE = ("):nav.index("ANLEIHEN = (")]
    except ValueError:
        return None
    dateien = [d for _, d in re.findall(r'\("([^"]+)", "([a-z0-9-]+\.html)"\)', block) if (ROOT / d).exists()]
    for i in range(len(dateien)):   # Seite ohne Titel oder Kurztext überspringen
        s = seite(dateien[(kw + i) % len(dateien)])
        if s["titel"] and s["text"]:
            return s
    return None


def neue_seiten(heute):
    """Seiten, die in den letzten NEU_TAGE zum ersten Mal da waren; führt newsletter/seiten.json fort."""
    pfad = AUS / "seiten.json"
    stand = lade("newsletter/seiten.json", None)
    erstmals = stand is None
    bekannt = dict((stand or {}).get("seiten") or {})
    da = {}
    for p in sorted(ROOT.glob("*.html")):
        if p.name == "404.html":
            continue
        s = seite(p.name)
        if s["noindex"] or not s["text"] or not s["titel"]:
            continue
        da[p.name] = s
        if p.name not in bekannt:
            bekannt[p.name] = "" if erstmals else heute.isoformat()   # beim allerersten Lauf gilt nichts als neu
    bekannt = {k: v for k, v in sorted(bekannt.items()) if k in da}
    if (stand or {}).get("seiten") != bekannt:
        write_atomic(pfad, {"seiten": bekannt}, indent=0)
    grenze = (heute - datetime.timedelta(days=NEU_TAGE)).isoformat()
    neu = sorted((d for d, tag in bekannt.items() if tag and tag >= grenze), key=lambda d: (bekannt[d], d), reverse=True)
    return [da[d] for d in neu[:NEU_MAX]]


# ---------------------------------------------------------------- Bausteine der HTML-Fassung (Tabellen, Inline-Stile, 600 px)
e = html.escape


def h2(s):
    return f'<tr><td style="padding:26px 32px 8px;{F}font-size:12px;font-weight:700;letter-spacing:0.08em;text-transform:uppercase;color:{TIEF};">{e(s)}</td></tr>'


def p(s, extra=""):
    return f'<tr><td style="padding:0 32px 10px;{F}font-size:15px;line-height:1.55;color:{INK};{extra}">{s}</td></tr>'


def klein(s):
    return f'<tr><td style="padding:0 32px 10px;{F}font-size:13px;line-height:1.5;color:{TXT};">{s}</td></tr>'


def link(u, s):
    return f'<a href="{e(u)}" style="color:{TIEF};font-weight:700;text-decoration:underline;">{e(s)}</a>'


def kachel(titel, wert, unter):
    return (f'<td width="33%" valign="top" style="padding:14px 12px;border:1px solid {LINIE};border-radius:10px;{F}">'
            f'<div style="font-size:12px;color:{TXT};">{e(titel)}</div><div style="font-size:24px;font-weight:700;color:{INK};padding:4px 0 2px;">{e(wert)}</div>'
            f'<div style="font-size:12px;line-height:1.4;color:{TXT};">{e(unter)}</div></td>')


def zeile(anleihe, *werte, kopf=False):
    """Tabellenzeile: Anleihe links, die Zahlen rechts in der Reihenfolge der Website-Tabellen (Rendite, Restlaufzeit, Kurs);
    die Rendite – die erste Zahl – fett wie auf der Website."""
    st = (f"padding:8px 0;border-bottom:1px solid {LINIE};{F}font-size:{'12' if kopf else '14'}px;color:{TXT if kopf else INK};"
          + ("text-transform:uppercase;letter-spacing:0.04em;" if kopf else ""))
    return (f'<tr><td valign="top" style="{st}">{anleihe}</td>'
            + "".join(f'<td align="right" valign="top" style="{st}white-space:nowrap;padding-left:10px;font-weight:{"700" if i == 0 and not kopf else "400"};">{w}</td>'
                      for i, w in enumerate(werte)) + "</tr>")


def unter(s, farbe=TXT):
    """Zweite Zeile in einer Zelle (Fälligkeit, Veränderung, Zinstermin) – klein und nicht fett."""
    return f'<div style="font-size:12px;font-weight:400;color:{farbe};padding-top:2px;">{s}</div>'


def tabellenkopf(anleihe, kurs_unter=""):
    """Kopfzeile der Anleihen-Tabellen: Bezeichnungen aus dem Feldkatalog, Restlaufzeit mit „Fälligkeit“ darunter (wie auf der Website)."""
    u = lambda s: f'<div style="font-size:11px;text-transform:none;letter-spacing:0;padding-top:1px;">{e(s)}</div>' if s else ""   # noqa: E731
    return zeile(e(anleihe), e(FELD["rendite"]["kurz"]), e(FELD["restlaufzeit"]["kurz"]) + u(FELD["restlaufzeit"]["unter"]),
                 e(FELD["kurs"]["kurz"]) + u(kurs_unter), kopf=True)


def anleihe_link(u, titel):
    return f'<a href="{e(u)}" style="color:{INK};text-decoration:none;font-weight:700;">{titel}</a>'


def tabelle(inhalt):
    return f'<tr><td style="padding:0 32px 8px;"><table role="presentation" width="100%" cellpadding="0" cellspacing="0">{inhalt}</table></td></tr>'


# Vorlagen für „Deine Merkliste“ – konto.php setzt je Abonnent die Zeilen ein (nl_merkliste; Platzhalter {{…}}, Werte im HTML
# maskiert). Platzhalter je Anleihe: TITEL, LINK, KERN (zweite Zeile, nl_kern), ZUSATZ (dritte Zeile der Textfassung samt Einzug und
# Zeilenende, sonst leer), RENDITE, RESTLAUFZEIT, FAELLIG, KURS, DIFF („+0,12 Pkt.“), DIFF_FARBE, ZT („Nächster Zinstermin …“).
MERK = {
    "farbe_plus": TIEF, "farbe_minus": MINUS, "farbe_null": TXT,
    "text_zeile": "{{TITEL}}\n  {{KERN}}\n{{ZUSATZ}}\n",
    "text_rahmen": "DEINE MERKLISTE IN DIESER WOCHE\n\n{{ZEILEN}}{{WEITERE}}Zur Merkliste: " + SEITE + "konto.html\n",
    "text_leer": "DEINE MERKLISTE\n\nDeine Merkliste ist noch leer. In der Anleihen-Suche und auf jedem Steckbrief steht der Knopf „Merken“ – dann zeigt dir der "
                 "Wochenbrief hier Rendite, Restlaufzeit, Kurs und den nächsten Zinstermin deiner Anleihen.\n" + SEITE + "anleihen-suche.html\n",
    "html_zeile": zeile(anleihe_link("{{LINK}}", "{{TITEL}}") + unter("{{ZT}}"), "{{RENDITE}}", "{{RESTLAUFZEIT}}" + unter("{{FAELLIG}}"),
                        "{{KURS}}" + unter("{{DIFF}}", "{{DIFF_FARBE}}")),
    "html_rahmen": h2("Deine Merkliste in dieser Woche") + tabelle(tabellenkopf(FELD["anleihe"]["kurz"], "zur Vorwoche") + "{{ZEILEN}}")
                   + klein('{{WEITERE}} ' + link(SEITE + "konto.html", "Zur Merkliste")),
    "html_leer": h2("Deine Merkliste") + p("Deine Merkliste ist noch leer. In der Anleihen-Suche und auf jedem Steckbrief steht der Knopf „Merken“ – dann zeigt dir "
                                         "der Wochenbrief hier Rendite, Restlaufzeit, Kurs und den nächsten Zinstermin deiner Anleihen.")
                 + klein(link(SEITE + "anleihen-suche.html", "Zur Anleihen-Suche")),
}


def baue(heute):
    """Ausgabe als Dict (siehe Kopf der Datei) und die Daten je Anleihe."""
    kw_jahr, kw, wtag = heute.isocalendar()[0], heute.isocalendar()[1], heute.weekday()
    anleihen, kstand = anleihen_daten(heute)
    b = bund(heute)
    ezb = lade("ezb.json", {}) or {}
    us = ((lade("renditen.json", {}) or {}).get("countries") or {}).get("us", {}).get("latest") or {}
    fenster, staat = meist("top10-staatsanleihen-laufzeit.json")
    _, firma = meist("top10-unternehmensanleihen-laufzeit.json")
    aka = akademie(kw)
    neu = neue_seiten(heute)

    # ---- Schutz: nur vollständige, frische Daten gehen raus ----
    probleme = []
    if not kstand or (heute - datetime.date.fromisoformat(kstand)).days > KURS_MAX_TAGE:
        probleme.append(f"Kurse veraltet (Stand {kstand or 'unbekannt'})")
    if len(anleihen) < 10000:
        probleme.append(f"nur {len(anleihen)} Anleihen mit Kurs")
    if not b or (heute - datetime.date.fromisoformat(b[10]["tag"])).days > 6:
        probleme.append("Bundrenditen der Bundesbank fehlen oder sind veraltet")
    if len(ezb.get("aktuell") or []) < 2 or len(ezb.get("stufen") or []) < 2:
        probleme.append("EZB-Einlagesatz fehlt")
    if len(staat) < 3 or len(firma) < 3:
        probleme.append("Liste der meistgehandelten Anleihen unvollständig")
    if aka is None:
        probleme.append("kein Akademie-Artikel lesbar")
    versandtag = wtag == VERSANDTAG or os.environ.get("NEWSLETTER_VERSAND") == "1"
    kopf = {"kw": f"{kw_jahr}-W{kw:02d}", "erstellt": heute.isoformat(), "versand": versandtag and not probleme,
            "grund": "; ".join(probleme) if probleme else ("" if versandtag else "kein Versandtag"), "warnen": versandtag and bool(probleme)}
    if probleme:
        return {**kopf, "betreff": "", "text": "", "html": "", "merk": MERK, "muster": []}, anleihen

    b2, b10 = b[2], b[10]
    richtung = "gestiegen" if b10["d"] > SCHWELLE else "gefallen" if b10["d"] < -SCHWELLE else "kaum verändert"
    ezb_seit, ezb_satz, ezb_davor = ezb["aktuell"][0], ezb["aktuell"][1], ezb["stufen"][-2][1]
    tag_text = f"{heute.day}. {MON[heute.month - 1]} {heute.year}"

    def titel_von(x):
        """Titel einer Anleihe der Rangliste – aus anleihen.json wie in der Merkliste; fehlt sie dort, aus dem Kurznamen der Rangliste."""
        a = anleihen.get(x["isin"])
        return titel_aus(a) if a else titel_text(x.get("kurz") or x.get("emittent") or x["isin"], x.get("kupon"), 0, x.get("faellig") or "")

    rlz = lambda x: restlaufzeit_text(jahre_bis(x.get("faellig"), heute))   # noqa: E731
    vorwoche = lambda d: pkt_text(d) + " zur Vorwoche"   # noqa: E731 – Veränderung der Rendite in Prozentpunkten
    titel = f"Bundrendite in dieser Woche {richtung}"
    einleitung = (f"Zehnjährige Bundesanleihen rentieren mit {pct_text(b10['r'])} – "
                  + (f"{zahl(abs(b10['d']))} Prozentpunkte {'mehr' if b10['d'] > 0 else 'weniger'} als vor einer Woche." if richtung != "kaum verändert" else "kaum anders als vor einer Woche.")
                  + f" Der Einlagesatz der EZB steht seit dem {datum(ezb_seit)} bei {pct_text(ezb_satz)}.")
    us_text = f"USA 10 Jahre: {pct_text(us['yield'])} (Stand {datum(us['date'])})." if isinstance(us.get("yield"), (int, float)) and us.get("date") else ""
    quelle_bund = (f"Bund: Rendite der {b10['art']} {kupon_text(b10['kupon'], b10['zinsart'])} {b10['jahr']} und der {b2['art']} "
                   f"{kupon_text(b2['kupon'], b2['zinsart'])} {b2['jahr']} laut Bundesbank, verglichen mit dem {datum(b10['vor'])}.")
    fenster_text = (f"Umsatz in Frankfurt und auf Tradegate, {datum(fenster['von'])} bis {datum(fenster['bis'])}. Keine Empfehlung."
                    if fenster.get("von") and fenster.get("bis") else "Umsatz in Frankfurt und auf Tradegate. Keine Empfehlung.")

    # ---- Textfassung ----
    t = [f"BONDARIUM WOCHENBRIEF · KW {kw} · {tag_text}", "", titel.upper(), "", einleitung, "", "ZINSEN DER WOCHE", "",
         f"Bund 10 Jahre  {pct_text(b10['r'])}  ({vorwoche(b10['d'])}, Stand {datum(b10['tag'])})",
         f"Bund 2 Jahre   {pct_text(b2['r'])}  ({vorwoche(b2['d'])})",
         f"EZB-Einlagesatz  {pct_text(ezb_satz)}  (seit {datum(ezb_seit)}, davor {pct_text(ezb_davor)})"]
    t += ([us_text] if us_text else []) + ["", quelle_bund, "Renditen ansehen: " + SEITE + "renditen.html", "", "MEISTGEHANDELT AN DER BÖRSE", fenster_text, ""]
    for kopfzeile, liste in (("Staatsanleihen", staat), ("Unternehmensanleihen", firma)):
        t += [kopfzeile + ":", ""]
        for x in liste:   # erste Zeile der Titel, zweite die Kernzahlen
            t += [titel_von(x), "  " + kern(x["rendite"], x["faellig"], rlz(x), x["kurs"]), ""]
    t += ["Alle Top-10-Listen: " + SEITE + "anleihen.html", "", "{{MERKLISTE}}", "AUS DER AKADEMIE", "", aka["titel"], aka["text"], aka["link"], ""]
    if neu:
        t += ["NEUE SEITEN AUF BONDARIUM", ""]
        for x in neu:
            t += [x["titel"], x["text"], x["link"], ""]
    t += ["--", "Keine Anlageberatung. Alle Angaben ohne Gewähr; Börsenkurse sind Schlusskurse, keine Echtzeitkurse.",
          "Quellen: Deutsche Bundesbank, Europäische Zentralbank, Federal Reserve, Deutsche Börse.", "",
          "Du bekommst diese E-Mail, weil du den Wochenbrief in „Mein Bondarium“ bestellt hast.", "Abbestellen mit einem Klick: {{ABMELDEN}}", "",
          "Bondarium – ein Angebot der urbanelo GmbH, Heinrich-Baumann-Straße 38, 70190 Stuttgart", SEITE + "rechtliches.html#impressum"]

    # ---- HTML-Fassung ----
    H = [f'<!doctype html><html lang="de"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Bondarium Wochenbrief {e(tag_text)}</title></head>',
         '<body style="margin:0;padding:0;background:#F4F3EE;"><table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#F4F3EE;"><tr><td align="center" style="padding:24px 12px;">',
         '<table role="presentation" width="600" cellpadding="0" cellspacing="0" style="width:600px;max-width:100%;background:#ffffff;border-radius:14px;overflow:hidden;">',
         f'<tr><td style="background:{GRUEN};padding:20px 32px;{F}"><table role="presentation" width="100%" cellpadding="0" cellspacing="0"><tr>'
         f'<td style="{F}font-size:24px;font-weight:700;letter-spacing:-0.02em;color:{INK};"><a href="{SEITE}" style="color:{INK};text-decoration:none;">bondarium</a></td>'
         f'<td align="right" style="{F}font-size:13px;color:{INK};">Wochenbrief · {e(tag_text)}</td></tr></table></td></tr>',
         f'<tr><td style="padding:26px 32px 4px;{F}font-size:26px;line-height:1.2;font-weight:700;letter-spacing:-0.02em;color:{INK};">{e(titel)}</td></tr>',
         p(e(einleitung), "padding-top:8px;"), h2("Zinsen der Woche"),
         '<tr><td style="padding:4px 26px 6px;"><table role="presentation" width="100%" cellpadding="0" cellspacing="6"><tr>'
         + kachel("Bund 10 Jahre", pct_text(b10['r']), f"{vorwoche(b10['d'])} · Stand {datum(b10['tag'])}")
         + kachel("Bund 2 Jahre", pct_text(b2['r']), f"{vorwoche(b2['d'])} · Stand {datum(b2['tag'])}")
         + kachel("EZB-Einlagesatz", pct_text(ezb_satz), f"seit {datum(ezb_seit)}, davor {pct_text(ezb_davor)}") + "</tr></table></td></tr>",
         klein(e(quelle_bund + (" " + us_text if us_text else "")) + " " + link(SEITE + "renditen.html", "Renditen ansehen")),
         h2("Meistgehandelt an der Börse"), klein(e(fenster_text))]
    for kopfzeile, liste in (("Staatsanleihen", staat), ("Unternehmensanleihen", firma)):
        H.append(tabelle(tabellenkopf(kopfzeile) + "".join(
            zeile(anleihe_link(f"{SEITE}anleihe.html?isin={x['isin']}", e(titel_von(x))), e(pct_text(x["rendite"])),
                  e(rlz(x)) + (unter(e(datum(x["faellig"]))) if x.get("faellig") else ""), e(kurs_text(x["kurs"]))) for x in liste)))
    H += [klein(link(SEITE + "anleihen.html", "Alle Top-10-Listen")), "{{MERKLISTE}}", h2("Aus der Akademie"),
          f'<tr><td style="padding:2px 32px 6px;{F}font-size:19px;font-weight:700;color:{INK};">{e(aka["titel"])}</td></tr>', p(e(aka["text"])), klein(link(aka["link"], "Artikel lesen"))]
    if neu:
        H += [h2("Neue Seiten auf Bondarium"),
              p("".join(f'<div style="padding:0 0 10px;"><a href="{e(x["link"])}" style="color:{INK};font-weight:700;text-decoration:underline;">{e(x["titel"])}</a><br>'
                        f'<span style="color:{TXT};">{e(x["text"])}</span></div>' for x in neu))]
    H += [f'<tr><td style="padding:18px 32px 24px;border-top:1px solid {LINIE};{F}font-size:12px;line-height:1.6;color:{TXT};">Keine Anlageberatung. Alle Angaben ohne Gewähr; '
          'Börsenkurse sind Schlusskurse, keine Echtzeitkurse. Quellen: Deutsche Bundesbank, Europäische Zentralbank, Federal Reserve, Deutsche Börse.<br><br>'
          f'Du bekommst diese E-Mail, weil du den Wochenbrief in „Mein Bondarium“ bestellt hast. <a href="{{{{ABMELDEN}}}}" style="color:{TIEF};">Newsletter abbestellen</a> – ein Klick genügt.<br>'
          f'Bondarium – ein Angebot der urbanelo GmbH, Heinrich-Baumann-Straße 38, 70190 Stuttgart · <a href="{SEITE}rechtliches.html#impressum" style="color:{TXT};">Impressum</a></td></tr>',
          "</table></td></tr></table></body></html>"]
    ausgabe = {**kopf, "betreff": f"Wochenbrief KW {kw}: Bundrendite {richtung}", "text": nur_text("\n".join(t) + "\n"), "html": "\n".join(H) + "\n",
               "merk": MERK, "muster": [firma[0]["isin"], staat[1]["isin"], firma[2]["isin"]]}
    return ausgabe, anleihen


def merk_werte(isin, b, v):
    """Platzhalter einer Anleihe für „Deine Merkliste“ – dieselben Werte wie nl_merkliste in konto.php (dort für den Versand)."""
    diff = "" if b[5] is None else pkt_text(b[5])
    r = round(b[5], 2) if b[5] is not None else 0
    zt = zinstermin_text(b)
    zusatz = " · ".join(x for x in ((FELD["kurs"]["kurz"] + " " + diff + " zur Vorwoche") if diff else "", zt) if x)
    rlz = restlaufzeit_text(jahre_bis(b[2], datetime.date.today())) if b[2] else "unbefristet"
    return {"TITEL": titel_aus(b), "LINK": SEITE + "anleihe.html?isin=" + isin, "KERN": kern(b[4], b[2], rlz, b[3]),
            "ZUSATZ": "  " + zusatz + "\n" if zusatz else "", "RENDITE": pct_text(b[4]), "RESTLAUFZEIT": rlz,
            "FAELLIG": datum(b[2]) if b[2] else "", "KURS": kurs_text(b[3]), "DIFF": diff,
            "DIFF_FARBE": v["farbe_plus"] if r > 0 else v["farbe_minus"] if r < 0 else v["farbe_null"], "ZT": zt}


def vorschau(ausgabe, anleihen):
    """Text und HTML mit Muster-Merkliste – dieselbe Ersetzung wie in konto.php (nl_merkliste), nur zum Ansehen."""
    v, text, zeilen = ausgabe["merk"], "", ""
    fuelle = lambda s, werte: re.sub(r"\{\{(\w+)\}\}", lambda m: str(werte.get(m.group(1), m.group(0))), s)   # noqa: E731
    for isin in ausgabe["muster"]:
        w = merk_werte(isin, anleihen[isin], v)
        text += nur_text(fuelle(v["text_zeile"], w))
        zeilen += fuelle(v["html_zeile"], {k: e(str(x)) for k, x in w.items()})
    ab = SEITE + "konto.html#nl-ab=0." + "0" * 32
    t = ausgabe["text"].replace("{{MERKLISTE}}", v["text_rahmen"].replace("{{ZEILEN}}", text).replace("{{WEITERE}}", "")).replace("{{ABMELDEN}}", ab)
    h = ausgabe["html"].replace("{{MERKLISTE}}", v["html_rahmen"].replace("{{ZEILEN}}", zeilen).replace("{{WEITERE}}", "")).replace("{{ABMELDEN}}", e(ab))
    (AUS / "vorschau.txt").write_text(t, encoding="utf-8")
    (AUS / "vorschau.html").write_text(h, encoding="utf-8")


def main():
    vorgabe = os.environ.get("NEWSLETTER_HEUTE")
    heute = datetime.date.fromisoformat(vorgabe) if vorgabe else datetime.datetime.now(ZoneInfo("Europe/Berlin")).date()
    AUS.mkdir(exist_ok=True)
    ausgabe, anleihen = baue(heute)
    write_atomic(AUS / "ausgabe.json", ausgabe, indent=None)
    write_atomic(AUS / "anleihen.json", anleihen, indent=None)
    if ausgabe["grund"] and ausgabe["warnen"]:
        log_err(f"Wochenbrief {ausgabe['kw']}: kein Versand – {ausgabe['grund']}")
    print(f"Wochenbrief {ausgabe['kw']} vom {ausgabe['erstellt']}: " + ("Versand freigegeben" if ausgabe["versand"] else f"kein Versand ({ausgabe['grund']})")
          + f"; {len(anleihen)} Anleihen mit Kurs" + (f"; Betreff „{ausgabe['betreff']}“" if ausgabe["betreff"] else ""))
    if "--vorschau" in sys.argv and ausgabe["html"]:
        vorschau(ausgabe, anleihen)
        print("Vorschau: newsletter/vorschau.html, newsletter/vorschau.txt")
    return 0


if __name__ == "__main__":
    sys.exit(main())
