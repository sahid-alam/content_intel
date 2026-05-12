"""
Google Sheets exporter for the Leads sheet.

Column-ownership contract:
- Pipeline owns all columns except `status` and `notes`.
- If `status` or `notes` differ from `sheet_sync_log.last_known_*`, the human
  edited the Sheet — mirror those changes back to lead_assignments in DB.
- Rows are keyed by `external_id` (column A) — never trust row index across runs.
"""

import asyncio
import logging
from dataclasses import dataclass
from datetime import UTC, datetime

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)

# Column layout (1-indexed for Sheets API, 0-indexed internally)
_HEADERS = [
    "external_id",   # A — stable key; pipeline-owned
    "created_utc",   # B
    "source",        # C
    "subreddit",     # D
    "author",        # E
    "url",           # F
    "what_they_want",  # G
    "urgency",       # H
    "budget_signal", # I
    "score",         # J
    "status",        # K — human-owned
    "notes",         # L — human-owned
    "last_synced",   # M
]

_COL_EXTERNAL_ID = 0
_COL_STATUS = 10
_COL_NOTES = 11
_SHEET_RANGE_ALL = "A:M"


@dataclass
class SheetLeadRow:
    assignment_id: int
    lead_id: int
    external_id: str
    created_utc: datetime
    source: str
    subreddit: str | None
    author: str
    url: str
    what_they_want: str
    urgency_signal: str
    budget_signal: str
    score: float
    status: str
    notes: str
    # sync log state (None means no prior sync)
    last_known_status: str | None
    last_known_notes: str | None
    row_index: int | None  # None means not yet in Sheet


@dataclass
class SheetExportResult:
    sheet_id: str
    sheet_url: str
    upserted: int
    mirrored: int  # human-edited rows mirrored back to DB
    errors: int


@dataclass
class HumanEdit:
    assignment_id: int
    new_status: str
    new_notes: str


def _get_sheet_data(sheets, sheet_id: str, tab: str) -> list[list[str]]:
    result = (
        sheets.spreadsheets()
        .values()
        .get(spreadsheetId=sheet_id, range=f"{tab}!{_SHEET_RANGE_ALL}")
        .execute()
    )
    return result.get("values", [])


def _ensure_header_row(sheets, sheet_id: str, tab: str, existing: list[list[str]]) -> None:
    if not existing or existing[0] != _HEADERS:
        sheets.spreadsheets().values().update(
            spreadsheetId=sheet_id,
            range=f"{tab}!A1",
            valueInputOption="RAW",
            body={"values": [_HEADERS]},
        ).execute()


def _build_row_values(row: SheetLeadRow, now_str: str) -> list[str]:
    return [
        row.external_id,
        row.created_utc.strftime("%Y-%m-%d %H:%M UTC"),
        row.source,
        row.subreddit or "",
        row.author,
        row.url,
        row.what_they_want,
        row.urgency_signal,
        row.budget_signal,
        str(round(row.score, 1)),
        row.status,    # will be preserved from Sheet if human-edited
        row.notes,     # same
        now_str,
    ]


def _sync_leads_to_sheet_sync(
    creds: Credentials,
    sheet_id: str,
    tab: str,
    rows: list[SheetLeadRow],
) -> tuple[SheetExportResult, list[HumanEdit]]:
    sheets = build("sheets", "v4", credentials=creds)
    now_str = datetime.now(tz=UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    sheet_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/edit"

    existing = _get_sheet_data(sheets, sheet_id, tab)
    _ensure_header_row(sheets, sheet_id, tab, existing)

    # Build external_id → (row_index_in_sheet_data, values) map
    # Row 0 = header, so sheet data row 1 = spreadsheet row 2, etc.
    id_to_sheet_row: dict[str, tuple[int, list[str]]] = {}
    for i, sheet_row in enumerate(existing[1:], start=1):  # skip header
        if sheet_row:
            ext_id = sheet_row[_COL_EXTERNAL_ID]
            id_to_sheet_row[ext_id] = (i + 1, sheet_row)  # +1: 1-indexed spreadsheet row

    human_edits: list[HumanEdit] = []
    updates: list[tuple[int, list[str]]] = []  # (spreadsheet_row, values)
    appends: list[list[str]] = []

    upserted = 0
    mirrored = 0
    errors = 0

    for row in rows:
        row_values = _build_row_values(row, now_str)

        if row.external_id in id_to_sheet_row:
            sheet_row_num, sheet_values = id_to_sheet_row[row.external_id]
            # Check for human edits in status/notes
            sheet_status = sheet_values[_COL_STATUS] if len(sheet_values) > _COL_STATUS else row.status
            sheet_notes = sheet_values[_COL_NOTES] if len(sheet_values) > _COL_NOTES else row.notes

            if (
                row.last_known_status is not None
                and (
                    sheet_status != row.last_known_status
                    or sheet_notes != (row.last_known_notes or "")
                )
            ):
                # Human edited — preserve their values and mirror back to DB
                row_values[_COL_STATUS] = sheet_status
                row_values[_COL_NOTES] = sheet_notes
                human_edits.append(HumanEdit(
                    assignment_id=row.assignment_id,
                    new_status=sheet_status,
                    new_notes=sheet_notes,
                ))
                mirrored += 1
            else:
                # Use current DB values (might have changed from dashboard)
                pass

            updates.append((sheet_row_num, row_values))
        else:
            appends.append(row_values)

        upserted += 1

    # Batch update existing rows
    if updates:
        value_ranges = [
            {
                "range": f"{tab}!A{row_num}",
                "values": [vals],
            }
            for row_num, vals in updates
        ]
        try:
            sheets.spreadsheets().values().batchUpdate(
                spreadsheetId=sheet_id,
                body={
                    "valueInputOption": "RAW",
                    "data": value_ranges,
                },
            ).execute()
        except HttpError as exc:
            logger.warning("Sheet batch update failed: %s", exc)
            errors += len(updates)

    # Append new rows
    if appends:
        try:
            sheets.spreadsheets().values().append(
                spreadsheetId=sheet_id,
                range=f"{tab}!A1",
                valueInputOption="RAW",
                insertDataOption="INSERT_ROWS",
                body={"values": appends},
            ).execute()
        except HttpError as exc:
            logger.warning("Sheet append failed: %s", exc)
            errors += len(appends)

    return (
        SheetExportResult(
            sheet_id=sheet_id,
            sheet_url=sheet_url,
            upserted=upserted,
            mirrored=mirrored,
            errors=errors,
        ),
        human_edits,
    )


async def sync_leads_to_sheet(
    creds: Credentials,
    sheet_id: str,
    tab: str,
    rows: list[SheetLeadRow],
) -> tuple[SheetExportResult, list[HumanEdit]]:
    return await asyncio.to_thread(
        _sync_leads_to_sheet_sync, creds, sheet_id, tab, rows
    )
