# Einrichtung: GitHub und Infomaniak

Schritt-für-Schritt-Anleitung für alles, was nicht im Code steckt und einmalig von Hand erledigt werden
muss. Reihenfolge einhalten: Teil A vor dem Merge von Phase 0, Teil B und C für Phase 1 (erstes
Deployment), Teil D für Phase 2.

Abhaken direkt hier im Dokument (per PR) oder in einem Issue.

---

## Teil A – GitHub, vor dem Merge von Phase 0

Alle Pfade beziehen sich auf `https://github.com/michschl/politdrift` → **Settings**.

### A1. Default-Branch auf `main` setzen

Der erste Push kam von einem Arbeitsbranch, deshalb ist dieser aktuell Default.

1. **Settings → General → Default branch** → Pfeil-Symbol (Switch to another branch).
2. `main` wählen → **Update** → bestätigen.

- [ ] Default-Branch ist `main`

### A2. Repository öffentlich machen

Vorher geprüft: Im Repository liegen keine Secrets, Schlüssel oder personenbezogenen Daten.

1. **Settings → General** → ganz unten **Danger Zone → Change visibility**.
2. **Change to public** → Warnungen bestätigen → Repository-Namen eintippen.

- [ ] Repository ist public

### A3. Merge-Einstellungen

**Settings → General → Pull Requests:**

1. **Allow merge commits**: aus
2. **Allow squash merging**: an (Default commit message: «Pull request title and description»)
3. **Allow rebase merging**: aus
4. **Always suggest updating pull request branches**: an
5. **Allow auto-merge**: an
6. **Automatically delete head branches**: an

- [ ] Merge-Einstellungen gesetzt

### A4. Security-Funktionen

**Settings → Advanced Security** (bei älteren Oberflächen: «Code security»):

1. **Private vulnerability reporting**: Enable
2. **Dependency graph**: **Enable**. Wird beim Umstellen von private auf public nicht automatisch
   aktiviert. Ohne ihn scheitert der Check `dependency-review`.
3. **Dependabot alerts**: Enable
4. **Dependabot security updates**: Enable
5. **Grouped security updates**: Enable
6. **Secret Protection / Secret scanning**: Enable
7. **Push protection**: Enable
8. **Code scanning → CodeQL analysis**: **nicht** «Default» aktivieren. Die Analyse läuft über den
   Workflow (Advanced Setup). Ist Default aktiv, scheitert der `codeql`-Job.

- [ ] Security-Funktionen aktiv, CodeQL-Default-Setup aus

### A5. Actions-Berechtigungen

**Settings → Actions → General:**

1. **Actions permissions**: «Allow michschl, and select non-michschl, actions and reusable workflows»
   - **Allow actions created by GitHub**: an
   - **Allow actions by Marketplace verified creators**: an
   - **Allow specified actions and reusable workflows**:
     ```
     astral-sh/setup-uv@*,
     aquasecurity/trivy-action@*,
     docker/*
     ```
   - Falls angeboten: **Require actions to be pinned to a full-length commit SHA**: an
2. **Approval for running fork pull request workflows from contributors**: «Require approval for all
   external contributors»
3. **Workflow permissions**: «Read repository contents and packages permissions»
4. **Allow GitHub Actions to create and approve pull requests**: aus
5. **Save**

- [ ] Actions-Berechtigungen gesetzt

### A6. Phase-0-PR mergen

1. Im PR prüfen, dass alle Checks grün sind: `web-quality`, `pipeline-quality`,
   `codeql (javascript-typescript)`, `codeql (python)`, `codeql (actions)`, `dependency-review`.
2. **Squash and merge**.
3. Danach läuft `CI/CD` auf `main`. `build-image` baut das Image und pusht es nach GHCR. `deploy`
   wird übersprungen, weil `DEPLOY_ENABLED` noch nicht gesetzt ist. Das ist so gewollt.

- [ ] Phase 0 gemergt, `build-image` grün

### A7. Branch-Ruleset importieren

Erst **nach** dem ersten Lauf auf `main`, damit GitHub die Check-Namen kennt.

