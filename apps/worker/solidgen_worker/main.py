from __future__ import annotations

import json
import logging
import os
import signal
import sys
import uuid

from google.cloud import pubsub_v1

from solidgen_worker.config import settings
from solidgen_worker.db import (
    db_conn,
    fetch_job,
    mark_job_failed,
    mark_job_running,
    mark_job_succeeded,
    refund_job_if_needed,
)
from solidgen_worker.gcs import download_image_from_gcs, upload_file_to_gcs
from solidgen_worker.trellis_runner import run_trellis_to_glb


_stop = False
_future = None


logger = logging.getLogger("solidgen-worker")


def _handle_sigterm(_signum, _frame):
    global _stop
    _stop = True
    global _future
    if _future is not None:
        _future.cancel()


def process_job(job_id: uuid.UUID):
    logger.info("Processing job_id=%s", job_id)
    with db_conn() as conn:
        conn.autocommit = False
        job = fetch_job(conn, job_id)
        if not job:
            logger.error("Job not found in DB (job_id=%s). Check worker DATABASE_URL / proxy.", job_id)
            conn.rollback()
            raise RuntimeError(f"job_not_found:{job_id}")

        status = str(job.get("status") or "")
        if status in {"SUCCEEDED"}:
            logger.info("Job already SUCCEEDED (job_id=%s); skipping.", job_id)
            conn.rollback()
            return
        if status in {"RUNNING"}:
            logger.info("Job already RUNNING (job_id=%s); skipping.", job_id)
            conn.rollback()
            return
        if status in {"FAILED"}:
            logger.info("Job already FAILED (job_id=%s); skipping.", job_id)
            conn.rollback()
            return

        mark_job_running(conn, job_id)
        conn.commit()
        logger.info("Marked RUNNING (job_id=%s)", job_id)

    # Heavy work outside transaction
    try:
        image = download_image_from_gcs(job["input_gcs_uri"])
        params = job.get("params") or {}
        resolution = int(params.get("resolution") or 1024)
        seed = int(params.get("seed") or 0)
        decimation_target = int(params.get("decimation_target") or 500_000)
        texture_size = int(params.get("texture_size") or 2048)

        repo_root = os.environ.get("SOLIDGEN_REPO_ROOT") or os.getcwd()
        out = run_trellis_to_glb(
            repo_root=repo_root,
            image=image,
            model_id=settings.trellis_model_id,
            resolution=resolution,
            seed=seed,
            decimation_target=decimation_target,
            texture_size=texture_size,
        )

        object_name = f"outputs/{job['user_id']}/{job_id}/asset.glb"
        output_uri = upload_file_to_gcs(local_path=out.glb_path, object_name=object_name, content_type="model/gltf-binary")

        with db_conn() as conn2:
            conn2.autocommit = False
            mark_job_succeeded(conn2, job_id, output_uri)
            conn2.commit()
        logger.info("Marked SUCCEEDED (job_id=%s, output=%s)", job_id, output_uri)
    except Exception as e:
        err = f"{type(e).__name__}: {e}"
        logger.exception("Job failed (job_id=%s): %s", job_id, err)
        with db_conn() as conn3:
            conn3.autocommit = False
            mark_job_failed(conn3, job_id, err)
            job_row = fetch_job(conn3, job_id)
            if job_row:
                refund_job_if_needed(conn3, job_row)
            conn3.commit()


def main():
    logging.basicConfig(
        level=os.environ.get("LOG_LEVEL", "INFO").upper(),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    signal.signal(signal.SIGTERM, _handle_sigterm)
    signal.signal(signal.SIGINT, _handle_sigterm)

    subscriber = pubsub_v1.SubscriberClient()
    sub_path = subscriber.subscription_path(settings.gcp_project_id, settings.pubsub_subscription)

    flow = pubsub_v1.types.FlowControl(max_messages=1)

    def callback(message: pubsub_v1.subscriber.message.Message):
        if _stop:
            message.nack()
            return
        try:
            data = json.loads(message.data.decode("utf-8"))
            job_id = uuid.UUID(data["job_id"])
        except Exception:
            # If parsing fails, ack to avoid poison-pill loops.
            logger.exception("Invalid Pub/Sub message; acking. data=%r", message.data)
            message.ack()
            return

        try:
            logger.info("Received Pub/Sub message job_id=%s", job_id)
            process_job(job_id)
            message.ack()
            logger.info("Acked Pub/Sub message job_id=%s", job_id)
        except Exception:
            # NACK so it retries (DB down, proxy misconfigured, transient GCS, etc.)
            logger.exception("Error processing job_id=%s; nacking for retry.", job_id)
            message.nack()

    global _future
    _future = subscriber.subscribe(sub_path, callback=callback, flow_control=flow)
    try:
        _future.result()
    finally:
        if _future:
            _future.cancel()
        subscriber.close()


if __name__ == "__main__":
    main()


