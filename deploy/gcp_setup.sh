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

case "${1:-}" in
  network) shift; cmd_network "$@" ;;
  *) echo "usage: $0 network" >&2; exit 1 ;;
esac