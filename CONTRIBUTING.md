# Mitwirken

Danke für dein Interesse an Politdrift. Grundlage ist [docs/KONZEPT.md](docs/KONZEPT.md); bitte lies
insbesondere die Leitplanken (Abschnitt 10).

## Zuordnungen hinterfragen

Hältst du die Achsen-Zuordnung einer Abstimmung für falsch, eröffne ein Issue mit der Vorlage
«Achsen-Zuordnung hinterfragen». Begründungen mit Quellen helfen am meisten.

## Code und Daten

1. Fork bzw. Branch von `main`, ein Thema pro PR.
2. Commit-Messages nach [Conventional Commits](https://www.conventionalcommits.org/)
   (`feat:`, `fix:`, `data:`, `chore:`, `docs:`, `ci:`), auf Englisch.
3. Lokal prüfen:
   ```bash
   cd web && npm run lint && npm run check && npm test -- --run && npm run test:e2e
   cd pipeline && uv run ruff check . && uv run ruff format --check . && uv run pyright && uv run pytest
   cd pipeline && uv run politdrift validate ../data/mappings
   ```
4. PR mit «Was / Warum / Wie getestet». CI muss grün sein; Merge per Squash.

## Konventionen

- Code, Kommentare, Commits: Englisch. UI-Texte und Dokumentation: Deutsch (Schweizer Rechtschreibung,
  kein «ß»).
- UI-Texte nur über i18n-Schlüssel (`web/src/lib/i18n/`), keine Literale in Komponenten.
- Neue Architekturentscheide als ADR unter `docs/adr/NNNN-titel.md`.
- Keine Secrets, keine Tracker, keine externen Ressourcen zur Laufzeit.
- Mapping-Änderungen nur mit Begründung im Feld `note`; `reviewed: true` nur nach menschlicher Prüfung.
