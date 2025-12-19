#!/usr/bin/env bash
set -euo pipefail

source "$(dirname "$0")/00_env.sh"

gcloud config set project "$PROJECT_ID" >/dev/null

WORKER_SA_EMAIL="${WORKER_SA}@${PROJECT_ID}.iam.gserviceaccount.com"

echo "Creating GPU VM ($WORKER_VM) in $ZONE ..."

# Prefer Deep Learning VM image family if available (CUDA + conda)
DL_PROJECT="deeplearning-platform-release"
DL_FAMILY="common-cu124"

IMAGE_ARGS=()
if gcloud compute images describe-from-family "$DL_FAMILY" --project "$DL_PROJECT" >/dev/null 2>&1; then
  IMAGE_ARGS+=(--image-family="$DL_FAMILY" --image-project="$DL_PROJECT")
else
  echo "Deep Learning image family not found; falling back to Ubuntu 22.04."
  IMAGE_ARGS+=(--image-family="ubuntu-2204-lts" --image-project="ubuntu-os-cloud")
fi

gcloud compute instances create "$WORKER_VM" \
  --zone="$ZONE" \
  --machine-type="$WORKER_MACHINE_TYPE" \
  --maintenance-policy=TERMINATE \
  --service-account="$WORKER_SA_EMAIL" \
  --scopes="https://www.googleapis.com/auth/cloud-platform" \
  --accelerator="type=$WORKER_GPU_TYPE,count=$WORKER_GPU_COUNT" \
  --boot-disk-size=200GB \
  "${IMAGE_ARGS[@]}"

echo
echo "VM created. Next run:"
echo "  gcloud compute ssh $WORKER_VM --zone $ZONE"
echo "Then inside the VM:"
echo "  cd /opt/solidgen || (sudo mkdir -p /opt/solidgen && sudo chown -R \\$USER:\\$USER /opt/solidgen && git clone https://github.com/dddFEDDDDDDDd/solidgen.git /opt/solidgen)"
echo "  cd /opt/solidgen && git submodule update --init --recursive"
echo "  bash infra/gcp/worker/setup_worker.sh"


