/* pdf.js – kleiner PDF-Schreiber im Browser (seit 30.09.2026), für den Depot-Auszug auf konto.html („Depot teilen“).
   Keine fremde Bibliothek: Die Website lädt nichts von fremden Servern. Schrift: Manrope wie auf der Website, eingebettet
   aus pdf-schrift.json (scripts/pdf_schrift.py); fehlt die Datei, nimmt das PDF die Standardschrift Helvetica.
   Zeichen: Windows-1252 (WinAnsi) – deutsche Umlaute, ß, €, Gedankenstrich, „Anführungszeichen“. Andere Zeichen werden
   auf ihren Grundbuchstaben zurückgeführt (İ → I, Ş → S), sonst „?“.

   Laden nach site.js:  <script src="pdf.js"></script>

   API (window.MC.pdf([schrift])) – schrift = Inhalt von pdf-schrift.json oder nichts. Maße in Punkt (1/72 Zoll),
   Ursprung oben links, y wächst nach unten; Farben als [r, g, b] mit Werten 0–1 oder als „#RRGGBB“:
     const P = MC.pdf(schrift);        A4 hochkant: P.B (Breite) × P.H (Höhe)
     P.seite() / P.auf(n) / P.anzahl() neue Seite (gibt ihre Nummer ab 0 zurück) / auf Seite n weiterzeichnen / Seitenzahl
     P.text(x, y, s, o)                Text, y = Grundlinie. o: { gr: Größe (10), schnitt: "r" | "s" | "b" (normal, halbfett,
                                       fett; fett: true = "b"), farbe, sperren: Zeichenabstand in Tausendstel der Größe,
                                       rechts: x ist der rechte Rand, mitte: x ist die Mitte, max: Breite – sonst mit „…“ gekürzt }
     P.rechteck(x, y, b, h, farbe[, radius[, rand[, staerke]]])   gefüllt; mit radius runde Ecken, mit rand zusätzlich Kontur
     P.kreis(x, y, r, farbe)           gefüllter Kreis um (x, y)
     P.linie(x1, y1, x2, y2, farbe, staerke[, rund])
     P.svg(d, x, y, massstab, farbe, o)   SVG-Pfad (M L H V Q C Z, absolut) als Fläche; (x, y) = Lage des SVG-Ursprungs
                                       o: { strich: Linienbreite im SVG-Maß → Kontur mit runden Enden statt Fläche }
     P.link(x, y, b, h, url)           anklickbare Fläche (y = Oberkante)
     P.weite(s, gr, schnitt)           Breite eines Texts; P.kuerzen(s, max, gr, schnitt), P.umbrechen(s, max, gr, schnitt)
     P.blob(titel)                     fertiges PDF als Blob (application/pdf) */
