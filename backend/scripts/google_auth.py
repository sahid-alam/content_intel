"""
One-time Google OAuth bootstrap. Run this once from the backend/ directory:

    uv run python scripts/google_auth.py

It opens your browser, you authorize, and writes backend/.gcp/token.json.
After that, the server uses get_credentials() silently.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))

from app.config import settings
from app.exporters.drive_client import SCOPES, _save_token
from google_auth_oauthlib.flow import InstalledAppFlow


def main() -> None:
    flow = InstalledAppFlow.from_client_secrets_file(settings.google_oauth_client_file, SCOPES)
    creds = flow.run_local_server(port=0)
    _save_token(creds, settings.google_token_file)
    print(f"Token saved to {settings.google_token_file}")
    print("You can now start the server — no further OAuth prompts needed.")


if __name__ == "__main__":
    main()
