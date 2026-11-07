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

Vergleiche am 7. November 2026, alle Modelle über denselben Endpunkt bei Infomaniak:

**Stichprobe:** 5 Schlussabstimmungen zu Volksinitiativen, bei denen die richtige Richtung aus
«Bedeutung Ja» eindeutig hervorgeht (Bundesbeschluss mit Empfehlung auf Ablehnung).

| Modell | richtig | Bemerkung |
|---|---|---|
| `google/gemma-4-31B-it` | 4 von 5 | der fünfte Fall ohne Achse statt falsch |
| `mistralai/Mistral-Small-4-119B-2603` | 2 von 5 | erster Prompt; mit verbessertem Prompt 1 von 5 |
| `Qwen/Qwen3.8-27B-FP8` | 2 von 5 | zweimal leere Antwort |
| `mistralai/Ministral-3-14B-Instruct-2512` | 1 von 5 | mit verbessertem Prompt 2 von 5 |
| `moonshotai/Kimi-K2.6` | 1 von 5 | dreimal HTTP 502, langsam |
| `swiss-ai/Apertus-v1.5-70B` | 0 von 5 | |
| `Qwen/Qwen3.5-397B-A17B-FP8` | – | HTTP 502, noch nicht verfügbar |

**Vollständiger Lauf:** alle 210 ungeprüften Schlussabstimmungen der 52. Legislatur, danach der
Konsistenz-Check gegen die Fraktionen (METHODIK, Regel 2), provisorisch mit allen Vorschlägen
gerechnet (`uv run politdrift compute --include-pending`):

| | Ministral 3 14B, erster Prompt | Gemma 4 31B, verbesserter Prompt |
|---|---|---|
| Vorschläge mit Konsistenz-Warnung | 93 | 39 |
| davon deutlich (ρ ≤ −0,5) | 39 | 17 |
| Median ρ aller zugeordneten Achsen | 0,39 | 0,66 |
| ohne Achse | 2 | 29 |
| Achsen insgesamt | 421 | 267 |
| Dauer | 11,5 min | 11,3 min |

Häufigster Fehler: Bei Volksinitiativen wird in der Schlussabstimmung über den Bundesbeschluss
abgestimmt. Empfiehlt er die Ablehnung, bedeutet Ja «gegen das Anliegen». Kleinere Modelle drehen
diese doppelte Verneinung oft falsch.

## Entscheid

1. **Anbieter:** Infomaniak AI Tools über die OpenAI-kompatible Schnittstelle
   (`/2/ai/<product_id>/openai/v1/chat/completions`). Der Code spricht nur dieses Protokoll und
   kann jeden kompatiblen Anbieter nutzen. Konfiguration nur über Umgebungsvariablen
   `POLITDRIFT_LLM_BASE_URL`, `POLITDRIFT_LLM_MODEL`, `POLITDRIFT_LLM_API_KEY`. Das Token liegt nie
   im Repository. In Cloud-Sessions setzt der Proxy es ein.
2. **Standardmodell:** `google/gemma-4-31B-it`. Infomaniak führt es noch als «coming soon»,
   es antwortet aber zuverlässig. Ein anderes Modell wird erst nach demselben Vergleich
   (Stichprobe und vollständiger Lauf mit Konsistenz-Check) übernommen.
3. **Eingabe:** nur öffentliche Angaben zur Abstimmung (Geschäftsnummer, Titel, Gegenstand,
   Bedeutung Ja/Nein). Keine Personendaten, keine Einzelstimmen.
4. **Ausgabe:** ein JSON-Objekt, das gegen dasselbe Schema geprüft wird wie die YAML-Zuordnungen.
   Ist die Antwort ungültig, erhält das Modell den Fehler genau einmal zurück. Scheitert auch der
   zweite Versuch, wird die Abstimmung übersprungen und gemeldet.
5. **Zuerst die Bedeutung:** Das Modell schreibt in `yes_means` zuerst, was ein Ja inhaltlich
   bewirkt, und wählt erst danach Achsen und Richtungen. Der Satz steht in der `note` des
   Vorschlags und hilft bei der Prüfung.
6. **Determinismus:** Temperatur 0. Prompt (`classify/prompt.md`) und Beispiele
   (`classify/examples.yaml`) sind versioniert. Modell, Prompt-Version und Datum stehen in der
   `note` jedes Vorschlags.
7. **Prüfung:** Vorschläge landen mit `source: llm` und `reviewed: false` in
   `data/mappings/<body>/<legislatur>.yaml`. Erst `politdrift review` (oder eine Änderung im PR)
   setzt `reviewed: true`, `reviewed_by` und `reviewed_at`. Wird eine Achse geändert, wird die
   Quelle `manual`.
8. **Reihenfolge:** zuerst Schlussabstimmungen (`--scope final`), weil sie das Ergebnis eines
   Geschäfts abbilden und selten Verfahrensfragen sind. Danach Gesamtabstimmungen und Vorstösse.

## Konsequenzen

- Pro Abstimmung eine Anfrage, bei ungültiger Antwort zwei. 211 Schlussabstimmungen der
  52. Legislatur kosten damit höchstens 422 Anfragen.
- Das Modell sieht nur Text, keine Abstimmungsergebnisse. So bleibt der Konsistenz-Check gegen
  die Fraktionen eine unabhängige Kontrolle. Er fängt vertauschte Richtungen auf, aber keine
  fehlenden Achsen. Die menschliche Prüfung bleibt nötig.
- Auch Gemma macht inhaltliche Fehler (z. B. Demokratie-Initiative als Abstimmungs- statt
  Einbürgerungsthema). Teilweise ist schon der Quelltext irreführend («Empfehlung der
  Volksinitiative» bei einer Empfehlung auf Ablehnung).
- Die Produkt-ID im Standard-Endpunkt ist kein Geheimnis. Ohne Token ist der Endpunkt nicht nutzbar.
- Eine Smartvote-Vereinbarung (KONZEPT 2.2 Regel 1) hat Vorrang: Gibt es eine passende Wahlfrage,
  wird deren Achse übernommen, auch wenn das Modell etwas anderes vorschlägt.
