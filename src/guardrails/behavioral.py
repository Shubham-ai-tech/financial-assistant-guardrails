"""Behavioral guardrails: finance-only scope and refusal templates."""

from __future__ import annotations

import re

_NON_FINANCE_STRONG = re.compile(
    r"\b(recipe|poem|essay|python\s+code|write\s+a\s+virus|who\s+won\s+the\s+world\s+cup)\b",
    re.I,
)


def behavioral_check(user_query: str, draft_answer: str) -> str:
    """Last-chance domain enforcement (normally input guard catches this)."""
    u = user_query or ""
    if _NON_FINANCE_STRONG.search(u):
        return (
            "I only answer finance-related questions in this demo. "
            "Ask about tickers, definitions, or market concepts."
        )
    return draft_answer
