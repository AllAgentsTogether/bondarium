/* pdf.js – kleiner PDF-Schreiber im Browser (seit 30.09.2026), für den Depot-Auszug auf konto.html („Depot teilen“).
   Keine fremde Bibliothek: Die Website lädt nichts von fremden Servern, und für eine Tabelle mit Text, Linien und
   Links reicht ein PDF mit den Standardschriften Helvetica und Helvetica-Bold (jedes PDF-Programm bringt sie mit).
   Zeichen: Windows-1252 (WinAnsi) – deutsche Umlaute, ß, €, Gedankenstrich, „Anführungszeichen“. Andere Zeichen werden
   auf ihren Grundbuchstaben zurückgeführt (İ → I, Ş → S), sonst „?“.

   Laden nach site.js:  <script src="pdf.js"></script>

   API (window.MC.pdf()) – Maße in Punkt (1/72 Zoll), Ursprung oben links, y wächst nach unten:
     const P = MC.pdf();               A4 hochkant: P.B (Breite) × P.H (Höhe)
     P.seite()                         neue Seite anhängen und darauf zeichnen; gibt ihre Nummer (ab 0) zurück
     P.auf(n)                          auf Seite n weiterzeichnen (z. B. für „Seite 1 von 3“ zum Schluss)
     P.anzahl()                        Zahl der Seiten
     P.text(x, y, s, o)                Text, y = Grundlinie. o: { gr: Größe (10), fett, farbe: [r, g, b] 0–1, rechts: x ist
                                       der rechte Rand, max: Breite – längerer Text wird mit „…“ gekürzt }
     P.rechteck(x, y, b, h, farbe)     gefülltes Rechteck
     P.linie(x1, y1, x2, y2, farbe, staerke)
     P.link(x, y, b, h, url)           anklickbare Fläche (y = Oberkante)
     P.weite(s, gr, fett)              Breite eines Texts
     P.kuerzen(s, max, gr, fett)       Text auf höchstens max Breite, sonst mit „…“
     P.umbrechen(s, max, gr, fett)     Text in Zeilen von höchstens max Breite → [Zeile, …]
     P.blob(titel)                     fertiges PDF als Blob (application/pdf) */
