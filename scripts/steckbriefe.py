"""Steckbriefe der Bundeswertpapiere vom Server (seit 03.10.2026; Entscheidung „Steckbriefe in Stufen, vom Server“ vom 02.10.2026).

Der Steckbrief anleihe.html?isin=… entsteht sonst erst im Browser: Für jede ISIN liefert der Server dasselbe HTML mit dem Titel
„Anleihe: Kurs, Rendite und Kursverlauf“ – Suchen nach ISIN, WKN oder Anleihename konnten nie hier landen. Stufe 1: die
Bundeswertpapiere (kurse/bund/, Kurse der Deutschen Bundesbank) bekommen eine fertige Seite mit eigenem Titel, eigener
Beschreibung, kanonischer Adresse, Überschrift, Registername, ISIN/WKN, Stammdaten (ohne JavaScript lesbar) und strukturierten
Daten. Alle übrigen Steckbriefe tragen „noindex, follow“ (Quell-HTML); Ausbau nach 6–8 Wochen Search Console.

Ausgeliefert wird die Seite unter der gewohnten Adresse: Die .htaccess schreibt anleihe.html?isin=<ISIN> intern auf
steckbrief/<ISIN>.html um (die Adresse im Browser bleibt, das Seitenskript liest ?isin= wie immer). Direkte Abrufe von
steckbrief/… leiten auf die Adresse mit ?isin= um (seit 09.10.2026 eine feste Regel in der .htaccess vor dem HTTPS-Block –
ein Sprung auch über http, ohne www und über .com; Technik-Test T-67). Kurse und Rendite kommen weiter vom Seitenskript –
Börsendaten (Kurse, Zinstermine der Börsenliste) stehen bewusst nicht im Server-HTML; den Zinstermin leiten wir aus der
Fälligkeit ab (Bundeswertpapiere zahlen jährlich am Fälligkeitstag).

Läuft im Workflow NACH „Zeitstempel & Versions-URLs“ (die Vorlage _site/anleihe.html trägt dann schon die Versions-URLs)
und VOR dem Minifizieren (das auch Unterordner erfasst):

    python3 scripts/steckbriefe.py _site

Schreibt: _site/steckbrief/<ISIN>.html, die interne Umschreibung in _site/.htaccess (an der Marke @@STECKBRIEFE@@, die allein
auf ihrer Zeile steht) und je Seite einen Eintrag in _site/sitemap.xml. Nur wenn alle Seiten gebaut sind, kommen Regel und
Sitemap-Einträge dazu – sonst bleibt alles beim Alten (die Vorlage funktioniert für jede ISIN).

Daten-Stand, dateModified und <lastmod> (seit 09.10.2026, Technik-Test T-71): der Stand der Stammdaten (jüngster „stand“ der
Teildateien anleihen/*.json, stammdaten_stand) – das ist, was die Seite ohne JavaScript zeigt. Vorher hing er am Ende der
Bundesbank-Kursreihe kurse/bund/<ISIN>.json: Kurse zeigt das Server-HTML aber nicht, und fiel die Reihe aus (Bundesbank ab
01.10.2026), blieb der Stand stehen.

Zahlen schreibt _common.zahl_de (wie die übrigen festen Tabellen), Organisation und Website kommen aus seo.py (gleiche Knoten wie
auf allen Seiten, Technik-Test T-72). Läuft mit Python 3.10+ (Workflow 3.12; _common.py braucht 3.10), nur Standardbibliothek.
"""
import datetime
import glob
import html
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import zahl_de  # noqa: E402
from seo import ORGANISATION, WEBSITE  # noqa: E402

BASE = "https://www.bondarium.de/"
ROBOTS_INDEX = "index, follow, max-image-preview:large, max-snippet:-1, max-video-preview:-1"
NBSP = "\u00a0"
MARKE = "# @@STECKBRIEFE@@"


def esc(s):
    return html.escape(str(s), quote=True)


def kupon_text(k):
    """wie fmtCoupon/MC.felder.kuponZahl: zwei Nachkommastellen, drei wenn nötig (5,625 %)"""
    return zahl_de(k, 3 if round(k * 1000) % 10 else 2) + NBSP + "%"


def datum(iso):
    return f"{iso[8:10]}.{iso[5:7]}.{iso[:4]}"


def art_von(name):
    """Art des Bundeswertpapiers aus dem Registernamen (FIRDS)."""
    n = name.lower()
    if "inflationsindex" in n or "infl." in n:
        art = "Inflationsindexierte Bundesanleihe"
    elif "bundesobl" in n:
        art = "Bundesobligation"
    elif "schatzanw" in n:
        art = "Bundesschatzanweisung"
    elif "anl" in n:
        art = "Bundesanleihe"
    else:
        return None
    return ("Grüne " + art) if re.search(r"\bgrüne\b", n) else art


