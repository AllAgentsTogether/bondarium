/* filter.js – Filterstandard für Anleihen-Listen (seit 02.10.2026): Grundfilter-Schalter und Filterleiste an einer Stelle.
   Genutzt von der Anleihen-Suche (anleihen-suche.html) und der Merkliste in „Mein Bondarium“ (konto.html) – beide zeigen
   dieselben Filter mit denselben Stufen, Texten und Regeln. Bis 02.10.2026 stand dieser Code in anleihen-suche.html.
   Stile: filter.css. Laden NACH site.js (MC.esc, MC.datum, MC.kuendigung).

   Zeilenformat wie suchindex.json (scripts/suchindex.py):
     r[0] isin · r[1] name · r[2] art · r[3] waehrung · r[4] kupon (Zahl oder "var") · r[5] faellig · r[6] volumen · r[7] stueckelung ·
     r[10] zinsart · r[11] land · r[13] "<Rückzahlungsart><Jahr erster Handelstag>" · r[14] Datenprüfung (Objekt oder 0) ·
     r[22] Bonität laut EZB (1 = Stufen 1 und 2, 3 = Stufe 3, fehlt = nicht auf der Liste)

   Aufruf:
     const F = MC.anleihenFilter({
       box,                 Element, in das Grundfilter und Filterleiste gezeichnet werden
       praefix: "",         Vorsatz für die IDs (zwei Leisten auf einer Seite kämen sich sonst in die Quere)
       art: () => [...],    Namen der Arten (Staat, Öffentlich, Unternehmen)
       ezb: () => "",       Stand der EZB-Liste (ISO-Datum) oder "" = keine Bonitätsangabe verfügbar
       kstand: () => "",    Kursstand (ISO-Datum) für den Hinweis am Renditefilter
       rendite: r => …,     angezeigte Rendite der Zeile oder null (Anzeige-Schutz der Seite)
       befund: r => …,      true = Datenprüfung mit Widerspruch
       bereit: () => …,     true, sobald die Daten geladen sind
       laden: () => Promise Daten bei Bedarf holen (optional – die Suche lädt erst beim ersten Klick)
       onChange: () => …    nach jeder Änderung an Filtern oder Grundfilter
     });
   Rückgabe:
     F.FILTER             die Filter [{ k, i, label, key(r), … }] – i ist die Stelle im Schlüssel-Array einer Zeile
     F.sel                { k: Set gewählter Werte }
     F.solide             Grundfilter an/aus (lesen und setzen)
     F.keys(r)            Schlüssel einer Zeile je Filter (null = nicht einstufbar; Kündigung: auch Array)
     F.solideRegel(r)     true = Zeile erfüllt die sechs Grundregeln
     F.daten(KEYS)        Auswahlfelder aus den Schlüsseln aller Zeilen bauen; gewählte Werte, die es nicht gibt, fallen weg
     F.auswerten(KEYS, SOL, pass)   → { hits: [Zeilenindex …], zahl: [Map je Filter] } – innerhalb eines Filters „oder“, zwischen
                          den Filtern „und“; gezählt wird je Option mit allen ÜBRIGEN Filtern; pass(i) = zusätzlicher Vorfilter
     F.zeigen(zahl)       Zahlen, Häkchen und Knopf-Beschriftungen aktualisieren
     F.aktiv()            Filter mit Auswahl; F.gesetzt() = irgendein Filter, ein Von/Bis-Feld oder der Grundfilter
     F.bereichLesen(k, von, bis), F.bereichTexte(k)   Von/Bis-Felder („rest“ = Fälligkeit, „rendite“) setzen bzw. als Text lesen
                          (für die Adresse); F.keys(r) hängt dafür Fälligkeit und angezeigte Rendite an die Filterschlüssel an
     F.spanneVerkehrt()   Von/Bis-Felder, bei denen Von über Bis liegt (["rest"], ["rendite"] oder []) – beide Felder sind dann
                          als ungültig markiert; die Seite sagt es statt „Keine Anleihe gefunden“
     F.zuruecksetzen()    alles löschen (ohne onChange)
     F.mehr(auf)          „Weitere Filter“ auf- oder zuklappen */
