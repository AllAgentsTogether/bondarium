/* felder.js – Feldkatalog und Standardtabelle der Anleihen-Angaben (seit 03.10.2026, Konzept „Einheitliche Anleihen-Angaben“;
   Regeln in docs/ANLEIHEN-ANGABEN.md). Laden NACH site.js (MC.zahl, MC.datum, MC.restlaufzeit, MC.esc):
     <script src="site.js"></script><script src="felder.js"></script>

   Eine Angabe – ein Name, eine Schreibweise, eine Rechenregel. Was zu einer Anleihe gezeigt wird (Suche, Ranglisten, Startseite,
   Langläufer, Merkliste, Vergleich, Musterdepot, PDFs, Steckbrief), nimmt Bezeichnung und Format von hier.

   Der Katalog zwischen den Markierungen KATALOG und KATALOG-ENDE ist reines JSON: scripts/_common.py (felder_katalog) liest ihn
   für die Python-Skripte (Wochenbrief, vorgerenderte Tabellen, Datenlauf), konto.php/erinnerung.php über den Wochenbrief-Datensatz.
   Darin: Bezeichnungen je Angabe (kurz = Tabellenkopf und Handy-Beschriftung, unter = zweite Zeile im Kopf, lang = Steckbrief und
   Vergleich, title = Erklärung beim Überfahren), Art, Bonitätsspannen, Ländernamen der Staaten, die Rechtsform-Regel und Ausnahmen für sperrige Emittentennamen
   (Schlüssel: Emittent in lesbarer Schreibung).

   API (MC.felder):
     K, F                       Katalog und Felder (F.rendite.kurz …)
     lesbar(name)               GLEIF-Versalien in übliche Schreibung („SIEMENS FINANCIERINGSMAATSCHAPPIJ N.V.“ → „Siemens Financieringsmaatschappij N.V.“)
     kurzName(emittent, art, land, reg)   Staat (art 0, Land ≠ INT): Ländername; sonst Emittent ohne Rechtsform; ohne Emittent: Registername
     titel(o)                   „Italien 3,50 % 2030“ (Kurzname, Kupon, Fälligkeitsjahr) – Legenden, Listen, Kalender, Auswahlfelder
     Formate: pct, kupon(o), kurs, pkt, datum, tag, restlaufzeit(iso|Jahre), volumen, stueckelung, betrag, bonitaet, jahre(iso)
     spalten, tabelle(spaltenIds, zeilen, opt), sortiere(zeilen, sort, spaltenIds, opt), sortierbar(table, sort, neu)

   Zeilenobjekt der Standardtabelle (Felder, die eine Spalte braucht; fehlende = „–“):
     { isin, kurz, reg, art (0 Staat · 1 Öffentlich · 2 Unternehmen), ccy, kupon (Zahl | "var"), zinsart (0 fest · 1 variabel · 2 Nullkupon),
       faellig (ISO | ""), kurs, kdatum (Kursdatum), boerse, vortag, rend (Zahl | null), rendGrund, fraglich, real, pruef (Text | ""),
       bon (1 · 3 · 0 · undefined), stk, vol, platz, ht, um, zt (nächster Zinstermin), ztGeschaetzt, lfd, mac, dur, auf, seit, merktag } */
