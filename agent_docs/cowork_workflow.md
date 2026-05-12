# Cowork Workflow

The pipeline mirrors curated material into a Google Doc + Sheet. You operate against them in a Cowork Project for premium drafts and lead magnets.

## Artifacts

### Google Doc: "Content Source — YYYY-WW"

Append-only weekly Doc. New items become new sections at the top; old sections never modified.

Section format:
```
## [LEAD] r/SaaS — "Looking for someone to build n8n workflows for me"

URL: https://reddit.com/r/SaaS/comments/...
Author: u/somefounder
Tag: lead   |   Score: 87   |   Comments: 24   |   Posted: 2026-05-11 14:32 UTC

One-liner: SaaS founder running 6-tool stack, needs automation help, budget mentioned.

Key points:
- Currently doing CSV exports between HubSpot, Stripe, Notion manually
- Estimates 8-10 hours/week lost; willing to pay "a few thousand"
- Explicitly says "DM open"

Key quote: "I'd rather pay someone who's done this before than burn another month."

---
```

`[LEAD]` / `[PAIN]` / `[TREND]` / `[SIGNAL]` prefixes let you reference sections by category in Cowork: "draft from the LEAD sections this week."

### Google Sheet: "Leads"

**v1 (single user):** one tab named `Leads`, one row per lead. Status and notes editable; pipeline preserves them.

**v2 (two users):** two tabs — `Leads — Yourname` and `Leads — Partnername`. Each user only edits their own tab. Both tabs reference the same underlying leads; only the per-user assignment data differs. Exporter handles this by writing each user's assignments to their tab.

Columns (same shape both versions):

| Column | Owner | Notes |
|---|---|---|
| `external_id` | pipeline | Unique key for upsert |
| `created_utc` | pipeline | Original post timestamp |
| `source` / `subreddit` / `author` / `url` | pipeline | Post metadata |
| `what_they_want` | pipeline | AI-extracted |
| `urgency` / `budget_signal` | pipeline | AI-extracted |
| `score` | pipeline | Rule-based |
| **`status`** | **you** | new / contacted / won / lost / dismissed |
| **`notes`** | **you** | Free text |
| `last_synced` | pipeline | Timestamp |

Exporter contract: **never overwrites `status` or `notes`.** Reads them, mirrors changes back to DB, preserves them on write.

## Cowork Project setup

Each user has their own Cowork Project. Curated content is shared (same Doc + Sheet); voice profiles are personal.

In Cowork, create a Project named "Content Intel — Yourname." Add to Project knowledge:

1. **`voice_profile.md`** — your tone, never-use list, do-use list, 3-5 real LinkedIn posts in your voice
2. **`agency_context.md`** describing:
   - Your agency's positioning, services, buyer profiles
   - Past hooks that worked, patterns that didn't
3. **Connector:** Google Drive (so Cowork can read the Doc and Sheet by name)

Project instructions:
```
You help draft LinkedIn content and lead magnet outlines for the user's Gen-AI dev agency. Source material comes from a Google Doc called "Content Source — YYYY-WW" (current week unless specified). The lead list is a Google Sheet called "Leads."

When drafting LinkedIn posts:
- Read voice_profile.md first; it is authoritative on tone
- Reference specific items from the Doc by section, not from your training data
- Never invent details beyond what the Doc contains
- 150-220 words unless asked otherwise
- End with a question that invites comments (not a CTA)

When drafting lead magnet outlines:
- Pull from the Sheet (filter to status=new where useful) and the Doc's LEAD sections
- Look for clusters of 3+ similar pain points before proposing a magnet
- Structure: title, reader, promise, 5-7 chapters, suggested CTA tied to agency services
- Be skeptical of clusters that are really just one pain point reworded
```

Don't put pipeline/crawling knowledge in Cowork. Cowork doesn't need to know how the Doc gets populated — only how to read it.

## Operating playbook

### Quick post from this week's trends
> "Read this week's Content Source Doc. Pick the two most contrarian items from the TREND sections, ignore the rest, draft a LinkedIn post tying them together. Voice rules from voice_profile.md apply."

### Targeted post from specific sections
> "Use sections 3 and 7 from the current week's Doc. Lead with the n8n quote from section 3. Thesis: most automation projects fail at the integration layer, not the AI layer."

### Pain-driven post
> "Pull the three most-upvoted PAIN sections from the last two weeks. Find a common thread if there is one (don't invent one). Draft a post that names the pattern without sounding like a sales pitch."

### Lead magnet outline
> "Open the Leads sheet (my tab). Filter to status=new where what_they_want mentions automation, n8n, or Make. If you see 4+ rows with overlapping pain (not just keywords), propose a lead magnet outline targeting that cluster."

### Outreach DM assist
> "Look at lead row 14 in my Leads tab. Read the linked post. Draft a Reddit DM (under 800 chars) opening with something specific from their post, mentioning a relevant capability without pitching, ending by asking if they'd want to see how I'd approach it. No links."

## What not to do in Cowork

- **Don't ask Cowork to scrape.** Pipeline's job. If material is missing, pipeline hasn't run — check the dashboard.
- **Don't paste raw Reddit/HN content.** Use the Doc. Raw content pollutes Project context.
- **Don't ask Cowork to update the Sheet.** Status and notes are yours; let Cowork read them only. Pipeline owns writes.
- **Don't run against last month's Doc when you mean this week's.** Say "this week's Doc" or "the 2026-W20 Doc" explicitly.

## Dashboard vs Cowork — when to use which

**Dashboard:** what's in the feed; mark a lead as contacted; fast draft to skim and copy; daily triage.
**Cowork:** drafts you'd publish without much editing; synthesizing across many items; lead magnets; outreach DMs needing real personalization.

Same source data. Different surface for different jobs.