(function (MC) {
  "use strict";
  MC = window.MC = MC || {};

  // Helvetica (Rückfall ohne pdf-schrift.json): Zeichenbreiten für die Codes 32–255 in WinAnsi aus den Adobe-Metriken (AFM).
  // „556*10“ = zehnmal 556.
  function breiten(s) {
    var aus = [];
    s.split(" ").forEach(function (t) { var m = t.split("*"), n = m[1] ? +m[1] : 1; for (var i = 0; i < n; i++) aus.push(+m[0]); });
    return aus;
  }
  var HELV = {
    r: breiten("278 278 355 556 556 889 667 191 333 333 389 584 278 333 278 278 556*10 278 278 584 584 584 556 1015 " +
      "667 667 722 722 667 611 778 722 278 500 667 556 833 722 778 667 778 722 667 611 722 667 944 667 667 611 278 278 278 469 556 333 " +
      "556 556 500 556 556 278 556 556 222 222 500 222 833 556 556 556 556 333 500 278 556 500 722 500 500 500 334 260 334 584 350 " +
      "556 350 222 556 333 1000 556 556 333 1000 667 333 1000 350 611 350 350 222 222 333 333 350 556 1000 333 1000 500 333 944 350 500 667 " +
      "278 333 556 556 556 556 260 556 333 737 370 556 584 333 737 333 400 584 333 333 333 556 537 278 333 333 365 556 834 834 834 611 " +
      "667*6 1000 722 667*4 278*4 722 722 778*5 584 778 722*4 667 667 611 556*6 889 500 556*4 278*4 556 556 556*5 584 611 556*4 500 556 500"),
    b: breiten("278 333 474 556 556 889 722 238 333 333 389 584 278 333 278 278 556*10 333 333 584 584 584 611 975 " +
      "722 722 722 722 667 611 778 722 278 556 722 611 833 722 778 667 778 722 667 611 722 667 944 667 667 611 333 278 333 584 556 333 " +
      "556 611 556 611 556 333 611 611 278 278 556 278 889 611 611 611 611 389 556 333 611 556 778 556 556 500 389 280 389 584 350 " +
      "556 350 278 556 500 1000 556 556 333 1000 667 333 1000 350 611 350 350 278 278 500 500 350 556 1000 333 1000 556 333 944 350 500 667 " +
      "278 333 556 556 556 556 280 556 333 737 370 556 584 333 737 333 400 584 333 333 333 611 556 278 333 333 365 556 834 834 834 611 " +
      "722*6 1000 722 667*4 278*4 722 722 778*5 584 778 722*4 667 667 611 556*6 889 556 556*4 278*4 611 611 611*5 584 611 611*4 556 611 556")
  };
  // Unicode → WinAnsi für die Codes 0x80–0x9F
  var WIN = { 8364: 128, 8218: 130, 402: 131, 8222: 132, 8230: 133, 8224: 134, 8225: 135, 710: 136, 8240: 137, 352: 138, 8249: 139,
    338: 140, 381: 142, 8216: 145, 8217: 146, 8220: 147, 8221: 148, 8226: 149, 8211: 150, 8212: 151, 732: 152, 8482: 153, 353: 154,
    8250: 155, 339: 156, 382: 158, 376: 159, 8722: 45 /* echtes Minus → Bindestrich */ };
  function code(ch) {
    var c = ch.charCodeAt(0);
    if ((c >= 32 && c < 127) || (c >= 160 && c <= 255)) return c;
    if (WIN[c]) return WIN[c];
    var z = ch.normalize ? ch.normalize("NFKD").charAt(0) : "";   // İ → I, Ş → S, ő → o
    return z && z !== ch && z.charCodeAt(0) >= 32 && z.charCodeAt(0) < 127 ? z.charCodeAt(0) : 63;
  }
  function codes(s) { return Array.from(String(s == null ? "" : s)).map(code); }
  function zahl(v) { return (Math.round(v * 100) / 100).toString(); }
  function rgb(f) {
    if (typeof f === "string") { var n = parseInt(f.slice(1), 16); return [(n >> 16 & 255) / 255, (n >> 8 & 255) / 255, (n & 255) / 255]; }
    return f;
  }
  function farbe(f, op) { f = rgb(f); return zahl(f[0]) + " " + zahl(f[1]) + " " + zahl(f[2]) + " " + op; }
  function pdfText(s) {   // WinAnsi-Bytes, Klammern und Rückstrich maskiert
    return "(" + codes(s).map(function (c) { var ch = String.fromCharCode(c); return c === 40 || c === 41 || c === 92 ? "\\" + ch : ch; }).join("") + ")";
  }

  MC.pdf = function (schrift) {
    var B = 595.28, H = 841.89, K = 0.5523, seiten = [], akt = null;
    var eigen = !!(schrift && schrift.r && schrift.b && schrift.s);
    // Schnitt „r“, „s“ oder „b“ (true = fett); ohne Manrope gibt es nur normal und fett – halbfett wird fett
    function norm(sn) { var s = typeof sn === "string" && sn ? sn : (sn ? "b" : "r"); return eigen ? s : (s === "r" ? "r" : "b"); }
    function schnittVon(o) { return norm(o && (o.schnitt || !!o.fett)); }
    function tab(s) { return eigen ? schrift[s].breiten : HELV[s]; }
    function res(s) { return eigen ? { r: "R", s: "S", b: "B" }[s] : (s === "r" ? "F1" : "F2"); }
    function weite(s, gr, sn, sperren) {
      var w = tab(norm(sn)), c = codes(s), sum = 0;
      c.forEach(function (k) { sum += w[k - 32] || 556; });
      return (sum + (sperren || 0) * c.length) * (gr || 10) / 1000;
    }
    function kuerzen(s, max, gr, sn, sperren) {
      s = String(s == null ? "" : s);
      if (!max || weite(s, gr, sn, sperren) <= max) return s;
      var z = Array.from(s);
      while (z.length && weite(z.join("") + "…", gr, sn, sperren) > max) z.pop();
      return z.join("").replace(/[\s,.;:·–-]+$/, "") + "…";
    }
    function umbrechen(s, max, gr, sn) {
      var zeilen = [], zeile = "";
      String(s).split(/\s+/).forEach(function (wort) {
        var neu = zeile ? zeile + " " + wort : wort;
        if (zeile && weite(neu, gr, sn) > max) { zeilen.push(zeile); zeile = wort; } else zeile = neu;
      });
      if (zeile) zeilen.push(zeile);
      return zeilen;
    }
    function y(v) { return zahl(H - v); }
    // Rechteck mit runden Ecken als Pfad (Bézier-Viertelkreise)
    function rundPfad(x, yy, b, h, r) {
      r = Math.min(r, b / 2, h / 2);
      var k = r * K, x2 = x + b, y2 = yy + h;
      return [zahl(x + r) + " " + y(yy) + " m", zahl(x2 - r) + " " + y(yy) + " l",
        zahl(x2 - r + k) + " " + y(yy) + " " + zahl(x2) + " " + y(yy + r - k) + " " + zahl(x2) + " " + y(yy + r) + " c",
        zahl(x2) + " " + y(y2 - r) + " l",
        zahl(x2) + " " + y(y2 - r + k) + " " + zahl(x2 - r + k) + " " + y(y2) + " " + zahl(x2 - r) + " " + y(y2) + " c",
        zahl(x + r) + " " + y(y2) + " l",
        zahl(x + r - k) + " " + y(y2) + " " + zahl(x) + " " + y(y2 - r + k) + " " + zahl(x) + " " + y(y2 - r) + " c",
        zahl(x) + " " + y(yy + r) + " l",
        zahl(x) + " " + y(yy + r - k) + " " + zahl(x + r - k) + " " + y(yy) + " " + zahl(x + r) + " " + y(yy) + " c h"].join(" ");
    }
    // SVG-Pfad (absolute Befehle M L H V Q C Z) → PDF-Pfad im SVG-Maß; Q wird zur kubischen Kurve
    function svgPfad(d) {
      var t = d.match(/[MLHVQCZ]|-?\d*\.?\d+(?:e-?\d+)?/gi) || [], i = 0, out = [], cx = 0, cy = 0, sx = 0, sy = 0, cmd = "";
      function n() { return +t[i++]; }
      while (i < t.length) {
        if (/[A-Za-z]/.test(t[i])) cmd = t[i++];
        switch (cmd) {
          case "M": cx = sx = n(); cy = sy = n(); out.push(zahl(cx) + " " + zahl(cy) + " m"); cmd = "L"; break;
          case "L": cx = n(); cy = n(); out.push(zahl(cx) + " " + zahl(cy) + " l"); break;
          case "H": cx = n(); out.push(zahl(cx) + " " + zahl(cy) + " l"); break;
          case "V": cy = n(); out.push(zahl(cx) + " " + zahl(cy) + " l"); break;
          case "C": { var a = [n(), n(), n(), n(), n(), n()]; out.push(a.map(zahl).join(" ") + " c"); cx = a[4]; cy = a[5]; break; }
          case "Q": {
            var qx = n(), qy = n(), ex = n(), ey = n();
            out.push([cx + 2 / 3 * (qx - cx), cy + 2 / 3 * (qy - cy), ex + 2 / 3 * (qx - ex), ey + 2 / 3 * (qy - ey), ex, ey].map(zahl).join(" ") + " c");
            cx = ex; cy = ey; break;
          }
          case "Z": case "z": out.push("h"); cx = sx; cy = sy; if (i < t.length && !/[A-Za-z]/.test(t[i])) i++; break;
          default: i++;
        }
      }
      return out.join(" ");
    }
    var P = {
      B: B, H: H, weite: weite, kuerzen: kuerzen, umbrechen: umbrechen,
      seite: function () { akt = { inhalt: [], links: [] }; seiten.push(akt); return seiten.length - 1; },
      auf: function (n) { akt = seiten[n]; },
      anzahl: function () { return seiten.length; },
      text: function (x, yy, s, o) {
        o = o || {};
        var gr = o.gr || 10, sn = schnittVon(o), sp = o.sperren || 0;
        var t = o.max ? kuerzen(s, o.max, gr, sn, sp) : String(s == null ? "" : s), w = weite(t, gr, sn, sp);
        if (o.rechts) x -= w; else if (o.mitte) x -= w / 2;
        akt.inhalt.push("BT /" + res(sn) + " " + zahl(gr) + " Tf " + zahl(sp * gr / 1000) + " Tc " + farbe(o.farbe || [0.102, 0.102, 0.098], "rg") +
          " " + zahl(x) + " " + y(yy) + " Td " + pdfText(t) + " Tj ET");
        return w;
      },
      rechteck: function (x, yy, b, h, f, radius, rand, staerke) {
        var pfad = radius ? rundPfad(x, yy, b, h, radius) : zahl(x) + " " + y(yy + h) + " " + zahl(b) + " " + zahl(h) + " re";
        if (f && rand) akt.inhalt.push(farbe(f, "rg") + " " + farbe(rand, "RG") + " " + zahl(staerke || 0.75) + " w " + pfad + " B");
        else if (f) akt.inhalt.push(farbe(f, "rg") + " " + pfad + " f");
        else if (rand) akt.inhalt.push(farbe(rand, "RG") + " " + zahl(staerke || 0.75) + " w " + pfad + " S");
      },
      kreis: function (x, yy, r, f) { P.rechteck(x - r, yy - r, 2 * r, 2 * r, f, r); },
      linie: function (x1, y1, x2, y2, f, st, rund) {
        akt.inhalt.push((rund ? "1 J " : "0 J ") + farbe(f || [0.8, 0.8, 0.78], "RG") + " " + zahl(st || 0.5) + " w " + zahl(x1) + " " + y(y1) + " m " + zahl(x2) + " " + y(y2) + " l S");
      },
      svg: function (d, x, yy, m, f, o) {
        o = o || {};
        // Matrix: SVG (y nach unten) → PDF (y nach oben)
        var fein = function (v) { return (Math.round(v * 1e6) / 1e6).toString(); };   // Maßstab genau – zwei Stellen verzerren kleine Maßstäbe
        var mat = "q " + fein(m) + " 0 0 " + fein(-m) + " " + zahl(x) + " " + y(yy) + " cm ";
        akt.inhalt.push(mat + (o.strich ? "1 J 1 j " + farbe(f, "RG") + " " + zahl(o.strich) + " w " + svgPfad(d) + " S" : farbe(f, "rg") + " " + svgPfad(d) + " f") + " Q");
      },
      link: function (x, yy, b, h, url) { akt.links.push([x, yy, b, h, url]); },
      blob: function (titel) {
        // Objekte: 1 Katalog, 2 Seitenbaum, 3 Dokumentinfo, dann Schriften, dann je Seite: Seite, Inhalt, Links
        var obj = [], kids = [], n = 4, schriften = {};
        var d = new Date(), p2 = function (k) { return (k < 10 ? "0" : "") + k; };
        obj[3] = "<< /Title " + pdfText(titel || "Bondarium") + " /Producer (Bondarium) /CreationDate (D:" + d.getFullYear() + p2(d.getMonth() + 1) +
          p2(d.getDate()) + p2(d.getHours()) + p2(d.getMinutes()) + p2(d.getSeconds()) + ") >>";
        if (eigen) {
          ["r", "s", "b"].forEach(function (s) {
            var f = schrift[s], name = "BNDRM" + s.toUpperCase() + "+" + f.name, datei = n++, besch = n++, font = n++, bin = atob(f.daten);
            obj[datei] = "<< /Length " + bin.length + " /Length1 " + f.laenge + " /Filter /FlateDecode >>\nstream\n" + bin + "\nendstream";
            obj[besch] = "<< /Type /FontDescriptor /FontName /" + name + " /Flags 32 /FontBBox [" + f.box.join(" ") + "] /ItalicAngle 0 /Ascent " +
              f.aufstieg + " /Descent " + f.abstieg + " /CapHeight " + f.versal + " /StemV " + f.stamm + " /FontFile2 " + datei + " 0 R >>";
            obj[font] = "<< /Type /Font /Subtype /TrueType /BaseFont /" + name + " /FirstChar 32 /LastChar 255 /Widths [" + f.breiten.join(" ") +
              "] /Encoding /WinAnsiEncoding /FontDescriptor " + besch + " 0 R >>";
            schriften[res(s)] = font;
          });
        } else {
          obj[n] = "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>"; schriften.F1 = n++;
          obj[n] = "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>"; schriften.F2 = n++;
        }
        var fontRes = "<< " + Object.keys(schriften).map(function (k) { return "/" + k + " " + schriften[k] + " 0 R"; }).join(" ") + " >>";
        seiten.forEach(function (s) {
          var seite = n++, inhalt = n++, annots = [];
          s.links.forEach(function (l) {
            annots.push(n);
            obj[n++] = "<< /Type /Annot /Subtype /Link /Rect [" + zahl(l[0]) + " " + y(l[1] + l[3]) + " " + zahl(l[0] + l[2]) + " " + y(l[1]) +
              "] /Border [0 0 0] /A << /S /URI /URI " + pdfText(l[4]) + " >> >>";
          });
          var strom = s.inhalt.join("\n");
          obj[inhalt] = "<< /Length " + strom.length + " >>\nstream\n" + strom + "\nendstream";
          obj[seite] = "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 " + zahl(B) + " " + zahl(H) + "] /Resources << /Font " + fontRes + " >> /Contents " +
            inhalt + " 0 R" + (annots.length ? " /Annots [" + annots.map(function (a) { return a + " 0 R"; }).join(" ") + "]" : "") + " >>";
          kids.push(seite + " 0 R");
        });
        obj[1] = "<< /Type /Catalog /Pages 2 0 R >>";
        obj[2] = "<< /Type /Pages /Kids [" + kids.join(" ") + "] /Count " + kids.length + " >>";
        // Zusammensetzen; alle Zeichen sind Bytes (0–255), die Länge der Zeichenkette ist also die Byte-Länge
        var out = "%PDF-1.4\n%âãÏÓ\n", lagen = [];
        for (var i = 1; i < n; i++) { lagen[i] = out.length; out += i + " 0 obj\n" + obj[i] + "\nendobj\n"; }
        var xref = out.length;
        out += "xref\n0 " + n + "\n0000000000 65535 f \n";
        for (i = 1; i < n; i++) out += ("0000000000" + lagen[i]).slice(-10) + " 00000 n \n";
        out += "trailer\n<< /Size " + n + " /Root 1 0 R /Info 3 0 R >>\nstartxref\n" + xref + "\n%%EOF\n";
        var bytes = new Uint8Array(out.length);
        for (i = 0; i < out.length; i++) bytes[i] = out.charCodeAt(i) & 255;
        return new Blob([bytes], { type: "application/pdf" });
      }
    };
    return P;
  };
})(window.MC);
