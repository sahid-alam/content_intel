from datetime import datetime

from app.db import Base
from sqlalchemy import (
    JSON,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column


class Item(Base):
    __tablename__ = "items"

    id: Mapped[int] = mapped_column(primary_key=True)
    external_id: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    source: Mapped[str] = mapped_column(String(16), index=True)
    subreddit: Mapped[str | None] = mapped_column(String(64), index=True, default=None)
    author: Mapped[str] = mapped_column(String(64), default="")
    title: Mapped[str] = mapped_column(String(512))
    body: Mapped[str] = mapped_column(Text, default="")
    url: Mapped[str] = mapped_column(String(512), default="")
    score: Mapped[int] = mapped_column(Integer, default=0)
    num_comments: Mapped[int] = mapped_column(Integer, default=0)
    created_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    content_hash: Mapped[str] = mapped_column(String(64), index=True)
    raw: Mapped[dict] = mapped_column(JSON, default=dict)


class Classification(Base):
    __tablename__ = "classifications"

    id: Mapped[int] = mapped_column(primary_key=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("items.id"), unique=True, index=True)
    tag: Mapped[str] = mapped_column(String(16), index=True)
    confidence: Mapped[float] = mapped_column(Float)
    reason: Mapped[str] = mapped_column(String(300))
    topics: Mapped[list] = mapped_column(JSON, default=list)
    model: Mapped[str] = mapped_column(String(32))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class Summary(Base):
    __tablename__ = "summaries"

    id: Mapped[int] = mapped_column(primary_key=True)
    content_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    one_liner: Mapped[str] = mapped_column(String(200))
    bullets: Mapped[list] = mapped_column(JSON)
    key_quote: Mapped[str | None] = mapped_column(String(300), default=None)
    model: Mapped[str] = mapped_column(String(32))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class Lead(Base):
    __tablename__ = "leads"

    id: Mapped[int] = mapped_column(primary_key=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("items.id"), unique=True, index=True)
    asker_username: Mapped[str] = mapped_column(String(64), index=True)
    what_they_want: Mapped[str] = mapped_column(String(500))
    pain_signals: Mapped[list] = mapped_column(JSON, default=list)
    budget_signal: Mapped[str] = mapped_column(String(16))
    urgency_signal: Mapped[str] = mapped_column(String(16))
    contact_hint: Mapped[str | None] = mapped_column(String(200), default=None)
    score: Mapped[float] = mapped_column(Float, index=True, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class LeadAssignment(Base):
    __tablename__ = "lead_assignments"

    id: Mapped[int] = mapped_column(primary_key=True)
    lead_id: Mapped[int] = mapped_column(ForeignKey("leads.id"), index=True)
    user_id: Mapped[str] = mapped_column(String(64), index=True)
    status: Mapped[str] = mapped_column(String(16), default="new")
    notes: Mapped[str] = mapped_column(Text, default="")
    contacted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    __table_args__ = (UniqueConstraint("lead_id", "user_id", name="uq_lead_user"),)


class Draft(Base):
    __tablename__ = "drafts"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[str] = mapped_column(String(64), index=True)
    kind: Mapped[str] = mapped_column(String(32))
    item_ids: Mapped[list] = mapped_column(JSON)
    body: Mapped[str] = mapped_column(Text)
    model: Mapped[str] = mapped_column(String(32))
    variant_index: Mapped[int] = mapped_column(default=0)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class AICallLog(Base):
    __tablename__ = "ai_call_log"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[str] = mapped_column(String(64), index=True)
    model: Mapped[str] = mapped_column(String(32), index=True)
    purpose: Mapped[str] = mapped_column(String(32))
    tokens_in: Mapped[int] = mapped_column(Integer)
    tokens_out: Mapped[int] = mapped_column(Integer)
    duration_ms: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class DocSyncLog(Base):
    __tablename__ = "doc_sync_log"

    id: Mapped[int] = mapped_column(primary_key=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("items.id"), index=True)
    doc_id: Mapped[str] = mapped_column(String(128), index=True)
    week_iso: Mapped[str] = mapped_column(String(8), index=True)
    section_heading: Mapped[str] = mapped_column(String(300))
    written_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class SheetSyncLog(Base):
    __tablename__ = "sheet_sync_log"

    id: Mapped[int] = mapped_column(primary_key=True)
    assignment_id: Mapped[int] = mapped_column(ForeignKey("lead_assignments.id"), unique=True, index=True)
    sheet_id: Mapped[str] = mapped_column(String(128))
    row_index: Mapped[int] = mapped_column(Integer)
    last_written_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    last_known_status: Mapped[str] = mapped_column(String(16))
    last_known_notes: Mapped[str] = mapped_column(Text, default="")
