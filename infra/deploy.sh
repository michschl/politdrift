#!/usr/bin/env bash
# /opt/politdrift/deploy.sh – runs exclusively as SSH forced command for the user `deploy`
# (KONZEPT 8.4). Owner root, mode 0755, so `deploy` cannot change it.
# Input: the image tag (sha-<hex>) in SSH_ORIGINAL_COMMAND. Nothing else is accepted.
set -euo pipefail
umask 027
cd /opt/politdrift

TAG="${SSH_ORIGINAL_COMMAND:-}"
[[ "$TAG" =~ ^sha-[0-9a-f]{7,40}$ ]] || { echo "invalid tag: ${TAG@Q}" >&2; exit 2; }

exec 9>/opt/politdrift/.deploy.lock
flock -n 9 || { echo "another deploy is running" >&2; exit 3; }

set_tag() { sed -i "s/^IMAGE_TAG=.*/IMAGE_TAG=$1/" .env; }

PREV="$(sed -n 's/^IMAGE_TAG=//p' .env)"
[[ -n "$PREV" ]] || { echo "IMAGE_TAG missing in .env" >&2; exit 4; }

rollback() {
  echo "deploy of ${TAG} failed, rolling back to ${PREV}" >&2
  set_tag "$PREV"
  if [[ "$PREV" != "bootstrap" ]]; then
    docker compose up -d --no-deps web || true
  fi
}
trap 'rollback; exit 1' ERR

set_tag "$TAG"
docker compose pull --quiet web
docker compose up -d --no-deps web
# Caddy waits for a healthy web container; start it if this is the first deploy.
docker compose up -d --no-recreate caddy

for _ in $(seq 1 20); do
  if curl -fsS http://127.0.0.1:8080/healthz >/dev/null 2>&1; then
    trap - ERR
    echo "deployed ${TAG} (previous ${PREV})"
    docker image prune -af --filter "until=168h" >/dev/null 2>&1 || true
    exit 0
  fi
  sleep 3
done

trap - ERR
rollback
exit 1
