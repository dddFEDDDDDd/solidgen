#!/usr/bin/env bash
set -euo pipefail

# You can override any of these by exporting env vars before running scripts.

export PROJECT_ID="${PROJECT_ID:-solidgen-481701}"
export REGION="${REGION:-us-central1}"
export ZONE="${ZONE:-us-central1-a}"

export APP_NAME="${APP_NAME:-solidgen}"

export AR_REPO="${AR_REPO:-solidgen}"

export CLOUD_RUN_API_SERVICE="${CLOUD_RUN_API_SERVICE:-solidgen-api}"
export CLOUD_RUN_WEB_SERVICE="${CLOUD_RUN_WEB_SERVICE:-solidgen-web}"

export PUBSUB_TOPIC="${PUBSUB_TOPIC:-solidgen-jobs}"
export PUBSUB_SUBSCRIPTION="${PUBSUB_SUBSCRIPTION:-solidgen-jobs-sub}"

# Buckets are globally unique; include project id to avoid collisions
export GCS_BUCKET="${GCS_BUCKET:-${PROJECT_ID}-assets}"

export CLOUDSQL_INSTANCE="${CLOUDSQL_INSTANCE:-solidgen-pg}"
export DB_NAME="${DB_NAME:-solidgen}"
export DB_USER="${DB_USER:-solidgen}"

export API_SA="${API_SA:-solidgen-api-sa}"
export WORKER_SA="${WORKER_SA:-solidgen-worker-sa}"

# Worker VM
export WORKER_VM="${WORKER_VM:-solidgen-worker}"
export WORKER_MACHINE_TYPE="${WORKER_MACHINE_TYPE:-n2-standard-8}"
export WORKER_GPU_TYPE="${WORKER_GPU_TYPE:-nvidia-tesla-a10}"
export WORKER_GPU_COUNT="${WORKER_GPU_COUNT:-1}"

echo "PROJECT_ID=$PROJECT_ID"
echo "REGION=$REGION"
echo "ZONE=$ZONE"
echo "GCS_BUCKET=$GCS_BUCKET"


