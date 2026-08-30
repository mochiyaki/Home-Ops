"""Minting the in-app Ops voice session."""

from __future__ import annotations

from app.config import Settings
from app.errors import VendorNotConfigured
from app.prompt import ops_first_message


def web_session(settings: Settings, house_snapshot: str = "") -> dict:
    """Ops runs on Guava WebRTC.

    The agent itself is served by `python -m guava_agent.ops --web`; this only
    hands the browser the widget code. Without a code we fall back to the
    browser's own speech APIs, which is a degraded but working path, not an
    error.
    """
    first = ops_first_message()
    if settings.guava_webrtc_code:
        return {
            "mode": "guava",
            "mock": False,
            "webrtc_code": settings.guava_webrtc_code,
            "first_message": first,
        }
    if settings.homeops_mock:
        return {
            "mode": "browser",
            "mock": True,
            "webrtc_code": "",
            "first_message": first,
        }
    raise VendorNotConfigured("guava", "GUAVA_WEBRTC_CODE")
