#!/usr/bin/env python3
"""CSS beim Deploy verkleinern (seit 02.10.2026) – konservativ, nur Standardbibliothek, läuft ab Python 3.9.

Aufruf:  python3 scripts/css_klein.py <ordner>      (bearbeitet <ordner>/*.css, im Workflow _site)

base.css und bildwelt2.css gingen bisher unverändert live – rund ein Drittel davon Kommentare. Sie blockieren auf jeder
Seite das erste Zeichnen. Das Skript macht nur, was die Bedeutung sicher nicht ändert:
  * Kommentare /* … */ entfernen – nicht in Zeichenketten "…"/'…' und nicht in url(…).
  * Leerraum (Leerzeichen, Tabulator, Zeilenumbruch) zu einem Leerzeichen zusammenfassen.
  * Leerzeichen entfernen: vor und nach { } ; überall; vor und nach „,“ und „>“ in Selektoren und Werten; vor und nach
    dem Doppelpunkt zwischen Eigenschaft und Wert (nur dort – im Selektor ist „a :hover“ etwas anderes als „a:hover“).
    In @-Regel-Köpfen (@media …) bleibt alles außer dem Zusammenfassen stehen.
Nichts wird umsortiert, zusammengelegt oder umgeschrieben (keine Selektor-, Farb- oder Zahlenkürzung, das letzte „;“
vor „}“ bleibt). Escape-Folgen (\\31 usw.) bleiben samt ihrem abschließenden Leerzeichen erhalten.

Sicherung: Nach dem Verkleinern zerlegt das Skript Original und Ergebnis in Regeln und Deklarationen (Selektor bzw.
@-Kopf, Eigenschaft, Wert – Leerraum normalisiert) und vergleicht beide Listen. Weichen sie ab oder geht etwas
schief, bleibt die Datei unverändert (Warnung im Protokoll). Der Deploy-Schritt hat continue-on-error.

Läuft VOR „Zeitstempel & Versions-URLs setzen“: Die Versions-URL (?v=<Hash>) gehört dann zur ausgelieferten Datei.
"""
from __future__ import annotations

import pathlib
import re
import sys

LEER = " \t\n\r\f"
HEX = "0123456789abcdefABCDEF"


class CssFehler(ValueError):
    pass


def _wortzeichen(c: str) -> bool:
    return c.isalnum() or c in "_-" or ord(c) > 127


