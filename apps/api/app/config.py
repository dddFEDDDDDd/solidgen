from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Core
    env: str = "dev"
    api_base_url: str = "http://localhost:8080"
    cors_origins: str = "*"  # comma-separated list or "*"

    # Auth
    jwt_secret: str = "dev-insecure"
    jwt_issuer: str = "solidgen-api"
    jwt_audience: str = "solidgen-web"
    jwt_exp_minutes: int = 60 * 24 * 7

    # GCP
    gcp_project_id: str = "solidgen-481701"
    gcs_bucket: str = "solidgen-uploads"

    pubsub_topic: str = "solidgen-jobs"

    # Signed URL signing (Cloud Run / Workload Identity)
    gcs_signer_service_account_email: str | None = None
    gcs_signed_url_exp_minutes: int = 15

    # Database
    database_url: str | None = None
    db_user: str = "solidgen"
    db_password: str = ""
    db_name: str = "solidgen"
    db_host: str = "127.0.0.1"
    db_port: int = 5432
    cloudsql_instance_connection_name: str | None = None

    # Billing
    stripe_secret_key: str | None = None
    stripe_webhook_secret: str | None = None
    stripe_success_url: str = "http://localhost:3000/billing/success"
    stripe_cancel_url: str = "http://localhost:3000/billing/cancel"

    nowpayments_api_key: str | None = None
    nowpayments_ipn_secret: str | None = None


settings = Settings()




