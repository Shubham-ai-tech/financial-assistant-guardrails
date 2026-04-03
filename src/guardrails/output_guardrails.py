"""Output guardrails: reduce unsafe guarantees and obvious hallucination cues."""

from __future__ import annotations

import re
from dataclasses import dataclass

_GUARANTEE = re.compile(
    r"\b(guaranteed\s+(return|profit)|risk-?free|sure\s+thing|will\s+definitely\s+go\s+up|"
    r"cannot\s+lose|no\s+risk)\b",
    re.I,
)

_PERSONALIZED_ILLEGAL = re.compile(
    r"\b(you\s+should\s+buy|you\s+must\s+sell|as\s+your\s+financial\s+advisor)\b",
    re.I,
)


@dataclass
class OutputGuardResult:
    allowed: bool
    text: str
    reason: str


_DISCLAIMER = (
    "\n\n*General information only - not personalized investment, tax, or legal advice.*"
)


def check_output(text: str) -> OutputGuardResult:
    """Soften unsafe phrasing and append disclaimer where needed."""
    raw = (text or "").strip()
    if not raw:
        return OutputGuardResult(
            False,
            "I could not produce a grounded answer. Try rephrasing or specify a ticker.",
            "empty",
        )

    if _GUARANTEE.search(raw):
        softened = _GUARANTEE.sub(
            "[removed strong guarantee language]",
            raw,
        )
        return OutputGuardResult(
            True,
            softened + _DISCLAIMER,
            "softened_guarantee_language",
        )

    if _PERSONALIZED_ILLEGAL.search(raw):
        softened = _PERSONALIZED_ILLEGAL.sub(
            "Consider discussing with a licensed professional:",
            raw,
        )
        return OutputGuardResult(
            True,
            softened + _DISCLAIMER,
            "softened_personalized_advice",
        )

    if _DISCLAIMER.strip() not in raw:
        return OutputGuardResult(True, raw + _DISCLAIMER, "appended_disclaimer")

    return OutputGuardResult(True, raw, "ok")
