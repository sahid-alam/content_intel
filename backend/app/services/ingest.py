import hashlib
import logging
from datetime import UTC, datetime

from app.ai.classifier import classify_item
from app.ai.lead_extractor import extract_lead
from app.ai.summarizer import summarize_item
from app.config import settings
from app.models import Classification, Item
from app.schemas import RawItem, SyncResult
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


def _content_hash(title: str, body: str) -> str:
    payload = title + "\n" + body[:5000]
    return hashlib.sha256(payload.encode()).hexdigest()


async def _classify_and_store(db: AsyncSession, item: Item, raw: RawItem) -> str | None:
    try:
        result = await classify_item(raw, db)
        db.add(Classification(
            item_id=item.id,
            tag=result.tag,
            confidence=result.confidence,
            reason=result.reason,
            topics=result.topics,
            model=settings.gemini_classify_model,
            created_at=datetime.now(tz=UTC),
        ))
        await db.flush()
        return result.tag
    except Exception as exc:
        logger.warning("classify failed for %s: %s", raw.external_id, exc)
        # Rollback any failed flush so the session stays usable for subsequent items.
        await db.rollback()
        return None


async def _summarize(db: AsyncSession, item: Item) -> None:
    try:
        await summarize_item(item, db)
    except Exception as exc:
        logger.warning("summarize failed for item %d: %s", item.id, exc)
        await db.rollback()


async def _extract(db: AsyncSession, item: Item) -> None:
    try:
        await extract_lead(item, db)
    except Exception as exc:
        logger.warning("lead extract failed for item %d: %s", item.id, exc)
        await db.rollback()


async def _process_item(db: AsyncSession, item: Item, raw: RawItem) -> None:
    tag = await _classify_and_store(db, item, raw)
    if tag and tag != "noise":
        await _summarize(db, item)
    if tag == "lead":
        await _extract(db, item)


async def ingest_items(db: AsyncSession, raw_items: list[RawItem], source: str) -> SyncResult:
    if not raw_items:
        return SyncResult(fetched=0, inserted=0, skipped=0, source=source)

    external_ids = [r.external_id for r in raw_items]
    existing = await db.execute(
        select(Item.external_id).where(Item.external_id.in_(external_ids))
    )
    seen_ids: set[str] = {row[0] for row in existing.fetchall()}

    now = datetime.now(tz=UTC)
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

    if new_items:
        # AsyncSession is not safe for concurrent use — process items sequentially.
        # AI calls within _process_item are still awaited one at a time but that's
        # fine: the bottleneck is the Gemini API rate limit (15 RPM), not local compute.
        for item, raw in new_items:
            await _process_item(db, item, raw)
        await db.commit()

    return SyncResult(fetched=len(raw_items), inserted=inserted, skipped=skipped, source=source)
