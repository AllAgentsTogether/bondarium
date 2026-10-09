/* site.js – gemeinsame Helfer für alle Seiten. Wird vor dem seitenspezifischen
   Inline-Script am Body-Ende geladen (DOM ist dann bereits geparst).
   Einzige Quelle für: HTML-Escaping (XSS-Schutz), Datenladen (eingebettete
   Deploy-Daten vor fetch, gemeinsamer Fetch-Cache), Zahlen-/Datumsformat, die
   „veraltet“-Regel, Nav-Dropdowns inkl. aria-current, Chart-Tooltips, Kursverläufe,
   den Wisch-Hinweis quer scrollender Tabellen und die Einordnungsregel.
   Der Kurs-Chart (MC.kursChart) steht seit 30.09.2026 in chart.js, die Anleihen-
   Mathematik (MC.bond) in bond.js – beide nur auf den Seiten, die sie brauchen.

   API (window.MC), Stand 30.09.2026:
     MC.esc(s)                 HTML-Escaping – für jede Fremd-Zeichenkette vor innerHTML
     MC.minus(s)               führendes „-“ → echtes Minus „−“
     MC.zahl(v, nachkomma)     1234.5 → „1.234,50“ (de-DE, echtes Minus); keine Zahl → „–“
     MC.datum(iso) / MC.tag(iso)   „2026-09-25“ → „25.09.2026“ / „25.09.“; ungültig → „–“
     MC.STALE_TAGE             5 – ab so vielen Börsentagen Alter gilt ein Datenstand als veraltet
     MC.heuteBerlin()          heutiger Kalendertag in Berlin (Börsentag) als Date um 12:00 UTC – „heute“ für Restlaufzeit, Valuta, Alter
     MC.boersentage(iso[, bis]) Börsentage (Mo–Fr ohne Börsenfeiertage) nach iso bis heute (Berlin); MC.veraltet(iso) → true ab STALE_TAGE
     MC.handelstag(d), MC.plusAbwicklungstage(d, n)   nächster Handelstag; Valuta n Abwicklungstage später (mit Feiertagen)
     MC.EURO_FEST              feste Umrechnungskurse der früheren Euro-Währungen (Einheiten je Euro, z. B. DEM 1,95583)
     MC.betragLesen(text[, {ganz, min, max}])         Betrag aus einem Eingabefeld, Tausenderpunkte nur im Dreierabstand
     MC.load(datei)            Promise mit JSON: eingebetteter Block (Deploy) oder fetch über MC.json
     MC.json(url)              fetch + JSON mit gemeinsamem Cache (jede URL einmal je Seitenaufruf)
     MC.restlaufzeit(jahre[, kurz]), MC.kuendigung(...), MC.kuendigungFeld(...)
     MC.teil(isin), MC.verlauf(isin[, bund][, {ab}])   Kursverlauf aus kurse/ (nur vorhandene Jahre, kurse/jahre.json)
     MC.hoverWrap(svg, series[, label[, opts]])        Chart-Tooltip; Daten bleiben im JS (nicht im DOM)
     MC.wischPruefen()         Wisch-Hinweis (.ueberlauf) neu prüfen
     MC.navInit()              Menü, aria-current, Kopfzeilen-Suche
     MC.percentile/stats/rate/pctText/ratePill         Einordnung gegen die eigene Historie */
