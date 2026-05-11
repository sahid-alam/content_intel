# Data Model

## Tables

```python
# backend/app/models.py — SQLAlchemy 2.0 declarative style

from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, Integer, Float, DateTime, Text, JSON, ForeignKey, Index
from datetime import datetime

class Base(DeclarativeBase): pass

class Item(Base):
    __tablename__ = "items"

    id: Mapped[int] = mapped_column(primary_key=True)
    external_id: Mapped[str] = mapped_column(String(128), unique=True, index=True)  # "reddit:abc" / "hn:12345"
    source: Mapped[str] = mapped_column(String(16), index=True)                     # "reddit" / "hn"
    subreddit: Mapped[str | None] = mapped_column(String(64), index=True, default=None)
    author: Mapped[str] = mapped_column(String(64), index=True)
    title: Mapped[str] = mapped_column(String(512))
    body: Mapped[str] = mapped_column(Text)
    url: Mapped[str] = mapped_column(String(512))
    score: Mapped[int] = mapped_column(default=0)
    num_comments: Mapped[int] = mapped_column(default=0)
    created_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    content_hash: Mapped[str] = mapped_column(String(64), index=True)
    raw: Mapped[dict] = mapped_column(JSON, default=dict)  # debugging only

class Classification(Base):
    __tablename__ = "classifications"

    id: Mapped[int] = mapped_column(primary_key=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("items.id"), unique=True, index=True)
    tag: Mapped[str] = mapped_column(String(16), index=True)         # pain | lead | trend | signal | noise
    confidence: Mapped[float]
    reason: Mapped[str] = mapped_column(String(300))
    topics: Mapped[list[str]] = mapped_column(JSON, default=list)
    model: Mapped[str] = mapped_column(String(32))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

class Summary(Base):
    __tablename__ = "summaries"

    id: Mapped[int] = mapped_column(primary_key=True)
    content_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)  # cache key
    one_liner: Mapped[str] = mapped_column(String(200))
    bullets: Mapped[list[str]] = mapped_column(JSON)
    key_quote: Mapped[str | None] = mapped_column(String(300), default=None)
    model: Mapped[str] = mapped_column(String(32))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

class Lead(Base):
    __tablename__ = "leads"

    id: Mapped[int] = mapped_column(primary_key=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("items.id"), unique=True, index=True)
    asker_username: Mapped[str] = mapped_column(String(64), index=True)
    what_they_want: Mapped[str] = mapped_column(String(500))
    pain_signals: Mapped[list[str]] = mapped_column(JSON, default=list)
    budget_signal: Mapped[str] = mapped_column(String(16))    # explicit | implicit | none
    urgency_signal: Mapped[str] = mapped_column(String(16))   # urgent | soon | exploring | unclear
    contact_hint: Mapped[str | None] = mapped_column(String(200), default=None)
    score: Mapped[float] = mapped_column(Float, index=True, default=0.0)  # rule-based, see lead_scorer.py
    status: Mapped[str] = mapped_column(String(16), default="new")        # new | contacted | won | lost | dismissed
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

class Draft(Base):
    __tablename__ = "drafts"

    id: Mapped[int] = mapped_column(primary_key=True)
    kind: Mapped[str] = mapped_column(String(32))   # "linkedin_post" | "lead_magnet_outline"
    item_ids: Mapped[list[int]] = mapped_column(JSON)
    body: Mapped[str] = mapped_column(Text)
    model: Mapped[str] = mapped_column(String(32))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

class AICallLog(Base):
    __tablename__ = "ai_call_log"

    id: Mapped[int] = mapped_column(primary_key=True)
    model: Mapped[str] = mapped_column(String(32), index=True)
    purpose: Mapped[str] = mapped_column(String(32))   # classify | summarize | extract_lead | linkedin | magnet
    tokens_in: Mapped[int]
    tokens_out: Mapped[int]
    cost_estimate_usd: Mapped[float]
    duration_ms: Mapped[int]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
```

## Indexes worth adding (in migrations)
```sql
CREATE INDEX idx_items_source_created ON items(source, created_utc DESC);
CREATE INDEX idx_classifications_tag_created ON classifications(tag, created_at DESC);
CREATE INDEX idx_leads_score_status ON leads(score DESC, status);
```

## Dedupe contract
- Insertion path: `services/ingest.py` does `INSERT ... ON CONFLICT(external_id) DO NOTHING`. SQLite supports this since 3.24.
- AI cache lookup: `Summary` is keyed by `content_hash`, not `item_id`, so a repost of the same content (same title+body) reuses the existing summary even if the post is new.

## Migrations
Use Alembic. `alembic init backend/migrations` once, then `alembic revision --autogenerate -m "..."` per change. Alembic + SQLite has well-known limitations on `ALTER TABLE` — for v1 the schema is small enough that "drop the dev DB and re-create" is acceptable; introduce real migrations only when you have data you can't lose.

## Backup
SQLite + WAL means a single-file backup is trivial: `cp data.db data.db.$(date +%F).bak`. Add a weekly cron or just do it manually. Since the AI outputs are cached in this DB, losing it = re-paying for everything you've classified and summarized.