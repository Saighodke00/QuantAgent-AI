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
    # Intent config
    user_prompt: str
    ai_filter_enabled: bool
    ai_confidence_threshold: float
    ticker: str
    strategy_name: str
    strategy_type: str
    date_start: str
    date_end: str
    strategy_description: str

    # Execution loop
    generated_code: str
    retry_count: int
    max_retries: int          # New limit tracking
    token_budget_used: int    # New token budget tracking
    
    # State flags
    validation_passed: bool   # Added for AST Validator
    execution_success: bool
    last_error: str
    result_json: dict         # {"equity_curve": [...], "win_rate": 0.58, ...}
    
    # UI Diff visualization
    critic_diff: str          
    critic_reasoning: str     

    # ── Agent communication channel (accumulated across all nodes) ────
    agent_logs: Annotated[list, operator.add]
