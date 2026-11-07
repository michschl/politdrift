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
| Repo-Kopie für Bootstrap | `/home/admin/politdrift` |

`/opt/politdrift` gehört `deploy` (Modus 750). Als `admin` daher nie `cd /opt/politdrift`, sondern
Compose immer so aufrufen:

```bash
dc() { sudo -u deploy docker compose -f /opt/politdrift/compose.yml "$@"; }
dc ps
```

Die Funktion `dc` gilt für die aktuelle Shell. Die Befehle unten setzen sie voraus.

## Ersteinrichtung (Phase 1)

Schritt für Schritt in [SETUP.md](SETUP.md), Teile B und C.

## Rollback

Automatisch: `deploy.sh` setzt bei fehlgeschlagenem Healthcheck den vorherigen Tag zurück.

Manuell (Notfall):

```bash
ssh admin@<host>
sudo -u deploy sed -i 's/^IMAGE_TAG=.*/IMAGE_TAG=sha-<vorherige Version>/' /opt/politdrift/.env
dc up -d --no-deps web
curl -fsS http://127.0.0.1:8080/version.json
```

Danach den fehlerhaften Commit auf `main` per PR zurücknehmen, damit der nächste Deploy nicht erneut
die defekte Version ausrollt.

Getestet am 7. November 2026 mit dem Workflow «Acceptance» (`rollback_drill: true`,
[Run 42386123680](https://github.com/michschl/politdrift/actions/runs/42386123680)): Das defekte Image
`sha-0bad0bad` (ohne `/healthz`) wurde deployt, `deploy.sh` brach mit Exit-Code 1 ab und stellte
`sha-c226d16` wieder her. Dauer rund 60 Sekunden, die Seiten blieben erreichbar. Der Drill kann
jederzeit wiederholt werden: Actions → Acceptance → Run workflow → `rollback_drill` aktivieren.

## Infra-Konfiguration ändern (Caddyfile, compose.yml, deploy.sh)

Ein Deploy tauscht nur das Web-Image aus. Änderungen an Dateien unter `infra/` kommen über einen
erneuten Lauf von `bootstrap.sh` auf den Server. Das Skript ist idempotent und erzeugt die
Container danach neu (Zertifikate bleiben erhalten, kurzer Unterbruch von wenigen Sekunden):

1. Als `admin` einloggen und das Repo holen bzw. aktualisieren:

   ```bash
   ssh admin@<host>
   cd ~ && { [ -d politdrift ] || git clone https://github.com/michschl/politdrift.git; } && cd politdrift && git pull
   ```

2. Die vorhandenen öffentlichen Schlüssel einlesen und prüfen. Die letzte Zeile muss `68` lauten,
   sonst abbrechen (ein abgeschnittener Deploy-Schlüssel sperrt den Deploy aus):

   ```bash
   ADMIN_PUB="$(head -1 ~/.ssh/authorized_keys)"
   DEPLOY_PUB="$(sudo awk '{print $(NF-2), $(NF-1)}' /home/deploy/.ssh/authorized_keys)"
   echo "$ADMIN_PUB"; echo "$DEPLOY_PUB"; k=${DEPLOY_PUB#ssh-ed25519 }; echo ${#k}
   ```

3. Bootstrap ausführen (Ende: `==> Done.`):

   ```bash
   sudo ADMIN_PUBKEY="$ADMIN_PUB" DEPLOY_PUBKEY="$DEPLOY_PUB" ./infra/vps/bootstrap.sh
   ```

4. Prüfen:

   ```bash
   dc ps
   curl -sI https://politdrift.org | grep -iE "^(via|server):" || echo "OK: kein Via/Server-Header"
   ```

5. Den Workflow «Acceptance» starten (Actions → Acceptance → Run workflow).

## Logs

```bash
dc logs --tail 200 web
dc logs --tail 200 caddy
sudo journalctl -u ssh --since today
```

## Zertifikate

Caddy holt und erneuert Zertifikate automatisch (Let's Encrypt, Fallback ZeroSSL). Bei Problemen:
`dc logs caddy | grep -i acme`. Häufige Ursachen: DNS zeigt nicht auf den VPS, Port 80
blockiert, CAA-Record ohne passenden Issuer.

## Rebuild von null

1. Neuen VPS gemäss [SETUP.md](SETUP.md) Teil B aufsetzen.
2. `VPS_HOST` und `VPS_KNOWN_HOSTS` im Environment `production` aktualisieren.
3. Workflow `CI/CD` auf `main` per `workflow_dispatch` neu starten.