window.MC = (function () {
  "use strict";

  // HTML-Escaping: MUSS auf jede Zeichenkette aus JSON-/Fremddaten angewendet
  // werden, bevor sie per innerHTML/Template-Literal ins DOM gelangt.
  function esc(s) {
    return String(s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }

  // Typografisches Minus: toLocaleString liefert in de-DE den ASCII-
  // Bindestrich; Tabellen/Charts sollen einheitlich „−“ (U+2212) zeigen.
  function minus(s) { return String(s).replace(/^-/, "−"); }

  // Restlaufzeit lesbar (Nutzerbefund 25.09.2026: „0,0 Jahre“ bei Anleihen, die in wenigen
  // Tagen fällig werden, war verwirrend): unter einem Monat in Tagen, unter einem Jahr in
  // Monaten, sonst in Jahren mit einer Nachkommastelle; abgelaufen = „fällig“.
  // years = Restlaufzeit in Jahren (Zahl), kurz = Kurzform („3 T.“, „5 Mon.“, „2,4 J.“).
  function restlaufzeit(years, kurz) {
    if (years == null || isNaN(years) || !isFinite(years)) return kurz ? "–" : "unbefristet";
    var tage = Math.round(years * 365.25);
    if (tage <= 0) return "fällig";
    if (tage < 31) return tage + (kurz ? " T." : tage === 1 ? " Tag" : " Tage");
    var monate = Math.round(tage / 30.44);
    if (monate < 12) return monate + (kurz ? " Mon." : monate === 1 ? " Monat" : " Monate");
    return years.toLocaleString("de-DE", { minimumFractionDigits: 1, maximumFractionDigits: 1 }) + (kurz ? " J." : " Jahre");
  }

  // Kündigung einer Anleihe (seit 27.09.2026; erklärt auf kuendbare-anleihen.html, genutzt von Suche und Steckbrief).
  // Quelle 1 – der Name: „Ausgabejahr(erstes Kündigungsjahr/Fälligkeitsjahr)“, z. B. „2024(27/34)“, bzw. „(28/Und.)“
  // für unbefristet. Quelle 2 – die Rückzahlungsart im ESMA-Register (5. Stelle des CFI-Codes, Index-Feld mehr[0][1]).
  // Der Name hat Vorrang: Das Register meldet die Rückzahlungsart oft ungenau (z. B. „feste Fälligkeit“ trotz
  // Kündigungsjahr im Namen). Schlüssel k (Filter „kue“ der Suche):
  //   n nicht kündbar · m Make-Whole (Kündigungsjahr = Ausgabejahr) · p kurz vor Fälligkeit (letztes Jahr) ·
  //   t ab festem Termin (Jahre vor Fälligkeit) · e ewig mit Kündigungstermin · u kündbar laut Register, Art unklar.
  // put = Kündigungsrecht des Anlegers laut Register (C, D, T, L) – Filterwert „a“.
  var KUE_RE = /(?:^|[^\d])(\d{4}|\d{2})?\s*\((\d{4}|\d{2})\/(\d{4}|\d{2}|Und\.?)\)/;
  function jahr4(s) { var n = +s; return s.length === 4 ? n : (n < 70 ? 2000 + n : 1900 + n); }
  function kuendigung(name, rz, faellig, erster) {
    var m = KUE_RE.exec(String(name || "")), k, jahr = null;
    rz = typeof rz === "string" && rz.length === 1 ? rz : "-";
    if (m) {
      jahr = jahr4(m[2]);
      if (/^Und/.test(m[3])) k = "e";
      else {
        var aj = m[1] ? jahr4(m[1]) : (erster ? +String(erster).slice(0, 4) : null);
        var fj = faellig ? +String(faellig).slice(0, 4) : jahr4(m[3]);
        k = aj != null && jahr <= aj ? "m" : fj - jahr <= 1 ? "p" : "t";
      }
    } else k = "GDBLQP-".indexOf(rz) >= 0 ? "u" : "n";
    // Fix-to-Float/Hybrid mit Kündigungsjahr = Ausgabejahr („FLR-Anleihe v.24(24/84)“): kein Make-Whole, der erste echte
    // Kündigungstermin ist meist der erste Zinsanpassungstermin Jahre später – aus dem Namen nicht ablesbar (27.09.2026)
    if (k === "m" && /FLR\b|Fix[- ]to[- ]Float/i.test(name)) { k = "u"; jahr = null; }
    return { k: k, jahr: jahr, put: "CDTL".indexOf(rz) >= 0 };
  }
  // Anzeige als Feld (Wert + Erläuterung), gleich in Suche und Steckbrief. kurs = aktueller Kurs in % oder null.
  // Rückgabe: { wert, klein (HTML), warn (true bei fester Kündigung/ewig), anker (Sprungmarke auf kuendbare-anleihen.html, leer = kein Link) }
  function kuendigungFeld(o, kurs) {
    var jetzt = new Date().getFullYear(), ab = o.jahr != null ? (o.jahr <= jetzt ? "seit " : "ab ") + o.jahr : "";
    var put = o.put ? " · du kannst kündigen (Put)" : "";
    var f = {
      n: o.put ? ["nur durch dich", "Kündigungsrecht für dich (Put) – ein Vorteil", "put"] : ["keine", "feste Laufzeit", ""],
      m: ["Make-Whole", "zum Barwert, meist über dem Kurs – harmlos" + put, "make-whole"],
      p: ["kurz vor Fälligkeit", ab + " zu 100 %, höchstens ein Jahr früher – harmlos" + put, "kurz-vor-ende"],
      t: [ab, (kurs != null && kurs > 100 ? "Kurs über 100: Bei Kündigung verlierst du den Aufschlag" : "meist zu 100 %, Jahre vor Fälligkeit – beachten") + put, "termin"],
      e: [ab, "ewige Anleihe – kündigt er nicht, läuft sie weiter" + put, "ewig"],
      u: ["ja, Termin unklar", "laut Register kündbar, Termin nicht gemeldet – Bedingungen prüfen" + put, "name"]
    }[o.k] || ["–", "", ""];
    return { wert: f[0], klein: f[1], warn: o.k === "t" || o.k === "e", anker: f[2] };
  }

  // Gemeinsamer Fetch-Cache (seit 30.09.2026): jede URL wird je Seitenaufruf nur einmal geladen – auch wenn
  // MC.load, MC.verlauf und das Seitenskript dieselbe Datei brauchen (anleihe.html lud kurse/<Jahr>/<teil>.json doppelt).
  // MC.json(url) → Promise mit dem geparsten JSON; bei HTTP-Fehler wird abgelehnt (Error mit dem Statuscode) und der
  // Eintrag verworfen, damit ein späterer Versuch neu lädt. Das Ergebnis ist geteilt – nur lesen, nicht verändern.
  var jsonCache = {};
  // Lokale Vorschau (python -m http.server sendet kein Cache-Control): Der Browser hielt Datendateien tagelang im Cache –
  // Kurse und „Stand“ blieben alt, obwohl die Datei neu war (30.09.2026). Lokal deshalb immer beim Server nachfragen;
  // live bleibt es beim Cache-Control des Servers.
  var lokal = /^(localhost|127\.0\.0\.1|\[::1\])$/.test(location.hostname);
  function json(url) {
    if (!jsonCache[url]) {
      jsonCache[url] = fetch(url, lokal ? { cache: "no-cache" } : undefined).then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); });
      jsonCache[url].catch(function () { delete jsonCache[url]; });
    }
    return jsonCache[url];
  }

  // Daten laden. Der Deploy-Workflow bettet die JSON-Dateien als
  // <script type="application/json" data-mc="renditen.json"> in jede Seite ein
  // (scripts/inline_data.py) – dann entfällt der zusätzliche Request und der
  // erste Render zeigt bereits die aktuellen Werte (kein Sprung, kein
  // „Flash“ alter Fallback-Zahlen). Ohne eingebettete Daten (lokal/Entwicklung)
  // wird per fetch geladen – über den gemeinsamen Cache (MC.json).
  function load(name) {
    var el = document.querySelector('script[type="application/json"][data-mc="' + name + '"]');
    if (el) {
      try { return Promise.resolve(JSON.parse(el.textContent)); }
      catch (e) { /* defekter Block: auf fetch zurückfallen */ }
    }
    return json(name);
  }

  // --- Zahlen und Daten (seit 30.09.2026 zentral; vorher in vielen Seiten als fmt()/fmtDate() nachgebaut) ---
  // MC.zahl(v, nachkomma): deutsches Zahlenformat mit fester Nachkommazahl und echtem Minuszeichen (U+2212);
  // keine Zahl (null, NaN, Text) → „–“. Beispiel: MC.zahl(-1234.5, 2) → „−1.234,50“. Kein Minus vor einer Null:
  // MC.zahl(-0.004, 2) → „0,00“ (seit 09.10.2026, Technik-Test 08.10.2026 T-53; vorher „−0,00“, wie _common.zahl_de).
  var NF = {};
  function zahl(v, dec) {
    if (typeof v !== "number" || !isFinite(v)) return "–";
    dec = dec || 0;
    var nf = NF[dec] || (NF[dec] = new Intl.NumberFormat("de-DE", { minimumFractionDigits: dec, maximumFractionDigits: dec }));
    var s = nf.format(v);
    return /[1-9]/.test(s) ? minus(s) : s.replace(/^[-−]/, "");
  }
  // ISO-Datum „JJJJ-MM-TT…“ → „TT.MM.JJJJ“ (MC.datum) bzw. „TT.MM.“ (MC.tag); ungültig → „–“
  var ISO_RE = /^(\d{4})-(\d{2})-(\d{2})/;
  function datum(iso) { var m = ISO_RE.exec(String(iso || "")); return m ? m[3] + "." + m[2] + "." + m[1] : "–"; }
  function tag(iso) { var m = ISO_RE.exec(String(iso || "")); return m ? m[3] + "." + m[2] + "." : "–"; }
  // „Heute“ ist der Berliner Kalendertag (seit 09.10.2026, Technik-Test 08.10.2026 T-51): Die Kurse sind Berliner Börsentage. Vorher
  // galt das Gerätedatum bzw. die UTC-Grenze – am Fälligkeitstag zwischen 0 und 2 Uhr stand „1 Tag“, in Auckland war ein Kurs einen
  // Börsentag älter als in Berlin. MC.heuteBerlin() → Date um 12:00 UTC dieses Tages; ohne Zeitzonen-Daten im Browser das Ortsdatum.
  // Der Tag bleibt zwischengespeichert, solange er sicher gilt (Berlin ist UTC+1 oder UTC+2: von 13 h vor bis 10 h nach 12:00 UTC).
  var berlinFmt = null, berlinTag = NaN;
  function heuteBerlin() {
    var jetzt = Date.now();
    if (jetzt >= berlinTag - 13 * 36e5 && jetzt < berlinTag + 10 * 36e5) return new Date(berlinTag);
    try {
      if (!berlinFmt) berlinFmt = new Intl.DateTimeFormat("en-US", { timeZone: "Europe/Berlin", year: "numeric", month: "numeric", day: "numeric" });
      var p = {};
      berlinFmt.formatToParts(new Date(jetzt)).forEach(function (x) { p[x.type] = +x.value; });
      if (p.year > 0 && p.month > 0 && p.day > 0) { berlinTag = Date.UTC(p.year, p.month - 1, p.day, 12); return new Date(berlinTag); }
    } catch (e) { /* alter Browser ohne Zeitzonen: Ortsdatum */ }
    var h = new Date(jetzt);
    return new Date(Date.UTC(h.getFullYear(), h.getMonth(), h.getDate(), 12));
  }
  // Veraltete Daten (eine Regel für alle Seiten): ab MC.STALE_TAGE Börsentagen (Mo–Fr, ohne Börsenfeiertage) Alter gilt
  // ein Kurs/Datenstand als „veraltet“. Gezählt wie auf anleihe.html: Börsentage NACH dem Datum bis heute einschließlich
  // (Kurs von Freitag ist am Montag 1 Börsentag alt). MC.boersentage(iso[, bis]) → Anzahl; bis = Date (Ortsdatum), Standard
  // heute in Berlin. Feiertage zählen seit 09.10.2026 nicht mehr mit (T-50: am 30.12. galt ein Kurs vom 23.12. als 5 Tage alt).
  var STALE_TAGE = 5;
  function boersentage(iso, bis) {
    var m = ISO_RE.exec(String(iso || ""));
    if (!m) return null;
    var ende = bis instanceof Date ? Date.UTC(bis.getFullYear(), bis.getMonth(), bis.getDate(), 12) : heuteBerlin().getTime();
    var d = new Date(Date.UTC(+m[1], +m[2] - 1, +m[3], 12)), n = 0;
    while (d.getTime() < ende) { d.setUTCDate(d.getUTCDate() + 1); if (d.getTime() <= ende && d.getUTCDay() % 6 && !feiertag(d, true)) n++; }
    return n;
  }
  function veraltet(iso, bis) { var n = boersentage(iso, bis); return n != null && n >= STALE_TAGE; }

  // Handels- und Abwicklungstage (seit 03.10.2026, Nutzertest: Das Rechenbeispiel rechnete am Samstag mit „Order am 03.10.“).
  // MC.handelstag(d) → d selbst, wenn an dem Tag an der Börse gehandelt wird, sonst der nächste Handelstag (ohne Wochenende,
  // Neujahr, Karfreitag, Ostermontag, 1. Mai, 24.–26. und 31. Dezember – Handelskalender der Börse Frankfurt).
  // MC.plusAbwicklungstage(d, n) → n Abwicklungstage nach d (ohne Wochenende und TARGET-Feiertage: Neujahr, Karfreitag,
  // Ostermontag, 1. Mai, 25. und 26. Dezember) – so liegt die Valuta. d jeweils als Date um 12 Uhr UTC.
  function ostersonntag(j) {   // Gauß/Spencer, gregorianisch
    var a = j % 19, b = Math.floor(j / 100), c = j % 100, d = Math.floor(b / 4), e = b % 4, f = Math.floor((b + 8) / 25),
      g = Math.floor((b - f + 1) / 3), h = (19 * a + b - d - g + 15) % 30, i = Math.floor(c / 4), k = c % 4,
      l = (32 + 2 * e + 2 * i - h - k) % 7, m = Math.floor((a + 11 * h + 22 * l) / 451), mon = Math.floor((h + l - 7 * m + 114) / 31);
    return Date.UTC(j, mon - 1, ((h + l - 7 * m + 114) % 31) + 1, 12);
  }
  function feiertag(d, boerse) {
    var mt = (d.getUTCMonth() + 1) * 100 + d.getUTCDate(), os = ostersonntag(d.getUTCFullYear()), t = d.getTime();
    if (mt === 101 || mt === 501 || mt === 1225 || mt === 1226 || t === os - 2 * 86400000 || t === os + 86400000) return true;
    return !!boerse && (mt === 1224 || mt === 1231);
  }
  function handelstag(d) {
    var x = new Date(Date.UTC(d.getUTCFullYear(), d.getUTCMonth(), d.getUTCDate(), 12));
    while (!(x.getUTCDay() % 6) || feiertag(x, true)) x.setUTCDate(x.getUTCDate() + 1);
    return x;
  }
  function plusAbwicklungstage(d, n) {
    var x = new Date(Date.UTC(d.getUTCFullYear(), d.getUTCMonth(), d.getUTCDate(), 12));
    while (n > 0) { x.setUTCDate(x.getUTCDate() + 1); if (x.getUTCDay() % 6 && !feiertag(x, false)) n--; }
    return x;
  }
  // Feste Umrechnungskurse der früheren Währungen des Euroraums (Einheiten je Euro, unwiderruflich seit 1999 bzw. GRD 2001).
  // Anleihen in DEM, ATS, ITL oder NLG sind damit Euro-Anleihen, kein Wechselkursrisiko (seit 09.10.2026, Technik-Test T-40).
  var EURO_FEST = { DEM: 1.95583, ATS: 13.7603, ITL: 1936.27, NLG: 2.20371, FRF: 6.55957, BEF: 40.3399, LUF: 40.3399, ESP: 166.386,
    PTE: 200.482, FIM: 5.94573, IEP: 0.787564, GRD: 340.750 };

  // Beträge aus Eingabefeldern lesen (seit 03.10.2026, Nutzertest: „5.0001.000“ vor dem vorbelegten Wert wurde im Steckbrief
  // still zu 50.001.000). Tausenderpunkte nur im Dreierabstand („5.000“, „12.500“), Komma für Nachkommastellen, Leerzeichen und
  // „€“ werden ignoriert. opt.ganz: nur ganze Beträge (",00" geht); opt.min / opt.max: Grenzen. Ungültig → NaN.
  function betragLesen(text, opt) {
    opt = opt || {};
    var t = String(text == null ? "" : text).replace(/[\s €]/g, "");
    var m = /^(\d+|\d{1,3}(?:\.\d{3})+)(?:,(\d+))?$/.exec(t);
    if (!m) return NaN;
    var nk = m[2] || "";
    if (opt.ganz && /[1-9]/.test(nk)) return NaN;
    var v = parseFloat(m[1].replace(/\./g, "") + (nk ? "." + nk : ""));
    if (!isFinite(v) || (opt.min != null && v < opt.min) || (opt.max != null && v > opt.max)) return NaN;
    return v;
  }

  // Nav-Dropdowns (die vier Stufen Verstehen, Entscheiden, Kaufen, Einordnen):
  // Hover, per Tastatur Pfeil runter/Leertaste, auf Touch-Geräten erster Tipp; Escape und Außenklick schließen,
  // Öffnen einer Gruppe schließt die anderen. Bis 760 px (Handy): Burger-Knopf
  // .nav-toggle öffnet das Menü (Klasse nav-open am <header>), die Gruppenköpfe
  // klappen als Akkordeon auf und zu statt zu navigieren (die Übersichtsseite
  // steht dort als Eintrag „Übersicht“, nav.py).
  // Setzt außerdem aria-current="page" auf den aktiven Nav-Link.
  function navInit() {
    document.querySelectorAll(".sitenav a.current, .sitenav .nav-group-btn.current")
      .forEach(function (el) { el.setAttribute("aria-current", "page"); });
    // Feste Kopfzeile (base.css, position: sticky): Sobald sie oben anliegt,
    // bekommt sie die Klasse is-stuck (feine Linie zum Inhalt darunter).
    // „Datenquellen und Methodik“ (details.quellen): Link auf #quellen klappt den Text auf.
    var openQuellen = function () {
      if (location.hash !== "#quellen") return;
      var q = document.getElementById("quellen");
      if (q && q.tagName === "DETAILS") q.open = true;
    };
    openQuellen();
    window.addEventListener("hashchange", openQuellen);
    // Weicher Bildlauf (base.css: html.sanft) erst nach dem Laden: Ein Sprung von außen auf einen Anker
    // (z. B. begriffe.html#kupon) steht so sofort an der Stelle, statt über Tausende Pixel zu gleiten (Nutzertest 03.10.2026).
    var sanft = function () { setTimeout(function () { document.documentElement.classList.add("sanft"); }, 200); };
    if (document.readyState === "complete") sanft(); else window.addEventListener("load", sanft);
    var bar = document.querySelector(".topbar");
    if (bar) {
      var stuck = function () { bar.classList.toggle("is-stuck", window.pageYOffset > 0 && bar.getBoundingClientRect().top <= 0.5); };
      window.addEventListener("scroll", stuck, { passive: true });
      stuck();
    }
    var groups = Array.prototype.slice.call(document.querySelectorAll(".nav-group"));
    if (!groups.length) return;
    var closeAll = function (except) {
      groups.forEach(function (g) {
        if (g !== except) { g.classList.remove("open"); g.classList.remove("kb"); g.querySelector(".nav-group-btn").setAttribute("aria-expanded", "false"); }
      });
    };
    // Handy-Akkordeon (base.css: bis 1000 px, bis 26.09.2026: 760 px)
    var mq = window.matchMedia ? window.matchMedia("(max-width: 1000px)") : { matches: false };
    var mobile = function () { return !!mq.matches; };
    var toggle = bar ? bar.querySelector(".nav-toggle") : null;
    var setOpen = function (open) {
      if (!bar || !toggle) return;
      bar.classList.toggle("nav-open", open);
      toggle.setAttribute("aria-expanded", open ? "true" : "false");
      toggle.setAttribute("aria-label", open ? "Menü schließen" : "Menü öffnen");
      closeAll(null);
      if (open) {   // die Stufe der aktuellen Seite gleich aufklappen, damit man sieht, wo man ist
        var cur = bar.querySelector(".nav-group-btn.current");
        if (cur) { cur.parentNode.classList.add("open"); cur.setAttribute("aria-expanded", "true"); }
      }
    };
    if (toggle) toggle.addEventListener("click", function () { setOpen(!bar.classList.contains("nav-open")); });
    // Wechsel Handy ↔ Desktop (Drehen, Fenster ändern): alles zu
    var onChange = function () { setOpen(false); };
    if (mq.addEventListener) mq.addEventListener("change", onChange); else if (mq.addListener) mq.addListener(onChange);
    // Der Gruppen-Kopf ist ein Link (Suche → anleihen-suche.html, Wissen →
    // wissen.html). Mit Maus öffnet das Menü per Hover (CSS), per Tastatur mit
    // Pfeil nach unten oder Leertaste (Klasse kb, unten); ein Klick oder Enter navigiert.
    // Der Fokus allein öffnet nicht mehr (Nutzertest 03.10.2026: Tab führte sonst durch
    // alle 20 Einträge der Akademie, bevor das nächste Menü kam).
    // Seit 23.09.2026 hat das Menü nur noch zwei Köpfe, alle Seiten liegen in
    // den Menüs: Auf Touch-Geräten (kein Hover) öffnet deshalb der erste Tipp
    // das Menü, der zweite Tipp auf den Kopf navigiert; Tipp daneben schließt.
    var touch = window.matchMedia && window.matchMedia("(hover: none)").matches;
    groups.forEach(function (grp) {
      var btn = grp.querySelector(".nav-group-btn");
      var menu = grp.querySelector(".nav-group-menu");
      // Ragt das Menü rechts aus dem Fenster (schmale Bildschirme: Marke und
      // Menü stehen seit 23.09.2026 in einer Zeile), wird es so weit nach links
      // geschoben, dass es passt – höchstens bis 8 px vor den linken Rand.
      var place = function () {
        if (!menu) return;
        menu.classList.remove("nav-menu-right");
        menu.style.left = "";
        var vw = document.documentElement.clientWidth;
        var r = menu.getBoundingClientRect();
        if (!r.width || r.right <= vw - 8) return;
        var shift = Math.min(r.right - (vw - 8), r.left - 8);
        if (shift > 0) menu.style.left = (menu.offsetLeft - shift) + "px";
      };
      // aria-expanded folgt Hover- und Fokuszustand (nicht im Handy-Akkordeon: dort zählt nur .open)
      grp.addEventListener("mouseenter", function () { if (mobile()) return; btn.setAttribute("aria-expanded", "true"); place(); });
      grp.addEventListener("mouseleave", function () { if (mobile()) return; if (!grp.contains(document.activeElement)) btn.setAttribute("aria-expanded", "false"); });
      // Tastatur: Solange der Fokus in der Gruppe steckt, hält die Klasse kb das Menü offen
      // (CSS). Reines :focus-visible/:focus-within reichte nicht: Beim Tab vom Kopf in den
      // ersten Eintrag war das Menü für einen Moment ausgeblendet, der Fokus fiel auf <body>.
      // Ein Maus-Klick auf den Kopf (kein :focus-visible) hält das Menü nicht fest.
      grp.addEventListener("focusin", function (e) {
        if (mobile()) return;
        if (grp._esc) { grp._esc = false; return; }   // Rückkehr per Escape: zu lassen
        if (e.target === btn) return;   // Fokus auf dem Kopf: Menü bleibt zu, Tab geht zum nächsten Kopf
        grp.classList.add("kb");
        btn.setAttribute("aria-expanded", "true"); place();
      });
      grp.addEventListener("focusout", function (e) {
        if (mobile()) return;
        if (!grp.contains(e.relatedTarget)) { grp.classList.remove("kb"); btn.setAttribute("aria-expanded", "false"); }
      });
      // Pfeil nach unten auf dem Kopf: Menü öffnen und ersten Eintrag fokussieren;
      // Leertaste: Menü auf- und zuklappen, der Fokus bleibt auf dem Kopf (Tab führt dann hinein)
      btn.addEventListener("keydown", function (e) {
        if (mobile()) return;
        if (e.key === " " || e.key === "Spacebar") {
          e.preventDefault();
          var auf = !grp.classList.contains("kb");
          closeAll(auf ? grp : null);
          grp.classList.toggle("kb", auf); btn.setAttribute("aria-expanded", auf ? "true" : "false");
          if (auf) place();
          return;
        }
        if (e.key !== "ArrowDown") return;
        e.preventDefault();
        grp.classList.add("kb"); btn.setAttribute("aria-expanded", "true"); place();
        var first = menu && Array.prototype.filter.call(menu.querySelectorAll("a"), function (a) { return a.offsetParent !== null; })[0];
        if (first) first.focus();
      });
      btn.addEventListener("click", function (e) {
        if (mobile()) {   // Akkordeon: Kopf klappt auf und zu, navigiert nicht
          e.preventDefault();
          var open = !grp.classList.contains("open");
          closeAll(null);
          grp.classList.toggle("open", open);
          btn.setAttribute("aria-expanded", open ? "true" : "false");
          return;
        }
        if (!touch) return;
        if (grp.classList.contains("open")) return;   // zweiter Tipp: Link folgen
        e.preventDefault();
        closeAll(grp);
        grp.classList.add("open");
        btn.setAttribute("aria-expanded", "true");
        place();
      });
    });
    var daneben = function (e) {
      if (!e.target || !e.target.closest) return;
      if (e.target.closest(".nav-group")) return;
      if (bar && bar.classList.contains("nav-open") && !e.target.closest(".topbar")) { setOpen(false); return; }   // Tipp neben das offene Handy-Menü
      if (!e.target.closest(".nav-toggle")) closeAll(null);
    };
    document.addEventListener("click", daneben);
    // iPhone/iPad: Ein Fingertipp auf Inhalt ohne eigenen Klick (Text, Überschrift) löst dort kein click am document aus – Menü blieb
    // offen. Deshalb dieselbe Regel schon beim Aufsetzen des Fingers (seit 09.10.2026, Technik-Test 08.10.2026 T-144; wie die Schaubilder
    // unten) – nur in der breiten Ansicht, wo das Menü über dem Inhalt liegt. Im Handy-Akkordeon (bis 1000 px) schiebt das Zuklappen die
    // Seite, bevor der Klick ankommt: Der Tipp auf „Mein Bondarium“ im offenen Menü traf dann etwas anderes. Dort bleibt es beim click.
    document.addEventListener("pointerdown", function (e) { if (e.pointerType === "touch" && !mobile()) daneben(e); });
    // Escape blendet auch das per Maus geöffnete Menü aus (WCAG 1.4.13, seit 09.10.2026, T-124): Klasse nav-esc am <html> bis zur
    // nächsten Mausbewegung – die CSS-Regel dazu (html.nav-esc blendet das Hover-Menü aus) gehört nach base.css; die
    // Schaubild-Tooltips schließt der Escape-Handler in hoverInit.
    var escAus = function () { document.documentElement.classList.remove("nav-esc"); document.removeEventListener("pointermove", escAus); };
    document.addEventListener("keydown", function (e) {
      if (e.key !== "Escape") return;
      document.documentElement.classList.add("nav-esc");
      document.addEventListener("pointermove", escAus);
      if (bar && bar.classList.contains("nav-open")) { setOpen(false); if (toggle) toggle.focus(); return; }
      closeAll(null);
      // Steckt der Fokus in einem Menü-Link, zurück auf den Gruppen-Button; das
      // Menü bleibt dort per :focus-visible sichtbar – aria-expanded entsprechend.
      var a = document.activeElement;
      var g = a && a.closest ? a.closest(".nav-group") : null;
      if (g) { var b = g.querySelector(".nav-group-btn"); if (a !== b) { g._esc = true; b.focus(); } b.setAttribute("aria-expanded", "false"); }
    });

    // Suchfeld in der Kopfzeile (nav.py SEARCH, seit 26.09.2026). Leer abgeschickt (am Handy nur die Lupe):
    // direkt auf die Anleihen-Suche, dort Fokus ins Suchfeld (#suchen). Auf der Suchseite selbst wird der
    // Begriff ohne Neuladen in deren Feld übernommen.
    var ks = bar ? bar.querySelector("form.kopfsuche") : null;
    var seitenFeld = document.querySelector("main input#q") || document.getElementById("q");
    if (ks) ks.addEventListener("submit", function (e) {
      var v = ks.q.value.trim();
      if (seitenFeld) {
        e.preventDefault();
        if (v) { seitenFeld.value = v; seitenFeld.dispatchEvent(new Event("input", { bubbles: true })); ks.q.value = ""; }
        setOpen(false);
        seitenFeld.focus();
        return;
      }
      if (!v) { e.preventDefault(); location.href = ks.action.split("?")[0] + "#suchen"; }
    });
    if (location.hash === "#suchen" && seitenFeld) {
      seitenFeld.focus();
      if (history.replaceState) history.replaceState(null, "", location.pathname + location.search);
    }
  }

  // --- Hover-Tooltip für Charts: beim Überfahren wird der nächstgelegene
  // Datenpunkt mit Markierungslinie, Punkt(en) und Label (Datum + Wert)
  // angezeigt; per Tastatur (Fokus + Pfeiltasten) und Tippen ebenso.
  //
  // Verwendung: Chart-SVG-String beim Rendern in hoverWrap(svg, series, label)
  // einpacken. series = Array von { x:[..], y:[..], tips:[..], color? } in
  // viewBox-Koordinaten. Mehrere Serien teilen sich die Markierungslinie;
  // jede Serie bekommt einen eigenen Punkt und eine eigene Label-Zeile.
  // Serien mit Lücken (Punkt weiter als ~1,5 Schritte entfernt) werden an
  // dieser Stelle ausgelassen. Die Event-Handler sind auf document delegiert
  // und überstehen dadurch Re-Renders (Datenladen, Resize).
  // opts.mode = "nearest": statt aller Serien wird nur die dem Zeiger
  // nächstgelegene Linie angezeigt (Punkt + eine Label-Zeile); per Tastatur
  // bleibt die zuletzt gewählte Serie aktiv.
  function hoverWrap(svgStr, series, label, opts) {
    var clean = (series || []).filter(function (s) { return s && s.x && s.x.length; });
    if (!clean.length) return svgStr;
    // Zugänglicher Name für den fokussierbaren Wrapper (role="group", damit
    // die Live-Region mit den Werten darin vorgelesen wird): explizites
    // Label, sonst das aria-label des inneren SVGs übernehmen (das SVG wird
    // dann versteckt, um Doppelnennungen zu vermeiden), sonst Standardtext.
    var m = !label && svgStr.match(/ role="img" aria-label="([^"]*)"/);
    var aria = label ? esc(label) : m ? m[1] : "Interaktives Schaubild – Werte mit den Pfeiltasten abrufbar";
    if (m) svgStr = svgStr.replace(' role="img" aria-label="' + m[1] + '"', ' aria-hidden="true"');
    // Seit 30.09.2026 stehen die Tooltip-Daten nicht mehr als JSON im Attribut (risikoaufschlaege.html hatte 220 KB
    // data-hover im DOM): data-hover trägt nur noch eine kurze Kennung, die Daten liegen in HOVER_DATEN (JS).
    var id = "h" + (++hoverNr);
    HOVER_DATEN[id] = { d: clean, t: Date.now() };
    aufraeumen();
    return '<div class="hovergraph" tabindex="0" role="group" aria-label="' + aria +
      '" aria-roledescription="Schaubild"' + (opts && opts.mode === "nearest" ? ' data-hover-mode="nearest"' : "") +
      ' data-hover="' + id + '">' + svgStr + "</div>";
  }
  // Kennung → Daten. Einträge, deren Chart nicht mehr im Dokument steht (neu gezeichnet, z. B. nach Resize), werden
  // nach 10 s verworfen; ein bereits angezeigter Chart behält seine Daten über HOVER_EL (WeakMap am Element).
  var HOVER_DATEN = {}, hoverNr = 0, HOVER_EL = typeof WeakMap === "function" ? new WeakMap() : null, aufraeumTimer = 0;
  function aufraeumen() {
    if (aufraeumTimer) return;
    aufraeumTimer = setTimeout(function () {
      aufraeumTimer = 0;
      var jetzt = Date.now(), offen = false;
      Object.keys(HOVER_DATEN).forEach(function (id) {
        if (jetzt - HOVER_DATEN[id].t < 10000) { offen = true; return; }
        if (!document.querySelector('.hovergraph[data-hover="' + id + '"]')) delete HOVER_DATEN[id];
      });
      if (offen) aufraeumen();
    }, 11000);
  }

  function hoverInit() {
    if (document.__mcHoverInit) return;
    document.__mcHoverInit = true;

    // Daten eines Charts: aus der Kennung in data-hover (hoverWrap); ältere Seiten-Kopien mit JSON im Attribut gehen weiter
    function dataOf(wrap) {
      var raw = wrap.getAttribute("data-hover") || "";
      if (HOVER_EL) { var c = HOVER_EL.get(wrap); if (c && c.raw === raw) return c.d; }
      var d = null;
      if (HOVER_DATEN[raw]) d = HOVER_DATEN[raw].d;
      else if (raw.charAt(0) === "[") { try { d = JSON.parse(raw); } catch (e) { d = null; } }
      if (HOVER_EL && d) HOVER_EL.set(wrap, { raw: raw, d: d });
      return d;
    }

    // Abbildung viewBox-Koordinaten -> Pixel relativ zum Wrapper. Beachtet
    // preserveAspectRatio="none" (Sparklines) wie auch das Standard-
    // "xMidYMid meet" (große Charts mit Letterboxing).
    function mapOf(wrap) {
      var svg = wrap.querySelector("svg");
      if (!svg || !svg.viewBox) return null;
      var vb = svg.viewBox.baseVal;
      var r = svg.getBoundingClientRect(), wr = wrap.getBoundingClientRect();
      if (!vb || !(vb.width > 0) || !(r.width > 0)) return null;
      var sx, sy, ox, oy;
      if ((svg.getAttribute("preserveAspectRatio") || "").indexOf("none") === 0) {
        sx = r.width / vb.width; sy = r.height / vb.height; ox = 0; oy = 0;
      } else {
        sx = sy = Math.min(r.width / vb.width, r.height / vb.height);
        ox = (r.width - vb.width * sx) / 2; oy = (r.height - vb.height * sy) / 2;
      }
      var dx = r.left - wr.left + ox, dy = r.top - wr.top + oy;
      return {
        px: function (v) { return dx + (v - vb.x) * sx; },
        py: function (v) { return dy + (v - vb.y) * sy; },
        vx: function (clientX) { return vb.x + (clientX - r.left - ox) / sx; },
        vy: function (clientY) { return vb.y + (clientY - r.top - oy) / sy; },
        left: dx, top: dy, width: vb.width * sx, height: vb.height * sy
      };
    }

    function nearest(arr, v) {
      var i = 0, bd = Infinity;
      for (var k = 0; k < arr.length; k++) { var d = Math.abs(arr[k] - v); if (d < bd) { bd = d; i = k; } }
      return i;
    }
    // Typischer Abstand zweier Datenpunkte einer Serie (für die Lücken-Prüfung)
    function stepOf(s) {
      if (!s.__step) s.__step = s.x.length > 1 ? Math.abs(s.x[s.x.length - 1] - s.x[0]) / (s.x.length - 1) : Infinity;
      return s.__step;
    }

    function hideAll(except) {
      document.querySelectorAll(".hovergraph.tipon").forEach(function (w) { if (w !== except) w.classList.remove("tipon"); });
    }

    // Zeigt den Tooltip; refX/refY = Cursor-/Referenzposition in viewBox-
    // Einheiten (refY nur im Modus "nearest" relevant, per Tastatur null).
    function show(wrap, refX, refY) {
      var data = dataOf(wrap), map = mapOf(wrap);
      if (!data || !map) return;
      var line = wrap.querySelector(".tipline"), lab = wrap.querySelector(".tiplab");
      if (!line) {
        line = document.createElement("span"); line.className = "tipline";
        lab = document.createElement("span"); lab.className = "tiplab";
        lab.setAttribute("aria-live", "polite"); // Screenreader liest den Wert bei Pfeiltasten-Navigation vor
        wrap.append(line, lab);
      }
      var dots = wrap.querySelectorAll(".tipdot");
      if (dots.length !== data.length) {
        dots.forEach(function (d) { d.remove(); });
        dots = data.map(function (s) {
          var d = document.createElement("span"); d.className = "tipdot";
          if (s.color) d.style.background = s.color;
          wrap.appendChild(d); return d;
        });
      }
      var i0 = nearest(data[0].x, refX);
      wrap.dataset.tipIdx = i0;
      var x0 = data[0].x[i0];
      var lineX = map.px(x0);
      var lines = [], topY = Infinity;
      // Modus "nearest": nur die Serie zeigen, deren Punkt dem Zeiger (in
      // viewBox-Einheiten) vertikal am nächsten liegt
      var only = -1;
      if (wrap.getAttribute("data-hover-mode") === "nearest") {
        if (refY != null) {
          var bd = Infinity;
          data.forEach(function (s, si) {
            var i = si === 0 ? i0 : nearest(s.x, x0);
            if (si !== 0 && Math.abs(s.x[i] - x0) > stepOf(s) * 1.5) return;
            var d = Math.abs(s.y[i] - refY);
            if (d < bd) { bd = d; only = si; }
          });
          wrap.dataset.tipSeries = only;
        } else if (wrap.dataset.tipSeries != null) only = Number(wrap.dataset.tipSeries);
      }
      data.forEach(function (s, si) {
        var i = si === 0 ? i0 : nearest(s.x, x0);
        // Serie hat an dieser Stelle keine Daten (z. B. China vor 2002): auslassen
        if (si !== 0 && Math.abs(s.x[i] - x0) > stepOf(s) * 1.5) { dots[si].style.display = "none"; return; }
        if (only >= 0 && si !== only) { dots[si].style.display = "none"; return; }
        var px = map.px(s.x[i]), py = map.py(s.y[i]);
        dots[si].style.display = ""; dots[si].style.left = px + "px"; dots[si].style.top = py + "px";
        if (py < topY) topY = py;
        lines.push(s.tips && s.tips[i] != null ? s.tips[i] : "");
      });
      line.style.left = lineX + "px"; line.style.top = map.top + "px"; line.style.height = map.height + "px";
      lab.textContent = lines.join("\n");
      wrap.classList.add("tipon");
      var lw = lab.offsetWidth, lh = lab.offsetHeight;
      lab.style.left = Math.max(map.left, Math.min(map.left + map.width - lw, lineX - lw / 2)) + "px";
      lab.style.top = (topY - lh - 10 < map.top ? Math.min(topY + 14, map.top + map.height - lh) : topY - lh - 10) + "px";
    }

    // Mausbewegung per requestAnimationFrame gedrosselt (max. 1 Update je
    // Frame statt je Event – spart getBoundingClientRect-Reflows)
    var rafId = 0, lastMove = null, lastDown = 0;
    document.addEventListener("pointermove", function (e) {
      lastMove = e;
      if (rafId) return;
      rafId = requestAnimationFrame(function () {
        rafId = 0;
        var ev = lastMove;
        var wrap = ev.target && ev.target.closest ? ev.target.closest(".hovergraph[data-hover]") : null;
        hideAll(wrap);
        if (!wrap) return;
        var map = mapOf(wrap);
        if (map) show(wrap, map.vx(ev.clientX), map.vy(ev.clientY));
      });
    });
    // Verlässt der Zeiger das Fenster über einem Chart, bleibt kein Tooltip stehen – nur für Maus/Stift:
    // Bei Touch feuert der Browser nach dem Loslassen ebenfalls pointerleave; das blendete den
    // angetippten Wert sofort wieder aus (Fehler auf allen Charts am Handy, behoben 26.09.2026).
    document.documentElement.addEventListener("pointerleave", function (e) { if (e.pointerType !== "touch") hideAll(null); });
    // Touch: Antippen zeigt den nächstgelegenen Punkt, Tippen außerhalb blendet aus
    document.addEventListener("pointerdown", function (e) {
      var wrap = e.target && e.target.closest ? e.target.closest(".hovergraph[data-hover]") : null;
      if (!wrap) { hideAll(null); return; }
      lastDown = Date.now();
      var map = mapOf(wrap);
      if (map) show(wrap, map.vx(e.clientX), map.vy(e.clientY));
    });
    // Tastatur: Fokus zeigt den letzten Datenpunkt, Pfeiltasten wandern, Escape
    // schließt. Der Fokus, der einem Tap/Klick folgt, überschreibt den getippten
    // Punkt NICHT (sonst springt der Tooltip zum letzten Wert).
    document.addEventListener("focusin", function (e) {
      var t = e.target;
      var wrap = (t && t.classList && t.classList.contains("hovergraph") && t.getAttribute("data-hover")) ? t : null;
      if (wrap && Date.now() - lastDown < 600) return;
      hideAll(wrap);
      if (!wrap) return;
      var data = dataOf(wrap);
      if (data) show(wrap, data[0].x[data[0].x.length - 1]);
    });
    document.addEventListener("focusout", function (e) {
      if (e.target && e.target.classList && e.target.classList.contains("hovergraph")) e.target.classList.remove("tipon");
    });
    document.addEventListener("keydown", function (e) {
      // Escape schließt jeden offenen Tooltip – auch den per Maus eingeblendeten, ohne Fokus im Schaubild (WCAG 1.4.13,
      // seit 09.10.2026, Technik-Test 08.10.2026 T-124); die nächste Mausbewegung über dem Schaubild zeigt ihn wieder
      if (e.key === "Escape") { hideAll(null); return; }
      var wrap = document.activeElement;
      if (!(wrap && wrap.classList && wrap.classList.contains("hovergraph") && wrap.getAttribute("data-hover"))) return;
      if (e.key === "ArrowLeft" || e.key === "ArrowRight" || e.key === "Home" || e.key === "End") {
        e.preventDefault();
        var data = dataOf(wrap);
        if (!data) return;
        var n = data[0].x.length;
        var cur = Number(wrap.dataset.tipIdx != null ? wrap.dataset.tipIdx : n - 1);
        var i = e.key === "Home" ? 0 : e.key === "End" ? n - 1 : Math.max(0, Math.min(n - 1, cur + (e.key === "ArrowRight" ? 1 : -1)));
        show(wrap, data[0].x[i]);
      }
    });
  }
  hoverInit();

  // --- Wisch-Hinweis für quer scrollende Tabellen und Grafiken (seit 30.09.2026) ---
  // Früher zeigte base.css den Hinweis „← Tabelle breiter als der Bildschirm – wischen →“ am Handy immer – auch
  // wenn nichts überlief (alle Chart-Seiten). Jetzt setzt site.js die Klasse „ueberlauf“ an .table-scroll/.chart-scroll
  // nur, solange der Inhalt wirklich breiter ist (scrollWidth > clientWidth); base.css zeigt den Hinweis nur dann.
  // Geprüft beim Laden, bei Größenänderung und wenn Seitenskripte Inhalte nachzeichnen. Eigener Text: data-wisch="…".
  // MC.wischPruefen() stößt die Prüfung von Hand an (z. B. nach dem Aufklappen eines Bereichs).
  var wischPlan = 0, wischRO = null;
  function wischPruefen() {
    if (wischPlan) return;
    var lauf = function () {
      wischPlan = 0;
      document.querySelectorAll(".table-scroll, .chart-scroll").forEach(function (el) {
        if (wischRO && !el.__wischRO) { el.__wischRO = true; wischRO.observe(el); if (el.firstElementChild) wischRO.observe(el.firstElementChild); }
        var breit = el.clientWidth > 0 && el.scrollWidth > el.clientWidth + 1;
        if (el.classList.contains("ueberlauf") !== breit) el.classList.toggle("ueberlauf", breit);
      });
    };
    wischPlan = setTimeout(lauf, 50);   // setTimeout statt requestAnimationFrame: rAF kann in Hintergrund-Frames ausbleiben
  }
  function wischInit() {
    window.addEventListener("resize", wischPruefen);
    window.addEventListener("load", wischPruefen);
    if (document.fonts && document.fonts.addEventListener) document.fonts.addEventListener("loadingdone", wischPruefen);   // Webfont ändert die Breite
    // Größe des Containers und seines Inhalts (Tabelle/SVG) beobachten; neue Container meldet der MutationObserver
    if (window.ResizeObserver) wischRO = new ResizeObserver(wischPruefen);
    wischPruefen();
    if (window.MutationObserver && document.body) {
      new MutationObserver(function (list) {
        for (var i = 0; i < list.length; i++) {
          var t = list[i].target;
          // Tooltip-Beschriftung und die Klasse selbst lösen keine neue Prüfung aus
          if (t.nodeType === 1 && t.closest && t.closest(".hovergraph")) continue;
          wischPruefen(); return;
        }
      }).observe(document.body, { childList: true, subtree: true });
    }
  }
  wischInit();

  // --- Kursverlauf einer Anleihe oder eines ETFs (seit 25.09.2026) ---
  // Daten: scripts/update_kurse.py. Deutsche Börse (Frankfurt, Xetra, Tradegate) ab 24.09.2026 in
  // kurse/<Jahr>/<teil>.json (256 Teildateien je Jahr), Bundeswertpapiere seit Ausgabe (Bundesbank)
  // in kurse/bund/<ISIN>.json. teil() MUSS mit update_kurse.py übereinstimmen.
  // Seit 30.09.2026 ohne blinde Jahresabrufe: kurse/jahre.json (scripts/kurse_jahre.py) sagt, welche Teildateien es je
  // Jahr gibt und welche ISINs einen Bundesbank-Verlauf haben – geladen werden nur vorhandene Dateien (keine 404 mehr).
  // Fehlt die Liste, gilt die alte Schleife ab VERLAUF_AB (die Zeile setzt scripts/import_kurshistorie.py --site-js).
  // Jahre nach dem letzten gelisteten Jahr bis heute werden immer versucht (Jahreswechsel vor dem nächsten Listenlauf).
  var VERLAUF_AB = 2021;
  function teil(isin) {
    var h = 0;
    for (var i = 0; i < isin.length; i++) h = (h * 31 + isin.charCodeAt(i)) % 65536;
    return ("0" + (h % 256).toString(16)).slice(-2);
  }
  var jahreListe = null;
  function kursJahre() {
    if (!jahreListe) jahreListe = json("kurse/jahre.json").then(function (d) { return d && d.jahre ? d : null; }, function () { return null; });
    return jahreListe;
  }
  // MC.verlauf(isin[, bund][, opts]) → Promise {t: [Datum], k: [Kurs], u: [Umsatz oder 0], bund?: true}
  //   bund = true: Bundeswertpapier – erst den Bundesbank-Verlauf kurse/bund/<ISIN>.json, sonst Börse.
  //   opts.ab = "JJJJ-MM-TT": nur Jahre ab diesem Datum laden und nur Punkte ab diesem Tag liefern
  //   (langlaeufer.html braucht nur die Kurse nach dem letzten eingebetteten Wochenkurs).
  //   Aufruf auch als MC.verlauf(isin, {ab: …}).
  function verlauf(isin, bund, opts) {
    if (bund && typeof bund === "object") { opts = bund; bund = false; }
    opts = opts || {};
    var ab = typeof opts.ab === "string" && /^\d{4}-\d{2}-\d{2}/.test(opts.ab) ? opts.ab.slice(0, 10) : "";
    var abJahr = ab ? +ab.slice(0, 4) : 0;
    var schneide = function (v) {
      if (!ab) return v;
      var out = { t: [], k: [], u: [] };
      if (v.bund) out.bund = true;
      v.t.forEach(function (t, i) { if (t >= ab) { out.t.push(t); out.k.push(v.k[i]); out.u.push(v.u ? v.u[i] || 0 : 0); } });
      return out;
    };
    var boerse = function (liste) {
      var jetzt = new Date().getFullYear(), t = teil(isin), jahre = [], j;
      if (liste) {
        var letztes = 0;
        Object.keys(liste.jahre).forEach(function (y) {
          var n = +y, s = liste.jahre[y];
          if (n > letztes) letztes = n;
          for (var i = 0; i < s.length; i += 2) if (s.substr(i, 2) === t) { jahre.push(n); break; }
        });
        for (j = letztes + 1; j <= jetzt; j++) jahre.push(j);
      } else for (j = VERLAUF_AB; j <= jetzt; j++) jahre.push(j);
      jahre = jahre.filter(function (y) { return y >= abJahr; }).sort(function (x, y) { return x - y; });
      return Promise.all(jahre.map(function (y) {
        return json("kurse/" + y + "/" + t + ".json").catch(function () { return null; });
      })).then(function (files) {
        var out = { t: [], k: [], u: [] };
        files.forEach(function (f) {
          if (!f || !f.k || !f.k[isin]) return;
          var reihe = f.k[isin], um = (f.u && f.u[isin]) || {};
          f.tage.forEach(function (tag, i) {
            if (reihe[i] == null) return;
            out.t.push(tag); out.k.push(reihe[i]); out.u.push(um[i] || 0);
          });
        });
        return schneide(out);
      });
    };
    return kursJahre().then(function (liste) {
      if (!bund || (liste && liste.bund && liste.bund.indexOf(isin) < 0)) return boerse(liste);
      return json("kurse/bund/" + isin + ".json").then(function (d) {
        return schneide({ t: d.t, k: d.k, u: d.t.map(function () { return 0; }), bund: true });
      }).catch(function () { return boerse(liste); });
    });
  }

  // MC.kursChart (Kursverlauf zeichnen) steht seit 30.09.2026 in chart.js – nur anleihe.html und anleihen-etf.html laden es.

  // --- Einordnung gegen die eigene Historie (seit 09/2026) ---
  // Einzige Quelle der Perzentil-/Einstufungsregel für Startseite, Bewertungs-
  // und Zinsen-Seite. percentile(v, arr): Anteil der Referenzwerte (z. B.
  // Jahresdurchschnitte seit 1928) unterhalb von v in Prozent, Gleichstände
  // zur Hälfte; null bei unbrauchbaren Eingaben.
  function isNum(x) { return typeof x === "number" && isFinite(x); }
  function percentile(v, arr) {
    var s = (arr || []).filter(isNum);
    if (!s.length || !isNum(v)) return null;
    var below = 0, equal = 0;
    for (var i = 0; i < s.length; i++) { if (s[i] < v) below++; else if (s[i] === v) equal++; }
    return (below + equal / 2) / s.length * 100;
  }
  // Mittelwert, Median, Spanne einer Reihe (für „Ø seit …“ und Hoch/Tief-Angaben)
  function stats(arr) {
    var s = (arr || []).filter(isNum).sort(function (a, b) { return a - b; });
    var n = s.length;
    if (!n) return null;
    var sum = 0;
    for (var i = 0; i < n; i++) sum += s[i];
    return { n: n, mean: sum / n, median: n % 2 ? s[(n - 1) / 2] : (s[n / 2 - 1] + s[n / 2]) / 2, min: s[0], max: s[n - 1] };
  }
  // Einstufung nach Perzentil-Bändern – die offengelegte Regel der Seite:
  // unter 10 % · 10–30 % · 30–70 % · 70–90 % · ab 90 % der Historie.
  // kind "valuation": hoher Wert = teuer (Bewertungskennzahlen);
  // kind "level": wertneutral (Zinsen, Inflation, Zinskurve);
  // invert: true dreht die Skala (z. B. Risikoprämie: hoher Wert = günstig).
  var RATE_BANDS = [10, 30, 70, 90];
  var RATE_WORDS = {
    valuation: ["sehr günstig", "günstig", "fair", "teuer", "sehr teuer"],
    level: ["sehr niedrig", "niedrig", "mittel", "hoch", "sehr hoch"]
  };
  // Bildwelt 2.0 (30.09.2026): Datenpalette – günstig Tiefgrün, fair Grau, teuer Orange; wertneutral in Tinte
  var RATE_COLORS = {
    valuation: ["#157C00", "#157C00", "#55544F", "#CF7430", "#A2561C"],
    level: ["#1A1A19", "#1A1A19", "#55544F", "#1A1A19", "#1A1A19"]
  };
  function rate(pct, kind, invert) {
    if (!isNum(pct)) return null;
    var k = RATE_WORDS[kind] ? kind : "level";
    var p = invert ? 100 - pct : pct;
    var idx = 0;
    while (idx < RATE_BANDS.length && p >= RATE_BANDS[idx]) idx++;
    return { idx: idx, label: RATE_WORDS[k][idx], color: RATE_COLORS[k][idx], pct: pct, extreme: idx === 0 || idx === 4 };
  }
  // Satzbaustein „höher als in 98 % der Jahre seit 1928“ (unit z. B. "Jahre"/"Monate")
  function pctText(pct, unit, since) {
    if (!isNum(pct)) return "";
    var p = Math.round(pct);
    var word = p >= 50 ? "höher als in " + p + "\u00a0%" : "niedriger als in " + Math.round(100 - pct) + "\u00a0%";
    return word + " der " + unit + (since ? " seit " + since : "");
  }
  // Status-Pille wie auf Startseite/Stimmungsseiten; Inhalt nur aus den Regelwörtern
  function ratePill(r) {
    return r ? '<span class="pill" style="background:' + r.color + '">' + esc(r.label) + '</span>' : "";
  }

  // Besucherzählung (seit 01.10.2026, docs/STATISTIK.md): meldet den Seitenaufruf an aufruf.php – ohne Cookies und
  // ohne Speicherung im Browser. Gesendet werden nur Pfad (ohne Suchparameter), Herkunft (Referrer) und utm_source.
  // Nicht gezählt: lokale Dateien, automatisierte Browser, „Global Privacy Control“ und „Do Not Track“.
  (function zaehlen() {
    try {
      var n = navigator, l = location;
      if (!/^https?:$/.test(l.protocol) || n.webdriver || n.globalPrivacyControl || n.doNotTrack === "1" || window.doNotTrack === "1") return;
      var q = (l.search.match(/[?&]utm_source=([^&#]*)/) || [])[1] || "";
      var daten = "p=" + encodeURIComponent(l.pathname) + "&r=" + encodeURIComponent(document.referrer || "") + "&q=" + q.slice(0, 100);
      var senden = function () {
        if (n.sendBeacon) n.sendBeacon("/aufruf.php", new Blob([daten], { type: "application/x-www-form-urlencoded" }));
        else fetch("/aufruf.php", { method: "POST", body: daten, keepalive: true, credentials: "omit",
          headers: { "Content-Type": "application/x-www-form-urlencoded" } }).catch(function () {});
      };
      // vorab geladene Seiten (Prerender) erst zählen, wenn sie wirklich gezeigt werden
      if (document.prerendering) document.addEventListener("prerenderingchange", senden, { once: true }); else senden();
    } catch (e) { /* Zählen darf die Seite nie stören */ }
  })();

  return { esc: esc, minus: minus, zahl: zahl, datum: datum, tag: tag, STALE_TAGE: STALE_TAGE, heuteBerlin: heuteBerlin, boersentage: boersentage, veraltet: veraltet,
    handelstag: handelstag, plusAbwicklungstage: plusAbwicklungstage, EURO_FEST: EURO_FEST, betragLesen: betragLesen,
    restlaufzeit: restlaufzeit, kuendigung: kuendigung, kuendigungFeld: kuendigungFeld, load: load, json: json, navInit: navInit, hoverWrap: hoverWrap, wischPruefen: wischPruefen,
    percentile: percentile, stats: stats, rate: rate, pctText: pctText, ratePill: ratePill,
    teil: teil, verlauf: verlauf };
})();
