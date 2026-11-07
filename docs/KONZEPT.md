# Politdrift – Umsetzungskonzept

**Version 0.1 · 7. November 2026**
**Repo:** `github.com/michschl/politdrift` · **Domain:** `politdrift.org` · **Hosting:** VPS bei Infomaniak
**Claim:** «Gesagt. Gestimmt.» (FR: «Dit. Voté.» · IT: «Detto. Votato.»)

---

## 0. Lesehinweise für Claude Code

- Dieses Dokument ist die verbindliche Arbeitsgrundlage. Arbeite **phasenweise** (Abschnitt 9). Jede Phase endet mit erfüllten Abnahmekriterien und einem Pull Request.
- Hier getroffene Entscheidungen werden nicht neu diskutiert. Neue Architekturentscheide werden als ADR unter `docs/adr/NNNN-titel.md` festgehalten (Kontext, Entscheid, Konsequenzen).
- Die **Leitplanken in Abschnitt 10 gelten immer** und schlagen alles andere.
- Bei Unklarheiten: begründete Annahme treffen, im PR dokumentieren, weiterarbeiten. Ausnahme: Fragen zu Sicherheit, Datenschutz oder Datenlizenzen → stoppen und rückfragen.
- Annahmen zu externen Schnittstellen (Feldnamen, Versionen, SHAs) sind vor Verwendung zu **verifizieren**, nicht aus diesem Dokument zu übernehmen. Stellen, die das betrifft, sind mit *(verifizieren)* markiert.

---

## 1. Projekt

### 1.1 In einem Absatz

Politdrift zeigt, wie Mitglieder des eidgenössischen Parlaments (zuerst Nationalrat) und später der kantonalen Parlamente tatsächlich abstimmen. Das Abstimmungsverhalten wird auf die acht Achsen des Smartspiders verdichtet («Ist-Profil»), dem Wahlprofil gegenübergestellt («Soll-Profil», sofern verfügbar) und über die Zeit verfolgt («Drift»). Jede Zahl ist bis zur einzelnen Abstimmung nachvollziehbar.

### 1.2 Zielgruppen

1. Politisch interessierte Bürger:innen (Hauptzielgruppe, mobile-first)
2. Journalist:innen und Datenjournalismus (Einbettung, Downloads, Methodik)
3. Forschung und Civic-Tech (offene Daten, reproduzierbare Pipeline)

### 1.3 Nicht-Ziele

- Keine Wahlempfehlung, kein Ranking «gut/schlecht». Drift ist eine Beobachtung, keine Wertung.
- Keine personenbezogenen Daten ausser dem öffentlichen Mandatsverhalten (Name, Partei, Kanton, Stimmverhalten, öffentliche Profile).
- Kein Nachbau von Smartvote. Politdrift misst das Verhalten *nach* der Wahl.

### 1.4 Abgrenzung zu Bestehendem

- **smartmonitor.ch** (Politools): Abstimmungsmonitoring Nationalrat mit Themenratings. Politdrift unterscheidet sich durch den expliziten Soll/Ist-Vergleich, die Zeitachse (Drift), die Kantone und eine konsequent visuelle Aufbereitung.
- **OpenParlData.ch**: Dateninfrastruktur, kein Endnutzerprodukt. Politdrift ist Konsument und nennt die Quelle.

---

## 2. Methodik: Achsen, Mapping, Scoring

### 2.1 Die acht Achsen

Reihenfolge wie bei Smartvote (12-Uhr-Position, dann im Uhrzeigersinn) *(verifizieren)*:

| Key | Bezeichnung | Hoher Wert bedeutet |
|---|---|---|
| `aussenpolitik_offen` | Offene Aussenpolitik | Öffnung, EU-Annäherung, internationale Zusammenarbeit |
| `wirtschaft_liberal` | Liberale Wirtschaftspolitik | Deregulierung, weniger Staat im Markt |
| `finanzen_restriktiv` | Restriktive Finanzpolitik | Sparen, tiefe Steuern und Abgaben |
| `law_order` | Law & Order | Innere Sicherheit, härtere Strafen |
| `migration_restriktiv` | Restriktive Migrationspolitik | Zuwanderung begrenzen, strengeres Asylrecht |
| `umwelt_ausgebaut` | Ausgebauter Umweltschutz | Klima, Energie, Natur vor Wirtschaft |
| `sozialstaat_ausgebaut` | Ausgebauter Sozialstaat | Sozialwerke, Umverteilung, Service public |
| `gesellschaft_liberal` | Liberale Gesellschaft | Selbstbestimmung, Gleichstellung |

Werte 0–100. Hoher Wert = starke Zustimmung zur Achsenbezeichnung.

### 2.2 Mapping einer Abstimmung auf Achsen

Jede relevante Abstimmung erhält null bis drei Achsenzuordnungen, je mit **Richtung** und **Gewicht**:

```yaml
# data/mappings/nr/52.yaml  (Nationalrat, 52. Legislatur)
- vote_id: 31353
  business: "25.024"
  title: "Kriegsmaterialgesetz – Abweichungskompetenz des Bundesrates (Schlussabstimmung)"
  axes:
    - axis: wirtschaft_liberal
      direction: 1        # Ja-Stimme = in Achsenrichtung
      weight: 0.5
    - axis: law_order
      direction: 1
      weight: 0.3
  topics: [sicherheit_neutralitaet]   # Themenratings ausserhalb des Spiders
  source: manual         # smartvote | manual | llm
  confidence: 0.7
  contested: true        # wird im UI als «umstrittene Zuordnung» angezeigt
  reviewed: true
  reviewed_by: michschl
  reviewed_at: 2026-11-07
  note: >
    Aussenpolitik bewusst nicht zugeordnet: Konsistenz-Check gegen
    Partei-Spider negativ (SVP Ja bei «geschlossenem», SP/Grüne Nein
    bei «offenem» Aussenpolitik-Profil).
```

Regeln:

1. **Vergleichbarkeit vor Plausibilität.** Hat Smartvote zur gleichen Sachfrage eine Wahlfrage gestellt, wird deren Achsenzuordnung übernommen (`source: smartvote`), auch wenn eine inhaltliche Einordnung anders ausfiele. Nur so messen Soll und Ist mit demselben Massstab.
2. **Konsistenz-Check gegen Partei-Spider.** Zeigt die Lagerbildung einer Abstimmung entgegen der Reihenfolge der Partei-Spider auf einer Achse, ist die Achse falsch gewählt. Die Pipeline berechnet diesen Check automatisch und markiert Verstösse (`consistency_warning`).
3. **Nicht jede Abstimmung gehört in den Spider.** Verfahrensabstimmungen, Ordnungsanträge, Gesamtabstimmungen ohne klaren Achsenbezug und Querschnittsgeschäfte bleiben ohne Achse. Sie können in **Themenratings** (z. B. `sicherheit_neutralitaet`, `digitalisierung`, `landwirtschaft`) geführt werden.
4. **Nur geprüfte Mappings zählen.** `reviewed: false` fliesst nie in publizierte Profile.
5. **Mappings sind versionierte Daten** (YAML im Repo). Jede Änderung ist ein Commit mit Begründung.