# ---------- Zerlegen in Bausteine ----------
# Arten: "str" (Zeichenkette samt Anführungszeichen), "url" (url(…) ohne Anführungszeichen, unverändert),
# "ws" (Leerraum, schon auf ein Leerzeichen gekürzt), "p" (eines von { } : ; , > ( )), "x" (alles andere).
def zerlege(css: str) -> list:
    teile: list = []
    i, n = 0, len(css)
    puffer: list = []

    def flush():
        if puffer:
            teile.append(("x", "".join(puffer)))
            puffer.clear()

    while i < n:
        c = css[i]
        if c == "/" and css.startswith("/*", i):
            ende = css.find("*/", i + 2)
            if ende < 0:
                raise CssFehler(f"Kommentar ohne Ende ab Zeichen {i}")
            # Ein Kommentar ist kein Leerraum: „a/**/.b“ bleibt „a.b“. Nur zwischen zwei Wortzeichen („0/**/auto“)
            # muss eine Trennung bleiben – dort ein Leerzeichen, sonst verschwindet er ganz.
            vor = css[i - 1] if i else " "
            nach = css[ende + 2] if ende + 2 < n else " "
            if _wortzeichen(vor) and _wortzeichen(nach):
                flush()
                teile.append(("ws", " "))
            i = ende + 2
        elif c in "\"'":
            flush()
            j = i + 1
            while j < n and css[j] != c:
                if css[j] == "\\":
                    j += 1
                elif css[j] == "\n":
                    raise CssFehler(f"Zeilenumbruch in Zeichenkette ab Zeichen {i}")
                j += 1
            if j >= n:
                raise CssFehler(f"Zeichenkette ohne Ende ab Zeichen {i}")
            teile.append(("str", css[i:j + 1]))
            i = j + 1
        elif c == "\\":
            # Escape: Backslash plus Zeichen; bei Hex bis 6 Ziffern und EIN folgender Leerraum gehören dazu
            j = i + 1
            if j < n and css[j] in HEX:
                k = j
                while k < n and k - j < 6 and css[k] in HEX:
                    k += 1
                if k < n and css[k] in LEER:
                    k += 2 if css.startswith("\r\n", k) else 1
                puffer.append(css[i:k])
                i = k
            else:
                puffer.append(css[i:j + 1])
                i = j + 1
        elif c in LEER:
            flush()
            j = i
            while j < n and css[j] in LEER:
                j += 1
            teile.append(("ws", " "))
            i = j
        elif c in "{}:;,>()":
            # url( ohne Anführungszeichen: Inhalt unverändert übernehmen
            if c == "(" and puffer and re.search(r"(?:^|[^A-Za-z0-9_-])url$", "".join(puffer), re.I):
                j = i + 1
                while j < n and css[j] in LEER:
                    j += 1
                if j < n and css[j] not in "\"'":
                    k = j
                    while k < n and css[k] != ")":
                        if css[k] == "\\":
                            k += 1
                        k += 1
                    if k >= n:
                        raise CssFehler(f"url( ohne Ende ab Zeichen {i}")
                    puffer.append(css[i:k + 1])
                    flush()
                    i = k + 1
                    continue
            flush()
            teile.append(("p", c))
            i += 1
        else:
            puffer.append(c)
            i += 1
    flush()
    # benachbarte Leerräume (z. B. Kommentar zwischen zwei Leerzeichen) zusammenfassen
    aus: list = []
    for t in teile:
        if t[0] == "ws" and aus and aus[-1][0] == "ws":
            continue
        aus.append(t)
    return aus


def abschnitte(teile: list) -> list:
    """Teilt in Abschnitte, die mit { } oder ; enden: (bausteine, abschluss). abschluss "" = Dateiende."""
    erg, akt = [], []
    for t in teile:
        if t[0] == "p" and t[1] in "{};":
            erg.append((akt, t[1]))
            akt = []
        else:
            akt.append(t)
    erg.append((akt, ""))
    return erg


def _ohne_rand(ts: list) -> list:
    while ts and ts[0][0] == "ws":
        ts = ts[1:]
    while ts and ts[-1][0] == "ws":
        ts = ts[:-1]
    return ts


def _ohne_leer_um(ts: list, zeichen: str) -> list:
    """Leerraum direkt vor und nach den Satzzeichen in <zeichen> entfernen."""
    aus = []
    for k, t in enumerate(ts):
        if t[0] == "ws":
            vor = aus[-1] if aus else None
            nach = ts[k + 1] if k + 1 < len(ts) else None
            if (vor and vor[0] == "p" and vor[1] in zeichen) or (nach and nach[0] == "p" and nach[1] in zeichen):
                continue
        aus.append(t)
    return aus


def _ist_eigenschaft(ts: list) -> bool:
    """Steht vor dem ersten Doppelpunkt nur ein Eigenschaftsname (color, --farbe, -webkit-x)?"""
    return len(ts) == 1 and ts[0][0] == "x" and re.fullmatch(r"-{0,2}[A-Za-z_][A-Za-z0-9_-]*", ts[0][1]) is not None


