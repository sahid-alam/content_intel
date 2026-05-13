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


class LeadOut(BaseModel):
    assignment_id: int
    lead_id: int
    item_id: int
    title: str
    url: str
    source: str
    subreddit: str | None
    author: str
    external_id: str
    created_utc: datetime
    what_they_want: str
    budget_signal: str
    urgency_signal: str
    score: float
    contact_hint: str | None
    status: str
    notes: str
    contacted_at: datetime | None


class LeadsResponse(BaseModel):
    leads: list[LeadOut]
    total: int
    limit: int
    offset: int


class AssignmentPatch(BaseModel):
    status: str | None = None
    notes: str | None = None


# ─── Drafts ───

class DraftOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: str
    kind: str
    item_ids: list[int]
    body: str
    model: str
    variant_index: int
    published_at: datetime | None
    created_at: datetime


class DraftsResponse(BaseModel):
    drafts: list[DraftOut]
    total: int
    limit: int
    offset: int


class GenerateDraftRequest(BaseModel):
    item_ids: list[int]
    notes: str = ""


class GeneratedVariant(BaseModel):
    variant_index: int
    body: str


class GenerateResponse(BaseModel):
    variants: list[GeneratedVariant]
    model: str


class SaveDraftRequest(BaseModel):
    item_ids: list[int]
    body: str
    variant_index: int = 0
    kind: str = "linkedin_post"


class DraftPatch(BaseModel):
    body: str | None = None
    published_at: datetime | None = None
