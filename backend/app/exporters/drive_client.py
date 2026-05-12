"""
Google OAuth credentials loader.

Call get_credentials() at runtime. If no token exists, raises RuntimeError
with instructions to run scripts/google_auth.py first.
"""

import os

from app.config import settings
from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

SCOPES = [
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/documents",
    "https://www.googleapis.com/auth/spreadsheets",
]

# Config paths like "backend/.gcp/token.json" are relative to the project root,
# but the server runs from backend/. Resolve from this file's anchor instead.
_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))


def _resolve(path: str) -> str:
    if os.path.isabs(path):
        return path
    return os.path.join(_PROJECT_ROOT, path)


def get_credentials() -> Credentials:
    token_path = _resolve(settings.google_token_file)

    if not os.path.exists(token_path):
        raise RuntimeError(
            f"Google OAuth token not found at {token_path}. "
            "Run: uv run python scripts/google_auth.py"
        )

    creds = Credentials.from_authorized_user_file(token_path, SCOPES)
    if creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            _save_token(creds, token_path)
        except RefreshError as exc:
            raise RuntimeError(
                f"Token refresh failed ({exc}). "
                "Re-run: uv run python scripts/google_auth.py"
            ) from exc
    return creds


def _save_token(creds: Credentials, path: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(creds.to_json())
