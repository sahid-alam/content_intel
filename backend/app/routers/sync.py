import asyncio

from app.db import get_db
from app.schemas import SyncResult
from app.services.ingest import ingest_items
from app.sources.hackernews import fetch_hn
from app.sources.reddit import fetch_reddit
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/sync", tags=["sync"])


@router.post("", response_model=list[SyncResult])
async def trigger_sync(db: AsyncSession = Depends(get_db)) -> list[SyncResult]:
    hn_raw, reddit_raw = await asyncio.gather(fetch_hn(), fetch_reddit())

    # ingest_items shares the DB session — must run sequentially
    hn_result = await ingest_items(db, hn_raw, source="hn")
    reddit_result = await ingest_items(db, reddit_raw, source="reddit")
    return [hn_result, reddit_result]
