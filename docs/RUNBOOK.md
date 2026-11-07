# Runbook

Betrieb von politdrift.org auf dem Infomaniak-VPS. Grundsatz: Der VPS ist bezüglich Anwendung
zustandslos. Alles kommt aus dem Image und diesem Repository. Deployments laufen ausschliesslich über
`.github/workflows/cicd.yml`; manuelle Eingriffe nur in den hier beschriebenen Notfällen.

## Überblick

| Was | Wo |
|---|---|
| App-Verzeichnis | `/opt/politdrift` (`compose.yml`, `Caddyfile`, `.env`, `deploy.sh`) |
| Aktive Version | `IMAGE_TAG` in `/opt/politdrift/.env`, live unter `https://politdrift.org/version.json` |
| Benutzer | `admin` (sudo, nur SSH-Key), `deploy` (nur Forced Command `deploy.sh`) |
| Images | `ghcr.io/michschl/politdrift-web:sha-<7>` |

## Ersteinrichtung (Phase 1)

1. VPS mit Ubuntu 24.04 LTS bei Infomaniak bestellen. Firewall im Infomaniak-Manager auf 22/80/443
   (TCP) und 443 (UDP) begrenzen, wöchentliche Snapshots aktivieren.
2. Deploy-Schlüssel lokal erzeugen (nur für GitHub Actions):
   `ssh-keygen -t ed25519 -f politdrift-deploy -C github-actions-deploy -N ''`
3. Als root auf dem VPS:
   ```bash
   git clone https://github.com/michschl/politdrift.git /root/politdrift
   cd /root/politdrift
   ADMIN_PUBKEY="$(cat ~/.ssh/authorized_keys | head -1)" \
   DEPLOY_PUBKEY="ssh-ed25519 AAAA… github-actions-deploy" \
   ./infra/vps/bootstrap.sh
   ```
4. In einem zweiten Terminal `ssh admin@<host>` testen, bevor die root-Sitzung geschlossen wird.
5. DNS bei Infomaniak: `A`/`AAAA` für `politdrift.org` und `www` auf den VPS (TTL 300 s),
   `CAA 0 issue "letsencrypt.org"`.
6. GitHub: Environment `production` mit `VPS_HOST`, `VPS_SSH_KEY` (privater Deploy-Schlüssel),
   `VPS_KNOWN_HOSTS` (Ausgabe von `bootstrap.sh`). Repository-Variable `DEPLOY_ENABLED=true`.
7. GHCR-Package `politdrift-web` nach dem ersten Push auf **public** stellen.
8. Einen Commit auf `main` mergen. Der Workflow deployt, `deploy.sh` startet beim ersten Mal auch Caddy.

## Rollback

Automatisch: `deploy.sh` setzt bei fehlgeschlagenem Healthcheck den vorherigen Tag zurück.

Manuell (Notfall):

```bash
ssh admin@<host>
cd /opt/politdrift
sudo -u deploy sed -i 's/^IMAGE_TAG=.*/IMAGE_TAG=sha-<vorherige Version>/' .env
sudo -u deploy docker compose up -d --no-deps web
curl -fsS http://127.0.0.1:8080/version.json
```

Danach den fehlerhaften Commit auf `main` per PR zurücknehmen, damit der nächste Deploy nicht erneut
die defekte Version ausrollt.

<!-- TODO Phase 1: Rollback mit absichtlich defektem Image einmal testen und hier dokumentieren. -->

## Logs

```bash
cd /opt/politdrift
docker compose logs --tail 200 web
docker compose logs --tail 200 caddy
journalctl -u ssh --since today
```

## Zertifikate

Caddy holt und erneuert Zertifikate automatisch (Let's Encrypt, Fallback ZeroSSL). Bei Problemen:
`docker compose logs caddy | grep -i acme`. Häufige Ursachen: DNS zeigt nicht auf den VPS, Port 80
blockiert, CAA-Record ohne passenden Issuer.

## Rebuild von null

1. Neuen VPS gemäss «Ersteinrichtung» aufsetzen (Schritte 1–5).
2. `VPS_HOST` und `VPS_KNOWN_HOSTS` im Environment `production` aktualisieren.
3. Workflow `CI/CD` auf `main` per `workflow_dispatch` neu starten.