### 2.3 Scoring

Für Person *p*, Achse *a* und Zeitfenster *w*:

```
s(p,v)   = +1 bei Ja, −1 bei Nein, 0 bei Enthaltung/Abwesenheit (zählt nicht)
S(p,a,w) = Σ_v [ weight(v,a) · direction(v,a) · s(p,v) ]  /  Σ_v [ weight(v,a) · |s(p,v)| ]
score    = (S + 1) / 2 · 100            # Normierung auf 0–100
```

- Mindestens `n_min = 8` zugeordnete, abgegebene Stimmen pro Achse und Fenster, sonst `null` («zu wenig Daten»).
- **Zeitfenster:** pro Session (Momentaufnahme), gleitend über die letzten 4 Sessionen (Standardanzeige) und kumuliert über die Legislatur.
- **Deckungsgrad** (nur mit Soll-Profil): `100 − Mittelwert(|soll_a − ist_a|)` über die verfügbaren Achsen.
- **Drift:** Veränderung des Ist-Profils über die Zeit (Vektor der Achsendifferenzen zwischen zwei Fenstern) sowie Distanz zum Soll-Profil pro Fenster.
- **Fraktionsdrift** (ohne Soll-Profil möglich): Distanz des Ist-Profils einer Person zum Ist-Profil ihrer Fraktion. Das ist der Standardvergleich, solange Smartvote-Daten fehlen.

Grenzen offen dokumentieren (`docs/METHODIK.md`, auch als Seite `/methodik`): Der Smartspider aus dem Fragebogen und der Ist-Spider aus Abstimmungen sind unterschiedlich konstruiert. Der Vergleich ist eine begründete Annäherung, keine exakte Messung.

### 2.4 Klassifikation mit LLM-Unterstützung

- Die Pipeline schlägt Mappings vor (`politdrift classify`): Eingaben sind Geschäftstitel, Abstimmungsgegenstand und die Felder «Bedeutung Ja / Bedeutung Nein». Ausgabe ist ein Mapping-Vorschlag mit `source: llm`, `reviewed: false`, Begründung und Konfidenz.
- Provider-Abstraktion: Anthropic API **oder** OpenAI-kompatibler Endpunkt (lokale Modelle). Konfiguration via Umgebungsvariablen, nie im Repo.
- Review-Workflow (`politdrift review`): CLI/TUI zum Annehmen, Ändern, Ablehnen. Erst danach `reviewed: true`.
- Prompt und Few-Shot-Beispiele liegen versioniert in `pipeline/politdrift/classify/`.

---

## 3. Datenquellen

### 3.1 Bund – Parlamentsdienste (Open Data Web Services)

- OData-Endpunkt: `https://ws.parlament.ch/odata.svc/` · Metadaten: `.../odata.svc/$metadata`
- Relevante Tabellen *(Felder gegen `$metadata` verifizieren)*:
  - `Person`, `MemberCouncil` (Ratsmitglieder, Fraktion, Kanton, Mandatszeiten)
  - `Voting` (eine Zeile pro Person und Abstimmung: `IdVote`, `PersonNumber`, `Decision`/`DecisionText`, `IdSession`, `IdLegislativePeriod`, `BusinessShortNumber`, `BusinessTitle`, `Subject`, `MeaningYes`, `MeaningNo`, `VoteEnd`, `ParlGroupName`)
  - `Vote` (Aggregat pro Abstimmung), `Session`, `LegislativePeriod`, `Business`
  - `SeatOrganisationNr` (Sitzordnung Nationalrat – Basis für den Hemicycle)
- Paging: `$top` max. 1000, `$skip`; immer `Language eq 'DE'` filtern. Inkrementell pro `IdSession` laden, nie blind alles.
- Legislatur 52 (2023–2027) ist der MVP-Umfang. Ältere Legislaturen später für Langzeit-Drift.
- `DecisionText` verwenden, Codes nicht hartkodieren.
- Nutzungsbedingungen beachten, Quelle nennen («Parlamentsdienste, parlament.ch»). Höflich abrufen (Rate-Limit clientseitig, Caching).

### 3.2 Kantone – OpenParlData.ch

- REST-API `https://api.openparldata.ch` (Swagger: `/documentation`, OpenAPI: `/openapi.json`), Bulk-Exports als gzipped NDJSON unter `files.openparldata.ch/exports/`.
- Lizenz CC BY 4.0, Attribution «Source: OpenParlData.ch». Beta-Status: Datenqualität pro Parlament prüfen und im UI ausweisen.
- Nur Kantone mit elektronischer Abstimmungsanlage liefern Einzelstimmen. Die Abdeckung ist lückenhaft und wird auf der Schweizer Karte **ehrlich** dargestellt («Daten vorhanden», «nur Aggregat», «keine Einzelstimmen publiziert»).
- Ergänzende direkte OGD-Quellen, wo vorhanden (z. B. Thurgau `data.tg.ch`, Basel-Stadt `data.bs.ch`); harmonisieren auf das eigene Datenmodell.

### 3.3 Soll-Profile – Smartvote (Politools)

- Smartspider-Daten sind **kein Open Data**. Nutzung nur mit Vereinbarung mit Politools. Kein Scraping.
- Das Datenmodell hält `profile_election` als austauschbaren Adapter bereit. Bis zur Vereinbarung läuft der Vergleich über Fraktionsdrift und Drift über die Zeit.
- Smartvote publiziert pro Wahl die Zuordnung der Fragen zu den Achsen (PDF). Diese dient als Referenz für `source: smartvote`-Mappings.

### 3.4 Volksabstimmungen (Bonus, Phase 3+)

- Resultate pro Kanton (BFS via opendata.swiss, swissvotes.ch) für den Vergleich «Ratsmitglied vs. Stimmvolk seines Kantons» bei Vorlagen, die das Parlament zuvor behandelt hat.

---

## 4. Architektur

### 4.1 Prinzip