(function (MC) {
  "use strict";
  if (!MC) return;
  var K = /*KATALOG*/{"felder":{"anleihe":{"kurz":"Anleihe","unter":"ISIN · Art · Währung","lang":"Anleihe","title":"Kurzname: bei Staaten das Land, sonst der Emittent ohne Rechtsform. Ein Klick öffnet den Steckbrief."},"emittent":{"kurz":"Emittent","lang":"Emittent","title":"Laut LEI-Register (GLEIF)"},"isin":{"kurz":"ISIN","lang":"ISIN"},"art":{"kurz":"Art","lang":"Art","title":"Staat: Zentralstaaten. Öffentlich: Bundesländer, Regionen, Förderbanken, Supranationale. Unternehmen: einschließlich Banken."},"waehrung":{"kurz":"Währung","lang":"Währung"},"land":{"kurz":"Land","lang":"Land des Emittenten","title":"Sitz des Konzerns laut LEI-Register"},"rendite":{"kurz":"Rendite","lang":"Rendite bis Fälligkeit","title":"Rendite bis Fälligkeit in % pro Jahr – von uns aus dem Schlusskurs berechnet (Bundeswertpapiere: Rendite der Deutschen Bundesbank)"},"kupon":{"kurz":"Kupon","lang":"Kupon","title":"Zinssatz pro Jahr auf den Nennwert"},"lfd":{"kurz":"lfd. Verzinsung","lang":"Laufende Verzinsung","title":"Kupon geteilt durch Kurs – Zinsen pro Jahr bezogen auf den Kurswert"},"restlaufzeit":{"kurz":"Restlaufzeit","unter":"Fälligkeit","lang":"Restlaufzeit","title":"Zeit von heute bis zur Fälligkeit, darunter der Fälligkeitstag"},"faelligkeit":{"kurz":"Fälligkeit","lang":"Fälligkeit","title":"Tag der Rückzahlung zum Nennwert"},"duration":{"kurz":"Duration","unter":"mod. Duration","lang":"Duration","title":"Duration: durchschnittliche Kapitalbindung in Jahren, die Zahlungen nach ihrem Barwert gewichtet. Modifizierte Duration: um so viel Prozent ändert sich der Kurs ungefähr, wenn die Rendite um einen Prozentpunkt steigt oder fällt."},"modDuration":{"kurz":"mod. Duration","lang":"Modifizierte Duration"},"aufschlag":{"kurz":"Risikoaufschlag","lang":"Risikoaufschlag zu Bund","title":"Rendite minus Rendite einer Bundesanleihe gleicher Restlaufzeit, in Prozentpunkten (nur Euro-Anleihen bis 30 Jahre)"},"kurs":{"kurz":"Kurs","lang":"Kurs","title":"Schlusskurs in % des Nennwerts"},"vortag":{"kurz":"zum Vortag","lang":"Veränderung zum Vortag","title":"Veränderung des Kurses zum vorherigen Schlusskurs, in Prozentpunkten"},"bonitaet":{"kurz":"Bonität","lang":"Bonität laut EZB","title":"Bonität laut EZB: Spanne der Notenskala, abgelesen aus der EZB-Liste notenbankfähiger Sicherheiten (keine Ratings der Agenturen). „–“: nicht auf der EZB-Liste."},"kuendigung":{"kurz":"Kündigung","lang":"Kündigungsrecht Emittent","title":"Ob und ab wann der Emittent vorzeitig zurückzahlen darf – laut Registername und Register"},"stueckelung":{"kurz":"Stückelung","lang":"Stückelung (Mindestanlage)","title":"Kleinster handelbarer Nennwert (zugleich Mindestanlage), in der Währung der Anleihe"},"volumen":{"kurz":"Volumen","lang":"Volumen","title":"Ausgegebener Nennbetrag laut ESMA-Register, in der Währung der Anleihe"},"umsatz":{"kurz":"Umsatz","lang":"Umsatz","title":"Börse Frankfurt und Tradegate, Stück × Kurs, in der Währung der Anleihe"},"handelstage":{"kurz":"Handelstage","lang":"Handelstage mit Umsatz","title":"Börsentage mit Umsatz an der Börse Frankfurt oder bei Tradegate im Zeitraum der Rangliste – danach ist gerankt; der Umsatz erscheint beim Überfahren"},"seitHoch":{"kurz":"Seit Hoch","lang":"Kurs seit dem Höchststand"},"seitMerken":{"kurz":"Seit dem Merken","unter":"gemerkt am","lang":"Rendite seit dem Merken","title":"Veränderung der Rendite seit dem Tag, an dem du die Anleihe gemerkt hast, in Prozentpunkten"},"zinstermin":{"kurz":"Nächster Zinstermin","lang":"Nächster Zinstermin","title":"Laut Deutscher Börse; geschätzt, wo die Börse keinen Termin nennt"},"zinsrhythmus":{"kurz":"Zinsrhythmus","lang":"Zinsrhythmus"},"nennwert":{"kurz":"Nennwert","lang":"Nennwert"},"kaufpreis":{"kurz":"Kaufpreis","lang":"Kaufpreis"},"kurswert":{"kurz":"Kurswert","lang":"Kurswert"},"anteil":{"kurz":"Anteil","lang":"Anteil"},"zinsenJahr":{"kurz":"Zinsen pro Jahr","lang":"Zinsen pro Jahr"},"platz":{"kurz":"#","lang":"Platz"}},"art":["Staat","Öffentlich","Unternehmen"],"bonitaet":{"1":"AAA bis A−","3":"BBB+ bis BBB−","0":"mindestens BBB−"},"rechtsform":"[\\s,]+(AG|SE|KGaA|GmbH|mbH|S\\.?A\\.?|S\\.?p\\.?A\\.?|N\\.?V\\.?|B\\.?V\\.?|plc|PLC|p\\.l\\.c\\.|Inc\\.?|Corp\\.?|Corporation|Ltd\\.?|Limited|LLC|LLP|L\\.?P\\.?|A/S|AB|ASA|Oyj|S\\.?A\\.?S\\.?|S\\.?à r\\.?l\\.?|S\\.r\\.l\\.|Co\\.?|Pte\\.?|Pty|Designated Activity Company|DAC|Aktiengesellschaft|Public Limited Company|Societa' per Azioni|Sociedad Anónima|Sociedad Anonima|Gesellschaft mit beschränkter Haftung|Kommanditgesellschaft auf Aktien|Incorporated|Anonim Şirketi|Aktiebolag|Unlimited Company|SPÓŁKA Akcyjna|Spółka Akcyjna)\\.?(?: VW)?$","staaten":{"AD":"Andorra","AL":"Albanien","AM":"Armenien","AO":"Angola","AR":"Argentinien","AT":"Österreich","AU":"Australien","AZ":"Aserbaidschan","BB":"Barbados","BE":"Belgien","BG":"Bulgarien","BH":"Bahrain","BJ":"Benin","BM":"Bermuda","BO":"Bolivien","BR":"Brasilien","BS":"Bahamas","CA":"Kanada","CG":"Kongo-Brazzaville","CH":"Schweiz","CI":"Côte d’Ivoire","CL":"Chile","CM":"Kamerun","CN":"China","CO":"Kolumbien","CR":"Costa Rica","CY":"Zypern","CZ":"Tschechien","DE":"Deutschland","DK":"Dänemark","DO":"Dominikanische Republik","EC":"Ecuador","EE":"Estland","EG":"Ägypten","ES":"Spanien","FI":"Finnland","FR":"Frankreich","GA":"Gabun","GB":"Großbritannien","GE":"Georgien","GH":"Ghana","GR":"Griechenland","GT":"Guatemala","HK":"Hongkong","HN":"Honduras","HR":"Kroatien","HU":"Ungarn","ID":"Indonesien","IE":"Irland","IL":"Israel","IM":"Isle of Man","IQ":"Irak","IS":"Island","IT":"Italien","JM":"Jamaika","JO":"Jordanien","JP":"Japan","KE":"Kenia","KR":"Südkorea","KW":"Kuwait","KZ":"Kasachstan","LB":"Libanon","LK":"Sri Lanka","LT":"Litauen","LU":"Luxemburg","LV":"Lettland","MA":"Marokko","ME":"Montenegro","MK":"Nordmazedonien","MT":"Malta","MX":"Mexiko","NG":"Nigeria","NL":"Niederlande","NO":"Norwegen","NZ":"Neuseeland","OM":"Oman","PA":"Panama","PE":"Peru","PH":"Philippinen","PK":"Pakistan","PL":"Polen","PT":"Portugal","PY":"Paraguay","QA":"Katar","RO":"Rumänien","RS":"Serbien","RU":"Russland","RW":"Ruanda","SA":"Saudi-Arabien","SE":"Schweden","SG":"Singapur","SI":"Slowenien","SK":"Slowakei","SM":"San Marino","SN":"Senegal","SR":"Suriname","SV":"El Salvador","TJ":"Tadschikistan","TR":"Türkei","TT":"Trinidad und Tobago","UA":"Ukraine","US":"USA","UY":"Uruguay","UZ":"Usbekistan","VE":"Venezuela","ZA":"Südafrika","ZM":"Sambia"},"ausnahmen":{"Kreditanstalt für Wiederaufbau KfW":"KfW","International Bank for Reconstruction and Development Weltbank World Bank IBRD":"Weltbank","His Majesty in right of Alberta":"Alberta","Landwirtschaftliche Rentenbank Rentenbank":"Rentenbank","Inter-American Development Bank":"Interamerikanische Entwicklungsbank","European Investment Bank EIB Europäische Investitionsbank":"Europäische Investitionsbank","Eurofima European Company for the Financing of Railroad Rolling Stock":"Eurofima","Landeskreditbank Baden-Württemberg -Förderbank-":"L-Bank","Council of Europe Development Bank":"Entwicklungsbank des Europarats","His Majesty the King in right of Ontario":"Ontario","His Majesty the King in Right of the Province of British Columbia":"British Columbia","Ministeries van de Vlaamse Gemeenschap":"Flandern","République et Canton de Genève":"Kanton Genf","Genossenschaft Emissionszentrale für gemeinnützige Wohnbauträger EGW":"EGW Emissionszentrale","DZ BANK AG Deutsche Zentral-Genossenschaftsbank, Frankfurt am Main":"DZ Bank","Landesbank Hessen-Thüringen Girozentrale":"Helaba","Ministerium der Finanzen und für Europa des Landes Brandenburg":"Land Brandenburg","Sächsische Aufbaubank - Förderbank -":"Sächsische Aufbaubank","Wirtschafts- und Infrastrukturbank Hessen, rechtlich unselbstständige Anstalt des öffentlichen Rechts in der Landesbank Hessen-Thüringen Girozentrale":"WIBank","Bausparkasse Schwäbisch Hall Aktiengesellschaft - Bausparkasse der Volksbanken und Raiffeisenbanken -":"Bausparkasse Schwäbisch Hall","Norddeutsche Landesbank - Girozentrale -":"NordLB","Dekabank Deutsche Girozentrale":"Dekabank","European Union EU Europäische Union":"Europäische Union","European Financial Stability Facility Efsf":"EFSF","European Stability Mechanism ESM":"ESM","Mediobanca - Banca di Credito Finanziario S.p.A.":"Mediobanca","European Bank for Reconstruction and Development":"Osteuropabank (EBRD)","Perusahaan Penerbit Surat Berharga Syariah Negara Indonesia III":"Indonesien (Sukuk)"},"reihe":["platz","anleihe","rendite","kupon","lfd","restlaufzeit","duration","aufschlag","kurs","bonitaet","kuendigung","stueckelung","volumen","handelstage","seitHoch","seitMerken","zinstermin","merken"]}/*KATALOG-ENDE*/;
  var F = K.felder, NBSP = " ";
  var esc = function (s) { return MC.esc(String(s == null ? "" : s)); };
  var zahl = function (v, d) { return MC.zahl(v, d || 0); };

  // ---------- Namen ----------
  // Lesbare Schreibung (gleiche Regel wie scripts/_common.py lesbar): nur reine Versalien-Namen werden umgesetzt; Rechtsformen in
  // üblicher Schreibung, kurze Kürzel und Wörter ohne Vokal bleiben groß (BNP, HSBC), Bindewörter klein (of, de, für).
  var RF_SCHREIB = { "AG": "AG", "SE": "SE", "KG": "KG", "KGAA": "KGaA", "GMBH": "GmbH", "MBH": "mbH", "N.V.": "N.V.", "B.V.": "B.V.", "S.A.": "S.A.", "S.A": "S.A.",
    "S.P.A.": "S.p.A.", "SPA": "S.p.A.", "S.A.S.": "S.A.S.", "S.À": "S.à", "R.L.": "r.l.", "S.R.L.": "S.r.l.", "SRL": "S.r.l.", "S.L.": "S.L.", "SARL": "S.à r.l.",
    "INC.": "Inc.", "INC": "Inc.", "LTD.": "Ltd.", "LTD": "Ltd", "CORP.": "Corp.", "CORP": "Corp.", "CO.": "Co.", "CO": "Co.", "PTE.": "Pte.", "PTE": "Pte.", "PTY": "Pty",
    "OYJ": "Oyj", "P.L.C.": "p.l.c.", "L.P.": "L.P.", "LLP": "LLP", "LLC": "LLC", "PLC": "PLC", "A/S": "A/S", "ASA": "ASA", "AB": "AB", "AS": "AS", "SA": "SA",
    "NV": "NV", "BV": "BV", "SAS": "SAS", "C.V.": "C.V.", "S.A.B.": "S.A.B.", "KFW": "KfW", "ENBW": "EnBW", "E.ON": "E.ON", "AT&T": "AT&T" };
  var RF_IMMER = ["KFW", "ENBW", "E.ON", "AT&T"];
  var KLEINWORT = new Set("OF AND THE FOR DE DI DEL DELLA DES DU LA LE LES Y E ET EN IN FÜR UND DER DIE DAS DEN VON VAN ZU AM IM AUF PER DA DO DOS".split(" "));
  var KUERZEL = new Set("BASF BBVA AMRO BAWAG NIBC RATP SICAV SOFOM HSBC LBBW NRW USA UK US EU".split(" "));
  var WORT3 = new Set("OIL GAS NEW AIR SEA SUN BAY CAR ONE TWO TEN BIG RED OWL TOP WAY KEY AID ART BIO BOX CAP FIN LAB LAW MAX NET PAY PRO RIO SKY SOL TEA TEL WEB BAU".split(" "));
  function lesbarWort(w, erstes, nachApostroph) {
    var u = w.toUpperCase();
    if (w.length === 1) return nachApostroph ? w.toLowerCase() : w;
    if (!erstes && KLEINWORT.has(u)) return w.toLowerCase();
    if (KUERZEL.has(u) || !/[AEIOUYÄÖÜÉÈÀÁÍÓÚÂÊÎÔÛİ]/.test(u)) return w;
    if (w.length <= 3 && !WORT3.has(u) && !KLEINWORT.has(u)) return w;
    return w[0] + w.slice(1).replace(/İ/g, "i").toLowerCase();
  }
  function lesbar(name) {
    var s = String(name || "").trim();
    if (!s || /[a-zß-ÿ]/.test(s) || !/[A-Z]/.test(s)) return s;
    return s.split(/\s+/).map(function (tok, i) {
      var kern = tok.replace(/^[,;()"']+|[,;()"']+$/g, ""), vor = kern ? tok.slice(0, tok.indexOf(kern)) : tok, nach = kern ? tok.slice(vor.length + kern.length) : "";
      var KK = kern.toUpperCase();
      if (RF_SCHREIB[KK] && (i > 0 || RF_IMMER.indexOf(KK) >= 0)) return vor + RF_SCHREIB[KK] + nach;
      var teile = tok.split(/([A-Za-zÀ-ÖØ-öø-ÿİŞĞÇ]+)/);
      return teile.map(function (t, j) { return j % 2 ? lesbarWort(t, i === 0 && j === 1, /'$/.test(teile[j - 1] || "")) : t; }).join("");
    }).join(" ");
  }
  var RECHTSFORM = new RegExp(K.rechtsform);
  function kurzName(emittent, art, land, reg) {
    if (art === 0 && land && land !== "INT") return K.staaten[land] || landName(land);
    var e = lesbar(emittent);
    if (!e) return String(reg || "");
    if (K.ausnahmen[e]) return K.ausnahmen[e];   // sperrige Registernamen großer Emittenten („Kreditanstalt für Wiederaufbau KfW“ → „KfW“)
    for (var i = 0; i < 3; i++) e = e.replace(RECHTSFORM, "").trim().replace(/[\s&,\-–]+$/, "");   // „Fresenius SE & Co. KGaA“ → „Fresenius“
    return e;
  }
  var DN = (function () { try { return new Intl.DisplayNames(["de"], { type: "region" }); } catch (e) { return null; } })();
  function landName(c) { if (c === "INT") return "International"; try { return (DN && DN.of(c)) || c; } catch (e) { return c; } }

  // ---------- Schreibweisen (Kapitel 6 des Konzepts) ----------
  function jahre(iso) { return iso ? (Date.parse(String(iso).slice(0, 10) + "T12:00:00Z") - Date.now()) / (365.25 * 864e5) : null; }
  function pct(v) { return typeof v === "number" && isFinite(v) ? zahl(v, 2) + NBSP + "%" : "–"; }
  function kuponZahl(c) { return zahl(c, Math.round(c * 1000) % 10 ? 3 : 2) + NBSP + "%"; }
  function kupon(o) {
    if (!o) return "–";
    if (o.zinsart === 1 || o.kupon === "var") return "variabel";
    if (o.zinsart === 2 || (o.kupon === 0 && o.zinsart !== 0)) return "Nullkupon";
    return typeof o.kupon === "number" ? kuponZahl(o.kupon) : "–";
  }
  function kurs(v) { return typeof v === "number" && isFinite(v) ? zahl(v, Math.abs(v * 100 - Math.round(v * 100)) > 1e-6 ? 3 : 2) + NBSP + "%" : "–"; }
  function pkt(v, d) { d = d == null ? 2 : d; if (typeof v !== "number" || !isFinite(v)) return "–"; var r = Math.round(v * Math.pow(10, d)) / Math.pow(10, d) || 0; return (r > 0 ? "+" : "") + zahl(r, d) + NBSP + "Pkt."; }
  function datum(iso) { return iso ? MC.datum(iso) : "–"; }
  function tag(iso) { return iso ? MC.tag(iso) : "–"; }
  function restlaufzeit(x) { var y = typeof x === "number" ? x : jahre(x); return y == null ? "unbefristet" : MC.restlaufzeit(y); }
  function volumen(v, w) {
    if (typeof v !== "number" || !isFinite(v) || v <= 0) return "–";
    var t = v < 1e6 ? zahl(v, 0) : (v >= 1e9 ? v / 1e9 : v / 1e6).toLocaleString("de-DE", { maximumSignificantDigits: 3 }) + NBSP + (v >= 1e9 ? "Mrd." : "Mio.");
    return t + (w ? NBSP + w : "");
  }
  function stueckelung(v, w) { return typeof v === "number" && isFinite(v) ? v.toLocaleString("de-DE", { maximumFractionDigits: 3 }) + (w ? NBSP + w : "") : "–"; }
  function betrag(v, w, d) { return typeof v === "number" && isFinite(v) ? zahl(v, d == null ? 2 : d) + (w ? NBSP + w : "") : "–"; }
  function bonitaet(b) { return b != null && K.bonitaet[String(b)] || ""; }
  function titel(o) { return [o.kurz || o.reg || o.isin, kupon(o), o.faellig ? String(o.faellig).slice(0, 4) : "unbefristet"].join(" "); }

  // ---------- Standardtabelle (Kapitel 5 des Konzepts) ----------
  // Gesamtliste der Spalten in fester Reihenfolge; jede Tabelle wählt aus, stellt aber nie um. Zelle: { h: HTML, s: zweite Zeile (HTML),
  // p: Vorsatz der zweiten Zeile auf der Handy-Karte, t: Titel beim Überfahren }.
  var REIHE = K.reihe;   // Gesamtliste der Spalten im Katalog (auch scripts/statische_tabellen.py und scripts/pruefen.py lesen sie dort)
  var ART = K.art;
  function renditeZelle(o) {
    if (o.rend == null) return { h: '<span title="' + esc(o.rendGrund || "keine Rendite") + '">–</span>' };
    if (o.fraglich) return { h: '<span class="fraglich" title="' + esc(o.fraglichText || "Kurs ohne Umsatz (Taxe), Rendite deutlich über Bund – Wert fraglich") + '">' + pct(o.rend) + "<sup>?</sup></span>" };
    return { h: pct(o.rend) + (o.real ? '<span title="Realrendite (inflationsindexiert)">*</span>' : "") };
  }
  function kursZelle(o, ctx) {
    var h = '<span title="' + (o.kdatum ? "Schlusskurs vom " + datum(o.kdatum) + (o.boerse && BOERSE[o.boerse] ? ", " + BOERSE[o.boerse] : "") : "") + '">' + kurs(o.kurs) + "</span>";
    var stand = ctx && ctx.kstand;
    if (o.kdatum && stand && o.kdatum !== stand) return { h: h, s: "vom " + tag(o.kdatum), p: "" };
    if (ctx && ctx.vortag && typeof o.vortag === "number" && typeof o.kurs === "number") {
      var d = o.kurs - o.vortag;
      return { h: h, s: '<span class="' + (d > 0.004 ? "plus" : d < -0.004 ? "minus" : "") + '">' + pkt(d) + "</span>", p: "zum Vortag" };
    }
    return { h: h };
  }
  var BOERSE = { F: "Börse Frankfurt", T: "Tradegate", X: "Xetra", B: "Deutsche Bundesbank" };
  var SPALTEN = {
    platz: { cls: "rk", sort: function (o) { return o.platz; }, zelle: function (o) { return { h: String(o.platz || "") }; } },
    anleihe: { th: true, sort: function (o) { return (o.kurz || "").toLowerCase(); },
      zelle: function (o, ctx) {
        var name = o.kurz || o.reg || o.isin, link = ctx && ctx.link ? ctx.link(o) : "anleihe.html?isin=" + encodeURIComponent(o.isin);
        var sub = [o.isin, ART[o.art] || "", o.ccy].filter(Boolean).join(" · ");
        return { h: (ctx && ctx.nameVor ? ctx.nameVor(o) : "") + '<a class="name-link" href="' + esc(link) + '" title="' + esc(o.reg ? "Registername: " + o.reg : "") + '" aria-label="Steckbrief ' + esc(titel(o)) + '">' + esc(name) + "</a>" +
          (o.pruef ? '<span class="pruef" title="' + esc(typeof o.pruef === "string" ? o.pruef : "Widerspruch im ESMA-Register – Registerwerte unverändert gezeigt, keine Rendite") + '">Daten?</span>' : "") +
          (ctx && ctx.nameZusatz ? ctx.nameZusatz(o) : ""), s: esc(sub), p: "" };
      } },
    rendite: { num: true, gross: true, abw: true, sort: function (o) { return o.rend; }, zelle: renditeZelle },
    kupon: { num: true, gross: true, abw: true, sort: function (o) { return typeof o.kupon === "number" ? o.kupon : o.zinsart === 2 ? 0 : null; },
      zelle: function (o, ctx) { var s = ctx && ctx.kuponZeile ? ctx.kuponZeile(o) : ""; return { h: kupon(o), s: esc(s), p: "Zinsen" }; } },
    lfd: { num: true, sort: function (o) { return o.lfd; }, zelle: function (o) { return { h: pct(o.lfd) }; } },
    restlaufzeit: { num: true, gross: true, sort: function (o) { return o.faellig || null; },
      zelle: function (o) { return o.faellig ? { h: restlaufzeit(o.faellig), s: datum(o.faellig), p: "fällig" } : { h: "unbefristet" }; } },
    duration: { num: true, sort: function (o) { return o.mac; }, zelle: function (o) { return o.mac != null ? { h: restlaufzeit(o.mac), s: zahl(o.dur, 1), p: "mod. Duration" } : { h: "–" }; } },
    aufschlag: { num: true, abw: true, sort: function (o) { return o.auf; }, zelle: function (o) { return { h: o.auf != null ? pkt(o.auf) : "–" }; } },
    kurs: { num: true, sort: function (o) { return o.kurs; }, zelle: kursZelle },
    bonitaet: { sort: function (o) { return o.bon === 1 ? 1 : o.bon === 3 ? 3 : o.bon === 0 ? 2 : null; },
      zelle: function (o) { var b = bonitaet(o.bon); return { h: b ? esc(b) : '<span title="nicht auf der EZB-Liste">–</span>' }; } },
    kuendigung: { sort: function (o) { return o.kue || null; }, zelle: function (o) { return { h: esc(o.kue || "–") }; } },
    stueckelung: { num: true, sort: function (o) { return o.stk; }, zelle: function (o) { return { h: stueckelung(o.stk, o.ccy) }; } },
    volumen: { num: true, abw: true, sort: function (o) { return o.vol; }, zelle: function (o) { return { h: volumen(o.vol, o.ccy) }; } },
    handelstage: { num: true, abw: true, sort: function (o) { return o.ht; },
      zelle: function (o, ctx) { return { h: o.ht == null ? "–" : '<span title="Umsatz ' + esc(volumen(o.um, o.ccy)) + '">' + o.ht + (ctx && ctx.tage ? " von " + ctx.tage : "") + "</span>" }; } },
    seitHoch: { num: true, sort: function (o) { return o.seitHoch; }, zelle: function (o) { return { h: o.seitHoch == null ? "–" : zahl(o.seitHoch, 0) + NBSP + "%", s: o.hochText || "", p: "" }; } },
    seitMerken: { num: true, sort: function (o) { return o.seit; },
      zelle: function (o) { return { h: o.seit == null ? "–" : '<span class="' + (o.seit > 0.004 ? "plus" : o.seit < -0.004 ? "minus" : "") + '">' + pkt(o.seit) + "</span>", s: o.merktag ? datum(o.merktag) : "", p: "gemerkt" }; } },
    zinstermin: { num: true, sort: function (o) { return o.zt || null; },
      zelle: function (o) { return { h: o.zt ? datum(o.zt) : "–", s: o.zt && o.zt === o.faellig ? "mit Rückzahlung" : o.zt && o.ztGeschaetzt ? "geschätzt" : !o.zt && o.zinsart === 2 ? "kein Kupon" : "", p: "" }; } },
    merken: { cls: "merkspalte", zelle: function (o) { return { h: MC.konto && MC.konto.knopf ? MC.konto.knopf(o.isin, "nur") : "" }; } },
  };
  Object.keys(SPALTEN).forEach(function (id) {
    var f = F[id] || {};
    SPALTEN[id].id = id; SPALTEN[id].kopf = f.kurz || ""; SPALTEN[id].unter = f.unter || ""; SPALTEN[id].title = f.title || "";
  });
  SPALTEN.merken.kopf = ""; SPALTEN.merken.title = "";
  // Spalten einer Tabelle in der Reihenfolge der Gesamtliste; opt.extra = { id: Spalte } für seitenspezifische Spalten (hinter „merken“
  // vorbei an der Gesamtliste nur, wenn opt.nach = { id: "nach dieser Spalte" } fehlt)
  function spalten(ids, opt) {
    opt = opt || {};
    var extra = opt.extra || {}, liste = REIHE.filter(function (id) { return ids.indexOf(id) >= 0; }).map(function (id) { return SPALTEN[id]; });
    Object.keys(extra).forEach(function (id) {
      var s = extra[id]; s.id = id;
      var nach = opt.nach && opt.nach[id], i = nach ? liste.findIndex(function (x) { return x.id === nach; }) : -1;
      if (i >= 0) liste.splice(i + 1, 0, s); else if (ids.indexOf(id) >= 0) { var m = liste.findIndex(function (x) { return x.id === "merken"; }); if (m >= 0) liste.splice(m, 0, s); else liste.push(s); }
    });
    return liste;
  }
  function sortiere(zeilen, sort, liste) {
    var s = liste.filter(function (x) { return x.id === sort.col; })[0] || SPALTEN[sort.col];
    if (!s || !s.sort) return zeilen.slice();
    return zeilen.slice().sort(function (a, b) {
      var x = s.sort(a), y = s.sort(b);
      if (x == null || y == null) return x == null && y == null ? (a.platz || 0) - (b.platz || 0) : x == null ? 1 : -1;   // ohne Wert ans Ende
      var c = typeof x === "string" ? x.localeCompare(y, "de", { numeric: true }) : x - y;
      return (c || (a.platz || 0) - (b.platz || 0)) * sort.dir;
    });
  }
  // HTML von thead und tbody. opt: { sort: {col, dir}, rang: Spalte, die bei Sortierung nach Platz fett ist, ctx, leer, sortierbar (Standard ja),
  //   sortieren (true: Zeilen hier nach sort ordnen), extra, nach, zeilenKlasse(o), nachZeile(o) (HTML hinter der Zeile, z. B. Kurzansicht) }
  function tabelle(ids, zeilen, opt) {
    opt = opt || {};
    var liste = spalten(ids, opt), sort = opt.sort || { col: null, dir: 1 }, ctx = opt.ctx || {};
    if (opt.sortieren && sort.col) zeilen = sortiere(zeilen, sort, liste);
    var fett = sort.col === "platz" || !sort.col ? opt.rang : sort.col;
    var kopf = "<thead><tr>" + liste.map(function (s) {
      var aria = sort.col === s.id ? ' aria-sort="' + (sort.dir > 0 ? "ascending" : "descending") + '"' : "";
      var unter = s.unter ? "<small>" + esc(s.unter) + "</small>" : "";   // zweite Kopfzeile unter dem Sortierknopf
      var knopf = s.sort && opt.sortierbar !== false && s.kopf ? '<button type="button" class="sortbtn" data-col="' + s.id + '">' + esc(s.kopf) + "</button>" + unter : (s.kopf ? esc(s.kopf) + unter : '<span class="sr-only">' + (s.id === "merken" ? "Merken" : s.id) + "</span>");
      return '<th scope="col" data-col="' + s.id + '" class="' + [s.num ? "num" : "", s.cls || ""].filter(Boolean).join(" ") + '"' + aria + (s.title ? ' title="' + esc(s.title) + '"' : "") + ">" + knopf + "</th>";
    }).join("") + "</tr></thead>";
    var rumpf = zeilen.length ? zeilen.map(function (o) {
      return '<tr' + (opt.zeilenKlasse ? ' class="' + esc(opt.zeilenKlasse(o) || "") + '"' : "") + ' data-isin="' + esc(o.isin) + '">' + liste.map(function (s) {
        var z = s.zelle(o, ctx) || { h: "–" };
        var cls = [s.num ? "num" : "", s.cls || "", s.gross ? "gross" : "", fett === s.id ? "sortiert" : ""].filter(Boolean).join(" ");
        var sub = z.s ? "<small" + (z.p ? ' data-p="' + esc(z.p) + '"' : "") + ">" + z.s + "</small>" : "";
        if (s.th) return '<th scope="row"' + (cls ? ' class="' + cls + '"' : "") + ">" + z.h + sub + "</th>";
        return "<td" + (cls ? ' class="' + cls + '"' : "") + (s.kopf ? ' data-l="' + esc(s.kopf) + '"' : "") + (z.t ? ' title="' + esc(z.t) + '"' : "") + ">" + z.h + sub + "</td>";
      }).join("") + "</tr>" + (opt.nachZeile ? opt.nachZeile(o, liste.length) || "" : "");
    }).join("") : '<tr><td class="leer" colspan="' + liste.length + '">' + esc(opt.leer || "Keine Anleihe.") + "</td></tr>";
    return kopf + "<tbody>" + rumpf + "</tbody>";
  }
  // Sortieren per Klick auf den Spaltenkopf: sort = {col, dir} wird geändert, danach neu(); erste Richtung absteigend bei Rendite, Kupon,
  // Volumen, Handelstage, Risikoaufschlag (abw), sonst aufsteigend
  function sortierbar(table, sort, neu) {
    table.addEventListener("click", function (e) {
      var b = e.target.closest(".sortbtn[data-col]");
      if (!b || !table.tHead || !table.tHead.contains(b)) return;
      var col = b.dataset.col;
      if (sort.col === col) sort.dir = -sort.dir; else { sort.col = col; sort.dir = SPALTEN[col] && SPALTEN[col].abw ? -1 : 1; }
      neu();
    });
  }

  MC.felder = {
    K: K, F: F, ART: ART, BOERSE: BOERSE, lesbar: lesbar, kurzName: kurzName, landName: landName, titel: titel, jahre: jahre,
    pct: pct, kupon: kupon, kuponZahl: kuponZahl, kurs: kurs, pkt: pkt, datum: datum, tag: tag, restlaufzeit: restlaufzeit,
    volumen: volumen, stueckelung: stueckelung, betrag: betrag, bonitaet: bonitaet,
    SPALTEN: SPALTEN, REIHE: REIHE, spalten: spalten, tabelle: tabelle, sortiere: sortiere, sortierbar: sortierbar
  };
})(window.MC);
