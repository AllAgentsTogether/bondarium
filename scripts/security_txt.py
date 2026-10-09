#!/usr/bin/env python3
"""security_txt.py – schreibt /.well-known/security.txt in den Veröffentlichungsordner (seit 30.09.2026).

    python3 scripts/security_txt.py _site

Die Datei nennt nach RFC 9116 eine Adresse für Sicherheitsmeldungen. „Expires“ ist Pflicht und darf höchstens
ein Jahr in der Zukunft liegen – deshalb entsteht die Datei bei jedem Deploy neu: Ablauf = Monatserster in rund
sieben Monaten. So ändert sie sich nur einmal im Monat und läuft nie ab, solange veröffentlicht wird.

Canonical (seit 09.10.2026, Technik-Test T-68): Die Datei wird auch unter bondarium.com und www.bondarium.com ausgeliefert
(/.well-known/ ist dort von der Weiterleitung ausgenommen, siehe .htaccess). Nach RFC 9116 (2.5.2) soll man ihr nicht
trauen, wenn die Abrufadresse in keinem Canonical-Feld steht – deshalb nennt sie alle drei Adressen.
"""
import datetime
import os
import sys

KONTAKT = "mailto:info@bondarium.com"
ADRESSE = "https://www.bondarium.de/.well-known/security.txt"
WEITERE_ADRESSEN = ("https://bondarium.com/.well-known/security.txt", "https://www.bondarium.com/.well-known/security.txt")


def ablauf(heute: datetime.date) -> str:
    monat = heute.year * 12 + (heute.month - 1) + 7
    return f"{monat // 12:04d}-{monat % 12 + 1:02d}-01T00:00:00Z"


def text(heute: datetime.date) -> str:
    return (
        "# Sicherheitslücke auf bondarium.de gefunden? Bitte an die folgende Adresse melden.\n"
        "# Found a security issue on bondarium.de? Please report it to the address below.\n"
        f"Contact: {KONTAKT}\n"
        f"Expires: {ablauf(heute)}\n"
        "Preferred-Languages: de, en\n"
        f"Canonical: {ADRESSE}\n"
        + "".join(f"Canonical: {a}\n" for a in WEITERE_ADRESSEN)
    )


def main() -> int:
    site = sys.argv[1] if len(sys.argv) > 1 else "_site"
    ordner = os.path.join(site, ".well-known")
    os.makedirs(ordner, exist_ok=True)
    with open(os.path.join(ordner, "security.txt"), "w", encoding="utf-8") as f:
        f.write(text(datetime.date.today()))
    print(f"security.txt geschrieben (Expires {ablauf(datetime.date.today())})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
