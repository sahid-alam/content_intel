import os

from pydantic_settings import BaseSettings, SettingsConfigDict

# Resolve .env from project root regardless of working directory.
_ENV_FILE = os.path.join(os.path.dirname(__file__), "..", "..", ".env")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=_ENV_FILE, extra="ignore")

    # Database
    database_url: str = "sqlite+aiosqlite:///./data.db"

    # Gemini
    gemini_api_key: str = ""
    gemini_classify_model: str = "gemini-3.1-flash-lite"
    gemini_summarize_model: str = "gemini-3.1-flash-lite"
    gemini_extract_model: str = "gemini-3.1-flash-lite"
    gemini_draft_model: str = "gemma-4-31b-it"

    # Reddit (RSS — no credentials needed)
    reddit_subreddits: str = "SaaS,Entrepreneur,AI_Agents,automation,n8n,nocode,smallbusiness"

    # HN
    hn_keywords: str = "AI agent,n8n,voice ai,workflow automation,Make.com,GoHighLevel"
    lookback_hours: int = 24

    # Google Drive
    google_oauth_client_file: str = "backend/.gcp/oauth_client.json"
    google_token_file: str = "backend/.gcp/token.json"
    google_drive_folder_id: str = ""
    leads_sheet_id: str = ""
    leads_sheet_tab: str = "Leads"

    # Cost guardrails
    daily_flash_call_cap: int = 500
    daily_gemma_call_cap: int = 1000

    # CORS
    frontend_origin: str = "http://localhost:3000"


settings = Settings()