1. Datei `infra/github/ruleset-main.json` lokal speichern (im Repo: Datei öffnen → **Download raw file**).
2. **Settings → Rules → Rulesets → New ruleset → Import a ruleset** → Datei wählen.
3. Prüfen:
   - Enforcement status: **Active**
   - Bypass list: **Repository admin**
   - Target: **Default branch**
   - Required status checks: `web-quality`, `pipeline-quality`, die drei `codeql`-Checks und
     `build-image` (Image-Build mit Trivy-Scan, auf PRs ohne Push). Werden sie nicht
     gefunden, über **Add checks** neu auswählen.
4. **Create**.

- [ ] Ruleset `main` aktiv

### A8. Container-Image öffentlich machen

Damit der VPS das Image ohne Zugangsdaten ziehen kann.

1. Profil → **Packages** → `politdrift-web` (oder direkt
   `https://github.com/users/michschl/packages/container/politdrift-web/settings`).
2. **Package settings → Danger Zone → Change visibility → Public**.
3. Unter **Manage Actions access** prüfen, dass `michschl/politdrift` mit Rolle **Write** eingetragen ist.

- [ ] Package `politdrift-web` ist public

---

## Teil B – Infomaniak, Phase 1

### B1. Domain

- `politdrift.org` muss bei Infomaniak verwaltet sein und die Infomaniak-Nameserver verwenden.
  Sonst gelten die DNS-Einträge aus B6 nicht.
- Empfehlung aus dem Konzept: zusätzlich `politdrift.ch` registrieren (später Weiterleitung).

- [ ] Domain mit Infomaniak-DNS

### B2. SSH-Schlüssel erzeugen (lokal)

Zwei getrennte Schlüssel: einer für dich, einer nur für GitHub Actions.

```bash
# Dein persönlicher Admin-Schlüssel (falls noch keiner vorhanden), mit Passphrase
ssh-keygen -t ed25519 -C "michael@politdrift-admin" -f ~/.ssh/politdrift_admin

# Deploy-Schlüssel für GitHub Actions, ohne Passphrase
ssh-keygen -t ed25519 -C "github-actions-deploy" -f ~/.ssh/politdrift_deploy -N ''
```

Der private Deploy-Schlüssel kommt nur in GitHub (C1) und danach am besten aus dem lokalen Speicher
entfernt oder sicher abgelegt.

- [ ] Admin- und Deploy-Schlüssel erzeugt

### B3. VPS bestellen

1. Infomaniak Manager → **Hosting / Cloud Computing → VPS** → bestellen.
2. Produkt: **VPS Lite** reicht für eine statische Website. **VPS Cloud** bietet zusätzlich Snapshots
   im Manager. Weil der Server zustandslos ist (Neuaufbau mit `bootstrap.sh`), sind Snapshots ein
   Komfort, keine Pflicht.
3. Kleinste Grösse genügt (1–2 vCPU, 2 GB RAM).
4. Betriebssystem: **Ubuntu 26.04 LTS** (24.04 LTS geht ebenfalls).
5. SSH-Schlüssel: den **öffentlichen** Admin-Schlüssel hochladen (`~/.ssh/politdrift_admin.pub`).
6. Nach der Bereitstellung IPv4- und IPv6-Adresse im Manager notieren.

- [ ] VPS läuft, IPv4: `…`, IPv6: `…`

### B4. Firewall im Infomaniak Manager

VPS im Manager öffnen → linkes Menü **Firewall** → Regeln hinzufügen (eingehend):

| Protokoll | Port | Quelle | Zweck |
|---|---|---|---|
| TCP | 22 | alle | SSH (Admin und GitHub-Deploy) |
| TCP | 80 | alle | HTTP (Zertifikatsausstellung, Weiterleitung) |
| TCP | 443 | alle | HTTPS |
| UDP | 443 | alle | HTTP/3 |

Alle übrigen eingehenden Ports bleiben zu. Port 22 muss für alle offen sein, weil GitHub Actions von
wechselnden Adressen deployt.

- [ ] Firewall-Regeln gesetzt

