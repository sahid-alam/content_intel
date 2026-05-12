import asyncio
import re
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import TypeVar

from app.config import settings
from app.models import AICallLog
from fastapi import HTTPException
from google.genai import errors as genai_errors
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

_T = TypeVar("_T")
_SERVER_DELAYS = (1.0, 2.0, 4.0)  # backoff for 5xx transient errors
_RATELIMIT_DELAYS = (30.0, 60.0, 120.0)  # backoff for 429 rate-limit errors


def _ratelimit_delay(exc: Exception, default: float) -> float:
    """Extract retryDelay from a Google 429 error, falling back to default."""
    match = re.search(r"retry(?:Delay|ing).*?(\d+(?:\.\d+)?)s", str(exc), re.IGNORECASE)
    return float(match.group(1)) + 2.0 if match else default


async def genai_with_retry(call: Callable[[], Awaitable[_T]]) -> _T:
    """Call a Gemini API coroutine, retrying on transient server and rate-limit errors."""
    for server_delay, rl_delay in zip(_SERVER_DELAYS, _RATELIMIT_DELAYS):
        try:
            return await call()
        except genai_errors.ServerError:
            await asyncio.sleep(server_delay)
        except genai_errors.ClientError as exc:
            if getattr(exc, "status_code", None) == 429:
                await asyncio.sleep(_ratelimit_delay(exc, rl_delay))
            else:
                raise
    return await call()

_CAPS = {
    "flash": settings.daily_flash_call_cap,
    "gemma": settings.daily_gemma_call_cap,
}

_MODEL_BUCKET = {
    "gemini": "flash",
    "gemma": "gemma",
}


def _bucket(model: str) -> str:
    for prefix, bucket in _MODEL_BUCKET.items():
        if model.startswith(prefix):
            return bucket
    return "flash"


async def check_daily_cap(db: AsyncSession, model: str) -> None:
    bucket = _bucket(model)
    cap = _CAPS.get(bucket, settings.daily_flash_call_cap)

    today_start = datetime.now(tz=UTC).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    result = await db.execute(
        select(func.count())
        .select_from(AICallLog)
        .where(AICallLog.model == model)
        .where(AICallLog.created_at >= today_start)
    )
    count: int = result.scalar_one()
    if count >= cap:
        raise HTTPException(
            status_code=429,
            detail=f"Daily cap reached for {model} ({count}/{cap}). Resets at midnight UTC.",
        )


async def log_call(
    db: AsyncSession,
    *,
    user_id: str,
    model: str,
    purpose: str,
    tokens_in: int,
    tokens_out: int,
    duration_ms: int,
) -> None:
    db.add(
        AICallLog(
            user_id=user_id,
            model=model,
            purpose=purpose,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            duration_ms=duration_ms,
            created_at=datetime.now(tz=UTC),
        )
    )
    await db.flush()
