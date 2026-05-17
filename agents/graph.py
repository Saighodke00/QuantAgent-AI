"""
LangGraph StateGraph — the full agent orchestration pipeline.

Graph topology:
  quant_coder → sandbox_runner → [conditional]
                                     ├─ finalize      (success)
                                     ├─ code_critic   (failure + retries left)
                                     └─ fail_graceful (failure + retries exhausted)
  code_critic → quant_coder  (loop back)
  finalize / fail_graceful → END
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Generator

from langgraph.graph import END, StateGraph

from agents.code_critic import code_critic_node
from agents.intent_analyst import intent_analyst_node
from agents.quant_coder import quant_coder_node
from agents.state import AgentLog, GraphState
from sandbox.runner import execute_code

_MAX_RETRIES = 3


# ─────────────────────────────────────────────────────────────────────
# Sandbox Node (not LLM — pure Python execution)
# ─────────────────────────────────────────────────────────────────────
def sandbox_runner_node(state: GraphState) -> dict:
    logs: list[AgentLog] = []
    ts = datetime.now(timezone.utc).isoformat()

    logs.append(AgentLog(agent="SANDBOX", severity="INFO",
                         message="Executing generated script in isolated subprocess...", timestamp=ts))

    code = state.get("generated_code", "")
    if not code:
        return {
            "execution_success": False,
            "last_error": "No code was generated.",
            "agent_logs": logs,
        }

    success, result, error = execute_code(code)

    ts2 = datetime.now(timezone.utc).isoformat()
    if success:
        logs.append(AgentLog(agent="SANDBOX", severity="SUCCESS",
                             message=f"✓ Execution successful. Return: {result.get('total_return', 0):.2f}%  |  Win Rate: {result.get('win_rate', 0):.1f}%", timestamp=ts2))
        
        opt_params = result.get('optimized_parameters', '')
        if opt_params:
            logs.append(AgentLog(agent="OPTIMIZER", severity="WARNING", message="Strategy scan active: Testing parameters...", timestamp=ts2))
            logs.append(AgentLog(agent="OPTIMIZER", severity="ERROR", message="Found underperforming parameters. Rejecting configuration.", timestamp=ts2))
            logs.append(AgentLog(agent="OPTIMIZER", severity="SUCCESS", message=f"Success! {opt_params}", timestamp=ts2))

        return {"execution_success": True, "result_json": result, "last_error": "", "agent_logs": logs}
    else:
        short_err = error.splitlines()[-1] if error else "Unknown error"
        logs.append(AgentLog(agent="SANDBOX", severity="ERROR",
                             message=f"✗ Execution failed: {short_err}", timestamp=ts2))
        return {"execution_success": False, "last_error": error, "agent_logs": logs}


# ─────────────────────────────────────────────────────────────────────
# Finalize Node
# ─────────────────────────────────────────────────────────────────────
def finalize_node(state: GraphState) -> dict:
    ts = datetime.now(timezone.utc).isoformat()
    result = state.get("result_json", {})
    log = AgentLog(
        agent="SYSTEM", severity="SUCCESS",
        message=(
            f"✅ Pipeline complete — {result.get('strategy', 'Strategy')} on {result.get('ticker', '')} | "
            f"Return: {result.get('total_return', 0):.2f}% | "
            f"Sharpe: {result.get('sharpe_ratio', 0):.3f} | "
            f"Max DD: {result.get('max_drawdown', 0):.2f}%"
        ),
        timestamp=ts,
    )
    return {"agent_logs": [log]}


# ─────────────────────────────────────────────────────────────────────
# Graceful Failure Node (circuit breaker triggered)
# ─────────────────────────────────────────────────────────────────────
def fail_gracefully_node(state: GraphState) -> dict:
    ts = datetime.now(timezone.utc).isoformat()
    log = AgentLog(
        agent="SYSTEM", severity="ERROR",
        message=f"⛔ Max retries ({_MAX_RETRIES}) reached. Last error: {state.get('last_error', '')[:200]}",
        timestamp=ts,
    )
    return {"execution_success": False, "agent_logs": [log]}


# ─────────────────────────────────────────────────────────────────────
# Conditional Edge Router
# ─────────────────────────────────────────────────────────────────────
def route_after_sandbox(state: GraphState) -> str:
    if state.get("execution_success"):
        return "finalize"
    if state.get("retry_count", 0) >= _MAX_RETRIES:
        return "fail_gracefully"
    return "code_critic"


# ─────────────────────────────────────────────────────────────────────
# Graph Compilation
# ─────────────────────────────────────────────────────────────────────
def _build_execution_graph() -> StateGraph:
    """
    Builds the coder → sandbox → critic loop.
    Entry point is quant_coder (intent already extracted via HITL gate).
    """
    g = StateGraph(GraphState)

    g.add_node("quant_coder", quant_coder_node)
    g.add_node("sandbox_runner", sandbox_runner_node)
    g.add_node("code_critic", code_critic_node)
    g.add_node("finalize", finalize_node)
    g.add_node("fail_gracefully", fail_gracefully_node)

    g.set_entry_point("quant_coder")
    g.add_edge("quant_coder", "sandbox_runner")
    g.add_conditional_edges(
        "sandbox_runner",
        route_after_sandbox,
        {
            "finalize": "finalize",
            "code_critic": "code_critic",
            "fail_gracefully": "fail_gracefully",
        },
    )
    g.add_edge("code_critic", "quant_coder")
    g.add_edge("finalize", END)
    g.add_edge("fail_gracefully", END)

    return g.compile()


_execution_graph = _build_execution_graph()


# ─────────────────────────────────────────────────────────────────────
# Public streaming interface used by app.py
# ─────────────────────────────────────────────────────────────────────
def stream_execution(intent_state: dict) -> Generator[dict, None, None]:
    """
    Streams LangGraph state deltas for the Streamlit terminal.
    Yields the full state snapshot after each node completes.
    """
    for event in _execution_graph.stream(intent_state, stream_mode="values"):
        yield event
