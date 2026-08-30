from __future__ import annotations

from datetime import datetime, timedelta, timezone

import httpx

from app.config import Settings
from app.errors import VendorError, VendorNotConfigured
from app.prompt import SYSTEM_PROMPT

GEMINI_MODELS = (
    "gemini-2.5-flash-native-audio-preview-09-2025",
    "gemini-2.0-flash-live-001",
    "gemini-live-2.5-flash-preview",
)


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _use_mock(settings: Settings, key: str) -> bool:
    return settings.homeops_mock and not key


async def mint_session(settings: Settings) -> dict:
    provider = (settings.live_provider or "gemini").strip().lower()
    if provider not in {"gemini", "openai"}:
        provider = "gemini"

    if provider == "openai":
        if _use_mock(settings, settings.openai_api_key):
            return _mock_payload("openai")
        if not settings.openai_api_key:
            raise VendorNotConfigured("openai", "OPENAI_API_KEY")
        return await _mint_openai(settings)

    if _use_mock(settings, settings.gemini_api_key):
        return _mock_payload("gemini")
    if not settings.gemini_api_key:
        raise VendorNotConfigured("gemini", "GEMINI_API_KEY")
    return await _mint_gemini(settings)


def _mock_payload(provider: str) -> dict:
    exp = datetime.now(timezone.utc) + timedelta(minutes=30)
    return {
        "client_secret": "mock-homeops-live",
        "expires_at": _iso(exp),
        "provider": provider,
        "mock": True,
        "instructions": SYSTEM_PROMPT,
    }


async def _mint_gemini(settings: Settings) -> dict:
    expire = datetime.now(timezone.utc) + timedelta(minutes=30)
    new_session = datetime.now(timezone.utc) + timedelta(minutes=2)
    urls = [
        "https://generativelanguage.googleapis.com/v1alpha/auth_tokens",
        "https://generativelanguage.googleapis.com/v1beta/auth_tokens",
    ]
    body = {
        "uses": 1,
        "expireTime": _iso(expire),
        "newSessionExpireTime": _iso(new_session),
    }
    last_error = "Gemini token mint failed"
    async with httpx.AsyncClient(timeout=20.0) as client:
        for url in urls:
            try:
                response = await client.post(
                    url,
                    params={"key": settings.gemini_api_key},
                    json=body,
                    headers={"Content-Type": "application/json"},
                )
            except httpx.HTTPError as exc:
                last_error = str(exc)
                continue
            if response.status_code >= 400:
                last_error = response.text[:500] or response.reason_phrase
                continue
            data = response.json()
            secret = data.get("name") or data.get("token") or data.get("accessToken")
            if not secret:
                last_error = "Gemini token response missing name"
                continue
            return {
                "client_secret": secret,
                "expires_at": data.get("expireTime") or _iso(expire),
                "provider": "gemini",
                "mock": False,
                "instructions": SYSTEM_PROMPT,
                "model": GEMINI_MODELS[0],
            }
    raise VendorError("gemini", last_error)


async def _mint_openai(settings: Settings) -> dict:
    payload = {
        "expires_after": {"anchor": "created_at", "seconds": 600},
        "session": {
            "type": "realtime",
            "model": "gpt-realtime",
            "instructions": SYSTEM_PROMPT,
        },
    }
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(
                "https://api.openai.com/v1/realtime/client_secrets",
                headers={
                    "Authorization": f"Bearer {settings.openai_api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            if response.status_code >= 400:
                # Older mint path used by some Realtime clients.
                fallback = await client.post(
                    "https://api.openai.com/v1/realtime/sessions",
                    headers={
                        "Authorization": f"Bearer {settings.openai_api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": "gpt-4o-realtime-preview",
                        "instructions": SYSTEM_PROMPT,
                    },
                )
                if fallback.status_code >= 400:
                    raise VendorError(
                        "openai",
                        (response.text or fallback.text)[:500] or "OpenAI session mint failed",
                    )
                data = fallback.json()
            else:
                data = response.json()
    except VendorError:
        raise
    except httpx.HTTPError as exc:
        raise VendorError("openai", str(exc)) from exc

    nested = data.get("client_secret") or {}
    secret = data.get("value") or nested.get("value") or nested.get("client_secret")
    expires = data.get("expires_at") or nested.get("expires_at")
    if isinstance(expires, (int, float)):
        expires_at = _iso(datetime.fromtimestamp(expires, tz=timezone.utc))
    elif isinstance(expires, str) and expires:
        expires_at = expires
    else:
        expires_at = _iso(datetime.now(timezone.utc) + timedelta(minutes=10))
    if not secret:
        raise VendorError("openai", "OpenAI session response missing client secret")
    return {
        "client_secret": secret,
        "expires_at": expires_at,
        "provider": "openai",
        "mock": False,
        "instructions": SYSTEM_PROMPT,
    }
