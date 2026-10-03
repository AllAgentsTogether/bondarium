/* bereich.js – „Mein Bondarium“ in fünf Ansichten (konto.html, seit 02.10.2026 abends; Nutzerauftrag: Mockup vom 01.10.2026 komplett
   umsetzen – 16 Funktionen). Das Seitenskript von konto.html bleibt zuständig für Anmeldung, Merklisten-Tabelle, Filter, Musterdepots
   und PDF; dieses Skript baut darauf auf und zeichnet alles Neue:
     Start                Seit deinem letzten Besuch · „Deine Anleihen“: Merkliste und Musterdepots · „Markt“: Mein Zins-Blick ·
                          Zuletzt angesehen (nur wenn eingeschaltet) – die Termine seit 03.10.2026 aus den Musterdepots statt aus der
                          Merkliste (Nutzerwunsch); seit 03.10.2026 abends nach Herkunft sortiert (Vorschlag „Start neu sortiert“,
                          tmp/Bondarium-Start-neu-sortiert.pdf): jede Zeile im Band trägt ein Etikett mit dem Namen des Reiters bzw.
                          des Musterdepots, die Karte „Musterdepots“ (je Depot eine Zeile, nächste Termine mit Depotname und Betrag)
                          ersetzt „Nächste Termine“, der Zins-Blick steht in voller Breite darunter
     Merkliste            eigene Listen, Notiz, Menü je Anleihe („…“), Vergleichen, ISINs einfügen, CSV, ETFs
     Musterdepots         nichts mehr – die Musterdepots zeichnet das Seitenskript von konto.html
     Meldungen und Konto  Meldungen (Regeln je Anleihe oder für alle gemerkten), Mitnehmen (PDF, CSV, Kalenderdatei), Konto
     Lernen               Lernstand zum Abhaken, Passend zu deiner Merkliste, Lesezeichen, gemerkte Begriffe
   Am 02.10.2026 abends auf Nutzerwunsch wieder entfernt: die Karten „Weiterlernen“ und „Gespeicherte Suchen“ auf Start (damit auch
   „Suche speichern“ und die Meldung „Neue Treffer“), die Etiketten in der Merkliste und „Gespeicherte Rechnungen“; ebenso „Meine Voreinstellungen“ (Ordergebühr, Anlagebetrag,
   Freistellungsauftrag, Startfilter der Suche) – nicht neu einbauen.
   Gespeichert wird nur, was der Nutzer selbst ablegt – in der Ablage des Kontos (konto.php, aktion=ablage; konto.js: MC.konto.ablage).
   Nichts davon ist eine Empfehlung: Etiketten und Meldungen nennen Tatsachen aus den Daten, „Passend zu deiner Merkliste“ zeigt
   Erklärseiten, keine Anleihen. Stile: bereich.css. Beschreibung: docs/KONTO.md, Abschnitt „Mein Bondarium“.

   Aufruf aus konto.html:  const B = MC.bereich(X)  – X ist die Brücke zum Seitenskript:
     K, $, fmt, fmtCoupon, TEXT, hinweis(html, fehler), reiterWahl(ansicht), heute (ISO), jahre(iso), STAMM,
     liste() → gemerkte Anleihen (Objekte aus anleihe()), daten() → Suchindex oder null, kstand(), filter() → Filter der Merkliste,
     ladeDaten(), ladeStamm(isins), anleihe(isin, seit, D), zeichneListe(), entfernen(isin), insDepot(isin), teilen(nurSpeichern)
   Rückgabe: zeige(ansicht), neu(), ablageNeu(art), etfLaden(isins), istEtf(isin), sichtbar(o), zeile*-Helfer für die Tabelle. */
