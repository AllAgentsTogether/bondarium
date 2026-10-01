/* konto.js – Benutzerbereich im Browser (seit 30.09.2026): Anmeldung mit E-Mail und Passwort, Merkliste und – seit
   01.10.2026 – das Beispieldepot „Mein Depot“ (gemerkte Anleihen mit gedachtem Nennwert).
   Spricht mit konto.php (Beschreibung dort und in docs/KONTO.md). Geladen auf konto.html, anleihe.html und
   anleihen-suche.html – nach site.js:
     <script src="site.js"></script><script src="konto.js"></script>

   Wer nicht angemeldet ist, löst keine Anfrage an den Server aus: konto.php setzt beim Anmelden neben dem eigentlichen
   Anmelde-Cookie (für Skripte unsichtbar) den Merker „bondarium-angemeldet=1“. Nur wenn er da ist, fragt die Seite den
   Stand ab.

   API (window.MC.konto):
     bereit()                 Promise mit dem Stand { angemeldet, email, favoriten: [[isin, zeit], …],
                              depot: [[isin, nennwert, zeit], …] } – fragt höchstens einmal
     stand()                  derselbe Stand, sofort (vor bereit(): nicht angemeldet)
     hat(isin)                true, wenn die Anleihe in der Merkliste steht
     knopf(isin[, klasse])    HTML des Merken-Knopfs; Klick, Beschriftung und Zustand übernimmt dieses Skript –
                              auch für Knöpfe, die eine Seite später ins Dokument schreibt
     merken(isin), entfernen(isin)            Promise mit dem neuen Stand; abgelehnt mit { status } bei Fehlern
     depot(isin, nennwert)                   ins Beispieldepot legen oder Nennwert ändern (0 = herausnehmen) → wie merken
     uebernehmen(isins)                      geteilte Merkliste (Array von ISINs) auf die eigene setzen → Promise mit der
                                             Antwort { neu, uebrig, max, … }; abgelehnt mit { status } bei Fehlern
     registrieren(email, passwort[, isin])   E-Mail mit Bestätigungslink anfordern → Promise { ok, status, stunden }
     bestaetigen(kennwort, passwort)         Registrierung abschließen (Link aus der E-Mail + Passwort) → { ok, status, gemerkt }
     anmelden(email, passwort[, isin])       → Promise { ok, status, gemerkt }
     vergessen(email)                        E-Mail mit Link für ein neues Passwort → Promise { ok, status, minuten }
     linkPruefen(kennwort)                   gilt der Link noch? → Promise { ok, art: "neu" | "passwort", email }
     passwortNeu(kennwort, passwort)         neues Passwort über den Link setzen → Promise { ok, status }
     passwortAendern(alt, neu)               angemeldet das Passwort ändern → Promise { ok, status }
     abmelden(), loeschen(passwort)          Promise { ok, status }
     Bei ok nach bestaetigen, anmelden und passwortNeu ist man angemeldet (der Stand ist übernommen).
     beiAenderung(fn)         fn(stand) nach jeder Änderung des Stands */
