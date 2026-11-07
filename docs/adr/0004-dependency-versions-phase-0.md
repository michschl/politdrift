# 0004 – Versionen in Phase 0

- Status: angenommen
- Datum: 2026-11-07

## Kontext

Das Konzept nennt Major-Versionen für Actions und Werkzeuge mit dem Vermerk *(verifizieren)*. Beim
Aufsetzen (7. November 2026) waren neuere Majors aktuell.

## Entscheid

Es werden die zum Zeitpunkt der Initialisierung aktuellen Versionen verwendet, Actions auf Commit-SHA
gepinnt (aufgelöst über die Git-Tags der jeweiligen Repositories):

| Komponente | Konzept | Verwendet |
|---|---|---|
| actions/checkout | v5 | v7.0.1 |
| actions/setup-node | v5 | v7.1.0 |
| actions/upload-artifact / download-artifact | v4 | v7.0.2 / v8.0.2 |
| astral-sh/setup-uv | v6 | v10.3.3 |
| github/codeql-action | v4 | v4.39.3 |
| actions/dependency-review-action | v4 | v5.0.0 |
| docker/setup-buildx / login / metadata / build-push | v3/v3/v5/v6 | v4.4.1 / v4.8.0 / v6.2.0 / v7.4.0 |
| aquasecurity/trivy-action | – | v0.36.0 |
| actions/attest-build-provenance | v3 | v4.2.2 |
| actions/cache | – | v6.1.0 |
| actions/create-github-app-token | – | v3.3.0 |
| SvelteKit / Svelte / Vite | – | 3.1 / 5.57 / 8.3 |
| nginx-unprivileged | – | 1.30.6-alpine (Digest gepinnt) |
| Caddy | 2-alpine | 2.11-alpine (Digest gepinnt) |

Weitere Abweichungen:

- SvelteKit 3 hat keine `svelte.config.js` mehr. Adapter und CSP sind in `web/vite.config.ts`
  konfiguriert.
- `web-quality` führt zusätzlich die Playwright-Smoke-Tests aus (inkl. CSP-Prüfung).
- `pip-audit` prüft die exportierten, gelockten Abhängigkeiten statt der Umgebung von `uvx`.
- Die Abhängigkeiten werden von Dependabot aktualisiert. Zusätzlich ist das Ökosystem
  `docker-compose` für die Caddy-Version in `infra/compose.yml` aktiviert.

## Konsequenzen

Die Inputs aller Actions wurden gegen die `action.yml` der gepinnten Commits geprüft. Bei Updates durch
Dependabot gelten Breaking Changes der jeweiligen Major-Version.
