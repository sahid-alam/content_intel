from datetime import datetime

from pydantic import BaseModel, ConfigDict


class RawItem(BaseModel):
    """Internal transfer object from sources → ingest. Never stored directly."""

    external_id: str
    source: str
    subreddit: str | None = None
    author: str = ""
    title: str
    body: str = ""
    url: str = ""
    score: int = 0
    num_comments: int = 0
    created_utc: datetime
    raw: dict = {}


class ItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    external_id: str
    source: str
    subreddit: str | None
    author: str
    title: str
    body: str
    url: str
    score: int
    num_comments: int
    created_utc: datetime
    fetched_at: datetime
    content_hash: str
    tag: str | None = None  # populated from classification join in feed router


class FeedResponse(BaseModel):
    items: list[ItemOut]
    total: int
    limit: int
    offset: int


class SyncResult(BaseModel):
    fetched: int
    inserted: int
    skipped: int
    source: str
