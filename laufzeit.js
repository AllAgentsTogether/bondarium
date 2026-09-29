/* laufzeit.js – gemeinsamer Code der Seiten „Staatsanleihen nach Laufzeit“ und
   „Unternehmensanleihen nach Laufzeit“ (seit 25.09.2026 ausgelagert; vorher stand er
   in beiden Seiten identisch inline).

   Erwartet in der Seite (vor diesem Skript geladen):
     - site.js (MC.esc, MC.minus) bzw. den Fallback der Seite
     - const ANLEIHEN = { date: "JJJJ-MM-TT", gruppen: { <anker>: [ {isin, emittent, art,
       cur, kupon, zins, faellig, kurs, vol, stk}, … ] } }
     - je Gruppe eine <table class="kpis" data-gruppe="<anker>"> mit <th data-col> und .sortbtn
   Rendite und Restlaufzeit werden aus Kurs, Kupon und Datum berechnet (Valuta T+1 für
   USD/GBP, sonst T+2). Der Deploy minifiziert die Datei und hängt ?v=<Hash> an.
   Seit 26.09.2026 optional in der Seite: const TOP10 = "<datei>.json" (scripts/update_top10.py) –
   ist die Datei „aktiv“ (genug Börsentage erfasst), ersetzen ihre Gruppen die Handauswahl in ANLEIHEN;
   danach ruft das Skript TOP10_AKTIV(daten) der Seite auf (Texte zur Methodik). Zeilen der Datei
   tragen kurs, datum und rendite selbst. */
