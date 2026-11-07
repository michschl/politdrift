#!/usr/bin/env bash
# Idempotent base installation of the Politdrift VPS (Ubuntu 24.04 or 26.04 LTS, KONZEPT 8.2).
#
# Run as root (e.g. via sudo from the image's default user) from a checkout of this repository:
#   sudo ADMIN_PUBKEY="ssh-ed25519 AAAA… you@laptop" \
#        DEPLOY_PUBKEY="ssh-ed25519 AAAA… github-actions-deploy" \
#        ./infra/vps/bootstrap.sh
# Step-by-step guide: docs/SETUP.md, part B.
#
# Safe to run again: every step checks or overwrites to a known state.
# Before logging out, verify `ssh admin@<host>` works in a second terminal: afterwards only
# `admin` and `deploy` may log in via SSH.
set -euo pipefail

: "${ADMIN_PUBKEY:?set ADMIN_PUBKEY (ssh public key for the admin user)}"
: "${DEPLOY_PUBKEY:?set DEPLOY_PUBKEY (ssh public key used by GitHub Actions)}"

[[ $EUID -eq 0 ]] || { echo "run as root" >&2; exit 1; }
# shellcheck source=/dev/null
. /etc/os-release
[[ "${ID}" == "ubuntu" && "${VERSION_ID}" =~ ^(24|26)\.04$ ]] || echo "warning: tested on Ubuntu 24.04/26.04 LTS only" >&2

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
APP_DIR=/opt/politdrift
export DEBIAN_FRONTEND=noninteractive

log() { printf '\n==> %s\n' "$*"; }

log "1. System update and unattended security upgrades"
apt-get update -q
apt-get -yq upgrade
apt-get -yq install ca-certificates curl gnupg unattended-upgrades ufw fail2ban jq
cat >/etc/apt/apt.conf.d/20auto-upgrades <<'CONF'
APT::Periodic::Update-Package-Lists "1";
APT::Periodic::Unattended-Upgrade "1";
CONF
cat >/etc/apt/apt.conf.d/52politdrift-unattended <<'CONF'
Unattended-Upgrade::Automatic-Reboot "true";
Unattended-Upgrade::Automatic-Reboot-Time "03:30";
CONF

log "2. Users admin (sudo) and deploy (forced command only)"
# Ubuntu ships a legacy group "admin", so a plain `useradd admin` fails. Reuse an existing
# group of the same name as primary group, otherwise create one.
ensure_user() { # name [extra groups]
  local name="$1" extra="${2:-}" args=(--create-home --shell /bin/bash)
  id "$name" >/dev/null 2>&1 && return 0
  if getent group "$name" >/dev/null; then args+=(--gid "$name"); else args+=(--user-group); fi
  [[ -n "$extra" ]] && args+=(--groups "$extra")
  useradd "${args[@]}" "$name"
}
ensure_user admin sudo
ensure_user deploy
usermod -aG sudo admin
passwd -l admin >/dev/null
passwd -l deploy >/dev/null
echo "admin ALL=(ALL) NOPASSWD:ALL" >/etc/sudoers.d/90-admin
chmod 0440 /etc/sudoers.d/90-admin
visudo -cf /etc/sudoers.d/90-admin >/dev/null

install -d -m 700 -o admin -g admin /home/admin/.ssh
printf '%s\n' "$ADMIN_PUBKEY" >/home/admin/.ssh/authorized_keys
chown admin:admin /home/admin/.ssh/authorized_keys
chmod 600 /home/admin/.ssh/authorized_keys

# .ssh and authorized_keys are root-owned: the deploy user cannot swap in a key without
# the forced command (sshd StrictModes accepts root ownership).
install -d -m 750 -o root -g deploy /home/deploy/.ssh
printf 'command="%s/deploy.sh",no-port-forwarding,no-agent-forwarding,no-X11-forwarding,no-pty %s\n' \
  "$APP_DIR" "$DEPLOY_PUBKEY" >/home/deploy/.ssh/authorized_keys
