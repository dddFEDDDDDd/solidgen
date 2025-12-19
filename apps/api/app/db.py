from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import settings


def _build_database_url() -> str:
    if settings.database_url:
        return settings.database_url

    if settings.cloudsql_instance_connection_name:
        # Cloud Run: connect via unix socket mounted at /cloudsql
        # https://cloud.google.com/sql/docs/postgres/connect-run
        return (
            "postgresql+psycopg2://"
            f"{settings.db_user}:{settings.db_password}"
            f"@/{settings.db_name}"
            f"?host=/cloudsql/{settings.cloudsql_instance_connection_name}"
        )

    return (
        "postgresql+psycopg2://"
        f"{settings.db_user}:{settings.db_password}"
        f"@{settings.db_host}:{settings.db_port}/{settings.db_name}"
    )


engine = create_engine(
    _build_database_url(),
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)




