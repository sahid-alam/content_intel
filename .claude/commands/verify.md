---
description: Run all checks before committing — lint, typecheck, tests, frontend build
---

Run, in order, and report any failures clearly:

1. `uv run ruff check . --fix`
2. `uv run mypy backend/app`
3. `uv run pytest -q`
4. `cd frontend && npm run lint`
5. `cd frontend && npm run typecheck`
6. `cd frontend && npm run build`

If any step fails, **stop and fix it**. Don't move on. Don't commit.

If all pass, summarize what changed in 3-5 bullets and propose a commit message in Conventional Commits format. Don't actually commit — let me review the message first.