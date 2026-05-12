"""
Reddit source via public RSS feeds.

Reddit locked down OAuth for external apps in 2026 (Responsible Builder Policy).
RSS requires no credentials and covers the same signal for our use case.
Limitation: no selftext body, no comment counts, score always 0.
"""
import asyncio
import xml.etree.ElementTree as ET
from datetime import UTC, datetime

import httpx
from app.config import settings
from app.schemas import RawItem

_NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "media": "http://search.yahoo.com/mrss/",
}
_RSS_URL = "https://www.reddit.com/r/{sub}/new.rss?limit=100"
_HEADERS = {"User-Agent": "content-intel/0.1 (RSS reader; personal tool)"}


def _post_id(entry_id: str) -> str:
    # <id> looks like: "https://www.reddit.com/r/sub/comments/abc123/title/"
    parts = [p for p in entry_id.rstrip("/").split("/") if p]
    return parts[-2] if len(parts) >= 2 else entry_id


def _parse_feed(xml_text: str, sub: str) -> list[RawItem]:
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return []

    items: list[RawItem] = []
    for entry in root.findall("atom:entry", _NS):
        entry_id = (entry.findtext("atom:id", namespaces=_NS) or "").strip()
        title = (entry.findtext("atom:title", namespaces=_NS) or "").strip()
        if not entry_id or not title:
            continue

        link_el = entry.find("atom:link", _NS)
        url = link_el.get("href", "") if link_el is not None else ""

        published = entry.findtext("atom:published", namespaces=_NS) or ""
        try:
            created_utc = datetime.fromisoformat(published.replace("Z", "+00:00"))
        except ValueError:
            created_utc = datetime.now(tz=UTC)

        author_el = entry.find("atom:author/atom:name", _NS)
        author = (author_el.text or "").strip() if author_el is not None else ""

        post_id = _post_id(entry_id)
        items.append(
            RawItem(
                external_id=f"reddit:{post_id}",
                source="reddit",
                subreddit=sub,
                author=author,
                title=title,
                body="",
                url=url,
                score=0,
                num_comments=0,
                created_utc=created_utc,
                raw={},
            )
        )
    return items


async def _fetch_sub(client: httpx.AsyncClient, sub: str) -> list[RawItem]:
    try:
        resp = await client.get(_RSS_URL.format(sub=sub), timeout=15)
        resp.raise_for_status()
        return _parse_feed(resp.text, sub)
    except Exception:
        return []


async def fetch_reddit() -> list[RawItem]:
    subs = [s.strip() for s in settings.reddit_subreddits.split(",") if s.strip()]
    async with httpx.AsyncClient(headers=_HEADERS) as client:
        results = await asyncio.gather(*[_fetch_sub(client, sub) for sub in subs])

    seen: set[str] = set()
    deduped: list[RawItem] = []
    for batch in results:
        for item in batch:
            if item.external_id not in seen:
                seen.add(item.external_id)
                deduped.append(item)
    return deduped
