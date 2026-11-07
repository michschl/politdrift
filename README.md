# Politdrift

**Gesagt. Gestimmt.**

Politdrift zeigt, wie Mitglieder des eidgenössischen Parlaments (zuerst Nationalrat) und später der
kantonalen Parlamente tatsächlich abstimmen. Das Abstimmungsverhalten wird auf die acht Achsen des
Smartspiders verdichtet («Ist-Profil»), mit der Fraktion und, wo verfügbar, mit dem Wahlprofil
verglichen und über die Zeit verfolgt («Drift»). Jede Zahl ist bis zur einzelnen Abstimmung
nachvollziehbar.

Status: **Phase 0**, Repository-Grundgerüst. Noch keine echten Daten.

- Konzept (verbindlich): [docs/KONZEPT.md](docs/KONZEPT.md)
- Methodik: [docs/METHODIK.md](docs/METHODIK.md)
- Einrichtung GitHub und Infomaniak: [docs/SETUP.md](docs/SETUP.md)
- Betrieb: [docs/RUNBOOK.md](docs/RUNBOOK.md)
- Architekturentscheide: [docs/adr/](docs/adr/)

## Aufbau

```
web/        SvelteKit (adapter-static), TypeScript strict, Tailwind, D3 (modular)
pipeline/   Python 3.12, uv, DuckDB, Typer-CLI «politdrift»
data/       mappings/ (YAML, geprüft) und derived/ (generiert, committet)
infra/      Dockerfile, nginx, Compose, Caddy, deploy.sh, VPS-Bootstrap, Ruleset
.github/    CI/CD (Quality → Security → Build → Deploy), Data-Refresh, Dependabot
```

## Quickstart

Voraussetzungen: Node 22, [uv](https://docs.astral.sh/uv/), Docker (optional).

```bash
# Website
cd web
npm ci
npm run dev          # http://localhost:5173
npm run lint && npm run check && npm test -- --run
npm run test:e2e     # Playwright, baut die Seite
npm run build        # statischer Build nach web/build

# Pipeline
cd pipeline
uv sync
uv run pytest
uv run politdrift validate ../data/mappings
uv run politdrift fetch      # Nationalrat, Legislatur 52 -> .cache/politdrift.duckdb (~8 min)
uv run politdrift classify   # LLM-Vorschläge (reviewed: false), Token in POLITDRIFT_LLM_API_KEY
uv run politdrift review     # Vorschläge einzeln annehmen, bearbeiten oder ohne Achse markieren
                             # --from entscheide.json übernimmt Entscheide einer Prüfseite
uv run politdrift compute    # Profile berechnen, Abdeckung und Warnungen anzeigen
                             # --include-pending: Konsistenz-Check über ungeprüfte Vorschläge
uv run politdrift export     # JSON nach ../data/derived/ (inkl. Schema)

# Image (nach npm run build)
docker build -f infra/Dockerfile.web -t politdrift-web .
docker run --rm --read-only --tmpfs /tmp --cap-drop ALL -p 8080:8080 politdrift-web
curl http://localhost:8080/healthz
```

## Quellen

- Parlamentsdienste, [parlament.ch](https://www.parlament.ch) (Open Data Web Services)
- [OpenParlData.ch](https://openparldata.ch), CC BY 4.0
- Smartvote / Politools: nur mit Vereinbarung

## Lizenz

- **Code:** [GNU Affero General Public License v3.0 oder später](LICENSE) (`AGPL-3.0-or-later`).
  Wer Politdrift verändert und als Website betreibt, muss den geänderten Quellcode ebenfalls
  offenlegen.
- **Eigene Daten** (`data/mappings/`, `data/derived/`): [CC BY 4.0](data/LICENSE). Frei nutzbar für
  Medien, Forschung und Civic Tech mit Quellenangabe «Politdrift (politdrift.org), CC BY 4.0».
- **Daten Dritter** behalten ihre Bedingungen: Parlamentsdienste (parlament.ch), OpenParlData.ch
  (CC BY 4.0). Smartvote-Daten sind nicht Teil der offenen Daten.

Begründung: [ADR 0005](docs/adr/0005-licensing.md).
