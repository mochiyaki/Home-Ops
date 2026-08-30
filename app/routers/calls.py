"""Reading call state. Guava pushes progress in, so these are plain reads."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app import repo
from app.db import session
from app.models import CallDetail, CallStatus, TurnOut

router = APIRouter(tags=["calls"])


@router.get("/calls", response_model=list[CallDetail])
async def list_calls(
    limit: int = 50,
    db: AsyncSession = Depends(session),
) -> list[dict]:
    """Call history, newest first. Survives restarts now that it is in Postgres."""
    calls = await repo.list_calls(db, limit=limit)
    return [repo.call_public(c) for c in calls]


@router.get("/calls/{call_id}", response_model=CallStatus)
async def get_call(
    call_id: str,
    db: AsyncSession = Depends(session),
) -> dict:
    """Cheap poll for the live call view."""
    call = await repo.get_call(db, call_id)
    if not call:
        raise HTTPException(status_code=404, detail="Unknown call id")
    return {
        "state": call.state,
        "summary": call.summary,
        "quote": call.quote,
        "booked": bool(call.booked),
        "appointment": (call.fields or {}).get("appointment") or None,
        "mock": bool(call.mock),
    }


@router.get("/calls/{call_id}/detail", response_model=CallDetail)
async def get_call_detail(
    call_id: str,
    db: AsyncSession = Depends(session),
) -> dict:
    """Structured fields plus the full transcript."""
    call = await repo.get_call(db, call_id)
    if not call:
        raise HTTPException(status_code=404, detail="Unknown call id")
    return repo.call_public(call, with_transcript=True)


@router.get("/calls/{call_id}/transcript", response_model=list[TurnOut])
async def get_transcript(
    call_id: str,
    db: AsyncSession = Depends(session),
) -> list[dict]:
    """Turn-by-turn transcript, written live as the call happens."""
    call = await repo.get_call(db, call_id)
    if not call:
        raise HTTPException(status_code=404, detail="Unknown call id")
    return [repo.turn_public(t) for t in call.turns]
