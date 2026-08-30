from __future__ import annotations

import httpx

from app.config import Settings
from app.errors import VendorError, VendorNotConfigured

MOCK_SUMMARY = (
    "[MOCK] Top-freezer refrigerator; common ice-maker kit IM4A. "
    "Not a live Exa result."
)
MOCK_URL = "https://example.invalid/mock-manual"


async def lookup_model(settings: Settings, query: str) -> dict:
    if settings.exa_api_key:
        return await _exa_search(settings.exa_api_key, query)
    if settings.homeops_mock:
        return {"summary": MOCK_SUMMARY, "url": MOCK_URL, "mock": True}
    raise VendorNotConfigured("exa", "EXA_API_KEY")


async def _exa_search(api_key: str, query: str) -> dict:
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(
                "https://api.exa.ai/search",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                    "x-api-key": api_key,
                },
                json={
                    "query": query,
                    "numResults": 3,
                    "type": "auto",
                    "contents": {"highlights": True, "summary": True},
                },
            )
    except httpx.HTTPError as exc:
        raise VendorError("exa", f"Exa request failed: {exc}") from exc

    if response.status_code >= 400:
        raise VendorError("exa", response.text[:500] or "Exa lookup failed")

    data = response.json()
    results = data.get("results") or []
    if not results:
        return {"summary": "Exa returned no results.", "url": None, "mock": False}

    first = results[0]
    summary = (
        first.get("summary")
        or " ".join(first.get("highlights") or [])
        or (first.get("text") or "")[:400]
        or first.get("title")
        or "Exa returned a result with no summary."
    )
    if isinstance(summary, list):
        summary = " ".join(str(part) for part in summary)
    return {
        "summary": str(summary).strip()[:800],
        "url": first.get("url"),
        "mock": False,
    }
