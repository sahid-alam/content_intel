# Deployment (v2)

Don't read this until v1 has been working for 2-4 weeks. Premature optimization is the v2 risk.

## What v2 changes

- **Database:** SQLite local file → Supabase Postgres
- **Auth:** none → Supabase Auth (you + partner, 2 users)
- **Pipeline host:** your laptop → Fly.io free tier (or $4/mo Hetzner)
- **Dashboard host:** localhost → Vercel free Hobby tier
- **Voice profile storage:** local file → Supabase Storage, one per user

## What v2 doesn't change

- Pipeline code (sources, AI, exporters, services, scheduler)
- Dashboard pages and components (only the data-fetching layer changes)
- Models (Flash-Lite + Gemma)
- Cowork workflow

The whole point of the v1 discipline (`user_id` threaded everywhere, hardcoded `"self"`) was to make v2 mechanical, not architectural.

## Cost

- Vercel Hobby: $0
- Supabase Free: $0 (500MB DB, 2GB egress, **pauses after 7 days inactive**)
- Pipeline host: $0 (Fly.io free) or ~$4/mo (Hetzner CX11)

Worst case ~$5/month. Best case $0.

The Supabase free-tier pause matters: if neither user opens the dashboard for 7 days, the project sleeps. First request after wakes it (10-30s). Annoying but acceptable for an internal tool. Pay the $25 Pro plan only if this bites you regularly.

## Migration outline (Phase 8-10 from `build_order.md`)

### Phase 8 — DB migration

1. Spin up a Supabase project. Note the connection string and the anon + service-role keys.
2. Run Alembic migrations against Supabase: `DATABASE_URL=postgresql+asyncpg://... uv run alembic upgrade head`. Schema appears empty in Supabase Studio.
3. Migrate data with a small Python script (`scripts/migrate_to_supabase.py`):
   - Read each table from SQLite via SQLAlchemy
   - Write to Postgres via SQLAlchemy with the new `DATABASE_URL`
   - Special handling: convert string `user_id = "self"` to the actual Supabase user UUID you just created for yourself
4. Verify row counts match per table.
5. Swap `.env`: `DATABASE_URL` points at Supabase.

### Phase 9 — Auth + RLS

1. Create accounts in Supabase Auth (you + partner). Use email/password or magic link.
2. RLS policies, one per personal table. Pattern:
   ```sql
   -- lead_assignments
   alter table lead_assignments enable row level security;

   create policy "users see their own assignments"
     on lead_assignments for select
     using (user_id = auth.uid()::text);

   create policy "users manage their own assignments"
     on lead_assignments for all
     using (user_id = auth.uid()::text)
     with check (user_id = auth.uid()::text);
   ```
   Same shape for `drafts`, `ai_call_log`, `sheet_sync_log`.
3. Shared tables (`items`, `classifications`, `summaries`, `leads`) get a permissive read policy for authenticated users:
   ```sql
   create policy "authenticated users read curated content"
     on items for select
     to authenticated using (true);
   ```
   Writes restricted to the service role (used by the pipeline).
4. `backend/app/auth.py` — `get_current_user()` now reads the JWT from the `Authorization` header (FastAPI dependency that validates against the Supabase JWKS).
5. Pipeline runs with the **service role key**, bypassing RLS. Dashboard uses the user's JWT, RLS enforces isolation.

### Phase 10 — Deploy

**Pipeline (Fly.io free tier):**
- `Dockerfile` based on `python:3.11-slim`, COPY backend, `uv sync --frozen`, CMD runs uvicorn + apscheduler
- `fly.toml` with one machine, 256MB RAM
- Secrets via `fly secrets set GEMINI_API_KEY=... DATABASE_URL=... etc`
- Volume for `.gcp/` (OAuth tokens) — small, persistent
- Health check on `/health`

**Dashboard (Vercel):**
- Push `dashboard/` to GitHub, connect Vercel
- Environment variables: `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`, `BACKEND_URL` (your Fly app URL)
- Vercel handles HTTPS, CDN, deploys on push to main

**Frontend talks to backend or Supabase?**
Decision: in v2, **Server Components in Next.js read directly from Supabase** using `@supabase/ssr`. Writes also go directly to Supabase (RLS enforces auth). The FastAPI surface remains only for things Supabase can't do: triggering a sync, triggering an export, generating drafts (AI calls). Dashboard calls those endpoints on the Fly app with the user's JWT.

This is the cleanest division: data layer = Supabase direct; action layer = FastAPI. Less code than routing everything through FastAPI.

## Things to verify before flipping the switch

- Backup SQLite first: `cp data.db data.pre-v2.db`
- Run migration script in dry-run mode if you build one
- Test login on a clean browser before announcing it to your partner
- Verify the pipeline can write through RLS using the service role
- Verify the dashboard sees your data and your partner's data is isolated

## When to revisit

- **Supabase paused too often** → upgrade to Pro ($25/mo) or move to Neon (also free, doesn't pause)
- **Pipeline outgrows Fly free** → upgrade Fly or move to Hetzner
- **3rd user joins** → still fine on free tiers; just create another Supabase Auth user
- **5+ users** → start thinking about a real team management UI, multi-tenant data partitioning, and probably a paid Supabase plan