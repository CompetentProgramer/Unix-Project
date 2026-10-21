#!/usr/bin/env bash
# update_all.sh - deploy the current commit to every running VM tagged obs-agent.
# Usage (in the Codespace, after git push): deploy/update_all.sh <DASHBOARD_IP> [MORE_IPS...]
set -euo pipefail

PROJECT="${PROJECT:-$(gcloud config get-value project 2>/dev/null || true)}"
TAG="obs-agent"

die() { echo "error: $*" >&2; exit 1; }
[[ $# -ge 1 ]] || die "usage: $0 <DASHBOARD_IP> [MORE_IPS...]"
[[ -n "$PROJECT" ]] || die "no gcloud project set"
for ip in "$@"; do
  [[ "$ip" =~ ^[0-9]{1,3}(\.[0-9]{1,3}){3}$ ]] || die "bad IP: $ip"
done

cd "$(git rev-parse --show-toplevel)"
git diff --quiet && git diff --cached --quiet || die "uncommitted changes; commit first"
git fetch -q
[[ "$(git rev-parse HEAD)" == "$(git rev-parse '@{u}')" ]] || die "not in sync with GitHub; git pull / git push first"
echo "Deploying commit $(git rev-parse --short HEAD)"

ok=0; failed=()
while read -r name zone; do
  [[ -n "$name" ]] || continue
  echo "==> $name"
  if git archive HEAD | gcloud compute ssh "$name" --zone "$zone" --project "$PROJECT" \
      --tunnel-through-iap --quiet --command \
      "rm -rf ~/Unix-Project && mkdir ~/Unix-Project && tar -x -C ~/Unix-Project && cd ~/Unix-Project && sudo deploy/setup_vm.sh $*"; then
    ok=$((ok + 1))
  else
    failed+=("$name")
  fi
done < <(gcloud compute instances list --project "$PROJECT" \
  --filter="tags.items=$TAG AND status=RUNNING" --format='value(name,zone.basename())')

echo
echo "Updated $ok VM(s)."
[[ ${#failed[@]} -eq 0 ]] || { echo "FAILED: ${failed[*]}" >&2; exit 1; }