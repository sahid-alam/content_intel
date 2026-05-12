# Data Model

## v1 vs v2

v1 is SQLite with single user (`user_id = "self"` hardcoded). v2 is Supabase Postgres with two users and RLS-enforced row-level access.

The schema is designed so the v1 → v2 migration is mechanical:
- **Shared tables** (curated content): `items`, `classifications`, `summaries` — no `user_id`. Same row visible to all users.
- **Personal tables**: `lead_assignments`, `drafts`, `ai_call_log` — every row has `user_id`. RLS in v2 filters by `auth.uid()`.
- **Hybrid: `leads`** — the lead itself is shared (it's just metadata about a public post). Per-user state (status, notes, contacted_at) lives on `lead_assignments`, one row per `(lead_id, user_id)` pair.

This split is the entire point of "hybrid data model." Curated content compounds across users; personal state stays personal.

## Tables

```python
# backend/app/models.py — SQLAlchemy 2.0 declarative

from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, Integer, Float, DateTime, Text, JSON, ForeignKey, UniqueConstraint
from datetime import datetime

class Base(DeclarativeBase): pass

# ─── SHARED CURATED CONTENT (no user_id) ───

class Item(Base):
    __tablename__ = "items"
    id: Mapped[int] = mapped_column(primary_key=True)
    external_id: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    source: Mapped[str] = mapped_column(String(16), index=True)
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
    raw: Mapped[dict] = mapped_column(JSON, default=dict)

class Classification(Base):
    __tablename__ = "classifications"
    id: Mapped[int] = mapped_column(primary_key=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("items.id"), unique=True, index=True)
    tag: Mapped[str] = mapped_column(String(16), index=True)
    confidence: Mapped[float]
    reason: Mapped[str] = mapped_column(String(300))
    topics: Mapped[list[str]] = mapped_column(JSON, default=list)
    model: Mapped[str] = mapped_column(String(32))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

class Summary(Base):
    __tablename__ = "summaries"
    id: Mapped[int] = mapped_column(primary_key=True)
    content_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    one_liner: Mapped[str] = mapped_column(String(200))
    bullets: Mapped[list[str]] = mapped_column(JSON)
    key_quote: Mapped[str | None] = mapped_column(String(300), default=None)
    model: Mapped[str] = mapped_column(String(32))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

class Lead(Base):
    """Shared lead metadata. AI-extracted; same row visible to all users."""
    __tablename__ = "leads"
    id: Mapped[int] = mapped_column(primary_key=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("items.id"), unique=True, index=True)
    asker_username: Mapped[str] = mapped_column(String(64), index=True)
    what_they_want: Mapped[str] = mapped_column(String(500))
    pain_signals: Mapped[list[str]] = mapped_column(JSON, default=list)
    budget_signal: Mapped[str] = mapped_column(String(16))
    urgency_signal: Mapped[str] = mapped_column(String(16))
    contact_hint: Mapped[str | None] = mapped_column(String(200), default=None)
    score: Mapped[float] = mapped_column(Float, index=True, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

# ─── PERSONAL STATE (user_id required, always) ───

class LeadAssignment(Base):
    """Per-user state on a lead. (lead_id, user_id) is unique."""
    __tablename__ = "lead_assignments"
    id: Mapped[int] = mapped_column(primary_key=True)
    lead_id: Mapped[int] = mapped_column(ForeignKey("leads.id"), index=True)
    user_id: Mapped[str] = mapped_column(String(64), index=True)  # "self" in v1; UUID in v2
    status: Mapped[str] = mapped_column(String(16), default="new")  # new|contacted|won|lost|dismissed
    notes: Mapped[str] = mapped_column(Text, default="")
    contacted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    __table_args__ = (UniqueConstraint("lead_id", "user_id", name="uq_lead_user"),)

class Draft(Base):
    __tablename__ = "drafts"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[str] = mapped_column(String(64), index=True)
    kind: Mapped[str] = mapped_column(String(32))  # "linkedin_post"
    item_ids: Mapped[list[int]] = mapped_column(JSON)
    body: Mapped[str] = mapped_column(Text)
    model: Mapped[str] = mapped_column(String(32))
    variant_index: Mapped[int] = mapped_column(default=0)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

class AICallLog(Base):
    __tablename__ = "ai_call_log"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[str] = mapped_column(String(64), index=True)  # whose action triggered the call
    model: Mapped[str] = mapped_column(String(32), index=True)
    purpose: Mapped[str] = mapped_column(String(32))  # classify | summarize | extract_lead | draft
    tokens_in: Mapped[int]
    tokens_out: Mapped[int]
    duration_ms: Mapped[int]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)

# ─── EXPORTER SYNC LOGS ───

class DocSyncLog(Base):
    __tablename__ = "doc_sync_log"
    id: Mapped[int] = mapped_column(primary_key=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("items.id"), index=True)
    doc_id: Mapped[str] = mapped_column(String(128), index=True)
    week_iso: Mapped[str] = mapped_column(String(8), index=True)
    section_heading: Mapped[str] = mapped_column(String(300))
    written_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

class SheetSyncLog(Base):
    """Per-assignment sync log. Tracks last-known human-owned values for reconciliation."""
    __tablename__ = "sheet_sync_log"
    id: Mapped[int] = mapped_column(primary_key=True)
    assignment_id: Mapped[int] = mapped_column(ForeignKey("lead_assignments.id"), unique=True, index=True)
    sheet_id: Mapped[str] = mapped_column(String(128))
    row_index: Mapped[int]
    last_written_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    last_known_status: Mapped[str] = mapped_column(String(16))
    last_known_notes: Mapped[str] = mapped_column(Text, default="")
```

## The `get_current_user()` discipline

In v1, `backend/app/auth.py`:

```python
async def get_current_user() -> str:
    return "self"  # hardcoded; v2 will read from Supabase JWT
```

Every router that touches personal data takes `user_id: str = Depends(get_current_user)`. Every query for personal data filters by `user_id`. Examples:

```python
# GOOD
stmt = select(Draft).where(Draft.user_id == user_id).order_by(Draft.created_at.desc())

# BAD — works in v1, breaks at v2
stmt = select(Draft).order_by(Draft.created_at.desc())
```

This is the single most important habit. Skip it and v2 becomes a rewrite instead of a migration.

## Indexes worth adding

```sql
CREATE INDEX idx_items_source_created ON items(source, created_utc DESC);
CREATE INDEX idx_classifications_tag_created ON classifications(tag, created_at DESC);
CREATE INDEX idx_assignments_user_status ON lead_assignments(user_id, status);
CREATE INDEX idx_assignments_lead_user ON lead_assignments(lead_id, user_id);
CREATE INDEX idx_drafts_user_created ON drafts(user_id, created_at DESC);
CREATE INDEX idx_ai_log_user_day ON ai_call_log(user_id, created_at DESC);
```

## Sheet reconciliation

Contract: **exporter never overwrites `status` or `notes` columns.** They're owned by the human, in the Sheet, and mirrored back into `lead_assignments`.

Flow per export run, scoped to the current user's assignments:
1. Read the user's assigned rows from the Sheet.
2. Compare each row's `status` / `notes` to `sheet_sync_log.last_known_*`.
3. If different → user edited it directly in Sheet → mirror into `lead_assignments`.
4. Compute desired write: pipeline columns fresh; human columns = current Sheet values.
5. Write. Update `sheet_sync_log`.

v2 note: each user gets their own tab (`Leads — Yourname`) in the same Sheet, so they can't accidentally edit each other's rows. Or two separate Sheets. Decide at v2 time.

## Migrations

Alembic. `alembic init backend/migrations` once. v1 schema can be re-derived ("drop and recreate") while it's churning. Once you have lead notes you'd hate to lose, switch to disciplined migrations.

## v1 → v2 migration outline

See `deployment.md`. Short version: export SQLite to Postgres via `pgloader` or a small Python script, change `DATABASE_URL`, switch `get_current_user()` to read the JWT, enable RLS policies (one per table, filtering by `auth.uid()`).

## Backup (v1)
SQLite + WAL = single-file backup. `cp data.db data.db.$(date +%F).bak`. Weekly cron or manual. Losing this DB means re-paying for AI work + losing your outreach notes.