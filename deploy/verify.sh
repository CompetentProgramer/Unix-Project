#!/usr/bin/env bash
# verify.sh - check that one agent is reachable and that the API key is enforced.
# Run from a machine the firewall allows (the dashboard machine).
#
# Usage: deploy/verify.sh <VM_IP> [API_KEY] [PORT]
#
# The "blocked from elsewhere" test cannot be automated from one machine: also run
#   curl -m 5 http://<VM_IP>:8090/health
# from a different network (phone hotspot) and confirm it times out. Screenshot it.
set -uo pipefail

IP="${1:-}"; KEY="${2:-}"; PORT="${3:-8090}"
[[ -n "$IP" ]] || { sed -n '2,9p' "$0"; exit 1; }

pass=0; fail=0
check() {  # check <description> <expected http code> <curl args...>
  local desc="$1" want="$2"; shift 2
  local got
  got="$(curl -s -o /dev/null -m 5 -w '%{http_code}' "$@" 2>/dev/null || true)"
  if [[ "$got" == "$want" ]]; then
    echo "PASS  $desc (HTTP $got)"; pass=$((pass + 1))
  else
    echo "FAIL  $desc (wanted $want, got ${got:-no response})"; fail=$((fail + 1))
  fi
}

BASE="http://$IP:$PORT"
check "/health answers without a key"      200 "$BASE/health"
check "/metrics refuses a missing key"     401 "$BASE/metrics"
check "/metrics refuses a wrong key"       401 -H "X-API-Key: wrong" "$BASE/metrics"
if [[ -n "$KEY" ]]; then
  check "/metrics answers with the key"    200 -H "X-API-Key: $KEY" "$BASE/metrics"
  check "/history answers with the key"    200 -H "X-API-Key: $KEY" "$BASE/history?seconds=60"
else
  echo "SKIP  key-based checks (no API_KEY given)"
fi

echo; echo "$pass passed, $fail failed"
[[ $fail -eq 0 ]]