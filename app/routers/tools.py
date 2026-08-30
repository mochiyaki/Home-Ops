"""Tool endpoints the voice agents call: manual lookup, trade search, dialling."""

from __future__ import annotations

import asyncio
import re
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app import repo, store
from app.config import Settings, get_settings
from app.db import Call, session
from app.errors import CallCapExceeded, DangerBlocked
from app.models import (
    CallIn, CallOut, ExaIn, ExaOut, ProvidersIn, ProvidersOut, dump_brief,
)
from app.phone import to_e164
from app.prompt import brief_text, is_danger
from app.services import apify, exa, guava_caller

router = APIRouter(tags=["tools"])


@router.post("/tools/exa", response_model=ExaOut)
async def lookup_model(
    body: ExaIn,
    settings: Settings = Depends(get_settings),
) -> ExaOut:
    data = await exa.lookup_model(settings, body.query)
    return ExaOut.model_validate(data)


@router.post("/tools/providers", response_model=ProvidersOut)
async def find_providers(
    body: ProvidersIn,
    settings: Settings = Depends(get_settings),
) -> ProvidersOut:
    data = await apify.find_providers(settings, body.trade, body.address)
    return ProvidersOut.model_validate(data)


@router.post("/tools/call", response_model=CallOut)
async def call_provider(
    body: CallIn,
    background: BackgroundTasks,
    settings: Settings = Depends(get_settings),
    db: AsyncSession = Depends(session),
) -> CallOut:
    """Place an outbound quote call. Returns immediately; poll /api/calls/{id}.

    The two product rules live here rather than in the UI, so no client can
    route around them.
    """
    if is_danger(brief_text(body.brief)):
        raise DangerBlocked(
            "Gas, fire, or an uncontrolled flood — tell the homeowner to call "
            "emergency services. HomeOps will not call a vendor."
        )

    if await repo.outbound_count(db) >= store.MAX_CALLS and not body.try_another:
        raise CallCapExceeded()

    guava_caller.ensure_configured(settings)

    # Decide up front whether a phone will actually ring, so the response tells
    # the client the truth. Previously the route reported mock=False and the
    # dialler then quietly suppressed the call.
    will_dial = guava_caller.will_dial(settings)
    dialed = guava_caller.target_number(settings, body.phone)

    call = Call(
        id=str(uuid.uuid4()),
        provider="guava",
        state="dialing",
        shop_name=body.shop_name,
        phone=to_e164(body.phone),
        dialed=dialed if will_dial else "",
        brief=_brief_dict(body.brief),
        mock=not will_dial,
    )
    db.add(call)
    await db.commit()
    await db.refresh(call)

    if not will_dial:
        background.add_task(_mock_progress, call.id, body.shop_name,
                            guava_caller.suppression_reason(settings),
                            _brief_dict(body.brief).get("budget") or "")
        return CallOut(call_id=call.id, mock=True)

    guava_caller.place_call(settings, call.id, body.phone, body.brief,
                            body.shop_name)
    return CallOut(call_id=call.id, mock=False)


def _brief_dict(brief) -> dict:
    dumped = dump_brief(brief)
    return dumped if isinstance(dumped, dict) else {"problem": str(dumped)}


async def _mock_progress(call_id: str, shop_name: str, reason: str,
                         budget: str = "") -> None:
    """Walk a suppressed call through the same states a real one would.

    Books the mock $250 quote exactly when the real agent would: the budget
    covers it, or no budget was given.
    """
    shop = shop_name or "The shop"
    match = re.search(r"\d+", budget or "")
    books = match is None or int(match.group()) >= 250
    await asyncio.sleep(0.7)
    await asyncio.to_thread(store.update, call_id, state="in-call")
    await asyncio.sleep(0.9)
    if books:
        summary = (f"[MOCK] {shop} quoted $250 — booked for tomorrow after "
                   f"7pm. No phone was dialed — {reason}")
        quote = "$250 · booked tomorrow after 7pm"
    else:
        summary = (f"[MOCK] {shop} quoted $250, over the {budget} budget. "
                   f"Not booked. No phone was dialed — {reason}")
        quote = "$250 · tomorrow after 7pm · not booked"
    await asyncio.to_thread(
        store.update,
        call_id,
        state="done",
        summary=summary,
        quote=quote,
        fields={"can_take_job": "yes", "quote": "$250",
                "earliest_window": "tomorrow after 7pm", "booked": books,
                "appointment": "tomorrow after 7pm" if books else ""},
        booked=books,
        mock=True,
    )
