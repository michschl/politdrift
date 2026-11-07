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

Noch nicht festgelegt (siehe [LICENSE](LICENSE) und KONZEPT Abschnitt 11).
