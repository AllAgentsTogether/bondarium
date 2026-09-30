#!/usr/bin/env python3
"""deploy_manifest.py – lädt nur geänderte Dateien per SFTP hoch (seit 30.09.2026).

Vorher wurden bei jedem Deploy alle ~1.400 Dateien übertragen (rund 12 Minuten). Jetzt liegt auf
dem Server eine Liste `.deploy-manifest` mit dem SHA-1 jeder hochgeladenen Datei (per .htaccess
gesperrt). Der Workflow holt sie, vergleicht mit dem neuen Stand und überträgt nur Abweichungen.

    python3 scripts/deploy_manifest.py manifest _site > neu.manifest
    python3 scripts/deploy_manifest.py lftp alt.manifest neu.manifest _site > upload.lftp

Das lftp-Skript legt fehlende Ordner an, lädt geänderte Dateien hoch und zuletzt das neue Manifest.
Fehlt das alte Manifest, wird alles hochgeladen.

Aufräumen (seit 30.09.2026): Dateien, die im alten Manifest stehen, im neuen Bau aber fehlen, werden auf dem
Server gelöscht – also nur, was dieser Deploy früher selbst hochgeladen hat und was es im Repository nicht mehr
gibt (Beispiel: etfs.json nach dem Umstieg auf das ETF-Register). Alles andere auf dem Server bleibt unberührt,
auch Dateien aus der Zeit vor dem Manifest (die archivierten Aktien-Seiten; sie sind per .htaccess umgeleitet).
Schutz: nie .htaccess, das Manifest oder etwas unter trigger/; sind es mehr als LOESCH_MAX Dateien, stimmt
vermutlich der Bau nicht – dann wird nichts gelöscht, nur gewarnt.
"""
import hashlib
import os
import sys

LOESCH_MAX = 40
GESCHUETZT = (".deploy-manifest",)


def loeschbar(pfad):
    name = os.path.basename(pfad)
    return not (name == ".htaccess" or pfad in GESCHUETZT or pfad.startswith("trigger/") or pfad.startswith("/") or ".." in pfad.split("/"))


def manifest(site):
    zeilen = []
    for wurzel, _, dateien in os.walk(site):
        for d in dateien:
            p = os.path.join(wurzel, d)
            rel = os.path.relpath(p, site).replace(os.sep, "/")
            with open(p, "rb") as f:
                zeilen.append(f"{hashlib.sha1(f.read()).hexdigest()}  {rel}")
    return sorted(zeilen, key=lambda z: z[42:])


def lies(pfad):
    m = {}
    if os.path.isfile(pfad):
        for z in open(pfad, encoding="utf-8"):
            z = z.rstrip("\n")
            if len(z) > 42:
                m[z[42:]] = z[:40]
    return m


def q(s):
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def main():
    art = sys.argv[1]
    if art == "manifest":
        print("\n".join(manifest(sys.argv[2])))
        return
    alt, neu, site = lies(sys.argv[2]), lies(sys.argv[3]), sys.argv[4]
    geaendert = [p for p, h in neu.items() if alt.get(p) != h]
    # .htaccess-Dateien zuletzt vor dem Manifest (Regeln erst aktiv, wenn die Seiten liegen)
    geaendert.sort(key=lambda p: (p.endswith(".htaccess"), p))
    print("set sftp:auto-confirm yes")
    print("set net:max-retries 3")
    print("set net:timeout 30")
    ordner = sorted({os.path.dirname(p) for p in geaendert if os.path.dirname(p)})
    for o in ordner:
        print(f"mkdir -p -f {q(o)}")
    for p in geaendert:
        ziel = os.path.dirname(p) or "."
        print(f"put -O {q(ziel)} {q(os.path.join(site, p))}")
    # Aufräumen: nur Dateien aus dem alten Manifest, die der neue Bau nicht mehr enthält
    weg = sorted(p for p in alt if p not in neu and loeschbar(p))
    if len(weg) > LOESCH_MAX:
        print(f"::warning::{len(weg)} Dateien stünden zum Löschen an (mehr als {LOESCH_MAX}) – nichts gelöscht, bitte Bau prüfen", file=sys.stderr)
        weg = []
    for p in weg:
        print(f"rm -f {q(p)}")
    print(f"put -O . {q(sys.argv[3])} -o .deploy-manifest")
    print(f"# {len(geaendert)} von {len(neu)} Dateien geändert, {len(weg)} gelöscht" + (": " + ", ".join(weg) if weg else ""), file=sys.stderr)


if __name__ == "__main__":
    main()