### B5. Server einrichten mit `bootstrap.sh`

```bash
ssh -i ~/.ssh/politdrift_admin ubuntu@<IPv4>
```

Auf dem Server:

```bash
sudo apt-get update && sudo apt-get install -y git
git clone https://github.com/michschl/politdrift.git ~/politdrift
cd ~/politdrift
sudo ADMIN_PUBKEY="$(head -1 ~/.ssh/authorized_keys)" \
     DEPLOY_PUBKEY="ssh-ed25519 AAAA…  github-actions-deploy" \
     ./infra/vps/bootstrap.sh
```

`DEPLOY_PUBKEY` ist der Inhalt von `~/.ssh/politdrift_deploy.pub` von deinem Rechner.

Am Ende gibt das Skript eine Zeile `VPS_KNOWN_HOSTS` aus, z. B.
`203.0.113.10 ssh-ed25519 AAAA…`. Diese Zeile kopieren (für C1).

**Wichtig, bevor du die Sitzung schliesst:** in einem zweiten Terminal

```bash
ssh -i ~/.ssh/politdrift_admin admin@<IPv4>
sudo -v   # muss ohne Passwort funktionieren
```

Ab jetzt ist nur noch `admin` und `deploy` per SSH erlaubt. Der Benutzer `ubuntu` kann sich nicht mehr
anmelden.

Optional, für `~/.ssh/config`:

```
Host politdrift
  HostName <IPv4>
  User admin
  IdentityFile ~/.ssh/politdrift_admin
```

- [ ] `bootstrap.sh` ohne Fehler durchgelaufen
- [ ] Login als `admin` funktioniert
- [ ] `VPS_KNOWN_HOSTS`-Zeile notiert

### B6. DNS-Einträge

Infomaniak Manager → **Domains** → `politdrift.org` → **DNS-Zone** → **Eintrag hinzufügen**.

Zuerst vorhandene Standardeinträge für `@` und `www` (A, AAAA, CNAME auf Infomaniak-Parkingseiten)
löschen, sonst zeigt die Domain teilweise woandershin.

| Typ | Name | Wert | TTL |
|---|---|---|---|
| A | (leer / `@`) | `<IPv4>` | 300 |
| AAAA | (leer / `@`) | `<IPv6>` | 300 |
| A | `www` | `<IPv4>` | 300 |
| AAAA | `www` | `<IPv6>` | 300 |
| CAA | (leer / `@`) | `0 issue "letsencrypt.org"` | 3600 |
| CAA | (leer / `@`) | `0 issue "sectigo.com"` | 3600 |

Der zweite CAA-Eintrag erlaubt ZeroSSL (Sectigo), den automatischen Fallback von Caddy. Nach ein paar
Minuten prüfen:

```bash
dig +short politdrift.org A
dig +short politdrift.org AAAA
dig +short politdrift.org CAA
```

Wenn alles stabil läuft, TTL der A/AAAA-Einträge auf 3600 erhöhen.

- [ ] DNS zeigt auf den VPS

### B7. Backups (optional)

Infomaniak macht von VPS selbst keine Backups. Bei **VPS Cloud**: im Manager **Snapshots** →
Snapshot erstellen, nach grösseren Änderungen wiederholen. Der Server ist so gebaut, dass er mit
`bootstrap.sh` und einem Deploy jederzeit neu aufgesetzt werden kann (RUNBOOK, «Rebuild von null»).

- [ ] Backup-Entscheid getroffen

---

## Teil C – GitHub, Phase 1 (erstes Deployment)

### C1. Environment `production`

**Settings → Environments → New environment** → Name `production` → **Configure environment**:

1. **Deployment branches and tags**: «Selected branches and tags» → **Add deployment branch rule** →
   `main`.
2. **Environment secrets → Add environment secret**:

| Name | Inhalt |
|---|---|
| `VPS_HOST` | IPv4 des VPS (oder `politdrift.org`, sobald DNS steht) |
| `VPS_SSH_KEY` | kompletter Inhalt von `~/.ssh/politdrift_deploy` (privat, inkl. `-----BEGIN…`/`-----END…`) |
| `VPS_KNOWN_HOSTS` | die Zeile aus B5. Der Hostname am Anfang muss genau `VPS_HOST` entsprechen |

