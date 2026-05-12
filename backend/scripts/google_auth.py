"""
One-time Google OAuth bootstrap. Run this once from the backend/ directory:

    uv run python scripts/google_auth.py

It opens your browser, you authorize, and writes backend/.gcp/token.json.
After that, the server uses get_credentials() silently.
"""
import os
import sys

# Project root is two levels up from this script (project/backend/scripts/google_auth.py)
_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(_PROJECT_ROOT, "backend"))

from dotenv import load_dotenv

load_dotenv(os.path.join(_PROJECT_ROOT, ".env"))

from app.config import settings
from app.exporters.drive_client import SCOPES, _save_token
from google_auth_oauthlib.flow import InstalledAppFlow


def _resolve(path: str) -> str:
    """Resolve a config path (relative to project root) to an absolute path."""
    if os.path.isabs(path):
        return path
    return os.path.join(_PROJECT_ROOT, path)


def main() -> None:
    client_file = _resolve(settings.google_oauth_client_file)
    token_file = _resolve(settings.google_token_file)

    flow = InstalledAppFlow.from_client_secrets_file(client_file, SCOPES)
    creds = flow.run_local_server(port=0)
    _save_token(creds, token_file)
    print(f"Token saved to {token_file}")
    print("You can now start the server — no further OAuth prompts needed.")


if __name__ == "__main__":
    main()