(function () {
  "use strict";
  const TXT = { years: "Jahre", bn: "Mrd." };
  // Restlaufzeit lesbar (Tage / Monate / Jahre, site.js); Rückfall: Jahre mit einer Nachkommastelle
  const RL = y => (window.MC && MC.restlaufzeit) ? MC.restlaufzeit(y) : `${fmt(y, 1)} ${TXT.years}`;

  // ---------- Formatierung ----------
  function fmt(v, dec = 0) {
    if (typeof v !== "number" || !isFinite(v)) return "–";
    return MC.minus(v.toLocaleString("de-DE", { minimumFractionDigits: dec, maximumFractionDigits: dec }));
  }
  function fmtDate(iso) { const d = new Date(String(iso).slice(0, 10) + "T12:00:00"); return isNaN(d) ? "–" : d.toLocaleDateString("de-DE", { day: "2-digit", month: "2-digit", year: "numeric" }); }
  const fmtCoupon = c => fmt(c, Math.round(c * 1000) % 10 ? 3 : 2);
  // Volumen immer in Mrd., höchstens drei gültige Ziffern (0,5 Mrd. · 0,0339 Mrd. · 1,25 Mrd. · 30,5 Mrd. · 122 Mrd.)
  function fmtVol(v) {
    return `${(v / 1e9).toLocaleString("de-DE", { maximumSignificantDigits: 3 })} ${TXT.bn}`;
  }
  // Stückelung: 0,01 · 1 · 1.000 · 200.000
  const fmtStk = v => v.toLocaleString("de-DE", { maximumFractionDigits: 2 });

  // ---------- Anleihemathematik (jährliche Verzinsung, Zeit taggenau; wie langlaeufer.html) ----------
  const DAY = 86400000;
  const utc = iso => new Date(iso + "T12:00:00Z").getTime();
  function addDays(iso, n) { const d = new Date(iso + "T12:00:00Z"); d.setUTCDate(d.getUTCDate() + n); return d.toISOString().slice(0, 10); }
  // Monat zurückrechnen ohne Überlauf (31.05. → 30.11.)
  function monthsBack(t, m) {
    const d = new Date(t), day = d.getUTCDate();
    d.setUTCDate(1); d.setUTCMonth(d.getUTCMonth() - m);
    const last = new Date(Date.UTC(d.getUTCFullYear(), d.getUTCMonth() + 1, 0, 12)).getUTCDate();
    d.setUTCDate(Math.min(day, last));
    return d.getTime();
  }
  function couponDates(b, settle) {
    const s = utc(settle), out = [];
    let t = utc(b.maturity);
    while (t > s) { out.unshift(t); t = monthsBack(t, 12 / b.freq); }
    return { dates: out, prev: t };
  }
  function cleanPrice(b, y, settle) {
    const s = utc(settle), { dates, prev } = couponDates(b, settle), c = b.coupon / b.freq;
    let pv = 0;
    dates.forEach((t, i) => { pv += (c + (i === dates.length - 1 ? 100 : 0)) / Math.pow(1 + y, (t - s) / DAY / 365.25); });
    return pv - c * (s - prev) / (dates[0] - prev);
  }
  function yieldFromPrice(b, p, settle) {
    let lo = -0.02, hi = 0.30;
    for (let i = 0; i < 80; i++) { const mid = (lo + hi) / 2; if (cleanPrice(b, mid, settle) > p) lo = mid; else hi = mid; }
    return (lo + hi) / 2;
  }
  // Valuta: US-Dollar und Pfund T+1, sonst T+2
  const settleDays = cur => (cur === "USD" || cur === "GBP") ? 1 : 2;
  // Tageskurse (kurse-auswahl.json, scripts/update_kurse.py – Deutsche Börse / Bundesbank, seit 25.09.2026):
  // {stand, tage: [Datum …], kurse: {ISIN: [kurs, rendite|null, tag, boerse, umsatz]}}; ohne Eintrag gilt der Kurs aus ANLEIHEN.
  let KURSE = {}, KTAGE = [], KSTAND = "";

  // ---------- Tabellen: eine je Laufzeitgruppe, jede für sich sortierbar ----------
  const SORT = {};   // je Gruppe { col, dir }
  function rows(key) {
    return ANLEIHEN.gruppen[key].map((r, i) => {
      const k = KURSE[r.isin], kurs = k ? k[0] : r.kurs, datum = k ? KTAGE[k[2]] : (r.datum || ANLEIHEN.date);
      const settle = addDays(datum, settleDays(r.cur));
      return {
        rank: i + 1, isin: r.isin, emittent: r.emittent, art: r.art, cur: r.cur,
        kupon: r.kupon, faellig: r.faellig, kurs, datum, vol: r.vol, stk: r.stk,
        // Mit Tageskurs gilt dessen Rendite – fehlt sie dort (seit 26.09.2026: nicht aussagekräftig, z. B. unplausibler Kurs ohne
        // Umsatz), bleibt die Zelle leer statt selbst nachzurechnen; ohne Tageskurs rechnet die Seite aus dem eingebetteten Kurs
        yld: k ? (typeof k[1] === "number" ? k[1] : null) : "rendite" in r ? (typeof r.rendite === "number" ? r.rendite : null) : yieldFromPrice({ coupon: r.kupon, freq: r.zins, maturity: r.faellig }, kurs, settle) * 100,
        years: (utc(r.faellig) - utc(settle)) / DAY / 365.25
      };
    });
  }
  function renderTable(key) {
    const s = SORT[key] || (SORT[key] = { col: "rank", dir: 1 });
    const cmp = (a, b) => {
      const x = a[s.col], y = b[s.col];
      if (x == null || y == null) return x == null && y == null ? a.rank - b.rank : x == null ? 1 : -1;   // ohne Wert ans Ende
      const r = typeof x === "string" ? x.localeCompare(y, "de", { numeric: true }) : x - y;
      return (r || a.rank - b.rank) * s.dir;
    };
    const table = document.querySelector(`table.kpis[data-gruppe="${key}"]`);
    const liste = rows(key);
    if (!liste.length) {   // automatische Rangliste ohne gehandelte Anleihe in dieser Gruppe
      const n = ANLEIHEN.auto ? ANLEIHEN.auto.fenster.tage : 0;
      table.tBodies[0].innerHTML = `<tr><td class="leer" colspan="11">In den letzten ${n} Börsentagen wurde keine Anleihe dieser Gruppe an der Börse Frankfurt oder bei Tradegate gehandelt.</td></tr>`;
      return;
    }
    table.tBodies[0].innerHTML = liste.sort(cmp).map(r =>
      `<tr><td class="num rk">${r.rank}</td>` +
      `<th scope="row">${MC.esc(r.emittent)}</th>` +
      `<td class="num"${r.yld == null ? ' title="Kurs ohne Umsatz – Rendite nicht aussagekräftig"' : ""}>${r.yld == null ? "–" : `${fmt(r.yld, 2)}\u00a0%`}</td>` +
      `<td class="num"${r.datum !== (KSTAND || ANLEIHEN.date) ? ` title="Kurs vom ${fmtDate(r.datum)}"` : ""}>${fmt(r.kurs, 2)}</td><td class="num">${fmtCoupon(r.kupon)}\u00a0%</td>` +
      `<td class="num">${fmtDate(r.faellig)}</td><td class="num">${RL(r.years)}</td>` +
      `<td class="isin"><a href="anleihe.html?isin=${MC.esc(r.isin)}" title="Steckbrief: Kurs, Rendite, Kursverlauf, Handel und Stammdaten">${MC.esc(r.isin)}</a></td><td class="txt">${MC.esc(r.cur)}</td>` +
      `<td class="num">${fmtVol(r.vol)}</td><td class="num">${fmtStk(r.stk)}</td></tr>`).join("");
    for (const th of table.tHead.querySelectorAll("th[data-col]")) {
      if (th.dataset.col === s.col) th.setAttribute("aria-sort", s.dir > 0 ? "ascending" : "descending");
      else th.removeAttribute("aria-sort");
    }
  }
  function initSort() {
    for (const table of document.querySelectorAll("table.kpis[data-gruppe]")) {
      table.tHead.addEventListener("click", e => {
        const b = e.target.closest(".sortbtn");
        if (!b) return;
        const key = table.dataset.gruppe, s = SORT[key], col = b.dataset.col;
        if (s.col === col) s.dir = -s.dir; else { s.col = col; s.dir = 1; }
        renderTable(key);
      });
    }
  }
  // Automatische Rangliste (update_top10.py): Gruppen ersetzen, Tabellenbeschriftungen anpassen
  const ZAHL = ["keine", "eine", "zwei", "drei", "vier", "fünf", "sechs", "sieben", "acht", "neun", "zehn"];
  function top10(d) {
    if (!d || !d.aktiv || !d.gruppen || !d.fenster) return false;
    ANLEIHEN.auto = d;
    ANLEIHEN.date = d.stand || ANLEIHEN.date;
    for (const g of Object.keys(ANLEIHEN.gruppen)) {
      ANLEIHEN.gruppen[g] = d.gruppen[g] || [];
      const cap = document.querySelector(`table.kpis[data-gruppe="${g}"] caption`);
      if (cap) cap.textContent = cap.textContent.replace(/die (?:zehn|neun|\d+) meistgehandelten/, (n => n ? `die ${ZAHL[n] || n} meistgehandelten` : "keine gehandelten")(ANLEIHEN.gruppen[g].length));
    }
    try { if (typeof TOP10_AKTIV === "function") TOP10_AKTIV(d); } catch (e) { console.warn(e); }
    return true;
  }
  (function () {
    try { Object.keys(ANLEIHEN.gruppen).forEach(renderTable); initSort(); } catch (e) { console.warn("Render fehlgeschlagen:", e); }
    if (!(window.MC && MC.load)) return;
    const kurse = MC.load("kurse-auswahl.json").catch(e => { console.warn("Tageskurse nicht geladen, eingebettete Kurse bleiben:", e); return null; });
    const liste = typeof TOP10 === "string" ? MC.load(TOP10).catch(e => { console.warn("Top 10 nicht geladen, Handauswahl bleibt:", e); return null; }) : Promise.resolve(null);
    Promise.all([kurse, liste]).then(([d, t]) => {
      if (d) { KURSE = d.kurse || {}; KTAGE = d.tage || []; KSTAND = d.stand || ""; }
      top10(t);
      Object.keys(ANLEIHEN.gruppen).forEach(renderTable);
      const el = document.getElementById("datastand");
      if (el && KSTAND) el.textContent = `Daten-Stand: ${fmtDate(KSTAND)}`;
    });
  })();
})();