chown root:deploy /home/deploy/.ssh/authorized_keys
chmod 640 /home/deploy/.ssh/authorized_keys

log "3. SSH hardening"
cat >/etc/ssh/sshd_config.d/99-hardening.conf <<'CONF'
PermitRootLogin no
PasswordAuthentication no
KbdInteractiveAuthentication no
PubkeyAuthentication yes
AuthenticationMethods publickey
X11Forwarding no
AllowAgentForwarding no
AllowTcpForwarding no
PermitTunnel no
MaxAuthTries 3
LoginGraceTime 20
AllowUsers admin deploy
KexAlgorithms sntrup761x25519-sha512@openssh.com,mlkem768x25519-sha256,curve25519-sha256,curve25519-sha256@libssh.org
Ciphers chacha20-poly1305@openssh.com,aes256-gcm@openssh.com,aes128-gcm@openssh.com
MACs hmac-sha2-512-etm@openssh.com,hmac-sha2-256-etm@openssh.com
HostKeyAlgorithms ssh-ed25519,rsa-sha2-512,rsa-sha2-256
CONF
sshd -t
# Ubuntu 24.04+ may socket-activate ssh; reload only if the service runs, a later start reads
# the new config anyway. Existing sessions stay open.
systemctl try-reload-or-restart ssh.service

log "4. Firewall and fail2ban"
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp
ufw allow 443/udp
ufw --force enable
cat >/etc/fail2ban/jail.d/sshd.local <<'CONF'
[sshd]
enabled = true
backend = systemd
maxretry = 5
bantime = 1h
CONF
systemctl enable --now fail2ban
systemctl restart fail2ban

log "5. Docker Engine and Compose plugin (official repository)"
if ! command -v docker >/dev/null 2>&1; then
  install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
  chmod a+r /etc/apt/keyrings/docker.asc
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu ${VERSION_CODENAME} stable" \
    >/etc/apt/sources.list.d/docker.list
  apt-get update -q
  apt-get -yq install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
fi
install -d /etc/docker
cat >/etc/docker/daemon.json <<'CONF'
{
  "log-driver": "json-file",
  "log-opts": { "max-size": "10m", "max-file": "5" },
  "live-restore": true,
  "no-new-privileges": true
}
CONF
systemctl enable docker
systemctl restart docker
usermod -aG docker deploy

log "6. Application directory ${APP_DIR}"
install -d -m 750 -o deploy -g deploy "$APP_DIR"
install -m 644 -o deploy -g deploy "$REPO_DIR/infra/compose.yml" "$APP_DIR/compose.yml"
install -m 644 -o deploy -g deploy "$REPO_DIR/infra/Caddyfile" "$APP_DIR/Caddyfile"
install -m 755 -o root -g root "$REPO_DIR/infra/deploy.sh" "$APP_DIR/deploy.sh"
if [[ ! -f "$APP_DIR/.env" ]]; then
  # "bootstrap" is a placeholder until the first deploy sets a real sha-… tag.
  printf 'IMAGE_TAG=bootstrap\n' >"$APP_DIR/.env"
fi
chown deploy:deploy "$APP_DIR/.env"
chmod 640 "$APP_DIR/.env"

log "7. Host key fingerprint for the GitHub secret VPS_KNOWN_HOSTS"
HOST_IP="$(curl -fsS4 https://api.ipify.org || hostname -I | awk '{print $1}')"
echo "VPS_KNOWN_HOSTS (paste into the production environment secret):"
printf '%s %s\n' "$HOST_IP" "$(cut -d' ' -f1,2 /etc/ssh/ssh_host_ed25519_key.pub)"
ssh-keygen -lf /etc/ssh/ssh_host_ed25519_key.pub

log "Done. Test 'ssh admin@${HOST_IP}' in a new terminal before closing this session."
