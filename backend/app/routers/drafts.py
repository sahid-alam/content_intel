from datetime import UTC, datetime

from app.ai import check_daily_cap, log_call
from app.ai.drafter import DraftVariant, generate_drafts
from app.auth import get_current_user
from app.config import settings
from app.db import get_db
from app.models import Draft, Item
from app.schemas import (
    DraftOut,
    DraftPatch,
    DraftsResponse,
    GenerateDraftRequest,
    GeneratedVariant,
    GenerateResponse,
    SaveDraftRequest,
)
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/drafts", tags=["drafts"])


def _items_to_text(items: list[Item]) -> str:
    parts = []
    for item in items:
        source = f"r/{item.subreddit}" if item.subreddit else item.source.upper()
        body_preview = item.body[:400].strip() if item.body else ""
        parts.append(
            f"[{source}] {item.title}\n"
            f"URL: {item.url}\n"
            + (f"Body: {body_preview}\n" if body_preview else "")
        )
    return "\n---\n".join(parts)


@router.get("", response_model=DraftsResponse)
async def list_drafts(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user),
) -> DraftsResponse:
    base = select(Draft).where(Draft.user_id == user_id).order_by(Draft.created_at.desc())
    total: int = (
        await db.execute(select(func.count()).select_from(base.subquery()))
    ).scalar_one()
    rows = (await db.execute(base.offset(offset).limit(limit))).scalars().all()
    return DraftsResponse(drafts=list(rows), total=total, limit=limit, offset=offset)


@router.post("/generate", response_model=GenerateResponse)
async def generate(
    req: GenerateDraftRequest,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user),
) -> GenerateResponse:
    if not req.item_ids:
        raise HTTPException(status_code=422, detail="item_ids must not be empty")

    model = settings.gemini_draft_model
    await check_daily_cap(db, model)

    items = (
        await db.execute(select(Item).where(Item.id.in_(req.item_ids)))
    ).scalars().all()

    if not items:
        raise HTTPException(status_code=404, detail="No matching items found")

    items_text = _items_to_text(list(items))
    variants: list[DraftVariant] = await generate_drafts(items_text, extra_notes=req.notes)

    if not variants:
        raise HTTPException(status_code=503, detail="All draft variants failed to generate")

    # Log one call per variant (serial — DB session not shared with parallel tasks)
    for v in variants:
        await log_call(
            db,
            user_id=user_id,
            model=model,
            purpose="draft",
            tokens_in=v.tokens_in,
            tokens_out=v.tokens_out,
            duration_ms=v.duration_ms,
        )
    await db.commit()

    return GenerateResponse(
        variants=[GeneratedVariant(variant_index=v.variant_index, body=v.body) for v in variants],
        model=model,
    )


@router.post("", response_model=DraftOut)
async def save_draft(
    req: SaveDraftRequest,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user),
) -> DraftOut:
    draft = Draft(
        user_id=user_id,
        kind=req.kind,
        item_ids=req.item_ids,
        body=req.body,
        model=settings.gemini_draft_model,
        variant_index=req.variant_index,
        created_at=datetime.now(tz=UTC),
    )
    db.add(draft)
    await db.commit()
    await db.refresh(draft)
    return DraftOut.model_validate(draft)


@router.patch("/{draft_id}", response_model=DraftOut)
async def update_draft(
    draft_id: int,
    patch: DraftPatch,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user),
) -> DraftOut:
    draft = (
        await db.execute(
            select(Draft).where(Draft.id == draft_id, Draft.user_id == user_id)
        )
    ).scalar_one_or_none()
    if draft is None:
        raise HTTPException(status_code=404, detail="Draft not found")

    if patch.body is not None:
        draft.body = patch.body
    if patch.published_at is not None:
        draft.published_at = patch.published_at

    await db.commit()
    await db.refresh(draft)
    return DraftOut.model_validate(draft)


@router.delete("/{draft_id}", status_code=204)
async def delete_draft(
    draft_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user),
) -> None:
    draft = (
        await db.execute(
            select(Draft).where(Draft.id == draft_id, Draft.user_id == user_id)
        )
    ).scalar_one_or_none()
    if draft is None:
        raise HTTPException(status_code=404, detail="Draft not found")
    await db.delete(draft)
    await db.commit()
