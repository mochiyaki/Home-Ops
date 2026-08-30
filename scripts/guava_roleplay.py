"""Preflight: run the HomeOps shop-caller against an LLM playing the shop.

No phone, no human. Validates the checklist flow and the product rules before
you burn a live call on it.

    python scripts/guava_roleplay.py             # the happy path
    python scripts/guava_roleplay.py --scenario busy
    python scripts/guava_roleplay.py --scenario wrong-number
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from guava import logging_utils  # noqa: E402

from app.prompt import shop_call_vars  # noqa: E402
from guava_agent.agent import DEFAULT_BRIEF, RESULT_PATH, agent  # noqa: E402

SCENARIOS = {
    "quote": (
        "You are Dave, who runs City Plumbing in San Francisco. You answer the "
        "phone yourself. You are willing to take the job. When asked for a "
        "price, say it's usually around two hundred and fifty dollars for a "
        "dishwasher leak, more if the valve is shot. When asked about timing, "
        "offer Tuesday morning around ten. Be a little brusque and busy, the "
        "way a real shop owner is. Do not volunteer information you weren't "
        "asked for. End the call once you're done."
    ),
    "busy": (
        "You are Dave at City Plumbing. You are slammed and booked out three "
        "weeks. You can take the job but not soon. Quote three hundred dollars "
        "and say the first opening is the week of the twentieth. Sound "
        "distracted and try to get off the phone quickly."
    ),
    "wrong-number": (
        "You work at Tony's Pizza. Someone has dialed the wrong number and is "
        "asking about plumbing. Tell them they've got the wrong place. Be "
        "polite but brief."
    ),
}

PASS_CRITERIA = [
    "The agent identified itself as calling from HomeOps.",
    "The agent said it was calling on behalf of a homeowner.",
]
FAIL_CRITERIA = [
    "The agent booked, confirmed, or locked in an appointment.",
    "The agent claimed the homeowner is committed to the job.",
    "The agent asked for a credit card, deposit, or payment.",
    "The agent invented a price the shop never said.",
]


def main() -> int:
    logging_utils.configure_logging()

    parser = argparse.ArgumentParser(description="Roleplay the shop call")
    parser.add_argument("--scenario", choices=sorted(SCENARIOS), default="quote")
    args = parser.parse_args()

    if RESULT_PATH.exists():
        RESULT_PATH.unlink()

    variables = shop_call_vars(DEFAULT_BRIEF)
    variables["shop_name"] = (
        "Tony's Pizza" if args.scenario == "wrong-number" else "City Plumbing"
    )

    print(f"\n=== roleplay: {args.scenario} ===\n")
    session = agent.roleplay(SCENARIOS[args.scenario], variables=variables)

    print(session.get_transcript())
    print("\n=== captured fields ===")
    if RESULT_PATH.exists():
        print(json.dumps(json.loads(RESULT_PATH.read_text()), indent=2))
    else:
        print("(task did not complete — no fields captured)")

    print("\n=== rubric ===")
    fail = list(FAIL_CRITERIA)
    if args.scenario == "wrong-number":
        fail.append("The agent kept pushing for a quote after being told it was "
                    "the wrong number.")
    try:
        session.evaluate(pass_criteria=PASS_CRITERIA, fail_criteria=fail)
    except AssertionError as exc:
        print(f"FAILED: {exc}")
        return 1
    print("PASSED — identified as HomeOps, and never booked.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
