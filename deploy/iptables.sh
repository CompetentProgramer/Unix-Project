#!/usr/bin/env bash
# iptables.sh - host firewall for the agent port (defense in depth behind the GCP firewall).
# Usage: sudo deploy/iptables.sh <DASHBOARD_IP> [MORE_IPS...]
# tcp/AGENT_PORT accepts only localhost (the cron watchdog) and the IPs you list.
# SSH and everything else are untouched, so this cannot lock you out. Safe to re-run.
# Each run replaces the previous list, so always pass every IP you want allowed.
set -euo pipefail

AGENT_PORT="${AGENT_PORT:-8090}"
CHAIN="OBS_AGENT"

[[ $EUID -eq 0 ]] || { echo "run as root (sudo)" >&2; exit 1; }
[[ $# -ge 1 ]] || { echo "usage: $0 <DASHBOARD_IP> [MORE_IPS...]" >&2; exit 1; }

for ip in "$@"; do
  [[ "$ip" =~ ^[0-9]{1,3}(\.[0-9]{1,3}){3}$ ]] || { echo "bad IP: $ip" >&2; exit 1; }
done

# Our own chain: create it if missing, otherwise empty it.
iptables -w -N "$CHAIN" 2>/dev/null || iptables -w -F "$CHAIN"

iptables -w -A "$CHAIN" -i lo -j ACCEPT
for ip in "$@"; do
  iptables -w -A "$CHAIN" -s "$ip" -j ACCEPT
done
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

echo "tcp/$AGENT_PORT now accepts only localhost and: $*"
iptables -w -L "$CHAIN" -n -v