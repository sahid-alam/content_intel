# Content Intelligence Pipeline

Local-first tool that pulls Reddit + Hacker News, runs items through a two-tier Gemini pipeline, and produces:
- A filterable feed of classified discussions (pain / lead / trend / signal / noise)
- A warm-lead list — people publicly asking for help with builds you can do
- One-click LinkedIn post drafts grounded in real, current discussions
- Lead-magnet outlines structured around recurring pain points

## Why this exists

If you run a Gen-AI dev agency, three things you do every week are: write LinkedIn content that gets engagement, find clients who actively want what you sell, and turn observed pain into pitch material. All three live in the same source data — the public discussions where your buyers complain. This tool makes that loop systematic.

## Stack

- **Backend:** FastAPI, async SQLAlchemy + SQLite, asyncpraw (Reddit), httpx (HN Algolia), google-genai
- **Frontend:** Vite + React + TypeScript + Tailwind + TanStack Query
- **Models:** Gemini 2.5 Flash-Lite (bulk classification + summarization) + Gemini 3.1 Pro (drafts + outlines)

## Prerequisites

- Python 3.11+
- Node 20+
- `uv` ([install](https://docs.astral.sh/uv/getting-started/installation/))
- Google AI Pro subscription (for the elevated Gemini API quota — set up once at https://aistudio.google.com/app/apikey)
- Reddit account (free; takes 2 min to register an app at https://www.reddit.com/prefs/apps)

## Setup

```bash
# Clone, then:
cp .env.example .env   # fill in GEMINI_API_KEY, REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, REDDIT_USER_AGENT

uv sync                # install Python deps
uv run alembic upgrade head   # create the DB

cd frontend
npm install
cd ..
```

## Run

In one terminal:
```bash
uv run uvicorn backend.app.main:app --reload
```

In another:
```bash
cd frontend && npm run dev
```

Open http://localhost:5173 and click "Sync now."

## Building it

This repo was designed to be built with [Claude Code](https://claude.com/claude-code) following `agent_docs/build_order.md`. Start with:

```bash
claude
> /build-phase 0
```

…and walk through phases 0-6. Each phase is a working demo state.

## Layout

See `CLAUDE.md` for the project layout and `agent_docs/` for detailed module docs.