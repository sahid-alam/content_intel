from datetime import UTC, datetime

from app.db import get_db
from app.models import AICallLog, Classification, Item
from app.schemas import FeedResponse, ItemOut
from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, outerjoin, select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/feed", tags=["feed"])


@router.get("", response_model=FeedResponse)
async def get_feed(
    source: str | None = Query(None),
    tag: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> FeedResponse:
    # LEFT JOIN so unclassified items still appear (tag=None)
    j = outerjoin(Item, Classification, Classification.item_id == Item.id)
    base = select(Item, Classification.tag).select_from(j)

    if source:
        base = base.where(Item.source == source)
    if tag:
        base = base.where(Classification.tag == tag)

    base = base.order_by(Item.created_utc.desc())

    count_q = select(func.count()).select_from(base.subquery())
    total: int = (await db.execute(count_q)).scalar_one()

    rows = await db.execute(base.offset(offset).limit(limit))

    items: list[ItemOut] = []
    for item_row, item_tag in rows.all():
        out = ItemOut.model_validate(item_row)
        out.tag = item_tag
        items.append(out)

    return FeedResponse(items=items, total=total, limit=limit, offset=offset)


@router.get("/usage")
async def get_today_usage(db: AsyncSession = Depends(get_db)) -> dict:
    today = datetime.now(tz=UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    count: int = (
        await db.execute(
            select(func.count()).select_from(AICallLog).where(AICallLog.created_at >= today)
        )
    ).scalar_one()
    return {"calls_today": count}