**Statisch vorberechnet, kein Backend im Betrieb.** Die Pipeline erzeugt versionierte JSON-Daten, das Frontend wird daraus statisch gebaut, ein Container liefert die Dateien hinter Caddy aus. Vorteile: minimale Angriffsfläche, tiefe Kosten, hohe Geschwindigkeit, jede Datenänderung ist ein Git-Commit (auditierbar).

```
 ws.parlament.ch ─┐
 OpenParlData    ─┼─▶ pipeline (Python/uv, DuckDB) ─▶ data/derived/**.json ─▶ Commit via Data-PR
 OGD Kantone     ─┘                                                   │
                                                                      ▼
 GitHub Actions: Quality ─▶ Security (CodeQL, Dep-Review, Trivy) ─▶ Build (SvelteKit static → Image) ─▶ GHCR
                                                                      │  Attestation (Provenance)
                                                                      ▼
 Infomaniak VPS: Caddy (TLS, Header) ─▶ web (nginx-unprivileged, read-only) ◀── SSH-Deploy mit Forced Command
```

Später optional: kleine API (FastAPI) für Suche/Embeds, DuckDB-WASM im Browser für Ad-hoc-Analysen. Nicht im MVP.

### 4.2 Datenmodell (DuckDB im Pipeline-Cache, Pydantic-Modelle als Vertrag)

| Tabelle | Inhalt |
|---|---|
| `bodies` | Parlamente (`nr`, `sr`, `zh_kr`, …), Name, Ebene, Datenquelle, Abdeckungsstatus |
| `legislatures` | Legislatur je Body, Zeitraum |
| `sessions` | Session je Legislatur, Zeitraum |
| `persons` | Stabile `person_id` (Quelle + Quell-ID), Name, Kanton |
| `memberships` | Person × Body × Zeitraum, Partei, Fraktion, Sitznummer |
| `votes` | Abstimmung: Body, Session, Datum, Geschäft, Titel, Gegenstand, Bedeutung Ja/Nein, Resultat |
| `ballots` | Person × Vote → Entscheid |
| `axis_mappings` | aus `data/mappings/**/*.yaml` (Abschnitt 2.2) |
| `profiles_voting` | Person × Fenster × Achse → Score, n |
| `profiles_election` | Person × Wahl × Achse → Soll-Wert (Adapter, optional) |

### 4.3 Export-Format (statisch, versioniert)

```
data/derived/
  meta.json                         # generated_at, Quellen, Zähler, Pipeline-Version
  nr/52/
    index.json                      # alle Mitglieder mit Kurzprofil (für Übersicht/Suche)
    parties.json                    # Fraktions-Ist-Spider pro Fenster
    persons/<person_id>.json        # Profile je Fenster, Driftserie, Ballots mit Mapping-Referenz
    votes/<vote_id>.json            # Abstimmungsdetail, Mapping, Abweichler je Fraktion
    seats.json                      # Hemicycle-Koordinaten
```

Budget: `persons/*.json` ≤ 300 KB gzipped. Rohdaten (Millionen Ballot-Zeilen) werden **nicht** ins Repo committet, sondern im Pipeline-Cache gehalten (Actions-Cache/lokal) und inkrementell aktualisiert.

---

## 5. Repo-Struktur

```
politdrift/
├─ CLAUDE.md                     # Arbeitsanweisungen für Claude Code (Anhang B)
├─ README.md                     # Projekt, Quickstart, Badges
├─ LICENSE                       # Code-Lizenz (Entscheid offen, Abschnitt 11)
├─ SECURITY.md                   # Responsible Disclosure, Kontakt
├─ CONTRIBUTING.md
├─ .github/
│  ├─ CODEOWNERS                 # * @michschl
│  ├─ dependabot.yml
│  ├─ PULL_REQUEST_TEMPLATE.md
│  ├─ ISSUE_TEMPLATE/
│  └─ workflows/
│     ├─ cicd.yml                # Quality → Security → Build → Deploy (Abschnitt 7)
│     ├─ data-refresh.yml        # Pipeline-Lauf nach Zeitplan → Data-PR
│     └─ uptime.yml              # Verfügbarkeitscheck (optional)
├─ web/                          # SvelteKit (adapter-static), TypeScript, Tailwind, D3
├─ pipeline/                     # Python 3.12, uv, DuckDB, Typer-CLI «politdrift»
├─ data/
│  ├─ mappings/<body>/<legislature>.yaml
│  └─ derived/                   # generiert, committet (Abschnitt 4.3)
├─ infra/
│  ├─ Dockerfile.web
│  ├─ nginx.conf
│  ├─ compose.yml                # läuft auf dem VPS unter /opt/politdrift
│  ├─ Caddyfile
│  ├─ deploy.sh                  # Forced Command für den SSH-Deploy-User
│  ├─ vps/bootstrap.sh           # idempotente Grundinstallation
│  └─ github/ruleset-main.json   # Branch-Ruleset als Code
└─ docs/
   ├─ KONZEPT.md                 # dieses Dokument
   ├─ METHODIK.md                # öffentlich, wird als /methodik publiziert
   ├─ RUNBOOK.md                 # Betrieb, Notfall, Rollback
   └─ adr/
```

---

## 6. Tech-Stack und Konventionen

### 6.1 Web (`web/`)

- **SvelteKit** mit `@sveltejs/adapter-static` (vollständiges Prerendering), **TypeScript strict**, **Tailwind CSS**, **D3** nur modular (`d3-shape`, `d3-scale`, `d3-interpolate`, `d3-selection`) für Spider, Morph-Animation, Hemicycle.
- Tests: **Vitest** (Unit), **Playwright** (E2E, Smoke), `svelte-check`, ESLint, Prettier.
- i18n von Anfang an vorbereitet (Schlüssel statt Literale), UI zuerst Deutsch; FR/IT später.
- CSP-tauglich bauen: `kit.csp` im Hash-Modus, keine Inline-Skripte von Dritten, Schriften selbst hosten, keine externen Requests zur Laufzeit.
- Build erzeugt `static/version.json` (`{"sha": "<GITHUB_SHA kurz>", "built_at": "…"}`) und `static/healthz` (`ok`).
- Performance-Budget: Lighthouse ≥ 90 in allen Kategorien, JS ≤ 150 KB gzipped auf der Personenseite, LCP < 2.5 s auf 4G.
- Barrierefreiheit: WCAG 2.1 AA, farbenblind-sichere Palette, jeder Spider hat eine Tabellenansicht mit Zahlenwerten, `prefers-reduced-motion` respektieren.

### 6.2 Pipeline (`pipeline/`)

