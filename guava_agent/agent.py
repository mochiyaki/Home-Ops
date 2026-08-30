"""HomeOps shop-quote caller, on Guava.

Product rules: HomeOps books autonomously, but only when the quote fits the
homeowner's budget and availability — and gas / fire / uncontrolled flood
blocks the vendor call entirely.

    python -m guava_agent.agent --chat                  # terminal, no audio
    python -m guava_agent.agent --local                 # your mic/speakers
    python -m guava_agent.agent --phone +14155550123    # live outbound call
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
from pathlib import Path

import guava
from guava import logging_utils

from app.config import get_settings
from app.prompt import brief_text, is_danger, job_phrase, shop_call_vars
from app.services import exa
from app import store

logger = logging.getLogger("homeops.guava")

RESULT_PATH = Path("guava_agent/last_call.json")

agent = guava.Agent(
    name="Ops",
    organization="HomeOps",
    purpose=(
        "You are an AI house super calling a local trade shop on behalf of a "
        "homeowner. You are gathering a price quote and the soonest time they "
        "could come out, and you book the appointment on the call when the "
        "price fits the homeowner's budget and the time fits their "
        "availability."
    ),
)


def _vars(call: guava.Call) -> dict[str, str]:
    keys = (
        "homeowner", "address", "problem", "trade",
        "budget", "availability", "asset", "shop_name",
    )
    out = {}
    for key in keys:
        value = call.get_variable(key)
        out[key] = "" if value is None else str(value)
    return out


def _report(call: guava.Call, **fields) -> None:
    """Mirror live call state into the HomeOps store when driven by the app."""
    call_id = call.get_variable("homeops_call_id")
    if not call_id:
        return
    store.update(str(call_id), **fields)


def _quote_line(quote: str | None, window: str | None,
                booked: bool = False, appointment: str | None = None) -> str | None:
    parts = [p for p in (quote, window) if p]
    if not parts:
        return None
    tail = f"booked {appointment}" if booked and appointment else (
        "booked" if booked else "not booked")
    return " · ".join(str(p) for p in parts) + f" · {tail}"


def _notify_homeowner(call: guava.Call, result: dict) -> str:
    """Text the homeowner the outcome once the call wraps.

    Guava's messaging is SMS-only (no email); the send only works once SMS is
    provisioned on the agent number - until then the API returns 400 and we
    record why instead of failing the call handler.
    """
    settings = get_settings()
    to = (call.get_variable("homeowner_phone")
          or os.environ.get("HOMEOWNER_PHONE") or "").strip()
    from_number = (settings.guava_agent_number
                   or os.environ.get("GUAVA_AGENT_NUMBER") or "").strip()
    if not to:
        return "skipped: HOMEOWNER_PHONE not set"
    if not from_number:
        return "skipped: GUAVA_AGENT_NUMBER not set"

    shop = (result.get("shop") or "The shop").replace("[MOCK] ", "")
    if result.get("ended") == "voicemail":
        text = f"HomeOps: {shop} didn't pick up - left a voicemail asking for a callback."
    elif result.get("booked"):
        when = result.get("appointment") or result.get("earliest_window") or "time confirmed on the call"
        text = f"HomeOps: Booked - {shop}, {when}. Quote: {result.get('quote') or 'on the call'}."
    elif result.get("can_take_job") == "no":
        text = f"HomeOps: {shop} can't take the job. Trying the next shop."
    else:
        text = (f"HomeOps: {shop} quoted {result.get('quote') or 'no price'}, "
                f"soonest {result.get('earliest_window') or 'unstated'}. "
                "Not booked - it didn't fit the budget or availability.")

    try:
        guava.Client(api_key=settings.guava_api_key or None).send_sms(
            from_number=from_number, to_number=to, message=text)
        logger.info("post-call SMS sent to %s", to)
        return f"sent to {to}"
    except Exception as exc:  # noqa: BLE001 - a failed text never kills the call
        logger.warning("post-call SMS failed: %s", exc)
        return f"failed: {exc}"


@agent.on_call_start
def on_call_start(call: guava.Call) -> None:
    v = _vars(call)
    homeowner = v["homeowner"] or "the homeowner"
    job = job_phrase(v["trade"])

    call.set_persona(
        organization_name="HomeOps",
        agent_name="Ops",
        agent_purpose=(
            f"You are calling on behalf of {homeowner} about {job}. "
            "You are an AI house super and you say so if asked. You want a "
            "ballpark price and the soonest they could come out, and you book "
            "the visit on this call when the price fits the homeowner's "
            "budget and the time fits their availability."
        ),
    )

    call.set_voicemail_action(
        message=(
            f"Hi, this is HomeOps calling on behalf of {homeowner} for {job}. "
            f"The issue is {v['problem']}. Please call back with a quote and "
            "the soonest time you could come out. Thank you."
        )
    )

    call.add_info("job_brief", {k: val for k, val in v.items() if val})
    call.add_info(
        "homeops_rules",
        {
            "identity": "HomeOps, an AI house super, calling for a homeowner.",
            "booking": "Book when the quote is at or under the budget (or no "
                       "budget was given) and the time fits the homeowner's "
                       "availability: confirm the date and time under the "
                       "homeowner's name and address and ask the shop to put "
                       "it on their calendar. If it does not fit, take the "
                       "numbers and say the homeowner will follow up.",
            "budget": "Budget is the booking cap. Above it, still record the "
                      "quote — just do not book.",
            "money": "Never take a card number, deposit, or payment.",
            "invention": "Never invent prices, times, or shop policies.",
        },
    )

    call.set_task(
        "quote",
        objective=(
            f"Find out whether this shop can take {job} for {homeowner}, what "
            "it would roughly cost, and the soonest they could come out — and "
            "book the visit if the price fits the budget and the time fits "
            "the homeowner's availability."
        ),
        checklist=[
            "In one sentence, say you're calling from HomeOps on behalf of "
            f"{homeowner} about {v['problem'] or 'a household issue'}"
            + (f" at {v['address']}" if v["address"] else "")
            + ", and ask if they have a minute.",
            guava.Field(
                key="can_take_job",
                field_type="multiple_choice",
                choices=["yes", "no"],
                description=f"Can this shop take {job}?",
                question="Is that something you all take on?",
            ),
            "Ask about price and timing as two separate questions, never "
            "in the same breath. Wait for an answer before moving on.",
            guava.Field(
                key="quote",
                field_type="text",
                description=(
                    "Their ballpark price for the job, in dollars, exactly as "
                    "they said it. If they will only quote after seeing it, "
                    "record their trip or diagnostic fee instead."
                ),
                question="Any ballpark on what that runs?",
            ),
            guava.Field(
                key="earliest_window",
                field_type="text",
                description=(
                    "The soonest they could come out. Record the DAY and the "
                    "TIME together, e.g. 'Tuesday at 10am' or 'tomorrow at "
                    "8am' - a bare time with no day is incomplete. "
                    + (f"The homeowner is free {v['availability']}, so steer "
                       f"toward that, but take what they offer."
                       if v["availability"] else "")
                ),
                question="What's the soonest you could get out there?",
            ),
            guava.Field(
                key="callback_number",
                field_type="text",
                required=False,
                description="Best number for the homeowner to call back on, "
                            "if they offer one. Do not push for it.",
            ),
            guava.Field(
                key="booked",
                field_type="multiple_choice",
                choices=["yes", "no"],
                description=(
                    "Whether you booked the visit on this call. Book only if "
                    "the quote is at or under the budget"
                    + (f" ({v['budget']})" if v["budget"] else "")
                    + " — or no budget was given — and the window fits the "
                    "homeowner's availability. To book: confirm the date and "
                    "time under "
                    f"{homeowner}'s name"
                    + (f" at {v['address']}" if v["address"] else "")
                    + " and ask them to put it on their calendar."
                ),
                question="Can you go ahead and put us down for that time?",
            ),
            guava.Field(
                key="appointment",
                field_type="text",
                required=False,
                description=(
                    "The booked day and time exactly as confirmed, e.g. "
                    "'Tuesday at 10am'. Leave empty if nothing was booked."
                ),
            ),
            "If you booked, repeat the day, the time, and the homeowner's "
            "name back once so it is on both calendars. If you did not book, "
            "say the homeowner will follow up to confirm.",
        ],
        completion_criteria=(
            "Done once you know whether they can take the job and, if they "
            "can, you have a price and a timeframe and you have either booked "
            "the visit or established that it does not fit the budget or "
            "availability. If they cannot take it, or they are booked out "
            "indefinitely, that also completes the task."
        ),
    )
    _report(call, state="in-call", mock=False)


@agent.on_agent_speech
def on_agent_speech(call: guava.Call, event) -> None:
    """Live transcript. Written turn-by-turn so the UI can follow the call."""
    call_id = call.get_variable("homeops_call_id")
    if call_id:
        store.add_turn(str(call_id), "agent", getattr(event, "utterance", ""),
                       bool(getattr(event, "interrupted", False)))


@agent.on_caller_speech
def on_caller_speech(call: guava.Call, event) -> None:
    call_id = call.get_variable("homeops_call_id")
    if call_id:
        store.add_turn(str(call_id), "shop", getattr(event, "utterance", ""))


@agent.on_question
def on_question(call: guava.Call, question: str) -> str:
    """The shop asks something about the appliance — look up the real manual."""
    v = _vars(call)
    asset = v["asset"]
    if not asset:
        return ("I don't have that detail in front of me. I can get it from "
                "the homeowner and follow up.")

    query = f"{asset} {question}".strip()
    logger.info("on_question -> exa: %s", query)
    try:
        result = asyncio.run(exa.lookup_model(get_settings(), query))
    except Exception as exc:  # noqa: BLE001 - never kill the call over a lookup
        logger.warning("exa lookup failed: %s", exc)
        return (f"The unit is a {asset}. I don't have more than that on hand.")

    # Never read a [MOCK] fixture aloud to a real shop. No EXA_API_KEY means
    # we answer from the house record alone rather than inventing detail.
    if result.get("mock"):
        logger.info("exa unconfigured; answering from the house record only")
        return f"The unit is a {asset}. I don't have more than that on hand."

    summary = (result.get("summary") or "").strip()
    if not summary:
        return f"The unit is a {asset}. I don't have more than that on hand."
    return f"The unit is a {asset}. From the manual: {summary[:400]}"


def _capture(call: guava.Call, *, reason: str = "") -> dict:
    """Read whatever the checklist collected. Safe to call at any point."""
    result = {
        "shop": _vars(call)["shop_name"],
        "can_take_job": call.get_field("can_take_job"),
        "quote": call.get_field("quote"),
        "earliest_window": call.get_field("earliest_window"),
        "callback_number": call.get_field("callback_number"),
        "booked": call.get_field("booked") == "yes",
        "appointment": call.get_field("appointment"),
    }
    if reason:
        result["ended"] = reason
    RESULT_PATH.write_text(json.dumps(result, indent=2))
    return result


def _summarize(result: dict) -> str:
    shop = result["shop"] or "The shop"
    if result["can_take_job"] == "no":
        return f"{shop} cannot take this job."
    if not result["quote"] and not result["earliest_window"]:
        return f"{shop} did not give a quote before the call ended."
    if result["booked"]:
        when = result["appointment"] or result["earliest_window"] or "a time"
        return (
            f"{shop} quoted {result['quote'] or 'no price'} and is booked "
            f"for {when}."
        )
    return (
        f"{shop} quoted {result['quote'] or 'no price'}, soonest "
        f"{result['earliest_window'] or 'unstated'}. "
        "Not booked - it did not fit the budget or availability."
    )


@agent.on_task_complete("quote")
def on_quote(call: guava.Call) -> None:
    result = _capture(call)
    logger.info("quote captured: %s", result)
    result["sms"] = _notify_homeowner(call, result)
    _report(
        call,
        state="done",
        summary=_summarize(result),
        quote=_quote_line(result["quote"], result["earliest_window"],
                          result["booked"], result["appointment"]),
        fields=result,
        booked=result["booked"],
        mock=False,
    )

    if result["can_take_job"] == "no":
        call.hangup("Thank them for their time and say goodbye.")
        return

    if result["booked"]:
        call.hangup(
            "Confirm the booked day and time once more, thank them, and say "
            "goodbye."
        )
        return

    call.hangup(
        "Read back the price and the timeframe once, say the homeowner will "
        "follow up to confirm, thank them, and say goodbye."
    )


@agent.on_session_end
def on_session_end(call: guava.Call, event) -> None:
    """Shops hang up abruptly. Never lose a quote we already have."""
    reason = getattr(event, "termination_reason", "?")
    logger.info("call ended: %s", reason)

    result = _capture(call, reason=reason)
    logger.info("captured at session end: %s", result)

    call_id = call.get_variable("homeops_call_id")
    if not call_id:
        return
    record = store.get(str(call_id))
    if record and record.get("state") == "done":
        return  # on_task_complete already wrote the good version

    if reason == "voicemail":
        summary = "Reached voicemail. Left a callback request. Nothing booked."
    elif result["quote"] or result["earliest_window"]:
        summary = _summarize(result) + f" (call ended early: {reason})"
    else:
        summary = f"Call ended before a quote came back ({reason})."

    result["sms"] = _notify_homeowner(call, result)

    _report(
        call,
        state="done",
        summary=summary,
        quote=_quote_line(result["quote"], result["earliest_window"],
                          result["booked"], result["appointment"]),
        fields=result,
        termination_reason=reason,
        booked=result["booked"],
        mock=False,
    )


DEFAULT_BRIEF = {
    "homeowner": os.environ.get("HOMEOWNER_NAME") or "Jordan Chen",
    "address": "1200 Folsom Street, San Francisco",
    "problem": "the dishwasher is leaking under the kitchen sink",
    "trade": "plumber",
    "budget": "around three hundred dollars",
    "availability": "weekday mornings",
    "asset": "Bosch SHPM88 dishwasher",
}


def main() -> None:
    logging_utils.configure_logging()

    parser = argparse.ArgumentParser(description="HomeOps shop-quote caller")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--chat", action="store_true", help="terminal chat")
    mode.add_argument("--local", action="store_true", help="local audio device")
    mode.add_argument("--phone", metavar="E164", help="place a live call")
    parser.add_argument("--shop", default="the shop", help="shop name")
    parser.add_argument("--problem", default=DEFAULT_BRIEF["problem"])
    parser.add_argument("--trade", default=DEFAULT_BRIEF["trade"])
    parser.add_argument("--homeowner", default=DEFAULT_BRIEF["homeowner"])
    args = parser.parse_args()

    brief = dict(DEFAULT_BRIEF)
    brief.update(
        problem=args.problem, trade=args.trade, homeowner=args.homeowner
    )

    # Product rule: gas, fire, or uncontrolled flood never becomes a vendor call.
    if is_danger(brief_text(brief)):
        raise SystemExit(
            "BLOCKED: gas, fire, or uncontrolled flood. Tell the homeowner to "
            "call emergency services. HomeOps does not call a vendor for this."
        )

    variables = shop_call_vars(brief)
    variables["shop_name"] = args.shop

    if args.chat:
        agent.chat(variables=variables)
    elif args.local:
        agent.call_local(variables=variables)
    else:
        from_number = os.environ.get("GUAVA_AGENT_NUMBER")
        if not from_number:
            raise SystemExit("Set GUAVA_AGENT_NUMBER to your Guava number.")
        agent.call_phone(
            from_number=from_number,
            to_number=args.phone,
            variables=variables,
        )


if __name__ == "__main__":
    main()
