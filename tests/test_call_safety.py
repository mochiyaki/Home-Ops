"""Guards that stop the backend ringing a real phone by accident.

Written after a test run dialed a real number eight times: the suite had
inherited a live API key from .env, and `test_call_cap` places calls by design.
"""

from __future__ import annotations

import pytest

from app.config import Settings
from app.services import guava_caller


def _settings(**kw):
    base = dict(guava_api_key="gva-test", guava_agent_number="+15550000000",
                homeops_allow_real_calls=False,
                homeops_call_cooldown_seconds=60)
    return Settings(_env_file=None, **{**base, **kw})


@pytest.fixture(autouse=True)
def _reset_cooldown():
    guava_caller._recent.clear()
    yield
    guava_caller._recent.clear()


def _record(call_id):
    from app import store
    store.put({"id": call_id, "provider": "guava", "state": "dialing",
               "shop_name": "s", "phone": "+15551230000",
               "brief": {"problem": "leak"}, "mock": False})


def _dialed(monkeypatch) -> list:
    """Capture dials without starting a thread or touching the network."""
    seen = []

    class FakeThread:
        def __init__(self, target=None, args=(), **kw):
            self.args = args

        def start(self):
            seen.append(self.args[1])

    monkeypatch.setattr(guava_caller.threading, "Thread", FakeThread)
    return seen


def test_dialing_is_off_by_default(monkeypatch):
    seen = _dialed(monkeypatch)
    _record("s1")
    guava_caller.place_call(_settings(), "s1", "+15551230000", {"problem": "leak"})
    assert seen == [], "must not dial unless HOMEOPS_ALLOW_REAL_CALLS is set"

    from app import store
    rec = store.get("s1")
    assert rec["mock"] is True
    assert "suppressed" in rec["summary"].lower()


def test_dialing_works_when_explicitly_enabled(monkeypatch):
    seen = _dialed(monkeypatch)
    _record("s2")
    guava_caller.place_call(_settings(homeops_allow_real_calls=True),
                            "s2", "+15551230000", {"problem": "leak"})
    assert seen == ["+15551230000"]


def test_cooldown_blocks_a_burst(monkeypatch):
    """The exact failure mode: a loop hammering the same number."""
    seen = _dialed(monkeypatch)
    settings = _settings(homeops_allow_real_calls=True)
    for i in range(8):
        _record(f"b{i}")
        guava_caller.place_call(settings, f"b{i}", "+15551230000",
                                {"problem": "leak"})
    assert len(seen) == 1, f"8 attempts should yield 1 dial, got {len(seen)}"

    from app import store
    assert store.get("b1")["state"] == "failed"


def test_cooldown_is_per_number(monkeypatch):
    seen = _dialed(monkeypatch)
    settings = _settings(homeops_allow_real_calls=True)
    for i, number in enumerate(["+15551230000", "+15551230001", "+15551230002"]):
        _record(f"n{i}")
        guava_caller.place_call(settings, f"n{i}", number, {"problem": "leak"})
    assert len(seen) == 3, "different shops must still be callable"


def test_dialled_number_is_the_one_given(monkeypatch):
    """No redirect: the number in the request is the number dialled."""
    seen = _dialed(monkeypatch)
    _record("d1")
    guava_caller.place_call(_settings(homeops_allow_real_calls=True),
                            "d1", "(925) 804-0698", {"problem": "leak"})
    assert seen == ["+19258040698"]


def test_will_dial_needs_both_key_and_permission():
    assert guava_caller.will_dial(_settings()) is False
    assert guava_caller.will_dial(_settings(homeops_allow_real_calls=True)) is True
    assert guava_caller.will_dial(
        _settings(guava_api_key="", homeops_allow_real_calls=True)) is False


@pytest.mark.parametrize("kwargs,fragment", [
    (dict(guava_api_key=""), "GUAVA_API_KEY"),
    (dict(guava_agent_number=""), "GUAVA_AGENT_NUMBER"),
    (dict(), "HOMEOPS_ALLOW_REAL_CALLS"),
])
def test_suppression_reason_is_specific(kwargs, fragment):
    assert fragment in guava_caller.suppression_reason(_settings(**kwargs))


def test_target_number_is_never_rewritten():
    assert guava_caller.target_number(_settings(), "(415) 555-0142") == "+14155550142"
    assert guava_caller.target_number(_settings(), "9258040698") == "+19258040698"