- Python 3.12, **uv** (Lockfile committet), `httpx`, `pydantic` v2, **DuckDB**, `typer`, `pyyaml`; Qualität: `ruff` (lint+format), `pyright`, `pytest` mit Fixtures aus aufgezeichneten API-Antworten (keine Netzwerkzugriffe in Tests).
- CLI `politdrift` mit Subkommandos: `fetch`, `classify`, `review`, `compute`, `export`, `validate`.
- `validate` prüft Mapping-YAML gegen Schema, Achsen-Keys, Richtungen, Pflichtfelder, Review-Status.

### 6.3 Konventionen

- **Conventional Commits** (`feat:`, `fix:`, `data:`, `chore:`, `docs:`, `ci:`), PR-basiert, CI grün vor Merge, Squash-Merge.
- Code, Kommentare, Commit-Messages: Englisch. UI-Texte und Dokumentation: Deutsch, Schweizer Rechtschreibung (kein «ß»).
- Keine Datei > 1 MB im Repo ausser bewusst dokumentierte Ausnahmen.

### 6.4 Visualisierung (Wow-Faktor, priorisiert)

**P1 (MVP)**
- Personenseite: Spider mit **Ist-Profil** (gefüllt) und Vergleichsprofil (gestrichelt: Fraktion oder Soll-Profil). **Zeit-Slider** über Sessionen morpht die Form animiert.
- Achsen-Drilldown: Klick auf eine Achse zeigt die Abstimmungen, die sie geprägt haben («Diese 12 Stimmen haben die Achse gezogen»), mit Gewicht und Richtung.
- Ratsübersicht mit Mini-Spidern, Filter nach Fraktion/Kanton, Sortierung nach Drift. Suche.

**P2**
- **Hemicycle** (Sitzplan Nationalrat), jeder Sitz nach Drift oder Deckungsgrad eingefärbt; Hover zeigt Mini-Spider, Klick öffnet Person.
- Abstimmungs-Explorer: Resultat, Mapping, Abweichler je Fraktion.
- Teilbare Profilkarten (OG-Images pro Person, beim Build generiert).
- Ranglisten «grösste Drift», «stabilstes Profil», «grösste Fraktionsabweichung» – neutral formuliert.

**P3**
- Schweizer Karte für kantonale Parlamente mit Abdeckungsstatus.
- Zwei Personen direkt vergleichen; Embed-Widget für Medien; FR/IT.

---

## 7. CI/CD und Sicherheit mit GitHub-Bordmitteln

### 7.1 Überblick

| Was | Werkzeug | Wann |
|---|---|---|
| Lint, Typecheck, Tests, Build | npm-Skripte, ruff, pyright, pytest | PR + Push `main` |
| Statische Code-Analyse | **CodeQL** (javascript-typescript, python, actions) | PR + Push `main` + wöchentlich |
| Abhängigkeits-Review | **Dependency Review Action** (fail ab `high`) | PR |
| Abhängigkeits-Updates & Alerts | **Dependabot** (npm, uv, github-actions, docker) | wöchentlich |
| Secrets | **Secret Scanning + Push Protection** | immer |
| Container-Scan | Trivy (Drittanbieter-Action, Ergebnis als SARIF ins Code Scanning) | Push `main`, vor dem Image-Push |
| Herkunftsnachweis | **Artifact Attestations** (`actions/attest-build-provenance`) | nach Image-Push |
| Deploy | SSH mit Forced Command, Smoke-Test, automatischer Rollback | Push `main`, nur wenn alles grün |

Hinweis zu Kosten: CodeQL, Secret Scanning und Dependency Review sind für **öffentliche** Repos kostenlos; für private Repos brauchen sie die kostenpflichtigen Add-ons «GitHub Code Security» / «Secret Protection». Empfehlung: Repo öffentlich (passt zur Transparenzmission). Entscheid in Abschnitt 11.

### 7.2 Hauptworkflow `.github/workflows/cicd.yml`

Alle `uses:`-Referenzen sind auf den **Commit-SHA** der aktuellen Major-Version zu pinnen (Kommentar mit Version dahinter). Versionen *(verifizieren)*.

