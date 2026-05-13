import logging
from datetime import UTC, datetime

from app.auth import get_current_user
from app.config import settings
from app.db import get_db
from app.exporters.drive_client import get_credentials
from app.exporters.gdocs import DocItemRow, sync_items_to_doc
from app.exporters.gsheets import SheetLeadRow, sync_leads_to_sheet
from app.models import (
    Classification,
    DocSyncLog,
    Item,
    Lead,
    LeadAssignment,
    SheetSyncLog,
    Summary,
)
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/export", tags=["export"])


class ExportResult(BaseModel):
    doc_url: str | None
    doc_appended: int
    sheet_url: str | None
    sheet_upserted: int
    sheet_mirrored: int
    exported_at: str


class ExportStatus(BaseModel):
    doc_url: str | None
    sheet_url: str | None
    drive_folder_url: str | None
    google_auth_ok: bool


@router.get("/status", response_model=ExportStatus)
async def export_status() -> ExportStatus:
    try:
        get_credentials()
        auth_ok = True
    except RuntimeError:
        auth_ok = False

    folder_url = (
        f"https://drive.google.com/drive/folders/{settings.google_drive_folder_id}"
        if settings.google_drive_folder_id
        else None
    )
    sheet_url = (
        f"https://docs.google.com/spreadsheets/d/{settings.leads_sheet_id}/edit"
        if settings.leads_sheet_id
        else None
    )

    return ExportStatus(
        doc_url=None,
        sheet_url=sheet_url,
        drive_folder_url=folder_url,
        google_auth_ok=auth_ok,
    )


