"""
Node 4 — Code Critic Agent
Called when the sandbox raises an exception.
Receives the broken code + error traceback and returns a repaired full script.
"""
import os
import re
from datetime import datetime, timezone

from agents.llm import get_llm, clean_response_content
from langchain_core.messages import HumanMessage, SystemMessage

from agents.state import AgentLog, GraphState
from agents.prompts import CODE_CRITIC_HUMAN, CODE_CRITIC_SYSTEM


def _make_log(msg: str, severity: str = "INFO") -> AgentLog:
    return AgentLog(
        agent="CRITIC",
        severity=severity,
        message=msg,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


def _strip_fences(code: str) -> str:
    """Extract code from markdown fences robustly to ignore conversational text."""
    match = re.search(r"```(?:python)?\s*(.*?)\s*```", code, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()
    
    # Fallback if the closing backticks are cut off or missing
    match = re.search(r"```(?:python)?\s*(.*)", code, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()
        
    # Super-fallback: If Qwen forgot backticks completely, slice from the first import
    match = re.search(r"(import\s+[a-zA-Z].*)", code, re.DOTALL)
    if match:
        return match.group(1).strip()

    # Final Fallback: filter out obvious conversational lines to prevent immediate crashes
    lines = code.split('\n')
    clean_lines = []
    for line in lines:
        if line.strip().startswith(("Okay", "Sure", "Here is", "First,", "Importing", "The user")):
            continue
        clean_lines.append(line)
        
    return '\n'.join(clean_lines).strip()


def code_critic_node(state: GraphState) -> dict:
    """
    LangGraph node: diagnose and repair the broken generated_code.
    Increments retry_count to enforce the circuit breaker.
    """
    logs: list[AgentLog] = []
    retry = state.get("retry_count", 0) + 1

    logs.append(_make_log(f"⚠ Sandbox exception detected. Activating critic (retry {retry}/3)...", "ERROR"))
    logs.append(_make_log(f"Error: {state.get('last_error', '')[:800]}", "ERROR"))

    human_prompt = CODE_CRITIC_HUMAN.format(
        error=state.get("last_error", "Unknown error"),
        code=state.get("generated_code", ""),
    )

    llm = get_llm(temperature=0.0)

    try:
        response = llm.invoke(
            [
                SystemMessage(content=CODE_CRITIC_SYSTEM),
                HumanMessage(content=human_prompt),
            ]
        )
        fixed_code = _strip_fences(clean_response_content(response.content))
        logs.append(_make_log("Patch applied. Routing back to sandbox...", "WARNING"))
        return {
            "generated_code": fixed_code,
            "retry_count": retry,
            "last_error": "",
            "agent_logs": logs,
        }

    except Exception as e:
        err_str = str(e)
        if "429" in err_str:
            logs.append(_make_log(f"🛑 Hit rate limits! Aborting loop to save token quota.", "ERROR"))
            return {"last_error": err_str, "agent_logs": logs, "retry_count": 99}

        logs.append(_make_log(f"Critic LLM call failed: {err_str}", "ERROR"))
        return {
            "retry_count": retry,
            "last_error": err_str,
            "agent_logs": logs,
        }
