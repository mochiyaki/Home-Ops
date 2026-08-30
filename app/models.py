from typing import Any, Literal

from pydantic import BaseModel


class ExaIn(BaseModel):
    query: str


class ExaOut(BaseModel):
    summary: str
    url: str | None = None
    mock: bool = False


class ProvidersIn(BaseModel):
    trade: str
    address: str


class Provider(BaseModel):
    name: str
    rating: str
    phone: str
    mapsUrl: str | None = None


class ProvidersOut(BaseModel):
    providers: list[Provider]
    mock: bool = False


class JobBrief(BaseModel):
    address: str = ""
    problem: str = ""
    trade: str = ""
    homeowner: str = ""
    budget: str | None = None
    availability: str | None = None
    asset: str | None = None
    drawings_note: str | None = None
    # Ops books autonomously: within budget and availability only.
    auto_book: bool = True


class CallIn(BaseModel):
    phone: str
    brief: JobBrief | str
    try_another: bool = False
    shop_name: str = ""


class CallOut(BaseModel):
    call_id: str
    mock: bool = False


class CallStatus(BaseModel):
    state: str
    summary: str | None = None
    quote: str | None = None
    booked: bool = False
    appointment: str | None = None
    mock: bool = False


class LiveSessionOut(BaseModel):
    client_secret: str
    expires_at: str
    provider: str
    mock: bool = False
    instructions: str = ""


class VoiceWebIn(BaseModel):
    house_snapshot: str = ""


class VoiceWebOut(BaseModel):
    mode: Literal["guava", "browser"]
    webrtc_code: str = ""
    mock: bool = False
    first_message: str = ""


def dump_brief(brief: JobBrief | str) -> dict[str, Any] | str:
    if isinstance(brief, str):
        return brief
    return brief.model_dump()


class AssetIn(BaseModel):
    roomId: str = ""
    category: str = "appliance"
    brand: str = ""
    model: str = ""
    serial: str = ""
    warrantyUntil: str = ""
    purchased: str = ""
    exaSummary: str = ""
    manualUrl: str = ""
    photoDataUrl: str = ""


class AssetOut(AssetIn):
    id: str


class HousePatch(BaseModel):
    address: str | None = None
    homeowner: str | None = None
    rooms: list[Any] | None = None
    drawings: list[Any] | None = None
    details: list[Any] | None = None
    contractors: list[Any] | None = None
    maintenance: list[Any] | None = None
    projects: list[Any] | None = None


class HouseOut(BaseModel):
    id: str
    slug: str
    address: str
    homeowner: str
    rooms: list[Any] = []
    drawings: list[Any] = []
    details: list[Any] = []
    contractors: list[Any] = []
    maintenance: list[Any] = []
    projects: list[Any] = []
    assets: list[AssetOut] = []
    updated_at: str | None = None


class TurnOut(BaseModel):
    seq: int
    speaker: str
    text: str
    interrupted: bool = False
    at: str | None = None


class CallDetail(BaseModel):
    id: str
    state: str
    summary: str | None = None
    quote: str | None = None
    mock: bool = False
    provider: str = "guava"
    shop_name: str = ""
    phone: str = ""
    fields: dict[str, Any] = {}
    booked: bool = False
    termination_reason: str | None = None
    error: str | None = None
    duration_seconds: int | None = None
    created_at: str | None = None
    ended_at: str | None = None
    transcript: list[TurnOut] = []
