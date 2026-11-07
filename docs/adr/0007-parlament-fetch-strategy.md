# 0007 – Abruf der Nationalratsdaten von ws.parlament.ch

- Status: angenommen
- Datum: 2026-11-07
- Bezug: KONZEPT 3.1, 6.2, Phase 2

## Kontext

Die Einzelstimmen (`Voting`) einer Legislatur umfassen rund 840'000 Zeilen. Messungen am
7. November 2026:

| Abfrage | Dauer |
|---|---|
| `Voting` gefiltert auf `IdSession`, 1000 Zeilen pro Seite | ca. 17 s pro Seite, ca. 18 min pro Session |
| `Voting` gefiltert auf `IdVote` (ca. 200 Zeilen) | ca. 0,6 s |
| `$inlinecount` auf `Voting` pro Session | Serverfehler |

Abnahme Phase 2: kompletter Lauf von null in unter 20 Minuten.

## Entscheid

1. **Einzelstimmen pro Abstimmung** abrufen (`IdVote eq …`), mit 4 parallelen Anfragen und
   einem gemeinsamen Rate-Limit (höchstens 10 Anfragen pro Sekunde), 3 Wiederholungen mit
   Backoff bei Serverfehlern.
2. **Inkrementell pro Session:** Abgeschlossene Sessionen, deren Abstimmungen alle Einzelstimmen
   haben, werden übersprungen. Laufende Sessionen werden neu geprüft.
3. **Mitgliedschaften** aus `MemberCouncilHistory` (Partei, Fraktion, Zeitraum).
   Die Fraktion zum Zeitpunkt jeder Abstimmung kommt zusätzlich aus `Voting.ParlGroupCode`.
4. **Entscheide** werden über `DecisionText` abgebildet, nicht über Codes. Unbekannte Texte
   brechen den Lauf ab, statt Profile still zu verfälschen.
5. **Speicher:** DuckDB-Datei unter `pipeline/.cache/` (nicht im Repo). Schreiben per Bulk-Import
   über NDJSON, weil `executemany` rund 2 ms pro Zeile braucht.
6. **Personen-ID:** `parlch:<PersonNumber>`.

## Konsequenzen

- Gemessener Lauf von null: 15 Sessionen, 4201 Abstimmungen, 839'717 Einzelstimmen in 7 min 55 s.
- Rund 4200 Anfragen pro Komplettlauf. Danach typischerweise nur die laufende Session.
- `Subject`, `MeaningYes` und `MeaningNo` liefert die Quelle teils in der Originalsprache
  (z. B. Französisch), auch mit `Language eq 'DE'`. Das UI muss damit umgehen.
- Tests laufen ohne Netzwerk gegen aufgezeichnete Antworten
  (`pipeline/tests/fixtures/parlament/`, neu erzeugt mit
  `uv run python scripts/record_parlament_fixtures.py`).
