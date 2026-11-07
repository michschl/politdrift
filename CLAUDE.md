# Politdrift

Zeigt das Abstimmungsverhalten von Parlamentsmitgliedern auf den acht
Smartspider-Achsen und dessen Drift über die Zeit. Konzept: docs/KONZEPT.md
(verbindlich), Methodik: docs/METHODIK.md, Betrieb: docs/RUNBOOK.md.

## Struktur
- web/       SvelteKit (adapter-static), TS strict, Tailwind, D3 (modular)
- pipeline/  Python 3.12, uv, DuckDB, Typer-CLI `politdrift`
- data/      mappings/ (YAML, reviewed) und derived/ (generiert, committet)
- infra/     Dockerfile, compose, Caddy, deploy.sh, VPS-Bootstrap
- .github/   cicd.yml (Quality → Security → Build → Deploy), data-refresh.yml

## Befehle
- web:      npm ci · npm run dev · npm run lint · npm run check · npm test · npm run build
            npm run test:e2e (Playwright; in Sandboxes mit vorinstalliertem Browser
            PLAYWRIGHT_CHROMIUM_EXECUTABLE setzen)
- pipeline: uv sync · uv run pytest · uv run ruff check . · uv run pyright
            uv run politdrift validate ../data/mappings
- image:    docker build -f infra/Dockerfile.web -t politdrift-web .

## Regeln
- Keine Secrets im Repo. Actions auf SHA pinnen. permissions minimal.
- Deploy nur über GitHub Actions (push auf main). Nie manuell auf dem VPS.
- Nur `reviewed: true`-Mappings fliessen in publizierte Profile.
- Conventional Commits, PR mit grüner CI, Squash-Merge.
- UI Deutsch (Schweizer Rechtschreibung, kein ß), Code Englisch.
- Entscheide als ADR in docs/adr/, nicht im Chat.
- Quellen nennen: parlament.ch, OpenParlData.ch (CC BY 4.0), Smartvote (nur mit Vereinbarung).

## Stolpersteine
- Achsen-Reihenfolge existiert zweimal: web/src/lib/axes.ts und pipeline/src/politdrift/axes.py.
  Beide Tests prüfen sie; bei Änderungen beide anpassen.
- CSP: kein Inline-JS/-CSS, keine `style=`-Attribute in Komponenten (SVG-Attribute wie fill/stroke
  sind ok). Die E2E-Tests schlagen bei jeder CSP-Verletzung fehl (ADR 0003).
