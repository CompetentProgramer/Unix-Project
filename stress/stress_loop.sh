#!/usr/bin/env bash
# stress_loop.sh - Member 2
#
# Endless load generator. Alternates between five stress classes
# (cpu, memory, io, disk, network) with random durations and short rests.
#
# Runs under systemd (obs-stress.service, Type=notify), so it must:
#   1. tell systemd it is ready                    -> READY=1
#   2. ping the systemd watchdog regularly         -> WATCHDOG=1
#      (WatchdogSec=30 in the unit; we ping every 5 s, also while resting)
#   3. publish the running event for the dashboard -> /run/obs-stress/state.json
#
# If this script hangs or crashes, pings stop, systemd kills it and
# Restart=always starts it again.

set -u
umask 022                                  # state.json must be readable by obs-agent

STATE_DIR=/run/obs-stress                  # created by RuntimeDirectory=obs-stress
STATE_FILE="$STATE_DIR/state.json"
SCRATCH=/var/tmp/obs-stress                # disk-stress scratch files
PING_EVERY=5                               # seconds between WATCHDOG=1 pings

MIN_RUN=20;  MAX_RUN=90                    # stress event length (seconds)
MIN_REST=10; MAX_REST=30                   # idle gap between events (seconds)

CLASSES=(cpu memory io disk network)       # the five stressed classes
CHILD=""                                   # PID of the running stress-ng

# systemd-notify fails when run by hand outside systemd; ignore that.
notify() { systemd-notify "$@" 2>/dev/null || true; }

log() { echo "[stress_loop] $*"; }          # stdout goes to the journal

rand_between() { echo $(( RANDOM % ($2 - $1 + 1) + $1 )); }

# Atomic write (tmp + rename) so the agent never reads a half-written file.
write_state() {   # class started ends
  printf '{"class": "%s", "started": %d, "ends": %d}\n' "$1" "$2" "$3" \
    > "$STATE_FILE.tmp" 2>/dev/null && mv -f "$STATE_FILE.tmp" "$STATE_FILE" 2>/dev/null
}

clear_state() { rm -f "$STATE_FILE" "$STATE_FILE.tmp" 2>/dev/null; }

cleanup() {
  [ -n "$CHILD" ] && kill "$CHILD" 2>/dev/null
  clear_state
}
trap 'exit 143' TERM INT                   # systemctl stop -> run cleanup via EXIT
trap cleanup EXIT

# Fill the global ARGS array with stress-ng options for one class.
set_args() {
  case "$1" in
    cpu)     ARGS=(--cpu 0) ;;                                        # all cores
    memory)  ARGS=(--vm 2 --vm-bytes 30% --vm-method all) ;;          # ~60% of RAM max
    io)      ARGS=(--io 2) ;;                                         # sync() pressure
    disk)    ARGS=(--hdd 2 --hdd-bytes 512m --temp-path "$SCRATCH") ;;
    network) ARGS=(--sock 2 --sock-port 15000) ;;                     # loopback traffic
    *)       return 1 ;;
  esac
}

# Sleep for N seconds but keep pinging the watchdog.
ping_sleep() {
  local left=$1 step
  while (( left > 0 )); do
    notify WATCHDOG=1
    step=$(( left < PING_EVERY ? left : PING_EVERY ))
    sleep "$step"
    left=$(( left - step ))
  done
}

run_stress() {   # class duration
  local class=$1 dur=$2 now tick=0
  set_args "$class" || return 1
  now=$(date +%s)
  write_state "$class" "$now" $(( now + dur ))
  notify "STATUS=stressing: $class for ${dur}s"
  log "start class=$class duration=${dur}s"

  # nice keeps this script (and its watchdog pings) responsive under CPU load
  nice -n 10 stress-ng "${ARGS[@]}" --timeout "${dur}s" >/dev/null 2>&1 &
  CHILD=$!

  while kill -0 "$CHILD" 2>/dev/null; do
    (( tick % PING_EVERY == 0 )) && notify WATCHDOG=1
    # safety net: stress-ng should stop by itself; if not, kill it
    if (( tick > dur + 20 )); then
      log "stress-ng overran, killing pid $CHILD"
      kill -TERM "$CHILD" 2>/dev/null
    fi
    sleep 1
    tick=$(( tick + 1 ))
  done
  wait "$CHILD" 2>/dev/null
  CHILD=""
  clear_state
  log "end class=$class"
}

# ---------------------------------------------------------------- main
command -v stress-ng >/dev/null || { log "stress-ng not installed"; exit 1; }
mkdir -p "$SCRATCH" 2>/dev/null

notify READY=1
log "ready"

last=""
while true; do
  # pick a class that differs from the previous one
  class=${CLASSES[RANDOM % ${#CLASSES[@]}]}
  [ "$class" = "$last" ] && continue
  last=$class

  run_stress "$class" "$(rand_between $MIN_RUN $MAX_RUN)"

  rest=$(rand_between $MIN_REST $MAX_REST)
  notify "STATUS=resting ${rest}s"
  ping_sleep "$rest"
done
