import asyncio

from app.db import get_db
from app.models import Classification, Item
from app.schemas import RawItem, SyncResult
from app.services.ingest import _process_item, ingest_items
from app.sources.hackernews import fetch_hn
from app.sources.reddit import fetch_reddit
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/sync", tags=["sync"])


@router.post("", response_model=list[SyncResult])
async def trigger_sync(db: AsyncSession = Depends(get_db)) -> list[SyncResult]:
    hn_raw, reddit_raw = await asyncio.gather(fetch_hn(), fetch_reddit())

    # ingest_items shares the DB session — must run sequentially
    hn_result = await ingest_items(db, hn_raw, source="hn")
    reddit_result = await ingest_items(db, reddit_raw, source="reddit")
    return [hn_result, reddit_result]


class BackfillResult(BaseModel):
    processed: int
    skipped_already_classified: int


@router.post("/backfill", response_model=BackfillResult)
async def backfill_classifications(
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
) -> BackfillResult:
    """Process unclassified items already in the DB. Call repeatedly until processed=0."""
    classified_ids_result = await db.execute(select(Classification.item_id))
    classified_ids: set[int] = {row[0] for row in classified_ids_result.all()}

    unclassified_result = await db.execute(
        select(Item)
        .where(Item.id.notin_(classified_ids))
        .order_by(Item.created_utc.desc())
        .limit(limit)
    )
    items: list[Item] = list(unclassified_result.scalars().all())

    if not items:
        return BackfillResult(processed=0, skipped_already_classified=len(classified_ids))

    for item in items:
        raw = RawItem(
            external_id=item.external_id,
            source=item.source,
            subreddit=item.subreddit,
            author=item.author,
            title=item.title,
            body=item.body,
            url=item.url,
            score=item.score,
            num_comments=item.num_comments,
            created_utc=item.created_utc,
            raw=item.raw,
        )
        await _process_item(db, item, raw)

    await db.commit()
    return BackfillResult(processed=len(items), skipped_already_classified=len(classified_ids))
