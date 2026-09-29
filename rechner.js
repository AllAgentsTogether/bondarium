// Anleihen-Rechner (rechner.html, 25.09.2026): vier Rechner, alles im Browser, keine Daten-Requests.
// 1 Rendite aus Kurs, Kupon, Fälligkeit · 2 Stückzinsen · 3 Netto nach Steuer · 4 Kurs bei verändertem Zinsniveau.
// Konventionen: Zinstage ACT/ACT, jährliche Verzinsung (ISMA), Valuta = heute + 2 Tage. Ergebnisse gerundet, keine Beratung.
(function () {
  "use strict";
  var MCX = window.MC || {};
  var minus = MCX.minus || function (s) { return String(s).replace(/^-/, "−"); };
  var DAY = 86400000;
  function $(id) { return document.getElementById(id); }
  // Deutsche Zahlen: "10.000" = 10000, "96,5" = 96.5, "1.234,56" = 1234.56; Zeichen wie % oder € werden ignoriert.
  function parseDe(str) {
    var v = String(str).replace(/[^\d,.\-]/g, "");
    if (!v) return NaN;
    if (v.indexOf(",") >= 0) v = v.replace(/\./g, "").replace(",", ".");
    else if (/^\-?\d{1,3}(\.\d{3})+$/.test(v)) v = v.replace(/\./g, "");
    var n = parseFloat(v);
    return isFinite(n) ? n : NaN;
  }
  function num(id, def) { var el = $(id); if (!el) return def; var n = parseDe(el.value); return isNaN(n) ? def : n; }
  function leerFeld(id) { var el = $(id); return !el || !String(el.value).trim(); }
  // Datum als Text: TT.MM.JJJJ (auch T.M.JJ, TT/MM/JJJJ oder JJJJ-MM-TT) – Textfeld statt Datumswähler, damit z. B. 2070 direkt eingetippt werden kann
  function dat(id) {
    var el = $(id); if (!el) return null;
    var v = String(el.value).trim(), m, d, mo, y;
    if (!v) return null;
    if ((m = v.match(/^(\d{1,2})[.\/ ](\d{1,2})[.\/ ](\d{2}|\d{4})$/))) { d = +m[1]; mo = +m[2]; y = +m[3]; if (y < 100) y += 2000; }
    else if ((m = v.match(/^(\d{4})-(\d{1,2})-(\d{1,2})$/))) { y = +m[1]; mo = +m[2]; d = +m[3]; }
    else return null;
    var dt = new Date(y, mo - 1, d, 12, 0, 0);
    if (dt.getFullYear() !== y || dt.getMonth() !== mo - 1 || dt.getDate() !== d) return null;
    return dt;
  }
  function fmt(v, dec) { if (!isFinite(v)) return "–"; return minus(v.toLocaleString("de-DE", { minimumFractionDigits: dec, maximumFractionDigits: dec })); }
  function eur(v) { return fmt(v, 2) + "\u00A0€"; }   // geschütztes Leerzeichen vor der Einheit
  // Rechner 1 in der Währung der Anleihe, wenn der Steckbrief sie übergibt (?w=USD, seit 29.09.2026)
  var EINH1 = "€";
  function geld1(v) { return fmt(v, 2) + "\u00A0" + EINH1; }
  function pct(v, dec) { return fmt(v, dec == null ? 2 : dec) + "\u00A0%"; }
  function fmtDate(d) { return d.toLocaleDateString("de-DE", { day: "2-digit", month: "2-digit", year: "numeric" }); }
  function iso(d) { return String(d.getDate()).padStart(2, "0") + "." + String(d.getMonth() + 1).padStart(2, "0") + "." + d.getFullYear(); }   // Vorbelegung der Textfelder
  function addMonths(d, m) { var r = new Date(d.getTime()); var day = r.getDate(); r.setDate(1); r.setMonth(r.getMonth() + m); var last = new Date(r.getFullYear(), r.getMonth() + 1, 0).getDate(); r.setDate(Math.min(day, last)); return r; }
  function days(a, b) { return Math.round((b.getTime() - a.getTime()) / DAY); }
  function setText(id, t) { var el = $(id); if (el) el.textContent = t; }
  function valuta() {   // heute + 2 Bankarbeitstage (Wochenenden übersprungen; Feiertage nicht berücksichtigt)
    var d = new Date(); d.setHours(12, 0, 0, 0); var n = 0;
    while (n < 2) { d = new Date(d.getTime() + DAY); if (d.getDay() !== 0 && d.getDay() !== 6) n++; }
    return d;
  }

  // Kupontermine rückwärts von der Fälligkeit; liefert letzten Termin vor settle und alle folgenden
  function schedule(maturity, freq, settle) {
    var step = 12 / freq, dates = [], d = new Date(maturity.getTime());
    var guard = 0;
    while (d > settle && guard++ < 2000) { dates.push(d); d = addMonths(d, -step); }
    dates.reverse();
    return { prev: d, next: dates };
  }
  // Barwert je 100 Nennwert (dirty) bei Rendite y (jährlich, taggenau)
  function pv(coupon, freq, sched, settle, y) {
    var p = 0, i, d, t, cf, mat = sched.next[sched.next.length - 1];
    for (i = 0; i < sched.next.length; i++) {
      d = sched.next[i]; t = days(settle, d) / 365.25;
      cf = coupon / freq + (d.getTime() === mat.getTime() ? 100 : 0);
      p += cf / Math.pow(1 + y, t);
    }
    return p;
  }
  function accrued(coupon, freq, sched, settle) {
    var next = sched.next[0], prev = sched.prev, per = days(prev, next);
    return per > 0 ? coupon / freq * days(prev, settle) / per : 0;
  }
  function solveYield(coupon, freq, sched, settle, dirty) {
    var lo = -0.5, hi = 5.0, mid, i;
    for (i = 0; i < 90; i++) { mid = (lo + hi) / 2; if (pv(coupon, freq, sched, settle, mid) > dirty) lo = mid; else hi = mid; }
    return (lo + hi) / 2;
  }

  // ---------- 1 Rendite ----------
  function rendite() {
    var kurs = num("r1-kurs", NaN), kupon = num("r1-kupon", NaN), nenn = num("r1-nenn", NaN), freq = num("r1-freq", 1), mat = dat("r1-faellig");
    var settle = valuta();
    function leer(msg) { ["r1-rendite", "r1-jahre", "r1-kauf", "r1-stz", "r1-gesamt", "r1-zinsen", "r1-rueck", "r1-gewinn"].forEach(function (id) { setText(id, "–"); }); setText("r1-out", msg); }
    if (leerFeld("r1-kurs") || leerFeld("r1-kupon") || leerFeld("r1-nenn") || leerFeld("r1-faellig")) { leer("Bitte Kurs, Kupon, Fälligkeit und Nennwert eingeben – der Kupon darf 0 sein."); return; }
    if (isNaN(kurs) || isNaN(kupon) || isNaN(nenn)) { leer("Eine Eingabe ist keine Zahl. Schreibweise: 96,50 oder 10.000."); return; }
    if (!mat) { leer("Bitte die Fälligkeit als Datum eingeben, zum Beispiel 15.08.2033."); return; }
    if (mat <= settle) { leer("Die Fälligkeit muss nach der Valuta (" + fmtDate(settle) + ") liegen."); return; }
    if (kurs <= 0 || nenn <= 0 || kupon < 0 || kupon > 30 || kurs > 300) { leer("Bitte prüfe die Eingaben: Kurs in Prozent (z. B. 96,50), Kupon in Prozent pro Jahr, Nennwert in Euro."); return; }
    var sched = schedule(mat, freq, settle), acc = accrued(kupon, freq, sched, settle), dirty = kurs + acc;
    // Marktkonvention: Im letzten Kuponabschnitt (nur noch eine Zahlung) einfache Verzinsung, sonst Rendite mit jährlichem Zinseszins (ISMA)
    var einfach = sched.next.length === 1, y;
    if (einfach) { y = (100 + kupon / freq - dirty) / dirty * 365 / days(settle, mat); }
    else { y = solveYield(kupon, freq, sched, settle, dirty); }
    var jahre = days(settle, mat) / 365.25;
    var zinsenSumme = sched.next.length * kupon / freq * nenn / 100;
    var kauf = kurs * nenn / 100, stz = acc * nenn / 100, gesamt = kauf + stz;
    var gewinn = zinsenSumme + nenn - gesamt;
    setText("r1-rendite", pct(y * 100));
    setText("r1-jahre", fmt(jahre, 1) + " Jahre");
    setText("r1-kauf", geld1(kauf));
    setText("r1-stz", geld1(stz) + " (" + days(sched.prev, settle) + " Tage)");
    setText("r1-gesamt", geld1(gesamt));
    setText("r1-zinsen", geld1(zinsenSumme) + " (" + sched.next.length + (sched.next.length === 1 ? " Zahlung)" : " Zahlungen)"));
    setText("r1-rueck", geld1(nenn) + " am " + fmtDate(mat));
    setText("r1-gewinn", geld1(gewinn));
    var hinweis = "";
    if (y > 0.25 || y < -0.05) hinweis = " Die Rendite ist unplausibel – prüfe Kurs und Fälligkeit (Kurs in Prozent des Nennwerts, z. B. 96,50).";
    else if (einfach) hinweis = " Restlaufzeit unter einem Kuponabschnitt: einfache Verzinsung aufs Jahr hochgerechnet, wie am Geldmarkt üblich.";
    setText("r1-out", "Rendite bei Kauf zu " + pct(kurs) + " mit Valuta " + fmtDate(settle) + ", bis zur Fälligkeit gehalten, vor Steuern und Gebühren. Letzter Zinstermin: " + fmtDate(sched.prev) + ", nächster: " + fmtDate(sched.next[0]) + "." + hinweis);
    var g = $("r1-gewinn"); if (g) g.className = "big " + (gewinn >= 0 ? "up" : "down");
  }

  // ---------- 2 Stückzinsen ----------
  function stueckzinsen() {
    var nenn = num("r2-nenn", NaN), kupon = num("r2-kupon", NaN), freq = num("r2-freq", 1), last = dat("r2-letzter"), val = dat("r2-valuta") || valuta();
    if (leerFeld("r2-nenn") || leerFeld("r2-kupon") || isNaN(nenn) || isNaN(kupon)) { setText("r2-out", "Bitte Nennwert und Kupon als Zahl eingeben (z. B. 10.000 und 3,00)."); setText("r2-stz", "–"); setText("r2-tage", "–"); setText("r2-next", "–"); return; }
    if (!last) { setText("r2-out", "Bitte den letzten Zinstermin als Datum eingeben, zum Beispiel 15.08.2026."); setText("r2-stz", "–"); return; }
    if (!$("r2-valuta").value.trim()) val = valuta();
    if (!dat("r2-valuta") && $("r2-valuta").value.trim()) { setText("r2-out", "Bitte die Valuta als Datum eingeben (TT.MM.JJJJ)."); setText("r2-stz", "–"); return; }
    var next = addMonths(last, 12 / freq), per = days(last, next), t = days(last, val);
    if (t < 0 || t > per) { setText("r2-out", "Die Valuta muss zwischen dem letzten und dem nächsten Zinstermin (" + fmtDate(next) + ") liegen."); setText("r2-stz", "–"); return; }
    var stz = nenn * kupon / 100 / freq * t / per;
    setText("r2-stz", eur(stz));
    setText("r2-tage", t + " von " + per + " Tagen");
    setText("r2-next", eur(nenn * kupon / 100 / freq) + " am " + fmtDate(next));
    setText("r2-out", "Du zahlst dem Verkäufer die Zinsen für " + t + " Tage seit dem " + fmtDate(last) + ". Am " + fmtDate(next) + " bekommst du den vollen Kupon – die Stückzinsen sind damit zurück. Steuerlich mindern gezahlte Stückzinsen deine Kapitalerträge im Kaufjahr.");
  }

  // ---------- 3 Netto nach Steuer ----------
  var SATZ = { "0": 0.26375, "8": 0.27819, "9": 0.27995 };   // Abgeltungsteuer 25 % + Soli 5,5 %; mit Kirchensteuer 8 %/9 % (Kirchensteuer mindert die Abgeltungsteuer)
  function netto() {
    var betrag = num("r3-betrag", NaN), rend = num("r3-rendite", NaN), jahre = num("r3-jahre", 1), kist = String(num("r3-kist", 0)), fsa = num("r3-fsa", 0);
    if (isNaN(betrag) || isNaN(rend)) { ["r3-brutto", "r3-frei", "r3-steuer", "r3-netto", "r3-nrend", "r3-gesamt"].forEach(function (id) { setText(id, "–"); }); setText("r3-out", "Bitte Anlagebetrag und Rendite als Zahl eingeben (z. B. 50.000 und 3,20). Ein leerer Freistellungsauftrag zählt als 0\u00A0€."); return; }
    var satz = SATZ[kist] || SATZ["0"];
    var brutto = betrag * rend / 100, pflichtig = Math.max(0, brutto - fsa), steuer = pflichtig * satz, net = brutto - steuer;
    var nettoRend = betrag > 0 ? net / betrag * 100 : 0, eff = brutto > 0 ? steuer / brutto * 100 : 0;
    setText("r3-brutto", eur(brutto));
    setText("r3-frei", eur(Math.min(brutto, fsa)));
    setText("r3-steuer", eur(steuer) + (steuer > 0 ? " (" + pct(eff, 1) + " der Zinsen)" : ""));
    setText("r3-netto", eur(net));
    setText("r3-nrend", pct(nettoRend));
    setText("r3-gesamt", eur(net * jahre) + " in " + fmt(jahre, jahre % 1 === 0 ? 0 : 1) + (jahre === 1 ? " Jahr" : " Jahren"));   // 2,5 Jahre bleiben 2,5
    var abg = 25 / (1 + 0.25 * (+kist) / 100);   // Kirchensteuer mindert die Abgeltungsteuer: 25 % / (1 + 0,25 × Kirchensteuersatz)
    setText("r3-out", "Steuersatz auf Zinsen: " + pct(satz * 100, 3).replace(",000", "") + (kist !== "0"
      ? " (Abgeltungsteuer " + pct(abg, 2) + " – die Kirchensteuer mindert sie –, Solidaritätszuschlag 5,5\u00A0% darauf und Kirchensteuer " + kist + "\u00A0% darauf)"
      : " (Abgeltungsteuer 25\u00A0% + Solidaritätszuschlag 5,5\u00A0% darauf)") + ". Der Freistellungsauftrag (Sparer-Pauschbetrag 1.000\u00A0€ je Person, 2.000\u00A0€ bei Zusammenveranlagung) gilt je Jahr für alle Kapitalerträge zusammen. Ohne Zinseszins gerechnet; persönliche Umstände (Günstigerprüfung, Verlusttopf) nicht berücksichtigt.");
  }

  // ---------- 4 Zinsniveau ----------
  function zinsniveau() {
    var kupon = num("r4-kupon", NaN), jahre = num("r4-jahre", NaN), y0 = num("r4-rendite", NaN) / 100;
    if (isNaN(kupon) || isNaN(jahre) || isNaN(y0) || jahre <= 0 || jahre > 120) { ["r4-kurs", "r4-dur", "r4-m2", "r4-m1", "r4-p1", "r4-p2"].forEach(function (id) { setText(id, "–"); }); setText("r4-out", "Bitte Kupon, Restlaufzeit (über 0, höchstens 120 Jahre) und Rendite als Zahl eingeben."); return; }
    function price(y) { var p = 0, n = Math.ceil(jahre), i, t; for (i = 1; i <= n; i++) { t = jahre - (n - i); p += kupon / Math.pow(1 + y, t); } return p + 100 / Math.pow(1 + y, jahre); }
    // Kurs wie beim Broker: ohne Stückzinsen. Bei gebrochener Restlaufzeit liegt der nächste Kupon in t0 < 1 Jahr, aufgelaufen ist kupon × (1 − t0).
    var t0 = jahre - (Math.ceil(jahre) - 1), acc = kupon * (1 - t0);
    function clean(y) { return price(y) - acc; }
    var p0 = clean(y0), rows = [[-2, "r4-m2"], [-1, "r4-m1"], [1, "r4-p1"], [2, "r4-p2"]], i, p, ch, el;
    for (i = 0; i < rows.length; i++) {
      p = clean(y0 + rows[i][0] / 100); ch = (p / p0 - 1) * 100;
      setText(rows[i][1], (ch > 0.05 ? "+" : "") + pct(ch, 1));
      el = $(rows[i][1] + "-bar"); if (el) { el.style.width = Math.min(100, Math.abs(ch) / 40 * 100) + "%"; el.className = "zb " + (ch < 0 ? "down" : "up"); }
      el = $(rows[i][1]); if (el) el.className = "zv " + (ch < 0 ? "down" : "up");
    }
    var dur = (price(y0 - 0.0005) - price(y0 + 0.0005)) / (2 * 0.0005) / price(y0);   // modifizierte Duration auf den vollen Preis (mit Stückzinsen)
    setText("r4-kurs", pct(p0));
    setText("r4-dur", fmt(dur, 1));
    setText("r4-out", "Kurs heute (ohne Stückzinsen) bei " + pct(y0 * 100) + " Rendite: " + pct(p0) + ". Modifizierte Duration " + fmt(dur, 1) + " – so viel Prozent verliert der Kurs ungefähr je Prozentpunkt, den das allgemeine Zinsniveau steigt. Die Balken zeigen die genaue Rechnung (mit Konvexität: der Gewinn bei fallendem Zinsniveau ist größer als der Verlust bei steigendem).");
  }

  function bind(ids, fn) { ids.forEach(function (id) { var el = $(id); if (el) { el.addEventListener("input", fn); el.addEventListener("change", fn); } }); fn(); }
  // Beim Verlassen eines Felds die Zahl sauber schreiben: Euro mit Tausenderpunkt, Prozent mit zwei Nachkommastellen
  function schoen(id, dec) { var el = $(id); if (!el) return; el.addEventListener("blur", function () { var n = parseDe(el.value); if (!isNaN(n) && el.value.trim()) el.value = n.toLocaleString("de-DE", { minimumFractionDigits: dec, maximumFractionDigits: Math.max(dec, 3) }); }); }
  function init() {
    var v = valuta(), f = $("r1-faellig"), l = $("r2-letzter"), rv = $("r2-valuta");
    // Vorbelegung aus dem Steckbrief (anleihe.html, seit 29.09.2026): ?kurs=99,99&kupon=1,625&faellig=30.09.2026&freq=2&w=USD
    var q = new URLSearchParams(location.search);
    [["kurs", "r1-kurs"], ["kupon", "r1-kupon"], ["faellig", "r1-faellig"], ["nenn", "r1-nenn"]].forEach(function (x) { var w = q.get(x[0]), el = $(x[1]); if (w && el && /^[\d.,]{1,12}$/.test(w)) el.value = w; });
    var fq = q.get("freq"), fs = $("r1-freq"); if (fs && (fq === "1" || fq === "2")) fs.value = fq;
    var wq = q.get("w"), nn = $("r1-nenn"); if (wq && /^[A-Z]{3}$/.test(wq) && wq !== "EUR") { EINH1 = wq; if (nn && nn.nextElementSibling) nn.nextElementSibling.textContent = wq; }
    if (f && !f.value) { f.value = "15.08." + (v.getFullYear() + 5); }   // mitten im Kuponjahr, damit Stückzinsen sichtbar sind
    if (l && !l.value) { var last = new Date(v.getTime()); last.setMonth(last.getMonth() - 4); l.value = iso(last); }
    if (rv && !rv.value) rv.value = iso(v);
    bind(["r1-kurs", "r1-kupon", "r1-faellig", "r1-nenn", "r1-freq"], rendite);
    bind(["r2-nenn", "r2-kupon", "r2-freq", "r2-letzter", "r2-valuta"], stueckzinsen);
    bind(["r3-betrag", "r3-rendite", "r3-jahre", "r3-kist", "r3-fsa"], netto);
    bind(["r4-kupon", "r4-jahre", "r4-rendite"], zinsniveau);
    ["r1-nenn", "r2-nenn", "r3-betrag", "r3-fsa"].forEach(function (id) { schoen(id, 0); });
    ["r1-kurs", "r1-kupon", "r2-kupon", "r3-rendite", "r4-kupon", "r4-rendite"].forEach(function (id) { schoen(id, 2); });
    ["r1-nenn", "r2-nenn", "r3-betrag", "r3-fsa"].forEach(function (id) { var el = $(id); if (el) el.dispatchEvent(new Event("blur")); });
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init); else init();
})();
