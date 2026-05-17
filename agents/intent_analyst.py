"""
Node 1 — Intent Analyst Agent
Extracts structured strategy metadata from a free-form user prompt.
Uses Gemini 1.5 Flash with forced JSON output.
"""
import json
import os
import re
from datetime import datetime, timezone, timedelta

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage

from agents.state import AgentLog, GraphState
from agents.prompts import INTENT_ANALYST_SYSTEM, TODAY


def _make_log(msg: str, severity: str = "INFO") -> AgentLog:
    return AgentLog(
        agent="ANALYST",
        severity=severity,
        message=msg,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


def intent_analyst_node(state: GraphState) -> dict:
    """
    LangGraph node: parse user_prompt → ticker, strategy fields.
    Returns a dict of state updates (partial update pattern).
    """
    logs: list[AgentLog] = []
    logs.append(_make_log("Initializing Intent Analyst..."))
    logs.append(_make_log(f"Parsing prompt: \"{state['user_prompt'][:80]}...\""))

    try:
        from langchain_groq import ChatGroq
        llm = ChatGroq(
            model="llama-3.3-70b-versatile",
            temperature=0.0,
            groq_api_key=os.environ["GROQ_API_KEY"],
        )
        response = llm.invoke(
            [
                SystemMessage(content=INTENT_ANALYST_SYSTEM),
                HumanMessage(content=f"User prompt: {state['user_prompt']}"),
            ]
        )
        raw = response.content.strip()

        # Strip markdown code fences if the model adds them
        raw = re.sub(r"^```[a-z]*\n?", "", raw)
        raw = re.sub(r"\n?```$", "", raw)

        parsed: dict = json.loads(raw)

        # Validate date range duration
        try:
            ds_str = parsed.get("date_start") or "2024-01-01"
            de_str = parsed.get("date_end") or TODAY
            ds = datetime.strptime(ds_str, "%Y-%m-%d").date()
            de = datetime.strptime(de_str, "%Y-%m-%d").date()
            if (de - ds).days < 90:
                new_ds = de - timedelta(days=365*2)
                parsed["date_start"] = new_ds.isoformat()
                parsed["date_end"] = de_str
                logs.append(_make_log(
                    f"⚠️ Extracted backtest range ({(de - ds).days} days) is too short for indicator calculation/ML splits. "
                    f"Auto-expanded start to {new_ds.isoformat()} (past 2 years) for safety.",
                    "WARNING"
                ))
        except Exception as date_err:
            logs.append(_make_log(f"Date validation warning: {date_err}", "WARNING"))

        logs.append(_make_log(f"Ticker identified   → {parsed.get('ticker') or '?'}"))
        logs.append(_make_log(f"Strategy type       → {parsed.get('strategy_type') or '?'}"))
        logs.append(_make_log(f"Date range          → {parsed.get('date_start')} to {parsed.get('date_end')}"))
        logs.append(_make_log(f"Strategy name       → {parsed.get('strategy_name') or '?'}"))
        logs.append(_make_log("Intent extraction complete.", "SUCCESS"))

        return {
            "ticker": parsed.get("ticker") or "AAPL",
            "strategy_name": parsed.get("strategy_name") or "Custom Strategy",
            "strategy_type": parsed.get("strategy_type") or "momentum",
            "date_start": parsed.get("date_start") or "2023-01-01",
            "date_end": parsed.get("date_end") or "2025-01-01",
            "strategy_description": parsed.get("strategy_description") or state["user_prompt"],
            "retry_count": 0,
            "last_error": "",
            "execution_success": False,
            "result_json": {},
            "agent_logs": logs,
        }

    except Exception as e:
        logs.append(_make_log(f"Intent extraction failed: {e}", "ERROR"))
        return {
            "ticker": "AAPL",
            "strategy_name": "RSI Mean Reversion",
            "strategy_type": "mean_reversion",
            "date_start": "2023-01-01",
            "date_end": "2025-01-01",
            "strategy_description": state["user_prompt"],
            "retry_count": 0,
            "last_error": str(e),
            "execution_success": False,
            "result_json": {},
            "agent_logs": logs,
        }


def run_analyst_only(prompt: str) -> dict:
    """
    Convenience wrapper — runs ONLY the analyst without a full LangGraph call.
    Used for the HITL gate phase in the Streamlit UI.
    """
    initial = GraphState(
        user_prompt=prompt,
        ticker="", strategy_name="", strategy_type="",
        date_start="", date_end="", strategy_description="",
        generated_code="", retry_count=0,
        execution_success=False, last_error="",
        result_json={}, agent_logs=[],
    )
    return intent_analyst_node(initial)
