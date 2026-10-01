/* chart.js – Kursverlauf-Chart (MC.kursChart) für den Steckbrief anleihe.html und die ETF-Seite anleihen-etf.html.
   Seit 30.09.2026 aus site.js ausgelagert: die übrigen Seiten laden den Code nicht mehr mit.
   Laden NACH site.js:  <script src="site.js"></script><script src="chart.js"></script>
   Braucht aus site.js: MC.zahl, MC.esc, MC.hoverWrap; die Daten liefert MC.verlauf (site.js).

   MC.kursChart(el, v, o) – zeichnet den Verlauf v = MC.verlauf(...) in den Container el.
     o.einheit  "%" (Anleihe, Standard) oder "€" (ETF)
     o.name, o.waehrung  für Beschriftung und Tooltip
     o.breit    breitere Grundfläche (Steckbrief)
     o.kopf     "zeitraum": Überschrift „TT.MM.JJJJ bis TT.MM.JJJJ“ statt „Kursverlauf seit …“
     o.neutral  Veränderung ohne Signalfarbe
     o.kupon    Kupon in % p. a. → zusätzlich „inkl. Kupons“
     o.faellig  Fälligkeit (ISO) → Rückzahlungskreis, wenn sie knapp hinter dem letzten Kurs liegt
     o.termine  Kupontermine (ISO-Daten) → Punktreihe auf der Zeitachse (seit 30.09.2026, Bildwelt 2.0)
   Zeitraum-Knöpfe erscheinen nur, wenn der Verlauf länger ist als der Zeitraum. */
(function (MC) {
  "use strict";
  if (!MC || !MC.hoverWrap) return;   // site.js fehlt (Netzfehler): Seite zeigt dann „Kursverlauf nicht erreichbar“
  var MON = ["Jan.", "Feb.", "März", "Apr.", "Mai", "Juni", "Juli", "Aug.", "Sep.", "Okt.", "Nov.", "Dez."];
  var zahl = MC.zahl, esc = MC.esc, hoverWrap = MC.hoverWrap;
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
    g.push('<path d="' + d + '" fill="none" stroke="#157C00" stroke-width="2" stroke-linejoin="round" stroke-linecap="round"/>');
    if (mitF) {
      var fx = X(tF).toFixed(1), fy = Y(100).toFixed(1);
      g.push('<line x1="' + xs[xs.length - 1] + '" y1="' + ys[ys.length - 1] + '" x2="' + fx + '" y2="' + fy + '" stroke="#157C00" stroke-width="2" stroke-dasharray="2 4"/>' +
        '<circle cx="' + fx + '" cy="' + fy + '" r="5" fill="#fff" stroke="#1A1A19" stroke-width="1.5"/>' +
        '<text x="' + fx + '" y="' + (+fy - 11) + '" text-anchor="end" font-size="' + FS + '" fill="#1A1A19" stroke="#FBFAF7" stroke-width="4" stroke-linejoin="round" paint-order="stroke">Fälligkeit ' + datumLang(o.faellig).slice(0, 6) + '</text>');
      label100 = label100.replace('x="' + (W - mr) + '" y="' + (+Y(100).toFixed(1) - 5) + '" text-anchor="end"', 'x="' + (ml + 6) + '" y="' + (+Y(100).toFixed(1) - 5) + '" text-anchor="start"');
    }
    if (label100) g.push(label100);   // über der Linie, mit Hof lesbar
    var mitUmsatz = 0;
    U.forEach(function (u, i) { if (u > 0) { mitUmsatz++; g.push('<circle cx="' + xs[i] + '" cy="' + ys[i] + '" r="2.6" fill="#1A1A19"/>'); } });
    // Bildwelt 2.0 (30.09.2026): Kupontermine im gezeigten Zeitraum als Punktreihe auf der Zeitachse (o.termine, ISO-Daten),
    // aktueller Kurs als Kupon-Punkt (Neon mit Tinten-Rand)
    var mitTerminen = 0;
    (o.termine || []).forEach(function (d) {
      var t = zeitOf(d);
      if (t < t0 || t > tLetzt) return;
      mitTerminen++;
      g.push('<circle cx="' + X(t).toFixed(1) + '" cy="' + (H - mb) + '" r="3.2" fill="#157C00" stroke="#FBFAF7" stroke-width="1.5"><title>Zinstermin ' + datumLang(d) + '</title></circle>');
    });
    g.push('<circle cx="' + xs[xs.length - 1] + '" cy="' + ys[ys.length - 1] + '" r="5" fill="#39FF14" stroke="#1A1A19" stroke-width="1.5"/>');
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
      inkl = ' · inkl. Zinsen <span class="kv-ver ' + cls(gs) + '">' + (gs > 0 ? "+" : "") + zahl(gs, 1) + "\u00a0%</span>";
    }
    var titel = o.kopf === "zeitraum" ? datumLang(T[0]) + " bis " + datumLang(T[T.length - 1]) : "Kursverlauf seit " + datumLang(T[0]);   // Steckbrief: Überschrift steht schon über dem Chart
    el.innerHTML = '<div class="kv-kopf"><span class="kv-titel">' + titel +
      ' <span class="kv-ver ' + cls(ver) + '">' + (ver > 0 ? "+" : "") + zahl(ver, 1) + "\u00a0%</span>" + inkl + (o.neutral && inkl ? ' <span class="ber">berechnet</span>' : "") + "</span>" + knoepfe + "</div>" +
      hoverWrap(svg, [{ x: xs, y: ys, tips: tips }]) +
      (mitUmsatz || inkl || mitF || mitTerminen ? '<p class="kv-legende">' + (mitUmsatz ? '<span class="kv-punkt" aria-hidden="true"></span>Tag mit Umsatz; die Linie verbindet die täglichen Schlusskurse.' : "") +
        (mitF ? " Kreis: Fälligkeit, Rückzahlung zum Nennwert (100\u00a0%)." : "") +
        (mitTerminen ? " Grüne Punkte auf der Zeitachse: Zinstermine." : "") +
        (inkl ? " „Inkl. Zinsen“: Kursänderung plus Kupon × Tage ÷ 365 im Zeitraum, bezogen auf den Anfangskurs, ohne Wiederanlage." : "") + "</p>" : "");
    el.onclick = function (e) {
      var b = e.target.closest ? e.target.closest(".kv-btn") : null;
      if (!b) return;
      el.__kvZeitraum = b.getAttribute("data-z");
      kursChart(el, v, o);
      var nb = el.querySelector('.kv-btn[data-z="' + el.__kvZeitraum + '"]');
      if (nb) nb.focus();
    };
  }

  MC.kursChart = kursChart;
})(window.MC);
