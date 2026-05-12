from datetime import UTC, datetime

from app.db import get_db
from app.models import Item, Lead, LeadAssignment
from app.schemas import AssignmentPatch, LeadOut, LeadsResponse
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/leads", tags=["leads"])

_VALID_STATUSES = {"new", "reviewing", "contacted", "closed"}


def _row_to_out(lead: Lead, assignment: LeadAssignment, item: Item) -> LeadOut:
    return LeadOut(
        assignment_id=assignment.id,
        lead_id=lead.id,
        item_id=item.id,
        title=item.title,
        url=item.url,
        source=item.source,
        subreddit=item.subreddit,
        author=item.author,
        external_id=item.external_id,
        created_utc=item.created_utc,
        what_they_want=lead.what_they_want,
        budget_signal=lead.budget_signal,
        urgency_signal=lead.urgency_signal,
        score=lead.score,
        contact_hint=lead.contact_hint,
        status=assignment.status,
        notes=assignment.notes,
        contacted_at=assignment.contacted_at,
    )


@router.get("", response_model=LeadsResponse)
async def get_leads(
    status: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> LeadsResponse:
    user_id = "self"
    base = (
        select(Lead, LeadAssignment, Item)
        .join(LeadAssignment, LeadAssignment.lead_id == Lead.id)
        .join(Item, Item.id == Lead.item_id)
        .where(LeadAssignment.user_id == user_id)
    )
    if status:
        base = base.where(LeadAssignment.status == status)
    base = base.order_by(Lead.score.desc(), Lead.created_at.desc())

    total: int = (await db.execute(select(func.count()).select_from(base.subquery()))).scalar_one()
    rows = (await db.execute(base.offset(offset).limit(limit))).all()

    return LeadsResponse(
        leads=[_row_to_out(lead, assignment, item) for lead, assignment, item in rows],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.patch("/{assignment_id}", response_model=LeadOut)
async def update_assignment(
    assignment_id: int,
    patch: AssignmentPatch,
    db: AsyncSession = Depends(get_db),
) -> LeadOut:
    user_id = "self"
    row = (await db.execute(
        select(Lead, LeadAssignment, Item)
        .join(LeadAssignment, LeadAssignment.lead_id == Lead.id)
        .join(Item, Item.id == Lead.item_id)
        .where(LeadAssignment.id == assignment_id)
        .where(LeadAssignment.user_id == user_id)
    )).one_or_none()

    if row is None:
        raise HTTPException(status_code=404, detail="Assignment not found")

    lead, assignment, item = row

    if patch.status is not None:
        if patch.status not in _VALID_STATUSES:
            raise HTTPException(status_code=422, detail=f"status must be one of {_VALID_STATUSES}")
        if patch.status == "contacted" and assignment.status != "contacted":
            assignment.contacted_at = datetime.now(tz=UTC)
        assignment.status = patch.status

    if patch.notes is not None:
        assignment.notes = patch.notes

    await db.commit()
    await db.refresh(assignment)

    return _row_to_out(lead, assignment, item)
