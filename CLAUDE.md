# Content Intelligence Pipeline

## Why
A standalone tool that turns raw Reddit + Hacker News activity into three deliverables for a Gen-AI dev agency:
1. LinkedIn post drafts grounded in real, current discussions (no hallucinated trends)
2. A warm-lead list — people who are publicly asking for help building things we can build
3. Lead-magnet outlines structured around clusters of pain points we can pitch against

The goal is signal extraction, not data hoarding. Quality of synthesis > volume scraped.

## What
Local-first web app. Backend is a FastAPI service that pulls from Reddit + HN, runs items through a two-tier Gemini pipeline, and stores everything in SQLite. Frontend is a React + Vite dashboard for browsing, filtering, and one-click exporting (LinkedIn drafts, CSV lead list, JSON dataset).

Stack:
- Backend: Python 3.11+, FastAPI, SQLAlchemy + SQLite, PRAW (Reddit), httpx (HN Algolia), google-genai (Gemini), APScheduler
- Frontend: React 18 + Vite, TanStack Query, Tailwind CSS, shadcn/ui
- Models: Gemini 3.1 Pro (analysis/generation) + Gemini 2.5 Flash-Lite (bulk classification)

## How
Read these in order before doing real work. Do **not** read all of them upfront — pull the one relevant to the task.

- `agent_docs/architecture.md` — module layout, data flow, why each piece exists
- `agent_docs/data_sources.md` — Reddit (PRAW + OAuth) and HN (Algolia) integration details, rate limit handling
- `agent_docs/ai_pipeline.md` — the two-tier Gemini pipeline: prompts, when each model fires, cost guardrails
- `agent_docs/data_model.md` — SQLite schema, dedupe strategy, what gets cached
- `agent_docs/frontend.md` — page layout, components, state management
- `agent_docs/build_order.md` — recommended order to build features (read this first if scaffolding from scratch)

## Workflow rules
- **Never commit `.env` or any API keys.** `.env.example` is the only file with credentials in it.
- **Use `uv` for Python deps**, not pip directly. Faster, deterministic. `uv add <pkg>` to add, `uv sync` to install.
- **Async by default in the backend.** Reddit + HN + Gemini are all I/O-bound; sync code will bottleneck.
- **Pydantic models for everything that crosses a boundary** (API request/response, DB row, AI tool input). No raw dicts in business logic.
- **Cost guardrail: never call Gemini 3.1 Pro on raw scraped content.** Always run Flash-Lite filtering first. See `agent_docs/ai_pipeline.md`.
- **Test the AI prompts on small fixtures before wiring them in.** `tests/fixtures/sample_posts.json` has 10 hand-picked posts.
- **Verify before pushing**: `uv run ruff check . && uv run pytest -q && cd frontend && npm run lint && npm run typecheck`

## Project layout
```
content_intel/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app
│   │   ├── config.py            # settings via pydantic-settings
│   │   ├── db.py                # SQLAlchemy engine + session
│   │   ├── models.py            # ORM models
│   │   ├── schemas.py           # Pydantic API schemas
│   │   ├── sources/             # reddit.py, hackernews.py
│   │   ├── ai/                  # classifier.py, summarizer.py, generator.py, prompts/
│   │   ├── services/            # ingest.py, lead_scorer.py, exporter.py
│   │   ├── routers/             # feed.py, leads.py, drafts.py, export.py
│   │   └── scheduler.py         # APScheduler jobs
│   └── tests/
├── frontend/
│   ├── src/
│   │   ├── routes/              # Feed, Leads, Drafts, Settings
│   │   ├── components/
│   │   ├── lib/api.ts
│   │   └── App.tsx
│   └── ...
├── agent_docs/                  # progressive-disclosure docs (you are reading these on demand)
├── .claude/
│   ├── skills/                  # reusable skills, see .claude/skills/README.md
│   └── commands/                # slash commands
├── .env.example
├── pyproject.toml
└── README.md
```

## What "done" looks like for v1
- `uv run uvicorn app.main:app --reload` starts the backend
- `npm run dev` in `frontend/` starts the dashboard at `localhost:5173`
- Hitting "Sync now" on the dashboard pulls last 24h from r/SaaS, r/entrepreneur, r/AI_Agents, r/automation, and HN, runs the AI pipeline, and surfaces:
  - Feed view with score/source/topic filters
  - Lead list filtered to "asking for help" posts, with username + question summary + link, CSV export
  - Drafts view: pick any item → generate a LinkedIn post in my voice → copy
- All state survives a restart (SQLite persists; AI outputs cached by content hash)