def stammdaten(site, isins):
    """ISIN → Zeile aus anleihen/<teil>.json: [name, art, waehrung, kupon, faellig, volumen, stueckelung, boerse, emittent,
    zinsart, land, …] (Format von scripts/update_anleihen_index.py)."""
    out = {}
    for f in glob.glob(os.path.join(site, "anleihen", "*.json")):
        try:
            d = json.load(open(f, encoding="utf-8"))
        except (OSError, ValueError):
            continue
        rows = d.get("rows") or d.get("a") or d
        if isinstance(rows, dict):
            for isin in isins:
                if isin in rows and isinstance(rows[isin], list):
                    out[isin] = rows[isin]
    return out


def stammdaten_stand(site):
    """Jüngster „stand“ (JJJJ-MM-TT) der Stammdaten-Teildateien anleihen/*.json oder None. Diesen Stand nennt auch das
    Seitenskript („Daten-Stand: Stammdaten …“, anleihe.html). stammdaten() bleibt unverändert – kennzahlen.py und
    statische_tabellen.py nutzen es."""
    staende = []
    for f in glob.glob(os.path.join(site, "anleihen", "*.json")):
        try:
            s = str(json.load(open(f, encoding="utf-8")).get("stand") or "")[:10]
        except (OSError, ValueError, AttributeError):
            continue
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", s):
            staende.append(s)
    return max(staende) if staende else None


def ersetze(text, muster, neu, pflicht=True, flags=0):
    t2, n = re.subn(muster, lambda m: neu, text, count=1, flags=flags)
    if pflicht and n != 1:
        raise ValueError(f"Stelle nicht gefunden: {muster[:60]}")
    return t2


