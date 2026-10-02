/* mein.js – „Mein Bondarium“ auf den Inhaltsseiten (seit 02.10.2026 abends; Nutzerauftrag: Mockup „Mein Bondarium“ komplett umsetzen).
   Setzt die Knöpfe ein, mit denen ein angemeldeter Nutzer etwas in seinen Bereich legt – gespeichert wird in der Ablage des Kontos
   (konto.js: MC.konto.ablage, konto.php: aktion=ablage; docs/KONTO.md). Laden nach site.js und konto.js:
     <script src="site.js"></script><script src="konto.js"></script><script src="mein.js"></script>

   Was die Seite bekommt, entscheidet ihr Platz im Menü (scripts/nav.py) – keine zweite Liste:
     Akademie-Seiten und die Seiten unter „Kaufen“ (ohne Rechner): am Ende die Leiste „Als gelesen markieren“ und „Lesezeichen“ – für
       alle sichtbar; wer nicht angemeldet ist, landet beim Klick auf konto.html. Angemeldet dazu ein kleines Lesezeichen an jeder
       Zwischenüberschrift (Abschnitt).
     Glossar (begriffe.html): angemeldet ein Stern an jedem Begriff („Gemerkte Begriffe“).
     Zinsen-Seiten: angemeldet die Knöpfe „In meinen Zins-Blick“ für die Kennzahlen der Seite (KENNZAHL – dieselben Kennungen wie in
       bereich.js, das die Werte zeigt).
     Rechner (rechner.html): angemeldet unter jedem Ergebnis „Rechnung speichern“ (Eingaben und Ergebnis); rechner.html?rg=<Kennung>
       öffnet eine gespeicherte Rechnung wieder; die Voreinstellungen (Anlagebetrag, Freistellungsauftrag) füllen die Felder. Die Kirchensteuer wird nie
       gespeichert – weder als Voreinstellung noch in einer Rechnung (Angabe zur Religionszugehörigkeit).
     Deine erste Anleihe: angemeldet liegt der Stand der Checkliste im Konto – auf jedem Gerät derselbe.
     „Zuletzt angesehen“: nur wenn der Nutzer es in „Meldungen und Konto“ eingeschaltet hat, merkt die Seite ihren Aufruf (höchstens
       einmal je Stunde und Seite). MC.mein.angesehen(schluessel, titel) ruft auch der Steckbrief (anleihe.html).
   Nichts davon läuft für Besucher ohne Konto: konto.js fragt den Server nur, wenn der Anmelde-Merker gesetzt ist. */