```yaml
name: CI/CD

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]
  schedule:
    - cron: "17 4 * * 1"      # CodeQL wöchentlich
  workflow_dispatch:

permissions:
  contents: read

concurrency:
  group: cicd-${{ github.ref }}
  cancel-in-progress: ${{ github.event_name == 'pull_request' }}

env:
  IMAGE: ghcr.io/michschl/politdrift-web

jobs:
  web-quality:
    name: web-quality
    runs-on: ubuntu-latest
    timeout-minutes: 15
    defaults:
      run:
        working-directory: web
    steps:
      - uses: actions/checkout@<sha>                 # v5
      - uses: actions/setup-node@<sha>               # v5
        with:
          node-version: 22
          cache: npm
          cache-dependency-path: web/package-lock.json
      - run: npm ci
      - run: npm run lint
      - run: npm run check
      - run: npm test -- --run
      - run: npm audit --audit-level=high
      - run: npm run build
        env:
          PUBLIC_BUILD_SHA: ${{ github.sha }}
      - uses: actions/upload-artifact@<sha>          # v4
        with:
          name: web-build
          path: web/build
          retention-days: 7

  pipeline-quality:
    name: pipeline-quality
    runs-on: ubuntu-latest
    timeout-minutes: 15
    defaults:
      run:
        working-directory: pipeline
    steps:
      - uses: actions/checkout@<sha>                 # v5
      - uses: astral-sh/setup-uv@<sha>               # v6 (Drittanbieter; Alternative: actions/setup-python + pip)
        with:
          enable-cache: true
      - run: uv sync --frozen
      - run: uv run ruff check . && uv run ruff format --check .
      - run: uv run pyright
      - run: uv run pytest
      - run: uv run politdrift validate ../data/mappings
      - run: uvx pip-audit --strict

  codeql:
    name: codeql
    runs-on: ubuntu-latest
    timeout-minutes: 30
    permissions:
      contents: read
      security-events: write
    strategy:
      fail-fast: false
      matrix:
        language: [javascript-typescript, python, actions]
    steps:
      - uses: actions/checkout@<sha>                 # v5
      - uses: github/codeql-action/init@<sha>        # v4
        with:
          languages: ${{ matrix.language }}
          queries: security-extended
      - uses: github/codeql-action/analyze@<sha>     # v4
        with:
          category: "/language:${{ matrix.language }}"

  dependency-review:
    name: dependency-review
    if: github.event_name == 'pull_request'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@<sha>                 # v5
      - uses: actions/dependency-review-action@<sha> # v4
        with:
          fail-on-severity: high
          comment-summary-in-pr: always

  build-image:
    name: build-image
    if: github.event_name == 'push' && github.ref == 'refs/heads/main'
    needs: [web-quality, pipeline-quality, codeql]
    runs-on: ubuntu-latest
    timeout-minutes: 20
    permissions:
      contents: read
      packages: write
      id-token: write
      attestations: write
      security-events: write
    outputs:
      tag: ${{ steps.meta.outputs.version }}
      digest: ${{ steps.push.outputs.digest }}
    steps:
      - uses: actions/checkout@<sha>                 # v5
      - uses: actions/download-artifact@<sha>        # v4
        with:
          name: web-build
          path: web/build
      - uses: docker/setup-buildx-action@<sha>       # v3
      - uses: docker/login-action@<sha>              # v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}
      - id: meta
        uses: docker/metadata-action@<sha>           # v5
        with:
          images: ${{ env.IMAGE }}
          tags: |
            type=sha,prefix=sha-,format=short
            type=raw,value=latest
      - name: Build (lokal, noch kein Push)
        uses: docker/build-push-action@<sha>         # v6
        with:
          context: .
          file: infra/Dockerfile.web
          load: true
          push: false
          tags: local/politdrift-web:scan
          cache-from: type=gha
          cache-to: type=gha,mode=max
      - name: Trivy – Image-Scan (blockiert bei HIGH/CRITICAL)
        uses: aquasecurity/trivy-action@<sha>        # Drittanbieter
        with:
          image-ref: local/politdrift-web:scan
          severity: CRITICAL,HIGH
          ignore-unfixed: true
          exit-code: "1"
          format: sarif
          output: trivy.sarif
      - name: Trivy – SARIF ins Code Scanning
        if: always()
        uses: github/codeql-action/upload-sarif@<sha> # v4
        with:
          sarif_file: trivy.sarif
          category: trivy-image
      - id: push
        name: Push nach GHCR
        uses: docker/build-push-action@<sha>         # v6
        with:
          context: .
          file: infra/Dockerfile.web
          push: true
          tags: ${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}
          cache-from: type=gha
      - uses: actions/attest-build-provenance@<sha>  # v3
        with:
          subject-name: ${{ env.IMAGE }}
          subject-digest: ${{ steps.push.outputs.digest }}
          push-to-registry: true

  deploy:
    name: deploy
    needs: build-image
    runs-on: ubuntu-latest
    timeout-minutes: 10
    environment:
      name: production
      url: https://politdrift.org
    concurrency:
      group: deploy-production
      cancel-in-progress: false
    steps:
      - name: SSH-Deploy (Forced Command auf dem VPS)
        env:
          SSH_KEY: ${{ secrets.VPS_SSH_KEY }}
          KNOWN_HOSTS: ${{ secrets.VPS_KNOWN_HOSTS }}
          HOST: ${{ secrets.VPS_HOST }}
          TAG: ${{ needs.build-image.outputs.tag }}
        run: |
          install -m 700 -d ~/.ssh
          printf '%s\n' "$SSH_KEY" > ~/.ssh/id_ed25519
          chmod 600 ~/.ssh/id_ed25519
          printf '%s\n' "$KNOWN_HOSTS" > ~/.ssh/known_hosts
          ssh -o StrictHostKeyChecking=yes -o BatchMode=yes "deploy@${HOST}" "${TAG}"
      - name: Smoke-Test (richtige Version live?)
        run: |
          expected="${GITHUB_SHA::7}"
          for i in $(seq 1 12); do
            live="$(curl -fsS https://politdrift.org/version.json | jq -r .sha || true)"
            if [ "$live" = "$expected" ]; then echo "live: $live"; exit 0; fi
            sleep 5
          done
          echo "Smoke-Test fehlgeschlagen: live=$live expected=$expected" >&2
          exit 1
```

Logik: `deploy` läuft nur bei Push auf `main` und nur, wenn `web-quality`, `pipeline-quality`, `codeql` und der Trivy-Scan bestanden sind. Das Image wird erst nach dem Scan gepusht. Der Deploy-Schlüssel kann auf dem VPS **nur** `deploy.sh` ausführen (Abschnitt 8.4).

### 7.3 Daten-Aktualisierung `.github/workflows/data-refresh.yml`

- Zeitplan: wöchentlich (während Sessionen täglich via zweitem Cron), plus `workflow_dispatch`.
- Ablauf: `uv run politdrift fetch --body nr --legislature 52` (Cache via `actions/cache`), `compute`, `export`, `validate`. Falls `git diff --quiet -- data/derived` → Ende. Sonst Branch `data/refresh-YYYY-MM-DD`, Commit `data: refresh nr/52 (YYYY-MM-DD)`, PR via `gh pr create`, `gh pr merge --auto --squash`.
- **Wichtig:** Pushes und PRs, die mit dem `GITHUB_TOKEN` erstellt werden, lösen **keine** weiteren Workflow-Läufe aus – der Data-PR bekäme keine Checks und würde nie auto-mergen. Deshalb Token einer eigenen **GitHub App** («politdrift-bot», nur auf diesem Repo installiert, Rechte: Contents + Pull Requests) via `actions/create-github-app-token` (GitHub-eigene Action) verwenden. App-ID und Private Key als Secrets.
- LLM-Klassifikation läuft **nicht** automatisch im Zeitplan; neue, noch nicht gemappte Abstimmungen werden im PR aufgelistet («42 neue Abstimmungen ohne Mapping»). Review bleibt manuell.

### 7.4 Dependabot `.github/dependabot.yml`

```yaml
version: 2
updates:
  - package-ecosystem: github-actions
    directory: /
    schedule:
      interval: weekly
    groups:
      actions:
        patterns: ["*"]
  - package-ecosystem: npm
    directory: /web
    schedule:
      interval: weekly
    groups:
      dev-dependencies:
        dependency-type: development
      prod-minor-patch:
        dependency-type: production
        update-types: [minor, patch]
  - package-ecosystem: uv            # falls nicht verfügbar: pip mit exportierten requirements
    directory: /pipeline
    schedule:
      interval: weekly
  - package-ecosystem: docker
    directory: /infra
    schedule:
      interval: weekly
```

### 7.5 Repo-Einstellungen (einmalig, via `gh`/REST oder UI)

