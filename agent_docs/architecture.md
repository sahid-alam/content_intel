# Architecture

## Two deployments, one source of truth

```
                                    ┌─────────────────────────────────┐
                                    │  Scheduler (APScheduler, 6h)    │
                                    └──────────────┬──────────────────┘
                                                   ▼
                            ┌────────────────────────────────────────┐
                            │  PYTHON SERVICE                        │
                            │  v1: laptop · v2: Fly.io/Hetzner       │
                            │                                        │
                            │  ┌──────────────────────────────────┐  │
                            │  │ sources/  ingest/  ai/  exporters│  │
                            │  └──────────────────────────────────┘  │
                            │  ┌──────────────────────────────────┐  │
                            │  │ FastAPI: /feed /leads /drafts    │  │
                            │  │         /sync /export            │  │
                            │  └──────────────────────────────────┘  │
                            └────────────────┬───────────────────────┘
                                             ▼
                                    ┌────────────────┐
                                    │  Database      │
                                    │  v1: SQLite    │
                                    │  v2: Supabase  │
                                    └────────┬───────┘
                                             ▲
                                             │ reads/writes via HTTP (v1)
                                             │ or Supabase client (v2)
                                             │
                            ┌────────────────┴───────────────────────┐
                            │  NEXT.JS DASHBOARD                     │
                            │  v1: localhost  ·  v2: Vercel          │
                            │                                        │
                            │  Server Components (Feed/Leads/Drafts) │
                            │  Server Actions (mutations)            │
                            │  Auth (none v1; Supabase Auth v2)      │
                            └────────────────────────────────────────┘

                            (Parallel path, same source data:)
                                             │
                                             ▼
                                  ┌─────────────────────┐
                                  │  Google Doc + Sheet │
                                  │  (curated material) │
                                  └──────────┬──────────┘
                                             ▼
                                  ┌─────────────────────┐
                                  │   Cowork Project    │
                                  │   (per-user voice)  │
                                  └─────────────────────┘
```

## Why this split

**Vercel is for HTTP, not for background workers.** Vercel serverless functions die at 60s. Your sync runs 30-90s. So the dashboard goes on Vercel, the pipeline doesn't.

**The dashboard never talks to the pipeline directly.** Dashboard reads/writes via the API (v1) or via Supabase (v2). Pipeline writes to the DB on its own schedule. They communicate only through stored state. Either can be down without breaking the other.

**Exporters are a layer, not a step.** They read from the DB, not from the ingest pipeline. So a failing classifier doesn't poison the Doc; a failing Drive sync doesn't block the classifier.

## Why each layer exists

**Sources** (`reddit.py`, `hackernews.py`) — normalize Reddit submissions + HN items to a single `RawItem` shape. Isolated so a broken source doesn't take down the rest.

**Ingest** (`services/ingest.py`) — dedupe boundary. Hash content; lookup `external_id`; skip if seen. Attaches `content_hash` so AI outputs cache forever.

**Classifier** (`ai/classifier.py`) — Flash-Lite, structured output (`pain` / `lead` / `trend` / `signal` / `noise`). The cost gate: noise stops here; everything else advances.

**Summarizer** (`ai/summarizer.py`) — Flash-Lite, cached by `content_hash`. One summary per piece of content, reused by feed view, drafter, and Doc exporter.

**Lead extractor** (`ai/lead_extractor.py`) — Flash-Lite, structured. Runs only on lead-tagged items. Feeds the leads table.

**Drafter** (`ai/drafter.py`) — Gemma 4 31B, 3 variants in parallel. Fires only on user action (clicking "Draft this"). Free, fast, good enough for triage.

**Exporters** (`exporters/`) — push from DB to Google Drive. Append-only on the Doc; upsert on the Sheet (preserving human-owned columns).

**FastAPI** — thin wrapper around the DB for the dashboard. Goes away at v2 (Next.js talks to Supabase directly).

## Why Next.js (and not Vite, Flask, etc.)

- **One framework, one deployment for the dashboard.** UI and any BFF logic live together.
- **Server Components fetch data without an API layer when we move to v2.** Less code, less to maintain.
- **Vercel free tier is genuinely generous** for the dashboard's traffic (you + 1 partner).
- **Server Actions handle mutations** cleanly without manual fetch+revalidate dance.

We use it for the **dashboard only**. Pipeline stays Python because Python has the libraries (asyncpraw, google-genai, APScheduler) and runs as a long-lived process, not as request-response.

## Why Cowork is a separate surface, not a feature

You could build "premium drafts" in the dashboard with a different model. We don't because:
1. Cowork has persistent memory, voice files as Project knowledge, and conversational iteration — building that in-house is months of work
2. It runs on your existing Claude subscription, not the Gemini API
3. The Doc/Sheet are a natural interface — readable by Cowork, also useful for you to skim manually

The dashboard handles speed; Cowork handles depth. Different jobs, different tools.

## What's deliberately out of scope

- LinkedIn API integration (partner approval is months; copy-paste works)
- Real-time websockets (polling on focus is enough at this volume)
- Embeddings (v1 keyword overlap is fine; revisit at ~50k items)
- Pro-tier Gemini calls (Cowork covers premium synthesis)