(function (MC) {
  "use strict";
  var K = MC && MC.konto;
  if (!K || !document.querySelector) return;
  var esc = MC.esc, seite = (location.pathname.replace(/^.*\//, "") || "index.html").replace(/\.html$/, "");
  var main = document.getElementById("main") || document.querySelector("main");
  if (!main) return;
  var h1 = main.querySelector("h1"), titel = (h1 ? h1.textContent : document.title).replace(/\s+/g, " ").trim().slice(0, 110);
  var datei = seite + ".html";
  function imMenue(sel) { var a = document.querySelector('#sitenav ' + sel + ' a[href="' + datei + '"]'); return !!a && !a.classList.contains("nav-ov"); }
  var lern = imMenue(".nav-akademie .nav-spalte") || (imMenue(".nav-kaufen .nav-group-menu") && seite !== "rechner");
  var zinsen = imMenue(".nav-zinsen .nav-group-menu") || seite === "beobachten";

  // Kennzahlen für „Mein Zins-Blick“ je Seite: [Kennung, Beschriftung] – Werte und Quellen stehen in bereich.js (KZ)
  var KENNZAHL = {
    beobachten: [["bund10", "Bundesanleihe 10 Jahre"], ["ezb", "EZB-Einlagesatz"]],
    renditen: [["bund10", "Bundesanleihe 10 Jahre"], ["us10", "US-Staatsanleihe 10 Jahre"]],
    zinskurve: [["kurve", "Zinskurve 10 J. minus 2 J."]],
    realzins: [["realzins", "Realzins 10 Jahre"]],
    unternehmensanleihen: [["aufschlag-us", "Aufschlag US-Unternehmen"]],
    risikoaufschlaege: [["aufschlag-it", "Risikoaufschlag Italien"], ["aufschlag-fr", "Risikoaufschlag Frankreich"], ["aufschlag-us", "Aufschlag US-Unternehmen"]],
    langlaeufer: [["bund2050", "Bundesanleihe 2050"]],
    zinsniveau: [["ezb", "EZB-Einlagesatz"]]
  };

  // ---------- Leiste am Ende einer Akademie-Seite ----------
  if (lern && !document.getElementById("mb-seite")) {
    var leiste = document.createElement("div");
    leiste.className = "mb-seite"; leiste.id = "mb-seite";
    leiste.innerHTML = '<p><b>Mein Bondarium</b>Hak ab, was du gelesen hast – dein Lernstand steht in <a href="konto.html#lernen">deinem Bereich</a>.</p>' +
      K.ablKnopf("gelesen", seite, 1, ["Als gelesen markieren", "Gelesen"]) + K.ablKnopf("lesezeichen", seite, { t: titel }, ["Lesezeichen", "Lesezeichen gesetzt"]);
    var vor = main.querySelector("nav.crossnav") || main.querySelector("details.quellen");
    if (vor && vor.parentNode) vor.parentNode.insertBefore(leiste, vor); else main.appendChild(leiste);
  }

  // „Zuletzt angesehen“ – nur eingeschaltet, höchstens einmal je Stunde und Eintrag
  function angesehen(k, t) {
    if (!K.stand().angemeldet || K.wert("einstellung", "zuletzt") !== 1) return;
    var e = K.abl("angesehen")[k];
    if (e && Date.now() / 1000 - e[1] < 3600) return;
    K.ablage("angesehen", k, String(t || k).slice(0, 90)).catch(function () {});
  }
  MC.mein = { angesehen: angesehen };

  // ---------- Rechner: Rechnung speichern, gespeicherte öffnen, Voreinstellungen ----------
  // Je Rechner: Abschnitt (zugleich Sprungmarke), Felder, Titel und Ergebnis in einem Satz
  function rechner() {
    var $ = function (id) { return document.getElementById(id); }, v = function (id) { var e = $(id); return e ? String(e.value).trim() : ""; }, t = function (id) { var e = $(id); return e ? e.textContent.replace(/\s+/g, " ").trim() : "–"; };
    var R = {
      rendite: { f: ["r1-kurs", "r1-kupon", "r1-faellig", "r1-nenn", "r1-freq"], n: function () { return "Rendite: Kurs " + v("r1-kurs") + ", Kupon " + v("r1-kupon") + " %, fällig " + v("r1-faellig"); }, r: function () { return "Rendite " + t("r1-rendite") + " · Restlaufzeit " + t("r1-jahre"); }, ok: "r1-rendite" },
      stueckzinsen: { f: ["r2-nenn", "r2-kupon", "r2-freq", "r2-letzter", "r2-valuta"], n: function () { return "Stückzinsen: " + v("r2-nenn") + " Nennwert, Kupon " + v("r2-kupon") + " %"; }, r: function () { return "Stückzinsen " + t("r2-stz") + " · " + t("r2-tage") + " Zinstage · Valuta " + v("r2-valuta"); }, ok: "r2-stz" },
      // ohne r3-kist: Die Kirchensteuer wird nie gespeichert (verriete die Religionszugehörigkeit, Art. 9 DSGVO)
      netto: { f: ["r3-betrag", "r3-rendite", "r3-jahre", "r3-fsa"], n: function () { return "Netto nach Steuer: " + v("r3-betrag") + " €, " + v("r3-rendite") + " % Rendite"; }, r: function () { return "netto " + t("r3-netto") + " im Jahr · nach Steuern " + t("r3-nrend"); }, ok: "r3-netto" },
      zinsniveau: { f: ["r4-kupon", "r4-jahre", "r4-rendite"], n: function () { return "Zinsniveau: Kupon " + v("r4-kupon") + " %, " + v("r4-jahre") + " Jahre"; }, r: function () { return "Kurs heute " + t("r4-kurs") + " · modifizierte Duration " + t("r4-dur"); }, ok: "r4-kurs" }
    };
    var setze = function (id, wert) { var e = $(id); if (!e || typeof wert !== "string" || !/^[\d.,\- ]{0,14}$/.test(wert)) return; e.value = wert; e.dispatchEvent(new Event("input", { bubbles: true })); e.dispatchEvent(new Event("change", { bubbles: true })); };
    var q = new URLSearchParams(location.search), rg = q.get("rg"), offen = rg && /^[a-z0-9-]{1,40}$/.test(rg) ? K.wert("rechnung", rg) : null;
    if (offen && R[offen.a] && offen.e && typeof offen.e === "object") {
      // gespeicherte Rechnung: Eingaben zurück in die Felder
      R[offen.a].f.forEach(function (id) { if (id in offen.e) setze(id, String(offen.e[id])); });
      var ziel = $(offen.a); if (ziel) ziel.scrollIntoView({ block: "start" });
    } else if (!location.search) {
      // Voreinstellungen: nur wenn die Seite ohne Vorgaben geöffnet wurde
      var zahl = function (n) { return n.toLocaleString("de-DE", { maximumFractionDigits: 2 }); };
      var b = K.wert("einstellung", "betrag"), f = K.wert("einstellung", "freistellung");
      if (typeof b === "number" && b > 0) { setze("r3-betrag", zahl(b)); setze("r1-nenn", zahl(b)); setze("r2-nenn", zahl(b)); }
      if (typeof f === "number" && f >= 0) setze("r3-fsa", zahl(f));
    }
    Object.keys(R).forEach(function (a) {
      var sec = $(a), bild = sec && sec.querySelector(".k-bild"); if (!bild || bild.querySelector(".mb-rech")) return;
      bild.insertAdjacentHTML("beforeend", '<p class="mb-rech"><button type="button" class="ablbtn klein" data-rg="' + a + '">Rechnung speichern</button><small role="status" aria-live="polite"></small></p>');
    });
    main.addEventListener("click", function (e) {
      var kn = e.target.closest ? e.target.closest("button[data-rg]") : null; if (!kn) return;
      var a = kn.getAttribute("data-rg"), d = R[a], st = kn.parentNode.querySelector("small"), ein = {};
      if (!d || t(d.ok) === "–") { st.textContent = "Erst alle Felder ausfüllen – dann lässt sich die Rechnung speichern."; return; }
      d.f.forEach(function (id) { ein[id] = v(id).slice(0, 14); });
      kn.disabled = true;
      K.ablage("rechnung", "r" + Date.now().toString(36), { a: a, n: d.n().slice(0, 90), e: ein, r: d.r().slice(0, 160), z: Math.floor(Date.now() / 1000) }).then(function () {
        kn.disabled = false; st.innerHTML = 'Gespeichert – sie steht in <a href="konto.html#planen">Mein Bondarium</a> unter „Rechnen und planen“.';
      }, function (j) {
        kn.disabled = false; st.textContent = j && j.status === "voll" ? "Es sind schon " + (j.max || 20) + " Rechnungen gespeichert – lösch erst eine in Mein Bondarium." : "Das Speichern hat nicht geklappt.";
      });
    });
  }

  // ---------- Deine erste Anleihe: Checkliste im Konto ----------
  // Die Seite merkt den Stand im Browser (localStorage). Angemeldet gilt zusätzlich das Konto: Was dort abgehakt ist, wird hier abgehakt;
  // was hier schon abgehakt war, wandert ins Konto; jede Änderung geht an beide.
  function checkliste() {
    var box = document.getElementById("checkliste"); if (!box) return;
    var cbs = Array.prototype.slice.call(box.querySelectorAll('input[type="checkbox"]')), da = K.abl("check"), lauf = Promise.resolve();
    var sende = function (k, an) { lauf = lauf.then(function () { return K.ablage("check", k, an ? 1 : null); }).catch(function () {}); };
    cbs.forEach(function (c) {
      if (!/^[a-z0-9-]{1,40}$/.test(c.value)) return;
      if (da[c.value] !== undefined && !c.checked) { c.checked = true; c.dispatchEvent(new Event("change", { bubbles: true })); }
      else if (c.checked && da[c.value] === undefined) sende(c.value, true);
      c.addEventListener("change", function () { sende(c.value, c.checked); });
    });
    var reset = box.querySelector(".fl-reset");
    if (reset) reset.addEventListener("click", function () { cbs.forEach(function (c) { if (K.abl("check")[c.value] !== undefined) sende(c.value, false); }); });
  }

  // ---------- Nur für Angemeldete ----------
  K.bereit().then(function (st) {
    if (!st.angemeldet) return;
    if (lern) {
      // Lesezeichen je Abschnitt: an jeder Zwischenüberschrift mit Sprungmarke (die des Abschnitts, sonst die eigene)
      Array.prototype.forEach.call(main.querySelectorAll("h2"), function (h) {
        if (h.closest(".mb-seite, .crossnav, .quellen, .weiter") || h.querySelector(".ablbtn") || h.classList.contains("sr-only")) return;
        var sec = h.closest("section[id]"), id = (sec && sec.id) || h.id;
        if (!id || !/^[A-Za-z0-9_-]{1,60}$/.test(id)) return;
        var text = h.textContent.replace(/\s+/g, " ").trim().slice(0, 110);
        h.insertAdjacentHTML("beforeend", " " + K.ablKnopf("lesezeichen", seite + "#" + id, { t: titel, a: text }, ["Lesezeichen für diesen Abschnitt", "Lesezeichen gesetzt – entfernen"], "nur mb-h"));
      });
      angesehen(seite, titel);
    }
    if (seite === "begriffe") {
      Array.prototype.forEach.call(main.querySelectorAll(".gl .e[id]"), function (e) {
        var dt = e.querySelector("dt");
        if (!dt || dt.querySelector(".ablbtn") || !/^[a-z0-9-]{1,40}$/.test(e.id)) return;
        dt.insertAdjacentHTML("beforeend", " " + K.ablKnopf("begriff", e.id, dt.textContent.replace(/\s+/g, " ").trim().slice(0, 70), ["Begriff merken", "Gemerkt – entfernen"], "nur mb-h"));
      });
    }
    if (seite === "rechner") rechner();
    if (seite === "erste-anleihe") checkliste();
    if (KENNZAHL[seite] && !document.getElementById("mb-pin")) {
      var p = document.createElement("p");
      p.className = "mb-pin"; p.id = "mb-pin";
      p.innerHTML = KENNZAHL[seite].map(function (k) { return K.ablKnopf("kennzahl", k[0], 1, ["In meinen Zins-Blick: " + k[1], "Im Zins-Blick: " + k[1]], "klein"); }).join(" ");
      var kopf = main.querySelector(".b2-kopf");
      if (kopf && kopf.parentNode) kopf.parentNode.insertBefore(p, kopf.nextSibling); else main.insertBefore(p, main.firstChild);
      if (zinsen) angesehen(seite, titel);
    }
  });
})(window.MC);