(function (MC) {
  "use strict";
  MC = window.MC = MC || {};

  var API = "konto.php", SEITE = "konto.html";
  var st = { angemeldet: false, email: "", favoriten: [], depot: [] }, menge = {}, hoerer = [], abfrage = null;

  function markiert() { return /(?:^|;\s*)bondarium-angemeldet=1(?:;|$)/.test(document.cookie); }
  function esc(s) { return MC.esc ? MC.esc(s) : String(s).replace(/[&<>"']/g, function (c) { return "&#" + c.charCodeAt(0) + ";"; }); }

  function uebernimm(j) {
    st = { angemeldet: !!(j && j.angemeldet), email: (j && j.email) || "", favoriten: (j && j.angemeldet && j.favoriten) || [], depot: (j && j.angemeldet && j.depot) || [] };
    menge = {};
    st.favoriten.forEach(function (f) { menge[f[0]] = true; });
    knoepfe();
    hoerer.forEach(function (fn) { try { fn(st); } catch (e) { console.warn(e); } });
    return st;
  }

  // Antwort von konto.php → { ok, code, status, … }; Netzfehler → { ok: false, status: "netz" }
  function sende(methode, felder) {
    var opt = { method: methode, credentials: "same-origin", cache: "no-store", headers: { "Accept": "application/json" } }, url = API;
    if (methode === "POST") { opt.headers["X-Requested-With"] = "bondarium-konto"; opt.body = new URLSearchParams(felder); }
    else url += "?" + new URLSearchParams(felder);
    return fetch(url, opt).then(function (r) {
      return r.json().then(function (j) { j = j || {}; j.code = r.status; j.ok = r.ok && j.status === "ok"; return j; });
    }).catch(function () { return { ok: false, code: 0, status: "netz" }; });
  }

  function bereit() {
    if (!abfrage) {
      abfrage = markiert()
        ? sende("GET", { aktion: "status" }).then(function (j) { return j.ok ? uebernimm(j) : st; })
        : Promise.resolve(st);
    }
    return abfrage;
  }

  function aendere(aktion, isin, nennwert) {
    var felder = { aktion: aktion, isin: isin };
    if (nennwert != null) felder.nennwert = String(nennwert);
    return sende("POST", felder).then(function (j) {
      if (j.ok) return uebernimm(j);
      if (j.status === "anmelden") uebernimm(null);   // Anmeldung abgelaufen
      throw j;
    });
  }

  // ---------- Merken-Knopf ----------
  var STERN = '<svg viewBox="0 0 24 24" width="14" height="14" aria-hidden="true" focusable="false"><path d="M12 3.2l2.7 5.6 6.1.8-4.5 4.3 1.1 6.1L12 17.1 6.6 20l1.1-6.1-4.5-4.3 6.1-.8z" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round"/></svg>';
  function inhalt(drin) { return STERN + "<span>" + (drin ? "Gemerkt" : "Merken") + "</span>"; }
  function zeichne(b) {
    var drin = !!menge[b.getAttribute("data-merk")];
    b.setAttribute("aria-pressed", drin ? "true" : "false");
    b.title = drin ? "Von deiner Merkliste nehmen" : "Auf deine Merkliste setzen";
    b.innerHTML = inhalt(drin);
  }
  function knoepfe() { Array.prototype.forEach.call(document.querySelectorAll("button[data-merk]"), zeichne); }
  function knopf(isin, klasse) {
    var drin = !!menge[isin];
    return '<button type="button" class="merkbtn' + (klasse ? " " + esc(klasse) : "") + '" data-merk="' + esc(isin) + '" aria-pressed="' + drin +
      '" title="' + (drin ? "Von deiner Merkliste nehmen" : "Auf deine Merkliste setzen") + '">' + inhalt(drin) + "</button>";
  }
  function melde(text) {
    var el = document.getElementById("merk-status");
    if (!el) {
      el = document.createElement("p"); el.id = "merk-status"; el.className = "sr-only";
      el.setAttribute("role", "status"); el.setAttribute("aria-live", "polite"); document.body.appendChild(el);
    }
    el.textContent = text;
  }
  function klick(b) {
    var isin = b.getAttribute("data-merk");
    if (b.disabled) return;
    b.disabled = true;
    bereit().then(function () {
      if (!st.angemeldet) { location.href = SEITE + "?merken=" + encodeURIComponent(isin); return; }
      var weg = !!menge[isin];
      return aendere(weg ? "entfernen" : "merken", isin).then(function () {
        melde(weg ? "Anleihe " + isin + " von der Merkliste genommen" : "Anleihe " + isin + " auf die Merkliste gesetzt");
      }, function (j) {
        if (j && j.status === "anmelden") { location.href = SEITE + "?merken=" + encodeURIComponent(isin); return; }
        var text = j && j.status === "voll" ? "Merkliste voll (" + (j.max || 200) + " Anleihen)" : "Hat nicht geklappt";
        b.querySelector("span").textContent = text; melde(text);
        setTimeout(function () { zeichne(b); }, 3000);
      });
    }).then(function () { b.disabled = false; });
  }
  document.addEventListener("click", function (e) {
    var b = e.target && e.target.closest ? e.target.closest("button[data-merk]") : null;
    if (b) klick(b);
  });

  // Antwort nach einer Anmeldung bzw. Abmeldung übernehmen: Der Stand gilt sofort, ohne neue Abfrage
  function an(j) { if (j.ok) abfrage = Promise.resolve(uebernimm(j)); return j; }
  function ab(j) { if (j.ok) abfrage = Promise.resolve(uebernimm(null)); return j; }

  MC.konto = {
    bereit: bereit,
    stand: function () { return st; },
    hat: function (isin) { return !!menge[isin]; },
    knopf: knopf,
    merken: function (isin) { return aendere("merken", isin); },
    entfernen: function (isin) { return aendere("entfernen", isin); },
    depot: function (isin, nennwert) { return aendere("depot", isin, nennwert); },
    uebernehmen: function (isins) {
      return sende("POST", { aktion: "uebernehmen", isins: isins.join(",") }).then(function (j) {
        if (j.ok) { uebernimm(j); return j; }
        if (j.status === "anmelden") uebernimm(null);
        throw j;
      });
    },
    registrieren: function (email, passwort, isin, falle) { return sende("POST", { aktion: "registrieren", email: email, passwort: passwort, isin: isin || "", website: falle || "" }); },
    bestaetigen: function (kennwort, passwort) { return sende("POST", { aktion: "bestaetigen", token: kennwort, passwort: passwort }).then(an); },
    anmelden: function (email, passwort, isin) { return sende("POST", { aktion: "anmelden", email: email, passwort: passwort, isin: isin || "" }).then(an); },
    vergessen: function (email, falle) { return sende("POST", { aktion: "vergessen", email: email, website: falle || "" }); },
    linkPruefen: function (kennwort) { return sende("POST", { aktion: "link-pruefen", token: kennwort }); },
    passwortNeu: function (kennwort, passwort) { return sende("POST", { aktion: "passwort-neu", token: kennwort, passwort: passwort }).then(an); },
    passwortAendern: function (alt, neu) { return sende("POST", { aktion: "passwort-aendern", alt: alt, passwort: neu }); },
    abmelden: function () { return sende("POST", { aktion: "abmelden" }).then(ab); },
    loeschen: function (passwort) { return sende("POST", { aktion: "loeschen", passwort: passwort || "" }).then(ab); },
    beiAenderung: function (fn) { hoerer.push(fn); }
  };

  // Stand holen (nur mit Merker, siehe oben) – danach zeigen schon gezeichnete Knöpfe den richtigen Zustand
  bereit();
})(window.MC);
