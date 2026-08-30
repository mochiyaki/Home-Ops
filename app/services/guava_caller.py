"""Guava adapter for the outbound shop-quote call.

Follows the same three-branch contract as every other vendor adapter: key set
-> real call, no key + HOMEOPS_MOCK -> labelled mock, else
VendorNotConfigured.

The Guava SDK's `call_phone` blocks for the length of the call, so it runs on a
daemon thread. The agent handlers in `guava_agent/agent.py` write progress
straight into `app.store` (the blocking one) as the call happens.

Nothing here dials unless `HOMEOPS_ALLOW_REAL_CALLS` is on. That default exists
because a test run once inherited a live key and rang a real phone eight times.
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Any

from app import store
from app.config import Settings
from app.errors import VendorNotConfigured
from app.phone import to_e164
from app.prompt import shop_call_vars

logger = logging.getLogger("homeops.guava")

# Last dial time per number, for the runaway-loop guard. Pruned on write so a
# long-running process does not accumulate entries forever.
_recent: dict[str, float] = {}
_recent_lock = threading.Lock()
_PRUNE_AFTER = 3600.0


def is_ready(settings: Settings) -> bool:
    """Credentials are present. Says nothing about whether dialling is allowed."""
    return bool(settings.guava_api_key and settings.guava_agent_number)


def will_dial(settings: Settings) -> bool:
    """Whether a call placed right now would actually ring a phone."""
    return is_ready(settings) and settings.homeops_allow_real_calls


def suppression_reason(settings: Settings) -> str:
    """Why a call would not ring. Shown to the user, so keep it plain."""
    if not settings.guava_api_key:
        return "GUAVA_API_KEY is not set."
    if not settings.guava_agent_number:
        return "GUAVA_AGENT_NUMBER is not set."
    if not settings.homeops_allow_real_calls:
        return "HOMEOPS_ALLOW_REAL_CALLS is off."
    return "calling is disabled."


def target_number(settings: Settings, phone: str) -> str:
    """The number that will be dialled. No redirect - what you see is dialled.

    The dev/demo shop gets a reachable number from the mocked trade search
    (HOMEOPS_DEV_SHOP_PHONE), so nothing has to be rewritten here.
    """
    return to_e164(phone)


def ensure_configured(settings: Settings) -> None:
    if is_ready(settings) or settings.homeops_mock:
        return
    missing = "GUAVA_API_KEY" if not settings.guava_api_key else "GUAVA_AGENT_NUMBER"
    raise VendorNotConfigured("guava", missing)


def _cooldown_ok(number: str, window: int) -> bool:
    now = time.monotonic()
    with _recent_lock:
        for old in [n for n, t in _recent.items() if now - t > _PRUNE_AFTER]:
            del _recent[old]
        if now - _recent.get(number, 0.0) < window:
            return False
        _recent[number] = now
        return True


def place_call(
    settings: Settings,
    call_id: str,
    phone: str,
    brief: Any,
    shop_name: str = "",
) -> None:
    """Dial the shop on a background thread. Returns as soon as it is queued."""
    ensure_configured(settings)

    dial = target_number(settings, phone)
    logger.info("dialing %s for %s", dial, shop_name or "an unnamed shop")

    if not will_dial(settings):
        logger.error("REFUSING TO DIAL %s - %s", dial, suppression_reason(settings))
        store.update(call_id, state="done", mock=True,
                     summary=f"[MOCK] Call suppressed: "
                             f"{suppression_reason(settings)} No phone was dialed.")
        return

    if not _cooldown_ok(dial, settings.homeops_call_cooldown_seconds):
        logger.error("REFUSING TO DIAL %s - already called within %ss "
                     "(runaway-loop guard)", dial,
                     settings.homeops_call_cooldown_seconds)
        store.update(call_id, state="failed",
                     summary=f"Call suppressed: {dial} was already dialed in "
                             f"the last {settings.homeops_call_cooldown_seconds} "
                             f"seconds.")
        return

    variables = shop_call_vars(brief, settings.homeowner_name)
    variables["shop_name"] = shop_name
    variables["homeops_call_id"] = call_id

    threading.Thread(
        target=_run_call,
        args=(settings.guava_agent_number, dial, variables, call_id),
        name=f"guava-call-{call_id[:8]}",
        daemon=True,
    ).start()


def _run_call(
    from_number: str,
    to_number: str,
    variables: dict[str, str],
    call_id: str,
) -> None:
    # Imported here so the SDK only loads when a call is actually placed.
    from guava_agent.agent import agent

    try:
        agent.call_phone(from_number=from_number, to_number=to_number,
                         variables=variables)
    except Exception as exc:  # noqa: BLE001 - surface it in the UI, don't crash
        logger.exception("Guava call failed")
        store.update(call_id, state="failed",
                     summary=f"Guava could not place the call: {exc}")
