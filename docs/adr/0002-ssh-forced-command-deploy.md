# 0002 – Deployment per SSH mit Forced Command

- Status: angenommen
- Datum: 2026-11-07

## Kontext

GitHub Actions soll nach grüner CI eine neue Version auf den Infomaniak-VPS ausrollen. Ein
kompromittierter Workflow oder ein geleakter Schlüssel darf dabei nicht zu einer Shell auf dem
Server führen.

## Entscheid

- Ein eigener Benutzer `deploy` ohne sudo. Sein einziger SSH-Schlüssel ist in `authorized_keys` an den
  Forced Command `/opt/politdrift/deploy.sh` gebunden (`no-pty`, kein Forwarding).
- `authorized_keys`, `.ssh/` und `deploy.sh` gehören root. `deploy` kann sie nicht verändern.
- `deploy.sh` akzeptiert nur einen Image-Tag der Form `sha-<hex>` als Argument, setzt ihn in `.env`,
  zieht das Image, startet den Container neu, prüft `/healthz` und rollt bei Fehlern auf den vorherigen
  Tag zurück. Parallele Deploys verhindert ein Lock.
- Der Workflow prüft danach öffentlich `version.json` (Smoke-Test).
- Das Deployment ist bis Phase 1 deaktiviert (Repository-Variable `DEPLOY_ENABLED`).

## Konsequenzen

- Ein geleakter Deploy-Schlüssel erlaubt höchstens das Ausrollen eines bestehenden Images aus GHCR.
- `deploy` ist Mitglied der Docker-Gruppe. Das ist root-äquivalent für alle, die als `deploy` beliebige
  Befehle ausführen können. Der Forced Command verhindert genau das. Die Härtung mit Rootless Docker
  oder ein pull-basierter Deploy ohne eingehendes SSH bleibt als Option offen (KONZEPT 8.2).
- Der Deploy ist in den Actions-Logs sichtbar, inklusive Rollback.
