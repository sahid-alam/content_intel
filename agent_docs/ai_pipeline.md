# AI Pipeline

## Model strategy (all free, all on your Google AI Pro quota)

| Step | Model | Why |
|---|---|---|
| Classification | `gemini-3.1-flash-lite` | 15 RPM / 500 RPD on your account. Structured output reliable. |
| Summarization | `gemini-3.1-flash-lite` | Same model, same quota. Cached forever by content_hash. |
| Lead extraction | `gemini-3.1-flash-lite` | Same. Only fires on lead-tagged items. |
| Dashboard drafts | `gemma-4-31b` | 15 RPM / 1,500 RPD, unlimited TPM. Free. Good enough for fast triage drafts. |
| Premium drafts + lead magnets | Cowork (Claude subscription) | Voice fidelity + iteration. Not in this codebase. |

**Hard rule from `CLAUDE.md`: no `gemini-3.1-pro` or `gemini-2.5-pro` calls anywhere.** Pro-tier work moves to Cowork, which runs on your Claude subscription, not the Gemini API. This keeps the Python project entirely inside free quotas.

## SDK

Use the unified `google-genai` SDK (the new one), not the older `google-generativeai`.

```python
from google import genai
from google.genai import types

client = genai.Client(api_key=settings.gemini_api_key)
```

Same client for Gemini and Gemma models — just change the `model` parameter.

## Classifier (`ai/classifier.py`)

Single-item, structured output. One of: `pain`, `lead`, `trend`, `signal`, `noise`.

```python
from pydantic import BaseModel, Field
from typing import Literal

class Classification(BaseModel):
    tag: Literal["pain", "lead", "trend", "signal", "noise"]
    confidence: float = Field(ge=0.0, le=1.0)
    reason: str = Field(max_length=200)
    topics: list[str] = Field(default_factory=list, max_length=5)

async def classify(item: RawItem) -> Classification:
    response = await client.aio.models.generate_content(
        model="gemini-3.1-flash-lite",
        contents=_build_prompt(item),
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=Classification,
            temperature=0.0,
            max_output_tokens=300,
        ),
    )
    return Classification.model_validate_json(response.text)
```

**Tag definitions (use verbatim in the prompt):**
- `pain`: Person is venting about a real problem but not asking for a build/service. Content fodder, not a lead.
- `lead`: Person is asking how to build / who can build / what tool to use for something we could build. Direct intent. Examples: "Looking for someone to build me an n8n workflow that...", "How do I automate X across Slack and HubSpot?", "Need a voice agent that..."
- `trend`: News/release/discussion about a tool, technique, or shift relevant to AI/automation/agents.
- `signal`: Useful but doesn't fit above — someone sharing what worked, a teardown, a technique.
- `noise`: Memes, drama, off-topic, generic complaints. Stored but never advances.

## Summarizer (`ai/summarizer.py`)

Runs on non-noise items. Outputs:
```python
class Summary(BaseModel):
    one_liner: str = Field(max_length=140)
    bullets: list[str] = Field(min_length=2, max_length=4)
    key_quote: str | None = Field(default=None, max_length=200)
```

Cache key: `content_hash`. Store JSON in DB, not memory. Multiple consumers (feed view, drafter, Doc exporter) read the same summary.

## Lead extractor (`ai/lead_extractor.py`)

For lead-tagged items, a targeted Flash-Lite pass:
```python
class LeadDetails(BaseModel):
    asker_username: str
    what_they_want: str = Field(max_length=300)
    pain_signals: list[str] = Field(max_length=5)
    budget_signal: Literal["explicit", "implicit", "none"]
    urgency_signal: Literal["urgent", "soon", "exploring", "unclear"]
    contact_hint: str | None = None  # "DM open", "email in profile", etc.
```

Powers both the Sheet export and the dashboard Leads view.

## Drafter (`ai/drafter.py`) — Gemma 4 31B

