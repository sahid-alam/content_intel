---
name: prompt-fixture-test
description: Test a Gemini prompt against the sample post fixtures before wiring it into the pipeline. Use this whenever you add or change a prompt in backend/app/ai/prompts/.
---

# Prompt fixture test

Always run a new or changed AI prompt against `tests/fixtures/sample_posts.json` before wiring it into the pipeline. The fixtures are 10 hand-picked posts with expected classifications/summaries.

## Steps

1. Open `tests/fixtures/sample_posts.json` and read the posts + expected outputs.
2. Write a one-off script under `tests/scripts/try_prompt.py` that:
   - Loads the fixture
   - Calls the prompt directly (don't go through the full ingest pipeline)
   - Prints expected vs actual side-by-side
3. Run it: `uv run python tests/scripts/try_prompt.py`
4. If results are off:
   - Adjust the prompt in `backend/app/ai/prompts/{name}.py`
   - Do **not** widen the schema to accept bad outputs
   - Do **not** raise temperature to "fix" determinism issues — lower it
5. Once it's passing on fixtures, write a real pytest case in `tests/test_ai_{name}.py` that asserts the same thing, mocking the actual Gemini call with a recorded response.

## Why this exists

- AI prompts are easy to break in subtle ways. Without fixtures, you don't notice.
- Doing a one-off script first is faster than iterating through the full pipeline.
- The recorded mock test makes regressions catchable in CI without burning tokens.

## What to never do

- Skip the fixture step "because the prompt is simple"
- Test by clicking "Sync now" in the UI (slow feedback, real tokens, hard to diff)
- Accept output that doesn't match the schema strictly — fix the prompt