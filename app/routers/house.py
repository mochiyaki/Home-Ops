"""House record for the homeowner assistant.

Server-side so Ops has the same view of the house whether the homeowner is in
the browser, on the phone, or gone entirely.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app import repo
from app.db import Asset, session
from app.models import AssetIn, AssetOut, HouseOut, HousePatch

router = APIRouter(tags=["house"])


@router.get("/house", response_model=HouseOut)
async def get_house(db: AsyncSession = Depends(session)) -> dict:
    house = await repo.ensure_house(db)
    return repo.house_public(house)


@router.patch("/house", response_model=HouseOut)
async def patch_house(
    body: HousePatch,
    db: AsyncSession = Depends(session),
) -> dict:
    house = await repo.ensure_house(db)
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(house, field, value)
    await db.commit()
    await db.refresh(house)
    return repo.house_public(house)


@router.get("/house/snapshot")
async def get_snapshot(db: AsyncSession = Depends(session)) -> dict:
    """The house as a voice agent sees it. Handy for debugging prompts."""
    house = await repo.ensure_house(db)
    return {"snapshot": repo.house_snapshot(house)}


@router.post("/house/assets", response_model=AssetOut, status_code=201)
async def add_asset(
    body: AssetIn,
    db: AsyncSession = Depends(session),
) -> dict:
    house = await repo.ensure_house(db)
    asset = Asset(
        house_id=house.id,
        room_id=body.roomId,
        category=body.category,
        brand=body.brand,
        model=body.model,
        serial=body.serial,
        warranty_until=body.warrantyUntil,
        purchased=body.purchased,
        manual_summary=body.exaSummary,
        manual_url=body.manualUrl,
        image_url=body.photoDataUrl,
    )
    db.add(asset)
    await db.commit()
    await db.refresh(asset)
    return repo.asset_public(asset)


@router.patch("/house/assets/{asset_id}", response_model=AssetOut)
async def patch_asset(
    asset_id: str,
    body: AssetIn,
    db: AsyncSession = Depends(session),
) -> dict:
    asset = await db.get(Asset, asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="Unknown asset")
    mapping = {
        "roomId": "room_id", "warrantyUntil": "warranty_until",
        "exaSummary": "manual_summary", "manualUrl": "manual_url",
        "photoDataUrl": "image_url",
    }
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(asset, mapping.get(field, field), value)
    await db.commit()
    await db.refresh(asset)
    return repo.asset_public(asset)


@router.delete("/house/assets/{asset_id}", status_code=204)
async def delete_asset(
    asset_id: str,
    db: AsyncSession = Depends(session),
) -> None:
    asset = await db.get(Asset, asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="Unknown asset")
    await db.delete(asset)
    await db.commit()
