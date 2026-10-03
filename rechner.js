// Anleihen-Rechner (rechner.html, 25.09.2026): vier Rechner, alles im Browser, keine Daten-Requests.
// 1 Rendite aus Kurs, Kupon, Fälligkeit · 2 Stückzinsen · 3 Netto nach Steuer · 4 Kurs bei verändertem Zinsniveau.
// Konventionen: Zinstage ACT/ACT, jährliche Verzinsung (ISMA), Valuta = heute + 2 Bankarbeitstage. Ergebnisse gerundet, keine Beratung.
// Seit 30.09.2026: Rechner 1 nutzt die gemeinsame Anleihen-Mathematik aus bond.js (MC.bond: Kupontermine, Stückzinsen,
// Barwert); Datumsfelder nehmen auch Ziffernfolgen (15082033, 150833); Prozentfelder lesen den Punkt als Komma (3.125);
// Plausibilitätsgrenzen je Feld mit aria-invalid; Ergebnis und Fehler werden entprellt über eine Live-Region angesagt.
(function () {
  "use strict";
  var MCX = window.MC || {};
  var minus = MCX.minus || function (s) { return String(s).replace(/^-/, "−"); };
  var BOND = MCX.bond;   // bond.js (nach site.js geladen)
  var DAY = 86400000;
  function $(id) { return document.getElementById(id); }
  // Deutsche Zahlen: "10.000" = 10000, "96,5" = 96.5, "1.234,56" = 1234.56; Zeichen wie % oder € werden ignoriert.
  // dezimal = true (Prozent- und Jahresfelder): ohne Komma gilt ein einzelner Punkt als Dezimalzeichen ("3.125" = 3,125 %),
  // denn Tausender kommen dort nicht vor und viele Handys bieten nur den Punkt an.
  function parseDe(str, dezimal) {
    var v = String(str).replace(/\u2212/g, "-").replace(/[^\d,.\-]/g, "");
    if (!v) return NaN;
    if (v.indexOf(",") >= 0) v = v.replace(/\./g, "").replace(",", ".");
    else if (dezimal && (v.match(/\./g) || []).length === 1) { /* Punkt = Dezimalzeichen */ }
    else if (/^\-?\d{1,3}(\.\d{3})+$/.test(v)) v = v.replace(/\./g, "");
    var n = parseFloat(v);
    return isFinite(n) ? n : NaN;
  }
  // Felder, in denen der Punkt Dezimalzeichen ist (Prozent und Jahre)
  var DEZ = { "r1-kurs": 1, "r1-kupon": 1, "r2-kupon": 1, "r3-rendite": 1, "r3-jahre": 1, "r4-kupon": 1, "r4-jahre": 1, "r4-rendite": 1 };
  function num(id, def) { var el = $(id); if (!el) return def; var n = parseDe(el.value, !!DEZ[id]); return isNaN(n) ? def : n; }
  function leerFeld(id) { var el = $(id); return !el || !String(el.value).trim(); }
  // Datum als Text: TT.MM.JJJJ (auch T.M.JJ, TT/MM/JJJJ, TT-MM-JJJJ oder JJJJ-MM-TT) – Textfeld statt Datumswähler, damit z. B.
  // 2070 direkt eingetippt werden kann. Seit 30.09.2026 auch reine Ziffern (Handy-Ziffernblock ohne Punkt):
  // 15082033 = 15.08.2033, 150833 = 15.08.2033, 20330815 = 15.08.2033. Zweistellige Jahre zählen als 20JJ.
  function datText(v) {
    v = String(v).trim();
    var m, d, mo, y;
    if (!v) return null;
    if ((m = v.match(/^(\d{1,2})[.\/ -](\d{1,2})[.\/ -](\d{2}|\d{4})\.?$/))) { d = +m[1]; mo = +m[2]; y = +m[3]; }
    else if ((m = v.match(/^(\d{4})-(\d{1,2})-(\d{1,2})$/))) { y = +m[1]; mo = +m[2]; d = +m[3]; }
    else if ((m = v.match(/^(\d{2})(\d{2})(\d{4})$/)) || (m = v.match(/^(\d{2})(\d{2})(\d{2})$/))) {
      d = +m[1]; mo = +m[2]; y = +m[3];
      if (m[3].length === 4 && !gueltig(d, mo, y) && (m = v.match(/^(\d{4})(\d{2})(\d{2})$/))) { y = +m[1]; mo = +m[2]; d = +m[3]; }
    }
    else return null;
    if (y < 100) y += 2000;
    return gueltig(d, mo, y) ? new Date(y, mo - 1, d, 12, 0, 0) : null;
  }
  function gueltig(d, mo, y) { var dt = new Date(y, mo - 1, d, 12, 0, 0); return y >= 1900 && dt.getFullYear() === y && dt.getMonth() === mo - 1 && dt.getDate() === d; }
  function dat(id) { var el = $(id); return el ? datText(el.value) : null; }
  function fmt(v, dec) { if (MCX.zahl) return MCX.zahl(v, dec); if (!isFinite(v)) return "–"; return minus(v.toLocaleString("de-DE", { minimumFractionDigits: dec, maximumFractionDigits: dec })); }
  function eur(v) { return fmt(v, 2) + "\u00A0€"; }   // geschütztes Leerzeichen vor der Einheit
  // Rechner 1 in der Währung der Anleihe, wenn der Steckbrief sie übergibt (?w=USD, seit 29.09.2026)
  var EINH1 = "€", EINH2 = "€";   // Rechner 2 seit 03.10.2026 ebenso in der Währung aus dem Steckbrief
  function geld1(v) { return fmt(v, 2) + "\u00A0" + EINH1; }
  function geld2(v) { return fmt(v, 2) + "\u00A0" + EINH2; }
  function pct(v, dec) { return fmt(v, dec == null ? 2 : dec) + "\u00A0%"; }
  function fmtDate(d) { return d.toLocaleDateString("de-DE", { day: "2-digit", month: "2-digit", year: "numeric" }); }
  function iso(d) { return String(d.getDate()).padStart(2, "0") + "." + String(d.getMonth() + 1).padStart(2, "0") + "." + d.getFullYear(); }   // Vorbelegung der Textfelder
  function addMonths(d, m) { var r = new Date(d.getTime()); var day = r.getDate(); r.setDate(1); r.setMonth(r.getMonth() + m); var last = new Date(r.getFullYear(), r.getMonth() + 1, 0).getDate(); r.setDate(Math.min(day, last)); return r; }
  function days(a, b) { return Math.round((b.getTime() - a.getTime()) / DAY); }
  function setText(id, t) { var el = $(id); if (el) el.textContent = t; }
  function isoOf(d) { return d.getFullYear() + "-" + String(d.getMonth() + 1).padStart(2, "0") + "-" + String(d.getDate()).padStart(2, "0"); }

  // ---------- Fehler und Ansage (Barrierefreiheit) ----------
  // Jeder Rechner hat ein Hinweisfeld rN-out (per aria-describedby an allen Eingaben) und eine unsichtbare Live-Region rN-live.
  // Ungültige Felder bekommen aria-invalid="true". Die Live-Region wird erst 900 ms nach der letzten Eingabe gefüllt, damit
  // Screenreader nicht bei jedem Tastendruck ein Ergebnis vorlesen; beim ersten Rechnen (Seitenaufruf) wird nichts angesagt.
  var FELDER = {
    r1: ["r1-kurs", "r1-kupon", "r1-faellig", "r1-nenn", "r1-freq"],
    r2: ["r2-nenn", "r2-kupon", "r2-letzter", "r2-valuta", "r2-freq"],
    r3: ["r3-betrag", "r3-rendite", "r3-jahre", "r3-fsa", "r3-kist"],
    r4: ["r4-kupon", "r4-jahre", "r4-rendite"]
  };
  var bereit = false, timer = {};
  var ZT = null, R1 = null;   // Zinstage aus dem Steckbrief (?zt=MM-TT,…) und das letzte Ergebnis von Rechner 1
  function markiere(r, falsch) {
    FELDER[r].forEach(function (id) { var el = $(id); if (!el) return; if (falsch.indexOf(id) >= 0) el.setAttribute("aria-invalid", "true"); else el.removeAttribute("aria-invalid"); });
  }
  function ansage(r, text) {
    if (!bereit) return;
    clearTimeout(timer[r]);
    timer[r] = setTimeout(function () { var el = $(r + "-live"); if (el) { el.textContent = ""; el.textContent = text; } }, 900);
  }
  // Fehler anzeigen: Hinweistext, Markierung, Ansage. felder = Liste der ungültigen Feld-IDs.
  function fehler(r, felder, msg) {
    setText(r + "-out", msg);
    var o = $(r + "-out"); if (o) o.classList.add("fehler");
    markiere(r, felder);
    ansage(r, msg);
  }
  function ok(r, msg, ansageText) {
    setText(r + "-out", msg);
    var o = $(r + "-out"); if (o) o.classList.remove("fehler");
    markiere(r, []);
    ansage(r, ansageText);
  }
  // Grenzen je Feld: [min, max, Meldung]; min/max eingeschlossen, außer wo „über“ steht (dann > min)
  function pruefe(r, liste) {
    for (var i = 0; i < liste.length; i++) {
      var x = liste[i], v = x[1];
      if (isNaN(v) || v < x[2] || v > x[3] || (x[5] && v === x[2])) { fehler(r, [x[0]], x[4]); return false; }
    }
    return true;
  }
  // Valuta: Order am nächsten Handelstag (am Wochenende und an Börsenfeiertagen nicht heute), dann zwei Abwicklungstage – seit 03.10.2026
  // über MC.handelstag/MC.plusAbwicklungstage (site.js, mit Feiertagen); vorher heute + 2 Werktage (Nutzertest: Order am Samstag)
  function valuta() {
    var h = new Date();
    if (MCX.handelstag && MCX.plusAbwicklungstage) {
      var u = MCX.plusAbwicklungstage(MCX.handelstag(new Date(Date.UTC(h.getFullYear(), h.getMonth(), h.getDate(), 12))), 2);
      return new Date(u.getUTCFullYear(), u.getUTCMonth(), u.getUTCDate(), 12, 0, 0);
    }
    var d = new Date(); d.setHours(12, 0, 0, 0); var n = 0;
    while (n < 2) { d = new Date(d.getTime() + DAY); if (d.getDay() !== 0 && d.getDay() !== 6) n++; }
    return d;
  }

  // Kupontermine, Stückzinsen und Barwert kommen aus bond.js (MC.bond, gemeinsame Anleihen-Mathematik der Website).
  // Die Rendite sucht der Rechner selbst per Halbierung im weiten Bereich −50 … 500 %, damit auch unplausible Eingaben
  // ein Ergebnis mit Warnhinweis liefern (MC.bond.yieldFromPrice ist auf −2 … 30 % begrenzt).
  function solveYield(f, clean) {
    var lo = -0.5, hi = 5.0, mid, i;
    for (i = 0; i < 90; i++) { mid = (lo + hi) / 2; if (f.price(mid) > clean) lo = mid; else hi = mid; }
    return (lo + hi) / 2;
  }

  // ---------- 1 Rendite ----------
  function rendite() {
    var kurs = num("r1-kurs", NaN), kupon = num("r1-kupon", NaN), nenn = num("r1-nenn", NaN), freq = num("r1-freq", 1), mat = dat("r1-faellig");
    var settle = valuta();
    function leer(felder, msg) { ["r1-rendite", "r1-jahre", "r1-kauf", "r1-stz", "r1-gesamt", "r1-zinsen", "r1-rueck", "r1-gewinn"].forEach(function (id) { setText(id, "–"); }); if (msg) fehler("r1", felder, msg); }
    var fehlt = ["r1-kurs", "r1-kupon", "r1-faellig", "r1-nenn"].filter(leerFeld);
    if (fehlt.length) { leer(fehlt, "Bitte Kurs, Kupon, Fälligkeit und Nennwert eingeben – der Kupon darf 0 sein."); return; }
    if (!BOND) { leer([], "Der Rechenbaustein (bond.js) wurde nicht geladen. Bitte die Seite neu laden."); return; }
    if (!mat) { leer(["r1-faellig"], "Bitte die Fälligkeit als Datum eingeben, zum Beispiel 15.08.2033 oder 15082033."); return; }
    if (mat <= settle) { leer(["r1-faellig"], "Die Fälligkeit muss nach der Valuta (" + fmtDate(settle) + ") liegen."); return; }
    if (days(settle, mat) > 120 * 365.25) { leer(["r1-faellig"], "Die Fälligkeit liegt mehr als 120 Jahre in der Zukunft – bitte prüfen."); return; }
    if (!pruefe("r1", [
      ["r1-kurs", kurs, 0, 300, "Der Kurs wird in Prozent des Nennwerts angegeben, über 0 und höchstens 300 – zum Beispiel 96,50.", true],
      ["r1-kupon", kupon, 0, 30, "Der Kupon wird in Prozent pro Jahr angegeben, von 0 bis 30 – zum Beispiel 3,00."],
      ["r1-nenn", nenn, 0, 1e9, "Der Nennwert muss über 0 liegen (höchstens 1 Milliarde) – zum Beispiel 1.000 oder 10.000.", true]
    ])) { leer(); return; }
    var b = { coupon: kupon, freq: freq, maturity: isoOf(mat) }, sIso = isoOf(settle);
    if (ZT && $("r1-faellig").value.trim() === ZT.faellig && freq === ZT.freq) b.days = ZT.days;   // Zinstage laut Deutscher Börse (Steckbrief)
    var cd = BOND.couponDates(b, sIso), f = BOND.pricer(b, sIso);
    var sched = { prev: new Date(cd.prev), next: cd.dates.map(function (t) { return new Date(t); }) };
    var acc = f.accrued, dirty = kurs + acc;
    // Marktkonvention: Im letzten Kuponabschnitt (nur noch eine Zahlung) einfache Verzinsung, sonst Rendite mit jährlichem Zinseszins (ISMA)
    var einfach = sched.next.length === 1, y;
    if (einfach) { y = (100 + kupon / freq - dirty) / dirty * 365 / days(settle, mat); }
    else { y = solveYield(f, kurs); }
    var jahre = days(settle, mat) / 365.25;
    var zinsenSumme = sched.next.length * kupon / freq * nenn / 100;
    var kauf = kurs * nenn / 100, stz = acc * nenn / 100, gesamt = kauf + stz;
    var gewinn = zinsenSumme + nenn - gesamt;
    setText("r1-rendite", pct(y * 100));
    R1 = { rendite: y * 100, jahre: jahre, prev: sched.prev, kauf: kauf };
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
    ok("r1", "Rendite bei Kauf zu " + pct(kurs) + " mit Valuta " + fmtDate(settle) + ", bis zur Fälligkeit gehalten, vor Steuern und Gebühren. Letzter Zinstermin: " + fmtDate(sched.prev) + ", nächster: " + fmtDate(sched.next[0]) + "." + hinweis,
      "Rendite pro Jahr " + pct(y * 100) + ". Du zahlst " + geld1(gesamt) + ", Ertrag vor Steuern " + geld1(gewinn) + "." + hinweis);
    var g = $("r1-gewinn"); if (g) g.className = "big " + (gewinn >= 0 ? "up" : "down");
  }

  // ---------- 2 Stückzinsen ----------
  function stueckzinsen() {
    var nenn = num("r2-nenn", NaN), kupon = num("r2-kupon", NaN), freq = num("r2-freq", 1), last = dat("r2-letzter"), val = dat("r2-valuta") || valuta();
    function leer(felder, msg) { setText("r2-stz", "–"); setText("r2-tage", "–"); setText("r2-next", "–"); if (msg) fehler("r2", felder, msg); }
    var fehlt = ["r2-nenn", "r2-kupon"].filter(leerFeld);
    if (fehlt.length) { leer(fehlt, "Bitte Nennwert und Kupon als Zahl eingeben (z. B. 10.000 und 3,00)."); return; }
    if (!pruefe("r2", [
      ["r2-nenn", nenn, 0, 1e9, "Der Nennwert muss über 0 liegen (höchstens 1 Milliarde) – zum Beispiel 10.000.", true],
      ["r2-kupon", kupon, 0, 30, "Der Kupon wird in Prozent pro Jahr angegeben, von 0 bis 30 – zum Beispiel 3,00."]
    ])) { leer(); return; }
    if (!last) { leer(["r2-letzter"], "Bitte den letzten Zinstermin als Datum eingeben, zum Beispiel 15.08.2026 oder 15082026."); return; }
    if (!$("r2-valuta").value.trim()) val = valuta();
    if (!dat("r2-valuta") && $("r2-valuta").value.trim()) { leer(["r2-valuta"], "Bitte die Valuta als Datum eingeben (TT.MM.JJJJ oder nur Ziffern, z. B. 02102026)."); return; }
    var next = addMonths(last, 12 / freq), per = days(last, next), t = days(last, val);
    if (t < 0 || t > per) { leer(["r2-letzter", "r2-valuta"], "Die Valuta muss zwischen dem letzten und dem nächsten Zinstermin (" + fmtDate(next) + ") liegen."); return; }
    var stz = nenn * kupon / 100 / freq * t / per;
    setText("r2-stz", geld2(stz));
    setText("r2-tage", t + " von " + per + " Tagen");
    setText("r2-next", geld2(nenn * kupon / 100 / freq) + " am " + fmtDate(next));
    ok("r2", "Du zahlst dem Verkäufer die Zinsen für " + t + " Tage seit dem " + fmtDate(last) + ". Am " + fmtDate(next) + " bekommst du den vollen Kupon – die Stückzinsen sind damit zurück. Steuerlich mindern gezahlte Stückzinsen deine Kapitalerträge im Kaufjahr.",
      "Stückzinsen " + geld2(stz) + " für " + t + " von " + per + " Zinstagen.");
  }

  // ---------- 3 Netto nach Steuer ----------
  var SATZ = { "0": 0.26375, "8": 0.27819, "9": 0.27995 };   // Abgeltungsteuer 25 % + Soli 5,5 %; mit Kirchensteuer 8 %/9 % (Kirchensteuer mindert die Abgeltungsteuer)
  function netto() {
    var betrag = num("r3-betrag", NaN), rend = num("r3-rendite", NaN), jahre = num("r3-jahre", 1), kist = String(num("r3-kist", 0)), fsa = num("r3-fsa", 0);
    function leer(felder, msg) { ["r3-brutto", "r3-frei", "r3-steuer", "r3-netto", "r3-nrend", "r3-gesamt"].forEach(function (id) { setText(id, "–"); }); if (msg) fehler("r3", felder, msg); }
    if (isNaN(betrag) || isNaN(rend)) { leer(["r3-betrag", "r3-rendite"].filter(function (id) { return isNaN(num(id, NaN)); }), "Bitte Anlagebetrag und Rendite als Zahl eingeben (z. B. 50.000 und 3,20). Ein leerer Freistellungsauftrag zählt als 0\u00A0€."); return; }
    if (!pruefe("r3", [
      ["r3-betrag", betrag, 0, 1e9, "Der Anlagebetrag muss über 0 liegen (höchstens 1 Milliarde) – zum Beispiel 50.000.", true],
      ["r3-rendite", rend, -5, 30, "Die Rendite wird in Prozent pro Jahr angegeben, von −5 bis 30 – zum Beispiel 3,20."],
      ["r3-jahre", jahre, 0, 100, "Die Laufzeit muss über 0 und höchstens 100 Jahre betragen.", true],
      ["r3-fsa", fsa, 0, 2000, "Der Freistellungsauftrag liegt zwischen 0 und 2.000\u00A0€ (1.000\u00A0€ je Person, 2.000\u00A0€ bei Zusammenveranlagung)."]
    ])) { leer(); return; }
    var satz = SATZ[kist] || SATZ["0"];
    var cent = function (x) { return Math.round(x * 100) / 100; };
    var brutto = cent(betrag * rend / 100), pflichtig = Math.max(0, brutto - fsa), steuer = cent(pflichtig * satz), net = cent(brutto - steuer);
    var nettoRend = betrag > 0 ? net / betrag * 100 : 0, eff = brutto > 0 ? steuer / brutto * 100 : 0;
    setText("r3-brutto", eur(brutto));
    setText("r3-frei", eur(Math.min(brutto, fsa)));
    setText("r3-steuer", eur(steuer) + (steuer > 0 ? " (" + pct(eff, 1) + " des Ertrags)" : ""));
    setText("r3-netto", eur(net));
    setText("r3-nrend", pct(nettoRend));
    setText("r3-gesamt", eur(net * jahre) + " in " + fmt(jahre, jahre % 1 === 0 ? 0 : 1) + (jahre === 1 ? " Jahr" : " Jahren"));   // 2,5 Jahre bleiben 2,5
    var abg = 25 / (1 + 0.25 * (+kist) / 100);   // Kirchensteuer mindert die Abgeltungsteuer: 25 % / (1 + 0,25 × Kirchensteuersatz)
    ok("r3", "Steuersatz auf Zinsen: " + pct(satz * 100, 3).replace(",000", "") + (kist !== "0"
      ? " (Abgeltungsteuer " + pct(abg, 2) + " – die Kirchensteuer mindert sie –, Solidaritätszuschlag 5,5\u00A0% darauf und Kirchensteuer " + kist + "\u00A0% darauf)"
      : " (Abgeltungsteuer 25\u00A0% + Solidaritätszuschlag 5,5\u00A0% darauf)") + ". Der Freistellungsauftrag (Sparerpauschbetrag 1.000\u00A0€ je Person, 2.000\u00A0€ bei Zusammenveranlagung) gilt je Jahr für alle Kapitalerträge zusammen. Ohne Zinseszins gerechnet; persönliche Umstände (Günstigerprüfung, Verlusttopf) nicht berücksichtigt.",
      "Ertrag pro Jahr netto " + eur(net) + ", Nettorendite " + pct(nettoRend) + ".");
  }

  // ---------- 4 Zinsniveau ----------
  function zinsniveau() {
    var kupon = num("r4-kupon", NaN), jahre = num("r4-jahre", NaN), y0 = num("r4-rendite", NaN) / 100;
    function leer(felder, msg) {
      ["r4-kurs", "r4-dur", "r4-m2", "r4-m1", "r4-p1", "r4-p2"].forEach(function (id) { setText(id, "–"); var b = $(id + "-bar"); if (b) b.style.width = "0"; });
      if (msg) fehler("r4", felder, msg);
    }
    var nan = ["r4-kupon", "r4-jahre", "r4-rendite"].filter(function (id) { return isNaN(num(id, NaN)); });
    if (nan.length) { leer(nan, "Bitte Kupon, Restlaufzeit (über 0, höchstens 120 Jahre) und Rendite als Zahl eingeben."); return; }
    if (!pruefe("r4", [
      ["r4-kupon", kupon, 0, 30, "Der Kupon wird in Prozent pro Jahr angegeben, von 0 bis 30 – zum Beispiel 2,60."],
      ["r4-jahre", jahre, 0, 120, "Die Restlaufzeit muss über 0 und höchstens 120 Jahre betragen.", true],
      ["r4-rendite", y0 * 100, -5, 30, "Die Rendite wird in Prozent pro Jahr angegeben, von −5 bis 30 – zum Beispiel 3,50."]
    ])) { leer(); return; }
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
    ok("r4", "Kurs heute (ohne Stückzinsen) bei " + pct(y0 * 100) + " Rendite: " + pct(p0) + " – aus Rendite und Restlaufzeit gerechnet, kann vom Börsenkurs leicht abweichen. Modifizierte Duration " + fmt(dur, 1) + " – so viel Prozent verliert der Kurs ungefähr je Prozentpunkt, den das allgemeine Zinsniveau steigt. Die Balken zeigen die genaue Rechnung (mit Konvexität: der Gewinn bei fallendem Zinsniveau ist größer als der Verlust bei steigendem).",
      "Kurs heute " + pct(p0) + ", modifizierte Duration " + fmt(dur, 1) + ". Zinsniveau plus 1 Prozentpunkt: " + $("r4-p1").textContent + ", minus 1 Prozentpunkt: " + $("r4-m1").textContent + ".");
  }

  function bind(ids, fn) { ids.forEach(function (id) { var el = $(id); if (el) { el.addEventListener("input", fn); el.addEventListener("change", fn); } }); fn(); }
  // Beim Verlassen eines Felds die Zahl sauber schreiben: Euro mit Tausenderpunkt, Prozent mit zwei Nachkommastellen
  function schoen(id, dec) { var el = $(id); if (!el) return; el.addEventListener("blur", function () { var n = parseDe(el.value, !!DEZ[id]); if (!isNaN(n) && el.value.trim()) el.value = n.toLocaleString("de-DE", { minimumFractionDigits: dec, maximumFractionDigits: Math.max(dec, 3) }); }); }
  // Datumsfelder: gültige Eingaben (auch 15082033) beim Verlassen als TT.MM.JJJJ schreiben
  function schoenDatum(id) { var el = $(id); if (!el) return; el.addEventListener("blur", function () { var d = datText(el.value); if (d && iso(d) !== el.value) el.value = iso(d); }); }
  function init() {
    var v = valuta(), f = $("r1-faellig"), l = $("r2-letzter"), rv = $("r2-valuta");
    // Vorbelegung aus dem Steckbrief (anleihe.html, seit 29.09.2026): ?kurs=99,99&kupon=1,625&faellig=30.09.2026&freq=2&w=USD
    var q = new URLSearchParams(location.search);
    [["kurs", "r1-kurs"], ["kupon", "r1-kupon"], ["faellig", "r1-faellig"], ["nenn", "r1-nenn"]].forEach(function (x) { var w = q.get(x[0]), el = $(x[1]); if (w && el && /^[\d.,]{1,12}$/.test(w)) el.value = w; });
    var fq = q.get("freq"), fs = $("r1-freq"); if (fs && /^(1|2|4|12)$/.test(fq || "")) fs.value = fq;   // seit 03.10.2026 auch vierteljährlich und monatlich
    // Welche Anleihe die Felder füllt (seit 03.10.2026): Titel und ISIN aus dem Steckbrief bzw. der Merkliste
    var qi = q.get("isin"), qt = q.get("titel"), ab = $("r1-anleihe");
    if (ab && qi && /^[A-Z]{2}[A-Z0-9]{9}\d$/.test(qi)) {
      var a = document.createElement("a"); a.href = "anleihe.html?isin=" + encodeURIComponent(qi); a.textContent = qt && qt.length < 90 ? qt : qi;
      ab.textContent = "Werte übernommen von "; ab.appendChild(a); ab.appendChild(document.createTextNode(" · ISIN " + qi)); ab.hidden = false;
    }
    var zt = q.get("zt"), fa = q.get("faellig");
    if (zt && fa && /^\d{2}-\d{2}(,\d{2}-\d{2}){0,11}$/.test(zt)) ZT = { faellig: fa, freq: +(fq || 1), days: zt.split(",") };
    var wq = q.get("w"), nn = $("r1-nenn"); if (wq && /^[A-Z]{3}$/.test(wq) && wq !== "EUR") { EINH1 = wq; if (nn && nn.nextElementSibling) nn.nextElementSibling.textContent = wq; }
    if (f && !f.value) { f.value = "15.08." + (v.getFullYear() + 5); }   // mitten im Kuponjahr, damit Stückzinsen sichtbar sind
    if (l && !l.value) { var last = new Date(v.getTime()); last.setMonth(last.getMonth() - 4); l.value = iso(last); }
    if (rv && !rv.value) rv.value = iso(v);
    bind(["r1-kurs", "r1-kupon", "r1-faellig", "r1-nenn", "r1-freq"], rendite);
    // Seit 03.10.2026 (Nutzertest): Kommt die Anleihe aus dem Steckbrief, füllen dieselben Werte auch die Rechner 2 bis 4 –
    // Stückzinsen (Nennwert, Kupon, letzter Zinstermin, Valuta), Netto (Kurswert als Anlagebetrag, Rendite, Restlaufzeit) und
    // Zinsniveau (Kupon, Restlaufzeit, Rendite). Vorher blieben dort die Beispielwerte stehen.
    if (q.get("kurs") && q.get("kupon") && q.get("faellig") && R1) {
      var setz = function (id, w) { var el = $(id); if (el && w != null && w !== "") el.value = w; };
      var rq = q.get("rendite"), rend = rq && /^-?[\d.,]{1,8}$/.test(rq) ? parseDe(rq, true) : R1.rendite;
      var z2 = function (x) { return x.toLocaleString("de-DE", { minimumFractionDigits: 2, maximumFractionDigits: 3 }); };
      var kup = parseDe(q.get("kupon"), true);
      setz("r2-nenn", $("r1-nenn") ? $("r1-nenn").value : ""); setz("r2-kupon", isNaN(kup) ? "" : z2(kup));
      setz("r2-letzter", iso(R1.prev)); setz("r2-valuta", iso(v)); var f2 = $("r2-freq"); if (f2 && fs) f2.value = fs.value;
      var n2 = $("r2-nenn"); if (EINH1 !== "€") { EINH2 = EINH1; if (n2 && n2.nextElementSibling) n2.nextElementSibling.textContent = EINH1; }
      if (EINH1 === "€") setz("r3-betrag", Math.round(R1.kauf).toLocaleString("de-DE"));   // Netto rechnet in Euro – Fremdwährung nicht als Euro übernehmen setz("r3-rendite", z2(rend)); setz("r3-jahre", R1.jahre.toLocaleString("de-DE", { maximumFractionDigits: 1 }));
      setz("r4-kupon", isNaN(kup) ? "" : z2(kup)); setz("r4-jahre", R1.jahre.toLocaleString("de-DE", { maximumFractionDigits: 1 })); setz("r4-rendite", z2(rend));
    }
    bind(["r2-nenn", "r2-kupon", "r2-freq", "r2-letzter", "r2-valuta"], stueckzinsen);
    bind(["r3-betrag", "r3-rendite", "r3-jahre", "r3-kist", "r3-fsa"], netto);
    bind(["r4-kupon", "r4-jahre", "r4-rendite"], zinsniveau);
    ["r1-nenn", "r2-nenn", "r3-betrag", "r3-fsa"].forEach(function (id) { schoen(id, 0); });
    ["r1-kurs", "r1-kupon", "r2-kupon", "r3-rendite", "r4-kupon", "r4-rendite"].forEach(function (id) { schoen(id, 2); });
    ["r1-faellig", "r2-letzter", "r2-valuta"].forEach(schoenDatum);
    ["r1-nenn", "r2-nenn", "r3-betrag", "r3-fsa"].forEach(function (id) { var el = $(id); if (el) el.dispatchEvent(new Event("blur")); });
    bereit = true;   // ab jetzt Ergebnisse und Fehler ansagen (nur nach Eingaben)
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init); else init();
})();
