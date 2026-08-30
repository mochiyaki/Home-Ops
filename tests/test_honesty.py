"""The API must not claim a call is real when nothing will ring.

Written after `POST /api/tools/call` returned `mock: false` for calls the
dialler then silently suppressed.
"""

from __future__ import annotations


def test_suppressed_call_is_reported_as_mock(client, brief):
    """No credentials in the test env, so nothing can dial."""
    r = client.post("/api/tools/call",
                    json={"phone": "(415) 555-0142", "brief": brief,
                          "shop_name": "City Plumbing"})
    assert r.status_code == 200
    assert r.json()["mock"] is True, "must not claim a real call"

    call_id = r.json()["call_id"]
    for _ in range(40):
        body = client.get(f"/api/calls/{call_id}").json()
        if body["state"] == "done":
            break
    assert body["mock"] is True
    assert "[MOCK]" in body["summary"]


def test_mock_summary_names_the_shop_and_the_reason(client, brief):
    r = client.post("/api/tools/call",
                    json={"phone": "(415) 555-0142", "brief": brief,
                          "shop_name": "City Plumbing"})
    call_id = r.json()["call_id"]
    for _ in range(40):
        body = client.get(f"/api/calls/{call_id}").json()
        if body["state"] == "done":
            break
    assert "City Plumbing" in body["summary"]
    assert "No phone was dialed" in body["summary"]


def test_health_separates_configured_from_live(client):
    h = client.get("/health").json()
    assert h["ok"] is True
    assert h["configured"] is False, "no key in the test env"
    assert h["calls_live"] is False
    assert h["mock"] is True
    assert h["suppression_reason"], "must say why it will not dial"


def test_suppressed_call_records_no_dialed_number(client, brief):
    from app.db import Call, sync_session

    r = client.post("/api/tools/call",
                    json={"phone": "(415) 555-0142", "brief": brief})
    with sync_session() as s:
        call = s.get(Call, r.json()["call_id"])
        assert call.dialed == "", "nothing was dialed, so record nothing"
        assert call.phone == "+14155550142", "but keep the shop's real number"


def test_unmatched_api_path_returns_json_not_html(client):
    """The SPA catch-all must not hand an API caller a webpage."""
    r = client.get("/api/calls/")
    assert r.status_code == 404
    assert r.headers["content-type"].startswith("application/json")
    assert r.json()["error"] == "NotFound"

    r = client.get("/api/nope")
    assert r.status_code == 404
    assert "<!DOCTYPE" not in r.text


def test_spa_still_serves_deep_links(client):
    """Non-API paths still fall through to the app."""
    r = client.get("/overview")
    assert r.status_code in (200, 503)  # 503 only if dist is not built
    assert r.json()["error"] != "NotFound" if r.status_code == 503 else True
