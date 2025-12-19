from __future__ import annotations

import contextlib
import uuid
from datetime import datetime
from typing import Any

import psycopg2
import psycopg2.extras

from solidgen_worker.config import settings


@contextlib.contextmanager
def db_conn():
    # Prefer discrete settings to avoid URL encoding issues with special chars.
    if settings.database_url:
        conn = psycopg2.connect(settings.database_url)
    else:
        conn = psycopg2.connect(
            host=settings.db_host,
            port=settings.db_port,
            user=settings.db_user,
            password=settings.db_password,
            dbname=settings.db_name,
        )
    try:
        yield conn
    finally:
        conn.close()


def fetch_job(conn, job_id: uuid.UUID) -> dict[str, Any] | None:
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute("SELECT * FROM jobs WHERE id = %s", (str(job_id),))
        row = cur.fetchone()
        return dict(row) if row else None


def mark_job_running(conn, job_id: uuid.UUID):
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE jobs SET status=%s, updated_at=%s WHERE id=%s",
            ("RUNNING", datetime.utcnow(), str(job_id)),
        )


def mark_job_succeeded(conn, job_id: uuid.UUID, output_gcs_uri: str):
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE jobs SET status=%s, output_gcs_uri=%s, error_text=NULL, updated_at=%s WHERE id=%s",
            ("SUCCEEDED", output_gcs_uri, datetime.utcnow(), str(job_id)),
        )


def mark_job_failed(conn, job_id: uuid.UUID, error_text: str):
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE jobs SET status=%s, error_text=%s, updated_at=%s WHERE id=%s",
            ("FAILED", error_text[:8000], datetime.utcnow(), str(job_id)),
        )


def refund_job_if_needed(conn, job_row: dict[str, Any]):
    """
    If job failed and we already charged credits, refund once.
    """
    job_id = job_row["id"]
    user_id = job_row["user_id"]
    cost = int(job_row.get("cost_credits") or 0)
    if cost <= 0:
        return

    with conn.cursor() as cur:
        # idempotency: refund once per job
        cur.execute(
            "SELECT 1 FROM credit_ledger WHERE job_id=%s AND reason=%s LIMIT 1",
            (str(job_id), "JOB_REFUND"),
        )
        if cur.fetchone():
            return

        cur.execute("UPDATE users SET credits_balance = credits_balance + %s WHERE id=%s", (cost, str(user_id)))
        cur.execute(
            """
            INSERT INTO credit_ledger (id, user_id, job_id, delta_credits, reason, provider, external_id, created_at)
            VALUES (%s, %s, %s, %s, %s, NULL, NULL, %s)
            """,
            (str(uuid.uuid4()), str(user_id), str(job_id), cost, "JOB_REFUND", datetime.utcnow()),
        )