Fires only on user action: clicking "Draft this" on a feed item, or selecting multiple items and clicking "Draft from selection."

```python
async def generate_draft(item_ids: list[int], voice_profile: str) -> str:
    items = await get_items_with_summaries(item_ids)
    prompt = _build_draft_prompt(items, voice_profile)
    response = await client.aio.models.generate_content(
        model="gemma-4-31b",
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=0.7,
            max_output_tokens=600,
        ),
    )
    return response.text.strip()
```

Note: Gemma models don't support structured output schemas the way Gemini Flash does. Don't try to force JSON output from Gemma — let it return plain text and parse downstream if needed.

### Prompt structure for `generate_draft`

```
You are drafting a LinkedIn post in {user_name}'s voice.

VOICE GUIDELINES:
{contents of voice_profile.md}

SOURCE MATERIAL (already summarized — do not invent details beyond these):
{for each item: source, title, one_liner, bullets, url}

TASK:
Write one LinkedIn post that opens with a specific observation from the source material,
develops a thesis the audience (technical founders, agency owners, ops leads) cares about,
and ends with a question that invites comments.

CONSTRAINTS:
- 150-220 words
- No emoji unless they appear in voice_profile.md
- No "I'm excited to share" / "thrilled to announce" openers
- One concrete number, name, or quote from the source material in the first 3 lines
- Do not link out (LinkedIn de-prioritizes posts with external links)

Return only the post text. No preamble, no explanation.
```

### Generating variants

Gemma is fast and free. When the user clicks "Draft this," generate **3 variants** in parallel (3x `asyncio.gather`) and show them as tabs in the UI. Picking the best of three is meaningfully better than iterating on one — and at zero cost you should.

## Voice profile

Create `frontend/voice_profile.md` (gitignored). Template:
```
TONE: direct, technical, occasionally dry. No hype.
NEVER USE: "in today's fast-paced world", "game-changer", "revolutionize", "unleash"
DO USE: specific numbers, named tools, concrete workflows, contrarian takes when warranted
STRUCTURE: hook (1-2 lines), build (4-8 lines), payoff/question (1-2 lines)
EXAMPLES OF MY ACTUAL POSTS:
[paste 3-5 of your real LinkedIn posts here]
```

The drafter loads this file on every call. Update it whenever your style evolves. The **same file** is uploaded to your Cowork Project so both surfaces use the same voice reference. See `cowork_workflow.md`.

## Cost guardrails (implement in `ai/__init__.py`)

Caps are per UTC day, configurable via `.env`:
- `DAILY_FLASH_CALL_CAP=400` (default; leaves headroom under the 500 RPD limit)
- `DAILY_GEMMA_CALL_CAP=1000` (default; under the 1,500 RPD limit on Gemma 4 31B)
- Hard fail when caps hit; banner in the dashboard. Never silently degrade.
- Log every call to `ai_call_log` table: model, tokens_in, tokens_out, duration_ms. Dashboard reads this for the "today's usage" pill.

## Why no Pro tier

Three reasons:
1. **Cowork is better for the work Pro would do.** Voice fidelity comes from accumulated context (past posts as files, persistent memory, conversational iteration). A single API call can't match a conversation in a Project with that context built up.
2. **Pro requires pay-per-request billing**, which means linking a card and managing a credit balance. Avoidable complexity for a personal tool.
3. **The dashboard's job is speed, not perfection.** Gemma 4 31B at ~60-70% first-draft usability is the right tradeoff when generation is free and fast. For the other 30-40% of drafts you'd want to polish, you have Cowork.

## Switching models later

If Gemma 4 31B quality is genuinely insufficient and you've validated this over two weeks of real use (not vibes), the swap is one config change: `GEMINI_DRAFT_MODEL=gemini-3.1-pro` in `.env`, plus enable pay-per-request billing in AI Studio. Code doesn't change. But: try the Cowork path first. That's what it's there for.