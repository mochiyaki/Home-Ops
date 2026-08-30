"""The two rules that define the product. If these break, ship nothing."""

from __future__ import annotations

import pytest

from app.prompt import is_danger


DANGEROUS = [
    "I smell gas near the stove",
    "there's a gas leak in the kitchen",
    "the carbon monoxide alarm is going off",
    "there is a fire under the sink",
    "water is flooding and I can't stop it",
]

ORDINARY = [
    "the dishwasher is leaking under the kitchen sink",
    "the fridge isn't cooling",
    "my water heater is making a noise",
    "the gas range burner won't light",  # mentions gas, is not an emergency
]


@pytest.mark.parametrize("text", DANGEROUS)
def test_danger_detected(text):
    assert is_danger(text), f"should be treated as an emergency: {text!r}"


@pytest.mark.parametrize("text", ORDINARY)
def test_ordinary_problems_not_flagged(text):
    assert not is_danger(text), f"false positive on: {text!r}"


def test_danger_blocks_the_call(client, brief):
    """Rule 1: gas / fire / flood never becomes a vendor call."""
    danger = dict(brief, problem="I smell gas near the stove")
    r = client.post("/api/tools/call",
                    json={"phone": "(415) 555-0142", "brief": danger})
    assert r.status_code == 409
    assert r.json()["error"] == "DangerBlocked"
    assert client.get("/api/calls").json() == [], "no call may be recorded"


def test_books_within_budget(client, brief):
    """Rule 2: HomeOps books autonomously when the quote fits the budget."""
    fits = dict(brief, budget="$300")  # mock quote is $250
    r = client.post("/api/tools/call",
                    json={"phone": "(415) 555-0142", "brief": fits,
                          "shop_name": "City Plumbing"})
    call_id = r.json()["call_id"]
    detail = client.get(f"/api/calls/{call_id}/detail").json()
    assert detail["booked"] is True
    assert "booked" in (detail["quote"] or "")


def test_never_books_over_budget(client, brief):
    """The budget is a hard cap: over it, take the quote but do not book."""
    tight = dict(brief, budget="$100")  # mock quote is $250
    r = client.post("/api/tools/call",
                    json={"phone": "(415) 555-0142", "brief": tight,
                          "shop_name": "City Plumbing"})
    call_id = r.json()["call_id"]
    detail = client.get(f"/api/calls/{call_id}/detail").json()
    assert detail["booked"] is False
    assert "not booked" in (detail["quote"] or "")


def test_brief_defaults_to_auto_book():
    from app.models import JobBrief

    b = JobBrief(address="x", problem="y", trade="plumber", homeowner="z")
    assert b.auto_book is True
