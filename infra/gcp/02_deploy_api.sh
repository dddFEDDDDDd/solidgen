#!/usr/bin/env bash
set -euo pipefail

source "$(dirname "$0")/00_env.sh"

gcloud config set project "$PROJECT_ID" >/dev/null

API_SA_EMAIL="${API_SA}@${PROJECT_ID}.iam.gserviceaccount.com"

IMAGE="${REGION}-docker.pkg.dev/${PROJECT_ID}/${AR_REPO}/solidgen-api:$(date +%Y%m%d-%H%M%S)"

echo "Building API image: $IMAGE"
gcloud builds submit --tag "$IMAGE" ../../apps/api

echo "Deploying Cloud Run API service: $CLOUD_RUN_API_SERVICE"
CLOUDSQL_CONN_NAME="$(gcloud sql instances describe "$CLOUDSQL_INSTANCE" --format='value(connectionName)')"

gcloud run deploy "$CLOUD_RUN_API_SERVICE" \
  --image "$IMAGE" \
  --region "$REGION" \
  --allow-unauthenticated \
  --service-account "$API_SA_EMAIL" \
  --cpu 2 \
  --memory 2Gi \
  --set-env-vars "GCP_PROJECT_ID=$PROJECT_ID" \
  --set-env-vars "GCS_BUCKET=$GCS_BUCKET" \
  --set-env-vars "PUBSUB_TOPIC=$PUBSUB_TOPIC" \
  --set-env-vars "GCS_SIGNER_SERVICE_ACCOUNT_EMAIL=$API_SA_EMAIL" \
  --set-env-vars "CLOUDSQL_INSTANCE_CONNECTION_NAME=$CLOUDSQL_CONN_NAME" \
  --set-env-vars "DB_NAME=$DB_NAME" \
  --set-env-vars "DB_USER=$DB_USER" \
  --set-secrets "DB_PASSWORD=solidgen-db-password:latest" \
  --set-secrets "JWT_SECRET=solidgen-jwt-secret:latest" \
  --set-secrets "STRIPE_SECRET_KEY=solidgen-stripe-secret-key:latest" \
  --set-secrets "STRIPE_WEBHOOK_SECRET=solidgen-stripe-webhook-secret:latest" \
  --set-secrets "NOWPAYMENTS_API_KEY=solidgen-nowpayments-api-key:latest" \
  --set-secrets "NOWPAYMENTS_IPN_SECRET=solidgen-nowpayments-ipn-secret:latest" \
  --set-env-vars "CORS_ORIGINS=*" \
  --set-env-vars "STRIPE_SUCCESS_URL=http://localhost:3000/billing/success" \
  --set-env-vars "STRIPE_CANCEL_URL=http://localhost:3000/billing/cancel" \
  --add-cloudsql-instances "$CLOUDSQL_CONN_NAME"

API_URL="$(gcloud run services describe "$CLOUD_RUN_API_SERVICE" --region "$REGION" --format='value(status.url)')"
echo "API deployed: $API_URL"

echo "NOTE: After deploying web, re-run 03_deploy_web.sh (it will update STRIPE_SUCCESS_URL/STRIPE_CANCEL_URL)."