def seite(vorlage, isin, r, stand, stand_art="Stammdaten "):
    name, kupon, faellig, volumen, stk, emittent = r[0], r[3], r[4], r[5], r[6], r[8] or "Bundesrepublik Deutschland"
    zinsart = r[9] if len(r) > 9 and isinstance(r[9], int) else 0
    art = art_von(name)
    if not art or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(faellig or "")) or not isinstance(kupon, (int, float)):
        raise ValueError(f"{isin}: Stammdaten unvollständig ({name!r}, {kupon!r}, {faellig!r})")
    null = zinsart == 2 or kupon == 0
    k_text = "Nullkupon" if null else kupon_text(kupon)
    jahr, wkn = faellig[:4], isin[5:11]
    url = f"{BASE}anleihe.html?isin={isin}"
    titel = f"{art} {k_text} {jahr} ({isin}) – Bondarium"
    zins = "ohne laufende Zinsen (Nullkupon)" if null else f"Zinsen jährlich am {faellig[8:10]}.{faellig[5:7]}."
    stk_text = f"{zahl_de(stk, 2 if stk >= 0.01 else 3)}{NBSP}€" if isinstance(stk, (int, float)) else "–"
    vol_text = f"{zahl_de(volumen / 1e9, 2).rstrip('0').rstrip(',')}{NBSP}Mrd.{NBSP}€" if isinstance(volumen, (int, float)) and volumen >= 1e9 else ""
    kupon_teil = "" if null else f"Kupon {k_text}, "   # bei Nullkupon sagt es „ohne laufende Zinsen“ schon
    beschr = (f"{art} {k_text} {jahr} der Bundesrepublik Deutschland, ISIN {isin}, WKN {wkn}: {kupon_teil}{zins}, fällig am "
              f"{datum(faellig)}, Stückelung {stk_text}. Kurs und Rendite börsentäglich.")
    # Kopf des Steckbriefs wie das Seitenskript (titel, titelFa, Registername, ISIN/WKN)
    kopf = f"Deutschland {k_text}"
    h = vorlage
    h = ersetze(h, r'<html lang="de"', '<html lang="de" data-steckbrief="server"')
    h = ersetze(h, r"<title>[^<]*</title>", f"<title>{esc(titel)}</title>")
    h = ersetze(h, r'<meta name="description" content="[^"]*">', f'<meta name="description" content="{esc(beschr)}">')
    h = ersetze(h, r'<link rel="canonical" href="[^"]*">', f'<link rel="canonical" href="{esc(url)}">')
    h = ersetze(h, r'<meta name="robots" content="[^"]*">', f'<meta name="robots" content="{ROBOTS_INDEX}">')
    for eig, wert in (("og:url", url), ("og:title", titel), ("og:description", beschr)):
        h = ersetze(h, r'<meta property="' + eig + r'" content="[^"]*">', f'<meta property="{eig}" content="{esc(wert)}">', pflicht=False)
    for eig, wert in (("twitter:title", titel), ("twitter:description", beschr)):
        h = ersetze(h, r'<meta name="' + eig + r'" content="[^"]*">', f'<meta name="{eig}" content="{esc(wert)}">', pflicht=False)
    graph = {"@context": "https://schema.org", "@graph": [
        {"@type": "WebPage", "@id": url + "#seite", "url": url, "name": titel.replace(" – Bondarium", ""), "description": beschr,
         "inLanguage": "de", "isPartOf": {"@id": BASE + "#website"}, "publisher": {"@id": BASE + "#organisation"},
         "breadcrumb": {"@id": url + "#brotkrumen"}, "about": {"@id": url + "#anleihe"}, "dateModified": stand},
        {"@type": "BreadcrumbList", "@id": url + "#brotkrumen", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Start", "item": BASE},
            {"@type": "ListItem", "position": 2, "name": "Anleihen", "item": BASE + "anleihen.html"},
            {"@type": "ListItem", "position": 3, "name": "Anleihen-Suche", "item": BASE + "anleihen-suche.html"},
            {"@type": "ListItem", "position": 4, "name": f"{art} {k_text} {jahr}", "item": url}]},
        {"@type": "FinancialProduct", "@id": url + "#anleihe", "name": f"{art} {k_text} {jahr}", "alternateName": name,
         "category": art, "identifier": [{"@type": "PropertyValue", "propertyID": "ISIN", "value": isin},
                                         {"@type": "PropertyValue", "propertyID": "WKN", "value": wkn}],
         "provider": {"@type": "GovernmentOrganization", "name": "Bundesrepublik Deutschland"},
         "interestRate": 0 if null else kupon, "url": url},
        WEBSITE, ORGANISATION]}
    # alle JSON-LD-Blöcke der Vorlage durch einen eigenen ersetzen
    bloecke = re.findall(r'<script type="application/ld\+json">.*?</script>', h, re.S)
    if not bloecke:
        raise ValueError("kein JSON-LD in der Vorlage")
    h = h.replace(bloecke[0], '<script type="application/ld+json">' + json.dumps(graph, ensure_ascii=False, separators=(",", ":")) + "</script>", 1)
    for b in bloecke[1:]:
        h = h.replace(b, "", 1)
    h = ersetze(h, r'<h1 id="titel">[^<]*</h1>', f'<h1 id="titel">{esc(kopf)} <span class="fa">· fällig {datum(faellig)}</span></h1>')
    h = ersetze(h, r'<p class="reg" id="reg"></p>',
                f'<p class="reg" id="reg">Registername <b>{esc(name)}</b> · Emittent <b>{esc(emittent)}</b></p>')
    h = ersetze(h, r'<p class="idz" id="idz"><span>[^<]*</span></p>',
                f'<p class="idz" id="idz"><span class="isin">ISIN <b>{isin}</b> · WKN <b>{wkn}</b></span></p>')
    # Ohne JavaScript (KI-Crawler, Vorschauen): die Stammdaten in Sätzen statt nur „braucht JavaScript“
    fakten = (f'<noscript><p class="note"><b>{esc(art)} {esc(k_text)} {jahr}</b> der Bundesrepublik Deutschland · '
              + ("" if null else f"Kupon {esc(k_text)} · ") + f'{esc(zins)} · fällig am {datum(faellig)} · Stückelung {stk_text}'
              + (f" · ausgegeben {vol_text}" if vol_text else "")
              + '. Kurs, Rendite und Kursverlauf zeigt der Steckbrief mit JavaScript; die Anleihe findest du auch in der '
                '<a href="anleihen-suche.html">Anleihen-Suche</a>.</p></noscript>')
    h = ersetze(h, r"<noscript><p class=\"note\">Der Steckbrief braucht JavaScript\..*?</noscript>", fakten, flags=re.S)
    h = ersetze(h, r'<p id="datastand">Daten-Stand: [^<]*</p>', f'<p id="datastand">Daten-Stand: {stand_art}{datum(stand)}</p>', pflicht=False)
    return h


