"""Playwright stub entrypoint for IRCTC browser automation.

This file is intentionally lightweight. It gives future automation work a
stable script location that the API can reference.
"""


def run() -> dict[str, str]:
    return {
        "provider": "IRCTC",
        "status": "stub",
        "message": "Implement Playwright browser steps for IRCTC search, traveller details, OTP pause, and payment handoff.",
    }