1. Sichtbarkeit: **public** (Entscheid Abschnitt 11).
2. `gh repo edit michschl/politdrift --enable-auto-merge --delete-branch-on-merge --enable-squash-merge --enable-merge-commit=false --enable-rebase-merge=false`
3. Security & Analysis: Dependabot Alerts + Security Updates (`PUT /repos/{o}/{r}/vulnerability-alerts`, `PUT /repos/{o}/{r}/automated-security-fixes`), Secret Scanning + Push Protection (`PATCH /repos/{o}/{r}` → `security_and_analysis`), Private Vulnerability Reporting (`PUT /repos/{o}/{r}/private-vulnerability-reporting`). Code Scanning läuft über den Workflow (Advanced Setup) – **kein** Default Setup zusätzlich aktivieren.
4. Actions-Berechtigungen: Default Workflow Permissions **read-only**; Actions nur von GitHub und verifizierten Erstellern plus explizite Allowlist (`astral-sh/setup-uv@*`, `docker/*`, `aquasecurity/trivy-action@*`); Approval für Workflows aus Fork-PRs erforderlich.
5. Environment `production` mit Secrets `VPS_HOST`, `VPS_SSH_KEY` (ed25519, nur für Deploy), `VPS_KNOWN_HOSTS`. Repo-Secrets für die GitHub App (`DATA_BOT_APP_ID`, `DATA_BOT_PRIVATE_KEY`).
6. Ruleset `main` aus `infra/github/ruleset-main.json` (`POST /repos/{o}/{r}/rulesets`): Löschen und Force-Push verboten, lineare History, PR erforderlich (0 Reviews – Solo-Entwicklung), Status-Checks `web-quality`, `pipeline-quality`, `codeql (javascript-typescript)`, `codeql (python)`, `codeql (actions)` erforderlich (Kontextnamen nach dem ersten Lauf verifizieren), Bypass nur für Repository-Admin.
7. GHCR-Package `politdrift-web` auf **public** stellen, damit der VPS ohne Credentials pullen kann (sonst Fine-grained Token mit `read:packages` in `/opt/politdrift/.env`).

---

## 8. VPS (Infomaniak): Provisionierung und Deployment

### 8.1 Grundsätze

- Der VPS ist **zustandslos** bezüglich Anwendung: alles kommt aus Image und Repo. Rebuild aus `bootstrap.sh` + ein Deploy muss jederzeit möglich sein.
- Keine manuellen Änderungen ausser Bootstrap und dokumentierten Notfällen (`docs/RUNBOOK.md`).
- Infomaniak-Snapshots wöchentlich (Manager), Firewall im Infomaniak-Manager zusätzlich auf 22/80/443 begrenzen.

### 8.2 Bootstrap (`infra/vps/bootstrap.sh`, idempotent, Ubuntu 24.04 LTS)

1. System aktualisieren, `unattended-upgrades` aktivieren (Security-Updates automatisch, Reboot-Fenster nachts).
2. User `admin` (sudo, nur SSH-Key) und User `deploy` (kein sudo, Docker-Gruppe, nur Forced Command). Root-Login aus.
3. SSH-Härtung als Drop-in `/etc/ssh/sshd_config.d/99-hardening.conf`: `PasswordAuthentication no`, `PermitRootLogin no`, `KbdInteractiveAuthentication no`, `X11Forwarding no`, `AllowUsers admin deploy`, moderne KEX/Cipher.
4. `ufw`: default deny incoming, allow 22/tcp, 80/tcp, 443/tcp, 443/udp (HTTP/3). `fail2ban` für sshd.
5. Docker Engine + Compose-Plugin aus dem offiziellen Docker-Repo; Log-Rotation (`json-file`, `max-size 10m`, `max-file 5`); `live-restore: true`.
6. `/opt/politdrift/` (Owner `deploy`): `compose.yml`, `Caddyfile`, `.env` (`IMAGE_TAG=…`), `deploy.sh` (0755, Owner root, damit `deploy` ihn nicht ändern kann).
7. `authorized_keys` von `deploy` mit Forced Command (Abschnitt 8.4). SSH-Hostkey-Fingerprint ausgeben → Secret `VPS_KNOWN_HOSTS`.

Optionale Härtung (ADR, wenn gewünscht): Rootless Docker (`net.ipv4.ip_unprivileged_port_start=80`), SSH für `admin` nur über das bestehende Headscale-Tailnet, Deploy pull-basiert ohne eingehendes SSH (Watchtower/Cron pollt GHCR) – dann entfällt der SSH-Secret in GitHub, dafür weniger Sichtbarkeit des Deploys in Actions.

### 8.3 Compose und Caddy

```yaml
# infra/compose.yml  → /opt/politdrift/compose.yml
services:
  caddy:
    image: caddy:2-alpine          # auf Digest pinnen
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
      - "443:443/udp"
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile:ro
      - caddy_data:/data
      - caddy_config:/config
    depends_on:
      web:
        condition: service_healthy
    security_opt:
      - no-new-privileges:true

  web:
    image: ghcr.io/michschl/politdrift-web:${IMAGE_TAG}
    restart: unless-stopped
    read_only: true
    tmpfs:
      - /tmp
    cap_drop: [ALL]
    security_opt:
      - no-new-privileges:true
    ports:
      - "127.0.0.1:8080:8080"      # nur lokal, für Healthcheck im deploy.sh
    healthcheck:
      test: ["CMD", "wget", "-qO-", "http://127.0.0.1:8080/healthz"]
      interval: 10s
      timeout: 3s
      retries: 5

volumes:
  caddy_data: {}
  caddy_config: {}
```

```caddyfile
# infra/Caddyfile
politdrift.org {
    encode zstd gzip
    header {
        Strict-Transport-Security "max-age=31536000; includeSubDomains; preload"
        Content-Security-Policy "default-src 'self'; img-src 'self' data:; style-src 'self'; script-src 'self'; connect-src 'self'; font-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
        X-Content-Type-Options "nosniff"
        Referrer-Policy "strict-origin-when-cross-origin"
        Permissions-Policy "camera=(), microphone=(), geolocation=()"
        -Server
    }
    reverse_proxy web:8080
}

www.politdrift.org {
    redir https://politdrift.org{uri} permanent
}
```

CSP in Phase 1 gegen den realen SvelteKit-Build feinjustieren (Hashes aus `kit.csp`); `'unsafe-inline'` ist nicht akzeptabel.

`infra/Dockerfile.web`: `nginxinc/nginx-unprivileged:<version>-alpine` (auf Digest pinnen), eigene `nginx.conf` (Port 8080, Cache-Header: `immutable` für gehashte Assets, kurz für `index.html`/`version.json`, `/healthz`), `COPY web/build/ /usr/share/nginx/html/`, `HEALTHCHECK`. Keine Build-Stage im Dockerfile – der Build kommt als Artefakt aus dem Quality-Job (ein Build, ein Artefakt, ein Image).

### 8.4 `deploy.sh` und Forced Command

`/home/deploy/.ssh/authorized_keys`:

```
command="/opt/politdrift/deploy.sh",no-port-forwarding,no-agent-forwarding,no-X11-forwarding,no-pty ssh-ed25519 AAAA… github-actions-deploy
```

