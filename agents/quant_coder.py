"""
Node 2 — Quantitative Coder Agent
Generates the strategy logic section of the backtest scaffold.
Uses Gemini 1.5 Flash. On retry, the last error is injected into the prompt.
"""
import os
import re
from datetime import datetime, timezone

from agents.llm import get_llm, clean_response_content
from langchain_core.messages import HumanMessage, SystemMessage

from agents.state import AgentLog, GraphState
from agents.prompts import (
    QUANT_CODER_HUMAN,
    QUANT_CODER_SYSTEM,
)


def _make_log(msg: str, severity: str = "INFO") -> AgentLog:
    return AgentLog(
        agent="CODER",
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


def quant_coder_node(state: GraphState) -> dict:
    """
    LangGraph node: generate full Python backtest script.
    If retry_count > 0, the last_error is passed to the prompt.

    Fix 5: On first attempt (retry==0) check the code cache before calling
    the LLM. On success, save the result to cache for future hits.
    """
    logs: list[AgentLog] = []
    retry = state.get("retry_count", 0)

    # ── Fix 5: Check code cache before LLM call (first attempt only) ──────
    if retry == 0:
        try:
            from agents.code_cache import get_cached_code
            cached = get_cached_code(
                state["ticker"],
                state["strategy_type"],
                state["date_start"],
                state["date_end"],
                state.get("ai_filter_enabled", True),
                state.get("ai_confidence_threshold", 0.5),
            )
            if cached:
                logs.append(_make_log(
                    f"⚡ Cache hit — reusing generated code for "
                    f"{state['ticker']} / {state['strategy_type']}. Skipping LLM call.",
                    "SUCCESS",
                ))
                return {"generated_code": cached, "agent_logs": logs}
        except Exception:
            pass  # Cache miss or error — proceed to LLM

    if retry == 0:
        logs.append(_make_log(f"Generating backtest script for {state['ticker']}..."))
    else:
        logs.append(_make_log(f"Re-generating script (attempt {retry + 1}/3) after critic patch...", "WARNING"))

    error_context = ""
    if state.get("last_error"):
        error_context = f"\n\nPREVIOUS ERROR TO AVOID:\n{state['last_error'][:800]}"

    human_prompt = QUANT_CODER_HUMAN.format(
        ticker=state["ticker"],
        strategy_name=state["strategy_name"],
        strategy_type=state["strategy_type"],
        strategy_description=state["strategy_description"],
        date_start=state["date_start"],
        date_end=state["date_end"],
        ai_filter_enabled=state.get("ai_filter_enabled", True),
        ai_confidence_threshold=state.get("ai_confidence_threshold", 0.5),
        error_context=error_context,
    )

    llm = get_llm(temperature=0.0)

    try:
        response = llm.invoke(
            [
                SystemMessage(content=QUANT_CODER_SYSTEM),
                HumanMessage(content=human_prompt),
            ]
        )
        strategy_logic = _strip_fences(clean_response_content(response.content))

        # The LLM now generates the entire standalone script directly
        full_code = strategy_logic

        logs.append(_make_log(f"Script generated — {len(full_code.splitlines())} lines.", "SUCCESS"))

        # ── Fix 5: Save successful generation to code cache ────────────────
        if retry == 0:
            try:
                from agents.code_cache import save_code
                save_code(
                    state["ticker"],
                    state["strategy_type"],
                    state["date_start"],
                    state["date_end"],
                    state.get("ai_filter_enabled", True),
                    state.get("ai_confidence_threshold", 0.5),
                    full_code,
                )
            except Exception:
                pass  # Cache write failure is non-fatal

        return {"generated_code": full_code, "agent_logs": logs}

    except Exception as e:
        err_str = str(e)
        if "429" in err_str:
            logs.append(_make_log(f"🛑 Hit rate limits! Aborting loop to save token quota.", "ERROR"))
            return {"generated_code": "", "last_error": err_str, "agent_logs": logs, "retry_count": 99}
        
        logs.append(_make_log(f"Code generation failed: {err_str}", "ERROR"))
        return {"generated_code": "", "last_error": err_str, "agent_logs": logs}
