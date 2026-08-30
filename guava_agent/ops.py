"""Ops — the homeowner-facing HomeOps agent, on Guava WebRTC.

The other half of the product. The homeowner talks to Ops in the browser;
Ops triages the problem, finds local trades, and asks the shop-caller agent
to go get a quote. Same two product rules: Ops never books, and gas / fire /
uncontrolled flood stops the vendor call in favour of emergency services.

    python -m guava_agent.ops --chat     # terminal
    python -m guava_agent.ops --web      # serve the browser widget
"""

from __future__ import annotations

import argparse
import json
import logging
import os

import guava
import httpx
from guava import logging_utils

from app.config import get_settings  # also loads .env
from app.prompt import is_danger

logger = logging.getLogger("homeops.ops")

API = os.environ.get("HOMEOPS_API", "http://localhost:8000")

# Fallback only. The live record comes from GET /api/house so Ops and the
# homeowner are looking at the same house.
FALLBACK_HOUSE = {
    "address": "1428 Folsom St, San Francisco, CA",
    "homeowner": "the homeowner",
    "assets": [],
}


def load_house() -> dict:
    try:
        res = httpx.get(f"{API}/api/house", timeout=10.0)
        res.raise_for_status()
        return res.json()
    except Exception as exc:  # noqa: BLE001
        logger.warning("house load failed (%s); using fallback", exc)
        return dict(FALLBACK_HOUSE)


def house_snapshot(house: dict) -> str:
    try:
        res = httpx.get(f"{API}/api/house/snapshot", timeout=10.0)
        res.raise_for_status()
        return res.json().get("snapshot", "")
    except Exception:  # noqa: BLE001
        return str(house)

agent = guava.Agent(
    name="Ops",
    organization="HomeOps",
    purpose=(
        "You are the homeowner's AI house super. You know this house. You "
        "triage what broke, find a local trade, and get a quote by phone. "
        "You never book an appointment - the homeowner always decides."
    ),
)


@agent.on_call_start
def on_call_start(call: guava.Call) -> None:
    call.set_persona(
        organization_name="HomeOps",
        agent_name="Ops",
        agent_purpose=(
            "You are Ops, the homeowner's house super. Warm, calm, slightly "
            "dry - like a good super who already has the keys. Short turns, "
            "one question at a time."
        ),
    )
    house = load_house()
    call.set_variable("house_address", house.get("address", ""))
    call.add_info("house_record", house_snapshot(house))
    call.add_info(
        "rules",
        {
            "booking": "You never book, schedule, or confirm an appointment. "
                       "You gather quotes; the homeowner decides.",
            "danger": "Gas leak, carbon monoxide, fire, or water they cannot "
                      "stop: tell them to call emergency services and do NOT "
                      "call a vendor.",
            "honesty": "Never invent serials, warranties, quotes, or shop "
                       "names. Use the house record.",
        },
    )
    call.set_task(
        "triage",
        objective=(
            "Find out what is going on at the house. If they are just asking "
            "a question about the house, answer it from the house record - "
            "you do not need this checklist. Only work the checklist when "
            "something is actually broken or needs a trade."
        ),
        checklist=[
            guava.Field(
                key="problem",
                description="What is wrong, in the homeowner's own words.",
                question="What's going on at the house?",
            ),
            guava.Field(
                key="trade",
                field_type="multiple_choice",
                choices=["plumber", "appliance repair", "hvac",
                         "handyman", "contractor"],
                description="Which trade this needs, inferred from the "
                            "problem. Do not ask the homeowner to pick a "
                            "trade - work it out yourself.",
            ),
            guava.Field(
                key="budget",
                required=False,
                description="Rough budget, if they mention one. Ask once, "
                            "then move on. Do not push.",
            ),
            guava.Field(
                key="availability",
                required=False,
                description="When someone could come by. Ask once, then "
                            "move on.",
            ),
        ],
    )


@agent.on_question
def on_question(call: guava.Call, question: str) -> str:
    """House questions answered from the record, never guessed."""
    logger.info("house question: %s", question)
    return (
        "Answer only from this house record: "
        f"{house_snapshot(load_house())}. "
        "If the answer is not in there, say it is not on file and offer to "
        "save it when they tell you."
    )