def main():
    site = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else "_site")
    vorlage = open(os.path.join(site, "anleihe.html"), encoding="utf-8").read()
    if "noindex" not in (re.search(r'<meta name="robots" content="([^"]*)"', vorlage) or [None, ""])[1]:
        print("::warning::steckbriefe.py: anleihe.html trägt kein noindex – alle übrigen Steckbriefe wären indexierbar")
    staende = {}
    for f in sorted(glob.glob(os.path.join(site, "kurse", "bund", "*.json"))):
        isin = os.path.basename(f)[:-5]
        try:
            t = json.load(open(f, encoding="utf-8")).get("t") or []
        except (OSError, ValueError):
            t = []
        if re.fullmatch(r"DE[A-Z0-9]{9}[0-9]", isin) and t:
            staende[isin] = max(t)
    stamm = stammdaten(site, staende)
    # Stand der Seite = Stand der Stammdaten (zeigt die Seite ohne JavaScript); nur ohne „stand“ in anleihen/*.json wie bisher
    # das Ende der Kursreihe kurse/bund/<ISIN>.json
    st_stamm, stand_art = stammdaten_stand(site), "Stammdaten "
    if st_stamm:
        staende = {isin: st_stamm for isin in staende}
    else:
        stand_art = ""
        print("::warning::steckbriefe.py: kein „stand“ in anleihen/*.json – Daten-Stand der Steckbriefe aus kurse/bund/")
    heute = datetime.date.today().isoformat()
    seiten, fehler = {}, []
    for isin, stand in staende.items():
        r = stamm.get(isin)
        if not r:
            fehler.append(f"{isin}: keine Stammdaten")
            continue
        if r[4] and r[4] <= heute:   # fällig: kein Steckbrief mehr (die Vorlage sagt „nicht mehr gelistet“)
            continue
        try:
            seiten[isin] = (seite(vorlage, isin, r, stand, stand_art), stand)
        except ValueError as e:
            fehler.append(str(e))
    if not seiten:
        print("::warning::steckbriefe.py: nichts geschrieben – " + ("; ".join(fehler[:5]) or "keine Bundeswertpapiere"))
        return
    if fehler:
        # Einzelne Bundeswertpapiere mit unvollständigen Stammdaten (z. B. Registername „Bundesrepublik Deutschland  Bond“
        # ohne erkennbare Art, 09.10.2026) bekommen keinen Server-Steckbrief und bleiben bei der Vorlage (noindex) – die
        # übrigen werden trotzdem geschrieben. Bis 09.10.2026 verhinderte ein einziger solcher Eintrag alle 79 Seiten.
        print(f"::warning::steckbriefe.py: {len(fehler)} Bundeswertpapier(e) ohne Server-Steckbrief – " + "; ".join(fehler[:5]))
    # 1) Seiten
    ordner = os.path.join(site, "steckbrief")
    os.makedirs(ordner, exist_ok=True)
    for isin, (inhalt, _) in seiten.items():
        with open(os.path.join(ordner, isin + ".html"), "w", encoding="utf-8") as f:
            f.write(inhalt)
    # 2) .htaccess: interne Umschreibung (Adresse bleibt). Der Rückweg für direkte Abrufe von steckbrief/… steht seit
    #    09.10.2026 fest in der .htaccess vor dem HTTPS-Block (ein Sprung auch über http, ohne www, .com).
    pfad = os.path.join(site, ".htaccess")
    ht = open(pfad, encoding="utf-8").read()
    if ht.count(MARKE) != 1:
        raise SystemExit("steckbriefe.py: Marke @@STECKBRIEFE@@ fehlt in .htaccess – Seiten geschrieben, aber nicht ausgeliefert")
    if "RewriteRule ^steckbrief/ " not in ht:
        print("::warning::steckbriefe.py: feste Regel für direkte Abrufe von steckbrief/<ISIN>.html fehlt in .htaccess")
    liste = "|".join(sorted(seiten))
    block = ("# ---- Steckbriefe der Bundeswertpapiere vom Server (scripts/steckbriefe.py, beim Deploy eingesetzt): anleihe.html?isin=<ISIN>\n"
             "#      liefert für diese ISIN steckbrief/<ISIN>.html aus, die Adresse bleibt. Direkte Abrufe: feste Regel vor dem HTTPS-Block. ----\n"
             f"RewriteCond %{{QUERY_STRING}} (?:^|&)isin=({liste})(?:&|$)\n"
             "RewriteRule ^anleihe\\.html$ /steckbrief/%1.html [L]")
    with open(pfad, "w", encoding="utf-8") as f:
        f.write(ht.replace(MARKE, block))
    # 3) Sitemap
    sm = os.path.join(site, "sitemap.xml")
    xml = open(sm, encoding="utf-8").read()
    neu = "".join(f"<url><loc>{BASE}anleihe.html?isin={isin}</loc><lastmod>{stand}</lastmod></url>\n" for isin, (_, stand) in sorted(seiten.items()))
    if "</urlset>" in xml:
        with open(sm, "w", encoding="utf-8") as f:
            f.write(xml.replace("</urlset>", neu + "</urlset>", 1))
    print(f"steckbriefe.py: {len(seiten)} Steckbriefe der Bundeswertpapiere vom Server (steckbrief/), .htaccess-Regel und Sitemap ergänzt")


if __name__ == "__main__":
    main()
