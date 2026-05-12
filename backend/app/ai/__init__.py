import asyncio
from collections.abc import Awaitable, Callable
from datetime import datetime, timezone
from typing import TypeVar

from fastapi import HTTPException
from google.genai import errors as genai_errors
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models import AICallLog

_T = TypeVar("_T")
_RETRY_DELAYS = (1.0, 2.0, 4.0)  # seconds; 3 retries → 4 total attempts


async def genai_with_retry(call: Callable[[], Awaitable[_T]]) -> _T:
    """Call a Gemini API coroutine, retrying on transient server errors."""
    for delay in _RETRY_DELAYS:
        try:
            return await call()
        except genai_errors.ServerError:
            await asyncio.sleep(delay)
        except genai_errors.ClientError as exc:
            if getattr(exc, "status_code", None) == 429:
                await asyncio.sleep(delay)
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

    today_start = datetime.now(tz=timezone.utc).replace(
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
            created_at=datetime.now(tz=timezone.utc),
        )
    )
    await db.flush()
