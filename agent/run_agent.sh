#!/usr/bin/env bash
# Start both agent processes; exit if either one stops.
set -euo pipefail

AGENT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
API_PID=""
COLLECTOR_PID=""

cleanup() {
    trap - EXIT INT TERM

    for pid in "$API_PID" "$COLLECTOR_PID"; do
        if [[ -n "$pid" ]]; then
            kill "$pid" 2>/dev/null || true
        fi
    done

    wait 2>/dev/null || true
}

trap cleanup EXIT
trap 'exit 0' INT TERM

/usr/bin/python3 -u "$AGENT_DIR/api.py" &
API_PID=$!

/usr/bin/python3 -u "$AGENT_DIR/collector.py" &
COLLECTOR_PID=$!

# If either child exits, stop the other and let systemd restart both.
set +e
wait -n "$API_PID" "$COLLECTOR_PID"
set -e

echo "An agent process stopped; restarting the service is required." >&2
exit 1
