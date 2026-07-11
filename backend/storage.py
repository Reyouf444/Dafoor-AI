"""
Google Cloud Storage helpers for Dafoor AI.

Authentication: Uses Application Default Credentials (ADC) automatically.
  - On Cloud Run: credentials come from the attached service account — no key file needed.
  - Locally: set GOOGLE_APPLICATION_CREDENTIALS=/path/to/key.json, or run:
             gcloud auth application-default login

PDF upload flow (browser → GCS directly, server stays lightweight):
  1. POST /api/pdfs/request-upload  → server returns a signed PUT URL
  2. Browser PUTs the file directly to GCS using that URL
  3. POST /api/pdfs/confirm-upload  → server records metadata in SQLite
"""

import datetime
import os
import uuid

from google.cloud import storage

# ---------------------------------------------------------------------------
# Configuration — set these as environment variables in Cloud Run
# ---------------------------------------------------------------------------

# Name of your GCS bucket (set GCS_BUCKET_NAME env var in Cloud Run)
GCS_BUCKET_NAME = os.getenv("GCS_BUCKET_NAME", "dafoor")

# How long a signed upload URL stays valid
SIGNED_URL_EXPIRY_MINUTES = int(os.getenv("GCS_SIGNED_URL_EXPIRY_MINUTES", "15"))

# ---------------------------------------------------------------------------
# Single shared client — ADC, no key file, reused across all requests
# ---------------------------------------------------------------------------

# storage.Client() with no arguments automatically finds credentials from:
#   • Cloud Run  → attached service account (metadata server)
#   • Local dev  → GOOGLE_APPLICATION_CREDENTIALS env var or gcloud ADC
storage_client = storage.Client()
bucket = storage_client.bucket(GCS_BUCKET_NAME)


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------

def generate_upload_signed_url(user_id: int, original_filename: str) -> dict:
    """Generate a v4 signed PUT URL for a direct browser-to-GCS PDF upload.

    Returns:
        signed_url  — the URL the browser should HTTP PUT to
        gcs_path    — the object path inside the bucket (pass to confirm-upload)
        expires_at  — ISO timestamp when the URL expires
    """
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
        "gcs_path":   gcs_path,
        "expires_at": expires_at,
    }


def get_public_url(gcs_path: str) -> str:
    """Return the public HTTPS URL for a GCS object.

    Requires the bucket (or the object) to have public read access.
    """
    return f"https://storage.googleapis.com/{GCS_BUCKET_NAME}/{gcs_path}"


def delete_object(gcs_path: str) -> None:
    """Delete a GCS object. Silently ignores missing-object errors."""
    try:
        blob = bucket.blob(gcs_path)
        blob.delete()
    except Exception as exc:
        # Don't crash a DELETE endpoint just because the file is already gone
        print(f"[GCS] Warning: could not delete {gcs_path}: {exc}")
