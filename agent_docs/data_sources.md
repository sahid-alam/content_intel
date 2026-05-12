# Data Sources

## Reddit (RSS, not PRAW/OAuth)

**Why RSS, not the API:** As of May 2026, Reddit requires all non-Devvit developer access to go through explicit approval (Responsible Builder Policy). Script-type OAuth apps (`reddit.com/prefs/apps`) now redirect to this policy page and cannot be created without approval. Reddit's Devvit platform is for building apps *inside* Reddit — it doesn't support reading posts into an external pipeline. Filing for commercial-use API access is slow and not guaranteed.

Reddit's public RSS feeds (`/r/<sub>/new.rss`) require no credentials, have no meaningful rate limits at our volume, and give us title, URL, author, score, and timestamp — everything the pipeline needs. Comments are not available via RSS; this means we can't fetch comment threads for leads (planned for Phase 4 enrichment). That's an acceptable tradeoff vs. waiting for API approval.

**No setup required.** No credentials, no `.env` entries. Just configure subreddit list.

**Blocking risk:** RSS feeds are public and served to any browser — Reddit cannot distinguish our fetcher from someone loading `/new` in a browser. At our volume (7 subs × 1 fetch/6h = ~28 requests/day) we are well below any threshold that would trigger a block. If Reddit ever adds auth to RSS (unlikely — it would break every RSS reader and Reddit's own embeds), the fallback is to use `old.reddit.com/r/{sub}/new.json` which has historically been more permissive than the main API, or to request API access at that point. For now, RSS is the right call.

**Implementation pattern (`backend/app/sources/reddit.py`):**
- Use `httpx.AsyncClient` (already a dependency). Fan out across all configured subs with `asyncio.gather`.
- Fetch `https://www.reddit.com/r/{sub}/new.rss?limit=100` for each sub.
- Parse XML with `xml.etree.ElementTree` (stdlib, no extra dep).
- Extract post ID from the `<id>` tag (`t3_<id>` format).
- Normalize to `RawItem`:
  ```python
  RawItem(
      external_id=f"reddit:{post_id}",
      source="reddit",
      subreddit=sub,
      author=entry.find("author/name").text or "",
      title=entry.find("title").text or "",
      body="",  # RSS doesn't include selftext
      url=entry.find("link").get("href") or "",
      score=0,   # RSS doesn't include score; set 0
      num_comments=0,
      created_utc=datetime.fromisoformat(entry.find("published").text),
      raw={},
  )
  ```
- Configurable subreddit list in `app/config.py`. Default set:
  `r/SaaS`, `r/Entrepreneur`, `r/AI_Agents`, `r/automation`, `r/n8n`, `r/nocode`, `r/smallbusiness`

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