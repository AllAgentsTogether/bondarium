/* bond.js – Anleihen-Mathematik und Anleihen-Formate an einer Stelle (seit 30.09.2026).
   Vorher stand derselbe Code in laufzeit.js und inline in anleihen-laender.html,
   unternehmensanleihen-laender.html und langlaeufer.html.

   Laden NACH site.js (nutzt MC.zahl/MC.minus, falls vorhanden):
     <script src="site.js"></script><script src="bond.js"></script>

   Konventionen: Datumsangaben als ISO-Zeichenkette „JJJJ-MM-TT“, Kurse und Kupons in Prozent vom Nennwert,
   Renditen als Dezimalzahl (0,0312 = 3,12 %). Anleihe-Objekt b = { coupon: 2.5, freq: 1 | 2 | 4 | 12, maturity: "2034-02-15",
   days: ["04-30", "10-30"] (optional) }.
   Rechnung wie bisher: jährliche Verzinsung, Zeit taggenau (Tage / 365,25), Stückzinsen linear im Kuponzeitraum.
   Kupontermine (seit 02.10.2026 wie scripts/_common.py, zinszahlungen):
     mit days  – die Zinstage „MM-TT“ laut Instrumentenliste der Deutschen Börse, jedes Jahr an diesen Tagen; der letzte Zins
                 kommt am Fälligkeitstag, bei einer kurzen Schlussperiode (mehr als 20 Tage neben dem Zinstag) anteilig;
     ohne days – geschätzt: vom Fälligkeitstag rückwärts in Schritten von 12/freq Monaten (Monatsende bleibt Monatsende,
                 31.05. → 30.11.; für Fälligkeitstage bis zum 28. identisch mit der früheren Rechnung in langlaeufer.html).

   API (window.MC.bond):
     DAY                               86 400 000 (ms je Tag)
     utc(iso)                          ms-Zeitstempel (12:00 UTC) des Datums
     addDays(iso, n)                   Datum + n Kalendertage → ISO
     monthsBack(t, m)                  Zeitstempel t minus m Monate, ohne Monatsüberlauf → Zeitstempel
     settleDays(cur)                   Valuta in Tagen: USD/GBP 1, sonst 2
     settle(iso, cur)                  Valutatag zum Handelstag → ISO (= addDays(iso, settleDays(cur)))
     yearsTo(maturity, from)           Restlaufzeit in Jahren (Tage / 365,25)
     couponDates(b, settle)            { dates: [künftige Kupontermine (ms), aufsteigend], prev: letzter Termin davor (ms),
                                         last: Anteil des letzten Kupons (1 = voll; kleiner bei kurzer Schlussperiode) }
                                       (Termine je Anleihe einmal erzeugt und zwischengespeichert – schnell für lange Reihen)
     accrued(b, settle)                Stückzinsen in % vom Nennwert
     pricer(b, settle)                 { price(y), slope(y) } – Clean-Kurs und Ableitung als Funktion der Rendite
     cleanPrice(b, y, settle)          Clean-Kurs (%) bei Rendite y
     dirtyPrice(b, y, settle)          Kurs inkl. Stückzinsen
     yieldFromPrice(b, p, settle[, start])  Rendite (dezimal) aus Clean-Kurs p; Newton, Rückfall Halbierung im Bereich −2 … 30 %
     duration(b, y, settle)            { macaulay, modified } in Jahren
     fmt(v, dec)                       wie MC.zahl: „1.234,50“, keine Zahl → „–“
     fmtDate(iso)                      „TT.MM.JJJJ“, ungültig → „–“
     fmtCoupon(c)                      Kupon mit 2 oder 3 Nachkommastellen („2,50“ / „2,125“)
     fmtVol(v[, einheit])              Volumen in Mrd., höchstens drei gültige Ziffern („1,25 Mrd.“)
     fmtStk(v)                         Stückelung („0,001“ · „0,01“ · „1.000“ · „200.000“)
*/
(function (MC) {
  "use strict";
  MC = window.MC = MC || {};

  var DAY = 86400000;
  var ISO = /^(\d{4})-(\d{2})-(\d{2})/;
  function utc(iso) { var m = ISO.exec(String(iso)); return m ? Date.UTC(+m[1], +m[2] - 1, +m[3], 12) : NaN; }
  function isoOf(t) { return new Date(t).toISOString().slice(0, 10); }
  function addDays(iso, n) { var d = new Date(utc(iso)); d.setUTCDate(d.getUTCDate() + n); return isoOf(d.getTime()); }
  // Monat zurückrechnen ohne Überlauf (31.05. → 30.11.). Ist t ein Monatsletzter am 30. oder 31., bleibt das Ergebnis ein
  // Monatsletzter (30.11. → 31.05., wie bei US-Staatsanleihen; vorher 30.05., Nutzertest 03.10.2026). Ende Februar bleibt beim
  // Tag – ob dort der 28. oder der Monatsletzte gemeint ist, lässt sich nicht erkennen. Gleiche Regel in scripts/_common.py.
  function monthsBack(t, m) {
    var d = new Date(t), day = d.getUTCDate(), ende = day >= 30 && new Date(t + DAY).getUTCDate() === 1;
    d.setUTCDate(1); d.setUTCMonth(d.getUTCMonth() - m);
    var last = new Date(Date.UTC(d.getUTCFullYear(), d.getUTCMonth() + 1, 0, 12)).getUTCDate();
    d.setUTCDate(ende ? last : Math.min(day, last));
    return d.getTime();
  }
  function settleDays(cur) { return cur === "USD" || cur === "GBP" ? 1 : 2; }
  function settle(iso, cur) { return addDays(iso, settleDays(cur)); }
  function yearsTo(maturity, from) { return (utc(maturity) - utc(from)) / DAY / 365.25; }

  // Kupontermine: vom Fälligkeitstag in Schritten von 12/freq Monaten rückwärts – immer vom Fälligkeitstag aus
  // gerechnet (Monatsende bleibt Monatsende). Die Folge hängt nur von der Anleihe ab; sie wird einmal je Anleihe bis
  // 1970 erzeugt (Cache nach Fälligkeit/Häufigkeit) und je Valutatag per Binärsuche geschnitten. Davor schrittweise.
  var FLOOR = Date.UTC(1970, 0, 1), CACHE = {};
  function folge(b) {
    var key = b.maturity + "/" + b.freq;
    if (CACHE[key]) return CACHE[key];
    var mat = utc(b.maturity), step = 12 / b.freq, seq = [], k = 0, t = mat;
    while (t > FLOOR) { seq.unshift(t); k++; t = monthsBack(mat, k * step); }
    seq.unshift(t);   // erstes Element ≤ 1970
    return (CACHE[key] = seq);
  }
  // Mit Zinstagen (b.days): alle Zinstage ab 1969, die mehr als TOL Tage vor der Fälligkeit liegen, dann der Fälligkeitstag.
  // last = Anteil des letzten Kupons: 1, wenn die Fälligkeit (bis auf TOL Tage) auf einem Zinstag liegt, sonst nach Tagen.
  var TOL = 20 * DAY;
  function folgeTage(b) {
    var key = b.maturity + "/" + b.freq + "/" + b.days.join(",");
    if (CACHE[key]) return CACHE[key];
    var mat = utc(b.maturity), jahr = new Date(mat).getUTCFullYear(), alle = [], j, i;
    for (j = 1969; j <= jahr + 1; j++) for (i = 0; i < b.days.length; i++) {
      var mo = +b.days[i].slice(0, 2), tg = +b.days[i].slice(3), letzter = new Date(Date.UTC(j, mo, 0, 12)).getUTCDate();
      alle.push(Date.UTC(j, mo - 1, Math.min(tg, letzter), 12));
    }
    alle.sort(function (x, y) { return x - y; });
    var seq = alle.filter(function (t) { return t < mat - TOL; });
    var danach = alle.filter(function (t) { return t >= mat - TOL; })[0];
    var voll = danach != null && Math.abs(danach - mat) <= TOL;
    var last = voll || !seq.length ? 1 : b.freq * (mat - seq[seq.length - 1]) / DAY / 365.25;
    seq.push(mat);
    return (CACHE[key] = { seq: seq, last: last });
  }
  function couponDates(b, settleIso) {
    var s = utc(settleIso), mat = utc(b.maturity), step = 12 / b.freq;
    if (b.days && b.days.length) {
      var f = folgeTage(b), q = f.seq, a = 1, e = q.length;
      while (a < e) { var h = (a + e) >> 1; if (q[h] > s) e = h; else a = h + 1; }
      return { dates: q.slice(a), prev: q[a - 1], last: f.last };
    }
    if (s <= FLOOR) {
      var out = [], k = 0, t = mat;
      while (t > s) { out.unshift(t); k++; t = monthsBack(mat, k * step); }
      return { dates: out, prev: t, last: 1 };
    }
    var seq = folge(b), lo = 1, hi = seq.length;   // erster Termin nach dem Valutatag
    while (lo < hi) { var m = (lo + hi) >> 1; if (seq[m] > s) hi = m; else lo = m + 1; }
    return { dates: seq.slice(lo), prev: seq[lo - 1], last: 1 };
  }
  function accrued(b, settleIso) {
    var s = utc(settleIso), cd = couponDates(b, settleIso);
    if (!cd.dates.length) return 0;
    return b.coupon / b.freq * (s - cd.prev) / (cd.dates[0] - cd.prev);
  }
  // Clean-Kurs als Funktion der Rendite für einen Valutatag – Laufzeiten der Zahlungen einmal vorberechnet
  function pricer(b, settleIso) {
    var s = utc(settleIso), cd = couponDates(b, settleIso), dates = cd.dates, n = dates.length, c = b.coupon / b.freq;
    var tau = dates.map(function (t) { return (t - s) / DAY / 365.25; });
    var cf = dates.map(function (t, i) { return i === n - 1 ? c * cd.last + 100 : c; });
    var acc = n ? c * (s - cd.prev) / (dates[0] - cd.prev) : 0;
    return {
      price: function (y) { var pv = 0; for (var i = 0; i < n; i++) pv += cf[i] / Math.pow(1 + y, tau[i]); return pv - acc; },
      slope: function (y) { var d = 0; for (var i = 0; i < n; i++) d -= tau[i] * cf[i] / Math.pow(1 + y, tau[i] + 1); return d; },
      tau: tau, cf: cf, accrued: acc
    };
  }
  function cleanPrice(b, y, settleIso) { return pricer(b, settleIso).price(y); }
  function dirtyPrice(b, y, settleIso) { var f = pricer(b, settleIso); return f.price(y) + f.accrued; }
  // Rendite aus dem Kurs: Newton-Verfahren (wenige Schritte); konvergiert es nicht im Bereich −2 … 30 %,
  // Halbierung mit 80 Schritten auf derselben Kursfunktion (Ergebnis wie die frühere reine Halbierung).
  function yieldFromPrice(b, p, settleIso, start) {
    var f = pricer(b, settleIso), y = start != null && isFinite(start) ? start : 0.03;
    for (var i = 0; i < 40; i++) {
      var step = (f.price(y) - p) / f.slope(y);
      if (!isFinite(step)) break;
      y -= step;
      if (!(y > -0.02 && y < 0.30)) break;
      if (Math.abs(step) < 1e-12) return y;
    }
    var lo = -0.02, hi = 0.30;
    for (var j = 0; j < 80; j++) { var mid = (lo + hi) / 2; if (f.price(mid) > p) lo = mid; else hi = mid; }
    return (lo + hi) / 2;
  }
  function duration(b, y, settleIso) {
    var f = pricer(b, settleIso), pv = 0, t = 0;
    for (var i = 0; i < f.tau.length; i++) { var x = f.cf[i] / Math.pow(1 + y, f.tau[i]); pv += x; t += f.tau[i] * x; }
    var mac = pv ? t / pv : 0;
    return { macaulay: mac, modified: mac / (1 + y) };
  }

  // ---------- Formate ----------
  function fmt(v, dec) {
    if (MC.zahl) return MC.zahl(v, dec || 0);
    if (typeof v !== "number" || !isFinite(v)) return "–";
    var s = v.toLocaleString("de-DE", { minimumFractionDigits: dec || 0, maximumFractionDigits: dec || 0 });
    return s.replace(/^-/, "−");
  }
  function fmtDate(iso) { var m = ISO.exec(String(iso || "")); return m ? m[3] + "." + m[2] + "." + m[1] : "–"; }
  function fmtCoupon(c) { return fmt(c, Math.round(c * 1000) % 10 ? 3 : 2); }
  function fmtVol(v, einheit) { return (v / 1e9).toLocaleString("de-DE", { maximumSignificantDigits: 3 }) + " " + (einheit || "Mrd."); }
  function fmtStk(v) { return v.toLocaleString("de-DE", { maximumFractionDigits: 3 }); }   // drei Stellen seit 01.10.2026: Landesanleihen mit Stückelung 0,001 standen als „0“ da

  MC.bond = {
    DAY: DAY, utc: utc, addDays: addDays, monthsBack: monthsBack, settleDays: settleDays, settle: settle, yearsTo: yearsTo,
    couponDates: couponDates, accrued: accrued, pricer: pricer, cleanPrice: cleanPrice, dirtyPrice: dirtyPrice,
    yieldFromPrice: yieldFromPrice, duration: duration,
    fmt: fmt, fmtDate: fmtDate, fmtCoupon: fmtCoupon, fmtVol: fmtVol, fmtStk: fmtStk
  };
})(window.MC);
