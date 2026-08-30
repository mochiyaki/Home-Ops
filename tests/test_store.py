"""The blocking store the Guava handler threads write through."""

from __future__ import annotations

from app import store


def _new(call_id="c1", **kw):
    return store.put({"id": call_id, "provider": "guava", "state": "dialing",
                      "shop_name": "City Plumbing", "phone": "(415) 555-0142",
                      "brief": {"problem": "leak"}, "mock": False, **kw})


def test_put_and_get():
    _new()
    rec = store.get("c1")
    assert rec["state"] == "dialing"
    assert rec["shop_name"] == "City Plumbing"


def test_update_merges_fields():
    _new()
    store.update("c1", fields={"quote": "250"})
    store.update("c1", fields={"earliest_window": "Tuesday"})
    assert store.get("c1")["fields"] == {"quote": "250",
                                         "earliest_window": "Tuesday"}


def test_update_sets_ended_at_on_terminal_state():
    _new()
    assert store.get("c1")["duration_seconds"] is None
    store.update("c1", state="done")
    assert store.get("c1")["duration_seconds"] is not None


def test_update_ignores_unknown_keys():
    _new()
    assert store.update("c1", state="done", not_a_column="x") is not None


def test_lookup_by_provider_call_id():
    _new()
    store.update("c1", provider_call_id="prov-123")
    assert store.get("prov-123")["id"] == "c1"


def test_transcript_is_ordered():
    _new()
    store.add_turn("c1", "agent", "Hi, this is HomeOps.")
    store.add_turn("c1", "shop", "City Plumbing.")
    store.add_turn("c1", "agent", "Can you take a dishwasher leak?")
    turns = store.transcript("c1")
    assert [t["seq"] for t in turns] == [0, 1, 2]
    assert [t["speaker"] for t in turns] == ["agent", "shop", "agent"]


def test_blank_turns_are_dropped():
    _new()
    store.add_turn("c1", "agent", "   ")
    store.add_turn("c1", "agent", "")
    assert store.transcript("c1") == []


def test_failed_calls_do_not_count_against_the_cap():
    _new("a")
    _new("b")
    store.update("b", state="failed")
    assert store.outbound_count() == 1


def test_update_unknown_call_is_survivable():
    assert store.update("ghost", state="done") is None