(function (MC) {
  "use strict";
  MC = window.MC = MC || {};
  const esc = s => MC.esc ? MC.esc(s) : String(s).replace(/[&<>"']/g, c => "&#" + c.charCodeAt(0) + ";");
  const fmtDate = iso => iso && MC.datum ? MC.datum(iso) : iso || "–";
  const norm = s => String(s).normalize("NFKD").replace(/[̀-ͯ]/g, "").toLowerCase();
  const NAMEN = (() => { try { return { land: new Intl.DisplayNames(["de"], { type: "region" }), w: new Intl.DisplayNames(["de"], { type: "currency" }) }; } catch (e) { return {}; } })();
  const landName = c => c === "INT" ? "International (supranational)" : ((NAMEN.land && (() => { try { return NAMEN.land.of(c); } catch (e) { return ""; } })()) || c);
  const wName = c => { try { const n = NAMEN.w && NAMEN.w.of(c); return n && n !== c ? `${c} · ${n}` : c; } catch (e) { return c; } };
  // „Heute“ ist der Berliner Kalendertag (MC.heuteBerlin, site.js; seit 09.10.2026, Technik-Test 08.10.2026 T-51) – vorher Uhrzeit des
  // Geräts: zwischen 0 und 2 Uhr und in fernen Zeitzonen eine andere Restlaufzeit als im Steckbrief
  const HEUTE = MC.heuteBerlin ? MC.heuteBerlin().getTime() : Date.now();
  const jahre = iso => iso ? (new Date(iso + "T12:00:00Z").getTime() - HEUTE) / (365.25 * 86400000) : Infinity;
  const bucket = (x, grenzen) => { for (const [g, k] of grenzen) if (x <= g) return k; return null; };
  // Kündigung je Anleihe (Regel in site.js); ohne site.js null = nicht einstufbar
  const kueVon = r => MC.kuendigung ? MC.kuendigung(r[1], typeof r[13] === "string" && r[13] ? r[13][0] : "-", r[5], typeof r[13] === "string" ? r[13].slice(1) : "") : null;
  // Schlüssel sind meist ein Wert, beim Filter Kündigung auch ein Array (trifft, wenn einer der Werte gewählt ist)
  const trifft = (sel, v) => Array.isArray(v) ? v.some(x => sel.has(x)) : sel.has(v);
  const zaehle = (m, v) => { if (Array.isArray(v)) { for (const x of v) m.set(x, (m.get(x) || 0) + 1); } else m.set(v, (m.get(v) || 0) + 1); };

  // Von/Bis (seit 03.10.2026, Nutzertest: „Restlaufzeit nur in Stufen, 2–5 Jahre nicht einstellbar“, „Juni–August 2027 muss man
  // selbst suchen“): Fälligkeit als Zeitraum im Feld Restlaufzeit, Rendite als Spanne im Feld Rendite – zusätzlich zu den Stufen.
  const BEREICHE = { rest: { datum: true, label: "Fällig von", ph: ["MM.JJJJ", "MM.JJJJ"], hint: "Monat und Jahr (06.2027), nur das Jahr (2027) oder ein Tag (15.06.2027)." },
    rendite: { datum: false, label: "Rendite von", ph: ["z. B. 3", "z. B. 5"], hint: "In Prozent, z. B. von 3 bis 4,5. Anleihen ohne Rendite fallen dann heraus." } };
  const letzterTag = (j, m) => new Date(Date.UTC(j, m, 0)).getUTCDate();
  // „2027“, „06.2027“, „6/2027“, „15.06.2027“ oder ISO → ISO-Datum; bis = letzter Tag des Jahres bzw. Monats; "" = leer, null = ungültig
  function datumLesen(t, bis) {
    t = String(t == null ? "" : t).trim(); if (!t) return "";
    let m = /^(\d{4})(?:-(\d{1,2})(?:-(\d{1,2}))?)?$/.exec(t), j, mo = null, d = null;
    if (m) { j = +m[1]; if (m[2]) mo = +m[2]; if (m[3]) d = +m[3]; }
    else if ((m = /^(?:(\d{1,2})[./])?(\d{1,2})[./](\d{4})$/.exec(t))) { j = +m[3]; mo = +m[2]; if (m[1]) d = +m[1]; }
    else return null;
    if (j < 1900 || j > 2200 || (mo != null && (mo < 1 || mo > 12))) return null;
    if (mo == null) { mo = bis ? 12 : 1; d = bis ? 31 : 1; }
    else if (d == null) d = bis ? letzterTag(j, mo) : 1;
    else if (d < 1 || d > letzterTag(j, mo)) return null;
    return j + "-" + String(mo).padStart(2, "0") + "-" + String(d).padStart(2, "0");
  }
  function zahlLesen(t) {
    t = String(t == null ? "" : t).trim().replace(/[\s%]/g, "").replace(",", "."); if (!t) return "";
    return /^-?\d+(\.\d+)?$/.test(t) ? +t : null;
  }

  const ZINS = ["fest", "variabel", "Nullkupon"];
  const TXT = {
    clear: "Auswahl löschen", landSuche: "Land suchen …", mehr: "Weitere Filter", weniger: "Weniger Filter", alle: "Alle Filter zurücksetzen",
    hint: {
      rendite: d => `Rendite bis Fälligkeit aus dem Schlusskurs vom ${d} (Börse Frankfurt, Bundeswertpapiere: Bundesbank). Ohne Rendite: variabel oder später variabel verzinste, Stufenzins-, Wandel-, Tilgungs-, unbefristete und inflationsindexierte Anleihen (inflationsindexierte Bundeswertpapiere: Realrendite, mit * gekennzeichnet) sowie Kurse ohne Umsatz mit unplausibler Rendite. Grau mit Fragezeichen: Rendite aus einer Taxe ohne Umsatz, die bei unter einem Jahr Restlaufzeit zu weit über Bund liegt (Staat 2, Öffentlich 1,5, Unternehmen 3 Prozentpunkte) – meist ist die Taxe veraltet.`,
      stk: "Stückelung = kleinster handelbarer Nennwert (zugleich Mindestanlage), in der Währung der Anleihe.",
      pruef: "Jede Anleihe wird gegen den Kurznamen im ESMA-Register (Kupon und Fälligkeit nach ISO 18774) und gegen ihren Namen geprüft. Weicht etwas ab, bleiben die Registerwerte stehen, der Widerspruch steht daneben („Daten?“) und es gibt keine Rendite – die Quelle wird nicht verändert.",
      vol: "Ausgegebener Nennbetrag in der Währung der Anleihe – 100 Mio. Yen sind also weniger als 100 Mio. Euro. Unter 100 Mio. stellt die Börse oft nur kleine Stückzahlen; wer vor der Fälligkeit verkaufen will, braucht Geduld oder nimmt Abschläge in Kauf. Ein Anhaltspunkt für die Handelbarkeit, keine Garantie.",
      land: "Sitz des Konzerns laut LEI-Register.",
      bon: d => `Von uns aus der Liste der notenbankfähigen Sicherheiten der EZB vom ${d} abgelesen: Der Bewertungsabschlag der EZB zeigt, ob eine Anleihe zu den Bonitätsstufen 1 und 2 (AAA bis A−) oder zur Stufe 3 (BBB+ bis BBB−) gehört. Kein Rating, keine Empfehlung. „Keine Angabe“ heißt nur: Die Anleihe steht nicht auf der Liste. <a href="bonitaet.html">Bonität und Ratings erklärt →</a>`,
      kue: 'Abgeleitet aus dem Namen – „2024(27/34)“ heißt kündbar ab 2027 – und dem ESMA-Register. Verbindlich sind die Anleihebedingungen. <a href="kuendbare-anleihen.html">Kündigungsarten erklärt →</a>',
    },
  };
  // Reihenfolge in der Leiste: die sieben wichtigsten immer sichtbar, fünf seltener gebrauchte hinter „Weitere Filter“ (UX 29.09.2026)
  const LEISTE = [["art", "Art"], ["land", "Land"], ["w", "Währung"], ["rest", "Restlaufzeit"], ["rendite", "Rendite"], ["kupon", "Kupon"], ["bon", "Bonität"],
    ["zins", "Zinsart", 1], ["kue", "Kündigung", 1], ["vol", "Volumen", 1], ["stk", "Stückelung", 1], ["pruef", "Datenprüfung", 1]];
  // Grundfilter (bis 01.10.2026 abends „Solide Auswahl“; Nutzerwunsch): sechs Grundregeln als Vorfilter vor allen übrigen Filtern.
  // Eigener Schalter statt gesetzter Filter: 8 Monate und 10.000 sind keine Filterstufen.
  const GRUNDFILTER =
    '<button type="button" class="sol-btn" aria-pressed="false"><span class="sol-sw" aria-hidden="true"></span><span><b>Grundfilter</b> <small>6 Grundregeln für Privatanleger</small></span></button>' +
    '<details class="sol-mehr"><summary>Was heißt das?</summary><ol class="sol-regeln">' +
    "<li><b>Restlaufzeit mindestens 8 Monate</b> <small>– sonst fressen die Kaufkosten den Ertrag</small></li>" +
    "<li><b>Kündigung: keine, Make-Whole oder kurz vor Fälligkeit</b> <small>– die Anleihe läuft so lange wie versprochen</small></li>" +
    "<li><b>Volumen ab 100 Mio.</b> <small>– meist reger Handel, Verkauf vor Fälligkeit eher möglich</small></li>" +
    "<li><b>Stückelung (Mindestanlage) bis 10.000</b> <small>– in der Währung der Anleihe</small></li>" +
    "<li><b>Währung Euro oder US-Dollar</b></li>" +
    "<li><b>Datenprüfung ohne Befund</b> <small>– Kupon und Fälligkeit stimmen mit dem Register überein</small></li></ol>" +
    '<p class="sol-fuss">Grundregeln, keine Empfehlung: Bonität des Emittenten und Anleihebedingungen prüfst du selbst. Alle übrigen Filter wirken zusätzlich.</p></details>';

  MC.anleihenFilter = function (opt) {
    const pre = opt.praefix || "", art = opt.art || (() => ["Staat", "Öffentlich", "Unternehmen"]), ezb = opt.ezb || (() => ""), kstand = opt.kstand || (() => "");
    const rendite = opt.rendite || (() => null), befund = opt.befund || (r => !!(r[14] && typeof r[14] === "object" && Object.keys(r[14]).length));
    const bereit = opt.bereit || (() => true), onChange = opt.onChange || (() => {});

    // ---------- Filter ----------
    // Jeder Filter ordnet einer Anleihe einen Schlüssel zu (oder null = nicht einstufbar; Kündigung: auch zwei).
    const FILTER = [
      { k: "art", opts: () => art().map((t, i) => [String(i), t]), key: r => r[2] == null ? null : String(r[2]) },
      { k: "land", liste: true, key: r => r[11] || null, name: landName, hint: () => TXT.hint.land },
      { k: "w", liste: true, key: r => r[3] || null, name: wName, kurz: c => c },
      { k: "kupon", opts: () => [["a", "bis 1 %"], ["b", "über 1 bis 3 %"], ["c", "über 3 bis 4 %"], ["g", "über 4 bis 5 %"], ["d", "über 5 bis 7 %"], ["e", "über 7 %"], ["v", "variabel"]],
        key: r => r[4] === "var" ? "v" : typeof r[4] === "number" ? bucket(r[4], [[1, "a"], [3, "b"], [4, "c"], [5, "g"], [7, "d"], [Infinity, "e"]]) : null },
      // Bonität laut EZB (seit 02.10.2026, scripts/update_bonitaet.py): Feld 22 – 1 = Bonitätsstufen 1 und 2, 3 = Stufe 3,
      // fehlt = nicht auf der EZB-Liste. Ohne Stand der Liste gibt es die Angabe nicht.
      { k: "bon", opts: () => [["a", "AAA bis A−", "Bonitätsstufen 1 und 2 der EZB"], ["b", "BBB+ bis BBB−", "Bonitätsstufe 3 der EZB"],
          ["k", "keine Angabe", "nicht auf der EZB-Liste – sagt nichts über die Bonität"]],
        key: r => !ezb() ? null : r[22] === 1 ? "a" : r[22] === 3 ? "b" : r[22] == null ? "k" : null, hintHtml: () => TXT.hint.bon(ezb() ? fmtDate(ezb()) : "–") },
      { k: "zins", opts: () => ZINS.map((t, i) => [String(i), t]), key: r => r[10] == null ? null : String(r[10]) },
      { k: "rest", opts: () => [["a", "bis 1 Jahr"], ["b", "1 bis 3 Jahre"], ["c", "3 bis 7 Jahre"], ["d", "7 bis 30 Jahre"], ["e", "über 30 Jahre"], ["u", "unbefristet"]],
        key: r => r[5] ? bucket(Math.max(0, jahre(r[5])), [[1, "a"], [3, "b"], [7, "c"], [30, "d"], [Infinity, "e"]]) : "u" },
      // Kündigung (seit 27.09.2026, erklärt auf kuendbare-anleihen.html): Art des Kündigungsrechts des Emittenten, dazu „a“ =
      // Kündigungsrecht des Anlegers (Put). Eine Anleihe kann zwei Schlüssel haben (z. B. Make-Whole und Put) – daher Array.
      { k: "kue", opts: () => [["n", "nicht kündbar", "feste Laufzeit"], ["m", "Make-Whole", "zum Barwert – meist ohne Nachteil"],
          ["p", "kurz vor Fälligkeit", "höchstens ein Jahr früher – meist ohne Nachteil"], ["t", "ab festem Termin", "zu 100 %, Jahre vor Fälligkeit – beachten"],
          ["e", "unbefristet, mit Kündigungstermin", "läuft weiter, wenn nicht gekündigt"], ["u", "Termin unklar", "laut Register oder Fix-to-Float – Bedingungen prüfen"],
          ["a", "du kannst kündigen (Put)", "ein Vorteil für dich"]],
        kurz: v => ({ n: "nein", m: "Make-Whole", p: "kurz vor Ende", t: "fester Termin", e: "unbefristet", u: "unklar", a: "Put" })[v] || v,
        key: r => { const o = kueVon(r); return o ? (o.put ? [o.k, "a"] : o.k) : null; }, hintHtml: () => TXT.hint.kue },
      { k: "rendite", opts: () => [["a", "unter 1 %"], ["b", "1 bis unter 2 %"], ["c", "2 bis unter 3 %"], ["d", "3 bis unter 4 %"], ["e", "4 % und mehr"]],
        // Stufe nach der angezeigten Rendite – Anzeige-Schutz und auf zwei Stellen gerundet wie in der Liste (seit 09.10.2026, Technik-Test
        // 08.10.2026 T-41: „4,00 %“ stand vorher unter „3 bis unter 4 %“)
        key: r => { const y = rendite(r); if (y == null) return null; const w = Math.round(y * 100) / 100; return w < 1 ? "a" : w < 2 ? "b" : w < 3 ? "c" : w < 4 ? "d" : "e"; },
        hint: () => TXT.hint.rendite(kstand() ? fmtDate(kstand()) : "–") },
      // Volumen (seit 27.09.2026): ausgegebener Nennbetrag in der Währung der Anleihe – Näherung für die Handelbarkeit;
      // eine Grenze genügt: unter 100 Mio. ist an deutschen Börsen selten ein belastbarer Markt, darüber ändert sich bis 1 Mrd. wenig
      { k: "vol", opts: () => [["a", "unter 100 Mio.", "kleine Emission – Verkauf vor Fälligkeit kann dauern"], ["b", "100 Mio. und mehr", "meist reger Handel"]],
        kurz: v => ({ a: "unter 100 Mio.", b: "ab 100 Mio." })[v] || v,
        key: r => typeof r[6] === "number" ? (r[6] < 1e8 ? "a" : "b") : null, hint: () => TXT.hint.vol },
      // Datenprüfung (seit 27.09.2026): Feld pruef aus dem Indexskript – Widersprüche Kurzname/Name gegen Register
      { k: "pruef", opts: () => [["a", "ohne Befund"], ["b", "Widerspruch im Register", "Kupon oder Fälligkeit laut Kurzname oder Name anders"]],
        kurz: v => ({ a: "ohne Befund", b: "Widerspruch" })[v] || v,
        key: r => befund(r) ? "b" : "a", hint: () => TXT.hint.pruef },
      { k: "stk", opts: () => [["a", "bis 1.000"], ["b", "über 1.000 bis unter 100.000"], ["c", "100.000 und mehr"]],
        key: r => typeof r[7] === "number" ? (r[7] <= 1000 ? "a" : r[7] < 100000 ? "b" : "c") : null, hint: () => TXT.hint.stk },
    ];
    const sel = {};
    FILTER.forEach((f, i) => { f.i = i; sel[f.k] = new Set(); f.label = (LEISTE.find(l => l[0] === f.k) || [])[1] || f.k; });
    const aktiv = () => FILTER.filter(f => sel[f.k].size);
    // Von/Bis: von/bis = gelesener Wert ("" = leer), tv/tb = eingegebener Text. Hinter den Filterschlüsseln einer Zeile stehen
    // Fälligkeit (ISO) und angezeigte Rendite (keys(r) unten).
    const bereich = { rest: { von: "", bis: "", tv: "", tb: "" }, rendite: { von: "", bis: "", tv: "", tb: "" } };
    const bereichAn = k => bereich[k].von !== "" || bereich[k].bis !== "";
    const bereichIrgend = () => Object.keys(bereich).some(bereichAn);
    const NF = FILTER.length;
    function imBereich(ks) {
      const f = bereich.rest, y = bereich.rendite;
      if (f.von !== "" || f.bis !== "") { const d = ks[NF]; if (!d || (f.von !== "" && d < f.von) || (f.bis !== "" && d > f.bis)) return false; }
      if (y.von !== "" || y.bis !== "") {
        const v = ks[NF + 1]; if (typeof v !== "number") return false;
        const w = Math.round(v * 100) / 100;   // wie angezeigt (zwei Stellen)
        if ((y.von !== "" && w < y.von) || (y.bis !== "" && w > y.bis)) return false;
      }
      return true;
    }
    function bereichSetzen(k, w, text) {   // w: "von" | "bis"; ungültig → leer (Feld wird markiert)
      const b = bereich[k], v = BEREICHE[k].datum ? datumLesen(text, w === "bis") : zahlLesen(text);
      b[w === "von" ? "tv" : "tb"] = String(text == null ? "" : text).trim();
      b[w] = v === null ? "" : v;
      return v !== null;
    }
    // Von über Bis (seit 09.10.2026, Technik-Test 08.10.2026 T-91): ergibt immer 0 Treffer – beide Felder als ungültig markieren und
    // den Zustand nach außen geben (F.spanneVerkehrt). Nicht still tauschen: die Eingabe gehört dem Nutzer.
    const verkehrt = k => { const b = bereich[k]; return b.von !== "" && b.bis !== "" && b.von > b.bis; };
    // Feld ungültig: Text, der sich nicht lesen ließ, oder Von über Bis
    const ungueltig = (k, w) => { const b = bereich[k]; return (b[w === "von" ? "tv" : "tb"] !== "" && b[w] === "") || verkehrt(k); };
    function markieren(k) {
      const g = grp(k); if (!g) return;
      g.querySelectorAll(".fber input").forEach(i => { if (ungueltig(k, i.classList.contains("fber-von") ? "von" : "bis")) i.setAttribute("aria-invalid", "true"); else i.removeAttribute("aria-invalid"); });
    }
    function bereichLeeren(k) { Object.assign(bereich[k], { von: "", bis: "", tv: "", tb: "" }); const g = grp(k); if (g) g.querySelectorAll(".fber input").forEach(i => { i.value = ""; i.removeAttribute("aria-invalid"); }); }
    function bereichText(k) {
      const b = bereich[k], e = BEREICHE[k].datum ? "" : "\u00a0%";
      const v = b.von !== "" ? b.tv : "", t = b.bis !== "" ? b.tb : "";
      return v && t ? `${v}–${t}${e}` : v ? `ab ${v}${e}` : t ? `bis ${t}${e}` : "";
    }
    // Grundregeln: Restlaufzeit ab 8 Monaten, Kündigung keine/Make-Whole/kurz vor Fälligkeit, Volumen ab 100 Mio., Stückelung bis
    // 10.000 (Währung der Anleihe), Euro oder US-Dollar, Datenprüfung ohne Befund
    const solideRegel = r => {
      if (!r[5] || jahre(r[5]) < 8 / 12) return false;
      const k = kueVon(r); if (!k || "nmp".indexOf(k.k) < 0) return false;
      return typeof r[6] === "number" && r[6] >= 1e8 && typeof r[7] === "number" && r[7] <= 10000 && (r[3] === "EUR" || r[3] === "USD") && !befund(r);
    };

    // ---------- Markup ----------
    opt.box.innerHTML = `<div class="solide" id="${pre}solide-z">${GRUNDFILTER}</div>` +
      `<div class="filter" id="${pre}filter" role="group" aria-label="Filter">` +
      LEISTE.map(([k, label, neben]) => `<div class="fgrp${neben ? " neben" : ""}" data-f="${k}"><button type="button" class="fbtn" aria-expanded="false" aria-controls="${pre}fp-${k}"><span class="flab">${label}</span><span class="fval"></span></button><div class="fpanel" id="${pre}fp-${k}" hidden></div></div>`).join("") +
      `<button type="button" class="fmehr" id="${pre}fmehr" aria-expanded="false"><span class="fmehr-t">${TXT.mehr}</span><span class="fanz"></span></button>` +
      `<button type="button" class="fclear" id="${pre}fclear" hidden>${TXT.alle}</button></div>`;
    const leiste = opt.box.querySelector(".filter"), sol = opt.box.querySelector(".sol-btn"), fmehr = leiste.querySelector(".fmehr"), fclear = leiste.querySelector(".fclear");
    sol.id = pre + "solide";
    const grp = k => leiste.querySelector(`.fgrp[data-f="${k}"]`);
    let solide = false, offen = null;

    function panelBauen(f, KEYS) {
      const p = grp(f.k).querySelector(".fpanel");
      let opts;
      if (f.liste) {   // Land/Währung: alle vorkommenden Werte, häufigste zuerst
        const n = new Map();
        for (const ks of KEYS) { const v = ks[f.i]; if (v != null) n.set(v, (n.get(v) || 0) + 1); }
        opts = [...n.keys()].sort((a, b) => n.get(b) - n.get(a) || f.name(a).localeCompare(f.name(b), "de")).map(v => [v, f.name(v)]);
      } else opts = f.opts();
      f.namen = new Map(opts.map(o => [o[0], o[1]]));
      const B = BEREICHE[f.k], bf = bereich[f.k];
      const feld = (w, i) => `<input type="text" class="fber-${w}" inputmode="${B.datum ? "numeric" : "decimal"}" autocomplete="off" placeholder="${B.ph[i]}" value="${esc(w === "von" ? bf.tv : bf.tb)}"${ungueltig(f.k, w) ? ' aria-invalid="true"' : ""} aria-label="${B.datum ? (w === "von" ? "Fällig ab" : "Fällig bis") + " (Monat und Jahr)" : (w === "von" ? "Rendite ab" : "Rendite bis") + " in Prozent"}">`;
      p.innerHTML =
        (f.k === "land" ? `<input type="search" class="fsuche" placeholder="${TXT.landSuche}" aria-label="${TXT.landSuche}">` : "") +
        (B ? `<div class="fber" data-b="${f.k}"><span class="fber-l">${B.label}</span>${feld("von", 0)}<span class="fber-s">bis</span>${feld("bis", 1)}${B.datum ? "" : '<span class="fber-s">%</span>'}<p class="fber-h">${esc(B.hint)}</p></div>` : "") +
        `<fieldset><legend class="sr-only">${esc(f.label)}</legend><div class="fopts">` +
        opts.map(([v, t, d]) => `<label class="fopt" data-v="${esc(v)}" data-n="${esc(norm(t))}"><input type="checkbox" value="${esc(v)}"><span class="ftxt">${esc(t)}${d ? `<small>${esc(d)}</small>` : ""}</span><span class="fnum"></span></label>`).join("") +
        `</div></fieldset>` +
        `<div class="ffoot">${f.hint ? `<p class="fhint">${esc(f.hint())}</p>` : f.hintHtml ? `<p class="fhint">${f.hintHtml()}</p>` : ""}<button type="button" class="freset">${TXT.clear}</button></div>`;
    }
    function daten(KEYS) {
      FILTER.forEach(f => panelBauen(f, KEYS));
      for (const f of FILTER) for (const v of [...sel[f.k]]) if (!f.namen.has(v)) sel[f.k].delete(v);   // Werte, die es nicht (mehr) gibt, verwerfen
    }
    // Ein Durchlauf: Treffer (alle Filter erfüllt) und Zählungen je Filteroption – gezählt wird jeweils mit allen
    // ÜBRIGEN Filtern, damit die Zahl zeigt, was diese Auswahl ergäbe.
    function auswerten(KEYS, SOL, pass) {
      const akt = aktiv().map(f => [f.i, sel[f.k]]);
      const zahl = FILTER.map(() => new Map()), hits = [];
      for (let i = 0; i < KEYS.length; i++) {
        if (solide && !SOL[i]) continue;
        if (pass && !pass(i)) continue;
        const ks = KEYS[i];
        if (!imBereich(ks)) continue;
        let fehl = -1, n = 0;
        for (const [fi, s] of akt) if (!trifft(s, ks[fi])) { fehl = fi; if (++n > 1) break; }
        if (n > 1) continue;
        if (n === 1) { zaehle(zahl[fehl], ks[fehl]); continue; }
        for (let fi = 0; fi < FILTER.length; fi++) zaehle(zahl[fi], ks[fi]);
        hits.push(i);
      }
      return { hits, zahl };
    }
    function zeigen(zahl) {
      for (const f of FILTER) {
        const g = grp(f.k), s = sel[f.k], m = zahl[f.i];
        for (const o of g.querySelectorAll(".fopt")) {
          const v = o.dataset.v, n = m.get(v) || 0, box = o.firstElementChild;
          box.checked = s.has(v);
          o.querySelector(".fnum").textContent = n.toLocaleString("de-DE");
          o.classList.toggle("leer", n === 0 && !s.has(v));
        }
        const b = g.querySelector(".fbtn"), val = g.querySelector(".fval"), ber = BEREICHE[f.k] ? bereichText(f.k) : "";
        b.classList.toggle("on", s.size > 0 || !!ber);
        const stufen = s.size === 1 ? ((f.kurz || (v => (f.namen && f.namen.get(v)) || v))([...s][0])) : s.size > 1 ? `${s.size} gewählt` : "";   // „Kupon · 2“ las sich wie 2 % (Nutzertest 03.10.2026)
        val.textContent = [ber, stufen].filter(Boolean).join(" · ");
      }
      fclear.hidden = !aktiv().length && !solide && !bereichIrgend();
      // Schalter „Weitere Filter“: Zahl der aktiven Filter im ausgeblendeten Teil
      const nNeben = FILTER.filter(f => sel[f.k].size && grp(f.k).classList.contains("neben")).length;
      fmehr.querySelector(".fanz").textContent = nNeben ? String(nNeben) : "";
    }
    function panel(k, auf) {
      const g = grp(k); if (!g) return;
      const b = g.querySelector(".fbtn"), p = g.querySelector(".fpanel");
      if (auf && offen && offen !== k) panel(offen, false);
      p.hidden = !auf; b.setAttribute("aria-expanded", String(auf)); g.classList.toggle("offen", auf);
      offen = auf ? k : (offen === k ? null : offen);
      if (auf) {
        p.classList.remove("rechts");
        const r = p.getBoundingClientRect();
        if (r.right > document.documentElement.clientWidth - 8 && window.innerWidth > 600) p.classList.add("rechts");
        const s = p.querySelector(".fsuche"); if (s) s.focus();
      }
    }
    function mehr(auf) {
      leiste.classList.toggle("alle", auf);
      fmehr.setAttribute("aria-expanded", String(auf));
      fmehr.querySelector(".fmehr-t").textContent = auf ? TXT.weniger : TXT.mehr;
      if (!auf && offen && grp(offen).classList.contains("neben")) panel(offen, false);
    }
    function setSolide(v) { solide = !!v; sol.setAttribute("aria-pressed", String(solide)); }
    function zuruecksetzen() { FILTER.forEach(f => sel[f.k].clear()); Object.keys(bereich).forEach(bereichLeeren); setSolide(false); if (offen) panel(offen, false); }
    const holen = () => opt.laden ? opt.laden() : Promise.resolve();

    // ---------- Bedienung ----------
    sol.addEventListener("click", () => { setSolide(!solide); holen(); onChange(); });
    leiste.addEventListener("click", e => {
      if (e.target.closest(".fmehr")) { holen(); mehr(!leiste.classList.contains("alle")); return; }
      const b = e.target.closest(".fbtn");
      // Vor dem Laden: Daten holen, dann das gewünschte Auswahlfeld öffnen
      if (b && !bereit()) { const k = b.parentElement.dataset.f; holen().then(() => { if (bereit()) panel(k, true); }); return; }
      if (b) { const k = b.parentElement.dataset.f; panel(k, b.getAttribute("aria-expanded") !== "true"); return; }
      const r = e.target.closest(".freset");
      if (r) { const k = r.closest(".fgrp").dataset.f; sel[k].clear(); if (bereich[k]) bereichLeeren(k); onChange(); return; }
      if (e.target.closest(".fclear")) { zuruecksetzen(); onChange(); }
    });
    function berEingabe(i, nurGueltig) {
      const k = i.closest(".fber").dataset.b, w = i.classList.contains("fber-von") ? "von" : "bis";
      const v = BEREICHE[k].datum ? datumLesen(i.value, w === "bis") : zahlLesen(i.value);
      if (nurGueltig && v === null) return;
      bereichSetzen(k, w, i.value);
      markieren(k);   // dieses Feld und – bei Von über Bis – auch das andere
      onChange();
    }
    let berT = 0;
    leiste.addEventListener("keydown", e => { const i = e.target.closest && e.target.closest(".fber input"); if (i && e.key === "Enter") { e.preventDefault(); clearTimeout(berT); berEingabe(i); } });
    leiste.addEventListener("change", e => {
      const i = e.target.closest(".fber input"); if (i) { clearTimeout(berT); berEingabe(i); return; }
      const c = e.target.closest(".fopt input"); if (!c) return;
      const s = sel[c.closest(".fgrp").dataset.f];
      if (c.checked) s.add(c.value); else s.delete(c.value);
      onChange();
    });
    leiste.addEventListener("input", e => {
      const i = e.target.closest(".fber input"); if (i) { clearTimeout(berT); berT = setTimeout(() => berEingabe(i, true), 700); return; }
      const s = e.target.closest(".fsuche"); if (!s) return;
      const q = norm(s.value.trim());
      for (const o of s.parentElement.querySelectorAll(".fopt")) o.hidden = q !== "" && !o.dataset.n.includes(q) && !o.dataset.v.toLowerCase().includes(q);
    });
    document.addEventListener("click", e => { if (offen && !e.target.closest(".fgrp")) panel(offen, false); });
    // iPhone/iPad schicken beim Tipp auf eine Fläche ohne Klick-Hörer (Text, Überschrift) kein click – die Tafel blieb dann offen.
    // Deshalb dieselbe Regel schon beim Aufsetzen des Fingers (seit 09.10.2026, Technik-Test 08.10.2026 T-144). Die Tafel liegt über dem
    // Inhalt (position: absolute), Zuklappen verschiebt also nichts unter dem Finger.
    document.addEventListener("pointerdown", e => { if (e.pointerType === "touch" && offen && e.target.closest && !e.target.closest(".fgrp")) panel(offen, false); });
    document.addEventListener("keydown", e => {
      if (e.key !== "Escape" || !offen) return;
      const k = offen; panel(k, false); grp(k).querySelector(".fbtn").focus();
    });

    return {
      FILTER, sel, keys: r => FILTER.map(f => f.key(r)).concat([r[5] || "", rendite(r)]), solideRegel, daten, auswerten, zeigen, aktiv, mehr, zuruecksetzen,
      gesetzt: () => aktiv().length > 0 || solide || bereichIrgend(),
      bereichLesen: (k, von, bis) => { if (!bereich[k]) return; bereichSetzen(k, "von", von || ""); bereichSetzen(k, "bis", bis || ""); },
      bereichTexte: k => bereich[k] ? [bereich[k].von !== "" ? bereich[k].tv : "", bereich[k].bis !== "" ? bereich[k].tb : ""] : ["", ""],
      spanneVerkehrt: () => Object.keys(bereich).filter(verkehrt),
      nebenAktiv: () => FILTER.some(f => sel[f.k].size && grp(f.k).classList.contains("neben")),
      get solide() { return solide; }, set solide(v) { setSolide(v); },
    };
  };
  MC.anleihenFilter.landName = landName;
})(window.MC);
