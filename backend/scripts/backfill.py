"""
Backfill classifications for items already in the DB.
Run from backend/:  uv run python scripts/backfill.py [--limit N]

Processes unclassified items in batches of 50, committing after each one.
Safe to kill and re-run — already-classified items are skipped.
"""
import argparse
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))

from app.db import AsyncSessionLocal
from app.models import Classification, Item
from app.schemas import RawItem
from app.services.ingest import _process_item
from sqlalchemy import select


async def backfill(limit: int) -> None:
    processed = 0
    skipped = 0

    async with AsyncSessionLocal() as db:
        classified_ids = {
            row[0]
            for row in (await db.execute(select(Classification.item_id))).all()
        }
        result = await db.execute(
            select(Item)
            .where(Item.id.notin_(classified_ids))
            .order_by(Item.created_utc.desc())
            .limit(limit)
        )
        items = list(result.scalars().all())

    if not items:
        print(f"Nothing to backfill. {len(classified_ids)} already classified.")
        return

    print(f"Found {len(items)} unclassified items (of {len(classified_ids)} already done). Processing...")

    for i, item in enumerate(items, 1):
        async with AsyncSessionLocal() as db:
            # Re-fetch item inside fresh session to avoid stale state
            fresh = (await db.execute(select(Item).where(Item.id == item.id))).scalar_one()
            raw = RawItem(
                external_id=fresh.external_id,
                source=fresh.source,
                subreddit=fresh.subreddit,
                author=fresh.author,
                title=fresh.title,
                body=fresh.body,
                url=fresh.url,
                score=fresh.score,
                num_comments=fresh.num_comments,
                created_utc=fresh.created_utc,
                raw=fresh.raw,
            )
            await _process_item(db, fresh, raw)
            await db.commit()

        processed += 1
        if i % 5 == 0:
            total_done = len(classified_ids) + processed
            print(f"  [{i}/{len(items)}] {processed} processed this run, {total_done} total classified")

    print(f"\nDone. Processed {processed} items this run, skipped {skipped}.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=200, help="Max items to process per run")
    args = parser.parse_args()
    asyncio.run(backfill(args.limit))
