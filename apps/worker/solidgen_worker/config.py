from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # GCP
    gcp_project_id: str = "solidgen-481701"
    pubsub_subscription: str = "solidgen-jobs-sub"
    gcs_bucket: str = "solidgen-uploads"

    # DB (prefer DATABASE_URL via Cloud SQL proxy)
    database_url: str = "postgresql://solidgen:solidgen@127.0.0.1:5432/solidgen"

    # Model
    trellis_model_id: str = "microsoft/TRELLIS.2-4B"


settings = Settings()




