from __future__ import annotations

import datetime
import uuid
from dataclasses import dataclass

from google.auth import default as google_auth_default
from google.auth.transport.requests import Request as GoogleAuthRequest
from google.cloud import pubsub_v1, storage

from app.config import settings


def _get_access_token() -> str:
    creds, _ = google_auth_default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
    req = GoogleAuthRequest()
    creds.refresh(req)
    return creds.token  # type: ignore[return-value]


def get_pubsub_publisher() -> pubsub_v1.PublisherClient:
    return pubsub_v1.PublisherClient()


def pubsub_topic_path() -> str:
    return pubsub_v1.PublisherClient.topic_path(settings.gcp_project_id, settings.pubsub_topic)


def get_storage_client() -> storage.Client:
    return storage.Client(project=settings.gcp_project_id)


@dataclass(frozen=True)
class SignedUrlResult:
    url: str
    object_name: str
    gcs_uri: str


def sign_gcs_upload_url(*, content_type: str, file_ext: str, user_id: uuid.UUID) -> SignedUrlResult:
    if not settings.gcs_signer_service_account_email:
        raise RuntimeError("Missing gcs_signer_service_account_email")

    object_name = f"uploads/{user_id}/{uuid.uuid4()}.{file_ext}"
    client = get_storage_client()
    bucket = client.bucket(settings.gcs_bucket)
    blob = bucket.blob(object_name)

    url = blob.generate_signed_url(
        version="v4",
        expiration=datetime.timedelta(minutes=settings.gcs_signed_url_exp_minutes),
        method="PUT",
        content_type=content_type,
        service_account_email=settings.gcs_signer_service_account_email,
        access_token=_get_access_token(),
    )
    return SignedUrlResult(url=url, object_name=object_name, gcs_uri=f"gs://{settings.gcs_bucket}/{object_name}")


def sign_gcs_download_url(*, gcs_uri: str) -> str:
    if not settings.gcs_signer_service_account_email:
        raise RuntimeError("Missing gcs_signer_service_account_email")

    if not gcs_uri.startswith("gs://"):
        raise ValueError("Invalid gcs_uri")
    _, rest = gcs_uri.split("gs://", 1)
    bucket_name, object_name = rest.split("/", 1)
    client = get_storage_client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(object_name)

    return blob.generate_signed_url(
        version="v4",
        expiration=datetime.timedelta(minutes=settings.gcs_signed_url_exp_minutes),
        method="GET",
        service_account_email=settings.gcs_signer_service_account_email,
        access_token=_get_access_token(),
    )




