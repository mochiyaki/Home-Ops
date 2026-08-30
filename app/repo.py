"""Async data access for the FastAPI routes.

Mirrors app.store, which is the blocking equivalent used by the Guava agent
threads. Routes should use this module so nothing blocks the event loop.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import Asset, Call, House, Turn

DEFAULT_SLUG = "default"


# --------------------------------------------------------------------- calls

def call_public(call: Call, *, with_transcript: bool = False) -> dict[str, Any]:
    data: dict[str, Any] = {
        "id": call.id,
        "state": call.state,
        "summary": call.summary,
        "quote": call.quote,
        "mock": bool(call.mock),
        "provider": call.provider,
        "shop_name": call.shop_name,
        "phone": call.phone,
        "fields": call.fields or {},
        "booked": bool(call.booked),
        "termination_reason": call.termination_reason,
        "error": call.error,
        "duration_seconds": call.duration_seconds,
        "created_at": call.created_at.isoformat() if call.created_at else None,
        "ended_at": call.ended_at.isoformat() if call.ended_at else None,
    }
    if with_transcript:
        data["transcript"] = [turn_public(t) for t in call.turns]
    return data


def turn_public(turn: Turn) -> dict[str, Any]:
    return {
        "seq": turn.seq,
        "speaker": turn.speaker,
        "text": turn.text,
        "interrupted": bool(turn.interrupted),
        "at": turn.at.isoformat() if turn.at else None,
    }


async def get_call(session: AsyncSession, call_id: str) -> Call | None:
    call = await session.get(Call, call_id)
    if call:
        return call
    return await session.scalar(
        select(Call).where(Call.provider_call_id == call_id)
    )


async def list_calls(session: AsyncSession, limit: int = 50) -> list[Call]:
    result = await session.scalars(
        select(Call).order_by(Call.created_at.desc()).limit(limit)
    )
    return list(result)


async def outbound_count(session: AsyncSession) -> int:
    """Non-failed calls in the last hour. Autonomous outreach chains up to
    three calls per job, so the cap is a rolling window, not a lifetime count —
    it still stops a runaway loop cold."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=1)
    return int(await session.scalar(
        select(func.count()).select_from(Call)
        .where(Call.state != "failed", Call.created_at >= cutoff)
    ) or 0)


# -------------------------------------------------------------------- houses

async def get_house(session: AsyncSession, slug: str = DEFAULT_SLUG) -> House | None:
    return await session.scalar(select(House).where(House.slug == slug))


async def ensure_house(session: AsyncSession, slug: str = DEFAULT_SLUG) -> House:
    """Get the house, seeding the demo record the first time it is asked for."""
    house = await get_house(session, slug)
    if house:
        return house
    house = House(slug=slug, **SEED)
    for asset in SEED_ASSETS:
        house.assets.append(Asset(**asset))
    session.add(house)
    await session.commit()
    await session.refresh(house)
    return house


def house_public(house: House) -> dict[str, Any]:
    """The house in the shape the frontend already speaks."""
    return {
        "id": house.id,
        "slug": house.slug,
        "address": house.address,
        "homeowner": house.homeowner,
        "rooms": house.rooms or [],
        "drawings": house.drawings or [],
        "details": house.details or [],
        "contractors": house.contractors or [],
        "maintenance": house.maintenance or [],
        "projects": house.projects or [],
        "assets": [asset_public(a) for a in house.assets],
        "updated_at": house.updated_at.isoformat() if house.updated_at else None,
    }


def asset_public(asset: Asset) -> dict[str, Any]:
    """Field names match frontend/src/house.js so the UI needs no translation."""
    return {
        "id": asset.id,
        "roomId": asset.room_id,
        "category": asset.category,
        "brand": asset.brand,
        "model": asset.model,
        "serial": asset.serial,
        "warrantyUntil": asset.warranty_until,
        "purchased": asset.purchased,
        "exaSummary": asset.manual_summary,
        "manualUrl": asset.manual_url,
        "photoDataUrl": asset.image_url,
    }