@agent.on_task_complete("triage")
def on_triaged(call: guava.Call) -> None:
    problem = str(call.get_field("problem") or "")
    trade = str(call.get_field("trade") or "plumber")

    if is_danger(problem):
        logger.warning("DANGER BLOCKED: %s", problem)
        call.send_instruction(
            "This is a gas, fire, or uncontrolled water emergency. Tell them "
            "plainly to call emergency services right now. Do NOT offer to "
            "find or call a contractor. Stay on and be calm."
        )
        return

    try:
        res = httpx.post(
            f"{API}/api/tools/providers",
            json={"trade": trade,
                  "address": call.get_variable("house_address") or ""},
            timeout=20.0,
        )
        res.raise_for_status()
        providers = res.json().get("providers", [])
    except Exception as exc:  # noqa: BLE001
        logger.exception("provider lookup failed")
        call.send_instruction(
            f"Tell them the shop lookup failed ({exc}). Offer to try again."
        )
        return

    if not providers:
        call.send_instruction("Tell them no shops came back, and ask if they "
                              "want to try a different trade.")
        return

    call.add_info("shops_found", providers)
    names = [p["name"] for p in providers]
    call.set_variable("providers_json", json.dumps(providers))

    call.set_task(
        "choose_shop",
        objective=(
            "Read back the shops you found by name and rating, then ask "
            "which one to call for a quote. Make clear you are only getting "
            "a price - you will not book anything."
        ),
        checklist=[
            guava.Field(
                key="chosen_shop",
                field_type="multiple_choice",
                choices=names,
                description="Which shop the homeowner wants called.",
            ),
        ],
    )


@agent.on_task_complete("choose_shop")
def on_chosen(call: guava.Call) -> None:
    chosen = str(call.get_field("chosen_shop") or "")
    raw = call.get_variable("providers_json") or "[]"
    try:
        providers = json.loads(raw)
    except (TypeError, ValueError):
        logger.warning("could not parse the shop shortlist: %r", raw)
        providers = []

    shop = next((p for p in providers if p.get("name") == chosen), None)
    if not shop:
        call.send_instruction("Tell them you could not match that shop and "
                              "ask them to pick one of the ones you listed.")
        return

    brief = {
        "address": call.get_variable("house_address") or "",
        "homeowner": get_settings().homeowner_name or "the homeowner",
        "problem": str(call.get_field("problem") or ""),
        "trade": str(call.get_field("trade") or ""),
        "budget": str(call.get_field("budget") or ""),
        "availability": str(call.get_field("availability") or ""),
        "do_not_book": True,
    }

    try:
        res = httpx.post(
            f"{API}/api/tools/call",
            json={"phone": shop["phone"], "brief": brief,
                  "shop_name": shop["name"]},
            timeout=30.0,
        )
        if res.status_code == 409:
            call.send_instruction(
                "Tell them this is an emergency and you will not call a "
                "vendor - they should call emergency services."
            )
            return
        if res.status_code == 429:
            call.send_instruction(
                "Tell them you have already called three shops, and ask if "
                "they want you to try one more."
            )
            return
        res.raise_for_status()
    except Exception as exc:  # noqa: BLE001
        logger.exception("call_shop failed")
        call.send_instruction(f"Tell them the call could not be placed ({exc}).")
        return

    logger.info("dialing %s at %s", shop["name"], shop["phone"])
    call.send_instruction(
        f"Tell them you're calling {shop['name']} right now for a quote "
        "only, that you will not book anything, and that you'll come back "
        "with the price and the timing once you have it."
    )


def main() -> None:
    logging_utils.configure_logging()
    parser = argparse.ArgumentParser(description="HomeOps Ops agent")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--chat", action="store_true")
    mode.add_argument("--local", action="store_true")
    mode.add_argument("--web", action="store_true", help="serve the widget")
    args = parser.parse_args()

    if args.chat:
        agent.chat()
    elif args.local:
        agent.call_local()
    else:
        code = get_settings().guava_webrtc_code
        if not code:
            raise SystemExit("Set GUAVA_WEBRTC_CODE (run: guava widget)")
        print(f"\n  Ops is live on WebRTC code {code}")
        print(f"  Open the app at {API} and press the mic.\n")
        agent.listen_webrtc(code)


if __name__ == "__main__":
    main()
