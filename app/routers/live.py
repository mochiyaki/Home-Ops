from fastapi import APIRouter, Depends

from app.config import Settings, get_settings
from app.models import LiveSessionOut
from app.prompt import SYSTEM_PROMPT
from app.services import live as live_service

router = APIRouter(tags=["live"])


@router.post("/live/session", response_model=LiveSessionOut)
async def create_live_session(
    settings: Settings = Depends(get_settings),
) -> LiveSessionOut:
    data = await live_service.mint_session(settings)
    data.setdefault("instructions", SYSTEM_PROMPT)
    return LiveSessionOut.model_validate(data)