@router.post("/now", response_model=ExportResult)
async def export_now(
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user),
) -> ExportResult:
    try:
        creds = get_credentials()
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    # ── Load data from DB into plain Python objects (close session before Google calls) ──
    rows_result = await db.execute(
        select(
            Item.id,
            Item.external_id,
            Item.source,
            Item.subreddit,
            Item.author,
            Item.title,
            Item.url,
            Item.score,
            Item.num_comments,
            Item.created_utc,
            Item.content_hash,
            Classification.tag,
        )
        .join(Classification, Classification.item_id == Item.id)
        .where(Classification.tag != "noise")
        .order_by(Item.created_utc.desc())
    )
    item_rows = rows_result.all()

    if not item_rows:
        return ExportResult(
            doc_url=None,
            doc_appended=0,
            sheet_url=None,
            sheet_upserted=0,
            sheet_mirrored=0,
            exported_at=datetime.now(tz=UTC).isoformat(),
        )

    item_ids = [r.id for r in item_rows]
    content_hashes = [r.content_hash for r in item_rows]

    # Load summaries keyed by content_hash
    summaries_result = await db.execute(
        select(Summary.content_hash, Summary.one_liner, Summary.bullets, Summary.key_quote)
        .where(Summary.content_hash.in_(content_hashes))
    )
    summaries: dict[str, tuple] = {
        row.content_hash: (row.one_liner, row.bullets, row.key_quote)
        for row in summaries_result.all()
    }

    # Load already-exported item IDs for Doc
    exported_result = await db.execute(
        select(DocSyncLog.item_id).where(DocSyncLog.item_id.in_(item_ids))
    )
    already_exported: set[int] = {row[0] for row in exported_result.all()}

    # Build DocItemRows
    doc_rows: list[DocItemRow] = []
    for r in item_rows:
        s = summaries.get(r.content_hash)
        doc_rows.append(DocItemRow(
            item_id=r.id,
            external_id=r.external_id,
            source=r.source,
            subreddit=r.subreddit,
            author=r.author,
            title=r.title,
            url=r.url,
            score=r.score,
            num_comments=r.num_comments,
            created_utc=r.created_utc,
            tag=r.tag,
            one_liner=s[0] if s else None,
            bullets=s[1] if s else [],
            key_quote=s[2] if s else None,
        ))

    # Load leads + assignments + sync log for Sheet export
    leads_result = await db.execute(
        select(
            Lead.id,
            Lead.item_id,
            Lead.what_they_want,
            Lead.urgency_signal,
            Lead.budget_signal,
            Lead.score,
            LeadAssignment.id.label("assignment_id"),
            LeadAssignment.status,
            LeadAssignment.notes,
            SheetSyncLog.last_known_status,
            SheetSyncLog.last_known_notes,
            SheetSyncLog.row_index,
        )
        .join(LeadAssignment, LeadAssignment.lead_id == Lead.id)
        .outerjoin(SheetSyncLog, SheetSyncLog.assignment_id == LeadAssignment.id)
        .where(LeadAssignment.user_id == user_id)
    )
    lead_rows_raw = leads_result.all()

    # We need item metadata for leads too
    lead_item_ids = [r.item_id for r in lead_rows_raw]
    items_for_leads_result = await db.execute(
        select(Item.id, Item.external_id, Item.source, Item.subreddit, Item.author, Item.url, Item.created_utc)
        .where(Item.id.in_(lead_item_ids))
    )
    items_for_leads: dict[int, tuple] = {
        r.id: (r.external_id, r.source, r.subreddit, r.author, r.url, r.created_utc)
        for r in items_for_leads_result.all()
    }

    sheet_rows: list[SheetLeadRow] = []
    for r in lead_rows_raw:
        item_meta = items_for_leads.get(r.item_id)
        if not item_meta:
            continue
        ext_id, source, subreddit, author, url, created_utc = item_meta
        sheet_rows.append(SheetLeadRow(
            assignment_id=r.assignment_id,
            lead_id=r.id,
            external_id=ext_id,
            created_utc=created_utc,
            source=source,
            subreddit=subreddit,
            author=author,
            url=url,
            what_they_want=r.what_they_want,
            urgency_signal=r.urgency_signal,
            budget_signal=r.budget_signal,
            score=r.score,
            status=r.status,
            notes=r.notes,
            last_known_status=r.last_known_status,
            last_known_notes=r.last_known_notes,
            row_index=r.row_index,
        ))

    # ── Google API calls (blocking I/O, run in thread) ──
    doc_result = await sync_items_to_doc(creds, doc_rows, already_exported)
    sheet_result, human_edits = await sync_leads_to_sheet(
        creds,
        settings.leads_sheet_id,
        settings.leads_sheet_tab,
        sheet_rows,
    )

    # ── Write sync logs back to DB ──
    now = datetime.now(tz=UTC)

    # Doc sync log: record only items that were actually written to the doc
    row_by_id = {r.item_id: r for r in doc_rows}
    for item_id in doc_result.exported_item_ids:
        row = row_by_id[item_id]
        db.add(DocSyncLog(
            item_id=item_id,
            doc_id=doc_result.doc_id,
            week_iso=doc_result.week_iso,
            section_heading=f"[{row.tag.upper()}] {row.title[:200]}",
            written_at=now,
        ))

    # Sheet sync log: upsert per assignment
    existing_logs_result = await db.execute(
        select(SheetSyncLog)
        .where(SheetSyncLog.assignment_id.in_([r.assignment_id for r in sheet_rows]))
    )
    existing_logs: dict[int, SheetSyncLog] = {
        log.assignment_id: log for log in existing_logs_result.scalars().all()
    }

    for row in sheet_rows:
        final_status = row.status
        final_notes = row.notes
        # Check if this was a human edit (mirrored)
        for edit in human_edits:
            if edit.assignment_id == row.assignment_id:
                final_status = edit.new_status
                final_notes = edit.new_notes
                break

        if row.assignment_id in existing_logs:
            log = existing_logs[row.assignment_id]
            log.last_written_at = now
            log.last_known_status = final_status
            log.last_known_notes = final_notes
        else:
            db.add(SheetSyncLog(
                assignment_id=row.assignment_id,
                sheet_id=settings.leads_sheet_id,
                row_index=0,
                last_written_at=now,
                last_known_status=final_status,
                last_known_notes=final_notes,
            ))

    # Mirror human edits back to LeadAssignment
    if human_edits:
        assignment_ids = [e.assignment_id for e in human_edits]
        assignments_result = await db.execute(
            select(LeadAssignment).where(LeadAssignment.id.in_(assignment_ids))
        )
        assignments: dict[int, LeadAssignment] = {
            a.id: a for a in assignments_result.scalars().all()
        }
        for edit in human_edits:
            if edit.assignment_id in assignments:
                a = assignments[edit.assignment_id]
                a.status = edit.new_status
                a.notes = edit.new_notes
                if edit.new_status == "contacted" and a.contacted_at is None:
                    a.contacted_at = now

    await db.commit()

    return ExportResult(
        doc_url=doc_result.doc_url,
        doc_appended=doc_result.appended,
        sheet_url=sheet_result.sheet_url,
        sheet_upserted=sheet_result.upserted,
        sheet_mirrored=sheet_result.mirrored,
        exported_at=now.isoformat(),
    )