(function (MC) {
  "use strict";
  MC = window.MC = MC || {};
  MC.bereich = function (X) {
    const K = X.K, $ = X.$, esc = MC.esc, fmt = X.fmt, fmtCoupon = X.fmtCoupon, HEUTE = X.heute;
    const zwei = n => (n < 10 ? "0" : "") + n;
    const tagDe = t => new Date(t * 1000).toLocaleDateString("de-DE", { day: "2-digit", month: "2-digit", year: "numeric" });
    const isoVon = t => { const d = new Date(t * 1000); return `${d.getFullYear()}-${zwei(d.getMonth() + 1)}-${zwei(d.getDate())}`; };
    const tageBis = iso => Math.round((Date.parse(iso + "T12:00:00Z") - Date.parse(HEUTE + "T12:00:00Z")) / 86400000);
    // Titel wie überall (felder.js, seit 03.10.2026): Kurzname, Kupon („variabel“, „Nullkupon“), Fälligkeitsjahr
    const titel = o => MC.felder ? MC.felder.titel({ kurz: o.name, kupon: o.kupon, zinsart: o.zinsart, faellig: o.faellig }) : `${o.name} ${fmtCoupon(o.kupon)}${o.faellig ? " " + o.faellig.slice(0, 4) : ""}`;
    const F = MC.felder;
    const abl = art => K.abl(art), wert = (art, k) => K.wert(art, k);
    const neuId = () => Date.now().toString(36) + Math.random().toString(36).slice(2, 6);
    const zahlDe = text => { const n = parseFloat(String(text).replace(/\s|%|€/g, "").replace(/\.(?=\d{3}(\D|$))/g, "").replace(",", ".")); return isFinite(n) ? n : NaN; };
    const plus = (v, dec) => (v > 0 ? "+" : "") + fmt(v, dec == null ? 2 : dec);
    const MONATE = ["Jan", "Feb", "Mär", "Apr", "Mai", "Jun", "Jul", "Aug", "Sep", "Okt", "Nov", "Dez"];
    const fehlerText = a => (a && X.TEXT[a.status]) || (a && a.status === "voll" ? `Hier ist kein Platz mehr (höchstens ${a.max || ""}).` : a && a.status === "wert" ? "Das ist zu lang oder kein gültiger Wert." : X.TEXT.fehler);
    // Speichern in der Ablage; ein Fehler steht im Hinweis oben auf der Seite
    const lege = (art, k, w) => K.ablage(art, k, w).catch(a => { if (a && a.status !== "anmelden") X.hinweis(esc(fehlerText(a)), true); throw a; });
    function lade(name, text, typ) {
      const url = URL.createObjectURL(new Blob([text], { type: typ })), a = document.createElement("a");
      a.href = url; a.download = name; document.body.appendChild(a); a.click(); a.remove();
      setTimeout(() => URL.revokeObjectURL(url), 60000);
    }

    // ---------- Seiten der Akademie: aus dem Menü der Seite (scripts/nav.py) – keine zweite Liste ----------
    const slug = a => (a.getAttribute("href") || "").replace(/^.*\//, "").replace(/\.html.*$/, "");
    const SEITEN_TITEL = {};
    document.querySelectorAll("#sitenav a[href]").forEach(a => { const s = slug(a); if (s && !a.classList.contains("nav-ov") && !a.classList.contains("nav-group-btn") && !SEITEN_TITEL[s]) SEITEN_TITEL[s] = (a.firstChild && a.firstChild.nodeType === 3 ? a.firstChild.textContent : a.textContent).trim(); });
    const GRUPPEN = (() => {
      const g = [];
      document.querySelectorAll("#sitenav .nav-akademie .nav-spalte").forEach(sp => {
        const cap = sp.querySelector(".nav-cap");
        g.push({ name: cap ? cap.textContent.trim() : "", seiten: [...sp.querySelectorAll("a")].map(a => [slug(a), a.textContent.trim()]) });
      });
      const kauf = [...document.querySelectorAll("#sitenav .nav-kaufen .nav-group-menu a")].filter(a => !a.classList.contains("nav-ov") && slug(a) !== "rechner").map(a => [slug(a), a.textContent.trim()]);
      if (kauf.length) g.splice(Math.min(2, g.length), 0, { name: "Kaufen", seiten: kauf });
      return g;
    })();
    const ALLE_SEITEN = [].concat(...GRUPPEN.map(g => g.seiten));
    const gruppeVon = s => { const g = GRUPPEN.find(x => x.seiten.some(p => p[0] === s)); return g ? g.name : document.querySelector(`#sitenav .nav-zinsen a[href^="${s}.html"]`) ? "Zinsen" : ""; };

    // ---------- Etiketten: Tatsachen aus den vorhandenen Daten, keine Wertung ----------
    const kueVon = o => o.r && MC.kuendigung ? MC.kuendigung(o.r[1], typeof o.r[13] === "string" && o.r[13] ? o.r[13][0] : "-", o.r[5], typeof o.r[13] === "string" ? o.r[13].slice(1) : "") : null;
    function etiketten(o) {
      const e = [];
      if (!o.cur) return e;
      const j = o.faellig ? X.jahre(o.faellig) : null;
      if (j != null && j > 0 && j < 1) e.push(["faellig", `fällig in ${MC.restlaufzeit(j)}`, ""]);
      if (o.cur !== "EUR") e.push(["fremd", `Fremdwährung ${o.cur}`, "o"]);
      if (o.kupon === 0) e.push(["null", "Nullkupon", ""]);
      if (o.kupon === "var" || o.zinsart === 1) e.push(["var", "variabel verzinst", ""]);
      const zt = X.STAMM[o.isin] && Array.isArray(X.STAMM[o.isin][14]) ? X.STAMM[o.isin][14] : null;
      if (zt && zt[0] === 2 && zt.length > 1) e.push(["halb", "Zinsen halbjährlich", ""]);
      const k = kueVon(o);
      if (k && "teu".indexOf(k.k) >= 0) e.push(["kuendbar", "kündbar", "o"]);
      if (!o.faellig) e.push(["ewig", "unbefristet", "o"]);
      if (o.kurs == null) e.push(["kurslos", "kein aktueller Kurs", "o"]);
      return e;
    }

    // ---------- ETFs auf der Merkliste: ISIN wie bei Anleihen; Daten aus etf-index.json und etf-kurse.json ----------
    const ETF = new Map();   // ISIN → Zeile aus etf-index.json
    let ETFK = null, ETF_LADEN = null;
    function etfLaden(isins) {
      if (!ETF_LADEN) ETF_LADEN = Promise.all([MC.json("etf-index.json"), MC.json("etf-kurse.json").catch(() => null)]).then(([d, k]) => {
        (d.rows || []).forEach(r => ETF.set(r[0], r)); ETFK = k;
      }).catch(() => { ETF_LADEN = null; });
      return ETF_LADEN.then(() => isins.filter(i => ETF.has(i)));
    }
    const istEtf = i => ETF.has(i);
    const etfListe = () => K.stand().favoriten.filter(f => ETF.has(f[0]));
    function etfZeile(f) {
      const r = ETF.get(f[0]), k = ETFK && ETFK.kurse ? ETFK.kurse[r[0]] : null, kurs = k && typeof k[0] === "number" ? k[0] : null, vor = k && typeof k[6] === "number" ? k[6] : null;
      const d = kurs != null && vor != null ? kurs - vor : null;
      return `<tr><th scope="row"><a href="anleihen-etf.html">${esc(r[1])}</a><small>${esc(r[0])}${r[3] ? " · " + esc(r[3]) : ""}${r[2] ? " · " + esc(r[2]) : ""}</small></th>` +
        `<td data-l="Kategorie">${esc(r[12] || "–")}${r[14] ? `<small>${esc(r[14])}</small>` : ""}</td>` +
        `<td class="num" data-l="Kurs">${kurs != null ? fmt(kurs, 2) : "–"}${d != null && Math.abs(d) >= 0.005 ? `<small class="${d < 0 ? "ab" : "auf"}">${plus(d)}</small>` : ""}</td>` +
        `<td class="num" data-l="Kosten im Jahr">${typeof r[5] === "number" ? fmt(r[5], 2) + " %" : "–"}</td>` +
        `<td data-l="Erträge">${r[6] === 1 ? "ausschüttend" : r[6] === 0 ? "thesaurierend" : "–"}</td>` +
        `<td class="num" data-l="Fondsvermögen">${typeof r[19] === "number" ? (r[19] >= 1000 ? fmt(r[19] / 1000, 1) + " Mrd. €" : fmt(r[19], 0) + " Mio. €") : "–"}</td>` +
        `<td><button type="button" class="kto-x" data-etf-weg="${esc(r[0])}" aria-label="${esc(r[1])} von der Merkliste entfernen" title="Von der Merkliste entfernen">×<span> Entfernen</span></button></td></tr>`;
    }

    // ---------- Merkliste: eigene Listen ----------
    let AKT = "alle", LEDIT = "";   // AKT: alle | anl | etf | <Kennung einer Liste>; LEDIT: "" | neu | name | weg
    const listen = () => Object.entries(abl("liste")).map(([id, e]) => ({ id, n: (e[0] && e[0].n) || "Liste", i: (e[0] && Array.isArray(e[0].i) ? e[0].i : []) }));
    const aktListe = () => listen().find(l => l.id === AKT) || null;
    function sichtbar(o) { if (AKT === "etf") return false; const l = aktListe(); return !l || l.i.indexOf(o.isin) >= 0; }
    function zeichneListen() {
      const box = $("mb-listen"); if (!box) return;
      const fav = K.stand().favoriten, nE = fav.filter(f => ETF.has(f[0])).length, nA = fav.length - nE, ls = listen();
      if (AKT !== "alle" && AKT !== "anl" && AKT !== "etf" && !aktListe()) AKT = "alle";
      if (AKT === "etf" && !nE) AKT = "alle";
      const hat = new Set(fav.map(f => f[0])), pille = (id, name, n) => `<button type="button" class="mb-l" data-liste="${esc(id)}" aria-pressed="${AKT === id}">${esc(name)}<i>${n}</i></button>`;
      const form = art => `<form class="mb-inline" id="mb-l-form" data-art="${art}"><label class="sr-only" for="mb-l-name">Name der Liste</label><input id="mb-l-name" type="text" maxlength="30" autocomplete="off" placeholder="Name, z. B. Beobachten" value="${art === "name" && aktListe() ? esc(aktListe().n) : ""}">` +
        `<button type="submit" class="go">${art === "neu" ? "Anlegen" : "Speichern"}</button><button type="button" class="kto-textbtn" data-l-akt="zu">Abbrechen</button></form>`;
      const l = aktListe();
      box.innerHTML = pille("alle", "Alle", fav.length) + (nE ? pille("anl", "Anleihen", nA) + pille("etf", "ETFs", nE) : "") +
        ls.map(x => LEDIT === "name" && x.id === AKT ? form("name") : pille(x.id, x.n, x.i.filter(i => hat.has(i)).length)).join("") +
        (LEDIT === "neu" ? form("neu") : ls.length < 12 ? '<button type="button" class="mb-l neu" data-l-akt="neu">+ Liste</button>' : "") +
        (l && !LEDIT ? ' <button type="button" class="kto-textbtn" data-l-akt="name">Umbenennen</button> <button type="button" class="kto-textbtn" data-l-akt="weg">Liste löschen</button>' : "") +
        (l && LEDIT === "weg" ? ` <button type="button" class="kto-weg" data-l-akt="weg-ja">„${esc(l.n)}“ löschen</button> <button type="button" class="kto-textbtn" data-l-akt="zu">Abbrechen</button>` : "");
      const f = $("mb-l-name"); if (f) { f.focus(); if (LEDIT === "name") f.select(); }
    }
    function listenKlick(e) {
      const p = e.target.closest("[data-liste]");
      if (p) { AKT = p.dataset.liste; LEDIT = ""; X.zeichneListe(); return; }
      const b = e.target.closest("[data-l-akt]"); if (!b) return;
      const w = b.dataset.lAkt;
      if (w === "weg-ja") { const id = AKT; AKT = "alle"; LEDIT = ""; lege("liste", id, null).catch(() => {}); return; }
      LEDIT = w === "zu" ? "" : w; zeichneListen();
    }
    function listenSubmit(e) {
      if (e.target.id !== "mb-l-form") return;
      e.preventDefault();
      const name = $("mb-l-name").value.replace(/\s+/g, " ").trim().slice(0, 30), art = e.target.dataset.art; if (!name) return;
      const l = aktListe(), id = art === "neu" ? "l" + neuId() : AKT;
      LEDIT = ""; if (art === "neu") AKT = id;
      lege("liste", id, { n: name, i: art === "neu" ? [] : l ? l.i : [] }).catch(() => { AKT = "alle"; });
    }
    // Anleihe einer Liste zuordnen (höchstens einer – wie im Menü je Anleihe); "" nimmt sie aus allen heraus
    function listeSetzen(isin, id) {
      let lauf = Promise.resolve();
      listen().forEach(l => {
        const drin = l.i.indexOf(isin) >= 0;
        if (drin && l.id !== id) lauf = lauf.then(() => K.ablage("liste", l.id, { n: l.n, i: l.i.filter(x => x !== isin) }));
        if (!drin && l.id === id) lauf = lauf.then(() => K.ablage("liste", l.id, { n: l.n, i: l.i.concat([isin]).slice(0, 200) }));
      });
      return lauf;
    }

    // ---------- Merkliste: Zusätze je Zeile ----------
    const VGL = new Set();   // zum Vergleichen angekreuzt (höchstens vier) – nur für diesen Seitenaufruf
    let OFFEN = "";          // ISIN, deren Menü („…“) offen ist
    const klasse = o => (VGL.has(o.isin) ? "gew" : "") + (OFFEN === o.isin ? " offen" : "");
    const zeileKopf = o => `<td class="mb-cb"><input type="checkbox" data-vgl="${esc(o.isin)}"${VGL.has(o.isin) ? " checked" : ""}${!o.cur ? " disabled" : ""} aria-label="${esc(o.name)} vergleichen" title="Zum Vergleichen ankreuzen (bis zu vier)"></td>`;
    // Unter dem Namen steht nur die Notiz. Die Etiketten („fällig in …“, „Zinsen halbjährlich“ …) sind seit 02.10.2026 abends auf
    // Nutzerwunsch aus der Merkliste entfernt; etiketten() dient nur noch „Passend zu deiner Merkliste“ in der Ansicht Lernen.
    function zeileUnter(o) {
      const n = wert("notiz", o.isin);
      return typeof n === "string" && n ? `<span class="mb-notiz">${esc(n)}</span>` : "";
    }
    const delta = o => typeof o.rseit === "number" && typeof o.rendite === "number" ? o.rendite - o.rseit : null;
    function zeileSeit(o) {
      const d = delta(o);
      return (d != null ? `<b class="mb-delta">${F ? F.pkt(d) : plus(d)}</b>` : "–") + `<small data-p="gemerkt">${esc(tagDe(o.seit))}</small>`;
    }
    const termin = o => { const t = (K.stand().termine || {})[o.isin]; return typeof t === "string" && t > HEUTE ? t : (o.kupon === 0 && o.faellig > HEUTE ? "" : null); };   // "" = kein Kupon, null = unbekannt
    function zeileTermin(o) {
      const t = termin(o);
      if (t === "") return "–<small>kein Kupon</small>";
      if (!t) return "–";
      const g = ((K.stand().termine_geschaetzt || {})[o.isin]) ? "geschätzt" : "";
      return esc(MC.datum(t)) + (t === o.faellig ? `<small>mit Rückzahlung${g ? " · " + g : ""}</small>` : g ? `<small>${g}</small>` : "");
    }
    const zeileKnopf = o => `<button type="button" class="mb-pkt" data-mehr="${esc(o.isin)}" aria-expanded="${OFFEN === o.isin}" aria-label="${esc(o.name)}: Notiz, Liste, Meldung und mehr" title="Notiz, Liste, Meldung und mehr">…</button>`;
    const SCHWELLE = { "rendite-ueber": "Rendite steigt über", "rendite-unter": "Rendite fällt unter", "kurs-ueber": "Kurs steigt über", "kurs-unter": "Kurs fällt unter" };
    const meldungVon = isin => Object.entries(abl("meldung")).map(([id, e]) => ({ id, w: e[0] })).find(m => m.w && m.w.i === isin && SCHWELLE[m.w.b]) || null;
    function zeileNach(o) {
      if (OFFEN !== o.isin) return "";
      const m = meldungVon(o.isin), ls = listen(), in_ = ls.find(l => l.i.indexOf(o.isin) >= 0), n = wert("notiz", o.isin) || "";
      const rech = typeof o.kurs === "number" && typeof o.kupon === "number" && o.faellig ? `rechner.html?kurs=${encodeURIComponent(fmt(o.kurs, 2))}&kupon=${encodeURIComponent(fmt(o.kupon, 3).replace(/0$/, ""))}&faellig=${encodeURIComponent(MC.datum(o.faellig))}&w=${encodeURIComponent(o.cur || "EUR")}&isin=${encodeURIComponent(o.isin)}&titel=${encodeURIComponent(titel(o))}#rendite` : "";
      return `<tr class="mb-form-z"><td colspan="9"><div class="mb-form" data-panel="${esc(o.isin)}">` +
        `<div class="mb-form-k"><h3>${esc(titel(o))}: Notiz, Liste, Meldung</h3><p>Alles hier siehst nur du. Die Notiz kommt nicht in das PDF zum Teilen.</p></div>` +
        `<div class="mb-felder"><label class="breit" for="mb-p-notiz">Notiz<input type="text" id="mb-p-notiz" maxlength="200" autocomplete="off" value="${esc(n)}"></label>` +
        `<label for="mb-p-liste">Liste<select id="mb-p-liste"><option value="">keine Liste</option>${ls.map(l => `<option value="${esc(l.id)}"${in_ && in_.id === l.id ? " selected" : ""}>${esc(l.n)}</option>`).join("")}</select></label>` +
        `<label for="mb-p-b">Melden, wenn<select id="mb-p-b"><option value="">keine Meldung</option>${Object.keys(SCHWELLE).map(k => `<option value="${k}"${m && m.w.b === k ? " selected" : ""}>${SCHWELLE[k]}</option>`).join("")}</select></label>` +
        `<label for="mb-p-w">Schwelle<input type="text" id="mb-p-w" inputmode="decimal" autocomplete="off" placeholder="z. B. 4,00" value="${m && typeof m.w.w === "number" ? fmt(m.w.w, 2) : ""}"></label>` +
        `<label for="mb-p-m">Nachricht<select id="mb-p-m"><option value="1"${m && !m.w.m ? "" : " selected"}>E-Mail</option><option value="0"${m && !m.w.m ? " selected" : ""}>nur im Bereich</option></select></label></div>` +
        `<ul class="mb-menue"><li><a href="anleihe.html?isin=${encodeURIComponent(o.isin)}">Steckbrief öffnen</a></li>` +
        (rech ? `<li><a href="${rech}">Im Rechner öffnen</a></li>` : "") +
        `<li><button type="button" data-p="depot">In ein Musterdepot legen</button></li>` +
        (termin(o) || o.faellig > HEUTE ? `<li><button type="button" data-p="ics">Termine in den Kalender</button></li>` : "") +
        `<li><button type="button" class="rot" data-p="weg">Von der Merkliste entfernen</button></li>` +
        `<li><small>${esc([o.isin, o.cur, typeof o.stk === "number" && F ? "Stückelung " + F.stueckelung(o.stk, o.cur) : "", typeof o.vol === "number" && F ? "Volumen " + F.volumen(o.vol, o.cur) : "", F && F.bonitaet(o.bon) ? "Bonität laut EZB " + F.bonitaet(o.bon) : ""].filter(Boolean).join(" · "))}</small></li></ul>` +
        `<div class="mb-form-a"><button type="button" class="go" data-p="speichern">Speichern</button><button type="button" class="kto-textbtn" data-p="zu">Abbrechen</button><p class="kf-status" id="mb-p-status" role="status" aria-live="polite"></p></div>` +
        `</div></td></tr>`;
    }
    let SPEICHERT = false;
    function panelSpeichern(isin) {
      const st = $("mb-p-status"), notiz = $("mb-p-notiz").value.replace(/\s+/g, " ").trim().slice(0, 200), liste = $("mb-p-liste").value, b = $("mb-p-b").value, per = $("mb-p-m").value === "1" ? 1 : 0;
      const w = zahlDe($("mb-p-w").value), alt = meldungVon(isin);
      if (b && isNaN(w)) { st.className = "kf-status fehler"; st.textContent = "Bitte eine Schwelle als Zahl eintragen, zum Beispiel 4,00."; return; }
      st.className = "kf-status"; st.textContent = "Einen Moment …"; SPEICHERT = true;
      let lauf = Promise.resolve();
      if (notiz !== (wert("notiz", isin) || "")) lauf = lauf.then(() => K.ablage("notiz", isin, notiz || null));
      lauf = lauf.then(() => listeSetzen(isin, liste));
      if (b) { if (!alt || alt.w.b !== b || alt.w.w !== w || (alt.w.m ? 1 : 0) !== per) lauf = lauf.then(() => K.ablage("meldung", alt ? alt.id : "m" + neuId(), { i: isin, b, w, m: per, an: 1 })); }
      else if (alt) lauf = lauf.then(() => K.ablage("meldung", alt.id, null));
      lauf.then(() => { SPEICHERT = false; OFFEN = ""; alles(); }, a => {
        SPEICHERT = false; if (a && a.status === "anmelden") return;
        const s = $("mb-p-status"); if (s) { s.className = "kf-status fehler"; s.textContent = fehlerText(a); }
      });
    }
    function zeilenKlick(e) {
      const m = e.target.closest("[data-mehr]");
      if (m) { OFFEN = OFFEN === m.dataset.mehr ? "" : m.dataset.mehr; X.zeichneListe(); const f = $("mb-p-notiz"); if (f) f.focus(); return; }
      const p = e.target.closest("[data-p]"); if (!p) return;
      const isin = p.closest("[data-panel]").dataset.panel, o = X.liste().find(x => x.isin === isin), w = p.dataset.p;
      if (w === "zu") { OFFEN = ""; X.zeichneListe(); }
      else if (w === "speichern") panelSpeichern(isin);
      else if (w === "weg") { OFFEN = ""; VGL.delete(isin); X.entfernen(isin); }
      else if (w === "depot") { OFFEN = ""; X.insDepot(isin); X.zeichneListe(); }
      else if (w === "ics" && o) kalender([o]);
    }
    function zeilenChange(e) {
      const c = e.target.closest("[data-vgl]"); if (!c) return;
      if (c.checked) { if (VGL.size >= 4) { c.checked = false; X.hinweis("Vergleichen lassen sich höchstens vier Anleihen."); return; } VGL.add(c.dataset.vgl); } else VGL.delete(c.dataset.vgl);
      const tr = c.closest("tr"); if (tr) tr.classList.toggle("gew", c.checked);
      zeichneVergleich(); zeichneAkt();
    }

    // ---------- Merkliste: Aktionen (Vergleichen, ISINs einfügen, CSV) ----------
    function zeichneAkt() {
      const b = $("mb-vgl-btn"); if (!b) return;
      b.textContent = `Vergleichen (${VGL.size})`; b.classList.toggle("an", VGL.size >= 2);
    }
    function csv() {
      const z = v => { v = v == null ? "" : String(v); return /[";\n]/.test(v) ? `"${v.replace(/"/g, '""')}"` : v; }, n = (v, d) => typeof v === "number" ? v.toLocaleString("de-DE", { minimumFractionDigits: d, maximumFractionDigits: d, useGrouping: false }) : "";
      // Seit 03.10.2026 Spalten wie die Tabelle in Langform mit Einheit (Konzept „Einheitliche Anleihen-Angaben“, Kapitel 5.5)
      const kopf = ["Anleihe", "ISIN", "Art", "Währung", "Rendite bis Fälligkeit in %", "Kupon in %", "Restlaufzeit in Jahren", "Fälligkeit", "Kurs in %", "Kurs vom",
        "Veränderung zum Vortag in Pkt.", "Rendite seit dem Merken in Pkt.", "Gemerkt am", "Nächster Zinstermin", "ETF: Kurs je Anteil"];
      const ART = ["Staat", "Öffentlich", "Unternehmen"], jahreBis = iso => (Date.parse(iso + "T12:00:00Z") - Date.parse(HEUTE + "T12:00:00Z")) / (365.25 * 864e5);
      const zeilen = X.liste().map(o => [o.name, o.isin, ART[o.art] || "", o.cur, n(o.rendite, 2),
        o.zinsart === 1 || o.kupon === "var" ? "variabel" : typeof o.kupon === "number" ? n(o.kupon, 3) : "", o.faellig ? n(Math.max(0, jahreBis(o.faellig)), 1) : "",
        o.faellig ? MC.datum(o.faellig) : "", n(o.kurs, 2), o.datum ? MC.datum(o.datum) : "",
        typeof o.kurs === "number" && typeof o.vortag === "number" ? n(o.kurs - o.vortag, 2) : "", delta(o) != null ? n(delta(o), 2) : "", tagDe(o.seit), termin(o) ? MC.datum(termin(o)) : "", ""]);
      etfListe().forEach(f => { const r = ETF.get(f[0]), k = ETFK && ETFK.kurse ? ETFK.kurse[f[0]] : null; zeilen.push([r[1], r[0], "ETF", r[9] || "", "", "", "", "", "", "", "", "", tagDe(f[1]), "", k && typeof k[0] === "number" ? n(k[0], 2) : ""]); });
      lade(`Bondarium-Merkliste-${HEUTE}.csv`, "﻿" + [kopf].concat(zeilen).map(r => r.map(z).join(";")).join("\r\n") + "\r\n", "text/csv;charset=utf-8");
    }
    // Kalenderdatei (.ics): nächster Zinstermin und Fälligkeit je Anleihe als ganztägige Termine – entsteht im Browser
    function kalender(liste) {
      const t = s => String(s).replace(/([\\;,])/g, "\\$1").replace(/\n/g, "\\n"), d = iso => iso.replace(/-/g, ""), morgen = iso => { const x = new Date(iso + "T12:00:00Z"); x.setUTCDate(x.getUTCDate() + 1); return x.toISOString().slice(0, 10).replace(/-/g, ""); };
      const jetzt = new Date().toISOString().replace(/[-:]/g, "").replace(/\.\d+/, ""), ev = [];
      liste.forEach(o => {
        const zt = naechster(o), url = `https://www.bondarium.de/anleihe.html?isin=${o.isin}`;
        const eintrag = (art, tag, text) => ev.push(["BEGIN:VEVENT", `UID:${art}-${o.isin}-${d(tag)}@bondarium.de`, `DTSTAMP:${jetzt}`, `DTSTART;VALUE=DATE:${d(tag)}`, `DTEND;VALUE=DATE:${morgen(tag)}`,
          `SUMMARY:${t(text)}`, `DESCRIPTION:${t(`${o.isin} – Termin laut Bondarium, maßgeblich sind die Anleihebedingungen. ${url}`)}`, `URL:${url}`, "TRANSP:TRANSPARENT", "END:VEVENT"].join("\r\n"));
        if (zt && zt !== o.faellig) eintrag("zins", zt, `Zinstermin: ${titel(o)}`);
        if (o.faellig && o.faellig > HEUTE) eintrag("faellig", o.faellig, `Fälligkeit${zt === o.faellig ? " und letzter Zinstermin" : ""}: ${titel(o)}`);
      });
      if (!ev.length) { X.hinweis("Für diese Auswahl gibt es keinen kommenden Termin."); return; }
      lade(liste.length === 1 ? `Bondarium-Termine-${liste[0].isin}.ics` : `Bondarium-Termine-${HEUTE}.ics`,
        ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//Bondarium//Mein Bondarium//DE", "CALSCALE:GREGORIAN", "X-WR-CALNAME:Bondarium – Termine"].concat(ev, ["END:VCALENDAR"]).join("\r\n") + "\r\n", "text/calendar;charset=utf-8");
    }
    function einfuegen(e) {
      e.preventDefault();
      const st = $("mb-einf-status"), isins = [...new Set(($("mb-einf-t").value.toUpperCase().match(/[A-Z]{2}[A-Z0-9]{9}\d/g) || []))].slice(0, 200);
      if (!isins.length) { st.textContent = "Keine ISIN gefunden – eine ISIN hat zwölf Zeichen, zum Beispiel DE0001102424."; return; }
      st.textContent = "Wird geprüft …";
      X.ladeDaten().then(D => X.ladeStamm(isins.filter(i => !D.idx.has(i))).then(() => etfLaden(isins)).then(() => D)).then(D => {
        const bekannt = isins.filter(i => D.idx.has(i) || X.STAMM[i] || ETF.has(i)), neu = bekannt.filter(i => !K.hat(i)), fremd = isins.length - bekannt.length;
        if (!neu.length) { st.textContent = bekannt.length ? "Alles davon steht schon auf deiner Merkliste." + (fremd ? ` ${fremd} ${fremd === 1 ? "ISIN kennt" : "ISINs kennt"} Bondarium nicht.` : "") : "Keine dieser ISINs kennt Bondarium."; return; }
        return K.uebernehmen(neu).then(a => {
          $("mb-einf-t").value = ""; $("mb-einf").hidden = true; st.textContent = "";
          X.hinweis(`${a.neu === 1 ? "1 Wertpapier ist" : a.neu + " Wertpapiere sind"} neu auf deiner Merkliste.` + (fremd ? ` ${fremd} ${fremd === 1 ? "ISIN kennt" : "ISINs kennt"} Bondarium nicht.` : "") + (a.uebrig ? ` ${a.uebrig} passten nicht mehr – die Merkliste fasst höchstens ${a.max || 200}.` : ""));
          K.besuch().catch(() => {});   // holt die Zinstermine der neuen Anleihen
        });
      }).catch(a => { st.textContent = fehlerText(a); });
    }

    // ---------- Merkliste: Vergleich (bis zu vier angekreuzte Anleihen nebeneinander, mit Kursverlauf über ein Jahr) ----------
    const VFARBEN = ["#157C00", "#1A1A19", "#DD803D", "#76756D"];
    let VLAUF = 0;
    const VZT = {};   // ISIN → Zinstermine aus anleihen/<teil>.json (Feld 14: [Zahlungen je Jahr, "MM-TT", …]) für die Duration im Vergleich
    function zeichneVergleich() {
      const box = $("mb-vgl"); if (!box) return;
      const ls = X.liste().filter(o => VGL.has(o.isin));
      [...VGL].forEach(i => { if (!ls.some(o => o.isin === i)) VGL.delete(i); });
      box.hidden = ls.length < 2; if (ls.length < 2) { box.innerHTML = ""; return; }
      const fehlt = ls.filter(o => !(o.isin in VZT));
      if (fehlt.length) {   // einmal nachladen (MC.json hält jede Datei nur einmal), danach mit Duration zeichnen
        fehlt.forEach(o => { VZT[o.isin] = null; });
        Promise.all(fehlt.map(o => MC.json(`anleihen/${MC.teil(o.isin)}.json`).then(d => { const r = d && d.rows && d.rows[o.isin]; VZT[o.isin] = r && Array.isArray(r[14]) ? r[14] : null; }, () => {})))
          .then(() => { if (!box.hidden) zeichneVergleich(); });
      }
      // Seit 03.10.2026 Angaben in der Reihenfolge der Gesamtliste und in Langform (Konzept „Einheitliche Anleihen-Angaben“, felder.js);
      // laufende Verzinsung und Duration wie in den Musterdepots gerechnet (Zinstermine aus den Stammdaten, Valuta zwei Börsentage)
      const zeile = (name, f) => `<tr><th scope="row">${name}</th>${ls.map(o => `<td>${f(o)}</td>`).join("")}</tr>`;
      const klein = t => t ? `<small style="display:block;color:var(--text);font-size:12.5px">${t}</small>` : "";
      const kue = o => { const k = kueVon(o); if (!k || !MC.kuendigungFeld) return "–"; const f = MC.kuendigungFeld(k, o.kurs); return esc(f.wert) + klein(f.klein); };
      const valuta = (() => { const x = new Date(HEUTE + "T12:00:00Z"); let n = 2; while (n) { x.setUTCDate(x.getUTCDate() + 1); if (x.getUTCDay() % 6) n--; } return x.toISOString().slice(0, 10); })();
      const kennz = o => {   // laufende Verzinsung, Duration (Macaulay), modifizierte Duration
        const fest = o.zinsart === 0 && typeof o.kupon === "number", out = { lfd: fest && o.kurs > 0 && !/infl/i.test(o.reg || "") ? o.kupon / o.kurs * 100 : null, mac: null, dur: null };
        const zt = VZT[o.isin];
        if (zt !== undefined && o.rendite != null && o.faellig && o.faellig > valuta && (fest || o.zinsart === 2) && MC.bond) {
          try { const d = MC.bond.duration({ coupon: fest ? o.kupon : 0, freq: Array.isArray(zt) && zt[0] > 0 ? zt[0] : 1, maturity: o.faellig, days: Array.isArray(zt) && zt.length > 1 ? zt.slice(1) : null }, o.rendite / 100, valuta); out.mac = d.macaulay; out.dur = d.modified; } catch (e) { /* ohne Duration */ }
        }
        return out;
      };
      const zinsenJahr = o => o.zinsart === 1 || o.kupon === "var" ? "variabel" : o.zinsart === 2 || o.kupon === 0 ? "keine (Nullkupon)" : typeof o.kupon === "number" ? F.betrag(o.kupon * 10, o.cur) : "–";
      box.innerHTML = `<div class="mb-kh"><h2 class="mb-h2">Vergleich</h2><p>${ls.length} gewählt · bis zu 4 möglich · <button type="button" class="kto-textbtn" id="mb-vgl-leer">Auswahl aufheben</button></p></div>` +
        `<div class="mb-vgl-g"><div class="table-scroll"><table class="mb-vt"><thead><tr><td></td>${ls.map((o, i) => `<th scope="col"><i style="background:${VFARBEN[i]}"></i><a href="anleihe.html?isin=${encodeURIComponent(o.isin)}">${esc(titel(o))}</a>${klein(esc([o.isin, ["Staat", "Öffentlich", "Unternehmen"][o.art] || "", o.cur].filter(Boolean).join(" · ")))}</th>`).join("")}</tr></thead><tbody>` +
        zeile("Rendite bis Fälligkeit", o => o.rendite != null ? F.pct(o.rendite) : "–") +
        zeile("Kupon", o => esc(F.kupon({ kupon: o.kupon, zinsart: o.zinsart }))) +
        zeile("Laufende Verzinsung", o => F.pct(kennz(o).lfd)) +
        zeile("Restlaufzeit", o => o.faellig ? esc(F.restlaufzeit(o.faellig)) + klein("fällig " + esc(MC.datum(o.faellig))) : "unbefristet") +
        zeile("Duration", o => { const k = kennz(o); return k.mac != null ? esc(F.restlaufzeit(k.mac)) + klein("mod. Duration " + fmt(k.dur, 1)) : "–"; }) +
        zeile("Risikoaufschlag zu Bund", o => typeof o.auf === "number" && o.rendite != null ? F.pkt(o.auf) : "–") +
        zeile("Kurs", o => o.kurs != null ? F.kurs(o.kurs) + klein(o.datum ? "vom " + esc(MC.datum(o.datum)) : "") : "–") +
        zeile("Bonität laut EZB", o => esc(F.bonitaet(o.bon) || "keine Angabe")) +
        zeile("Kündigungsrecht Emittent", kue) +
        zeile("Stückelung (Mindestanlage)", o => F.stueckelung(o.stk, o.cur)) +
        zeile("Volumen", o => F.volumen(o.vol, o.cur)) +
        zeile("Zinsen pro Jahr je 1.000", zinsenJahr) +
        `</tbody></table></div><div><p class="mb-zk" style="margin-top:0">Kursverlauf, 1 Jahr</p><div id="mb-vgl-bild"><p class="mb-leer">Kurse werden geladen …</p></div></div></div>`;
      const nr = ++VLAUF, ab = (() => { const d = new Date(HEUTE + "T12:00:00Z"); d.setUTCFullYear(d.getUTCFullYear() - 1); return d.toISOString().slice(0, 10); })();
      Promise.all(ls.map(o => MC.verlauf(o.isin, true, { ab }).catch(() => ({ t: [], k: [] })))).then(v => {
        if (nr !== VLAUF || !$("mb-vgl-bild")) return;
        const alle = [].concat(...v.map(x => x.k)).filter(k => typeof k === "number");
        if (alle.length < 2) { $("mb-vgl-bild").innerHTML = '<p class="mb-leer">Für diese Auswahl gibt es keinen Kursverlauf.</p>'; return; }
        // Die Achse beginnt beim ersten vorhandenen Kurs (höchstens ein Jahr zurück) – so steht eine kurze Kursreihe nicht als Strich am Rand
        const erster = v.map(x => x.t[0]).filter(Boolean).sort()[0] || ab, kurz = tageBis(erster) > -330;
        const W = 420, H = 190, L = 6, R = 34, O = 10, U = 24, lo = Math.min(...alle), hi = Math.max(...alle), sp = hi - lo || 1, t0 = Date.parse(erster), t1 = Date.parse(HEUTE);
        const x = t => L + (W - L - R) * Math.min(1, Math.max(0, (Date.parse(t) - t0) / (t1 - t0 || 1))), y = k => O + (H - O - U) * (1 - (k - lo) / sp);
        let s = `<svg class="mb-svg" viewBox="0 0 ${W} ${H}" role="img" aria-label="Kursverlauf der gewählten Anleihen über ein Jahr">`;
        [lo, (lo + hi) / 2, hi].forEach(k => { s += `<line x1="${L}" y1="${y(k).toFixed(1)}" x2="${W - R}" y2="${y(k).toFixed(1)}" stroke="#E4E3DF"/><text x="${W - R + 5}" y="${(y(k) + 4).toFixed(1)}">${fmt(k, 0)}</text>`; });
        v.forEach((reihe, i) => {
          const pts = reihe.t.map((t, j) => typeof reihe.k[j] === "number" ? `${x(t).toFixed(1)},${y(reihe.k[j]).toFixed(1)}` : "").filter(Boolean);
          if (pts.length > 1) s += `<polyline points="${pts.join(" ")}" fill="none" stroke="${VFARBEN[i]}" stroke-width="2" stroke-linejoin="round" stroke-linecap="round"><title>${esc(titel(ls[i]))}</title></polyline>`;
        });
        const m = iso => `${MONATE[+iso.slice(5, 7) - 1]} ${iso.slice(0, 4)}`;
        s += `<text x="${L}" y="${H - 6}">${kurz ? esc(MC.datum(erster)) : m(erster)}</text><text x="${W - R}" y="${H - 6}" text-anchor="end">${kurz ? esc(MC.datum(HEUTE)) : m(HEUTE)}</text></svg>`;
        $("mb-vgl-bild").innerHTML = s + (kurz ? `<p class="mb-klein">Kurse seit ${esc(MC.datum(erster))} – länger reicht die Kursreihe dieser Auswahl nicht zurück.</p>` : "");
      });
    }

    // ---------- Mein Zins-Blick: angeheftete Kennzahlen (Knopf auf den Zinsen-Seiten, mein.js – dieselben Kennungen) ----------
    const pct = v => fmt(v, 2) + " %", KZ = {
      bund10: { t: "Bundesanleihe 10 Jahre", s: "renditen.html", f: "renditen.json", w: d => { const l = d.countries.de.latest; return [pct(l.yield), "Stand " + MC.datum(l.date)]; } },
      us10: { t: "US-Staatsanleihe 10 Jahre", s: "renditen.html", f: "renditen.json", w: d => { const l = d.countries.us.latest; return [pct(l.yield), "Stand " + MC.datum(l.date)]; } },
      kurve: { t: "Zinskurve 10 J. minus 2 J.", s: "zinskurve.html", f: "zinskurve.json", w: d => { const h = d.heute.DE; return [plus(h[2] - h[1]) + "\u00a0Pkt.", `2 J. ${pct(h[1])} · 10 J. ${pct(h[2])}`]; } },
      ezb: { t: "EZB-Einlagesatz", s: "zinsniveau.html", f: "ezb.json", w: d => [pct(d.aktuell[1]), "seit " + MC.datum(d.aktuell[0])] },
      realzins: { t: "Realzins 10 Jahre", s: "realzins.html", f: "realzins.json", w: d => [pct(d.heute.zins10[1] - d.heute.vpi[1]), `Zins ${pct(d.heute.zins10[1])} − Inflation ${fmt(d.heute.vpi[1], 1)} %`] },
      "aufschlag-it": { t: "Risikoaufschlag Italien", s: "risikoaufschlaege.html", f: "risikoaufschlaege.json", w: d => { const h = d.laender.heute.find(x => x.code === "IT"); return [fmt(h.aufschlag, 2) + "\u00a0Pkt.", "über Bund, 10 Jahre"]; } },
      "aufschlag-fr": { t: "Risikoaufschlag Frankreich", s: "risikoaufschlaege.html", f: "risikoaufschlaege.json", w: d => { const h = d.laender.heute.find(x => x.code === "FR"); return [fmt(h.aufschlag, 2) + "\u00a0Pkt.", "über Bund, 10 Jahre"]; } },
      "aufschlag-us": { t: "Aufschlag US-Unternehmen", s: "risikoaufschlaege.html", f: "risikoaufschlaege.json", w: d => [fmt(d.us.heute[1], 2) + "\u00a0Pkt.", "über US-Staatsanleihen"] },
      bund2050: { t: "Bundesanleihe 2050", s: "langlaeufer.html", f: "langlaeufer.json", w: d => { const l = d.bonds.bund2050.latest; return [F ? F.kurs(l.price) : fmt(l.price, 2), `Kurs · Rendite ${pct(l.yield)}`]; } },
    };
    let KZLAUF = 0;
    function zinsBlick(el) {
      const ids = Object.keys(abl("kennzahl")).filter(k => KZ[k]).slice(0, 6), nr = ++KZLAUF;
      if (!ids.length) { el.innerHTML = '<p class="mb-leer">Noch nichts angeheftet. Auf den Seiten unter <a href="beobachten.html">Zinsen</a> steht der Knopf „In meinen Zins-Blick“ – ein Klick heftet die Kennzahl hier an.</p>'; return; }
      const kachel = (k, w) => `<a class="mb-zk-k" href="${KZ[k].s}"><span>${esc(KZ[k].t)}</span><b>${w ? esc(w[0]) : "–"}</b><small>${w ? esc(w[1]) : "gerade nicht erreichbar"}</small></a>`;
      el.innerHTML = `<div class="mb-zk-g">${ids.map(k => kachel(k, null)).join("")}</div>`;
      Promise.all(ids.map(k => MC.json(KZ[k].f).then(d => { try { return KZ[k].w(d); } catch (e) { return null; } }, () => null))).then(w => {
        if (nr === KZLAUF) el.innerHTML = `<div class="mb-zk-g">${ids.map((k, i) => kachel(k, w[i])).join("")}</div>`;
      });
    }

    // ---------- Lernstand ----------
    const gelesen = s => abl("gelesen")[s] !== undefined;
    const naechste = () => ALLE_SEITEN.find(p => !gelesen(p[0])) || null;
    const balken = (n, von, gross) => `<div class="mb-jb${gross ? " gross" : ""}"><i style="width:${von ? Math.round(100 * n / von) : 0}%"></i></div>`;

    // ---------- Termine: der Musterdepots (Start, seit 03.10.2026 – Nutzerwunsch) oder der Merkliste (Meldung „Zinstermin steht an“) ----------
    // Die Anleihen der Musterdepots bringen ihren nächsten Zinstermin mit (zt, berechnet wie in der Depot-Tabelle; X.depotAnleihen()).
    const naechster = o => o.zt !== undefined ? o.zt : termin(o);
    // Termine der Musterdepots (seit 03.10.2026 abends): je Depot und Anleihe der nächste Zinstermin und die Fälligkeit, mit dem Betrag
    // aus der Zahlungsliste des Depots (X.zahlungen – in Euro, Fremdwährung zum EZB-Kurs wie im Reiter „Musterdepots“); Anleihen, die
    // sich nicht rechnen lassen (variabler Zins …), nur mit der Fälligkeit
    function depotTermine(d) {
      const z = X.zahlungen(d.pos), t = [], dep = { id: d.id, name: d.name };
      d.pos.forEach(p => {
        const o = Object.assign({}, p.o, { gesch: p.fest && !p.tage }), meine = z.filter(x => x.p === p);
        const zins = meine.find(x => x.art === "Zinsen"), rueck = meine.find(x => x.art === "Rückzahlung"), mit = !!(zins && rueck && zins.tag === rueck.tag);
        if (zins) t.push({ tag: zins.tag, o, p, dep, art: mit ? "Zinsen und Rückzahlung" : "Zinstermin", betrag: zins.betrag + (mit ? rueck.betrag : 0), roh: zins.roh + (mit ? rueck.roh : 0) });
        if (rueck && !mit) t.push({ tag: rueck.tag, o, p, dep, art: "Fälligkeit", betrag: rueck.betrag, roh: rueck.roh });
        if (!p.rechnet && o.faellig && o.faellig > HEUTE) t.push({ tag: o.faellig, o, p, dep, art: "Fälligkeit", betrag: p.nennEur, roh: p.nenn });
      });
      return t;
    }
    function termine(max, merk) {
      const t = [];
      if (!merk) (X.depots() || []).forEach(d => t.push(...depotTermine(d)));
      else X.liste().forEach(o => {
        const zt = naechster(o);
        if (zt) t.push({ tag: zt, o, art: zt === o.faellig ? "Zinsen und Rückzahlung" : "Zinstermin" });
        if (o.faellig && o.faellig > HEUTE && zt !== o.faellig) t.push({ tag: o.faellig, o, art: "Fälligkeit" });
      });
      return t.sort((a, b) => a.tag < b.tag ? -1 : a.tag > b.tag ? 1 : a.o.isin.localeCompare(b.o.isin) || (a.dep && b.dep ? a.dep.name.localeCompare(b.dep.name, "de") : 0)).slice(0, max);
    }

    // ---------- Meldungen ----------
    const MART = Object.assign({ termin: "Zinstermin steht an", kurslos: "Seit 14 Tagen kein Kurs mehr oder Daten fraglich" }, SCHWELLE);
    const meldungen = () => Object.entries(abl("meldung")).map(([id, e]) => ({ id, w: e[0] || {} })).filter(m => MART[m.w.b]);
    // Stand einer Meldung: { wer, was, stand (HTML), aktiv (jetzt ausgelöst) }
    function meldungStand(m, D) {
      const w = m.w, an = !!w.an, aus = an ? "" : "Ausgeschaltet";
      if (SCHWELLE[w.b]) {
        const o = X.liste().find(x => x.isin === w.i) || (D ? X.anleihe(w.i, 0, D) : null), rend = w.b.indexOf("rendite") === 0, v = o ? (rend ? o.rendite : o.kurs) : null;
        const zahl = v != null ? (rend ? `Rendite ${F.pct(v)}` : `Kurs ${F.kurs(v)}`) : "kein aktueller Wert";
        const erf = v != null && (/ueber$/.test(w.b) ? v > w.w : v < w.w);
        return { wer: o && o.cur ? titel(o) : w.i, was: `${SCHWELLE[w.b]} ${rend ? F.pct(w.w) : F.kurs(w.w)}`, aktiv: an && (erf || !!w.a),
          stand: !an ? `${aus} · letzter Stand: ${zahl}` : w.a ? `<em>Ausgelöst am ${esc(MC.datum(w.a))}</em> · ${typeof w.aw === "number" ? (rend ? `Rendite ${F.pct(w.aw)}` : `Kurs ${F.kurs(w.aw)}`) : zahl}` : erf ? `<em>Bedingung erfüllt</em> · ${zahl}` : `Aktiv · ${zahl}` };
      }
      if (w.b === "termin") {
        const t = termine(9999, true).filter(x => x.art === "Zinstermin")[0], nah = t && tageBis(t.tag) <= 7;   // seit 03.10.2026 nur Zinstermine
        return { wer: "Alle gemerkten Anleihen", was: MART.termin, aktiv: an && !!nah,
          stand: !an ? aus : `${nah ? `<em>In ${tageBis(t.tag)} ${tageBis(t.tag) === 1 ? "Tag" : "Tagen"}</em>` : "7 Tage vorher"} · ${t ? `nächster: ${esc(titel(t.o))}, ${esc(MC.datum(t.tag))}` : "derzeit kein Termin bekannt"}` };
      }
      const ohne = X.liste().filter(o => o.cur && (o.kurs == null || o.befund) && !(o.faellig && o.faellig <= HEUTE));
      return { wer: "Alle gemerkten Anleihen", was: MART.kurslos, aktiv: an && ohne.length > 0, stand: !an ? aus : ohne.length ? `<em>${ohne.length} ${ohne.length === 1 ? "Anleihe" : "Anleihen"}</em> · ${esc(ohne.slice(0, 3).map(titel).join(", "))}${ohne.length > 3 ? " …" : ""}` : "Aktiv · derzeit keine" };
    }
    function zeichneMeldungen() {
      const box = $("mb-meld"); if (!box) return;
      const D = X.daten(), ms = meldungen(), ls = X.liste().filter(o => o.cur);
      const liste = ms.length ? `<ul class="mb-alarme">${ms.map(m => { const s = meldungStand(m, D), an = !!m.w.an;
        return `<li${an ? "" : ' class="aus"'}><button type="button" class="mb-schalter" role="switch" aria-checked="${an}" data-m-an="${esc(m.id)}" aria-label="${esc(s.wer)}: ${esc(s.was)} – Meldung ${an ? "ausschalten" : "einschalten"}"></button>` +
          `<div><b>${esc(s.wer)}</b><span>${esc(s.was)}</span></div><p class="mb-weg"><span>${m.w.m ? "E-Mail" : "nur im Bereich"}</span><button type="button" class="mb-x" data-m-weg="${esc(m.id)}" aria-label="Meldung löschen" title="Meldung löschen">×</button></p><p class="mb-stand">${s.stand}</p></li>`; }).join("")}</ul>`
        : '<p class="mb-leer">Noch keine Meldung. Leg unten eine an – zum Beispiel „Rendite steigt über 4,00 %“ für eine gemerkte Anleihe oder „Zinstermin steht an“ für alle.</p>';
      box.innerHTML = `<div class="mb-kh"><h2 class="mb-h2">Meldungen</h2><p>geprüft an jedem Börsentag nach dem Datenlauf</p></div>${liste}` +
        `<form class="mb-neu-a" id="mb-m-form"><p class="mb-zk">Neue Meldung</p><div class="mb-felder">` +
        `<label for="mb-m-i">Anleihe<select id="mb-m-i"><option value="*">Alle gemerkten Anleihen</option>${ls.map(o => `<option value="${esc(o.isin)}">${esc(titel(o))}</option>`).join("")}</select></label>` +
        `<label for="mb-m-b">Wenn<select id="mb-m-b"></select></label>` +
        `<label for="mb-m-w">Wert<input type="text" id="mb-m-w" inputmode="decimal" autocomplete="off" placeholder="z. B. 4,25"></label>` +
        `<label for="mb-m-m">Nachricht<select id="mb-m-m"><option value="1">E-Mail</option><option value="0">nur im Bereich</option></select></label></div>` +
        `<button type="submit" class="go">Meldung anlegen</button><p class="kf-status" id="mb-m-status" role="status" aria-live="polite"></p>` +
        `<p class="mb-klein">E-Mails gehen an ${esc(K.stand().email)} – nur für Meldungen mit „E-Mail“, höchstens eine am Tag, jede mit einem Link zum Ausschalten. „Nur im Bereich“ zeigt die Meldung beim nächsten Besuch hier und auf „Start“. Fälligkeiten kommen über „Vor Fälligkeit“ in der Karte „E-Mails an dich“.</p></form>`;
      meldungFormular();
      // Karte „E-Mails an dich“ (konto.html, seit 03.10.2026): Zahl der Meldungen, die per E-Mail kommen
      const em = $("em-meld");
      if (em) {
        const an = ms.filter(m => m.w.an), mail = an.filter(m => m.w.m).length;
        em.textContent = !ms.length ? "Noch keine Meldung angelegt." : !an.length ? "Alle Meldungen sind ausgeschaltet."
          : an.length === 1 ? (mail ? "Deine Meldung kommt per E-Mail – höchstens eine E-Mail am Tag." : "Deine Meldung steht nur im Bereich, nicht per E-Mail.")
          : `${mail} von ${an.length} Meldungen ${mail === 1 ? "kommt" : "kommen"} per E-Mail – höchstens eine E-Mail am Tag.`;
      }
    }
    function meldungFormular() {
      const i = $("mb-m-i"), b = $("mb-m-b"); if (!i || !b) return;
      const arten = i.value === "*" ? ["termin", "kurslos"] : Object.keys(SCHWELLE), alt = b.value;
      b.innerHTML = arten.map(k => `<option value="${k}">${esc(MART[k])}${k === "termin" ? " (7 Tage vorher)" : ""}</option>`).join("");
      if (arten.indexOf(alt) >= 0) b.value = alt;
      const schwelle = !!SCHWELLE[b.value], nurBereich = b.value === "kurslos";
      $("mb-m-w").disabled = !schwelle; $("mb-m-w").placeholder = schwelle ? (b.value.indexOf("kurs") === 0 ? "z. B. 98,50" : "z. B. 4,25") : "–"; if (!schwelle) $("mb-m-w").value = "";
      $("mb-m-m").disabled = nurBereich; if (nurBereich) $("mb-m-m").value = "0";
    }
    function meldungAnlegen(e) {
      e.preventDefault();
      const st = $("mb-m-status"), i = $("mb-m-i").value, b = $("mb-m-b").value, w = zahlDe($("mb-m-w").value), per = $("mb-m-m").value === "1" ? 1 : 0;
      if (SCHWELLE[b] && isNaN(w)) { st.className = "kf-status fehler"; st.textContent = "Bitte einen Wert als Zahl eintragen, zum Beispiel 4,25."; return; }
      if (!SCHWELLE[b] && meldungen().some(m => m.w.b === b)) { st.className = "kf-status fehler"; st.textContent = "Diese Meldung gibt es schon."; return; }
      st.className = "kf-status"; st.textContent = "Einen Moment …";
      const neu = SCHWELLE[b] ? { i, b, w, m: per, an: 1 } : { i: "*", b, m: b === "termin" ? per : 0, an: 1 };
      K.ablage("meldung", "m" + neuId(), neu).catch(a => { const s = $("mb-m-status"); if (s) { s.className = "kf-status fehler"; s.textContent = fehlerText(a); } });
    }
    function meldungKlick(e) {
      const s = e.target.closest("[data-m-an]");
      if (s) { const m = meldungen().find(x => x.id === s.dataset.mAn); if (m) { const w = Object.assign({}, m.w, { an: m.w.an ? 0 : 1 }); delete w.a; delete w.aw; s.disabled = true; lege("meldung", m.id, w).catch(() => {}); } return; }
      const x = e.target.closest("[data-m-weg]"); if (x) { x.disabled = true; lege("meldung", x.dataset.mWeg, null).catch(() => {}); }
    }
    const meldungenAktiv = D => meldungen().filter(m => meldungStand(m, D).aktiv);

    // ---------- Ansicht „Start“ (seit 03.10.2026 abends nach Herkunft sortiert: erst deins, dann der Markt) ----------
    // Zeichen für Etiketten und Kartenköpfe: Stern = Merkliste, Mappe = Musterdepot, Kupon-Punkt = Neu auf Bondarium, Linie = Zinsen
    const ICON = {
      stern: '<svg viewBox="0 0 16 16" aria-hidden="true" focusable="false" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round"><path d="M8 1.6l1.9 4 4.3.5-3.2 3 .9 4.3L8 11.2l-3.9 2.2.9-4.3-3.2-3 4.3-.5z"/></svg>',
      mappe: '<svg viewBox="0 0 16 16" aria-hidden="true" focusable="false" fill="none" stroke="currentColor" stroke-width="1.6"><rect x="2" y="4" width="12" height="9" rx="1.5"/><path d="M5.5 4V2.8h5V4"/></svg>',
      punkt: '<svg viewBox="0 0 16 16" aria-hidden="true" focusable="false"><circle cx="8" cy="8" r="5" fill="#39FF14" stroke="#1A1A19" stroke-width="1.6"/></svg>',
      linie: '<svg viewBox="0 0 16 16" aria-hidden="true" focusable="false" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M2 12l4-4 3 2.5L14 4"/></svg>',
    };
    const etikett = (ic, text, alarm) => `<span class="mb-her${alarm ? " alarm" : ""}" title="${esc(text)}">${ICON[ic]}<span>${esc(text)}</span></span>`;
    // Beträge auf Start: Euro ganz, wenn glatt; umgerechnete Fremdwährung mit „≈“ und ganz
    const euro = (v, ca) => (ca ? "≈ " : "") + fmt(v, ca || Math.abs(v - Math.round(v)) < 0.005 ? 0 : 2) + " €";
    const roh = (v, cur) => `${fmt(v, Math.abs(v - Math.round(v)) < 0.005 ? 0 : 2)} ${cur}`;
    const IN12 = (+HEUTE.slice(0, 4) + 1) + HEUTE.slice(4);
    function seitBesuch(D) {
      const st = K.stand(), seit = st.besuch ? isoVon(st.besuch) : "", zeilen = [];
      meldungenAktiv(D).forEach(m => { const s = meldungStand(m, D); zeilen.push([etikett("stern", "Merkliste", true), `<b>Meldung: ${esc(s.wer)}</b> – ${esc(s.was)}. ${s.stand.replace(/<\/?em>/g, "")}`, '<button type="button" data-zu="meldungen">Zur Meldung</button>']); });
      termine(40).filter(t => tageBis(t.tag) <= 14).slice(0, 3).forEach(t => { const n = tageBis(t.tag), b = t.betrag != null ? euro(t.betrag, t.p.fremd) : "";
        const was = t.art === "Fälligkeit" ? `wird am ${esc(MC.tag(t.tag))} zurückgezahlt${b ? ` – ${b}` : ""}.` : t.art === "Zinstermin" ? `zahlt am ${esc(MC.tag(t.tag))} Zinsen${b ? ` – ${b}` : ""}.` : `zahlt am ${esc(MC.tag(t.tag))} Zinsen und den Nennwert zurück${b ? ` – ${b}` : ""}.`;
        zeilen.push([etikett("mappe", t.dep.name), `<b>${t.art === "Fälligkeit" ? "Fälligkeit" : "Zinstermin"} ${n <= 0 ? "heute" : n === 1 ? "morgen" : `in ${n} Tagen`}:</b> ${esc(titel(t.o))} ${was}`, `<button type="button" data-mdepot="${esc(t.dep.id)}">Zum Musterdepot</button>`]); });
      const ab = seit || (() => { const d = new Date(HEUTE + "T12:00:00Z"); d.setUTCDate(d.getUTCDate() - 14); return d.toISOString().slice(0, 10); })();
      Object.entries(st.neueSeiten || {}).filter(([f, tag]) => tag >= ab && SEITEN_TITEL[f.replace(/\.html$/, "")] && !gelesen(f.replace(/\.html$/, ""))).slice(0, 2)
        .forEach(([f]) => zeilen.push([etikett("punkt", "Neu auf Bondarium"), `<b>${esc(SEITEN_TITEL[f.replace(/\.html$/, "")])}</b>`, `<a href="${esc(f)}">Lesen</a>`]));
      const kopf = st.besuch ? `Seit deinem letzten Besuch <small>am ${esc(tagDe(st.besuch))}</small>` : "Willkommen in deinem Bereich";
      if (!zeilen.length) zeilen.push(["", st.besuch ? "Nichts Neues – keine Meldung und kein Termin in den nächsten 14 Tagen." : "Hier steht künftig, was sich seit deinem letzten Besuch getan hat: ausgelöste Meldungen, anstehende Zinstermine und neue Seiten.", ""]);
      return `<section class="mb-neu" aria-labelledby="mb-h-neu"><h2 class="mb-h2" id="mb-h-neu">${kopf}</h2><ul>${zeilen.map(z => `<li>${z[0] || "<span></span>"}<span>${z[1]}</span>${z[2]}</li>`).join("")}</ul></section>`;
    }
    const dach = (t, u) => `<p class="mb-dz"><b>${t}</b><span>${u}</span></p>`;
    const kartenKopf = (ic, t, rechts, unter) => `<div class="mb-kh"><h2 class="mb-h2 mb-hi">${ICON[ic]}${t}</h2><p>${rechts}</p></div><p class="mb-unter">${unter}</p>`;
    // Karte „Merkliste“: bis zu vier Anleihen – zuerst die größten Änderungen der Rendite seit dem Merken, aufgefüllt mit den zuletzt
    // gemerkten (dann mit Kurs); heute gemerkte zeigen „gemerkt heute“ statt einer Änderung von 0,00
    function merkKarte(st, ls, nE) {
      const heuteGem = o => isoVon(o.seit) === HEUTE;
      const mitD = ls.filter(o => delta(o) != null && !heuteGem(o) && Math.abs(delta(o)) >= 0.005).sort((a, b) => Math.abs(delta(b)) - Math.abs(delta(a)));
      const top = mitD.concat(ls.filter(o => mitD.indexOf(o) < 0).sort((a, b) => b.seit - a.seit)).slice(0, 4), weitere = ls.length - top.length;
      const zeile = o => { const d = mitD.indexOf(o) >= 0 ? delta(o) : null;
        return `<li><div><a href="anleihe.html?isin=${encodeURIComponent(o.isin)}">${esc(titel(o))}</a><span>${heuteGem(o) ? "gemerkt heute" : "gemerkt " + esc(tagDe(o.seit))}</span></div><p><b>${o.rendite != null ? "Rendite " + F.pct(o.rendite) : "–"}</b><span>${d != null ? `${F.pkt(d)} seit dem Merken` : o.kurs != null ? `Kurs ${F.kurs(o.kurs)}` : ""}</span></p></li>`; };
      return `<section class="mb-karte">` + kartenKopf("stern", "Merkliste", `${ls.length} ${ls.length === 1 ? "Anleihe" : "Anleihen"}${nE ? ` · ${nE} ${nE === 1 ? "ETF" : "ETFs"}` : ""}`, `Beobachtet, ohne Beträge${mitD.length ? " · größte Änderung seit dem Merken zuerst" : ""}`) +
        (top.length ? `<ul class="mb-mini">${top.map(zeile).join("")}</ul>${weitere > 0 ? `<p class="mb-weitere">und ${weitere} weitere</p>` : ""}`
          : st.favoriten.length ? '<p class="mb-leer">Kurse werden geladen …</p>' : '<p class="mb-leer">Noch nichts gemerkt. In der <a href="anleihen-suche.html">Anleihen-Suche</a> und auf jedem Steckbrief steht der Knopf „Merken“.</p>') +
        `<p class="mb-fuss"><span>${X.kstand() ? "Schlusskurse vom " + esc(MC.datum(X.kstand())) : ""}</span><button type="button" class="kto-textbtn" data-zu="merkliste">Zur Merkliste</button></p></section>`;
    }
    // Karte „Musterdepots“ (ersetzt „Nächste Termine“): je Depot Anleihen, Nennwert und Zinsen der nächsten zwölf Monate (in Euro),
    // darunter die nächsten drei Termine aller Depots mit Depotname und Betrag
    function depotKarte(st) {
      const deps = X.depots(), nD = [].concat(...(st.depots || []).map(d => d[2])).length, zahl = (st.depots || []).length || 1;
      const kopf = kartenKopf("mappe", "Musterdepots", `${zahl} ${zahl === 1 ? "Depot" : "Depots"}`, "Planspiel mit gedachten Beträgen");
      let inhalt;
      if (!nD) inhalt = '<p class="mb-leer">Sobald in deinen Musterdepots Anleihen liegen, stehen hier ihr Nennwert, die Zinsen der nächsten zwölf Monate und die nächsten Termine. Hinzufügen mit „+“ in der Merkliste oder auf jedem Steckbrief.</p>';
      else if (!deps) inhalt = '<p class="mb-leer">Musterdepots werden geladen …</p>';
      else {
        const zeilen = deps.map(d => {
          const nenn = d.pos.filter(p => p.nennEur != null), fremd = d.pos.some(p => p.fremd), z = X.zahlungen(d.pos).filter(x => x.art === "Zinsen" && x.tag < IN12);
          const ohne = d.pos.filter(p => !p.rechnet && !(p.o.faellig && p.o.faellig <= HEUTE)).length;
          return `<tr><th scope="row"><button type="button" class="mb-dlink" data-mdepot="${esc(d.id)}">${esc(d.name)}</button></th><td>${d.pos.length}</td>` +
            `<td>${nenn.length ? euro(nenn.reduce((a, p) => a + p.nennEur, 0), fremd) : "–"}</td>` +
            `<td${ohne ? ` title="${esc(`ohne ${ohne === 1 ? "eine Anleihe" : ohne + " Anleihen"} mit variablem oder unbekanntem Zins`)}"` : ""}>${d.pos.length && (z.length || ohne < d.pos.length) ? euro(z.reduce((a, x) => a + x.betrag, 0), fremd || ohne > 0) : "–"}</td></tr>`;
        }).join("");
        const t = termine(3);
        inhalt = `<table class="mb-dep"><thead><tr><th scope="col">Depot</th><th scope="col">Anleihen</th><th scope="col">Nennwert</th><th scope="col">Zinsen 12 Mon.</th></tr></thead><tbody>${zeilen}</tbody></table>` +
          `<p class="mb-zk">Nächste Termine</p>` +
          (t.length ? `<ul class="mb-termine">${t.map(x => { const n = tageBis(x.tag);
            return `<li><span class="mb-tag"><b>${+x.tag.slice(8, 10)}</b>${MONATE[+x.tag.slice(5, 7) - 1]} ${x.tag.slice(2, 4)}</span><div><b>${esc(titel(x.o))}</b><span class="mb-dn">${esc(x.dep.name)}</span>${esc(x.art)}${n <= 30 ? ` · ${n <= 0 ? "heute" : n === 1 ? "morgen" : `in ${n} Tagen`}` : ""}</div>` +
              `<p class="mb-betrag">${x.betrag != null ? euro(x.betrag, x.p.fremd) : ""}<span>${x.betrag == null ? "" : x.p.fremd ? `${roh(x.roh, x.p.o.cur)} · EZB-Kurs` : `auf ${fmt(x.p.nenn, 0)} €`}</span></p></li>`; }).join("")}</ul>`
            : '<p class="mb-leer">Für die Anleihen in deinen Musterdepots ist kein kommender Termin bekannt.</p>');
        return `<section class="mb-karte">${kopf}${inhalt}<p class="mb-fuss"><span>Zinstermine laut Deutscher Börse${t.some(x => x.o.gesch && x.art !== "Fälligkeit") ? ", teils geschätzt" : ""}</span><span class="mb-fr">${t.length ? '<button type="button" class="kto-textbtn" data-ics="depot">Kalender (.ics)</button>' : ""}<button type="button" class="kto-textbtn" data-zu="depot">Zu den Musterdepots</button></span></p></section>`;
      }
      return `<section class="mb-karte">${kopf}${inhalt}<p class="mb-fuss"><span></span><button type="button" class="kto-textbtn" data-zu="depot">Zu den Musterdepots</button></p></section>`;
    }
    function zeichneStart() {
      const el = $("a-start"); if (!el) return;
      const D = X.daten(), st = K.stand(), ls = X.liste(), nE = etfListe().length, nZ = Object.keys(abl("kennzahl")).filter(k => KZ[k]).slice(0, 6).length;
      const zins = `<section class="mb-karte mb-zinsblick">` + kartenKopf("linie", "Mein Zins-Blick", nZ ? `${nZ} angeheftet` : "", "Marktzahlen, die du auf den Zinsen-Seiten angeheftet hast") +
        `<div id="mb-zins"></div><p class="mb-fuss"><span>${nZ ? "Ein Klick auf eine Kachel öffnet die Seite dazu" : ""}</span><a href="beobachten.html">Alle Zinsen</a></p></section>`;
      const an = wert("einstellung", "zuletzt") === 1, ang = Object.entries(abl("angesehen")).sort((a, b) => b[1][1] - a[1][1]);
      const zuletzt = an && ang.length ? `<div class="mb-zuletzt"><p class="mb-zk">Zuletzt angesehen</p><p class="mb-chips-a">${ang.map(([k, e]) => `<a href="${/^[A-Z]{2}/.test(k) ? "anleihe.html?isin=" + encodeURIComponent(k) : esc(k) + ".html"}">${esc(typeof e[0] === "string" && e[0] ? e[0] : k)}</a>`).join("")}</p></div>` : "";
      el.innerHTML = seitBesuch(D) + dach("Deine Anleihen", "was du beobachtest und was du durchspielst") + `<div class="mb-reihe">${merkKarte(st, ls, nE)}${depotKarte(st)}</div>` +
        dach("Markt", "gilt für alle – hängt nicht an deinen Anleihen") + zins + zuletzt;
      zinsBlick($("mb-zins"));
    }

    // ---------- Ansicht „Lernen“ ----------
    const PASSEND = [   // Etikett → Erklärseite (Seite, Titel, Satz); gezeigt wird, was zur Merkliste passt – Erklärseiten, keine Anleihen
      ["fremd", "risiko", "Risiko kennen: Wenn die Währung schwankt", n => `Du hast ${n === 1 ? "eine Anleihe" : n + " Anleihen"} in fremder Währung gemerkt.`],
      ["null", "anleihe-arten", "Anleihe-Arten: Nullkupon-Anleihe", n => `Du hast ${n === 1 ? "eine Nullkupon-Anleihe" : n + " Nullkupon-Anleihen"} gemerkt.`],
      ["kuendbar", "kuendbare-anleihen", "Kündbar ist nicht gleich kündbar", n => `${n === 1 ? "Eine deiner Anleihen kann" : n + " deiner Anleihen können"} vor der Fälligkeit gekündigt werden.`],
      ["var", "anleihe-arten", "Anleihe-Arten: variabel verzinst", n => `Du hast ${n === 1 ? "eine variabel verzinste Anleihe" : n + " variabel verzinste Anleihen"} gemerkt.`],
      ["lang", "duration", "Duration: Wie stark der Kurs auf Zinsen reagiert", n => `${n === 1 ? "Eine deiner Anleihen läuft" : n + " deiner Anleihen laufen"} noch länger als zehn Jahre.`],
      ["firma", "bonitaet", "Bonität und Ratings", n => `Du hast ${n === 1 ? "eine Unternehmensanleihe" : n + " Unternehmensanleihen"} gemerkt.`],
      ["etf", "etf-oder-anleihe", "ETF oder Anleihe?", () => "Du hast Anleihen und ETFs gemerkt."],
    ];
    function passend() {
      const ls = X.liste(), zahl = {};
      ls.forEach(o => { etiketten(o).forEach(e => { zahl[e[0]] = (zahl[e[0]] || 0) + 1; }); if (o.faellig && X.jahre(o.faellig) > 10) zahl.lang = (zahl.lang || 0) + 1; if (o.art === 2) zahl.firma = (zahl.firma || 0) + 1; });
      if (etfListe().length && ls.length) zahl.etf = 1;
      const CHIP = { fremd: ["Fremdwährung", "o"], null: ["Nullkupon", ""], kuendbar: ["kündbar", "o"], var: ["variabel", ""], lang: ["lange Laufzeit", ""], firma: ["Unternehmen", ""], etf: ["ETF", ""] };
      const z = PASSEND.filter(p => zahl[p[0]] && SEITEN_TITEL[p[1]]).slice(0, 5);
      if (!z.length) return `<p class="mb-leer">${ls.length ? "Zu deiner Merkliste gibt es gerade keinen besonderen Lesetipp." : "Sobald du Anleihen gemerkt hast, stehen hier die Erklärseiten, die zu ihnen passen – zum Beispiel zum Währungsrisiko, wenn du eine Dollar-Anleihe merkst."}</p>`;
      return `<ul class="mb-passend">${z.map(p => `<li><span class="mb-chip${CHIP[p[0]][1] ? " " + CHIP[p[0]][1] : ""}">${CHIP[p[0]][0]}</span><div><a href="${p[1]}.html">${esc(p[2])}</a><span>${esc(p[3](zahl[p[0]]))}${gelesen(p[1]) ? "<em>Gelesen</em>" : ""}</span></div></li>`).join("")}</ul>`;
    }
    function zeichneLernen() {
      const el = $("a-lernen"); if (!el) return;
      const n = ALLE_SEITEN.filter(p => gelesen(p[0])).length, nx = naechste(), check = Object.keys(abl("check")).length;
      const kopf = `<div class="mb-fort"><div><p class="mb-k">Mein Lernstand</p><h2>${n} von ${ALLE_SEITEN.length} Seiten gelesen</h2>${balken(n, ALLE_SEITEN.length, true)}</div>` +
        (nx ? `<div class="mb-fort-w"><p><span>Weiter mit</span><b>${esc(nx[1])}</b><small>${esc(gruppeVon(nx[0]))}</small></p><a class="go" href="${esc(nx[0])}.html">Weiterlesen</a></div>`
          : `<div class="mb-fort-w"><p><span>Geschafft</span><b>Alle Seiten abgehakt</b><small>Neue Seiten erscheinen hier von selbst.</small></p></div>`) + `</div>`;
      const stufen = `<div class="mb-vier">${GRUPPEN.map(g => { const k = g.seiten.filter(p => gelesen(p[0])).length;
        return `<section class="mb-karte mb-stufe"><div class="mb-kh"><h2 class="mb-h2">${esc(g.name)}</h2><p>${k} von ${g.seiten.length}</p></div>${balken(k, g.seiten.length)}<ul class="mb-haken">${g.seiten.map(p => {
          const ok = gelesen(p[0]), next = nx && nx[0] === p[0];
          return `<li class="${ok ? "ok" : next ? "next" : ""}"><button type="button" class="mb-hk" data-gelesen="${esc(p[0])}" aria-pressed="${ok}" aria-label="${esc(p[1])}: ${ok ? "als ungelesen markieren" : "als gelesen markieren"}" title="${ok ? "Gelesen – Klick nimmt den Haken weg" : "Als gelesen markieren"}"></button>` +
            `<span><a href="${esc(p[0])}.html">${esc(p[1])}</a>${next ? "<em>Weiter</em>" : ""}${p[0] === "erste-anleihe" && check ? `<small>Checkliste: ${check} ${check === 1 ? "Schritt" : "Schritte"} abgehakt</small>` : ""}</span></li>`; }).join("")}</ul></section>`; }).join("")}</div>`;
      const lz = Object.entries(abl("lesezeichen")).sort((a, b) => b[1][1] - a[1][1]), bg = Object.entries(abl("begriff")).sort((a, b) => String(a[1][0]).localeCompare(String(b[1][0]), "de"));
      const lesez = `<section class="mb-karte"><div class="mb-kh"><h2 class="mb-h2">Lesezeichen</h2><p>Seiten und Abschnitte</p></div>` +
        (lz.length ? `<ul class="mb-lz">${lz.map(([k, e]) => { const w = e[0] || {}, s = k.split("#")[0], g = gruppeVon(s);
          return `<li><div><a href="${esc(s)}.html${k.indexOf("#") > 0 ? "#" + esc(k.split("#")[1]) : ""}">${esc(w.t || SEITEN_TITEL[s] || s)}</a>${w.a ? `<span>Abschnitt „${esc(w.a)}“</span>` : ""}</div><span class="mb-r">${g ? `<span class="mb-chip">${esc(g)}</span>` : ""}<button type="button" class="mb-x" data-lz-weg="${esc(k)}" aria-label="Lesezeichen entfernen" title="Lesezeichen entfernen">×</button></span></li>`; }).join("")}</ul>`
          : '<p class="mb-leer">Noch kein Lesezeichen. Am Ende jeder Seite der Akademie steht der Knopf „Lesezeichen“, an jeder Zwischenüberschrift ein kleines Lesezeichen für den Abschnitt.</p>') + `</section>`;
      const begr = `<section class="mb-karte"><div class="mb-kh"><h2 class="mb-h2">Gemerkte Begriffe</h2><p>aus dem Glossar</p></div>` +
        (bg.length ? `<p class="mb-chips-a">${bg.map(([k, e]) => `<span><a href="begriffe.html#${esc(k)}" style="border:0;padding:0;background:none">${esc(typeof e[0] === "string" && e[0] ? e[0] : k)}</a><button type="button" data-bg-weg="${esc(k)}" aria-label="Begriff entfernen" title="Begriff entfernen">×</button></span>`).join("")}</p>`
          : '<p class="mb-leer">Noch kein Begriff gemerkt. Im <a href="begriffe.html">Glossar</a> steht an jedem Begriff ein Stern.</p>') + `</section>`;
      el.innerHTML = kopf + stufen + `<div class="mb-zwei e"><section class="mb-karte"><div class="mb-kh"><h2 class="mb-h2">Passend zu deiner Merkliste</h2><p>aus dem, was du gemerkt hast</p></div>${passend()}</section><div class="mb-sp">${lesez}${begr}</div></div>`;
    }

    // ---------- Ansicht „Meldungen und Konto“: Konto-Zeilen (Markup in konto.html) ----------
    function zeichneKonto() {
      const st = K.stand(); if (!$("mb-k-email")) return;
      $("mb-k-email").textContent = st.email;
      const g = st.geraete || [], hier = g.find(x => x[2]), andere = g.filter(x => !x[2]);
      $("mb-k-geraete").textContent = (hier ? `Dieses Gerät: ${hier[0]}` : "Dieses Gerät") + (andere.length ? " · " + andere.map(x => `${x[0]}, zuletzt ${tagDe(x[1])}`).join(" · ") : " · sonst keines");
      $("mb-k-geraete-ab").hidden = !andere.length;
      const an = wert("einstellung", "zuletzt") === 1, s = $("mb-k-zuletzt");
      s.setAttribute("aria-checked", String(an));
      $("mb-k-zuletzt-t").textContent = an ? "Eingeschaltet: Dein Konto merkt sich die acht zuletzt geöffneten Steckbriefe und Akademie-Seiten und zeigt sie auf „Start“."
        : "Ausgeschaltet. Eingeschaltet merkt sich dein Konto die acht zuletzt geöffneten Steckbriefe und Akademie-Seiten.";
    }
    function kontoKlick(e) {
      const auf = e.target.closest("[data-auf]");
      if (auf) { const d = $(auf.dataset.auf); if (d) { if (d.tagName === "DETAILS") d.open = !d.open; else d.hidden = !d.hidden; const f = d.querySelector("input:not([tabindex='-1'])"); if (f && (d.open || d.hidden === false)) f.focus(); } return; }
      if (e.target.closest("#mb-k-geraete-ab")) {
        const b = e.target.closest("button"); b.disabled = true;
        K.geraeteAb().then(() => { b.disabled = false; X.hinweis("Alle anderen Geräte sind abgemeldet."); }, a => { b.disabled = false; if (a && a.status !== "anmelden") X.hinweis(esc(fehlerText(a)), true); });
        return;
      }
      if (e.target.closest("#mb-k-zuletzt")) {
        const an = wert("einstellung", "zuletzt") === 1;
        // Ausschalten löscht auch, was gemerkt wurde
        let lauf = K.ablage("einstellung", "zuletzt", an ? null : 1);
        if (an) Object.keys(abl("angesehen")).forEach(k => { lauf = lauf.then(() => K.ablage("angesehen", k, null)); });
        lauf.catch(a => { if (a && a.status !== "anmelden") X.hinweis(esc(fehlerText(a)), true); });
        return;
      }
      if (e.target.closest("#mb-k-export")) {
        K.exportieren().then(a => {
          if (!a.ok) { X.hinweis(esc(fehlerText(a)), true); return; }
          lade(`Bondarium-Meine-Daten-${HEUTE}.json`, JSON.stringify(a.daten, null, 2), "application/json");
        });
      }
    }
    function emailFormular() {
      const f = $("f-email"); if (!f) return;
      f.addEventListener("submit", e => {
        e.preventDefault();
        if (!f.checkValidity()) { f.reportValidity(); return; }
        const st = f.querySelector(".kf-status"), knopf = f.querySelector("button[type=submit]"), neu = f.email.value.trim();
        knopf.disabled = true; st.className = "kf-status"; st.textContent = "Einen Moment …";
        K.emailAendern(neu, f.passwort.value).then(a => {
          knopf.disabled = false;
          if (a.ok) { f.reset(); f.hidden = true; st.textContent = ""; X.hinweis(`<b>Schau in das Postfach von ${esc(neu)}.</b> Dort liegt ein Link – erst wenn du ihn anklickst, gilt die neue Adresse. Er gilt ${a.stunden || 24} Stunden.`); return; }
          st.className = "kf-status fehler";
          st.textContent = a.status === "zugang" ? "Das Passwort stimmt nicht." : a.status === "gleich" ? "Das ist schon die Adresse deines Kontos." : a.status === "zuviel" ? "Für diese Adresse wurden gerade schon mehrere E-Mails angefordert. Bitte versuch es später noch einmal." : fehlerText(a);
        });
      });
    }
    // Links aus E-Mails: konto.html#email=<Kennwort> (neue Adresse bestätigen) und #meldungen-aus=<Kennung> (keine Meldungen mehr
    // per E-Mail). Der Teil hinter „#“ geht nicht an den Server und wird sofort aus der Adresse genommen.
    function ausLink() {
      let m = /^#email=([A-Za-z0-9_-]{43})$/.exec(location.hash);
      if (m) {
        try { history.replaceState(null, "", location.pathname); } catch (e) {}
        K.emailBestaetigen(m[1]).then(a => X.hinweis(a.ok ? `<b>Deine E-Mail-Adresse ist geändert.</b> ${a.email ? "" : "Melde dich ab jetzt mit der neuen Adresse an. "}Alle anderen Geräte sind abgemeldet.`
          : a.status === "link" ? "Dieser Link ist abgelaufen oder wurde schon benutzt. Fordere die Änderung in „Meldungen und Konto“ noch einmal an." : esc(fehlerText(a)), !a.ok));
        return;
      }
      m = /^#meldungen-aus=(\d{1,10}\.[0-9a-f]{32})$/.exec(location.hash);
      if (m) {
        try { history.replaceState(null, "", location.pathname); } catch (e) {}
        K.meldungenAus(m[1]).then(a => X.hinweis(a.ok ? "<b>Du bekommst keine E-Mails mehr zu Meldungen.</b> Die Meldungen bleiben und stehen weiter in deinem Bereich – dort kannst du sie auch wieder auf „E-Mail“ stellen."
          : a.status === "link" ? "Dieser Link gilt nicht mehr – vielleicht ist das Konto gelöscht. Angemeldet findest du die Meldungen unter „Meldungen und Konto“." : esc(fehlerText(a)), !a.ok));
      }
    }

    // ---------- Zeichnen ----------
    let ANSICHT = "start";
    function zeichneMerkliste() {
      zeichneListen(); zeichneAkt();
      const e = etfListe(), box = $("mb-etf"), l = aktListe();
      if (box) {
        const zeig = e.filter(f => AKT !== "anl" && (!l || l.i.indexOf(f[0]) >= 0));
        box.hidden = !zeig.length;
        if (zeig.length) $("mb-etf-zeilen").innerHTML = zeig.map(etfZeile).join("");
      }
      const t = $("liste"); if (t && X.liste().length) t.hidden = AKT === "etf";
      zeichneVergleich();
    }
    function kopfZahlen() {
      const n = K.stand().favoriten.length, a = meldungenAktiv(X.daten()).length;
      if ($("r-merk-n")) $("r-merk-n").textContent = n || "";
      if ($("t-meld-n")) $("t-meld-n").textContent = a || "";
    }
    function alles() {
      if (SPEICHERT || !K.stand().angemeldet) return;
      kopfZahlen();
      if (ANSICHT === "start") zeichneStart();
      else if (ANSICHT === "merkliste") X.zeichneListe();
      else if (ANSICHT === "lernen") zeichneLernen();
      else if (ANSICHT === "meldungen") { zeichneMeldungen(); zeichneKonto(); }
    }
    function zeige(a) { ANSICHT = a; const d = $("depot"); if (d) d.dataset.ansicht = a; alles(); }
    // Meldungen brauchen den Suchindex – auch wenn die Merkliste leer ist
    function datenFuerSuchen() { if (!X.daten() && meldungen().length && K.stand().angemeldet) X.neuLaden(); }

    // ---------- Ereignisse ----------
    const depot = $("depot");
    depot.addEventListener("click", e => {
      const zu = e.target.closest("[data-zu]"); if (zu && depot.contains(zu)) { X.reiterWahl(zu.dataset.zu, true); window.scrollTo({ top: Math.max(0, depot.getBoundingClientRect().top + window.scrollY - 90) }); return; }
      const dp = e.target.closest("[data-mdepot]"); if (dp && depot.contains(dp)) { X.oeffneDepot(+dp.dataset.mdepot); window.scrollTo({ top: Math.max(0, depot.getBoundingClientRect().top + window.scrollY - 90) }); return; }
      const ics = e.target.closest("[data-ics]"); if (ics) { kalender(ics.dataset.ics === "depot" ? X.depotAnleihen() || [] : X.liste()); return; }
      const g = e.target.closest("[data-gelesen]"); if (g) { g.disabled = true; lege("gelesen", g.dataset.gelesen, gelesen(g.dataset.gelesen) ? null : 1).catch(() => { g.disabled = false; }); return; }
      const lz = e.target.closest("[data-lz-weg]"); if (lz) { lege("lesezeichen", lz.dataset.lzWeg, null).catch(() => {}); return; }
      const bg = e.target.closest("[data-bg-weg]"); if (bg) { lege("begriff", bg.dataset.bgWeg, null).catch(() => {}); return; }
      const ew = e.target.closest("[data-etf-weg]"); if (ew) { ew.disabled = true; K.entfernen(ew.dataset.etfWeg).catch(() => {}); return; }
      if (e.target.closest("#mb-vgl-btn")) { if (VGL.size < 2) X.hinweis("Kreuz in der Tabelle mindestens zwei Anleihen an – dann stehen sie hier nebeneinander."); else $("mb-vgl").scrollIntoView({ behavior: "smooth", block: "start" }); return; }
      if (e.target.closest("#mb-vgl-leer")) { VGL.clear(); X.zeichneListe(); return; }
      if (e.target.closest("#mb-einf-btn")) { const b = $("mb-einf"); b.hidden = !b.hidden; if (!b.hidden) $("mb-einf-t").focus(); return; }
      if (e.target.closest("#mb-einf-zu")) { $("mb-einf").hidden = true; return; }
      if (e.target.closest("#mb-csv")) { csv(); return; }
      if (e.target.closest("#mb-mit-pdf")) { X.teilen(true); return; }
      if (e.target.closest("#mb-mit-csv")) { csv(); return; }
      if (e.target.closest("#mb-mit-ics")) { kalender(X.liste()); return; }
      if (e.target.closest("#mb-listen")) { listenKlick(e); return; }
      if (e.target.closest("#mb-meld")) { meldungKlick(e); return; }
      if (e.target.closest("#konto")) kontoKlick(e);
    });
    depot.addEventListener("submit", e => {
      if (e.target.id === "mb-l-form") listenSubmit(e);
      else if (e.target.id === "mb-einf-form") einfuegen(e);
      else if (e.target.id === "mb-m-form") meldungAnlegen(e);
    });
    depot.addEventListener("change", e => {
      if (e.target.id === "mb-m-i" || e.target.id === "mb-m-b") meldungFormular();
    });
    depot.addEventListener("keydown", e => { if (e.key === "Escape" && LEDIT && e.target.closest("#mb-listen")) { LEDIT = ""; zeichneListen(); } });
    $("zeilen").addEventListener("click", zeilenKlick);
    $("zeilen").addEventListener("change", zeilenChange);
    emailFormular();
    window.addEventListener("hashchange", ausLink);
    ausLink();

    return {
      zeige, neu: () => { alles(); datenFuerSuchen(); }, ablageNeu: () => alles(), etfLaden, istEtf, sichtbar, klasse, zeileKopf, zeileUnter, zeileSeit, zeileTermin, zeileKnopf, zeileNach,
      nachListe: zeichneMerkliste, delta, termin: o => termin(o) || "", etfZahl: () => etfListe().length, ansicht: () => ANSICHT,
      zurueck: () => { VGL.clear(); OFFEN = ""; AKT = "alle"; LEDIT = ""; },
    };
  };
})(window.MC);
