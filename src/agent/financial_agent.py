"""LangGraph ReAct agent for finance Q&A using tools."""

from __future__ import annotations

import os
import time
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_mistralai import ChatMistralAI
from langgraph.errors import GraphRecursionError
from langgraph.prebuilt import create_react_agent

from src.tools.finance_tools import TOOLS

_SYSTEM = """You are a Financial Assistant for education and information only.

Reasoning: Think step by step—decide which tools to call, interpret tool outputs, and avoid inventing numbers.
- For prices, returns, or company facts, you MUST use the provided tools (get_stock_quote, get_price_history_summary).
- For definitions (e.g. diversification), prefer search_finance_faq when relevant.
- For arithmetic (percentages, ratios), use calculate.
- Be efficient: for a single ticker, prefer one get_stock_quote unless the user clearly needs history too; avoid redundant tool calls.

Policies:
- Do not give personalized investment, tax, or legal advice. Offer general factors to consider and suggest licensed professionals for personal decisions.
- Never guarantee returns or claim an investment is risk-free.
- If data is missing from tools, say you cannot see it instead of guessing.

Always ground numerical claims in tool output."""


def _get_mistral_api_key() -> str:
    key = (os.getenv("MISTRAL_API_KEY") or "").strip()
    if not key:
        raise RuntimeError(
            "MISTRAL_API_KEY is missing. Copy .env.example to `.env` and add your key "
            "from https://console.mistral.ai/"
        )
    return key


def _get_llm() -> ChatMistralAI:
    model = os.getenv("MISTRAL_MODEL", "mistral-small-latest")
    max_retries = max(1, int(os.getenv("MISTRAL_SDK_MAX_RETRIES", "2")))
    return ChatMistralAI(
        model=model,
        temperature=0.2,
        api_key=_get_mistral_api_key(),
        max_retries=max_retries,
    )


def _build_graph():
    llm = _get_llm()
    return create_react_agent(llm, TOOLS, prompt=SystemMessage(content=_SYSTEM))


_compiled: Any = None


def _get_compiled():
    global _compiled
    if _compiled is None:
        _compiled = _build_graph()
    return _compiled


def _is_rate_limit_error(exc: BaseException) -> bool:
    msg = str(exc).lower()
    full = str(exc)
    if "429" in full or "too many requests" in msg:
        return True
    if "resource exhausted" in msg or "resourceexhausted" in msg.replace(" ", ""):
        return True
    if "quota" in msg and ("exceed" in msg or "limit" in msg):
        return True
    if "rate limit" in msg:
        return True
    return False


def _is_auth_error(exc: BaseException) -> bool:
    msg = str(exc).lower()
    full = str(exc)
    if "401" in full or "403" in full:
        return True
    if "api key" in msg and ("invalid" in msg or "permission" in msg):
        return True
    if "unauthorized" in msg:
        return True
    return False


def run_financial_agent(user_message: str) -> str:
    """Run the agent with bounded steps and retries on transient API 429s."""
    g = _get_compiled()

    recursion_limit = max(6, int(os.getenv("AGENT_RECURSION_LIMIT", "12")))
    max_rounds = max(1, int(os.getenv("LLM_INVOKE_RETRIES", "5")))
    base_delay = float(os.getenv("LLM_RETRY_BASE_SEC", "3.0"))

    config: dict[str, Any] = {"recursion_limit": recursion_limit}

    payload = {
        "messages": [
            HumanMessage(content=user_message.strip()),
        ]
    }

    result: dict[str, Any] | None = None
    for attempt in range(max_rounds):
        try:
            result = g.invoke(payload, config=config)
            break
        except GraphRecursionError:
            return (
                "This question used too many agent steps (tool/model turns). "
                "Try a shorter question or one ticker at a time. "
                "You can raise AGENT_RECURSION_LIMIT in `.env` slightly if needed."
            )
        except Exception as e:
            if _is_auth_error(e):
                return (
                    "Invalid or missing Mistral API key. Set MISTRAL_API_KEY in `.env` "
                    "(see https://console.mistral.ai/)."
                )
            if _is_rate_limit_error(e) and attempt < max_rounds - 1:
                time.sleep(base_delay * (2**attempt))
                continue
            if _is_rate_limit_error(e):
                return (
                    "The Mistral API is still rate-limiting after retries (HTTP 429). "
                    "Wait several minutes, try again later, or check your plan and usage "
                    "at https://console.mistral.ai/. "
                    "Tip: each answer uses multiple model calls."
                )
            return f"Agent error: {e!s}"

    if result is None:
        return "Unexpected: no result from agent."

    messages = result.get("messages") or []
    last = messages[-1] if messages else None
    if isinstance(last, AIMessage):
        return (last.content or "").strip()
    if last is not None and hasattr(last, "content"):
        return str(last.content or "").strip()
    return str(result)
