from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # GCP
    gcp_project_id: str = "solidgen-481701"
    pubsub_subscription: str = "solidgen-jobs-sub"
    gcs_bucket: str = "solidgen-uploads"

    # DB (prefer discrete fields; fall back to DATABASE_URL)
    database_url: str | None = None
    db_user: str = "solidgen"
    db_password: str = "solidgen"
    db_host: str = "127.0.0.1"
    db_port: int = 5432
    db_name: str = "solidgen"

    # Model
    trellis_model_id: str = "microsoft/TRELLIS.2-4B"


settings = Settings()




