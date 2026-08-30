"""Guava handler behaviour, exercised with MockCall - no network, no phone."""

from __future__ import annotations

import pytest
from guava.testing import MockCall

from app import store
import guava_agent.agent as shop
import guava_agent.ops as ops


def _call(call_id="c1", **fields):
    c = MockCall()
    c.set_variable("homeops_call_id", call_id)
    c.set_variable("shop_name", "City Plumbing")
    for k, v in fields.items():
        c.set_field(k, v)
    return c


def _record(call_id="c1"):
    store.put({"id": call_id, "provider": "guava", "state": "dialing",
               "shop_name": "City Plumbing", "phone": "x",
               "brief": {"problem": "leak"}, "mock": False})


# ------------------------------------------------------------- shop caller

def test_speech_lands_in_the_transcript():
    _record()
    shop.on_agent_speech(_call(), type("E", (), {"utterance": "Hi, HomeOps here.",
                                                 "interrupted": False})())
    shop.on_caller_speech(_call(), type("E", (), {"utterance": "City Plumbing."})())
    turns = store.transcript("c1")
    assert [t["speaker"] for t in turns] == ["agent", "shop"]


def test_booked_quote_is_captured_as_booked():
    _record()
    c = _call(can_take_job="yes", quote="two fifty",
              earliest_window="Tuesday at ten", booked="yes",
              appointment="Tuesday at ten")
    shop.on_quote(c)
    rec = store.get("c1")
    assert rec["state"] == "done"
    assert rec["fields"]["quote"] == "two fifty"
    assert rec["booked"] is True
    assert "booked Tuesday at ten" in (rec["quote"] or "")


def test_unbooked_quote_is_captured_and_not_booked():
    _record()
    c = _call(can_take_job="yes", quote="two fifty",
              earliest_window="Tuesday at ten", booked="no")
    shop.on_quote(c)
    rec = store.get("c1")
    assert rec["state"] == "done"
    assert rec["fields"]["quote"] == "two fifty"
    assert rec["booked"] is False
    assert "not booked" in (rec["quote"] or "")


def test_quote_survives_an_early_hangup():
    """A shop hanging up must not discard fields already collected."""
    _record()
    c = _call(can_take_job="yes", quote="three hundred",
              earliest_window="week of the twentieth")
    shop.on_session_end(c, type("E", (), {"termination_reason": "user-hangup"})())
    rec = store.get("c1")
    assert rec["state"] == "done"
    assert rec["fields"]["quote"] == "three hundred"
    assert rec["termination_reason"] == "user-hangup"


def test_voicemail_is_reported_as_such():
    _record()
    shop.on_session_end(_call(), type("E", (), {"termination_reason": "voicemail"})())
    assert "voicemail" in store.get("c1")["summary"].lower()


def test_declined_job_is_summarised():
    _record()
    shop.on_quote(_call(can_take_job="no"))
    assert "cannot take" in store.get("c1")["summary"]


def test_mock_manual_text_is_never_spoken():
    """With no EXA key the lookup returns [MOCK] - it must not reach the shop."""
    c = MockCall()
    c.set_variable("asset", "Bosch SHPM88Z75N dishwasher")
    answer = shop.on_question(c, "what model is that?")
    assert "[MOCK]" not in answer
    assert "Bosch" in answer


# -------------------------------------------------------------------- ops

def test_ops_danger_never_reaches_a_vendor(monkeypatch):
    called = []
    monkeypatch.setattr(ops.httpx, "post",
                        lambda *a, **k: called.append(a) or None)
    c = MockCall()
    c.set_field("problem", "I smell gas near the stove")
    c.set_field("trade", "plumber")
    ops.on_triaged(c)
    assert called == [], "a gas leak must never trigger a provider lookup"


def test_ops_falls_back_when_the_api_is_down(monkeypatch):
    monkeypatch.setattr(ops.httpx, "get",
                        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("down")))
    house = ops.load_house()
    assert house["address"], "must still hand the agent something usable"
