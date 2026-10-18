#!/usr/bin/env bash
# gcp_setup.sh - create and manage the GCP resources for the observability project.
set -euo pipefail

PROJECT="${PROJECT:-$(gcloud config get-value project 2>/dev/null || true)}"
REGION="${REGION:-us-central1}"
ZONE="${ZONE:-us-central1-a}"
AGENT_PORT="${AGENT_PORT:-8090}"

NETWORK="obs-vpc"
SUBNET="obs-subnet"
TAG="obs-agent"
SUBNET_RANGE="10.10.0.0/24"

FW_AGENT="obs-allow-agent" # dashboard IP -> tcp:AGENT_PORT
FW_SSH="obs-allow-ssh-iap" # Google IAP range -> tcp:22
IAP_RANGE="35.235.240.0/20"

die()  { echo "error: $*" >&2; exit 1; }
info() { echo "==> $*"; }

[[ -n "$PROJECT" ]] || die "no project set. Run: gcloud config set project YOUR_PROJECT_ID"

# In DRY_RUN mode print the command instead of running it.
run() {
  if [[ -n "${DRY_RUN:-}" ]]; then echo "+ $*"; else "$@"; fi
}

# True if a "gcloud ... describe" command succeeds, meaning the resource already exists.
# Always false in DRY_RUN, so the whole flow gets printed.
has() {
  [[ -z "${DRY_RUN:-}" ]] && "$@" --project "$PROJECT" >/dev/null 2>&1
}

# Secceeds only for a valid IPv4 address
valid_ipv4() {
  local ip="$1" o
  [[ "$ip" =~ ^[0-9]{1,3}(\.[0-9]{1,3}){3}$ ]] || return 1
  IFS=. read -ra octets <<<"$ip"
  for o in "${octets[@]}"; do (( 10#$o <= 255 )) || return 1; done
}

cmd_network() {
  info "Enabling APIs in project $PROJECT"
  run gcloud services enable compute.googleapis.com iap.googleapis.com --project "$PROJECT"

  if has gcloud compute networks describe "$NETWORK"; then
    info "VPC $NETWORK already exists"
  else
    info "Creating VPC $NETWORK (custom subnet mode)"
    run gcloud compute networks create "$NETWORK" --subnet-mode=custom --project "$PROJECT"
  fi

  if has gcloud compute networks subnets describe "$SUBNET" --region "$REGION"; then
    info "Subnet $SUBNET already exists"
  else
    info "Creating subnet $SUBNET ($SUBNET_RANGE) in $REGION"
    run gcloud compute networks subnets create "$SUBNET" \
      --network="$NETWORK" --region="$REGION" --range="$SUBNET_RANGE" --project "$PROJECT"
  fi
}

cmd_firewall() {
  local ip="${1:-}"
  valid_ipv4 "$ip" || die "usage: $0 firewall <DASHBOARD_IP>"

  if has gcloud compute firewall-rules describe "$FW_AGENT"; then
    info "Updating $FW_AGENT: tcp:$AGENT_PORT allowed only from $ip/32"
    run gcloud compute firewall-rules update "$FW_AGENT" \
      --source-ranges="$ip/32" --project "$PROJECT"
  else
    info "Creating $FW_AGENT: tcp:$AGENT_PORT allowed only from $ip/32"
    run gcloud compute firewall-rules create "$FW_AGENT" \
      --network="$NETWORK" --direction=INGRESS --action=ALLOW \
      --rules="tcp:$AGENT_PORT" --source-ranges="$ip/32" \
      --target-tags="$TAG" --project "$PROJECT"
  fi

  if has gcloud compute firewall-rules describe "$FW_SSH"; then
    info "$FW_SSH already exists"
  else
    info "Creating $FW_SSH: SSH only through Google IAP ($IAP_RANGE)"
    run gcloud compute firewall-rules create "$FW_SSH" \
      --network="$NETWORK" --direction=INGRESS --action=ALLOW \
      --rules=tcp:22 --source-ranges="$IAP_RANGE" \
      --target-tags="$TAG" --project "$PROJECT"
  fi
}

case "${1:-}" in
  network)  shift; cmd_network "$@" ;;
  firewall) shift; cmd_firewall "$@" ;;
  *) echo "usage: $0 {network|firewall <DASHBOARD_IP>}" >&2; exit 1 ;;
esac