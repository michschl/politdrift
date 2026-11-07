# 0008 – Zuordnungsvorschläge mit einem Sprachmodell bei Infomaniak

- Status: angenommen
- Datum: 2026-11-07
- Bezug: KONZEPT 2.2, 2.4, Phase 2

## Kontext

Für belastbare Profile braucht jede Person auf jeder Achse mindestens 8 zugeordnete, abgegebene
Stimmen. Das sind über 150 geprüfte Zuordnungen pro Legislatur. Ein Sprachmodell soll Vorschläge
machen, damit die menschliche Prüfung schneller geht. Es darf aber nie selbst publizieren.

Vorgabe von Michael: Das Modell läuft bei Infomaniak AI Services (Schweiz), nicht bei einem
US-Anbieter.

Vergleich am 7. November 2026 mit 8 Schlussabstimmungen der 52. Legislatur:

| Modell | Ergebnis |
|---|---|
| `Qwen/Qwen3.5-397B-A17B-FP8` | HTTP 502, Modell noch nicht verfügbar («coming soon») |
| `swiss-ai/Apertus-v1.5-70B` | funktioniert, vereinzelt ungültiges JSON; Subvention für Stärkeproduktion als «wirtschaftsliberal +1» eingeordnet (falsch) |
| `mistralai/Ministral-3-14B-Instruct-2512` | funktioniert, vereinzelt ungültiges JSON; dieselbe Subvention als «wirtschaftsliberal −1» eingeordnet (richtig) |

## Entscheid

1. **Anbieter:** Infomaniak AI Tools über die OpenAI-kompatible Schnittstelle
   (`/2/ai/<product_id>/openai/v1/chat/completions`). Der Code spricht nur dieses Protokoll und
   kann jeden kompatiblen Anbieter nutzen. Konfiguration nur über Umgebungsvariablen
   `POLITDRIFT_LLM_BASE_URL`, `POLITDRIFT_LLM_MODEL`, `POLITDRIFT_LLM_API_KEY`. Das Token liegt nie
   im Repository. In Cloud-Sessions setzt der Proxy es ein.
2. **Standardmodell:** `mistralai/Ministral-3-14B-Instruct-2512`. Wechsel auf ein grösseres Modell,
   sobald Qwen 3.5 verfügbar ist und im selben Vergleich besser abschneidet.
3. **Eingabe:** nur öffentliche Angaben zur Abstimmung (Geschäftsnummer, Titel, Gegenstand,
   Bedeutung Ja/Nein). Keine Personendaten, keine Einzelstimmen.
4. **Ausgabe:** ein JSON-Objekt, das gegen dasselbe Schema geprüft wird wie die YAML-Zuordnungen.
   Ist die Antwort ungültig, erhält das Modell den Fehler genau einmal zurück. Scheitert auch der
   zweite Versuch, wird die Abstimmung übersprungen und gemeldet.
5. **Determinismus:** Temperatur 0. Prompt (`classify/prompt.md`) und Beispiele
   (`classify/examples.yaml`) sind versioniert. Modell, Prompt-Version und Datum stehen in der
   `note` jedes Vorschlags.
6. **Prüfung:** Vorschläge landen mit `source: llm` und `reviewed: false` in
   `data/mappings/<body>/<legislatur>.yaml`. Erst `politdrift review` (oder eine Änderung im PR)
   setzt `reviewed: true`, `reviewed_by` und `reviewed_at`. Wird eine Achse geändert, wird die
   Quelle `manual`.
7. **Reihenfolge:** zuerst Schlussabstimmungen (`--scope final`), weil sie das Ergebnis eines
   Geschäfts abbilden und selten Verfahrensfragen sind. Danach Gesamtabstimmungen und Vorstösse.

## Konsequenzen

- Pro Abstimmung eine Anfrage, bei ungültiger Antwort zwei. 211 Schlussabstimmungen der
  52. Legislatur kosten damit höchstens 422 Anfragen.
- Das Modell sieht nur Text, keine Abstimmungsergebnisse. Fehler wie eine vertauschte Richtung
  fängt der Konsistenz-Check gegen die Fraktionen (METHODIK, Regel 2) zusätzlich auf.
- Die Produkt-ID im Standard-Endpunkt ist kein Geheimnis. Ohne Token ist der Endpunkt nicht nutzbar.
- Eine Smartvote-Vereinbarung (KONZEPT 2.2 Regel 1) hat Vorrang: Gibt es eine passende Wahlfrage,
  wird deren Achse übernommen, auch wenn das Modell etwas anderes vorschlägt.
