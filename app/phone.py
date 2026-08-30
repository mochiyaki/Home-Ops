"""Phone-number normalization, shared by every call adapter."""

from __future__ import annotations

import re


def to_e164(phone: str) -> str:
    digits = re.sub(r"\D", "", phone or "")
    if len(digits) == 10:
        return "+1" + digits
    if len(digits) == 11 and digits.startswith("1"):
        return "+" + digits
    if digits:
        return "+" + digits
    return phone
