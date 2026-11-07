# Daten

- `mappings/<body>/<legislature>.yaml`: Achsen-Zuordnungen von Abstimmungen (manuell gepflegt,
  versioniert). Schema und Regeln: `docs/METHODIK.md`. Prüfen mit
  `cd pipeline && uv run politdrift validate ../data/mappings`.
- `derived/`: von der Pipeline generierte JSON-Dateien (KONZEPT 4.3). Nicht von Hand bearbeiten.

Rohdaten (Einzelstimmen) werden nicht committet, sondern im Pipeline-Cache gehalten.
