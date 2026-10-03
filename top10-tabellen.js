/* top10-tabellen.js – gemeinsamer Code der vier Top-10-Seiten (seit 30.09.2026; vorher laufzeit.js für die beiden
   Laufzeit-Seiten, dazu je eine Inline-Kopie in anleihen-laender.html und unternehmensanleihen-laender.html).

     Staatsanleihen/Unternehmensanleihen nach Laufzeit   → T10.laufzeit({ anleihen, daten, aktiv })
     Staatsanleihen/Unternehmensanleihen nach Ländern    → T10.laender({ daten, laender, … })

   Laden NACH site.js, felder.js (Standardtabelle, MC.felder) und bond.js (Anleihen-Mathematik, MC.bond):
     <script src="site.js"></script><script src="felder.js"></script><script src="bond.js"></script><script src="top10-tabellen.js"></script>
   Die Seite ruft danach selbst MC.load("kurse-auswahl.json") und MC.load("top10-….json") auf und übergibt die Promises
   als daten: [kurse, top10] – so erkennt scripts/inline_data.py die Dateien am Aufruf und bettet sie beim Deploy ein
   (vorher hing das an einem HTML-Kommentar, der den Aufruf wörtlich wiederholte).

   Tabelle (alle Ranglisten gleich, seit 03.10.2026 Standardtabelle aus felder.js, Konzept „Einheitliche Anleihen-Angaben“):
   # · Anleihe (darunter ISIN · Art · Währung) · Rendite · Kupon · Restlaufzeit (darunter Fälligkeit) · Kurs · Bonität · Stückelung · Volumen
   · Handelstage (nur bei der automatischen Rangliste – danach ist gerankt, fett) · Merken. Am Handy Karten (base.css, .atab).
   Kurzname und Bonität: aus der Zeile (kurz, bon – automatische Listen) bzw. anleihen-auswahl.json (Handauswahl der Seite).
   Laden: daten = [kurse-auswahl.json, top10-….json, anleihen-auswahl.json] – alle per MC.load, damit inline_data.py sie einbettet.

   Zeilen (Handauswahl in der Seite oder automatische Liste aus scripts/update_top10.py):
     { isin, emittent?, art?, cur?, kupon, zins (Zahlungen je Jahr), zt? (Zinstage „MM-TT“ laut Börsenliste), faellig, kurs,
       datum?, rendite?, vol, stk }
   Rendite: Tageskurs aus kurse-auswahl.json → dessen Rendite (fehlt sie dort: leer, nicht nachrechnen); sonst die
   vorgegebene rendite der Zeile; sonst aus Kurs, Kupon und Datum berechnet (MC.bond, Valuta T+1 für USD/GBP, sonst T+2). */
