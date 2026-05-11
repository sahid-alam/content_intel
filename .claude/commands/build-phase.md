---
description: Implement a specific build phase from agent_docs/build_order.md. Argument: phase number (e.g. /build-phase 2)
---

Read `agent_docs/build_order.md` and find Phase $ARGUMENTS.

Before writing any code:
1. Read the relevant doc(s) the phase touches (e.g. `agent_docs/data_sources.md` for Phase 1/2, `agent_docs/ai_pipeline.md` for Phases 3-5).
2. Show me a brief plan: files you'll create, files you'll modify, the order, and the demo that proves it works.
3. Wait for my "go" before implementing.

Once approved, implement the phase end-to-end. After implementation:
- Run `/verify`
- Tell me how to demo it (the exact commands and what I should see)
- Do **not** start the next phase. Wait for me.