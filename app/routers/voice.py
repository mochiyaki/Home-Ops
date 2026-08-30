from fastapi import APIRouter, Depends

from app.config import Settings, get_settings
from app.models import VoiceWebIn, VoiceWebOut
from app.services import voice as voice_service

router = APIRouter(tags=["voice"])


@router.post("/voice/web", response_model=VoiceWebOut)
async def create_web_voice(
    body: VoiceWebIn,
    settings: Settings = Depends(get_settings),
) -> VoiceWebOut:
    data = voice_service.web_session(settings, body.house_snapshot)
    return VoiceWebOut.model_validate(data)
