/* Duration zum Schieben (duration.html#schieben, seit 02.10.2026).
   Anleihe mit jährlichem Kupon und glatter Restlaufzeit; Kurs = Barwert aller Zahlungen zur eingestellten Rendite.
   Modifizierte Duration = Macaulay-Duration ÷ (1 + Rendite). Das Schaubild zeigt für Zinsänderungen von −3 bis +3
   Prozentpunkten die exakte Kursänderung (Kurve) und die Gerade der Duration (Faustformel −mod. Duration × Zinsänderung);
   das Dreieck an der Geraden macht den Hebel sichtbar. Achsen fest (±3 Pkt., ±40 %), damit lange und kurze Laufzeiten
   vergleichbar bleiben – was darüber hinausgeht, wird am Rand mit Pfeil angezeigt. Gezeichnet in echten Pixeln
   (viewBox = Breite des Kastens), damit die Schrift am Handy nicht schrumpft. */
(function () {
  "use strict";
  var $ = function (id) { return document.getElementById(id); };
  var svg = $("dh-svg");
  if (!svg) return;
  var R = { jahre: $("dh-jahre"), kupon: $("dh-kupon"), rendite: $("dh-rendite"), delta: $("dh-delta") };
  var box = svg.parentNode;
  var NS = "http://www.w3.org/2000/svg";
  var DMAX = 3, YMAX = 40, YSTEP = 10;            // x: Zinsänderung in Pkt., y: Kursänderung in %
  var ML = 48, MR = 14, MT = 12, MB = 30, DAUMEN = 24;   // Ränder des Zeichenfelds; DAUMEN = Breite des Reglerknopfs (CSS)
  var FARBE = { gruen: "#157C00", orange: "#CF7430", orangeDunkel: "#A2561C", tinte: "#1A1A19", grau: "#55544F" };
  var NB = " ", MINUS = "−";

  function fmt(v, d) {
    var s = Math.abs(v).toLocaleString("de-DE", { minimumFractionDigits: d, maximumFractionDigits: d });
    return (v < 0 && Number(s.replace(/\./g, "").replace(",", ".")) !== 0 ? MINUS : "") + s;
  }
  // mit Vorzeichen, „0“ ohne
  function sg(v, d) {
    var s = fmt(v, d);
    return (v > 0 && Number(s.replace(/\./g, "").replace(",", ".")) !== 0 ? "+" : "") + s;
  }
  function wert(r) { return Number(r.value); }

  // Kurs in % des Nennwerts und Macaulay-Duration in Jahren
  function rechne(n, c, y) {
    var f = 1 / (1 + y), df = 1, p = 0, w = 0;
    for (var t = 1; t <= n; t++) {
      df *= f;
      var cf = c + (t === n ? 100 : 0);
      p += cf * df;
      w += t * cf * df;
    }
    return { kurs: p, mac: w / p };
  }

  function el(name, attr, text) {
    var e = document.createElementNS(NS, name);
    for (var k in attr) e.setAttribute(k, attr[k]);
    if (text != null) e.textContent = text;
    return e;
  }

  // Füllung der Reglerspur: von Anteil a bis b (0–1) des Knopfwegs, in Farbe f (CSS-Variablen in duration.html)
  function spur(r, a, b, f) {
    r.style.setProperty("--a", a);
    r.style.setProperty("--b", b);
    if (f) r.style.setProperty("--f", f);
  }
  function anteil(r) { return (wert(r) - Number(r.min)) / (Number(r.max) - Number(r.min)); }

  var live = $("dh-live"), liveT = null;

  function zeichne(ansage) {
    var n = wert(R.jahre), c = wert(R.kupon), y = wert(R.rendite) / 100, d = wert(R.delta);
    var heute = rechne(n, c, y);
    var md = heute.mac / (1 + y);
    var pct = function (dd) { return (rechne(n, c, y + dd / 100).kurs / heute.kurs - 1) * 100; };
    var echt = pct(d), gerade = -md * d;
    var kursNeu = heute.kurs * (1 + echt / 100);

    // ----- Regler-Beschriftungen -----
    $("dh-jahre-o").textContent = n + (n === 1 ? " Jahr" : " Jahre");
    R.jahre.setAttribute("aria-valuetext", n + (n === 1 ? " Jahr" : " Jahre"));
    $("dh-kupon-o").textContent = fmt(c, 2) + NB + "% pro Jahr";
    R.kupon.setAttribute("aria-valuetext", fmt(c, 2) + " Prozent pro Jahr");
    $("dh-rendite-o").textContent = fmt(y * 100, 2) + NB + "%";
    R.rendite.setAttribute("aria-valuetext", fmt(y * 100, 2) + " Prozent");
    var dTxt = sg(d, 2) + NB + "Pkt.";
    $("dh-delta-o").textContent = dTxt;
    R.delta.setAttribute("aria-valuetext", sg(d, 2) + " Prozentpunkte");
    [R.jahre, R.kupon, R.rendite].forEach(function (r) { spur(r, 0, anteil(r)); });
    var mitte = 0.5, pos = anteil(R.delta);
    spur(R.delta, Math.min(mitte, pos), Math.max(mitte, pos), d > 0 ? FARBE.orange : FARBE.gruen);

    $("dh-kurs0").textContent = fmt(heute.kurs, 2);
    $("dh-mac").textContent = fmt(heute.mac, 1);

    // ----- Zahlen über dem Schaubild -----
    $("dh-md").textContent = fmt(md, 1);
    $("dh-md-f").textContent = "Kurs " + MINUS + fmt(md, 1) + NB + "% je Prozentpunkt mehr Zinsniveau";
    $("dh-erg-l").textContent = "Kursänderung bei " + dTxt;
    var erg = $("dh-erg");
    erg.textContent = (Math.abs(echt) < 0.05 ? "0,0" : sg(echt, 1)) + NB + "%";
    erg.className = Math.abs(echt) < 0.05 ? "" : (echt < 0 ? "ab" : "auf");
    $("dh-erg-f").textContent = d === 0
      ? "Schieb den Regler unter dem Schaubild."
      : "Kurs " + fmt(kursNeu, 2) + " statt " + fmt(heute.kurs, 2) + " – aus 10.000" + NB + "€ werden " + fmt(10000 * (1 + echt / 100), 0) + NB + "€";

    var satz;
    if (d === 0) satz = "Schieb den Regler: Er hebt oder senkt das allgemeine Zinsniveau. Das Dreieck zeigt dann den Hebel.";
    else if (Math.abs(echt - gerade) < 0.05) satz = "Bei so kleinen Schritten liegen Gerade und echter Kurs fast gleich auf: " + sg(echt, 1) + NB + "%.";
    else if (d > 0) satz = "Die Gerade sagt " + sg(gerade, 1) + NB + "%, der echte Kurs fällt nur um " + fmt(-echt, 1) + NB + "% – die Kurve liegt darüber. Das ist die Konvexität (Karte 4).";
    else satz = "Die Gerade sagt " + sg(gerade, 1) + NB + "%, der echte Kurs steigt sogar um " + fmt(echt, 1) + NB + "% – die Kurve liegt darüber. Das ist die Konvexität (Karte 4).";
    $("dh-satz").textContent = satz;

    // ----- Schaubild -----
    var W = Math.max(280, Math.round(box.clientWidth));
    var H = Math.round(Math.min(380, Math.max(280, W * 0.72)));
    var pw = W - ML - MR, ph = H - MT - MB;
    var X = function (v) { return ML + (v + DMAX) / (2 * DMAX) * pw; };
    var Y = function (v) { return MT + (YMAX - v) / (2 * YMAX) * ph; };
    var klemm = function (v) { return Math.max(-YMAX, Math.min(YMAX, v)); };
    svg.setAttribute("viewBox", "0 0 " + W + " " + H);
    svg.setAttribute("width", W);
    svg.setAttribute("height", H);
    while (svg.lastChild && svg.lastChild.nodeName !== "title") svg.removeChild(svg.lastChild);
    $("dh-svg-t").textContent = "Schaubild: Kursänderung einer Anleihe mit " + n + " Jahren Restlaufzeit, " + fmt(c, 2) +
      " Prozent Kupon und " + fmt(y * 100, 2) + " Prozent Rendite, wenn sich das Zinsniveau um minus 3 bis plus 3 Prozentpunkte ändert. " +
      "Modifizierte Duration " + fmt(md, 1) + ". Bei " + sg(d, 2) + " Prozentpunkten: echter Kurs " + sg(echt, 1) +
      " Prozent, Gerade der Duration " + sg(gerade, 1) + " Prozent.";

    var defs = el("defs");
    var cp = el("clipPath", { id: "dh-clip" });
    cp.appendChild(el("rect", { x: ML, y: MT, width: pw, height: ph }));
    defs.appendChild(cp);
    svg.appendChild(defs);

    // Raster und Achsen
    var g = el("g", { "class": "dh-raster" });
    for (var v = -YMAX; v <= YMAX; v += YSTEP) {
      g.appendChild(el("line", { x1: ML, x2: W - MR, y1: Y(v), y2: Y(v), stroke: FARBE.tinte, "stroke-opacity": v === 0 ? 0.45 : 0.10, "stroke-width": v === 0 ? 1.5 : 1 }));
      g.appendChild(el("text", { x: ML - 8, y: Y(v) + 4, "text-anchor": "end", "class": "dh-tick" }, (v > 0 ? "+" : v < 0 ? MINUS : "") + Math.abs(v) + NB + "%"));
    }
    for (var u = -DMAX; u <= DMAX; u++) {
      if (u === 0) g.appendChild(el("line", { x1: X(0), x2: X(0), y1: MT, y2: MT + ph, stroke: FARBE.tinte, "stroke-opacity": 0.30 }));
      g.appendChild(el("text", { x: X(u), y: MT + ph + 20, "text-anchor": "middle", "class": "dh-tick" }, (u > 0 ? "+" : u < 0 ? MINUS : "") + Math.abs(u)));
    }
    g.appendChild(el("text", { x: W - MR - 6, y: MT + 16, "text-anchor": "end", "class": "dh-ecke" }, "↑ Kursgewinn"));
    g.appendChild(el("text", { x: ML + 6, y: MT + ph - 8, "class": "dh-ecke" }, "↓ Kursverlust"));
    svg.appendChild(g);

    var feld = el("g", { "clip-path": "url(#dh-clip)" });
    // Dreieck: waagerecht die Zinsänderung, senkrecht die Kursänderung laut Gerade = der Hebel
    var farbe = d > 0 ? FARBE.orange : FARBE.gruen;
    if (d !== 0) {
      feld.appendChild(el("path", { d: "M" + X(0) + "," + Y(0) + " L" + X(d) + "," + Y(0) + " L" + X(d) + "," + Y(klemm(gerade)) + " Z", fill: farbe, "fill-opacity": d > 0 ? 0.16 : 0.12 }));
      feld.appendChild(el("line", { x1: X(d), x2: X(d), y1: Y(0), y2: Y(klemm(gerade)), stroke: farbe, "stroke-width": 2.5 }));
    }
    // Gerade der Duration
    feld.appendChild(el("line", { x1: X(-DMAX), y1: Y(md * DMAX), x2: X(DMAX), y2: Y(-md * DMAX), stroke: FARBE.tinte, "stroke-width": 2, "stroke-dasharray": "7 5" }));
    // echter Kurs
    var pfad = "";
    for (var i = 0; i <= 120; i++) {
      var dd = -DMAX + i * (2 * DMAX / 120);
      var yy = Math.max(-YMAX - 40, Math.min(YMAX + 40, pct(dd)));
      pfad += (i ? " L" : "M") + X(dd).toFixed(1) + "," + Y(yy).toFixed(1);
    }
    feld.appendChild(el("path", { d: pfad, fill: "none", stroke: FARBE.gruen, "stroke-width": 3, "stroke-linecap": "round", "stroke-linejoin": "round" }));
    svg.appendChild(feld);

    // heute: Kupon-Punkt im Nullpunkt
    // Eine fallende Kurve durch einen Punkt lässt rechts oberhalb und links unterhalb des Punkts immer Platz:
    // „heute“ steht rechts oberhalb des Nullpunkts, die Werte links unterhalb des verschobenen Punkts
    svg.appendChild(el("text", { x: X(0) + 10, y: Y(0) - 10, "class": "dh-ecke dh-heute" }, "heute"));
    if (d !== 0) {
      var yE = Y(klemm(echt)), yG = Y(klemm(gerade));
      svg.appendChild(el("line", { x1: X(d), x2: X(d), y1: Y(0), y2: yE, stroke: FARBE.tinte, "stroke-opacity": 0.35, "stroke-dasharray": "2 3" }));
      svg.appendChild(el("circle", { cx: X(d), cy: yG, r: 4.5, fill: "#fff", stroke: FARBE.tinte, "stroke-width": 2 }));
      svg.appendChild(el("circle", { cx: X(d), cy: yE, r: 6, fill: d > 0 ? FARBE.orangeDunkel : FARBE.gruen, stroke: "#fff", "stroke-width": 2 }));
      // Beschriftung links unterhalb (die Gerade liegt immer unter der Kurve); fehlt dort Platz, rechts oberhalb.
      // Liegt ein Punkt außerhalb des Felds, stehen die Werte in der freien Ecke (Gewinn oben rechts, Verlust unten links).
      var pfeil = function (v) { return v > YMAX ? "↑ " : v < -YMAX ? "↓ " : ""; };
      var tx, anker, y1;
      if (Math.abs(echt) > YMAX || Math.abs(gerade) > YMAX) {
        if (d < 0) { tx = W - MR - 6; anker = "end"; y1 = MT + 38; }
        else { tx = ML + 6; anker = "start"; y1 = MT + ph - 45; }
      } else if (X(d) - 125 > ML && yG + 38 < MT + ph) {
        tx = X(d) - 10; anker = "end"; y1 = yG + 21;
      } else {
        tx = X(d) + 10; anker = "start"; y1 = Math.max(MT + 30, yE - 26);
      }
      var y2 = y1 + 17;
      svg.appendChild(el("text", { x: tx, y: y1, "text-anchor": anker, "class": "dh-wert", fill: d > 0 ? FARBE.orangeDunkel : FARBE.gruen }, pfeil(echt) + sg(echt, 1) + NB + "%"));
      svg.appendChild(el("text", { x: tx, y: y2, "text-anchor": anker, "class": "dh-ecke" }, pfeil(gerade) + "Gerade " + sg(gerade, 1) + NB + "%"));
    }
    svg.appendChild(el("circle", { cx: X(0), cy: Y(0), r: 6.5, fill: "#39FF14", stroke: FARBE.tinte, "stroke-width": 2.5 }));

    // Regler unter dem Schaubild genau auf die x-Achse legen: Knopfmitte = Wert
    R.delta.style.marginLeft = (ML - DAUMEN / 2) + "px";
    R.delta.style.width = (pw + DAUMEN) + "px";

    // Ansage für Bildschirmleser, erst wenn der Regler ruht (nicht beim bloßen Neuzeichnen nach Größenänderung)
    if (ansage !== true) return;
    clearTimeout(liveT);
    liveT = setTimeout(function () {
      live.textContent = "Modifizierte Duration " + fmt(md, 1) + ". Bei " + sg(d, 2) + " Prozentpunkten Zinsniveau ändert sich der Kurs um " + sg(echt, 1) + " Prozent.";
    }, 600);
  }

  [R.jahre, R.kupon, R.rendite, R.delta].forEach(function (r) { r.addEventListener("input", function () { zeichne(true); }); });

  // Ziehen direkt im Schaubild setzt die Zinsänderung
  var zieht = false;
  function setzeAus(ev) {
    var rect = svg.getBoundingClientRect();
    var W = rect.width, pw = W - ML - MR;
    var v = ((ev.clientX - rect.left) - ML) / pw * 2 * DMAX - DMAX;
    v = Math.max(-DMAX, Math.min(DMAX, Math.round(v / 0.05) * 0.05));
    R.delta.value = v.toFixed(2);
    zeichne(true);
  }
  svg.addEventListener("pointerdown", function (ev) { zieht = true; svg.setPointerCapture(ev.pointerId); setzeAus(ev); });
  svg.addEventListener("pointermove", function (ev) { if (zieht) setzeAus(ev); });
  ["pointerup", "pointercancel"].forEach(function (t) { svg.addEventListener(t, function () { zieht = false; }); });

  if (window.ResizeObserver) new ResizeObserver(function () { zeichne(); }).observe(box);
  else window.addEventListener("resize", zeichne);
  zeichne();
})();
