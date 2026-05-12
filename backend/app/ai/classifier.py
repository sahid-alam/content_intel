import time
from typing import Literal

from google import genai
from google.genai import types
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai import check_daily_cap, genai_with_retry, log_call
from app.config import settings
from app.schemas import RawItem

_client: genai.Client | None = None


def _get_client() -> genai.Client:
    global _client
    if _client is None:
        _client = genai.Client(api_key=settings.gemini_api_key)
    return _client

TAG_DEFINITIONS = """
- pain: Person venting about a real problem but NOT asking for a build/service. Content fodder.
- lead: Person asking how to build / who can build / what tool to use for something a Gen-AI dev agency could build. Direct intent. Examples: "Looking for someone to build me an n8n workflow", "How do I automate X across Slack and HubSpot?", "Need a voice agent that..."
- trend: News/release/discussion about a tool, technique, or shift relevant to AI/automation/agents.
- signal: Useful but doesn't fit above — someone sharing what worked, a teardown, a technique.
- noise: Memes, drama, off-topic, generic complaints. Never advances past classification.
"""


class ClassificationResult(BaseModel):
    tag: Literal["pain", "lead", "trend", "signal", "noise"]
    confidence: float = Field(ge=0.0, le=1.0)
    reason: str = Field(max_length=200)
    topics: list[str] = Field(default_factory=list, max_length=5)


def _build_prompt(item: RawItem) -> str:
    body_preview = item.body[:500].strip() if item.body else ""
    body_section = f"\nBody: {body_preview}" if body_preview else ""
    return f"""You are classifying a post from {item.source.upper()} for a Gen-AI development agency's content pipeline.

Source: {item.source.upper()}{f' (r/{item.subreddit})' if item.subreddit else ''}
Title: {item.title}{body_section}

Tag definitions:
{TAG_DEFINITIONS}

Classify this post. Return JSON matching the schema exactly."""


async def classify_item(
    item: RawItem,
    db: AsyncSession,
    user_id: str = "self",
) -> ClassificationResult:
    model = settings.gemini_classify_model
    await check_daily_cap(db, model)

    prompt = _build_prompt(item)
    t0 = time.monotonic()

    response = await genai_with_retry(
        lambda: _get_client().aio.models.generate_content(
            model=model,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=ClassificationResult,
                temperature=0.0,
                max_output_tokens=1024,
            ),
        )
    )

    duration_ms = int((time.monotonic() - t0) * 1000)
    usage = response.usage_metadata
    tokens_in = (usage.prompt_token_count or 0) if usage else 0
    tokens_out = (usage.candidates_token_count or 0) if usage else 0

    await log_call(
        db,
        user_id=user_id,
        model=model,
        purpose="classify",
        tokens_in=tokens_in,
        tokens_out=tokens_out,
        duration_ms=duration_ms,
    )

    text = response.text
    if not text:
        raise ValueError("Empty response from classifier model")
    return ClassificationResult.model_validate_json(text)
