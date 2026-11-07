# 0009 – Sicherheitshinweise in Entwicklungsabhängigkeiten

- Status: angenommen
- Datum: 2026-11-07
- Bezug: ADR 0004, KONZEPT 10 (Leitplanken)

## Kontext

Dependabot meldete am 7. November 2026 zwei Hinweise auf `main`. Beide betreffen nur Werkzeuge
für Entwicklung und Build. `npm audit --omit=dev` findet nichts, und die ausgelieferte Seite
enthält keine der beiden Bibliotheken.

| Paket | Hinweis | Herkunft | Behebung |
|---|---|---|---|
| `minimatch` 10.2.6 | [GHSA-g3hv-75wg-m249](https://github.com/advisories/GHSA-g3hv-75wg-m249), mittel, DoS über Glob-Muster | eslint 10, typescript-eslint 8 | erst ab 11.0.1; eslint verlangt `^10` |
| `deepmerge` 4.3.1 | [GHSA-gcqx-w48m-w2h4](https://github.com/advisories/GHSA-gcqx-w48m-w2h4), niedrig, Prototype Poisoning | `@sveltejs/vite-plugin-svelte` | keine korrigierte Version, Paket seit 2023 unverändert |

## Entscheid

1. **minimatch:** `overrides` in `web/package.json` hebt minimatch auf `^11.0.5`. Mit dieser
   Version laufen eslint, svelte-check, Unit-Tests, Build und Playwright ohne Fehler. Der Override
   wird entfernt, sobald eslint und typescript-eslint selbst minimatch 11 oder neuer verlangen.
2. **Allgemein:** Hinweise in Entwicklungsabhängigkeiten werden behoben, wenn es eine korrigierte
   Version gibt. Ein Override über eine Major-Grenze ist zulässig, wenn alle Prüfungen der CI
   grün bleiben, und wird hier dokumentiert. Gibt es keine Korrektur, entscheidet Michael, ob der
   Hinweis mit Begründung geschlossen wird.

## Konsequenzen

- Overrides umgehen die Versionsangaben der Werkzeuge. Bei Updates von eslint und
  typescript-eslint durch Dependabot ist zu prüfen, ob der Override noch nötig ist.
- `deepmerge` bleibt vorerst gemeldet. Es verarbeitet nur die eigene Build-Konfiguration, also
  keine fremden Eingaben.