(function () {
  "use strict";
  var ZAHL = ["keine", "eine", "zwei", "drei", "vier", "fünf", "sechs", "sieben", "acht", "neun", "zehn"];
  var ZAHL_GROSS = ["Keine", "Ein", "Zwei", "Drei", "Vier", "Fünf", "Sechs", "Sieben", "Acht", "Neun", "Zehn"];
  var KURSE = {}, KTAGE = [], KSTAND = "", AUS = {}, TAGE = 0;   // AUS: anleihen-auswahl.json {ISIN: [kurz, art, waehrung, bon, registername]}
  var ARTNR = { "Staat": 0, "Öffentlich": 1, "Unternehmen": 2 };

  function fmt(v, dec) { return MC.zahl(v, dec || 0); }
  function fmtDate(iso) { return MC.bond.fmtDate(iso); }
  function RL(y) { return MC.restlaufzeit ? MC.restlaufzeit(y) : fmt(y, 1) + " Jahre"; }

  // ---------- Zeilen: Kurs, Datum, Rendite – als Zeilenobjekte der Standardtabelle (felder.js) ----------
  function zeilen(liste, def) {
    def = def || {};
    return liste.map(function (r, i) {
      var k = KURSE[r.isin], kurs = k ? k[0] : r.kurs, datum = k ? KTAGE[k[2]] : (r.datum || def.date);
      var cur = r.cur || def.cur, settle = MC.bond.settle(datum, cur);
      var yld = k ? (typeof k[1] === "number" ? k[1] : null)
        : "rendite" in r ? (typeof r.rendite === "number" ? r.rendite : null)
        : MC.bond.yieldFromPrice({ coupon: r.kupon, freq: r.zins, maturity: r.faellig, days: r.zt }, kurs, settle) * 100;
      var a = AUS[r.isin] || [], artTxt = r.art || def.art;
      var art = artTxt in ARTNR ? ARTNR[artTxt] : a[1];
      return {
        platz: i + 1, isin: r.isin, kurz: r.kurz || a[0] || MC.felder.kurzName(r.emittent || def.emittent || "", art, null, r.isin), reg: a[4] || "",
        art: art, ccy: cur, kupon: r.kupon, zinsart: r.kupon === 0 ? 2 : 0, faellig: r.faellig, kurs: kurs, kdatum: datum,
        boerse: k ? k[3] : "", vortag: k ? k[6] : null, rend: yld, rendGrund: "keine Rendite in den Kursdaten",
        bon: r.bon != null ? r.bon : a[3], vol: r.vol, stk: r.stk, ht: r.ht, um: r.um
      };
    });
  }
  // Tabelle zeichnen (Kopf und Zeilen neu): rows aus zeilen(), sort = { col, dir } (Spalten-Ids aus felder.js), leer = Text ohne Zeile,
  // rang = Spalte, nach der gerankt ist (fett, solange nach Platz sortiert ist): Handelstage bei der automatischen Rangliste, sonst angegeben
  function tabelle(table, rows, sort, leer, rang) {
    var ids = ["platz", "anleihe", "rendite", "kupon", "restlaufzeit", "kurs", "bonitaet", "stueckelung", "volumen"];
    var ht = rows.length > 0 && rows.every(function (r) { return typeof r.ht === "number"; });
    if (ht) ids.push("handelstage");
    if (MC.konto) ids.push("merken");
    var html = MC.felder.tabelle(ids, rows, { sort: sort, sortieren: true, rang: rang || (ht ? "handelstage" : null), leer: leer || "",
      ctx: { kstand: KSTAND || (rows[0] && rows[0].kdatum), tage: TAGE } });
    table.classList.add("atab");
    if (table.tHead) table.tHead.remove();
    [].slice.call(table.tBodies).forEach(function (b) { b.remove(); });
    table.insertAdjacentHTML("beforeend", html);
  }
  function sortierbar(table, sort, neu) { MC.felder.sortierbar(table, sort, neu); }
  function kurseSetzen(d) { if (d) { KURSE = d.kurse || {}; KTAGE = d.tage || []; KSTAND = d.stand || ""; } }
  function auswahlSetzen(d) { if (d && d.a) AUS = d.a; }
  function aktiv(d) { return !!(d && d.aktiv && d.gruppen && d.fenster); }
  // Kursdatum auch sichtbar über der ersten Tabelle (seit 03.10.2026, Nutzertest: stand nur im zugeklappten Methodik-Teil)
  function standZeile(iso) {
    var t = document.querySelector("table.kpis[data-gruppe], .table-scroll table.kpis"), box = t && t.closest(".table-scroll");
    if (!iso || !box) return;
    var p = document.getElementById("kurs-stand");
    if (!p) { p = document.createElement("p"); p.id = "kurs-stand"; p.className = "kurs-stand"; box.parentNode.insertBefore(p, box); }
    p.textContent = "Schlusskurse vom " + fmtDate(iso);
  }
  function datenstand() {
    var el = document.getElementById("datastand"); if (el && KSTAND) el.textContent = "Daten-Stand: " + fmtDate(KSTAND);
    standZeile(KSTAND);
  }
  function laden(daten) {
    daten = daten || [];
    return Promise.all([
      Promise.resolve(daten[0]).catch(function (e) { console.warn("Tageskurse nicht geladen, eingebettete Kurse bleiben:", e); return null; }),
      Promise.resolve(daten[1]).catch(function (e) { console.warn("Top 10 nicht geladen, Handauswahl bleibt:", e); return null; }),
      Promise.resolve(daten[2]).catch(function (e) { console.warn("anleihen-auswahl.json nicht geladen – Namen aus der Zeile:", e); return null; })
    ]);
  }

  // ---------- Laufzeit-Seiten: eine Tabelle je Laufzeitgruppe ----------
  // opt: { anleihen: { date, gruppen: {<anker>: [Zeilen]} } (Handauswahl der Seite), daten: [kurse, top10],
  //        aktiv: d => {} (Texte der Seite bei automatischer Liste) }; Tabellen: <table class="kpis" data-gruppe="<anker>">
  function laufzeit(opt) {
    var A = opt.anleihen, SORT = {};
    var render = function (key) {
      var table = document.querySelector('table.kpis[data-gruppe="' + key + '"]');
      if (!table) return;
      var n = A.auto ? A.auto.fenster.tage : 0;
      tabelle(table, zeilen(A.gruppen[key], { date: A.date }), SORT[key] || (SORT[key] = { col: "platz", dir: 1 }),
        "In den letzten " + n + " Börsentagen wurde keine Anleihe dieser Gruppe an der Börse Frankfurt oder bei Tradegate gehandelt.");
    };
    var alle = function () { Object.keys(A.gruppen).forEach(render); };
    try {
      alle();
      Object.keys(A.gruppen).forEach(function (key) {
        var t = document.querySelector('table.kpis[data-gruppe="' + key + '"]');
        if (t) sortierbar(t, SORT[key], function () { render(key); });
      });
    } catch (e) { console.warn("Render fehlgeschlagen:", e); }
    return laden(opt.daten).then(function (res) {
      kurseSetzen(res[0]); auswahlSetzen(res[2]);
      var d = res[1];
      if (aktiv(d)) {   // automatische Rangliste: Gruppen ersetzen, Tabellenbeschriftungen anpassen
        A.auto = d; A.date = d.stand || A.date; TAGE = d.fenster.tage || 0;
        Object.keys(A.gruppen).forEach(function (g) {
          A.gruppen[g] = d.gruppen[g] || [];
          var cap = document.querySelector('table.kpis[data-gruppe="' + g + '"] caption');
          var n = A.gruppen[g].length;
          if (cap) cap.textContent = cap.textContent.replace(/die (?:zehn|neun|acht|sieben|sechs|fünf|vier|drei|zwei|eine|\d+) meistgehandelten/, n ? "die " + (ZAHL[n] || n) + " meistgehandelten" : "keine gehandelten");
        });
        try { if (opt.aktiv) opt.aktiv(d); } catch (e) { console.warn(e); }
      }
      alle();
      datenstand();
    });
  }

  // ---------- Länder-Seiten: Weltkarte (weltkarte.svg), Knopfleiste, eine Tabelle ----------
  // opt: { laender: {key: {name, emittent?, art, cur, date, pt: [x, y], note?, rows, auto?}}, standard: "deutschland",
  //        titel: n => "die zehn meistgehandelten …", hinweis: "…" (Notiz unter der Tabelle), daten: [kurse, top10],
  //        aktiv: d => {} (Texte der Seite bei automatischer Liste), leer: "…", vorlaeufig: d => "…" }
  // auto: true (seit 30.09.2026) = Land ohne Handauswahl (rows: []): Seine Zeilen kommen schon vor „aktiv“ aus der automatischen
  // Liste, mit dem Hinweis opt.vorlaeufig(d); fehlt es dort oder lädt die Liste nicht, entfällt es wie ein Land ohne Anleihe.
  function laender(opt) {
    var L = opt.laender, SORT = { col: "platz", dir: 1 }, AUTO = null, current = opt.standard;
    var map = document.getElementById("map"), lands = document.getElementById("lands"), tip = document.getElementById("maptip");
    var table = document.getElementById("kpis");
    var HANDY = window.matchMedia ? window.matchMedia("(max-width: 600px)") : { matches: false };

    // Kartenausschnitt: am Handy auf das gewählte Land gezoomt (240 × 106 Einheiten, ca. 1,5-fach), damit
    // Nachbarländer groß genug zum Antippen sind; auf dem Desktop die ganze Welt
    function ansicht() {
      var svg = map && map.querySelector("svg"); if (!svg) return;
      var pt = L[current] && L[current].pt;
      if (HANDY.matches && pt) {
        var w = 240, h = w * 0.44, x = Math.max(0, Math.min(1000 - w, pt[0] - w / 2)), y = Math.max(0, Math.min(440 - h, pt[1] - h / 2));
        svg.setAttribute("viewBox", x.toFixed(1) + " " + y.toFixed(1) + " " + w + " " + h.toFixed(1));
        svg.classList.add("zoom");
      } else { svg.setAttribute("viewBox", "0 0 1000 440"); svg.classList.remove("zoom"); }
    }
    function render() {
      var c = L[current];
      tabelle(table, zeilen(c.rows, c), SORT, opt.leer ? opt.leer(AUTO ? AUTO.fenster.tage : 0) : "");
      var titel = c.name + ": " + opt.titel(c.rows.length);
      document.getElementById("land-titel").textContent = titel;
      if (table.caption) table.caption.textContent = titel;
      document.getElementById("land-note").textContent = (c.note ? c.note + " " : "") + opt.hinweis;
      var ue = document.getElementById("uebergang"); if (ue && !AUTO) ue.hidden = !!c.auto;   // Übergangshinweis gilt nur für die Handauswahl
    }
    function select(key, o) {
      o = o || {};
      if (!L[key] || L[key].aus) key = opt.standard;
      current = key;
      lands.querySelectorAll(".lbtn").forEach(function (b) { b.setAttribute("aria-pressed", b.dataset.land === key ? "true" : "false"); });
      if (map) map.querySelectorAll(".pick").forEach(function (p) { p.classList.toggle("on", p.dataset.land === key); });
      var mark = document.getElementById("mapmark"), pt = L[key].pt;
      if (mark && pt) { mark.setAttribute("cx", pt[0]); mark.setAttribute("cy", pt[1]); }
      ansicht();
      render();
      if (o.push) {
        try { history.replaceState(null, "", "#" + key); } catch (e) { /* file:// o. Ä. */ }
        // Liegt die Tabelle noch unterhalb des sichtbaren Bereichs, zu ihr scrollen – sonst bliebe der Klick scheinbar ohne Wirkung
        var h = document.getElementById("land-titel"), r = h.getBoundingClientRect();
        if (r.top > window.innerHeight - 140) h.scrollIntoView({ behavior: "smooth", block: "start" });
      }
    }
    // Länder ohne Anleihen (automatische Liste): Knopf und Kartenfläche entfernen, Länderzahl in den Texten anpassen
    function landWeg(key) {
      L[key].aus = true;
      var b = lands.querySelector('.lbtn[data-land="' + key + '"]'); if (b) b.remove();
      if (map) map.querySelectorAll('[data-land="' + key + '"]').forEach(function (p) { p.remove(); });
    }
    function zaehlen() {
      var n = Object.keys(L).filter(function (k) { return !L[k].aus; }).length;
      document.querySelectorAll("[data-anzahl-laender]").forEach(function (el) {
        el.textContent = el.dataset.anzahlLaender === "gross" ? (ZAHL_GROSS[n] || n) : (n <= 10 ? ZAHL[n] : n);
      });
    }
    // Karte: gemeinsame, cachebare Datei weltkarte.svg (vorher je Seite 49 KB inline); nur die Länder dieser Seite bleiben wählbar.
    // ?v= nach jeder Änderung der Karte hochzählen – sonst zeigt der Browser bis zu einen Tag die alte (v=2: 20 Länder, 30.09.2026).
    function karte() {
      if (!map) return Promise.resolve();
      return fetch("weltkarte.svg?v=2").then(function (r) { if (!r.ok) throw new Error(r.status); return r.text(); }).then(function (t) {
        var box = map.querySelector(".map-svg");
        box.innerHTML = t;
        var svg = box.querySelector("svg");
        svg.setAttribute("aria-hidden", "true"); svg.setAttribute("focusable", "false");
        svg.querySelectorAll("[data-land]").forEach(function (p) { if (!L[p.dataset.land] || L[p.dataset.land].aus) p.remove(); });
        map.classList.add("geladen");
        select(current);
      }).catch(function (e) { console.warn("Weltkarte nicht geladen – Auswahl über die Knöpfe:", e); map.hidden = true; });
    }
    function initMap() {
      var onClick = function (e) { var el = e.target.closest("[data-land]"); if (el && L[el.dataset.land]) select(el.dataset.land, { push: true }); };
      lands.addEventListener("click", onClick);
      var hot = function (key, on) { document.querySelectorAll('#map .pick[data-land="' + key + '"], #lands .lbtn[data-land="' + key + '"]').forEach(function (el) { el.classList.toggle("hot", on); }); };
      var boxes = [lands];
      if (map) {
        map.addEventListener("click", onClick);
        boxes.push(map);
        // Überfahren von Land oder Knopf hebt jeweils beides hervor; auf der Karte zeigt ein Tooltip den Namen
        map.addEventListener("pointermove", function (e) {
          var el = e.target.closest("[data-land]");
          if (!el || e.pointerType === "touch" || !L[el.dataset.land]) { tip.hidden = true; return; }
          var r = map.getBoundingClientRect();
          tip.textContent = L[el.dataset.land].name;
          tip.style.left = Math.max(40, Math.min(r.width - 40, e.clientX - r.left)) + "px";
          tip.style.top = (e.clientY - r.top) + "px";
          tip.hidden = false;
        });
        map.addEventListener("pointerleave", function () { tip.hidden = true; });
      }
      boxes.forEach(function (box) {
        box.addEventListener("pointerover", function (e) { var el = e.target.closest("[data-land]"); if (el) hot(el.dataset.land, true); });
        box.addEventListener("pointerout", function (e) { var el = e.target.closest("[data-land]"); if (el) hot(el.dataset.land, false); });
      });
      // Nur Länder-Anker reagieren (der Skip-Link „#main“ lässt die Auswahl stehen)
      window.addEventListener("hashchange", function () { var k = location.hash.slice(1); if (L[k]) select(k); });
      if (HANDY.addEventListener) HANDY.addEventListener("change", ansicht);
    }
    try {
      initMap();
      sortierbar(table, SORT, render);
      select(L[location.hash.slice(1)] ? location.hash.slice(1) : opt.standard);
    } catch (e) { console.warn("Render fehlgeschlagen:", e); }
    var kartenLauf = karte();
    return laden(opt.daten).then(function (res) {
      kurseSetzen(res[0]); auswahlSetzen(res[2]);
      var d = res[1];
      if (d && d.fenster) TAGE = d.fenster.tage || 0;
      if (aktiv(d)) {
        AUTO = d;
        var ue = document.getElementById("uebergang"); if (ue) ue.hidden = true;   // Übergangshinweis gilt nur für die Handauswahl
        Object.keys(L).forEach(function (k) { L[k].rows = d.gruppen[k] || []; L[k].note = null; L[k].date = d.stand; if (!L[k].rows.length) landWeg(k); });
        zaehlen();
        if (L[current].aus) current = opt.standard;
        try { if (opt.aktiv) opt.aktiv(d); } catch (e) { console.warn(e); }
      } else {
        // Übergang: Die Handauswahl bleibt, nur die Länder ohne Handauswahl (auto) zeigen schon die automatische Liste
        var autos = Object.keys(L).filter(function (k) { return L[k].auto; });
        autos.forEach(function (k) {
          L[k].rows = (d && d.gruppen && d.fenster && d.gruppen[k]) || [];
          if (!L[k].rows.length) { landWeg(k); return; }
          L[k].date = d.stand;
          try { L[k].note = opt.vorlaeufig ? opt.vorlaeufig(d) : null; } catch (e) { console.warn(e); }
        });
        if (autos.length) zaehlen();
        if (L[current].aus) current = opt.standard;
      }
      select(current);
      datenstand();
      return kartenLauf;
    });
  }

  window.T10 = { zeilen: zeilen, tabelle: tabelle, sortierbar: sortierbar, laufzeit: laufzeit, laender: laender, standZeile: standZeile,
    kurseSetzen: kurseSetzen, auswahlSetzen: auswahlSetzen };
})();
