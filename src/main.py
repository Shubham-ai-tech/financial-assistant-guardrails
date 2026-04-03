"""CLI entry: input guardrails → LangGraph agent → behavioral + output guardrails."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(_PROJECT_ROOT / ".env")
load_dotenv()  # cwd fallback

from src.agent.financial_agent import run_financial_agent
from src.guardrails import behavioral_check, check_input, check_output


def run_pipeline(user_query: str) -> str:
    ing = check_input(user_query)
    if not ing.allowed:
        return ing.reason

    mistral = (os.getenv("MISTRAL_API_KEY") or "").strip()
    if not mistral:
        env_path = _PROJECT_ROOT / ".env"
        hint = ""
        if not env_path.is_file():
            hint = (
                " No `.env` file found in the project folder. Copy `.env.example` "
                "to a new file named `.env` (same directory), then put your key there."
            )
        return (
            "LLM is not configured: set MISTRAL_API_KEY in `.env`. "
            "Get a key at https://console.mistral.ai/" + hint
        )

    draft = run_financial_agent(user_query)
    draft = behavioral_check(user_query, draft)
    out = check_output(draft)
    return out.text if out.allowed else out.text


def main() -> None:
    parser = argparse.ArgumentParser(description="Financial Assistant (LangChain + guardrails)")
    parser.add_argument("query", nargs="*", help="Question (or use interactive mode with no args)")
    parser.add_argument("-i", "--interactive", action="store_true", help="REPL mode")
    args = parser.parse_args()

    if args.interactive or not args.query:
        print("Financial Assistant — type 'quit' to exit.\n")
        while True:
            try:
                line = input("You: ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                break
            if not line or line.lower() in {"quit", "exit", "q"}:
                break
            print("Assistant:", run_pipeline(line), "\n")
        return

    print(run_pipeline(" ".join(args.query)))


if __name__ == "__main__":
    main()
    sys.exit(0)
