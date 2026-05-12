# How to start with Claude Code

Once you've put your keys in `.env` and created the Drive folder, run this from the project root:

```bash
claude
```

Paste this as your first message:

---

Read `CLAUDE.md` and `agent_docs/build_order.md` first. Don't read the other docs upfront — pull them on demand per phase.

Operating mode:

1. We build in phases per `agent_docs/build_order.md`. v1 is phases 0-7 (local SQLite, single user). v2 (phases 8-10) is deployment and won't start until I explicitly green-light it after 2-4 weeks of v1 use.

2. Each phase, before writing code:
   - Read the doc(s) relevant to the phase
   - Show me a 5-10 line plan (files, demo)
   - Wait for my "go"

3. While implementing:
   - Pydantic at Python boundaries, Zod at TypeScript boundaries
   - Python async by default (asyncpraw, httpx, async SQLAlchemy)
   - Next.js Server Components by default; `'use client'` only when needed
   - **`user_id` threaded through every personal query, hardcoded to `"self"` in v1.** This is non-negotiable. See `agent_docs/data_model.md`.
   - No Gemini Pro calls anywhere. Flash-Lite + Gemma only. If you think a feature needs Pro, stop and ask.
   - Sheet `status` and `notes` columns are human-owned. Exporter never overwrites. See `data_model.md` reconciliation flow.
   - Test AI prompts on `tests/fixtures/sample_posts.json` first. See `.claude/skills/prompt-fixture-test/SKILL.md`.

4. End of each phase:
   - Run `/verify`
   - Tell me the exact demo commands and what I should see
   - Stop. Wait for me.

5. Always ask before:
   - Adding a dep not in `pyproject.toml` or `dashboard/package.json`
   - Schema changes after Phase 4
   - Anything touching `voice_profile.md`
   - Anything that would require a real Alembic migration (vs drop dev DB)
   - Drive API scope changes after Phase 5

Start with Phase 0. Show me the plan, then wait.

---

## Tips while building

- Docs are authoritative. If Claude Code contradicts a doc, point at the section.
- If a phase drags, `/clear` and reload only that phase's relevant docs. Long sessions degrade quality.
- After Phase 5 (exporters), open the Doc in Drive yourself before building the drafter. Confirm the section format is what you actually want.
- After Phase 6 (drafter), use the dashboard drafter for one full week before judging if you need the Cowork path. They serve different jobs.

## Manual steps (Phase 7)

Cowork Project setup is yours, not Claude Code's:

1. In Cowork, create a Project named "Content Intel — Yourname"
2. Upload `voice_profile.md` and `agency_context.md` as Project knowledge
3. Paste the "Project instructions" block from `agent_docs/cowork_workflow.md`
4. Enable Google Drive connector for the Project
5. Test with the prompts in the "Operating playbook" section