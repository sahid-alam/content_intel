# Data Sources

## Reddit (PRAW + OAuth, not .json scraping)

**Why not the .json endpoint:** Reddit started returning 403 on the `.json` URLs increasingly through 2026. Public scrapers built on it are fragile and against ToS. PRAW with OAuth is free for personal/research use, gives 60 req/min instead of the unauthenticated 10, and is what Reddit officially supports.

**Setup (one-time, ~3 min):**
1. Go to https://www.reddit.com/prefs/apps
2. Click "create another app" at the bottom
3. Choose "script" type
4. Name: `content-intel-local`. Redirect URI: `http://localhost:8080`
5. Note the client ID (under the app name) and the secret
6. Put both in `.env`:
   ```
   REDDIT_CLIENT_ID=...
   REDDIT_CLIENT_SECRET=...
   REDDIT_USER_AGENT=content-intel/0.1 by /u/yourusername
   ```
   The user agent format Reddit wants: `<platform>:<app-name>:<version> (by /u/<username>)`

**Implementation pattern (`backend/app/sources/reddit.py`):**
- Use `asyncpraw` (PRAW's async fork), not sync PRAW. We're fanning out across many subs.
- One `Reddit` client per process; reuse across calls.
- Configurable subreddit list in `app/config.py`. Default starting set:
  - `r/SaaS`, `r/Entrepreneur`, `r/AI_Agents`, `r/automation`, `r/n8n`, `r/nocode`, `r/smallbusiness`
- For each sub, fetch top of `new` and top of `top?t=day`. Most lead signal is in `new`; `top` gives engagement validation.
- Normalize to `RawItem`:
  ```python
  RawItem(
      external_id=f"reddit:{submission.id}",
      source="reddit",
      subreddit=submission.subreddit.display_name,
      author=submission.author.name if submission.author else "[deleted]",
      title=submission.title,
      body=submission.selftext or "",
      url=f"https://reddit.com{submission.permalink}",
      score=submission.score,
      num_comments=submission.num_comments,
      created_utc=datetime.fromtimestamp(submission.created_utc, tz=timezone.utc),
      raw=submission_to_dict(submission),  # for debugging only
  )
  ```
- Rate limit handling: PRAW handles this internally if you respect its ratelimit warnings. Set `ratelimit_seconds=300` on the client so it sleeps rather than 429s.
- **Comments**: only fetch comments for items the classifier flagged as `lead` (someone asking for help). The comment thread is what makes a lead actionable. Use `submission.comments.replace_more(limit=0)` then walk top 20.

## Hacker News (Algolia API, not Firebase)

**Why Algolia, not Firebase:** Firebase is the official HN API but has no search and requires N HTTP calls for N comments. Algolia indexes everything, supports full-text search, filtering by points/date, and returns full comment trees in one call. No auth needed, no rate limit worth mentioning for our volume. Endpoint: `https://hn.algolia.com/api/v1/`.

**Implementation pattern (`backend/app/sources/hackernews.py`):**
- Use `httpx.AsyncClient` with a shared instance.
- Two query patterns we actually use:
  - **Recent stories (front page-ish):** `GET /search_by_date?tags=story&numericFilters=points>20,created_at_i>{since_ts}&hitsPerPage=100`
  - **Ask HN (best lead source on HN):** `GET /search_by_date?tags=ask_hn&numericFilters=created_at_i>{since_ts}&hitsPerPage=50`
- Optional keyword query: `GET /search?query={kw}&tags=story&numericFilters=points>10` for tracking specific topics ("AI agent", "n8n", etc.) — make this configurable.
- For lead-tagged Ask HN items, fetch the comment tree with `GET /items/{id}`. Returns nested children objects in a single call.
- Normalize to the same `RawItem` shape as Reddit so downstream code doesn't care about source.

## Common dedupe contract

Both sources must produce `external_id` in the form `{source}:{native_id}` so ingest can use a single unique constraint. `content_hash` should be `sha256(title + "\n" + body[:5000]).hexdigest()` — hashing the body excludes vote counts and comment counts, which change. This is what lets us cache AI outputs reliably.

## What about LinkedIn / X / others?

**LinkedIn:** Their ToS prohibits scraping and they actively litigate. Don't. The closest legal substitute is to use Reddit + HN as proxies for what your LinkedIn audience cares about — those are the same people in different clothes. If you need actual LinkedIn trending data later, the only legit path is the official Marketing Developer Platform, which requires partner approval.

**X/Twitter:** API is paid and expensive ($200+/mo for anything useful). Skip for v1.

**Indie Hackers, Product Hunt:** No good public API; not worth scraping for the volume of signal you'd get vs the maintenance burden.

Stick with Reddit + HN. Two sources, both free, both legal, both rich.