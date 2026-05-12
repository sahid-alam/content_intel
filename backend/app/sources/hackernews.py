import asyncio
from datetime import UTC, datetime

import httpx
from app.config import settings
from app.schemas import RawItem

_BASE = "https://hn.algolia.com/api/v1"


def _parse_hit(hit: dict) -> RawItem | None:
    story_id = hit.get("objectID") or hit.get("story_id")
    if not story_id:
        return None
    title = hit.get("title") or hit.get("story_title") or ""
    if not title:
        return None

    created_ts = hit.get("created_at_i")
    if created_ts:
        created_utc = datetime.fromtimestamp(int(created_ts), tz=UTC)
    else:
        created_utc = datetime.now(tz=UTC)

    return RawItem(
        external_id=f"hn:{story_id}",
        source="hn",
        author=hit.get("author") or "",
        title=title,
        body=hit.get("story_text") or hit.get("comment_text") or "",
        url=hit.get("url") or f"https://news.ycombinator.com/item?id={story_id}",
        score=hit.get("points") or 0,
        num_comments=hit.get("num_comments") or 0,
        created_utc=created_utc,
        raw=hit,
    )


async def _search(client: httpx.AsyncClient, path: str, params: dict) -> list[RawItem]:
    try:
        resp = await client.get(f"{_BASE}/{path}", params=params, timeout=15)
        resp.raise_for_status()
        hits = resp.json().get("hits", [])
        results = [_parse_hit(h) for h in hits]
        return [r for r in results if r is not None]
    except Exception:
        return []


async def fetch_hn(lookback_hours: int | None = None) -> list[RawItem]:
    hours = lookback_hours or settings.lookback_hours
    since_ts = int(datetime.now(tz=UTC).timestamp()) - hours * 3600

    keywords = [kw.strip() for kw in settings.hn_keywords.split(",") if kw.strip()]

    async with httpx.AsyncClient() as client:
        tasks = [
            # Recent stories with traction
            _search(client, "search_by_date", {
                "tags": "story",
                "numericFilters": f"points>20,created_at_i>{since_ts}",
                "hitsPerPage": 100,
            }),
            # Ask HN — best lead source
            _search(client, "search_by_date", {
                "tags": "ask_hn",
                "numericFilters": f"created_at_i>{since_ts}",
                "hitsPerPage": 50,
            }),
            # Keyword queries
            *[
                _search(client, "search", {
                    "query": kw,
                    "tags": "story",
                    "numericFilters": f"points>10,created_at_i>{since_ts}",
                    "hitsPerPage": 30,
                })
                for kw in keywords
            ],
        ]

        results = await asyncio.gather(*tasks)

    # Dedupe by external_id (same story can appear in multiple queries)
    seen: set[str] = set()
    deduped: list[RawItem] = []
    for batch in results:
        for item in batch:
            if item.external_id not in seen:
                seen.add(item.external_id)
                deduped.append(item)

    return deduped
