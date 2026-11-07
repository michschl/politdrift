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

Schritt für Schritt in [SETUP.md](SETUP.md), Teile B und C.

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

## Infra-Konfiguration ändern (Caddyfile, compose.yml, deploy.sh)

Ein Deploy tauscht nur das Web-Image aus. Änderungen an Dateien unter `infra/` kommen über einen
erneuten Lauf von `bootstrap.sh` auf den Server. Das Skript ist idempotent und erzeugt die
Container danach neu (Zertifikate bleiben erhalten, kurzer Unterbruch von wenigen Sekunden):

```bash
ssh admin@<host>
cd ~/politdrift && git pull
sudo ADMIN_PUBKEY="$(head -1 ~/.ssh/authorized_keys)" \
     DEPLOY_PUBKEY="$(sudo awk '{print $(NF-2), $(NF-1)}' /home/deploy/.ssh/authorized_keys)" \
     ./infra/vps/bootstrap.sh
```

Danach den Workflow «Acceptance» starten (Actions → Acceptance → Run workflow).

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

1. Neuen VPS gemäss [SETUP.md](SETUP.md) Teil B aufsetzen.
2. `VPS_HOST` und `VPS_KNOWN_HOSTS` im Environment `production` aktualisieren.
3. Workflow `CI/CD` auf `main` per `workflow_dispatch` neu starten.
