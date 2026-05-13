"""
Google Docs exporter.

Writes non-noise items with summaries into a weekly append-only Doc
("Content Source — YYYY-WW") in the configured Drive folder.
"""

import asyncio
import logging
from dataclasses import dataclass
from datetime import UTC, datetime

from app.config import settings
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)

_DOC_TITLE_PREFIX = "Content Source"


@dataclass
class DocItemRow:
    item_id: int
    external_id: str
    source: str
    subreddit: str | None
    author: str
    title: str
    url: str
    score: int
    num_comments: int
    created_utc: datetime
    tag: str
    one_liner: str | None
    bullets: list[str]
    key_quote: str | None


@dataclass
class DocExportResult:
    doc_id: str
    doc_url: str
    week_iso: str
    appended: int
    skipped: int
    exported_item_ids: list[int]  # IDs that were actually written (empty if batch failed)


def _week_iso() -> str:
    now = datetime.now(tz=UTC)
    return f"{now.isocalendar().year}-W{now.isocalendar().week:02d}"


def _doc_title(week: str) -> str:
    return f"{_DOC_TITLE_PREFIX} — {week}"


def _find_doc(drive, folder_id: str, title: str) -> str | None:
    q = (
        f"'{folder_id}' in parents"
        f" and name = '{title}'"
        " and mimeType = 'application/vnd.google-apps.document'"
        " and trashed = false"
    )
    result = drive.files().list(q=q, fields="files(id)", pageSize=1).execute()
    files = result.get("files", [])
    return files[0]["id"] if files else None


def _create_doc(drive, docs, folder_id: str, title: str) -> str:
    doc = docs.documents().create(body={"title": title}).execute()
    doc_id: str = doc["documentId"]
    drive.files().update(
        fileId=doc_id,
        addParents=folder_id,
        removeParents="root",
        fields="id, parents",
    ).execute()
    return doc_id


def _build_section_text(row: DocItemRow) -> str:
    tag_label = row.tag.upper()
    source_label = f"r/{row.subreddit}" if row.subreddit else row.source.upper()
    heading = f"[{tag_label}] {source_label} — \"{row.title}\""

    created_str = row.created_utc.strftime("%Y-%m-%d %H:%M UTC")
    meta = (
        f"URL: {row.url}\n"
        f"Author: u/{row.author}\n"
        f"Tag: {row.tag}   |   Score: {row.score}   |   Comments: {row.num_comments}"
        f"   |   Posted: {created_str}"
    )

    body_parts = [f"\n\n## {heading}\n\n{meta}"]
    if row.one_liner:
        body_parts.append(f"\nOne-liner: {row.one_liner}")
    if row.bullets:
        body_parts.append("\nKey points:")
        for b in row.bullets:
            body_parts.append(f"- {b}")
    if row.key_quote:
        body_parts.append(f'\nKey quote: "{row.key_quote}"')
    body_parts.append("\n\n---")
    return "\n".join(body_parts)


def _batch_append_to_doc(docs, doc_id: str, texts: list[str]) -> None:
    """Insert all texts in a single batchUpdate (one get + one write call)."""
    doc = docs.documents().get(documentId=doc_id).execute()
    end_index = doc["body"]["content"][-1]["endIndex"] - 1
    # Concatenate and insert in one request to stay under Docs write quota (60/min).
    combined = "".join(texts)
    docs.documents().batchUpdate(
        documentId=doc_id,
        body={"requests": [{"insertText": {"location": {"index": end_index}, "text": combined}}]},
    ).execute()


def _sync_items_to_doc_sync(
    creds: Credentials,
    rows: list[DocItemRow],
    already_exported: set[int],
) -> DocExportResult:
    drive = build("drive", "v3", credentials=creds)
    docs = build("docs", "v1", credentials=creds)

    week = _week_iso()
    title = _doc_title(week)
    folder_id = settings.google_drive_folder_id

    doc_id = _find_doc(drive, folder_id, title)
    if doc_id is None:
        doc_id = _create_doc(drive, docs, folder_id, title)
        logger.info("Created new Doc: %s (%s)", title, doc_id)

    doc_url = f"https://docs.google.com/document/d/{doc_id}/edit"
    skipped = 0
    new_rows: list[DocItemRow] = []

    for row in rows:
        if row.item_id in already_exported:
            skipped += 1
            continue
        new_rows.append(row)

    exported_item_ids: list[int] = []
    if new_rows:
        texts = [_build_section_text(r) for r in new_rows]
        try:
            _batch_append_to_doc(docs, doc_id, texts)
            exported_item_ids = [r.item_id for r in new_rows]
        except HttpError as exc:
            logger.warning("Doc batch append failed: %s", exc)
            skipped += len(new_rows)

    return DocExportResult(
        doc_id=doc_id,
        doc_url=doc_url,
        week_iso=week,
        appended=len(exported_item_ids),
        skipped=skipped,
        exported_item_ids=exported_item_ids,
    )


async def sync_items_to_doc(
    creds: Credentials,
    rows: list[DocItemRow],
    already_exported: set[int],
) -> DocExportResult:
    return await asyncio.to_thread(
        _sync_items_to_doc_sync, creds, rows, already_exported
    )