```bash
#!/usr/bin/env bash
# /opt/politdrift/deploy.sh – wird ausschliesslich als SSH Forced Command ausgeführt
set -euo pipefail
cd /opt/politdrift

TAG="${SSH_ORIGINAL_COMMAND:-}"
[[ "$TAG" =~ ^sha-[0-9a-f]{7,40}$ ]] || { echo "invalid tag: $TAG" >&2; exit 2; }

PREV="$(sed -n 's/^IMAGE_TAG=//p' .env)"
sed -i "s/^IMAGE_TAG=.*/IMAGE_TAG=${TAG}/" .env

docker compose pull --quiet web
docker compose up -d --no-deps web

for i in $(seq 1 20); do
  if curl -fsS http://127.0.0.1:8080/healthz >/dev/null 2>&1; then
    echo "deployed ${TAG} (previous ${PREV})"
    docker image prune -f --filter "until=168h" >/dev/null 2>&1 || true
    exit 0
  fi
  sleep 3
done

echo "healthcheck failed for ${TAG}, rolling back to ${PREV}" >&2
sed -i "s/^IMAGE_TAG=.*/IMAGE_TAG=${PREV}/" .env
docker compose up -d --no-deps web
exit 1
```

Optional nach dem Pull: Provenance prüfen mit `gh attestation verify oci://ghcr.io/michschl/politdrift-web:${TAG} --owner michschl` (benötigt `gh` auf dem VPS).

### 8.5 DNS (Infomaniak)

