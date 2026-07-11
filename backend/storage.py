"""
Google Cloud Storage helpers for Dafoor AI.

Authentication: Application Default Credentials (ADC) — no key file needed.
  • Cloud Run  → attached service account via Workload Identity (metadata server)
  • Local dev  → gcloud auth application-default login

Signed URL signing on Cloud Run:
  generate_signed_url() normally requires an RSA private key, but Cloud Run's
  Workload Identity only provides an OAuth2 token. We fix this by passing
  service_account_email + access_token to the call, which delegates signing
  to the IAM signBlob API instead of a local key.

  Required IAM permission on the Cloud Run service account:
      roles/iam.serviceAccountTokenCreator  (on itself)
  Or the narrower permission:
      iam.serviceAccounts.signBlob

PDF upload flow (browser → GCS directly, server stays lightweight):
  1. POST /api/pdfs/request-upload  → server returns a signed PUT URL
  2. Browser PUTs the PDF directly to GCS using that URL
  3. POST /api/pdfs/confirm-upload  → server records metadata in SQLite
"""

import datetime
import os
import uuid

import google.auth
import google.auth.transport.requests
from google.cloud import storage

# ---------------------------------------------------------------------------
# Configuration — set these as environment variables in Cloud Run
# ---------------------------------------------------------------------------

GCS_BUCKET_NAME            = os.getenv("GCS_BUCKET_NAME", "dafoor")
SIGNED_URL_EXPIRY_MINUTES  = int(os.getenv("GCS_SIGNED_URL_EXPIRY_MINUTES", "15"))

# ---------------------------------------------------------------------------
# Shared GCS client — pure ADC, no key file
# ---------------------------------------------------------------------------

storage_client = storage.Client()
bucket         = storage_client.bucket(GCS_BUCKET_NAME)


# ---------------------------------------------------------------------------
# Internal: get refreshed ADC credentials for IAM-based URL signing
# ---------------------------------------------------------------------------

def _get_fresh_credentials():
    """Return refreshed ADC credentials.

    On Cloud Run these are Compute Engine credentials attached to the
    service account. refresh() is needed so .token is populated and
    .service_account_email is available for the signBlob API call.
    """
    credentials, _ = google.auth.default(
        scopes=["https://www.googleapis.com/auth/cloud-platform"]
    )
    auth_request = google.auth.transport.requests.Request()
    credentials.refresh(auth_request)
    return credentials


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------

def generate_upload_signed_url(user_id: int, original_filename: str) -> dict:
    """Generate a v4 signed PUT URL for a direct browser-to-GCS PDF upload.

    Uses IAM signBlob API for signing — works on Cloud Run without a key file.

    Returns:
        signed_url  — the URL the browser should HTTP PUT the file to
        gcs_path    — object path inside the bucket (pass to confirm-upload)
        expires_at  — ISO timestamp when the URL expires
    """
    # Build a unique, collision-free object path
    safe_name = "".join(
        c if c.isalnum() or c in (".", "-", "_") else "_"
        for c in original_filename
    )
    gcs_path = f"pdfs/{user_id}/{uuid.uuid4().hex}_{safe_name}"
    blob     = bucket.blob(gcs_path)

    # Get fresh ADC credentials — provides service_account_email + access_token
    credentials = _get_fresh_credentials()

    expiration = datetime.timedelta(minutes=SIGNED_URL_EXPIRY_MINUTES)

    # Passing service_account_email + access_token delegates signing to the
    # IAM API — no RSA private key required on Cloud Run.
    signed_url = blob.generate_signed_url(
        version="v4",
        expiration=expiration,
        method="PUT",
        content_type="application/pdf",
        service_account_email=credentials.service_account_email,
        access_token=credentials.token,
    )

    expires_at = (datetime.datetime.utcnow() + expiration).isoformat() + "Z"

    return {
        "signed_url": signed_url,
        "gcs_path":   gcs_path,
        "expires_at": expires_at,
    }


def get_public_url(gcs_path: str) -> str:
    """Return the public HTTPS URL for a GCS object."""
    return f"https://storage.googleapis.com/{GCS_BUCKET_NAME}/{gcs_path}"


def delete_object(gcs_path: str) -> None:
    """Delete a GCS object. Silently ignores missing-object (404) errors."""
    try:
        bucket.blob(gcs_path).delete()
    except Exception as exc:
        print(f"[GCS] Warning: could not delete {gcs_path}: {exc}")
