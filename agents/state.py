"""
LangGraph GraphState — the single shared state object passed between all agent nodes.
Lists use Annotated[list, operator.add] so each node's appended logs accumulate correctly.
"""
from __future__ import annotations
import operator
from typing import Annotated, TypedDict


class AgentLog(TypedDict):
    agent: str        # 'ANALYST' | 'CODER' | 'SANDBOX' | 'CRITIC' | 'SYSTEM'
    severity: str     # 'INFO' | 'WARNING' | 'ERROR' | 'SUCCESS'
    message: str
    timestamp: str


class GraphState(TypedDict):
    # ── Input ─────────────────────────────────────────────────────────
    user_prompt: str

    # ── Extracted intent (Node 1 output) ─────────────────────────────
    ticker: str
    strategy_name: str
    strategy_type: str        # mean_reversion | momentum | crossover | volatility
    date_start: str           # YYYY-MM-DD
    date_end: str             # YYYY-MM-DD
    strategy_description: str

    # ── Code generation ───────────────────────────────────────────────
    generated_code: str
    retry_count: int          # Circuit breaker — max 3

    # ── Execution results ─────────────────────────────────────────────
    execution_success: bool
    last_error: str
    result_json: dict         # {"equity_curve": [...], "win_rate": 0.58, ...}

    # ── Agent communication channel (accumulated across all nodes) ────
    agent_logs: Annotated[list, operator.add]
