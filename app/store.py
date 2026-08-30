"""Call state, persisted in Postgres.

Called from two places with different concurrency stories:

  * FastAPI routes -> use `app.repo` (async) instead of this module.
  * Guava handlers -> run on plain threads with no event loop, so they use
    these blocking helpers.

The function names match the old in-memory store so the agent handlers did not
have to change when this moved to Postgres.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import func, select

from app.db import Call, Turn, sync_session

logger = logging.getLogger("homeops.store")

MAX_CALLS = 3


def _public(call: Call) -> dict[str, Any]:
    return {
        "id": call.id,
        "state": call.state,
        "summary": call.summary,
        "quote": call.quote,
        "mock": bool(call.mock),
        "shop_name": call.shop_name,
        "provider": call.provider,
        "fields": call.fields or {},
        "booked": bool(call.booked),
        "termination_reason": call.termination_reason,
        "duration_seconds": call.duration_seconds,
        "created_at": call.created_at.isoformat() if call.created_at else None,
    }


def _find(session, call_id: str) -> Call | None:
    """Accept either our uuid or the provider's own call id."""
    call = session.get(Call, call_id)
    if call:
        return call
    return session.scalar(select(Call).where(Call.provider_call_id == call_id))


def put(record: dict[str, Any]) -> dict[str, Any]:
    with sync_session() as s:
        call = Call(
            id=record["id"],
            provider=record.get("provider", "guava"),
            provider_call_id=record.get("provider_call_id"),
            state=record.get("state", "dialing"),
            shop_name=record.get("shop_name", "") or "",
            phone=record.get("phone", "") or "",
            dialed=record.get("dialed", "") or "",
            brief=record.get("brief") if isinstance(record.get("brief"), dict)
            else {"problem": str(record.get("brief") or "")},
            mock=bool(record.get("mock")),
        )
        s.add(call)
        s.commit()
        s.refresh(call)
        return _public(call)


def get(call_id: str) -> dict[str, Any] | None:
    with sync_session() as s:
        call = _find(s, call_id)
        return _public(call) if call else None


def update(call_id: str, **fields: Any) -> dict[str, Any] | None:
    """Patch a call. Unknown keys are ignored so old call sites keep working."""
    with sync_session() as s:
        call = _find(s, call_id)
        if not call:
            logger.warning("update for unknown call %s", call_id)
            return None
        for key, value in fields.items():
            if key == "fields" and isinstance(value, dict):
                call.fields = {**(call.fields or {}), **value}
                continue
            if hasattr(call, key):
                setattr(call, key, value)
        if call.state in ("done", "failed") and call.ended_at is None:
            call.ended_at = datetime.now(timezone.utc)
        s.commit()
        s.refresh(call)
        return _public(call)


def add_turn(call_id: str, speaker: str, text: str,
             interrupted: bool = False) -> None:
    """Append one utterance. Called live from the Guava speech handlers."""
    text = (text or "").strip()
    if not text:
        return
    with sync_session() as s:
        call = _find(s, call_id)
        if not call:
            return
        seq = s.scalar(
            select(func.coalesce(func.max(Turn.seq), -1)).where(Turn.call_id == call.id)
        )
        s.add(Turn(call_id=call.id, seq=int(seq) + 1, speaker=speaker,
                   text=text, interrupted=interrupted))
        s.commit()


def transcript(call_id: str) -> list[dict[str, Any]]:
    with sync_session() as s:
        call = _find(s, call_id)
        if not call:
            return []
        return [
            {"seq": t.seq, "speaker": t.speaker, "text": t.text,
             "interrupted": t.interrupted, "at": t.at.isoformat()}
            for t in call.turns
        ]


def outbound_count() -> int:
    """Non-failed calls in the last hour (rolling window, matches app.repo)."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=1)
    with sync_session() as s:
        return int(s.scalar(
            select(func.count()).select_from(Call)
            .where(Call.state != "failed", Call.created_at >= cutoff)
        ) or 0)


def public_view(rec: dict[str, Any]) -> dict[str, Any]:
    """Kept for call sites that already hold a dict."""
    return {
        "state": rec.get("state", "unknown"),
        "summary": rec.get("summary"),
        "quote": rec.get("quote"),
        "mock": bool(rec.get("mock")),
    }
