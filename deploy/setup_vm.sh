#!/usr/bin/env bash
# setup_vm.sh - prepare one Ubuntu VM and install the agent + stress services from this repo.
# Usage (on the VM, from a clone of the repo):  sudo deploy/setup_vm.sh <DASHBOARD_IP> [MORE_IPS...]
# Safe to re-run. Pieces other members have not committed yet (agent/, stress/) are
# skipped with a warning, so you can run this early to check the infrastructure.
set -euo pipefail

APP_DIR="/opt/obs-agent"
ENV_DIR="/etc/obs-agent"
ENV_FILE="$ENV_DIR/agent.env"
AGENT_PORT="${AGENT_PORT:-8090}"
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

die()  { echo "error: $*" >&2; exit 1; }
info() { echo "==> $*"; }
warn() { echo "warning: $*" >&2; }

[[ $EUID -eq 0 ]] || die "run as root: sudo $0 <DASHBOARD_IP> [MORE_IPS...]"
[[ $# -ge 1 ]] || die "usage: sudo $0 <DASHBOARD_IP> [MORE_IPS...]"

info "Installing packages"
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq stress-ng python3-psutil iptables-persistent cron curl openssl git

info "Creating service accounts"
for u in obs-agent obs-stress; do
  id -u "$u" >/dev/null 2>&1 || useradd --system --no-create-home --shell /usr/sbin/nologin "$u"
done

info "Installing code to $APP_DIR (owned by root, read-only to the services)"
install -d -m 755 "$APP_DIR"
for d in agent stress deploy; do
  if [[ -d "$REPO_DIR/$d" ]]; then
    rm -rf "${APP_DIR:?}/$d"
    cp -a "$REPO_DIR/$d" "$APP_DIR/$d"
  fi
done
chown -R root:root "$APP_DIR"
find "$APP_DIR" -name '*.sh' -exec chmod 755 {} +
install -d -o obs-stress -g obs-stress -m 750 /var/tmp/obs-stress

info "API key file $ENV_FILE"
install -d -o root -g obs-agent -m 750 "$ENV_DIR"
NEW_KEY=""
if [[ ! -f "$ENV_FILE" ]]; then
  NEW_KEY="$(openssl rand -hex 16)"
  printf 'OBS_API_KEY=%s\n' "$NEW_KEY" > "$ENV_FILE"
fi
chown root:obs-agent "$ENV_FILE"
chmod 640 "$ENV_FILE"

info "Installing systemd units"
UNITS=()
for unit in agent/obs-agent.service stress/obs-stress.service; do
  if [[ -f "$REPO_DIR/$unit" ]]; then
    install -m 644 "$REPO_DIR/$unit" "/etc/systemd/system/$(basename "$unit")"
    UNITS+=("$(basename "$unit")")
  else
    warn "$unit not in the repo yet; skipped"
  fi
done

info "Installing cron watchdog (every 5 minutes) and log rotation"
if [[ -x "$APP_DIR/agent/watchdog.sh" && -f "$REPO_DIR/deploy/obs-watchdog.cron" ]]; then
  install -m 644 -o root -g root "$REPO_DIR/deploy/obs-watchdog.cron" /etc/cron.d/obs-watchdog
else
  warn "agent/watchdog.sh or deploy/obs-watchdog.cron missing; cron entry skipped"
fi
cat > /etc/logrotate.d/obs-watchdog <<'EOF'
/var/log/obs-watchdog.log {
    weekly
    rotate 4
    missingok
    notifempty
    compress
}
EOF

info "Applying host firewall (iptables)"
AGENT_PORT="$AGENT_PORT" "$APP_DIR/deploy/iptables.sh" "$@"

info "Enabling services"
systemctl daemon-reload
for u in "${UNITS[@]}"; do
  systemctl enable "$u"
  systemctl restart "$u"
done

EXT_IP="$(curl -fsS --max-time 3 -H 'Metadata-Flavor: Google' \
  http://metadata.google.internal/computeMetadata/v1/instance/network-interfaces/0/access-configs/0/external-ip \
  2>/dev/null || echo '<VM external IP>')"

echo
echo "Setup finished."
if [[ -n "$NEW_KEY" ]]; then
  echo "New API key (give it to whoever runs the dashboard; do not commit it):"
  echo "  $NEW_KEY"
else
  echo "Existing API key kept in $ENV_FILE"
fi
echo "Dashboard servers.yaml entry:"
echo "  - name: $(hostname)"
echo "    host: $EXT_IP"
echo "    port: $AGENT_PORT"
echo "    api_key: <key above>"