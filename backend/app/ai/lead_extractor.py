import time
from datetime import UTC, datetime
from typing import Literal

from app.ai import check_daily_cap, genai_with_retry, log_call
from app.config import settings
from app.models import Item, Lead, LeadAssignment
from app.services.lead_scorer import score_lead
from google import genai
from google.genai import types
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

_client: genai.Client | None = None


def _get_client() -> genai.Client:
    global _client
    if _client is None:
        _client = genai.Client(api_key=settings.gemini_api_key)
    return _client


class LeadExtraction(BaseModel):
    what_they_want: str = Field(max_length=500)
    pain_signals: list[str] = Field(default_factory=list, max_length=5)
    budget_signal: Literal["none", "mentioned", "explicit"] = "none"
    urgency_signal: Literal["none", "mentioned", "explicit"] = "none"
    contact_hint: str | None = Field(None, max_length=200)


_FIELD_INSTRUCTIONS = """\
- what_they_want: one crisp sentence (≤30 words) describing exactly what they want built/automated
- pain_signals: up to 5 short strings capturing specific frustrations or friction they mention
- budget_signal:
    "explicit" = a number/range named ("$500", "under 2k", "paid project")
    "mentioned" = budget implied but no number ("willing to pay", "budget exists")
    "none" = no budget mention
- urgency_signal:
    "explicit" = hard deadline named ("by Friday", "this week", "ASAP")
    "mentioned" = softer urgency ("soon", "as quickly as possible")
    "none" = no urgency mention
- contact_hint: email, username, or explicit invite to DM found in post, or null"""


def _build_prompt(item: Item) -> str:
    body_preview = item.body[:800].strip() if item.body else ""
    body_section = f"\nBody: {body_preview}" if body_preview else ""
    subreddit_section = f" (r/{item.subreddit})" if item.subreddit else ""
    return f"""Extract lead intelligence from this {item.source.upper()}{subreddit_section} post for a Gen-AI dev agency.

Author: {item.author}
Title: {item.title}{body_section}

Field instructions:
{_FIELD_INSTRUCTIONS}

Return JSON matching the schema exactly."""


async def extract_lead(
    item: Item,
    db: AsyncSession,
    user_id: str = "self",
) -> LeadExtraction:
    model = settings.gemini_extract_model
    await check_daily_cap(db, model)

    t0 = time.monotonic()
    response = await genai_with_retry(
        lambda: _get_client().aio.models.generate_content(
            model=model,
            contents=_build_prompt(item),
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=LeadExtraction,
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
        purpose="extract",
        tokens_in=tokens_in,
        tokens_out=tokens_out,
        duration_ms=duration_ms,
    )

    text = response.text
    if not text:
        raise ValueError("Empty response from lead extractor")
    result = LeadExtraction.model_validate_json(text)

    lead = Lead(
        item_id=item.id,
        asker_username=item.author,
        what_they_want=result.what_they_want,
        pain_signals=result.pain_signals,
        budget_signal=result.budget_signal,
        urgency_signal=result.urgency_signal,
        contact_hint=result.contact_hint,
        score=score_lead(result.budget_signal, result.urgency_signal, result.pain_signals, item.source),
        created_at=datetime.now(tz=UTC),
    )
    db.add(lead)
    await db.flush()  # populates lead.id

    db.add(LeadAssignment(
        lead_id=lead.id,
        user_id=user_id,
        status="new",
        notes="",
        created_at=datetime.now(tz=UTC),
    ))
    await db.flush()

    return result
