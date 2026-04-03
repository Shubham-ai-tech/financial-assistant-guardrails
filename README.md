# Financial Assistant with Guardrails

Educational **LLM agent** (LangChain + LangGraph) that answers finance questions using **Yahoo Finance data** (`yfinance`), a **safe calculator**, and a small **FAQ retrieval** layer. Includes **input**, **output**, and **behavioral** guardrails.

## Features

- **Agent**: LangGraph `create_react_agent` with tools for quotes, historical summaries, math, and FAQ search.
- **Data**: Live market data via `yfinance` (unofficial; fine for demos).
- **Guardrails**: Prompt-injection / off-topic detection, output softening for risky claims, disclaimers, finance-only behavior.

## Setup

1. **Python 3.10+**

2. Create a virtual environment and install dependencies:

```bash
cd uptqi
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

3. Configure the API key (use a file named **`.env`**, not only `.env.example`):

```bash
copy .env.example .env
```

Edit **`.env`** and set **`MISTRAL_API_KEY`** from [Mistral AI Console](https://console.mistral.ai/). Optionally set **`MISTRAL_MODEL`** (default: `mistral-small-latest`). Never commit `.env` to git.

**Rate limits / 429:** Mistral enforces per-plan limits. This app uses **several** model calls per question (ReAct agent). If you hit `429`, wait and retry, or lower `AGENT_RECURSION_LIMIT` in `.env`. The agent **retries with backoff** on rate limits.

### Always use the project virtualenv

Use the venv’s Python so dependencies (`langgraph`, etc.) resolve:

**Windows (PowerShell):**

```powershell
cd uptqi
.\.venv\Scripts\Activate.ps1
$env:PYTHONPATH = "$PWD"
pip install -r requirements.txt
python -m src.main "What is the recent price context for AAPL?"
```

Or without activating:

```powershell
$env:PYTHONPATH = "$PWD"
.\.venv\Scripts\python.exe -m src.main "What is the recent price context for AAPL?"
```

## Run

From the project root (`uptqi`), after activating venv (see above):

```bash
python -m src.main "What is the recent price context for AAPL?"
```

Interactive mode:

```bash
python -m src.main -i
```

Guardrail smoke tests (no API key required):

```bash
python evaluation/run_eval.py
```

## Project layout

```
uptqi/
├── src/
│   ├── main.py              # CLI + pipeline
│   ├── agent/               # LangGraph ReAct agent
│   ├── tools/               # yfinance + calculator + FAQ
│   └── guardrails/          # Input / output / behavioral
├── data/finance_faq.json
├── evaluation/
│   ├── run_eval.py
│   └── EVALUATION_REPORT.md
├── requirements.txt
├── ARCHITECTURE.md
└── README.md
```

## License

See [LICENSE](LICENSE) (MIT).
