# Content Intelligence Pipeline

Local tool that pulls Reddit + Hacker News, classifies discussions via Gemini, and produces:
- A filterable feed of classified posts (pain / lead / trend / signal / noise)
- A warm-lead list — people publicly asking for help with builds you can do
- One-click LinkedIn post drafts via Gemma 4 31B
- Premium drafts + lead magnet outlines via Cowork (Claude subscription)

## Architecture

Two deployments, one source of truth:
- **Pipeline (Python)** — scrapes, classifies, exports to Google Drive. v1: laptop. v2: Fly.io/Hetzner.
- **Dashboard (Next.js)** — Feed, Leads, Drafts UI. v1: localhost. v2: Vercel.

See `agent_docs/architecture.md` for the diagram.

## Prerequisites

- Python 3.11+, `uv` ([install](https://docs.astral.sh/uv/getting-started/installation/))
- Node 20+, pnpm
- Google AI Pro subscription
- Reddit account
- Google account for Drive integration

## Setup (v1, local)

```bash
# Clone, then:
cp .env.example .env   # fill in GEMINI_API_KEY, REDDIT_*, GOOGLE_DRIVE_FOLDER_ID

# Backend
uv sync
uv run alembic upgrade head

# Frontend
cd dashboard
pnpm install
cd ..
```

## Run

Terminal 1:
```bash
uv run uvicorn backend.app.main:app --reload
```

Terminal 2:
```bash
cd dashboard && pnpm dev
```

Open http://localhost:3000 → click "Sync now."

## Building it

This repo is designed to be built phase-by-phase with [Claude Code](https://claude.com/claude-code) following `agent_docs/build_order.md`. Start with:

```bash
claude
> /build-phase 0
```

…and walk through phases 0-7 for v1. v2 (deployment) is phases 8-10, only after you've used v1 for 2-4 weeks.

## Layout

- `backend/` — Python pipeline + FastAPI
- `dashboard/` — Next.js App Router
- `agent_docs/` — module docs (Claude reads on demand)
- `.claude/` — skills + slash commands
- `CLAUDE.md` — project context entry point

See `CLAUDE.md` for the full layout and conventions.