(function (MC) {
  "use strict";
  MC = window.MC = MC || {};

  // Zeichenbreiten (Tausendstel der Schriftgröße) für die Codes 32–255 in WinAnsi, aus den Adobe-Metriken (AFM) der
  // Standardschriften. „556*10“ = zehnmal 556.
  function breiten(s) {
    var aus = [];
    s.split(" ").forEach(function (t) { var m = t.split("*"), n = m[1] ? +m[1] : 1; for (var i = 0; i < n; i++) aus.push(+m[0]); });
    return aus;
  }
  var W = {
    F1: breiten("278 278 355 556 556 889 667 191 333 333 389 584 278 333 278 278 556*10 278 278 584 584 584 556 1015 " +
      "667 667 722 722 667 611 778 722 278 500 667 556 833 722 778 667 778 722 667 611 722 667 944 667 667 611 278 278 278 469 556 333 " +
      "556 556 500 556 556 278 556 556 222 222 500 222 833 556 556 556 556 333 500 278 556 500 722 500 500 500 334 260 334 584 350 " +
      "556 350 222 556 333 1000 556 556 333 1000 667 333 1000 350 611 350 350 222 222 333 333 350 556 1000 333 1000 500 333 944 350 500 667 " +
      "278 333 556 556 556 556 260 556 333 737 370 556 584 333 737 333 400 584 333 333 333 556 537 278 333 333 365 556 834 834 834 611 " +
      "667*6 1000 722 667*4 278*4 722 722 778*5 584 778 722*4 667 667 611 556*6 889 500 556*4 278*4 556 556 556*5 584 611 556*4 500 556 500"),
    F2: breiten("278 333 474 556 556 889 722 238 333 333 389 584 278 333 278 278 556*10 333 333 584 584 584 611 975 " +
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
  function weite(s, gr, fett) {
    var w = W[fett ? "F2" : "F1"], sum = 0;
    codes(s).forEach(function (c) { sum += w[c - 32] || 556; });
    return sum * (gr || 10) / 1000;
  }
  function kuerzen(s, max, gr, fett) {
    s = String(s == null ? "" : s);
    if (!max || weite(s, gr, fett) <= max) return s;
    var z = Array.from(s);
    while (z.length && weite(z.join("") + "…", gr, fett) > max) z.pop();
    return z.join("").replace(/[\s,.;:–-]+$/, "") + "…";
  }
  function umbrechen(s, max, gr, fett) {
    var zeilen = [], zeile = "";
    String(s).split(/\s+/).forEach(function (wort) {
      var neu = zeile ? zeile + " " + wort : wort;
      if (zeile && weite(neu, gr, fett) > max) { zeilen.push(zeile); zeile = wort; } else zeile = neu;
    });
    if (zeile) zeilen.push(zeile);
    return zeilen;
  }
  function zahl(v) { return (Math.round(v * 100) / 100).toString(); }
  function farbe(f, op) { return zahl(f[0]) + " " + zahl(f[1]) + " " + zahl(f[2]) + " " + op; }
  // Text als PDF-Zeichenkette: WinAnsi-Bytes, Klammern und Rückstrich maskiert
  function pdfText(s) {
    return "(" + codes(s).map(function (c) { var ch = String.fromCharCode(c); return c === 40 || c === 41 || c === 92 ? "\\" + ch : ch; }).join("") + ")";
  }

  MC.pdf = function () {
    var B = 595.28, H = 841.89, seiten = [], akt = null;
    function y(v) { return zahl(H - v); }
    var P = {
      B: B, H: H,
      seite: function () { akt = { inhalt: [], links: [] }; seiten.push(akt); return seiten.length - 1; },
      auf: function (n) { akt = seiten[n]; },
      anzahl: function () { return seiten.length; },
      weite: weite, kuerzen: kuerzen, umbrechen: umbrechen,
      text: function (x, yy, s, o) {
        o = o || {};
        var gr = o.gr || 10, t = o.max ? kuerzen(s, o.max, gr, o.fett) : String(s == null ? "" : s);
        if (o.rechts) x -= weite(t, gr, o.fett);
        akt.inhalt.push("BT /" + (o.fett ? "F2" : "F1") + " " + zahl(gr) + " Tf " + farbe(o.farbe || [0.1, 0.1, 0.098], "rg") +
          " " + zahl(x) + " " + y(yy) + " Td " + pdfText(t) + " Tj ET");
      },
      rechteck: function (x, yy, b, h, f) { akt.inhalt.push(farbe(f, "rg") + " " + zahl(x) + " " + y(yy + h) + " " + zahl(b) + " " + zahl(h) + " re f"); },
      linie: function (x1, y1, x2, y2, f, st) {
        akt.inhalt.push(farbe(f || [0.8, 0.8, 0.78], "RG") + " " + zahl(st || 0.5) + " w " + zahl(x1) + " " + y(y1) + " m " + zahl(x2) + " " + y(y2) + " l S");
      },
      link: function (x, yy, b, h, url) { akt.links.push([x, yy, b, h, url]); },
      blob: function (titel) {
        // Objekte: 1 Katalog, 2 Seitenbaum, 3/4 Schriften, 5 Dokumentinfo, danach je Seite: Seite, Inhalt, Links
        var obj = [], kids = [];
        obj[3] = "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>";
        obj[4] = "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>";
        var d = new Date(), p2 = function (n) { return (n < 10 ? "0" : "") + n; };
        obj[5] = "<< /Title " + pdfText(titel || "Bondarium") + " /Producer (Bondarium) /CreationDate (D:" + d.getFullYear() + p2(d.getMonth() + 1) +
          p2(d.getDate()) + p2(d.getHours()) + p2(d.getMinutes()) + p2(d.getSeconds()) + ") >>";
        var n = 6;
        seiten.forEach(function (s) {
          var seite = n++, inhalt = n++, annots = [];
          s.links.forEach(function (l) {
            annots.push(n);
            obj[n++] = "<< /Type /Annot /Subtype /Link /Rect [" + zahl(l[0]) + " " + y(l[1] + l[3]) + " " + zahl(l[0] + l[2]) + " " + y(l[1]) +
              "] /Border [0 0 0] /A << /S /URI /URI " + pdfText(l[4]) + " >> >>";
          });
          var strom = s.inhalt.join("\n");
          obj[inhalt] = "<< /Length " + strom.length + " >>\nstream\n" + strom + "\nendstream";
          obj[seite] = "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 " + zahl(B) + " " + zahl(H) + "] /Resources << /Font << /F1 3 0 R /F2 4 0 R >> >> /Contents " +
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
        out += "trailer\n<< /Size " + n + " /Root 1 0 R /Info 5 0 R >>\nstartxref\n" + xref + "\n%%EOF\n";
        var bytes = new Uint8Array(out.length);
        for (i = 0; i < out.length; i++) bytes[i] = out.charCodeAt(i) & 255;
        return new Blob([bytes], { type: "application/pdf" });
      }
    };
    return P;
  };
})(window.MC);