def house_snapshot(house: House) -> str:
    """The house rendered for a voice agent's context window."""
    rooms = ", ".join(r.get("name", "") for r in (house.rooms or [])) or "none"
    lines = []
    by_room = {r.get("id"): r.get("name", "") for r in (house.rooms or [])}
    for a in house.assets:
        room = by_room.get(a.room_id, "")
        bits = [b for b in (room, a.brand, a.model or a.category) if b]
        if a.warranty_until:
            bits.append(f"warranty {a.warranty_until}")
        lines.append(" · ".join(bits))
    inventory = "; ".join(lines) or "nothing on file"
    details = ", ".join(
        f"{d.get('label')}: {d.get('value')}" for d in (house.details or [])
    ) or "none"
    return (
        f"Address: {house.address or 'unset'}\n"
        f"Homeowner: {house.homeowner or 'unset'}\n"
        f"Rooms: {rooms}\n"
        f"Inventory: {inventory}\n"
        f"Home details: {details}"
    )


SEED = {
    "address": "1428 Folsom St, San Francisco, CA",
    "homeowner": "Jordan Chen",
    "rooms": [
        {"id": "r1", "name": "Kitchen"},
        {"id": "r2", "name": "Bathroom"},
        {"id": "r3", "name": "Laundry"},
        {"id": "r4", "name": "Living"},
    ],
    "drawings": [{"id": "d1", "name": "bathroom-plan.png", "roomId": "r2",
                  "dataUrl": "/floor-plan.jpg"}],
    "details": [
        {"id": "n0", "label": "Homeowner", "value": "Jordan Chen"},
        {"id": "n1", "label": "Bathroom paint",
         "value": "Benjamin Moore OC-17 White Dove"},
        {"id": "n2", "label": "Kitchen backsplash",
         "value": "Fireclay 3x6 white, stacked"},
    ],
    "contractors": [
        {"id": "c1", "name": "City Plumbing", "trade": "Plumber",
         "phone": "(415) 555-0142", "lastJob": "Supply line, 2019"},
    ],
    "maintenance": [
        {"id": "m1", "title": "HVAC filter", "due": "Sep 2026", "room": "Utility"},
        {"id": "m2", "title": "Water heater flush", "due": "Nov 2026",
         "room": "Utility"},
    ],
    "projects": [
        {"id": "p1", "title": "Bathroom refresh", "kind": "reno",
         "status": "quoting", "budget": "$12,000", "roomId": "r2",
         "notes": "Keep the existing layout. Walls stay White Dove.",
         "bids": [
             {"name": "Bay Tile Co", "phone": "(415) 555-0190",
              "rating": "4.8 · 120 reviews",
              "quote": "Tile + labor $9,400. Three weeks."},
             {"name": "Folsom Bath", "phone": "(415) 555-0118",
              "rating": "4.6 · 88 reviews", "quote": ""},
         ]},
    ],
}

SEED_ASSETS = [
    {"room_id": "r1", "category": "fridge", "brand": "Samsung",
     "model": "RF28R7351SR", "serial": "SM-884219",
     "warranty_until": "Oct 2027", "purchased": "Oct 2022",
     "image_url": "/inventory/samsung-french-door-fridge.jpg",
     "manual_summary": "28 cu. ft. Smart 4-Door Flex French Door with "
                       "FlexZone & AutoFill Pitcher"},
    {"room_id": "r1", "category": "dishwasher", "brand": "Bosch",
     "model": "SHPM88Z75N", "serial": "FD-881240",
     "warranty_until": "Nov 2026", "purchased": "Nov 2021",
     "image_url": "/inventory/bosch-800-series-dishwasher.jpg",
     "manual_summary": "800 Series, CrystalDry technology, 42 dBA, "
                       "third rack layout"},
    {"room_id": "r1", "category": "cooktop", "brand": "Wolf", "model": "GR366",
     "serial": "WF-994320", "warranty_until": "Jan 2028",
     "purchased": "Jan 2023",
     "image_url": "/inventory/wolf-gas-cooktop-range.jpg",
     "manual_summary": "36-inch Dual-Stacked Burner Gas Range with signature "
                       "red knobs"},
    {"room_id": "r2", "category": "fixture", "brand": "Kohler",
     "model": "Purist K-14402", "serial": "KH-001924",
     "warranty_until": "Lifetime finish", "purchased": "Aug 2021",
     "image_url": "/inventory/kohler-purist-faucet.jpg",
     "manual_summary": "Matte Black Widespread Bathroom Sink Faucet with "
                       "lever handles"},
    {"room_id": "r3", "category": "washer", "brand": "LG",
     "model": "WM4000HBA", "serial": "LG-773190",
     "warranty_until": "Apr 2027", "purchased": "Apr 2022",
     "image_url": "/inventory/lg-front-load-washer.jpg",
     "manual_summary": "4.5 cu. ft. Ultra Large Capacity Smart Front Load "
                       "Washer with TurboWash 360"},
]
