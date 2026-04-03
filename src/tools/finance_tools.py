"""LangChain tools: Yahoo Finance (yfinance), safe calculator, FAQ retrieval."""

from __future__ import annotations

import ast
import json
import operator
import re
from pathlib import Path
from typing import Any

import yfinance as yf
from langchain_core.tools import tool

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_FAQ_PATH = _PROJECT_ROOT / "data" / "finance_faq.json"


def _load_faq() -> list[dict[str, Any]]:
    if not _FAQ_PATH.exists():
        return []
    with open(_FAQ_PATH, encoding="utf-8") as f:
        return json.load(f)


def _safe_calc(expression: str) -> float:
    """Evaluate + - * / and parentheses on numbers only (no names, no calls)."""

    allowed = set("0123456789+-*/(). eE")
    if not expression or any(c not in allowed for c in expression.replace(" ", "")):
        raise ValueError("Expression contains disallowed characters.")

    node = ast.parse(expression, mode="eval")

    def _eval(n: ast.expr) -> float:
        if isinstance(n, ast.Constant):
            if isinstance(n.value, (int, float)):
                return float(n.value)
            raise ValueError("Only numeric constants are allowed.")
        if isinstance(n, ast.UnaryOp) and isinstance(n.op, (ast.UAdd, ast.USub)):
            v = _eval(n.operand)
            return v if isinstance(n.op, ast.UAdd) else -v
        if isinstance(n, ast.BinOp) and isinstance(n.op, (ast.Add, ast.Sub, ast.Mult, ast.Div)):
            left, right = _eval(n.left), _eval(n.right)
            ops = {
                ast.Add: operator.add,
                ast.Sub: operator.sub,
                ast.Mult: operator.mul,
                ast.Div: operator.truediv,
            }
            return ops[type(n.op)](left, right)
        raise ValueError("Unsupported expression.")

    return _eval(node.body)


@tool
def get_stock_quote(ticker: str) -> str:
    """Fetch latest quote and key stats for a stock ticker (e.g. AAPL, MSFT). Use for current price and company name."""
    t = ticker.strip().upper()
    if not re.fullmatch(r"[A-Z]{1,5}", t):
        return "Invalid ticker format. Use 1-5 letters (e.g. AAPL)."
    try:
        stock = yf.Ticker(t)
        info = stock.info or {}
        hist = stock.history(period="5d")
        last = None
        if hist is not None and not hist.empty:
            last = float(hist["Close"].iloc[-1])
        name = info.get("shortName") or info.get("longName") or t
        currency = info.get("currency") or "USD"
        parts = [f"Ticker: {t}", f"Name: {name}"]
        if last is not None:
            parts.append(f"Recent close (approx): {last:.4f} {currency}")
        market_cap = info.get("marketCap")
        if market_cap:
            parts.append(f"Market cap (if available): {market_cap}")
        return "\n".join(parts)
    except Exception as e:  # noqa: BLE001 — tool must return string, not raise
        return f"Could not fetch data for {t}: {e!s}. Try another ticker or retry later."


@tool
def get_price_history_summary(ticker: str, period: str = "3mo") -> str:
    """Summarize historical closes for a ticker. period: 1d,5d,1mo,3mo,6mo,1y,2y,5y,ytd,max."""
    t = ticker.strip().upper()
    allowed_periods = {"1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "ytd", "max"}
    p = period.strip().lower() if period else "3mo"
    if p not in allowed_periods:
        p = "3mo"
    if not re.fullmatch(r"[A-Z]{1,5}", t):
        return "Invalid ticker format."
    try:
        hist = yf.Ticker(t).history(period=p)
        if hist is None or hist.empty:
            return f"No history returned for {t} (period={p})."
        closes = hist["Close"].astype(float)
        ret = (closes.iloc[-1] / closes.iloc[0] - 1.0) * 100.0
        vol = closes.pct_change().std() * 100.0
        return (
            f"{t} period={p}: start_close≈{closes.iloc[0]:.4f}, end_close≈{closes.iloc[-1]:.4f}, "
            f"approx total return≈{ret:.2f}%, simple vol of daily returns≈{vol:.2f}% (historical, not predictive)."
        )
    except Exception as e:  # noqa: BLE001
        return f"History error for {t}: {e!s}"


@tool
def calculate(expression: str) -> str:
    """Evaluate a safe arithmetic expression with + - * / and parentheses. Example: (1 + 0.07) ** 10 — not supported; use only + - * /."""
    expr = expression.strip()
    try:
        # Disallow ** for simplicity in ast walker; user can use repeated multiply
        if "**" in expr or "//" in expr:
            return "Only +, -, *, / and parentheses are supported in this tool."
        val = _safe_calc(expr)
        return f"Result: {val}"
    except Exception as e:  # noqa: BLE001
        return f"Could not calculate: {e!s}"


@tool
def search_finance_faq(query: str) -> str:
    """Search internal finance FAQ for definitions (diversification, volatility, dividends, market cap). Use for conceptual questions."""
    q = query.lower()
    rows = _load_faq()
    if not rows:
        return "FAQ database not available."
    scored: list[tuple[int, dict[str, Any]]] = []
    for row in rows:
        text = f"{row.get('question', '')} {row.get('topic', '')} {row.get('answer', '')}".lower()
        score = sum(1 for word in re.findall(r"[a-z]+", q) if len(word) > 2 and word in text)
        if score > 0:
            scored.append((score, row))
    scored.sort(key=lambda x: -x[0])
    if not scored:
        return "No matching FAQ entries. Answer from general finance knowledge only if consistent with disclaimers."
    out = []
    for _, row in scored[:3]:
        out.append(f"[{row['id']}] Q: {row['question']}\nA: {row['answer']}")
    return "\n\n".join(out)


TOOLS = [
    get_stock_quote,
    get_price_history_summary,
    calculate,
    search_finance_faq,
]
