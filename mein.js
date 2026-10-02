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
