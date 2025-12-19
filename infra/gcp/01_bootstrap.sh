#!/usr/bin/env bash
set -euo pipefail

source "$(dirname "$0")/00_env.sh"

gcloud config set project "$PROJECT_ID" >/dev/null

echo "Enabling APIs..."
gcloud services enable \
  run.googleapis.com \
  artifactregistry.googleapis.com \
  cloudbuild.googleapis.com \
  sqladmin.googleapis.com \
  pubsub.googleapis.com \
  secretmanager.googleapis.com \
  iamcredentials.googleapis.com \
  compute.googleapis.com >/dev/null

echo "Creating Artifact Registry repo (if needed)..."
gcloud artifacts repositories describe "$AR_REPO" --location="$REGION" >/dev/null 2>&1 || \
  gcloud artifacts repositories create "$AR_REPO" --repository-format=docker --location="$REGION" >/dev/null

echo "Creating GCS bucket (if needed): gs://$GCS_BUCKET"
gsutil ls -b "gs://$GCS_BUCKET" >/dev/null 2>&1 || \
  gsutil mb -l "$REGION" -p "$PROJECT_ID" "gs://$GCS_BUCKET"

echo "Creating Pub/Sub topic/subscription (if needed)..."
gcloud pubsub topics describe "$PUBSUB_TOPIC" >/dev/null 2>&1 || \
  gcloud pubsub topics create "$PUBSUB_TOPIC" >/dev/null

gcloud pubsub subscriptions describe "$PUBSUB_SUBSCRIPTION" >/dev/null 2>&1 || \
  gcloud pubsub subscriptions create "$PUBSUB_SUBSCRIPTION" --topic="$PUBSUB_TOPIC" >/dev/null

echo "Creating service accounts (if needed)..."
gcloud iam service-accounts describe "${API_SA}@${PROJECT_ID}.iam.gserviceaccount.com" >/dev/null 2>&1 || \
  gcloud iam service-accounts create "$API_SA" --display-name="Solidgen API" >/dev/null

gcloud iam service-accounts describe "${WORKER_SA}@${PROJECT_ID}.iam.gserviceaccount.com" >/dev/null 2>&1 || \
  gcloud iam service-accounts create "$WORKER_SA" --display-name="Solidgen Worker" >/dev/null

API_SA_EMAIL="${API_SA}@${PROJECT_ID}.iam.gserviceaccount.com"
WORKER_SA_EMAIL="${WORKER_SA}@${PROJECT_ID}.iam.gserviceaccount.com"

echo "Granting IAM roles..."
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:${API_SA_EMAIL}" \
  --role="roles/pubsub.publisher" >/dev/null

gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:${API_SA_EMAIL}" \
  --role="roles/cloudsql.client" >/dev/null

gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:${WORKER_SA_EMAIL}" \
  --role="roles/pubsub.subscriber" >/dev/null

gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:${WORKER_SA_EMAIL}" \
  --role="roles/storage.objectAdmin" >/dev/null

gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:${WORKER_SA_EMAIL}" \
  --role="roles/cloudsql.client" >/dev/null

# For signed URLs from Cloud Run: allow the API SA to sign as itself
gcloud iam service-accounts add-iam-policy-binding "$API_SA_EMAIL" \
  --member="serviceAccount:${API_SA_EMAIL}" \
  --role="roles/iam.serviceAccountTokenCreator" >/dev/null

echo "Creating Cloud SQL instance (if needed)..."
gcloud sql instances describe "$CLOUDSQL_INSTANCE" >/dev/null 2>&1 || \
  gcloud sql instances create "$CLOUDSQL_INSTANCE" \
    --database-version=POSTGRES_15 \
    --region="$REGION" \
    --tier="db-custom-2-8192" \
    --storage-size=20 \
    --storage-type=SSD >/dev/null

echo "Creating database (if needed)..."
gcloud sql databases describe "$DB_NAME" --instance "$CLOUDSQL_INSTANCE" >/dev/null 2>&1 || \
  gcloud sql databases create "$DB_NAME" --instance "$CLOUDSQL_INSTANCE" >/dev/null

echo "Ensuring DB password secret exists..."
DB_PASSWORD_SECRET="solidgen-db-password"
if ! gcloud secrets describe "$DB_PASSWORD_SECRET" >/dev/null 2>&1; then
  DB_PASS="$(openssl rand -base64 32 | tr -d '\n')"
  printf "%s" "$DB_PASS" | gcloud secrets create "$DB_PASSWORD_SECRET" --data-file=- >/dev/null
else
  echo "Secret $DB_PASSWORD_SECRET already exists."
fi

echo "Creating DB user (if needed)..."
DB_PASS="$(gcloud secrets versions access latest --secret="$DB_PASSWORD_SECRET")"
gcloud sql users create "$DB_USER" \
  --instance "$CLOUDSQL_INSTANCE" \
  --password "$DB_PASS" >/dev/null 2>&1 || true

echo "Ensuring app secrets exist (you will be prompted if missing)..."
ensure_secret () {
  local name="$1"
  local prompt="$2"
  if gcloud secrets describe "$name" >/dev/null 2>&1; then
    return 0
  fi
  echo -n "$prompt: "
  read -r -s value
  echo
  printf "%s" "$value" | gcloud secrets create "$name" --data-file=- >/dev/null
}

ensure_secret "solidgen-jwt-secret" "JWT secret (random string)"
ensure_secret "solidgen-stripe-secret-key" "Stripe secret key (sk_...)"
ensure_secret "solidgen-stripe-webhook-secret" "Stripe webhook secret (whsec_...)"
ensure_secret "solidgen-nowpayments-api-key" "NOWPayments API key"
ensure_secret "solidgen-nowpayments-ipn-secret" "NOWPayments IPN secret"

echo "Bootstrap complete."
echo "API service account: $API_SA_EMAIL"
echo "Worker service account: $WORKER_SA_EMAIL"


