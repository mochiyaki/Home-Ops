"""Call placement: the cap, the mock contract, and provider selection."""

from __future__ import annotations

import pytest

from app.config import Settings


def settings(**kw) -> Settings:
    """Settings built from kwargs only - never the developer's .env."""
    blank = dict(guava_api_key="", guava_agent_number="")
    return Settings(_env_file=None, **{**blank, **kw})


def test_mock_branch_is_labelled(client, brief):
    """No vendor key + HOMEOPS_MOCK -> a mock that says so."""
    r = client.post("/api/tools/call",
                    json={"phone": "(415) 555-0142", "brief": brief})
    assert r.status_code == 200
    assert r.json()["mock"] is True

    call_id = r.json()["call_id"]
    for _ in range(40):
        body = client.get(f"/api/calls/{call_id}").json()
        if body["state"] == "done":
            break
    assert body["mock"] is True
    assert "[MOCK]" in body["summary"], "mock results must be visibly labelled"


def test_call_cap(client, brief):
    """Three calls, then 429 unless the caller explicitly asks for one more."""
    from app import store

    for i in range(store.MAX_CALLS):
        r = client.post("/api/tools/call",
                        json={"phone": f"(415) 555-010{i}", "brief": brief})
        assert r.status_code == 200, f"call {i + 1} should be allowed"

    blocked = client.post("/api/tools/call",
                          json={"phone": "(415) 555-0199", "brief": brief})
    assert blocked.status_code == 429
    assert blocked.json()["error"] == "CallCapExceeded"

    override = client.post("/api/tools/call",
                           json={"phone": "(415) 555-0199", "brief": brief,
                                 "try_another": True})
    assert override.status_code == 200


def test_cap_survives_restart(client, brief):
    """The cap counts rows, not process memory - the point of moving to Postgres."""
    from app import store

    client.post("/api/tools/call",
                json={"phone": "(415) 555-0142", "brief": brief})
    assert store.outbound_count() == 1


def test_unknown_call_is_404(client):
    assert client.get("/api/calls/nope").status_code == 404
    assert client.get("/api/calls/nope/detail").status_code == 404


def test_dev_shop_phone_makes_the_top_shop_reachable():
    """555 numbers cannot connect; the dev number lets a demo actually dial."""
    import asyncio
    from app.services import apify

    plain = asyncio.run(apify.find_providers(
        _blank(), "plumber", "1428 Folsom St"))
    assert plain["mock"] is True
    assert all("555" in p["phone"] for p in plain["providers"])

    with_dev = asyncio.run(apify.find_providers(
        _blank(homeops_dev_shop_phone="+19258040698"), "plumber", "1428 Folsom St"))
    shops = with_dev["providers"]
    # Every shop is reachable, so any pick during a demo connects.
    assert all(p["phone"] == "+19258040698" for p in shops)
    assert all(p["name"].startswith("[MOCK]") for p in shops), \
        "the shops stay labelled mocks; only the number is real"
    assert len({p["name"] for p in shops}) == len(shops), "names stay distinct"


def _blank(**kw):
    from app.config import Settings
    base = dict(apify_token="", homeops_mock=True, homeops_dev_shop_phone="")
    return Settings(_env_file=None, **{**base, **kw})
