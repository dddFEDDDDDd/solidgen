#!/usr/bin/env bash
set -euo pipefail

source "$(dirname "$0")/00_env.sh"

gcloud config set project "$PROJECT_ID" >/dev/null

API_URL="$(gcloud run services describe "$CLOUD_RUN_API_SERVICE" --region "$REGION" --format='value(status.url)')"

IMAGE="${REGION}-docker.pkg.dev/${PROJECT_ID}/${AR_REPO}/solidgen-web:$(date +%Y%m%d-%H%M%S)"

echo "Building web image: $IMAGE"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
gcloud builds submit --tag "$IMAGE" "${REPO_ROOT}/apps/web"

echo "Deploying Cloud Run web service: $CLOUD_RUN_WEB_SERVICE"
gcloud run deploy "$CLOUD_RUN_WEB_SERVICE" \
  --image "$IMAGE" \
  --region "$REGION" \
  --allow-unauthenticated \
  --cpu 1 \
  --memory 512Mi \
  --set-env-vars "NEXT_PUBLIC_API_BASE_URL=$API_URL"

WEB_URL="$(gcloud run services describe "$CLOUD_RUN_WEB_SERVICE" --region "$REGION" --format='value(status.url)')"
echo "Web deployed: $WEB_URL"

echo "Updating API success/cancel URLs to point to the web..."
gcloud run services update "$CLOUD_RUN_API_SERVICE" \
  --region "$REGION" \
  --update-env-vars "STRIPE_SUCCESS_URL=${WEB_URL}/billing/success,STRIPE_CANCEL_URL=${WEB_URL}/billing/cancel"

echo "Done."




