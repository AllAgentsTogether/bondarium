#!/usr/bin/env python3
"""kurs_luecken.py – prüft den Kursverlauf kurse/<Jahr>/00.json auf fehlende Börsentage (seit 29.09.2026).

Die Tagesdateien der Deutschen Börse (MiFIR-Delayed-Data) liegen nur etwa einen Börsentag online. Fällt ein Lauf
aus, fehlt der Tag dauerhaft. Dieses Skript vergleicht die gespeicherten Tage mit den Börsentagen seit Beginn der
Sammlung (24.09.2026) – Wochenenden und die Feiertage der Frankfurter Börse ausgenommen (Neujahr, Karfreitag,
Ostermontag, 1. Mai, 24.–26.12., 31.12.) – und prüft, ob der letzte Börsentag vor heute schon da ist.

Aufruf:
  python scripts/kurs_luecken.py            Bericht; Rückgabe 1 bei Lücken (für die Alarm-Prüfung im Workflow);
                                             Tage in BEKANNTE_LUECKEN zählen nicht als Alarm
  python scripts/kurs_luecken.py --fehlt-neu Rückgabe 0, wenn der letzte Börsentag vor heute fehlt (Nachhol-Lauf nötig),
                                             sonst 1 – für den Nachhol-Workflow
"""
import datetime
import json
import sys
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
BEGINN = datetime.date(2026, 9, 24)
# Bekannte, nicht mehr nachholbare Lücken – lösen keinen Alarm aus, werden im Bericht aber genannt.
#   2026-09-28: Umzug ins neue Repository (Bondarium); am 29.09. lief kein Abruf, die Tagesdateien der Deutschen Börse
#               waren danach nicht mehr online (geprüft am 30.09.2026: DaysToKeepOnWebpage = 1, Direktabruf 404).
BEKANNTE_LUECKEN = {datetime.date(2026, 9, 28)}


def ostern(j: int) -> datetime.date:
    a, b, c = j % 19, j // 100, j % 100
    d, e = b // 4, b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = c // 4, c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    monat = (h + l - 7 * m + 114) // 31
    tag = (h + l - 7 * m + 114) % 31 + 1
    return datetime.date(j, monat, tag)


def feiertage(j: int) -> set:
    o = ostern(j)
    return {datetime.date(j, 1, 1), o - datetime.timedelta(days=2), o + datetime.timedelta(days=1), datetime.date(j, 5, 1),
            datetime.date(j, 12, 24), datetime.date(j, 12, 25), datetime.date(j, 12, 26), datetime.date(j, 12, 31)}


def boersentag(d: datetime.date) -> bool:
    return d.weekday() < 5 and d not in feiertage(d.year)


def gespeicherte_tage() -> set:
    tage = set()
    for datei in sorted((ROOT / "kurse").glob("20[0-9][0-9]/00.json")):
        try:
            tage |= set(json.loads(datei.read_text(encoding="utf-8")).get("tage", []))
        except Exception:  # noqa: BLE001
            pass
    return {datetime.date.fromisoformat(t) for t in tage}


def main() -> int:
    heute = datetime.datetime.now(ZoneInfo("Europe/Berlin")).date()
    letzter = heute - datetime.timedelta(days=1)
    while not boersentag(letzter):
        letzter -= datetime.timedelta(days=1)
    da = gespeicherte_tage()
    if "--fehlt-neu" in sys.argv:
        fehlt = letzter not in da
        print(f"Letzter Börsentag {letzter}: {'fehlt – nachholen' if fehlt else 'vorhanden'}")
        return 0 if fehlt else 1
    soll, d = [], BEGINN
    while d <= letzter:
        if boersentag(d):
            soll.append(d)
        d += datetime.timedelta(days=1)
    offen = [x for x in soll if x not in da]
    fehlend = [x for x in offen if x not in BEKANNTE_LUECKEN]
    bekannt = [x for x in offen if x in BEKANNTE_LUECKEN]
    print(f"Kursverlauf: {len(da)} Tage gespeichert, {len(soll)} Börsentage seit {BEGINN}, fehlend: "
          + (", ".join(x.isoformat() for x in fehlend) or "keine")
          + (f" (bekannte Lücken: {', '.join(x.isoformat() for x in bekannt)})" if bekannt else ""))
    return 1 if fehlend else 0


if __name__ == "__main__":
    sys.exit(main())