def verkleinere(css: str) -> str:
    teile = zerlege(css)
    stuecke = []
    for ts, abschluss in abschnitte(teile):
        ts = _ohne_rand(ts)
        erstes = next((t for t in ts if t[0] != "ws"), None)
        at_regel = bool(erstes and erstes[0] == "x" and erstes[1].startswith("@"))
        if abschluss == "{":
            if not at_regel:
                ts = _ohne_leer_um(ts, ",>")          # Selektor: a , b > c → a,b>c
        elif not at_regel and ts:
            # Deklaration „Eigenschaft : Wert“
            k = next((k for k, t in enumerate(ts) if t == ("p", ":")), None)
            if k is not None and _ist_eigenschaft(_ohne_rand(ts[:k])):
                name = _ohne_rand(ts[:k])
                wert = _ohne_rand(ts[k + 1:])
                wert = _ohne_leer_um(wert, ",")
                # leerer Wert einer eigenen Eigenschaft (--x: ;) behält sein Leerzeichen
                ts = name + [("p", ":")] + (wert if wert else [("ws", " ")])
            else:
                ts = _ohne_leer_um(ts, ",")
        stuecke.append("".join(t[1] for t in ts) + abschluss)
    return "".join(stuecke).strip()


# ---------- Sicherung: Regeln und Deklarationen vergleichen ----------
def struktur(css: str) -> list:
    """Liste der Abschnitte als (Art, Text) mit normalisiertem Leerraum – unabhängig davon, wo Leerzeichen standen."""
    def norm(ts: list) -> str:
        s = ""
        for t in ts:
            if t[0] == "ws":
                s += " "
            else:
                s += t[1]
        s = re.sub(r" +", " ", s).strip()
        # Leerraum um Satzzeichen ist hier bedeutungslos (Doppelpunkt nur zwischen Eigenschaft und Wert, s. u.)
        return re.sub(r" ?([,>{};]) ?", r"\1", s)

    erg = []
    for ts, abschluss in abschnitte(zerlege(css)):
        ts = _ohne_rand(ts)
        if not ts and abschluss in ("}", ""):
            erg.append(("ende" if abschluss else "datei", ""))
            continue
        erstes = ts[0] if ts else None
        if abschluss == "{":
            erg.append(("kopf", norm(ts)))
            continue
        k = next((k for k, t in enumerate(ts) if t == ("p", ":")), None)
        if erstes and erstes[1].startswith("@") or k is None:
            erg.append(("anweisung", norm(ts)))
        else:
            erg.append(("dekl", norm(ts[:k]), norm(ts[k + 1:])))
        if abschluss == "}":
            erg.append(("ende", ""))
    return erg


def main() -> int:
    if len(sys.argv) != 2:
        print("Aufruf: python3 scripts/css_klein.py <ordner>", file=sys.stderr)
        return 2
    ordner = pathlib.Path(sys.argv[1])
    dateien = sorted(ordner.glob("*.css"))
    if not dateien:
        print(f"::warning::css_klein: keine CSS-Dateien in {ordner}")
        return 0
    summe_vor = summe_nach = 0
    for pfad in dateien:
        roh = pfad.read_bytes()
        try:
            text = roh.decode("utf-8")
            klein = verkleinere(text)
            if struktur(text) != struktur(klein):
                raise CssFehler("Regeln/Deklarationen weichen nach dem Verkleinern ab")
            if not klein or len(klein.encode("utf-8")) > len(roh):
                raise CssFehler("Ergebnis leer oder größer als das Original")
        except Exception as e:  # jede Datei für sich: im Fehlerfall bleibt das Original
            print(f"::warning::css_klein: {pfad.name} bleibt unverändert ({e})")
            summe_vor += len(roh)
            summe_nach += len(roh)
            continue
        neu = klein.encode("utf-8")
        pfad.write_bytes(neu)
        summe_vor += len(roh)
        summe_nach += len(neu)
        print(f"{pfad.name}: {len(roh):,} → {len(neu):,} Bytes ({100 - 100 * len(neu) / len(roh):.0f} % kleiner)"
              .replace(",", "."))
    print(f"Zusammen: {summe_vor:,} → {summe_nach:,} Bytes".replace(",", "."))
    return 0


if __name__ == "__main__":
    sys.exit(main())
