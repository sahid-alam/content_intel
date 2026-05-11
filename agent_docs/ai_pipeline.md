# AI Pipeline

## The two-tier model strategy (and why)

You have Google AI Pro, which gives you both Gemini 3.1 Pro and the Flash-Lite tier with elevated rate limits and monthly API credits. The right way to use this is **not** to send everything to Pro.

| Step | Model | Why |
|---|---|---|
| Classification (every new item) | Gemini 2.5 Flash-Lite | $0.10/$0.40 per 1M tokens. Often free at our volume. Structured output is reliable on simple taxonomies. |
| Summarization (items that survived classification) | Gemini 2.5 Flash-Lite | Same cost story. 3-bullet summary is a Flash-tier task. Cached by content_hash forever. |
| LinkedIn draft generation | Gemini 3.1 Pro | $2/$12 per 1M. Fires only when the user clicks "generate." Voice and judgment matter here. |
| Lead-magnet outline | Gemini 3.1 Pro | Same as drafts — synthesis across many items is where Pro earns its cost. |
| Lead scoring (rule-based) | No model | Engagement metrics + classifier tag + author signals. No reason to spend tokens on this. |

Hard rule from `CLAUDE.md`: **never call 3.1 Pro on raw scraped content**. Always run Flash-Lite filtering + summarization first, then pass the *summary* to Pro. This typically cuts Pro input tokens by 90%+ and is the difference between staying inside subscription credits vs blowing through them.

## SDK

Use the unified `google-genai` SDK (the new one), not the older `google-generativeai`. The old one is deprecated.

```python
from google import genai
from google.genai import types

client = genai.Client(api_key=settings.gemini_api_key)
```

API key comes from AI Studio → "Get API key" while signed in to your Google AI Pro account. With Pro, this key inherits your subscription's elevated quota.

## Classifier (`ai/classifier.py`)

Single-item, structured-output classification. Returns one of: `pain`, `lead`, `trend`, `signal`, `noise`.

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
        model="gemini-2.5-flash-lite",
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

**Tag definitions (in the prompt, exactly):**
- `pain`: Person is venting about a real problem they have but is not asking for a build or service. Useful as content fodder, not a lead.
- `lead`: Person is asking how to build / who can build / what tool to use for something we could build for them. Direct intent. Examples: "Looking for someone to build me an n8n workflow that...", "How do I automate X across Slack and HubSpot?", "Need a voice agent that..."
- `trend`: News/release/discussion about a tool, technique, or industry shift relevant to AI/automation/agents. Useful for content.
- `signal`: Useful but doesn't fit above — e.g. someone publicly sharing what worked, a teardown, a technique.
- `noise`: Memes, drama, off-topic, low-signal venting, generic complaints. Stored but never passed downstream.

## Summarizer (`ai/summarizer.py`)

Runs on items NOT tagged `noise`. Outputs:
```python
class Summary(BaseModel):
    one_liner: str = Field(max_length=140)        # for feed cards
    bullets: list[str] = Field(min_length=2, max_length=4)  # for drafts/exports
    key_quote: str | None = Field(default=None, max_length=200)  # if there's a memorable line
```

Cache key: `content_hash`. Store the JSON in the DB, not in memory. Multiple downstream consumers read the same summary.

## Lead extractor (`ai/lead_extractor.py`)

For items tagged `lead`, do a second targeted Flash-Lite pass to extract:
```python
class LeadDetails(BaseModel):
    asker_username: str
    what_they_want: str = Field(max_length=300)        # plain English description of the build
    pain_signals: list[str] = Field(max_length=5)      # specific frustrations they mention
    budget_signal: Literal["explicit", "implicit", "none"]
    urgency_signal: Literal["urgent", "soon", "exploring", "unclear"]
    contact_hint: str | None = None                    # e.g., "DM open", "email in profile"
```

This is what powers the CSV export and the lead-scoring rules.

## Generator (`ai/generator.py`) — Gemini 3.1 Pro

Two endpoints, both fire on user action only:

### `generate_linkedin_draft(item_ids: list[int], style: str)`

Inputs: 1-3 already-summarized items + the user's voice profile (loaded from `frontend/voice_profile.md`, see below). Output: a single LinkedIn post draft, 150-220 words, formatted with line breaks LinkedIn renders well.

Prompt structure:
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

Return only the post text. No preamble.
```

### `generate_lead_magnet_outline(cluster_id: int)`

A "cluster" is N lead-tagged items grouped by topic via simple keyword overlap. Generates a structured outline:
- Working title
- Reader (1 sentence)
- Promise (1 sentence)
- 5-7 chapter headlines drawn from actual recurring pain points in the cluster
- Suggested CTA tied to your agency's services

This is the highest-leverage Pro call — one outline can become a $5k engagement.

## Cost guardrails (implement in `ai/__init__.py`)

- Soft daily cap: 2,000 Flash-Lite calls/day, 50 Pro calls/day. Configurable in `.env`.
- Hard fail when caps hit; surface in the dashboard as a banner. Never silently fall back to a different model.
- Log every call to a `ai_call_log` table: model, tokens_in, tokens_out, cost_estimate, timestamp. The dashboard has a "spend this month" widget reading from this.

## Voice profile

Create `frontend/voice_profile.md` (gitignored — personal). Template:
```
TONE: direct, technical, occasionally dry. No hype.
NEVER USE: "in today's fast-paced world", "game-changer", "revolutionize", "unleash"
DO USE: specific numbers, named tools, concrete workflows, contrarian takes when warranted
STRUCTURE: hook (1-2 lines), build (4-8 lines), payoff/question (1-2 lines)
EXAMPLES OF MY ACTUAL POSTS:
[paste 3-5 of your real LinkedIn posts here]
```

The generator loads this file on every Pro call. Update it whenever your style evolves.