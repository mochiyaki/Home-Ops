from __future__ import annotations

import httpx

from app.config import Settings
from app.errors import VendorError, VendorNotConfigured

# 555 numbers are reserved and unroutable, so a mocked shop cannot be called.
# Setting HOMEOPS_DEV_SHOP_PHONE gives the top-ranked shop a number that really
# answers, which is what makes an end-to-end demo possible without a live
# Apify key. The shop stays labelled [MOCK]; only its number is real.
MOCK_PROVIDERS = [
    {
        "name": "[MOCK] City Plumbing",
        "rating": "4.8 (210)",
        "phone": "(415) 555-0142",
        "mapsUrl": None,
    },
    {
        "name": "[MOCK] Mission Pipe",
        "rating": "4.6 (88)",
        "phone": "(415) 555-0190",
        "mapsUrl": None,
    },
    {
        "name": "[MOCK] Noe Valley Drain",
        "rating": "4.9 (41)",
        "phone": "(415) 555-0118",
        "mapsUrl": None,
    },
]


async def find_providers(settings: Settings, trade: str, address: str) -> dict:
    if settings.apify_token:
        providers = await _apify_search(settings, trade, address)
        return {"providers": providers, "mock": False}
    if settings.homeops_mock:
        ranked = _rank(_with_dev_phone(settings, MOCK_PROVIDERS))[:3]
        return {"providers": ranked, "mock": True}
    raise VendorNotConfigured("apify", "APIFY_TOKEN")


def _with_dev_phone(settings: Settings, providers: list[dict]) -> list[dict]:
    """Point every mock shop at one reachable number.

    All of them, not just the best-rated one: during a demo whoever is driving
    picks a shop by name, and any 555 placeholder they land on would hang
    instead of connecting. One number means every choice works.
    """
    if not settings.homeops_dev_shop_phone:
        return providers
    return [{**p, "phone": settings.homeops_dev_shop_phone} for p in providers]


def _score(item: dict) -> float:
    raw = str(item.get("rating") or "0").split()[0]
    try:
        return float(raw)
    except ValueError:
        return 0.0


def _rank(providers: list[dict]) -> list[dict]:
    score = _score
    callable_shops = [p for p in providers if p.get("phone")]
    return sorted(callable_shops, key=score, reverse=True)


async def _apify_search(settings: Settings, trade: str, address: str) -> list[dict]:
    actor = (settings.apify_actor or "compass/crawler-google-places").replace("/", "~")
    url = f"https://api.apify.com/v2/acts/{actor}/run-sync-get-dataset-items"
    payload = {
        "searchStringsArray": [f"{trade} near {address}"],
        "locationQuery": address,
        "maxCrawledPlacesPerSearch": 8,
        "language": "en",
        "maxImages": 0,
        "maxReviews": 0,
        "scrapePlaceDetailPage": False,
    }
    try:
        async with httpx.AsyncClient(timeout=95.0) as client:
            response = await client.post(
                url,
                params={"token": settings.apify_token, "timeout": 90},
                json=payload,
            )
    except httpx.HTTPError as exc:
        raise VendorError("apify", f"Apify request failed: {exc}") from exc

    if response.status_code >= 400:
        raise VendorError("apify", response.text[:500] or "Apify search failed")

    items = response.json()
    if not isinstance(items, list):
        items = items.get("items") or []

    mapped: list[dict] = []
    for item in items:
        phone = (
            item.get("phoneUnformatted")
            or item.get("phone")
            or item.get("phoneNumber")
            or ""
        )
        phone = str(phone).strip()
        if not phone:
            continue
        name = item.get("title") or item.get("name") or "Unknown shop"
        score = item.get("totalScore") or item.get("rating") or item.get("stars")
        count = (
            item.get("reviewsCount")
            or item.get("reviewsNr")
            or item.get("reviewCount")
            or ""
        )
        try:
            rating = f"{float(score):.1f}"
        except (TypeError, ValueError):
            rating = str(score) if score else "n/a"
        if count != "":
            rating = f"{rating} ({count})"
        mapped.append(
            {
                "name": str(name),
                "rating": rating,
                "phone": phone,
                "mapsUrl": item.get("url") or item.get("googleMapsUrl"),
            }
        )

    return _rank(mapped)[:3]
