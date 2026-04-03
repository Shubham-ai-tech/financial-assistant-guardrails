"""Input guardrails: prompt injection and off-topic / harmful patterns."""

from __future__ import annotations

import re
from dataclasses import dataclass

_INJECTION_PATTERNS = [
    re.compile(p, re.I)
    for p in [
        r"ignore\s+(all\s+)?(previous|prior|above)\s+instructions",
        r"disregard\s+(the\s+)?(system|developer)\s+message",
        r"you\s+are\s+now\s+(a|an)\s+",
        r"new\s+instructions\s*:",
        r"jailbreak",
        r"system\s+prompt",
        r"reveal\s+(your\s+)?(hidden|secret)\s+",
        r"<\|.*\|>",  # pseudo special tokens
    ]
]

_FINANCE_HINTS = re.compile(
    r"\b(stock|ticker|share|price|invest|portfolio|dividend|market|cap|etf|equity|"
    r"finance|financial|yahoo|return|volatility|interest|loan|mortgage|budget|savings|"
    r"inflation|gdp|recession|bond|yield|forex|crypto|bitcoin|btc|ethereum|eth|"
    r"should\s+i\s+invest|buy|sell|hold)\b",
    re.I,
)

_HARMFUL = re.compile(
    r"\b(kill|bomb|hack\s+into|steal\s+(password|money)|money\s+laundering|"
    r"evade\s+tax|insider\s+trading\s+tip)\b",
    re.I,
)


@dataclass
class InputGuardResult:
    allowed: bool
    reason: str


def check_input(text: str) -> InputGuardResult:
    """Block prompt injection, harmful finance-adjacent abuse, and clearly non-finance queries."""
    t = (text or "").strip()
    if len(t) < 2:
        return InputGuardResult(False, "Please ask a clearer question.")

    for rx in _INJECTION_PATTERNS:
        if rx.search(t):
            return InputGuardResult(
                False,
                "This request looks like an attempt to override assistant instructions. "
                "Ask a straightforward finance question instead.",
            )

    if _HARMFUL.search(t):
        return InputGuardResult(
            False,
            "I cannot help with harmful or illegal activities, including abusive financial misconduct.",
        )

    _off_topic = re.compile(
        r"\b(weather|recipe|sports\s+score|movie|song|poem|homework\s+essay)\b",
        re.I,
    )
    if _off_topic.search(t) and not _FINANCE_HINTS.search(t):
        return InputGuardResult(
            False,
            "This assistant only handles finance-related questions. Rephrase with a finance angle.",
        )

    if not _FINANCE_HINTS.search(t) and len(t) > 60:
        return InputGuardResult(
            False,
            "This assistant only handles finance-related questions (markets, definitions, data lookups). "
            "Rephrase with a finance angle.",
        )

    if len(t) > 8000:
        return InputGuardResult(False, "Message too long; shorten your question.")

    return InputGuardResult(True, "ok")
