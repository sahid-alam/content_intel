# Build Order

Vertical slices. Each phase is a working state. Don't skip ahead.

## v1 — Local, single user (target: 8-12 focused hours)

### Phase 0 — Skeleton (1 hour)
- `backend/`: `pyproject.toml`, FastAPI app, `/health` endpoint, async SQLAlchemy, single `Item` model, alembic init
- `dashboard/`: `pnpm create next-app@latest dashboard --typescript --tailwind --app`, then `pnpm dlx shadcn@latest init`
- `dashboard/lib/api.ts` with typed `getHealth()` calling `http://localhost:8000/health`
- `dashboard/app/page.tsx` is a Server Component that calls `getHealth()` and renders the result
- `dashboard/lib/user.ts` with `getCurrentUser()` returning `{ id: "self" }`
- `.env.example` written, `.env` gitignored

**Demo:** `uv run uvicorn ...` + `pnpm dev` → open localhost:3000, see "backend ok".

### Phase 1 — HN source, no AI (1-2 hours)
- `sources/hackernews.py` — Algolia client
- `services/ingest.py` — dedupe by external_id, insert items
- `routers/feed.py` — `GET /feed` returns paginated items
- `routers/sync.py` — `POST /sync` triggers HN fetch
- `dashboard/app/page.tsx` — server component fetches feed and renders cards
- Server Action for "Sync now" button

**Demo:** click Sync now → real HN stories appear.

Start HN before Reddit: no auth means no credential debugging.

### Phase 2 — Add Reddit (1 hour)
- `sources/reddit.py` — asyncpraw client
- `/sync` fans out across HN + configured subs via `asyncio.gather`
- Source filter via URL search params on Feed

**Demo:** sync pulls both sources; source badge visible.

### Phase 3 — Classifier (1-2 hours)
- `ai/classifier.py` — Gemini 3.1 Flash-Lite, structured output
- Wire into ingest: classify after insert
- `ai_call_log` writes (with `user_id`)
- Tag pills on cards; tag filter
- Daily-cap check; banner when hit
- `tests/fixtures/sample_posts.json` (10 hand-picked) + pytest test

**Demo:** noise items dim, lead/pain items prominent. "Today's usage" pill shows real numbers.

### Phase 4 — Summarizer + lead extractor + leads UI (2 hours)
- `ai/summarizer.py` cache-keyed by content_hash
- `ai/lead_extractor.py` for lead-tagged items only
- `services/lead_scorer.py` — rule-based score
- **`LeadAssignment` auto-created** for `user_id = "self"` whenever a new lead lands (in v1; v2 will be explicit "claim")
- `dashboard/app/leads/page.tsx` — table with inline `status` dropdown and `notes` editor
- Server Action `updateAssignment(leadId, patch)`

**Demo:** open /leads, see warm leads, mark one as "contacted" — refresh, status persists.

### Phase 5 — Google Drive exporters (2-3 hours)
- `exporters/drive_client.py` — OAuth (Desktop app credentials)
- `exporters/gdocs.py` — append-only weekly Doc per `cowork_workflow.md`
- `exporters/gsheets.py` — upsert with column-ownership contract
- `routers/export.py` — `POST /export/now`
- Sync log tables wired up
- Settings page exposes Doc/Sheet URLs

**Demo:** trigger export → open Doc + Sheet in Drive → edit `status` in Sheet → re-export → confirm edit survived and mirrored back to DB.

### Phase 6 — Drafter (Gemma) + Drafts UI (1-2 hours)
- `ai/drafter.py` — Gemma 4 31B, 3 variants in parallel via `asyncio.gather`
- `voice_profile.md` template (you fill in 3-5 real posts)
- `routers/drafts.py` — `POST /drafts/generate`, `POST /drafts` (save)
- `dashboard/app/drafts/new/page.tsx` — pick items, generate, 3 tabs, save best
- `dashboard/app/drafts/page.tsx` — saved drafts grid

**Demo:** pick a top trend item, click "Draft this," see 3 variants in seconds, save and copy.

### Phase 7 — Scheduler + Cowork Project setup (1 hour)
- APScheduler job: sync every 6h, export immediately after
- Cowork Project setup walkthrough (see `cowork_workflow.md`) — you do this, not Claude Code
- Backup script `scripts/backup.sh`
- README pass — verify fresh-clone setup works

**Demo:** close laptop overnight. Open in morning. Fresh feed, fresh exports. Cowork Project still has its memory.

## v2 — Deployed, two users (target: 1-2 focused days, after 2-4 weeks of v1 use)

Don't start until v1 has proven itself. Then see `agent_docs/deployment.md` for the full path. Brief outline:

### Phase 8 — Schema migration
- Add Alembic migration: items/classifications/summaries/leads stay same; rest already have `user_id`
- Migrate SQLite → Supabase Postgres via small Python script or `pgloader`

### Phase 9 — Auth + RLS
- Supabase Auth (email/password or magic link)
- RLS policies on personal tables filtering by `auth.uid()`
- `backend/app/auth.py` → reads JWT instead of returning "self"
- `dashboard/lib/user.ts` → reads Supabase session
- `@supabase/ssr` middleware in Next.js for protecting routes

### Phase 10 — Deploy
- Pipeline to Fly.io (free tier) or Hetzner ($4/mo) — Docker + systemd
- Next.js to Vercel (free Hobby)
- Domain (optional)
- Supabase Storage for `voice_profile.md` per user (one file per user_id)

## What's out of scope across v1 and v2

- LinkedIn API integration (months of partner approval, copy-paste is fine)
- Real-time websockets (polling on focus is enough)
- Embeddings / clustering (Cowork does this conversationally)
- Pro-tier Gemini (Cowork covers it)
- Slack/Discord notifications (could add later, not core)
- Auto-DM (don't — manual outreach is the moat)