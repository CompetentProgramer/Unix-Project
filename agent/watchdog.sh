#!/usr/bin/env bash
# watchdog.sh - Member 2
#
# Run as root by cron every 5 minutes (/etc/cron.d/obs-watchdog).
# Checks that obs-agent and obs-stress are running, and that the API really
# answers (a running but hung agent is caught by the /health check).
# Restarts whatever is broken and logs everything to /var/log/obs-watchdog.log.

set -u

LOG=/var/log/obs-watchdog.log
LOCK=/run/obs-watchdog.lock
HEALTH_URL="http://127.0.0.1:8090/health"
GRACE=60                     # don't judge /health in the first 60 s after a start
MAX_LOG_BYTES=1048576        # trim the log at 1 MB

log() { printf '%s [watchdog] %s\n' "$(date '+%F %T')" "$*" >> "$LOG"; }

[ "$(id -u)" -eq 0 ] || { echo "watchdog.sh must run as root" >&2; exit 1; }

# never run two copies at once
exec 9>"$LOCK"
flock -n 9 || exit 0

# keep the log small
if [ -f "$LOG" ] && [ "$(stat -c %s "$LOG")" -gt "$MAX_LOG_BYTES" ]; then
  tail -n 500 "$LOG" > "$LOG.tmp" && mv "$LOG.tmp" "$LOG"
fi

# seconds since the unit last became active (0 if not active)
unit_age() {
  local since
  since=$(systemctl show -p ActiveEnterTimestamp --value "$1")
  [ -n "$since" ] || { echo 0; return; }
  echo $(( $(date +%s) - $(date -d "$since" +%s) ))
}

restart_unit() {   # unit reason
  log "$1: $2 -> restarting"
  systemctl reset-failed "$1" 2>/dev/null     # clear any start-limit lockout
  systemctl restart "$1"
  sleep 2
  if systemctl is-active --quiet "$1"; then
    log "$1: restart OK"
  else
    log "$1: restart FAILED ($(systemctl is-active "$1"))"
  fi
}

problems=0

# 1. both services must be active
for unit in obs-agent obs-stress; do
  if ! systemctl is-active --quiet "$unit"; then
    restart_unit "$unit" "state is $(systemctl is-active "$unit")"
    problems=$(( problems + 1 ))
  fi
done

# 2. the API must answer and report fresh data
if systemctl is-active --quiet obs-agent && [ "$(unit_age obs-agent)" -gt "$GRACE" ]; then
  body=$(curl -s --max-time 5 "$HEALTH_URL" || true)
  if ! printf '%s' "$body" | grep -Eq '"status": ?"ok"'; then
    restart_unit obs-agent "health check failed (got: ${body:-no response})"
    problems=$(( problems + 1 ))
  fi
fi

[ "$problems" -eq 0 ] && log "all ok (obs-agent, obs-stress, /health)"
exit 0