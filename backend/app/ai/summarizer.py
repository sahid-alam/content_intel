import time
from datetime import UTC, datetime

from app.ai import check_daily_cap, genai_with_retry, log_call
from app.config import settings
from app.models import Item, Summary
from google import genai
from google.genai import types
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

_client: genai.Client | None = None


def _get_client() -> genai.Client:
    global _client
    if _client is None:
        _client = genai.Client(api_key=settings.gemini_api_key)
    return _client


class SummaryResult(BaseModel):
    one_liner: str = Field(max_length=200)
    bullets: list[str] = Field(default_factory=list, max_length=3)
    key_quote: str | None = Field(None, max_length=300)


def _build_prompt(item: Item) -> str:
    body_preview = item.body[:600].strip() if item.body else ""
    body_section = f"\nBody: {body_preview}" if body_preview else ""
    return f"""Summarize this {item.source.upper()} post for a Gen-AI dev agency's content pipeline.

Title: {item.title}{body_section}

Return JSON with:
- one_liner: one crisp sentence (≤25 words) capturing the core signal
- bullets: 2-3 bullet strings with the most actionable details
- key_quote: the single best quoted sentence from the body, or null if body is empty"""


async def summarize_item(
    item: Item,
    db: AsyncSession,
    user_id: str = "self",
) -> SummaryResult:
    existing = (await db.execute(
        select(Summary).where(Summary.content_hash == item.content_hash)
    )).scalar_one_or_none()
    if existing:
        return SummaryResult(
            one_liner=existing.one_liner,
            bullets=existing.bullets,
            key_quote=existing.key_quote,
        )

    model = settings.gemini_summarize_model
    await check_daily_cap(db, model)

    t0 = time.monotonic()
    response = await genai_with_retry(
        lambda: _get_client().aio.models.generate_content(
            model=model,
            contents=_build_prompt(item),
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=SummaryResult,
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
        purpose="summarize",
        tokens_in=tokens_in,
        tokens_out=tokens_out,
        duration_ms=duration_ms,
    )

    text = response.text
    if not text:
        raise ValueError("Empty response from summarizer")
    result = SummaryResult.model_validate_json(text)

    db.add(Summary(
        content_hash=item.content_hash,
        one_liner=result.one_liner,
        bullets=result.bullets,
        key_quote=result.key_quote,
        model=model,
        created_at=datetime.now(tz=UTC),
    ))
    await db.flush()
    return result
