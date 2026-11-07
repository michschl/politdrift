# 0005 – Lizenzierung: AGPL-3.0 für Code, CC BY 4.0 für eigene Daten

- Status: angenommen
- Datum: 2026-11-07
- Bezug: KONZEPT Abschnitt 11, Entscheide 1, 2 und 7

## Kontext

Politdrift ist ein Transparenzprojekt. Die Methodik und jede Zahl sollen nachvollziehbar sein, die
Daten sollen Medien, Forschung und Civic Tech möglichst frei nutzen können. Gleichzeitig soll niemand
eine geschlossene, veränderte Kopie betreiben können, deren Zahlen nicht mehr überprüfbar sind.

Offen waren: MIT, Apache-2.0 oder AGPL-3.0 für den Code, CC BY 4.0 oder CC BY-SA 4.0 für die eigenen
Mappings, öffentliches oder privates Repository.

## Entscheid

1. **Code: `AGPL-3.0-or-later`.** Wer Politdrift verändert und als Website betreibt, muss den
   geänderten Quellcode den Nutzerinnen und Nutzern zugänglich machen (Abschnitt 13). Unter MIT oder
   Apache-2.0 wäre ein geschlossener Betrieb mit veränderter Berechnung möglich. Das widerspräche dem
   Kern des Projekts: Nachvollziehbarkeit. Die Website verlinkt im Footer auf den Quellcode.
2. **Eigene Daten (`data/mappings/`, `data/derived/`): CC BY 4.0.** Gleiche Lizenz wie OpenParlData.ch.
   Maximale Weiterverwendbarkeit für Datenjournalismus und Forschung. CC BY-SA wäre für Redaktionen
   hinderlich, weil ihre Artikel und Grafiken dann ebenfalls unter SA stehen müssten.
3. **Repository öffentlich.** Passt zur Transparenzmission, und CodeQL, Secret Scanning und Dependency
   Review sind für öffentliche Repositories kostenlos.

## Konsequenzen

- Beiträge von Dritten stehen automatisch unter AGPL-3.0-or-later. Ein CLA ist nicht vorgesehen. Eine
  spätere Umlizenzierung bräuchte die Zustimmung aller Beitragenden.
- Einbettungen und Screenshots der Website sowie die Nutzung der JSON-Daten fallen nicht unter die AGPL,
  sondern unter CC BY 4.0 (Daten).
- Daten Dritter behalten ihre Bedingungen (Parlamentsdienste, OpenParlData.ch). Smartvote-Daten sind
  nicht Teil der offenen Daten (`data/LICENSE`).
