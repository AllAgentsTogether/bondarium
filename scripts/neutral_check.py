#!/usr/bin/env python3
"""Neutralitätstest für den Anleihe-Steckbrief (anleihe.html), seit 29.09.2026.

Regel (Nutzerentscheid 29.09.2026): Die Detailansicht zeigt nur Werte aus den Quellen und einfache,
gekennzeichnete Berechnungen – keine Bewertung, keine Handlungsaufforderung, keine Signalfarben.
Der Test liest alle sichtbaren Texte der Seite (HTML-Text und die Zeichenketten im Skript, ohne
Kommentare, ohne den Aufklapper „Datenquellen und Methodik“) und meldet jedes Wort aus der Wortliste.
Dazu: keine Statusklassen (plus/minus/warn) im Steckbrief.

Aufruf im Ordner website:  python3 scripts/neutral_check.py [datei]   → Rückgabewert 1 bei Treffern
"""
import re, sys, pathlib

WORTE = r"gut|gute[nmrs]?|schlecht\w*|sicher|sichere[nmrs]?|unsicher\w*|riskant\w*|risiko\w*|lohn\w*|empfehl\w*|empfohlen|passt|passend\w*|" \
        r"vorteil\w*|nachteil\w*|harmlos|attraktiv\w*|günstig\w*|teuer\w*|achtung|vorsicht\w*|solide\w*|geschenk|beachte\w*|unbedingt|" \
        r"sollte\w*|besser\w*|nie|chance\w*|gefahr\w*|warn\w*|kaum|gering\w*|niedrig\w*|lieber|ideal\w*|geeignet\w*|interessant\w*"
RE_WORT = re.compile(r"\b(" + WORTE + r")\b", re.I)
AUSNAHMEN = {"Hoch / Tief"}   # Spaltenkopf, kein Urteil (steht nicht in der Wortliste, nur zur Dokumentation)


def js_texte(code):
    """Inhalte aller String- und Template-Literale (ohne ${…}-Ausdrücke), Kommentare übersprungen."""
    out, i, n = [], 0, len(code)
    prev = ""   # letztes bedeutsames Zeichen – entscheidet, ob „/“ einen RegExp beginnt
    while i < n:
        c = code[i]
        if code.startswith("//", i):
            i = code.find("\n", i); i = n if i < 0 else i; continue
        if code.startswith("/*", i):
            j = code.find("*/", i + 2); i = n if j < 0 else j + 2; continue
        if c in "\"'":
            j, buf = i + 1, []
            while j < n and code[j] != c:
                if code[j] == "\\": buf.append(code[j:j + 2]); j += 2; continue
                buf.append(code[j]); j += 1
            out.append("".join(buf)); i = j + 1; prev = c; continue
        if c == "`":
            j, buf, tiefe = i + 1, [], 0
            while j < n:
                if code[j] == "\\": j += 2; continue
                if code.startswith("${", j):
                    # Ausdruck überspringen, verschachtelte Klammern zählen; innere Strings rekursiv prüfen
                    k, t = j + 2, 1
                    while k < n and t:
                        if code[k] == "{": t += 1
                        elif code[k] == "}": t -= 1
                        k += 1
                    out.extend(js_texte(code[j + 2:k - 1])); buf.append(" "); j = k; continue
                if code[j] == "`": break
                buf.append(code[j]); j += 1
            out.append("".join(buf)); i = j + 1; prev = "`"; continue
        if c == "/" and (prev == "" or prev in "(,=:[!&|?{};+-*%<>~^"):
            j, klasse = i + 1, False   # RegExp-Literal überspringen
            while j < n:
                if code[j] == "\\": j += 2; continue
                if code[j] == "[": klasse = True
                elif code[j] == "]": klasse = False
                elif code[j] == "/" and not klasse: break
                j += 1
            i = j + 1
            while i < n and code[i].isalpha(): i += 1
            prev = "/"; continue
        if not c.isspace(): prev = c
        i += 1
    return out


def pruefe(pfad):
    s = pathlib.Path(pfad).read_text(encoding="utf-8")
    body = s[s.index("<body"):]
    skripte = re.findall(r"<script>(.*?)</script>", body, re.S)
    html = re.sub(r"<script.*?</script>|<style.*?</style>|<!--.*?-->|<details class=\"quellen\".*?</details>|<noscript>.*?</noscript>", " ", body, flags=re.S)
    html = re.sub(r"<header class=\"topbar\".*?</header>|<footer>.*?</footer>", " ", html, flags=re.S)
    texte = [re.sub(r"<[^>]+>", " ", html)]
    for sk in skripte: texte += js_texte(sk)
    treffer = []
    for t in texte:
        t2 = re.sub(r"<[^>]+>", " ", t)
        for a in AUSNAHMEN: t2 = t2.replace(a, " ")
        for m in RE_WORT.finditer(t2):
            treffer.append((m.group(0), " ".join(t2[max(0, m.start() - 40):m.end() + 30].split())))
    klassen = [k for k in re.findall(r'class="([^"]*)"', s) if re.search(r"\b(plus|minus|warn)\b", k)]
    return treffer, klassen


if __name__ == "__main__":
    datei = sys.argv[1] if len(sys.argv) > 1 else "anleihe.html"
    treffer, klassen = pruefe(datei)
    for w, ctx in treffer: print(f"Wort „{w}“: …{ctx}…")
    for k in klassen: print(f"Statusklasse: {k}")
    print(f"{datei}: {len(treffer)} Wort-Treffer, {len(klassen)} Statusklassen")
    sys.exit(1 if treffer or klassen else 0)
