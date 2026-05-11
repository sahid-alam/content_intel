# Build Order

Don't build top-to-bottom. Build in vertical slices that each produce a working demo, so you catch integration problems early. Each phase below is a working state.

## Phase 0 — Skeleton (30 min)
- `pyproject.toml` with deps via `uv`
- FastAPI app boots, `/health` returns `{"status":"ok"}`
- SQLAlchemy engine + a single `Item` model + `alembic init`
- Vite + React + Tailwind initialized; one page that fetches `/health` and shows it
- `.env.example` written; `.env` gitignored
- Single `make dev` (or two-pane terminal) that runs both

**Demo:** open localhost:5173, see "backend ok".

## Phase 1 — One source, no AI (1-2 hours)
- `sources/hackernews.py` — Algolia client, `fetch_recent_stories(since)`
- `services/ingest.py` — dedupe by external_id, write to `items` table
- `routers/feed.py` — `GET /feed` returns paginated items
- Frontend `/` route — shows the items in a basic list
- `POST /sync` endpoint that triggers an HN fetch synchronously

**Demo:** click "Sync now" → see real HN stories appear.

Do HN before Reddit. HN needs no auth, so you can't get blocked on credentials; if Phase 1 is broken, the bug is in your code, not Reddit's permissions.

## Phase 2 — Add Reddit (1 hour)
- `sources/reddit.py` — asyncpraw client, `fetch_subreddit(name, sort)`
- Extend `/sync` to fan out across HN + configured subreddits in parallel (asyncio.gather)
- Source filter on the feed view

**Demo:** sync now pulls from both, source badge visible in UI.

## Phase 3 — Classifier (1-2 hours)
- `ai/classifier.py` with Gemini 2.5 Flash-Lite + structured output
- Wire into ingest: classify after insert, store in `classifications` table
- `ai_call_log` writes
- Tag pill on feed cards; tag filter in left rail
- Daily-cap check; banner in UI when hit
- A `tests/fixtures/sample_posts.json` with 10 hand-picked posts and a `pytest` test asserting expected tags

**Demo:** noise items dim, lead/pain items prominent. Spend pill shows real numbers.

## Phase 4 — Summarizer + Lead extractor (1-2 hours)
- `ai/summarizer.py` keyed by content_hash
- `ai/lead_extractor.py` for `lead`-tagged items only
- `/leads` route + table view
- CSV export endpoint

**Demo:** open `/leads`, see real warm leads from today, export to CSV.

## Phase 5 — Drafts via Gemini 3.1 Pro (1-2 hours)
- `ai/generator.py` — `generate_linkedin_draft`
- `voice_profile.md` template (you fill it in with 3-5 of your real LinkedIn posts)
- `/drafts/new` UI: pick items, click generate, edit, save
- Saved drafts list at `/drafts`

**Demo:** generate a post from today's top trend item; quality should be high enough to publish with light edits.

## Phase 6 — Scheduler + polish (1 hour)
- APScheduler job: sync every 6 hours
- Lead-magnet outline generator (second Pro endpoint)
- Settings page: edit subreddit list, daily caps, voice profile inline
- Backup script: `scripts/backup.sh` copies `data.db` with date suffix

**Demo:** close laptop overnight. Open in the morning. Fresh feed, classified, ready.

## What's explicitly punted to v2
- Embeddings + clustering for the lead-magnet feature (v1 uses keyword overlap, which is good enough)
- Multiple voice profiles (v1: one profile, edit in place)
- Topic-trend graphs (v1: counts in the dashboard header)
- Slack/Discord notifications on high-score leads
- Auto-DM the asker (you should never auto-DM. Manual outreach is the moat.)

## Total estimate
~8 focused hours for a production-quality v1. Realistic calendar time depends on how often you stop to use the thing. Don't try to do this in one sitting; ship phase 1 in one session, sleep on it, see if the data is what you expected before building on top.