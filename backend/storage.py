"""
Google Cloud Storage helpers for Dafoor AI.

PDF uploads use a "signed URL" flow so files go directly from the
browser → GCS without passing through the FastAPI server, keeping
the server lightweight and Cloud Run-friendly.

Flow:
  1. Frontend calls POST /api/pdfs/request-upload
       → server returns a signed PUT URL (valid 15 min)
  2. Frontend PUTs the file directly to GCS using that URL
  3. Frontend calls POST /api/pdfs/confirm-upload
       → server records the file metadata in SQLite
"""

import datetime
import os
import uuid

from google.cloud import storage

# ---------------------------------------------------------------------------
# Configuration — override via environment variables in Cloud Run
# ---------------------------------------------------------------------------

GCS_BUCKET_NAME = os.getenv("GCS_BUCKET_NAME", "dafoor")
SIGNED_URL_EXPIRY_MINUTES = int(os.getenv("GCS_SIGNED_URL_EXPIRY_MINUTES", "15"))


def _get_client() -> storage.Client:
    """Return an authenticated GCS client.
    
    On Cloud Run the service account credentials are picked up automatically
    from the metadata server. Locally you can set GOOGLE_APPLICATION_CREDENTIALS
    to a service account key file.
    """
    return storage.Client()


def generate_upload_signed_url(user_id: int, original_filename: str) -> dict:
    """Generate a v4 signed PUT URL for a PDF upload.

    Returns a dict with:
      - signed_url: the URL the client should PUT to
      - gcs_path:   the object path inside the bucket (used in confirm step)
      - expires_at: ISO timestamp when the URL expires
    """
    client = _get_client()
    bucket = client.bucket(GCS_BUCKET_NAME)

    # Build a unique, safe object path: pdfs/<user_id>/<uuid>_<filename>
    safe_name = "".join(
        c if c.isalnum() or c in (".", "-", "_") else "_"
        for c in original_filename
    )
    gcs_path = f"pdfs/{user_id}/{uuid.uuid4().hex}_{safe_name}"

    blob = bucket.blob(gcs_path)

    expiration = datetime.timedelta(minutes=SIGNED_URL_EXPIRY_MINUTES)
    signed_url = blob.generate_signed_url(
        version="v4",
        expiration=expiration,
        method="PUT",
        content_type="application/pdf",
    )

    expires_at = (datetime.datetime.utcnow() + expiration).isoformat() + "Z"

    return {
        "signed_url": signed_url,
        "gcs_path": gcs_path,
        "expires_at": expires_at,
    }


def get_public_url(gcs_path: str) -> str:
    """Return the public HTTPS URL for an object.

    NOTE: The bucket must have public read access (or you should use
    another signed GET URL). For private buckets, generate a signed
    GET URL instead.
    """
    return f"https://storage.googleapis.com/{GCS_BUCKET_NAME}/{gcs_path}"


def delete_object(gcs_path: str) -> None:
    """Delete an object from GCS. Silently ignores 404 errors."""
    try:
        client = _get_client()
        bucket = client.bucket(GCS_BUCKET_NAME)
        blob = bucket.blob(gcs_path)
        blob.delete()
    except Exception as exc:
        # Log but don't raise — a missing object shouldn't crash a delete endpoint
        print(f"[GCS] Warning: could not delete {gcs_path}: {exc}")
