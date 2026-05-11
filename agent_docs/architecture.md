# Architecture

## Data flow (end to end)

```
        ┌───────────────────────────────────────────────┐
        │  Scheduler (APScheduler, every 6h by default) │
        └─────────────────────┬─────────────────────────┘
                              ▼
   ┌─────────────────────────────────────────────────────┐
   │   sources/reddit.py        sources/hackernews.py    │
   │   - PRAW + OAuth           - HN Algolia API         │
   │   - configurable subs      - configurable queries   │
   │   - polite rate limiting   - no auth needed         │
   └────────────────────┬───────┴─────────────────────────┘
                        ▼
              ┌────────────────────┐
              │   services/ingest  │   ← dedupe by external_id, hash content
              └─────────┬──────────┘
                        ▼
              ┌────────────────────┐
              │  ai/classifier     │   ← Gemini 2.5 Flash-Lite (cheap, fast)
              │  Tag: pain, lead,  │     bulk pass: 1 call per item, structured output
              │  trend, signal,    │
              │  noise             │
              └─────────┬──────────┘
                        ▼ (only items tagged pain/lead/trend continue)
              ┌────────────────────┐
              │  ai/summarizer     │   ← Flash-Lite again, cached by content hash
              │  3-bullet summary  │
              └─────────┬──────────┘
                        ▼
                ┌──────────────┐
                │   SQLite     │   ← canonical store, drives all UI reads
                └──────┬───────┘
                       ▼
       ┌───────────────────────────────────────┐
       │            FastAPI routers            │
       │  /feed   /leads   /drafts   /export   │
       └───────────────────┬───────────────────┘
                           ▼
                    React dashboard
                    (on demand: /drafts/{id}/generate
                     fires Gemini 3.1 Pro)
```

## Why each layer exists

**Sources are isolated, never call AI directly.** `reddit.py` and `hackernews.py` only fetch and normalize to a common `RawItem` shape. Mixing scraping with AI logic makes both harder to test and rate-limit. If a source breaks, the rest of the pipeline keeps running.

**Ingest is the dedupe boundary.** Same post can appear in multiple sub-queries. Same HN story can show up in "top" and "by_date." Ingest is where we hash, look up by `external_id`, and skip if seen. This is also where we attach a `content_hash` so AI outputs can be cached.

**Classifier runs on everything; the expensive models do not.** The classifier is the single most important cost control. It runs Flash-Lite once per new item with a structured-output schema returning `{tag, confidence, reason}`. Items tagged `noise` are stored but never sent to a more expensive model. This is the difference between $5/month and $200/month at any meaningful volume.

**Summarizer is cache-keyed.** Content rarely changes after posting. Once we have a summary for `content_hash X`, never re-summarize. Cached summaries are reused for both the feed view and as input to draft generation.

**Generator (Gemini 3.1 Pro) only fires on user action.** No background "generate drafts for everything." Drafts are generated when the user clicks the button on a specific item. This keeps Pro-tier spend correlated with actual usage, not background crawling.

## Why FastAPI, not Flask
- **Async-native.** When the user clicks "Sync now," we want to fan out: Reddit subs in parallel, HN queries in parallel, classifier batches in parallel. Flask makes this awkward.
- **Pydantic-first.** Models defined once, used as request schema, response schema, and (with ORM mode) DB serialization.
- **Auto-docs.** `/docs` gives Swagger UI for free — useful when you want to wire this into n8n or Make later.

## Why SQLite, not Postgres
- Single-user, local-first tool. Postgres adds a daemon, port, password, and zero capability you'll use.
- WAL mode handles the concurrency we'll see (one scheduler writer + one API reader).
- If the tool ever gets multi-user, the swap to Postgres is a 5-line `DATABASE_URL` change since SQLAlchemy abstracts it.

## What's deliberately not in v1
- Auth (single-user local tool — adding auth is busywork)
- Vector search / embeddings (keyword + tag filtering is enough for the volumes we'll see; revisit if the dataset grows past ~50k items)
- LinkedIn API integration (manual copy-paste is fine; LinkedIn API approval is a months-long process not worth it for v1)
- Hosted deployment (this runs on your laptop; if you want it always-on later, a $5 Hetzner box + systemd is one afternoon)