- `A`/`AAAA` für `politdrift.org` und `www` → VPS. TTL anfangs 300 s.
- `CAA 0 issue "letsencrypt.org"` (Caddy nutzt Let's Encrypt/ZeroSSL – zweiten Issuer ergänzen, falls Fallback gewünscht).
- Später: `politdrift.ch` als Weiterleitung registrieren (Schweizer Publikum).

### 8.6 Betrieb

- `uptime.yml`: alle 30 Minuten `curl -f https://politdrift.org/healthz`; bei Fehler schlägt der Lauf fehl → GitHub-Benachrichtigung. Alternativ externer Uptime-Dienst.
- `docs/RUNBOOK.md`: Rollback manuell (`ssh admin@…`, `IMAGE_TAG` auf Vorgänger setzen, `docker compose up -d web`), Zertifikatsprobleme, Logs (`docker compose logs`), Rebuild von null.
- `/.well-known/security.txt` mit Kontakt und Policy (SECURITY.md).

---

## 9. Phasenplan mit Abnahmekriterien

### Phase 0 – Repo initialisieren (erste Aufgabe für Claude Code)

Arbeite auf Branch `chore/phase-0-init`, ein PR am Ende.

1. Grundgerüst gemäss Abschnitt 5 anlegen: `README.md`, `CLAUDE.md` (Anhang B), `SECURITY.md`, `CONTRIBUTING.md`, `.github/CODEOWNERS`, PR-Template, `.gitignore`, `.editorconfig`, `LICENSE`-Platzhalter mit `TODO`-Hinweis auf Abschnitt 11.
2. `web/`: SvelteKit (adapter-static) + TypeScript strict + Tailwind + Vitest + Playwright + ESLint/Prettier. Startseite «Politdrift – Gesagt. Gestimmt.» mit einem statischen, aber korrekt gezeichneten Beispiel-Spider (acht Achsen, Reihenfolge gemäss 2.1) aus Dummy-Daten. `version.json`, `healthz`, `robots.txt`, Seiten `/methodik`, `/impressum`, `/datenschutz` als Platzhalter. `kit.csp` Hash-Modus aktiv.
3. `pipeline/`: uv-Projekt, Paket `politdrift`, Typer-CLI mit allen Subkommandos als Stubs, `validate` funktionsfähig (Schema-Prüfung für Mapping-YAML), Pydantic-Modelle gemäss 4.2, Tests für `validate` und Scoring-Funktion (Abschnitt 2.3, reine Funktion mit Unit-Tests inkl. `n_min`-Fall).
4. `data/mappings/nr/52.yaml` mit dem Kriegsmaterial-Beispiel aus 2.2; `data/derived/.gitkeep`.
5. `infra/`: `Dockerfile.web`, `nginx.conf`, `compose.yml`, `Caddyfile`, `deploy.sh`, `vps/bootstrap.sh`, `github/ruleset-main.json`.
6. `.github/workflows/cicd.yml`, `data-refresh.yml` (mit `workflow_dispatch`, Cron zunächst auskommentiert), `uptime.yml`; `.github/dependabot.yml`. Alle Actions auf SHA gepinnt.
7. `docs/METHODIK.md` (Inhalt aus Abschnitt 2 in publizierbarer Form), `docs/RUNBOOK.md` (Gerüst), `docs/adr/0001-static-first-architecture.md`, `docs/adr/0002-ssh-forced-command-deploy.md`.
8. Repo-Einstellungen gemäss 7.5 per `gh` setzen, soweit Rechte vorhanden; Rest als Checkliste im PR.

**Abnahme Phase 0**
- `cicd.yml` ist auf dem PR grün (`web-quality`, `pipeline-quality`, `codeql ×3`, `dependency-review`).
- `docker build -f infra/Dockerfile.web .` baut lokal; Container antwortet auf `/healthz` und `/version.json`.
- `uv run politdrift validate data/mappings` läuft fehlerfrei; ein absichtlich fehlerhaftes Mapping wird abgelehnt (Test).
- Lighthouse auf der Startseite ≥ 90 in allen Kategorien.
- Keine `uses:` ohne SHA-Pin; `permissions:` pro Job minimal.

### Phase 1 – VPS und erstes Deployment

- `bootstrap.sh` auf dem Infomaniak-VPS ausführen (manuell durch Michael, Anleitung in RUNBOOK), DNS setzen, Secrets im Environment `production` hinterlegen, GHCR-Package public.
- Erster Push auf `main` deployt die Platzhalter-Seite.

**Abnahme:** `https://politdrift.org` liefert die Seite mit A+ bei SSL Labs und allen Headern aus 8.3 (Mozilla Observatory ≥ A). Smoke-Test grün. Ein absichtlich defektes Image (Healthcheck schlägt fehl) löst den Rollback aus – einmal getestet und im RUNBOOK dokumentiert.

### Phase 2 – Pipeline Nationalrat (Legislatur 52)

- `fetch`: Personen, Mitgliedschaften, Sitzordnung, Abstimmungen und Ballots inkrementell pro Session in DuckDB; Fixtures für Tests aufzeichnen.
- `classify` + `review`: LLM-Vorschläge, Review-Workflow, Konsistenz-Check gegen Fraktions-Spider.
- `compute` + `export`: Profile, Fraktionsdrift, Drift-Serien, Export gemäss 4.3.
- Mindestens 150 geprüfte Mappings über alle acht Achsen, sodass jede Achse `n_min` für alle Ratsmitglieder erreicht.
- `data-refresh.yml` scharf schalten (GitHub App).

**Abnahme:** Reproduzierbarer Lauf von null (`fetch → compute → export`) in < 20 Minuten; Export validiert gegen JSON-Schema; stichprobenartiger Abgleich von 10 Ballots gegen das Abstimmungsprotokoll auf parlament.ch stimmt.

### Phase 3 – Frontend MVP (P1-Features aus 6.4)

- Ratsübersicht, Personenseite mit Spider, Zeit-Slider, Achsen-Drilldown, Abstimmungsdetail, Suche, Methodik-Seite mit echten Zahlen (Anzahl Abstimmungen, Mappings, Abdeckung).
- OG-Images und Hemicycle, wenn Zeit bleibt (P2).

**Abnahme:** Nutzertest mit drei Personen ausserhalb des Projekts: Jede findet in < 1 Minute ein Ratsmitglied, versteht den Spider und kann eine Achse bis zur Einzelabstimmung nachvollziehen. Performance-Budget eingehalten. Barrierefreiheit per axe ohne kritische Befunde.

### Phase 4 – Soll-Profile

- Vereinbarung mit Politools (Michael). Adapter `profile_election` implementieren, Deckungsgrad und Soll/Ist-Overlay freischalten, `source: smartvote`-Mappings anhand der publizierten Fragenzuordnung ergänzen.
- Fallback ohne Vereinbarung: UI bleibt bei Fraktionsdrift und Zeitdrift; Hinweis auf Datenlage.

### Phase 5 – Kantone

- OpenParlData-Adapter, Pilot Zürich oder Thurgau, dann Ausrollen. Karte mit Abdeckungsstatus. Mappings pro Kantonsparlament (eigene YAML-Dateien, eigene Reviewer:innen möglich).

---

## 10. Leitplanken (immer gültig)

**Sicherheit**
- Keine Secrets im Repo, auch nicht in Tests oder Fixtures. Secrets nur in GitHub Environments und in `/opt/politdrift/.env` auf dem VPS.
- Alle GitHub Actions auf Commit-SHA gepinnt; `permissions:` pro Job minimal; Drittanbieter-Actions nur die in 7.5 genannten, jede weitere braucht ein ADR.
- Deployment ausschliesslich über den Workflow. Kein `docker compose up` von Hand ausser im dokumentierten Notfall.
- Container: non-root, read-only, `cap_drop ALL`, Images auf Digest gepinnt, Dependabot aktualisiert.
- Keine externen Skripte, Fonts, Analytics oder Embeds zur Laufzeit. CSP ohne `unsafe-*`.

**Daten und Recht**
- Nur öffentliches Mandatsverhalten. Keine Bewertungen, keine Mutmassungen über Motive.
- Quellen auf jeder Seite nennen: Parlamentsdienste (parlament.ch), OpenParlData.ch (CC BY 4.0), Smartvote/Politools (sofern vereinbart). Datenstand sichtbar.
- Methodik öffentlich, jede Zahl bis zur Einzelabstimmung klickbar.
- Impressum und Datenschutzerklärung (Schweizer DSG); keine Cookies, keine Tracker im MVP.

**Qualität**
- CI grün vor Merge; keine Tests überspringen, um grün zu werden.
- Conventional Commits, Squash-Merge, PR-Beschreibung mit «Was/Warum/Wie getestet».
- Entscheide als ADR, nicht im Chat.

**Sprache und Gestaltung**
- UI Deutsch (Schweizer Rechtschreibung), i18n-fähig. Code Englisch.
- WCAG 2.1 AA, farbenblind-sichere Palette, `prefers-reduced-motion`, jede Grafik mit Textalternative.

---

## 11. Offene Entscheidungen (Michael)

| # | Entscheid | Optionen | Empfehlung |
|---|---|---|---|
| 1 | Code-Lizenz | MIT · Apache-2.0 · AGPL-3.0 | AGPL-3.0, wenn geschlossene Forks verhindert werden sollen; sonst MIT |
| 2 | Repo-Sichtbarkeit | public · private | public (kostenlose Security-Features, Transparenzmission) |
| 3 | LLM für Klassifikation | Anthropic API · lokal (OpenAI-kompatibel) | Vorschläge lokal, Stichproben mit Anthropic API vergleichen |
| 4 | Smartvote | Anfrage an Politools jetzt · nach MVP | jetzt anfragen, parallel MVP ohne Soll-Profile bauen |
| 5 | Analytics | keine · selbst gehostet (Plausible/Umami) | keine im MVP |
| 6 | Zweitdomain | politdrift.ch als Redirect | ja, früh registrieren |
| 7 | Daten-Lizenz der eigenen Mappings | CC BY 4.0 · CC BY-SA 4.0 | CC BY 4.0 |

---

## Anhang A – Kickoff-Prompt für Claude Code

```
Lies docs/KONZEPT.md vollständig, bevor du etwas tust. Es ist die verbindliche
Arbeitsgrundlage für dieses Repository.

Führe anschliessend Phase 0 (Abschnitt 9) aus:
- Arbeite auf dem Branch chore/phase-0-init.
- Setze die Repo-Struktur aus Abschnitt 5 und die Konventionen aus Abschnitt 6 um.
- Erstelle die Workflows aus Abschnitt 7 mit allen Actions auf Commit-SHA gepinnt.
  Ermittle dafür die aktuellen Major-Versionen und SHAs; übernimm keine
  Platzhalter.
- Erstelle die Infra-Dateien aus Abschnitt 8.
- Halte dich strikt an die Leitplanken in Abschnitt 10.
- Triff bei Unklarheiten begründete Annahmen und dokumentiere sie in
  docs/adr/. Frage nur bei Sicherheits-, Datenschutz- oder Lizenzfragen nach.
- Prüfe am Ende die Abnahmekriterien von Phase 0 selbst (lokaler Build,
  Docker-Build, validate, Tests) und liste das Ergebnis im PR auf.
- Eröffne einen PR «chore: initialize repository (phase 0)» mit einer
  Checkliste der Repo-Einstellungen aus Abschnitt 7.5, die ich manuell
  setzen muss.
```

## Anhang B – `CLAUDE.md` (Vorlage für die Repo-Wurzel)

```markdown
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
```