- [ ] Environment `production` mit drei Secrets

### C2. Deployment einschalten

**Settings → Secrets and variables → Actions → Variables → New repository variable**:

- Name: `DEPLOY_ENABLED`, Wert: `true`

- [ ] `DEPLOY_ENABLED=true`

### C3. Ersten Deploy auslösen

1. **Actions → CI/CD → Run workflow** → Branch `main` → **Run workflow**.
2. Im Job `deploy` muss stehen: `deployed sha-xxxxxxx (previous bootstrap)` und `live: xxxxxxx`.
3. Prüfen:
   ```bash
   curl -s https://politdrift.org/version.json
   curl -sI https://politdrift.org | grep -iE "strict-transport|content-security|x-frame"
   ```
4. Externe Prüfungen:
   - SSL Labs: `https://www.ssllabs.com/ssltest/analyze.html?d=politdrift.org` → Ziel **A+**
   - Mozilla Observatory: `https://developer.mozilla.org/en-US/observatory/analyze?host=politdrift.org`
     → Ziel **≥ A**

- [ ] Website live, SSL Labs A+, Observatory ≥ A

### C4. Rollback einmal testen (Abnahme Phase 1)

Gemeinsam mit Claude: ein Commit, der `/healthz` absichtlich bricht, wird auf `main` gemergt. Erwartung:
Deploy-Job scheitert, `deploy.sh` meldet «rolling back», die vorherige Version bleibt live. Danach
revertieren und das Ergebnis im RUNBOOK festhalten.

- [ ] Rollback getestet und dokumentiert

### C5. Uptime-Check einschalten

Per PR in `.github/workflows/uptime.yml` den `schedule`-Block aktivieren. Benachrichtigungen bei
fehlgeschlagenen Läufen: GitHub → Profil → **Settings → Notifications → Actions** → «Only notify for
failed workflows».

- [ ] Uptime-Check aktiv

---

## Teil D – Phase 2 (Daten-Aktualisierung)

### D1. GitHub App «politdrift-bot»

PRs, die mit dem Standard-Token erstellt werden, lösen keine Checks aus. Deshalb öffnet eine eigene
GitHub App die Data-PRs.

1. Profil → **Settings → Developer settings → GitHub Apps → New GitHub App**.
2. Angaben:
   - GitHub App name: `politdrift-bot`
   - Homepage URL: `https://github.com/michschl/politdrift`
   - **Webhook → Active**: aus
   - Repository permissions: **Contents: Read and write**, **Pull requests: Read and write**,
     (Metadata: Read-only wird automatisch gesetzt)
   - Where can this GitHub App be installed: **Only on this account**
3. **Create GitHub App**. Die **App ID** notieren.
4. Ganz unten **Private keys → Generate a private key** → `.pem`-Datei wird heruntergeladen.
5. Links **Install App** → `michschl` → **Only select repositories** → `politdrift` → **Install**.
6. Im Repository **Settings → Secrets and variables → Actions → New repository secret**:
   - `DATA_BOT_APP_ID`: die App ID
   - `DATA_BOT_PRIVATE_KEY`: kompletter Inhalt der `.pem`-Datei
7. Die `.pem`-Datei lokal löschen oder im Passwortmanager ablegen.
8. Im Ruleset `main` (A7) die App **nicht** in die Bypass-Liste aufnehmen: Data-PRs sollen durch die
   Checks.

- [ ] GitHub App installiert, Secrets gesetzt

### D2. Weitere Punkte ausserhalb von GitHub und Infomaniak

- [ ] Anfrage an Politools für Smartvote-Daten (KONZEPT 3.3, Entscheid 4)
- [ ] Inhalte für **Impressum** (Name, Adresse, Kontakt) und **Datenschutzerklärung** (DSG) liefern.
      Beide Seiten sind Platzhalter und müssen vor der öffentlichen Bekanntmachung gefüllt sein.
