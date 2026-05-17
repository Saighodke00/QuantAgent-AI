# ⚡ APEX Quant-Forge

> Autonomous Multi-Agent Quantitative Research & Backtesting Workspace

A solo-mode Python application that converts natural-language trading hypotheses into a fully executed, charted backtest — powered by a self-correcting LangGraph agent network and Google Gemini 1.5 Flash.

---

## 🚀 Quick Start

### 1. Install dependencies
```bash
cd Quant-Forge
pip install -r requirements.txt
```

### 2. Add your Gemini API key
Get a free key at [aistudio.google.com](https://aistudio.google.com/app/apikey), then:
```bash
# Edit .env and replace the placeholder:
GEMINI_API_KEY=your_actual_key_here
```

### 3. Run the app
```bash
streamlit run app.py
```

### 4. (Optional) Share publicly via ngrok
```bash
pip install pyngrok
ngrok authtoken 3DokoR0G5ZlL2tnuy4aLBubrZUb_k9YJyV4FkoN6s16Zufvy
ngrok http 8501
```

---

## 🏗️ Architecture

```
User Prompt
    │
    ▼
[Intent Analyst]  ──── Gemini 1.5 Flash extracts ticker, strategy, dates
    │
    ▼
[HITL Gate]  ──────── Confirmation UI before any API calls
    │
    ▼
[Quant Coder]  ─────── Gemini writes Python strategy logic
    │
    ▼
[Sandbox Runner]  ───── subprocess execution, 45s timeout
    │
    ├─ FAIL (retry < 3) ──► [Code Critic] ──► back to Coder
    ├─ FAIL (retry = 3) ──► Graceful failure
    └─ SUCCESS ──────────► SQLite save + Chart render
```

## 🤖 Agent Roles

| Agent | Model | Role |
|-------|-------|------|
| Intent Analyst | Gemini 1.5 Flash | Extracts ticker, strategy type, date range |
| Quant Coder | Gemini 1.5 Flash | Generates Python backtest strategy logic |
| Sandbox Runner | Python subprocess | Executes code safely, parses results |
| Code Critic | Gemini 1.5 Flash | Diagnoses errors, rewrites broken code |

## 🔒 Security

- Regex allowlist blocks `os`, `sys`, `subprocess`, `eval`, `exec` in generated code
- 45-second hard subprocess timeout
- Max 3 retry circuit breaker stops infinite loops

## 📊 Example Prompts

- `Buy TSLA when RSI falls below 30, sell when it crosses 70, test over 2 years`
- `Run a 50/200 EMA golden cross on NIFTY 50 since 2022`
- `MACD crossover strategy on BTC-USD for the last 18 months`
- `Bollinger Band mean reversion on AAPL for the past 3 years`

## 📁 Project Structure

```
Quant-Forge/
├── app.py                    # Streamlit entry point
├── requirements.txt
├── .env                      # Your API keys (gitignored)
├── agents/
│   ├── state.py              # LangGraph GraphState TypedDict
│   ├── prompts.py            # All LLM system prompts + frozen scaffold
│   ├── intent_analyst.py     # Node 1: strategy extraction
│   ├── quant_coder.py        # Node 2: code generation
│   ├── code_critic.py        # Node 4: error correction
│   └── graph.py              # LangGraph StateGraph + streaming
├── sandbox/
│   ├── sanitizer.py          # Security: import allowlist
│   └── runner.py             # Subprocess executor
├── db/
│   ├── models.py             # SQLite schema
│   └── crud.py               # save/fetch helpers
├── ui/
│   ├── terminal.py           # Color-coded log renderer
│   ├── chart.py              # Plotly equity curve + stat cards
│   └── sidebar.py            # Historical ledger panel
└── assets/
    └── style.css             # Obsidian dark theme
```
