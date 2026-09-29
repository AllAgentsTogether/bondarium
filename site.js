/* site.js – gemeinsame Helfer für alle Seiten. Wird vor dem seitenspezifischen
   Inline-Script am Body-Ende geladen (DOM ist dann bereits geparst).
   Einzige Quelle für: HTML-Escaping (XSS-Schutz), Datenladen (eingebettete
   Deploy-Daten vor fetch), Nav-Dropdowns inkl. aria-current, Chart-Tooltips und
   die Einordnungsregel (Perzentil/Einstufung gegen die eigene Historie). */
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

  // Daten laden. Der Deploy-Workflow bettet die JSON-Dateien als
  // <script type="application/json" data-mc="renditen.json"> in jede Seite ein
  // (scripts/inline_data.py) – dann entfällt der zusätzliche Request und der
  // erste Render zeigt bereits die aktuellen Werte (kein Sprung, kein
  // „Flash“ alter Fallback-Zahlen). Ohne eingebettete Daten (lokal/Entwicklung)
  // wird wie bisher per fetch geladen.
  function load(name) {
    var el = document.querySelector('script[type="application/json"][data-mc="' + name + '"]');
    if (el) {
      try { return Promise.resolve(JSON.parse(el.textContent)); }
      catch (e) { /* defekter Block: auf fetch zurückfallen */ }
    }
    return fetch(name).then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); });
  }

  // Nav-Dropdowns (die vier Stufen Verstehen, Entscheiden, Kaufen, Einordnen):
  // Hover/Fokus, auf Touch-Geräten erster Tipp; Escape und Außenklick schließen,
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
    // wissen.html). Mit Maus öffnet das Menü per Hover (CSS), per Tastatur über
    // den Fokus (Klasse kb, unten); ein Klick navigiert.
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
        var kb = e.target !== btn || !btn.matches || btn.matches(":focus-visible");
        if (kb) grp.classList.add("kb");
        btn.setAttribute("aria-expanded", "true"); place();
      });
      grp.addEventListener("focusout", function (e) {
        if (mobile()) return;
        if (!grp.contains(e.relatedTarget)) { grp.classList.remove("kb"); btn.setAttribute("aria-expanded", "false"); }
      });
      // Pfeil nach unten auf dem Kopf: Menü öffnen und ersten Eintrag fokussieren
      btn.addEventListener("keydown", function (e) {
        if (e.key !== "ArrowDown" || mobile()) return;
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
    document.addEventListener("click", function (e) {
      if (!e.target.closest) return;
      if (e.target.closest(".nav-group")) return;
      if (bar && bar.classList.contains("nav-open") && !e.target.closest(".topbar")) { setOpen(false); return; }   // Tipp neben das offene Handy-Menü
      if (!e.target.closest(".nav-toggle")) closeAll(null);
    });
    document.addEventListener("keydown", function (e) {
      if (e.key !== "Escape") return;
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
    var aria = label ? esc(label) : m ? m[1] : "Interaktives Diagramm – Werte mit den Pfeiltasten abrufbar";
    if (m) svgStr = svgStr.replace(' role="img" aria-label="' + m[1] + '"', ' aria-hidden="true"');
    return '<div class="hovergraph" tabindex="0" role="group" aria-label="' + aria +
      '" aria-roledescription="Diagramm"' + (opts && opts.mode === "nearest" ? ' data-hover-mode="nearest"' : "") +
      ' data-hover="' + esc(JSON.stringify(clean)) + '">' + svgStr + "</div>";
  }

  function hoverInit() {
    if (document.__mcHoverInit) return;
    document.__mcHoverInit = true;

    function dataOf(wrap) {
      var raw = wrap.getAttribute("data-hover");
      if (wrap.__mcHoverRaw !== raw) {
        try { wrap.__mcHover = JSON.parse(raw); } catch (e) { wrap.__mcHover = null; }
        wrap.__mcHoverRaw = raw;
      }
      return wrap.__mcHover;
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
      } else if (e.key === "Escape") {
        wrap.classList.remove("tipon");
      }
    });
  }
  hoverInit();

  // --- Kursverlauf einer Anleihe oder eines ETFs (seit 25.09.2026) ---
  // Daten: scripts/update_kurse.py. Deutsche Börse (Frankfurt, Xetra, Tradegate) ab 24.09.2026 in
  // kurse/<Jahr>/<teil>.json (256 Teildateien je Jahr), Bundeswertpapiere seit Ausgabe (Bundesbank)
  // in kurse/bund/<ISIN>.json. teil() MUSS mit update_kurse.py übereinstimmen.
  var VERLAUF_AB = 2021;
  function teil(isin) {
    var h = 0;
    for (var i = 0; i < isin.length; i++) h = (h * 31 + isin.charCodeAt(i)) % 65536;
    return ("0" + (h % 256).toString(16)).slice(-2);
  }
  var jsonCache = {};
  function json(url) {
    if (!jsonCache[url]) jsonCache[url] = fetch(url).then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); });
    return jsonCache[url];
  }
  // → Promise {t: [Datum], k: [Kurs], u: [Umsatz oder 0]}; bund = Bundeswertpapier (Bundesbank-Verlauf)
  function verlauf(isin, bund) {
    var boerse = function () {
      var jahre = [];
      for (var j = VERLAUF_AB; j <= new Date().getFullYear(); j++) jahre.push(j);
      return Promise.all(jahre.map(function (j) {
        return json("kurse/" + j + "/" + teil(isin) + ".json").catch(function () { return null; });
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
        return out;
      });
    };
    if (!bund) return boerse();
    return json("kurse/bund/" + isin + ".json").then(function (d) {
      return { t: d.t, k: d.k, u: d.t.map(function () { return 0; }), bund: true };
    }).catch(boerse);
  }

  var MON = ["Jan.", "Feb.", "März", "Apr.", "Mai", "Juni", "Juli", "Aug.", "Sep.", "Okt.", "Nov.", "Dez."];
  function zahl(v, dec) { return minus(v.toLocaleString("de-DE", { minimumFractionDigits: dec, maximumFractionDigits: dec })); }
  function datumLang(iso) { return iso.slice(8, 10) + "." + iso.slice(5, 7) + "." + iso.slice(0, 4); }
  function zeitOf(iso) { return Date.UTC(+iso.slice(0, 4), +iso.slice(5, 7) - 1, +iso.slice(8, 10)); }
  function schritt(spanne) {   // „schöne“ Achsenschritte
    var roh = spanne / 4, p = Math.pow(10, Math.floor(Math.log10(roh))), n = roh / p;
    return (n < 1.5 ? 1 : n < 3.5 ? 2 : n < 7.5 ? 5 : 10) * p;
  }

  // Kursverlauf zeichnen. el: Container; v: verlauf(); o: {einheit: "%" | "€", name, waehrung, breit}
  // Zeitraum-Knöpfe erscheinen nur, wenn der Verlauf länger ist als der Zeitraum.
  var ZEITRAUM = [["1 Monat", 31], ["3 Monate", 92], ["1 Jahr", 366], ["5 Jahre", 1827], ["Alles", Infinity]];
  function kursChart(el, v, o) {
    o = o || {};
    var einheit = o.einheit || "%";
    var fmtK = function (x) { return zahl(x, x < 10 ? 3 : 2) + (einheit === "%" ? "\u00a0%" : "\u00a0€"); };
    el.__kvArgs = [v, o];
    if (!el.__kvResize) {   // bei Größenänderung in der neuen Breite zeichnen (Handy drehen, Fenster ziehen)
      var rt;
      el.__kvResize = function () {
        clearTimeout(rt);
        rt = setTimeout(function () {
          if (el.isConnected && el.__kvCW && Math.abs(el.clientWidth - el.__kvCW) > 24) kursChart(el, el.__kvArgs[0], el.__kvArgs[1]);
        }, 150);
      };
      window.addEventListener("resize", el.__kvResize);
    }
    if (!v || !v.t || !v.t.length) {
      el.innerHTML = '<p class="kv-leer">Für dieses Papier gibt es noch keinen Kursverlauf – er beginnt mit dem ersten Börsentag, an dem ein Kurs festgestellt wird.</p>';
      return;
    }
    if (v.t.length < 2) {
      el.innerHTML = '<p class="kv-leer">Kursverlauf ab ' + datumLang(v.t[0]) + ': bisher ein Kurs (' + fmtK(v.k[0]) +
        '). Ab jetzt kommt jeden Börsentag ein Wert dazu – die Linie wächst täglich.</p>';
      return;
    }
    if (v.t.length < 5) {   // zwei bis vier Punkte ergäben nur eine flache Linie über die volle Breite
      el.innerHTML = '<p class="kv-leer">Kursverlauf wird seit ' + datumLang(v.t[0]) + ' gesammelt: bisher ' + v.t.length + ' Kurse, zuletzt ' +
        fmtK(v.k[v.k.length - 1]) + ' (' + datumLang(v.t[v.t.length - 1]) + '). Ab fünf Börsentagen erscheint hier die Linie.</p>';
      return;
    }
    var ende = zeitOf(v.t[v.t.length - 1]), tageGesamt = (ende - zeitOf(v.t[0])) / 864e5;
    var wahl = ZEITRAUM.filter(function (z) { return z[1] === Infinity || z[1] < tageGesamt; });
    var aktiv = el.__kvZeitraum && wahl.some(function (z) { return z[0] === el.__kvZeitraum; }) ? el.__kvZeitraum
      : (wahl.filter(function (z) { return z[1] === 366; })[0] || wahl[wahl.length - 1])[0];
    el.__kvZeitraum = aktiv;
    var tage = wahl.filter(function (z) { return z[0] === aktiv; })[0][1];
    var i0 = 0;
    while (i0 < v.t.length - 1 && (ende - zeitOf(v.t[i0])) / 864e5 > tage) i0++;
    var T = v.t.slice(i0), K = v.k.slice(i0), U = (v.u || []).slice(i0);
    // Breite: in der tatsächlichen Pixelbreite zeichnen, damit die Schrift am Handy nicht schrumpft
    var basisW = o.breit ? 960 : 640, cw = el.clientWidth || 0;
    el.__kvCW = cw;
    var W = cw >= 240 && cw < basisW ? Math.round(cw) : basisW, schmal = W < 560;
    var H = o.breit ? 330 : schmal ? Math.round(Math.max(220, W * 0.66)) : 250, ml = 46, mr = 14, mt = 26, mb = 46, FS = 12;   // breit: Steckbrief-Seite
    var t0 = zeitOf(T[0]), t1 = zeitOf(T[T.length - 1]) || t0 + 1, tLetzt = t1;
    var lo = Math.min.apply(null, K), hi = Math.max.apply(null, K);
    // Steckbrief (o.faellig, seit 29.09.2026): liegt die Fälligkeit knapp hinter dem letzten Kurs (höchstens 12 % der Zeitspanne),
    // reicht die Achse bis dorthin, und ein Kreis markiert die Rückzahlung zu 100 %
    var tF = o.faellig && einheit === "%" ? zeitOf(o.faellig) : 0, mitF = tF > t1 && tF - t1 <= 0.12 * (t1 - t0);
    if (mitF) { t1 = tF; lo = Math.min(lo, 100); hi = Math.max(hi, 100); }
    if (hi - lo < hi * 0.004) { lo -= hi * 0.002 + 0.05; hi += hi * 0.002 + 0.05; }
    var st = schritt(hi - lo);
    lo = Math.floor(lo / st) * st; hi = Math.ceil(hi / st) * st;
    if (mitF && hi <= 100) hi = 100 + st;   // Platz über der Rückzahlungslinie für den Kreis
    var X = function (t) { return ml + (t - t0) / Math.max(1, t1 - t0) * (W - ml - mr); };
    var Y = function (k) { return mt + (hi - k) / (hi - lo) * (H - mt - mb); };
    var dec = st < 0.1 ? 2 : st < 1 ? 1 : 0;
    var g = [], label100 = "";
    for (var y = lo; y <= hi + st / 2; y += st) {
      var py = Y(y).toFixed(1);
      g.push('<line x1="' + ml + '" x2="' + (W - mr) + '" y1="' + py + '" y2="' + py + '" stroke="#1A1A19" stroke-opacity="0.09"/>' +
        '<text x="' + (ml - 7) + '" y="' + (+py + 4) + '" text-anchor="end" font-size="' + FS + '" fill="#55544F">' + zahl(y, dec) + '</text>');
    }
    if (einheit === "%" && lo < 100 && hi > 100) {
      var p100 = Y(100).toFixed(1);
      g.push('<line x1="' + ml + '" x2="' + (W - mr) + '" y1="' + p100 + '" y2="' + p100 + '" stroke="#1A1A19" stroke-opacity="0.45" stroke-dasharray="4 4"/>');
      label100 = '<text x="' + (W - mr) + '" y="' + (+p100 - 5) + '" text-anchor="end" font-size="' + FS + '" fill="#55544F" stroke="#FBFAF7" stroke-width="4" stroke-linejoin="round" paint-order="stroke">100\u00a0% = Rückzahlung</text>';
    }
    // x-Achse: Beschriftungen an Kalendergrenzen (Jahresanfang, Monatsanfang) bzw. gleichmäßig bei kurzen Zeiträumen
    var span = (t1 - t0) / 864e5, maxT = schmal ? 4 : 6, ticks = [];
    var iso = function (t) { return new Date(t).toISOString().slice(0, 10); };
    if (span > 1100) {
      var y0 = new Date(t0).getUTCFullYear() + 1, y1 = new Date(t1).getUTCFullYear(), ys1 = Math.max(1, Math.ceil((y1 - y0 + 1) / maxT));
      for (var yy = y0; yy <= y1; yy += ys1) ticks.push([Date.UTC(yy, 0, 1), String(yy)]);
    } else if (span > 100) {
      var d0 = new Date(t0), m = d0.getUTCFullYear() * 12 + d0.getUTCMonth() + 1, mEnd = new Date(t1).getUTCFullYear() * 12 + new Date(t1).getUTCMonth();
      var ms = Math.max(1, Math.ceil((mEnd - m + 1) / maxT));
      for (; m <= mEnd; m += ms) ticks.push([Date.UTC(Math.floor(m / 12), m % 12, 1), MON[m % 12] + " " + String(Math.floor(m / 12)).slice(2)]);
    } else {
      var nt = Math.min(maxT, T.length);
      for (var j = 0; j < nt; j++) { var tt = t0 + j * (t1 - t0) / Math.max(1, nt - 1), s8 = iso(tt); ticks.push([tt, s8.slice(8, 10) + "." + s8.slice(5, 7) + "."]); }
    }
    ticks.forEach(function (tk) {
      var px = X(tk[0]), anc = px < ml + 24 ? "start" : px > W - mr - 24 ? "end" : "middle";
      g.push('<line x1="' + px.toFixed(1) + '" x2="' + px.toFixed(1) + '" y1="' + (H - mb) + '" y2="' + (H - mb + 4) + '" stroke="#1A1A19" stroke-opacity="0.35"/>' +
        '<text x="' + px.toFixed(1) + '" y="' + (H - mb + 17) + '" text-anchor="' + anc + '" font-size="' + FS + '" fill="#55544F">' + tk[1] + '</text>');
    });
    g.push('<text x="4" y="13" font-size="' + FS + '" font-weight="600" fill="#55544F">' + (einheit === "%" ? "↑ Kurs in %" : "↑ Kurs in €") + '</text>');
    g.push('<text x="' + (W - mr) + '" y="' + (H - 4) + '" text-anchor="end" font-size="' + FS + '" font-weight="600" fill="#55544F">Datum →</text>');
    var xs = T.map(function (t) { return +X(zeitOf(t)).toFixed(1); }), ys = K.map(function (k) { return +Y(k).toFixed(1); });
    var d = xs.map(function (x, i) { return (i ? "L" : "M") + x + " " + ys[i]; }).join("");
    g.push('<path d="' + d + '" fill="none" stroke="#1DA300" stroke-width="2" stroke-linejoin="round" stroke-linecap="round"/>');
    if (mitF) {
      var fx = X(tF).toFixed(1), fy = Y(100).toFixed(1);
      g.push('<line x1="' + xs[xs.length - 1] + '" y1="' + ys[ys.length - 1] + '" x2="' + fx + '" y2="' + fy + '" stroke="#1DA300" stroke-width="2" stroke-dasharray="2 4"/>' +
        '<circle cx="' + fx + '" cy="' + fy + '" r="5" fill="#fff" stroke="#1A1A19" stroke-width="1.5"/>' +
        '<text x="' + fx + '" y="' + (+fy - 11) + '" text-anchor="end" font-size="' + FS + '" fill="#1A1A19" stroke="#FBFAF7" stroke-width="4" stroke-linejoin="round" paint-order="stroke">Fälligkeit ' + datumLang(o.faellig).slice(0, 6) + '</text>');
      label100 = label100.replace('x="' + (W - mr) + '" y="' + (+Y(100).toFixed(1) - 5) + '" text-anchor="end"', 'x="' + (ml + 6) + '" y="' + (+Y(100).toFixed(1) - 5) + '" text-anchor="start"');
    }
    if (label100) g.push(label100);   // über der Linie, mit Hof lesbar
    var mitUmsatz = 0;
    U.forEach(function (u, i) { if (u > 0) { mitUmsatz++; g.push('<circle cx="' + xs[i] + '" cy="' + ys[i] + '" r="2.6" fill="#1A1A19"/>'); } });
    var tips = T.map(function (t, i) {
      return datumLang(t) + ": " + fmtK(K[i]) + (U[i] > 0 ? " · Umsatz " + zahl(U[i], 0) + (o.waehrung ? " " + o.waehrung : "") : "");
    });
    var aria = (o.name ? o.name + ": " : "") + "Kursverlauf " + datumLang(T[0]) + " bis " + datumLang(T[T.length - 1]) +
      ", von " + fmtK(K[0]) + " auf " + fmtK(K[K.length - 1]) + ", Tief " + fmtK(Math.min.apply(null, K)) + ", Hoch " + fmtK(Math.max.apply(null, K));
    var svg = '<svg viewBox="0 0 ' + W + " " + H + '" role="img" aria-label="' + esc(aria) + '">' + g.join("") + "</svg>";
    var knoepfe = wahl.length > 1 ? '<div class="kv-zeit" role="group" aria-label="Zeitraum">' + wahl.map(function (z) {
      return '<button type="button" class="kv-btn" aria-pressed="' + (z[0] === aktiv) + '" data-z="' + z[0] + '">' + z[0] + "</button>";
    }).join("") + "</div>" : "";
    var ver = (K[K.length - 1] / K[0] - 1) * 100;
    if (Math.abs(ver) < 0.05) ver = 0;   // gerundet unverändert: ohne Vorzeichen und ohne Farbe
    // o.neutral (Steckbrief, seit 29.09.2026): Veränderung nur mit Vorzeichen, ohne Signalfarbe.
    // o.kupon (Kupon in % p. a.): zusätzlich „inkl. Kupons“ = (Kursänderung + Kupon × Tage/365) / Anfangskurs, ohne Wiederanlage
    var cls = function (x) { return o.neutral ? "null" : x > 0 ? "plus" : x < 0 ? "minus" : "null"; };
    var inkl = "";
    if (typeof o.kupon === "number" && einheit === "%") {
      var gs = (K[K.length - 1] - K[0] + o.kupon * (tLetzt - zeitOf(T[0])) / 864e5 / 365) / K[0] * 100;
      if (Math.abs(gs) < 0.05) gs = 0;
      inkl = ' · inkl. Kupons <span class="kv-ver ' + cls(gs) + '">' + (gs > 0 ? "+" : "") + zahl(gs, 1) + "\u00a0%</span>";
    }
    var titel = o.kopf === "zeitraum" ? datumLang(T[0]) + " bis " + datumLang(T[T.length - 1]) : "Kursverlauf seit " + datumLang(T[0]);   // Steckbrief: Überschrift steht schon über dem Chart
    el.innerHTML = '<div class="kv-kopf"><span class="kv-titel">' + titel +
      ' <span class="kv-ver ' + cls(ver) + '">' + (ver > 0 ? "+" : "") + zahl(ver, 1) + "\u00a0%</span>" + inkl + (o.neutral && inkl ? ' <span class="ber">berechnet</span>' : "") + "</span>" + knoepfe + "</div>" +
      hoverWrap(svg, [{ x: xs, y: ys, tips: tips }]) +
      (mitUmsatz || inkl || mitF ? '<p class="kv-legende">' + (mitUmsatz ? '<span class="kv-punkt" aria-hidden="true"></span>Tag mit Umsatz; die Linie verbindet die täglichen Schlusskurse.' : "") +
        (mitF ? " Kreis: Fälligkeit zum Rückzahlungskurs 100\u00a0%." : "") +
        (inkl ? " „Inkl. Kupons“: Kursänderung plus Kupon × Tage ÷ 365 im Zeitraum, bezogen auf den Anfangskurs, ohne Wiederanlage." : "") + "</p>" : "");
    el.onclick = function (e) {
      var b = e.target.closest ? e.target.closest(".kv-btn") : null;
      if (!b) return;
      el.__kvZeitraum = b.getAttribute("data-z");
      kursChart(el, v, o);
      var nb = el.querySelector('.kv-btn[data-z="' + el.__kvZeitraum + '"]');
      if (nb) nb.focus();
    };
  }

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
  var RATE_COLORS = {
    valuation: ["#14543F", "#1F7A5E", "#8A6A2A", "#B84A22", "#993C1D"],
    level: ["#1D5FA0", "#3E7CB8", "#6B6A64", "#3E7CB8", "#1D5FA0"]
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

  return { esc: esc, minus: minus, restlaufzeit: restlaufzeit, kuendigung: kuendigung, kuendigungFeld: kuendigungFeld, load: load, navInit: navInit, hoverWrap: hoverWrap,
    percentile: percentile, stats: stats, rate: rate, pctText: pctText, ratePill: ratePill,
    teil: teil, verlauf: verlauf, kursChart: kursChart };
})();
