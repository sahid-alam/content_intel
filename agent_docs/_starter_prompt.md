# How to start with Claude Code

Once you've put your keys in `.env`, run this from the project root:

```bash
claude
```

Then paste the following as your first message:

---

I want you to read `CLAUDE.md` and `agent_docs/build_order.md` first. Don't read the other docs in `agent_docs/` upfront — pull them on demand as each phase needs them.

Here's the operating mode I want for this build:

1. We build in phases. The phases are defined in `agent_docs/build_order.md`. Don't skip ahead.

2. At the start of each phase, before writing code:
   - Read the doc(s) relevant to that phase
   - Show me a 5-10 line plan: files you'll create, files you'll modify, and what the demo at the end of the phase looks like
   - Wait for my "go"

3. While implementing:
   - Pydantic for everything that crosses a boundary
   - Async by default (asyncpraw, httpx, async SQLAlchemy)
   - Test AI prompts on `tests/fixtures/sample_posts.json` before wiring (see `.claude/skills/prompt-fixture-test/SKILL.md`)
   - Never call Gemini 3.1 Pro on raw scraped content — always Flash-Lite first

4. At the end of each phase:
   - Run `/verify` (see `.claude/commands/verify.md`)
   - Tell me the exact commands to demo the phase and what I should see
   - Stop. Don't start the next phase until I say so.

5. Things you should always ask me about, not assume:
   - Adding a new dependency that wasn't in `pyproject.toml`
   - Changing the data model after Phase 4
   - Anything that touches `voice_profile.md`
   - Schema changes that need a real Alembic migration (vs dropping dev DB)

Start with Phase 0. Show me the plan, then wait.

---

Tips while building:

- If Claude Code suggests something that contradicts a doc, point it at the specific doc section. The docs are authoritative.
- If a phase is taking too long, run `/clear` and start a fresh session — re-load just that phase's relevant docs. Long sessions degrade quality.
- After Phase 5 you'll have a tool that's actually useful. Use it for a week before building Phase 6 polish — you'll learn what's actually missing.