"""
Gemma drafter — generates LinkedIn post variants.

Reads voice profile from dashboard/voice_profile.md (graceful fallback if missing).
Generates n variants in parallel (pure API, no DB side effects).
Caller owns check_daily_cap() + log_call().
"""

import asyncio
import logging
import time
from dataclasses import dataclass
from pathlib import Path

from app.config import settings
from google import genai
from google.genai import types

logger = logging.getLogger(__name__)

_PROJECT_ROOT = Path(__file__).parents[3]  # content_intel/
_VOICE_PROFILE_PATH = _PROJECT_ROOT / "dashboard" / "voice_profile.md"

_client: genai.Client | None = None


def _get_client() -> genai.Client:
    global _client
    if _client is None:
        _client = genai.Client(api_key=settings.gemini_api_key)
    return _client


_SYSTEM = (
    "You are a ghostwriter for a Gen-AI development agency founder. "
    "Write LinkedIn posts grounded in real community discussions, not generic takes. "
    "Be direct and specific. No corporate jargon. Conversational but professional tone. "
    "No hashtags unless they add concrete context. No emojis. "
    "150–300 words. End with a question or observation, not a call to action."
)


def _load_voice_profile() -> str:
    try:
        return _VOICE_PROFILE_PATH.read_text()
    except FileNotFoundError:
        return ""


def _build_prompt(items_text: str, voice: str, extra_notes: str) -> str:
    parts = []
    if voice:
        parts.append(f"Voice profile (write in this style):\n{voice}\n")
    parts.append(
        f"Source discussions from Reddit / Hacker News:\n\n{items_text}\n\n"
        "Write a LinkedIn post grounded in these discussions. "
        "Make it feel like an original insight, not a summary. "
        "Use specific details from the discussions."
    )
    if extra_notes:
        parts.append(f"\nAdditional instructions: {extra_notes}")
    return "\n".join(parts)


@dataclass
class DraftVariant:
    variant_index: int
    body: str
    tokens_in: int
    tokens_out: int
    duration_ms: int


async def _generate_one(prompt: str, variant_index: int) -> DraftVariant:
    t0 = time.monotonic()
    response = await _get_client().aio.models.generate_content(
        model=settings.gemini_draft_model,
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=_SYSTEM,
            temperature=0.8 + variant_index * 0.05,
            max_output_tokens=512,
        ),
    )
    duration_ms = int((time.monotonic() - t0) * 1000)
    usage = response.usage_metadata
    return DraftVariant(
        variant_index=variant_index,
        body=(response.text or "").strip(),
        tokens_in=(usage.prompt_token_count or 0) if usage else 0,
        tokens_out=(usage.candidates_token_count or 0) if usage else 0,
        duration_ms=duration_ms,
    )


async def generate_drafts(
    items_text: str,
    extra_notes: str = "",
    n_variants: int = 3,
) -> list[DraftVariant]:
    """Generate n_variants drafts in parallel. Pure API — no DB side effects."""
    voice = _load_voice_profile()
    prompt = _build_prompt(items_text, voice, extra_notes)

    results = await asyncio.gather(
        *[_generate_one(prompt, i) for i in range(n_variants)],
        return_exceptions=True,
    )

    variants: list[DraftVariant] = []
    for r in results:
        if isinstance(r, Exception):
            logger.warning("Variant %d generation failed: %s", len(variants), r)
        else:
            variants.append(r)
    return variants
