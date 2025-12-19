from __future__ import annotations

import io

from google.cloud import storage
from PIL import Image

from solidgen_worker.config import settings


def storage_client() -> storage.Client:
    return storage.Client(project=settings.gcp_project_id)


def download_image_from_gcs(gcs_uri: str) -> Image.Image:
    if not gcs_uri.startswith("gs://"):
        raise ValueError("Invalid gcs_uri")
    _, rest = gcs_uri.split("gs://", 1)
    bucket_name, object_name = rest.split("/", 1)

    client = storage_client()
    blob = client.bucket(bucket_name).blob(object_name)
    data = blob.download_as_bytes()
    return Image.open(io.BytesIO(data))


def upload_file_to_gcs(*, local_path: str, object_name: str, content_type: str) -> str:
    client = storage_client()
    bucket = client.bucket(settings.gcs_bucket)
    blob = bucket.blob(object_name)
    blob.upload_from_filename(local_path, content_type=content_type)
    return f"gs://{settings.gcs_bucket}/{object_name}"




