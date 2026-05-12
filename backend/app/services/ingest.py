import asyncio
import hashlib
import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.classifier import classify_item
from app.models import Classification, Item
from app.schemas import RawItem, SyncResult

logger = logging.getLogger(__name__)


def _content_hash(title: str, body: str) -> str:
    payload = title + "\n" + body[:5000]
    return hashlib.sha256(payload.encode()).hexdigest()


async def _classify_and_store(db: AsyncSession, item: Item, raw: RawItem) -> None:
    try:
        result = await classify_item(raw, db)
        db.add(
            Classification(
                item_id=item.id,
                tag=result.tag,
                confidence=result.confidence,
                reason=result.reason,
                topics=result.topics,
                model="gemini-classify",
                created_at=datetime.now(tz=timezone.utc),
            )
        )
        await db.flush()
    except Exception as exc:
        # Cap hit or API error — log and continue; item is still stored
        logger.warning("classify failed for %s: %s", raw.external_id, exc)


async def ingest_items(db: AsyncSession, raw_items: list[RawItem], source: str) -> SyncResult:
    if not raw_items:
        return SyncResult(fetched=0, inserted=0, skipped=0, source=source)

    external_ids = [r.external_id for r in raw_items]
    existing = await db.execute(
        select(Item.external_id).where(Item.external_id.in_(external_ids))
    )
    seen_ids: set[str] = {row[0] for row in existing.fetchall()}

    now = datetime.now(tz=timezone.utc)
    inserted = 0
    skipped = 0
    new_items: list[tuple[Item, RawItem]] = []

    for raw in raw_items:
        if raw.external_id in seen_ids:
            skipped += 1
            continue
        item = Item(
            external_id=raw.external_id,
            source=raw.source,
            subreddit=raw.subreddit,
            author=raw.author,
            title=raw.title,
            body=raw.body,
            url=raw.url,
            score=raw.score,
            num_comments=raw.num_comments,
            created_utc=raw.created_utc,
            fetched_at=now,
            content_hash=_content_hash(raw.title, raw.body),
            raw=raw.raw,
        )
        db.add(item)
        try:
            await db.flush()
            new_items.append((item, raw))
            inserted += 1
        except IntegrityError:
            await db.rollback()
            skipped += 1

    await db.commit()

    # Classify new items — run concurrently but cap concurrency to avoid rate-limiting
    if new_items:
        sem = asyncio.Semaphore(5)

        async def _guarded(item: Item, raw: RawItem) -> None:
            async with sem:
                await _classify_and_store(db, item, raw)

        await asyncio.gather(*[_guarded(item, raw) for item, raw in new_items])
        await db.commit()

    return SyncResult(fetched=len(raw_items), inserted=inserted, skipped=skipped, source=source)
