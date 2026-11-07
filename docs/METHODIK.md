# Methodik

Politdrift zeigt, wie Mitglieder des Parlaments tatsächlich abstimmen. Diese Seite erklärt, wie aus
einzelnen Stimmen ein Profil wird, was die Zahlen bedeuten und wo ihre Grenzen liegen.

> Stand: Entwurf (Version 0.1). Die Zahlen zu Abstimmungen, Zuordnungen und Abdeckung folgen, sobald
> die ersten Daten publiziert sind.

## Die acht Achsen

Politdrift verwendet die acht Achsen des Smartspiders. Jede Achse reicht von 0 bis 100. Ein hoher Wert
bedeutet starke Zustimmung zur Bezeichnung der Achse.

| Achse | Hoher Wert bedeutet |
|---|---|
| Offene Aussenpolitik | Öffnung, EU-Annäherung, internationale Zusammenarbeit |
| Liberale Wirtschaftspolitik | Deregulierung, weniger Staat im Markt |
| Restriktive Finanzpolitik | Sparen, tiefe Steuern und Abgaben |
| Law & Order | Innere Sicherheit, härtere Strafen |
| Restriktive Migrationspolitik | Zuwanderung begrenzen, strengeres Asylrecht |
| Ausgebauter Umweltschutz | Klima, Energie, Natur vor Wirtschaft |
| Ausgebauter Sozialstaat | Sozialwerke, Umverteilung, Service public |
| Liberale Gesellschaft | Selbstbestimmung, Gleichstellung |

Im Spider beginnt die erste Achse oben (12 Uhr), die weiteren folgen im Uhrzeigersinn.

## Von der Abstimmung zur Achse

Nicht jede Abstimmung sagt etwas über eine Achse aus. Jede relevante Abstimmung erhält deshalb null bis
drei Zuordnungen. Jede Zuordnung hat:

- eine **Richtung**: Bedeutet ein Ja eine Bewegung in Richtung der Achsenbezeichnung (+1) oder davon weg (−1)?
- ein **Gewicht** zwischen 0 und 1: Wie deutlich ist der Bezug zur Achse?

Für die Zuordnung gelten diese Regeln:

1. **Vergleichbarkeit vor Plausibilität.** Hat Smartvote zur gleichen Sachfrage eine Wahlfrage gestellt,
   übernehmen wir deren Achsenzuordnung, auch wenn eine eigene inhaltliche Einordnung anders ausfiele.
   Nur so messen wir Wahlprofil und Abstimmungsverhalten mit demselben Massstab.
2. **Konsistenz-Check gegen die Fraktionen.** Verläuft die Lagerbildung in einer Abstimmung entgegen der
   Reihenfolge der Fraktionen auf einer Achse, ist die Achse vermutlich falsch gewählt. Die Pipeline prüft
   das automatisch und markiert solche Fälle. Dazu vergleicht sie, wie stark jede Fraktion in dieser
   Abstimmung in Achsenrichtung gestimmt hat, mit dem Fraktionsprofil auf dieser Achse aus allen
   *anderen* zugeordneten Abstimmungen (Rangkorrelation nach Spearman). Ist die Korrelation bei
   mindestens vier Fraktionen negativ, wird die Zuordnung markiert.
3. **Nicht jede Abstimmung gehört in den Spider.** Verfahrensabstimmungen, Ordnungsanträge und
   Geschäfte ohne klaren Achsenbezug bleiben ohne Achse. Sie können in Themenratings geführt werden.
4. **Nur geprüfte Zuordnungen zählen.** Vorschläge, die noch nicht von einem Menschen geprüft wurden,
   fliessen nie in publizierte Profile.
5. **Alles ist versioniert.** Die Zuordnungen liegen offen im Repository. Jede Änderung ist mit
   Begründung nachvollziehbar.

Umstrittene Zuordnungen werden als solche gekennzeichnet. Wer eine Zuordnung für falsch hält, kann sie
öffentlich hinterfragen.

### Unterstützung durch ein Sprachmodell

Ein Sprachmodell kann Zuordnungen vorschlagen. Es erhält Titel, Gegenstand und die offizielle Bedeutung
von Ja und Nein. Ein Vorschlag bleibt so lange ungeprüft, bis ein Mensch ihn annimmt, ändert oder
ablehnt.

Das Modell läuft bei Infomaniak in der Schweiz und erhält nur öffentliche Angaben zur Abstimmung,
keine Personendaten und keine Stimmen. Bei jedem Vorschlag sind Modell, Prompt-Version und Datum
vermerkt. Ändert die prüfende Person eine Achse, gilt die Zuordnung als manuell.

## Berechnung

Für eine Person *p*, eine Achse *a* und ein Zeitfenster *w*:

```
s(p,v)   = +1 bei Ja, −1 bei Nein, 0 bei Enthaltung oder Abwesenheit (zählt nicht)
S(p,a,w) = Σ [ Gewicht · Richtung · s(p,v) ]  /  Σ [ Gewicht · |s(p,v)| ]
Wert     = (S + 1) / 2 · 100
```

- Ein Wert wird nur ausgewiesen, wenn mindestens **8** zugeordnete, abgegebene Stimmen vorliegen.
  Sonst steht «zu wenig Daten».
- **Zeitfenster:** pro Session (Momentaufnahme), gleitend über die letzten vier Sessionen
  (Standardanzeige) und über die ganze Legislatur.

### Vergleiche

- **Fraktionsprofil:** Jede Fraktion zählt pro Abstimmung einmal, mit ihrer Bilanz
  (Ja minus Nein, geteilt durch die abgegebenen Ja- und Nein-Stimmen ihrer Mitglieder). So hängt das
  Profil nicht von der Grösse der Fraktion ab, und die Mindestzahl von 8 gilt für Abstimmungen wie bei
  Personen. Massgebend ist die Fraktion zum Zeitpunkt der Abstimmung.
- **Fraktionsdrift:** mittlere Abweichung des Profils einer Person vom Profil ihrer Fraktion über alle
  Achsen. Das ist der Standardvergleich.
- **Drift über die Zeit:** Veränderung des Profils zwischen zwei Zeitfenstern, pro Achse.
- **Deckungsgrad** (nur mit Wahlprofil): 100 minus die mittlere Abweichung zwischen Wahlprofil und
  Abstimmungsprofil über die verfügbaren Achsen.

Drift ist eine Beobachtung, keine Wertung. Politdrift gibt keine Wahlempfehlungen und bewertet keine
Motive.

## Grenzen

- Der Smartspider aus dem Wahlfragebogen und das Profil aus Abstimmungen sind unterschiedlich
  konstruiert. Der Vergleich ist eine begründete Annäherung, keine exakte Messung.
- Die Auswahl und Gewichtung der Abstimmungen prägt das Ergebnis. Deshalb ist jede Zuordnung offen
  einsehbar und jede Zahl bis zur einzelnen Abstimmung nachvollziehbar.
- Abwesenheiten und Enthaltungen fliessen nicht ein. Wer selten abstimmt, hat weniger belastbare Werte.
- Wahlprofile von Smartvote sind kein Open Data. Sie werden nur mit einer Vereinbarung mit Politools
  verwendet. Bis dahin vergleicht Politdrift mit der Fraktion und über die Zeit.

## Quellen

- Abstimmungen des eidgenössischen Parlaments: Parlamentsdienste, [parlament.ch](https://www.parlament.ch)
- Kantonale Parlamente: [OpenParlData.ch](https://openparldata.ch), Lizenz CC BY 4.0
- Wahlprofile: Smartvote / Politools, nur mit Vereinbarung
