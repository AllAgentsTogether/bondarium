# Titel-Illustration – Platz, Größe, Zeichenfläche

Stand: 01.10.2026 · gilt für die Illustration neben der Überschrift (`.b2-kopf` / `.b2-spot`, Dateien `spot-<seite>.svg`)
auf den 39 Themenseiten. Die Regeln stehen in `bildwelt2.css`; diese Datei erklärt sie und hält fest, was gemessen wurde.

## Wozu die Illustration da ist

Sie ist Schmuck und Wiedererkennung, kein Inhalt: Sie zeigt das Motiv der Seite, dasselbe wie auf der Kachel der
Übersichtsseite. Sie trägt keine Information, die nicht auch im Text steht (`alt=""`), ist kein Link und darf den Text
nie verdrängen. Daraus folgt alles Weitere: Die Überschrift bestimmt den Platz, die Illustration ordnet sich ihr zu.

## Die Regeln

1. **Neben der Überschrift, nicht neben dem Text.** Die Illustration steht rechts in der Kopfzeile der Seite und ist
   **oben an der Überschrift ausgerichtet**. Nie senkrecht mittig zum Textblock – dessen Höhe hängt von der Länge der
   Unterzeile ab, und die Illustration wanderte mit.
2. **Die Überschrift steht auf jeder Seite an derselben Stelle** (22 px unter den Brotkrumen). Die Illustration darf sie
   nicht verschieben, auch nicht bei kurzem Text.
3. **Rechts bündig mit dem Inhaltsrand** – derselbe Rand, an dem Suchfeld und Tabellen enden. 40 px Abstand zum Text.
4. **Oberkante der Zeichnung auf Höhe der Großbuchstaben der ersten Titelzeile.** Der Bildrahmen ist dafür 8 px über die
   Titel-Oberkante gezogen (so viel freie Fläche hat die Zeichnung oben im Mittel).
5. **Eine Illustration je Seite**, immer im Kopf, nie im Fließtext, nie wiederholt.
6. **Nach unten wird nichts gezogen.** Unter der Zeichnung bleiben mindestens 5 px bis zum nächsten Element; kein Element
   darf sie berühren.

| Fensterbreite | Anordnung | Bildrahmen | Abstand zum Text |
|---|---|---|---|
| ab 901 px | rechts neben der Überschrift, oben ausgerichtet | 232 × 160 px | 40 px |
| 721 bis 900 px | wie oben, kleiner – die Überschrift bekommt mehr Breite | 160 × 110 px | 28 px |
| bis 720 px | über der Überschrift, linksbündig | 160 × 110 px | 8 px |

## Die Zeichenfläche (für neue oder überarbeitete Illustrationen)

- Fläche **160 × 110** (`viewBox="0 0 160 110"`), Strich 2,5, Farben der Bildwelt 2.0.
- Die Zeichnung sitzt **mittig in der Fläche** – waagerecht und senkrecht höchstens 5 % daneben. Nur dann stimmt die
  Ausrichtung des Rahmens auch fürs Auge, und nur dann sitzt das Motiv auf der Kachel der Übersichtsseite mittig.
- Die Zeichnung füllt **75 bis 95 % der Breite**. Schmalere Motive wirken neben der Überschrift eingerückt, weil ihr
  rechter Rand weit vom Inhaltsrand entfernt ist.
- Mindestens 4 Einheiten Rand nach allen Seiten, nichts ragt über die Fläche.

Einbau:

```html
<div class="b2-kopf">
  <div>
    <h1>…</h1>
    <p class="sub">…</p>
  </div>
  <div class="b2-spot"><img src="spot-<seite>.svg" alt="" width="232" height="160"></div>
</div>
```

## Was am 01.10.2026 gemessen und geändert wurde

Anlass: Auf der Seite „Anleihen nach Kupon“ stand die Illustration neben dem Fließtext statt neben der Überschrift.
Gemessen wurden alle 39 Seiten bei 1280, 1000, 800 und 375 px Breite.

| | vorher | nachher |
|---|---|---|
| Bild-Oberkante zur Titel-Oberkante (1280 px) | 53 px darüber bis 129 px darunter | auf allen Seiten 8 px darüber |
| Überschrift unter den Brotkrumen | 22 bis 44 px, auf dem leeren Steckbrief 75 px | auf allen Seiten 22 px |
| Titelzeilen bei 800 px Breite | bis zu 5 | bis zu 4 |
| Kleinster Abstand der Zeichnung zum nächsten Element | nicht gemessen | 5 px, keine Berührung |

Ursache war eine einzige Regel: `align-items: center` im Kopf-Raster. Jetzt `align-items: start`, dazu die Stufe für
721 bis 900 px. Zwei Zeichnungen saßen nicht mittig in ihrer Fläche und wurden über die `viewBox` zentriert:
`spot-anlegerprofile.svg` (7,5 % nach rechts versetzt) und `spot-anleihenleiter.svg` (6,4 % nach oben).

## Offen

- **Sechs schmale Motive** füllen weniger als 60 % der Breite (oder enden mehr als 40 px vor dem Inhaltsrand): Rechner
  (39 %), Rechtliches (48 %), Bonität (51 %), Erste Anleihe (53 %), Grundlagen (59 %), Broker-Vergleich. Sie sind richtig
  platziert, wirken aber eingerückt. Abhilfe wäre, sie breiter zu zeichnen – nicht, sie anders zu platzieren.
- **Zwei Dateien haben eine Fläche von 320 × 200** statt 160 × 110 (`spot-anlageziele.svg`, `spot-etf-oder-anleihe.svg`).
  Sie werden im Rahmen etwas kleiner dargestellt. Beim nächsten Anfassen auf 160 × 110 umstellen.
- **Am Handy steht die Illustration über der Überschrift** und schiebt sie um 118 px nach unten. Das ist unverändert –
  eine Geschmacksfrage zwischen Wiedererkennung und „Inhalt zuerst“, die der Betreiber entscheidet.

## So wird nachgemessen

Seite im Browser öffnen und in der Konsole Rahmen und Überschrift vergleichen:

```js
const k = document.querySelector('.b2-kopf'), h = k.querySelector('h1').getBoundingClientRect(),
      i = k.querySelector('.b2-spot img').getBoundingClientRect();
({ bildZuTitelOben: Math.round(i.top - h.top), rechtsBuendig: Math.round(k.getBoundingClientRect().right - i.right) })
// Soll ab 901 px Breite: { bildZuTitelOben: -8, rechtsBuendig: 0 }
```
