#!/usr/bin/env bash
# iptables.sh - host firewall for the agent port (defense in depth behind the GCP firewall).
# Usage: sudo deploy/iptables.sh <DASHBOARD_IP>
# tcp/AGENT_PORT accepts only localhost (the cron watchdog) and the dashboard IP.
# SSH and everything else are untouched, so this cannot lock you out. Safe to re-run.
set -euo pipefail

AGENT_PORT="${AGENT_PORT:-8090}"
CHAIN="OBS_AGENT"
DASH_IP="${1:-}"

[[ $EUID -eq 0 ]] || { echo "run as root (sudo)" >&2; exit 1; }
[[ "$DASH_IP" =~ ^[0-9]{1,3}(\.[0-9]{1,3}){3}$ ]] || { echo "usage: $0 <DASHBOARD_IP>" >&2; exit 1; }

# Our own chain: create it if missing, otherwise empty it.
iptables -w -N "$CHAIN" 2>/dev/null || iptables -w -F "$CHAIN"

iptables -w -A "$CHAIN" -i lo -j ACCEPT
iptables -w -A "$CHAIN" -s "$DASH_IP" -j ACCEPT
iptables -w -A "$CHAIN" -j DROP

# Send agent-port traffic through the chain (added only once).
if ! iptables -w -C INPUT -p tcp --dport "$AGENT_PORT" -j "$CHAIN" 2>/dev/null; then
  iptables -w -I INPUT 1 -p tcp --dport "$AGENT_PORT" -j "$CHAIN"
fi

# Persist across reboots.
if command -v netfilter-persistent >/dev/null 2>&1; then
  netfilter-persistent save >/dev/null
  echo "rules saved with netfilter-persistent"
else
  echo "warning: netfilter-persistent not installed; rules will be lost on reboot" >&2
fi

echo "tcp/$AGENT_PORT now accepts only localhost and $DASH_IP"
iptables -w -L "$CHAIN" -n -v