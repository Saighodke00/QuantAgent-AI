"""
APEX Quant-Forge — Main Streamlit Application
Run with: streamlit run app.py
"""
import os
import time
from pathlib import Path

import streamlit as st
import pandas as pd
from dotenv import load_dotenv

# ── Load env early ────────────────────────────────────────────────────
load_dotenv()

# ── Page config (must be first Streamlit call) ────────────────────────
st.set_page_config(
    page_title="APEX Quant-Forge",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Inject CSS ────────────────────────────────────────────────────────
_CSS_PATH = Path(__file__).parent / "assets" / "style.css"
with open(_CSS_PATH, encoding="utf-8") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# ── Lazy imports (after env is loaded) ───────────────────────────────
from agents.intent_analyst import run_analyst_only
from agents.graph import stream_execution
from db.crud import save_backtest, save_agent_logs
from ui.terminal import render_terminal_html
from ui.chart import render_equity_chart, render_stat_cards, render_code_block
from ui.sidebar import render_sidebar_ledger

# ─────────────────────────────────────────────────────────────────────
# Session State Initialization
# ─────────────────────────────────────────────────────────────────────
_DEFAULTS = {
    "phase": "idle",          # idle | analyzing | hitl | running | done | error
    "agent_logs": [],
    "extracted_intent": None,
    "backtest_result": None,
    "generated_code": "",
    "error_msg": "",
    "last_prompt": "",
}
for k, v in _DEFAULTS.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ─────────────────────────────────────────────────────────────────────
# Header
# ─────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="apex-header">
  <div class="apex-logo">⚡ APEX <span>Quant-Forge</span></div>
  <div style="display:flex;gap:8px;align-items:center;">
    <span class="apex-badge">🟢 Gemini 2.5 & Groq Llama 3.3</span>
    <span class="apex-badge">⬡ LangGraph</span>
    <span class="apex-badge">📊 yfinance</span>
  </div>
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────
# API Key Guard
# ─────────────────────────────────────────────────────────────────────
if not os.environ.get("GEMINI_API_KEY"):
    st.error("⚠️ GEMINI_API_KEY not found. Create a `.env` file — see `.env.example`.")
    st.stop()

# ─────────────────────────────────────────────────────────────────────
# Layout: 3 Columns
# ─────────────────────────────────────────────────────────────────────
col_left, col_mid, col_right = st.columns([1.1, 2.4, 1.8], gap="medium")

# ═════════════════════════════════════════════════════════════════════
# LEFT COLUMN — Historical Ledger
# ═════════════════════════════════════════════════════════════════════
with col_left:
    render_sidebar_ledger()

# ═════════════════════════════════════════════════════════════════════
# MIDDLE COLUMN — Agent Terminal + Input
# ═════════════════════════════════════════════════════════════════════
with col_mid:
    st.markdown('<div class="panel-header">🤖 AGENT MATRIX STREAM</div>', unsafe_allow_html=True)

    # Terminal placeholder — updated in streaming loop
    terminal_slot = st.empty()

    # Render current logs
    with terminal_slot.container():
        st.markdown(
            render_terminal_html(st.session_state.agent_logs),
            unsafe_allow_html=True,
        )

    st.markdown("<hr class='apex-divider'>", unsafe_allow_html=True)

    # ── Prompt Input ─────────────────────────────────────────────────
    st.markdown('<div class="panel-header">💬 STRATEGY PROMPT</div>', unsafe_allow_html=True)

    prompt = st.text_area(
        label="strategy_input",
        label_visibility="collapsed",
        placeholder=(
            'e.g. "Buy TSLA when RSI falls below 30 and sell when it crosses 70, '
            'test over the past 2 years"\n\n'
            'or: "Run a 50/200 EMA golden cross strategy on NIFTY 50 since 2022"'
        ),
        height=100,
        key="prompt_input",
    )

    btn_col1, btn_col2, btn_col3 = st.columns([2, 1.2, 1])

    with btn_col1:
        analyze_clicked = st.button(
            "🔍 Analyze Strategy",
            use_container_width=True,
            disabled=st.session_state.phase in ("analyzing", "running"),
        )

    with btn_col2:
        reset_clicked = st.button("↺ Reset", use_container_width=True)

    # ── HITL Confirmation Box ─────────────────────────────────────────
    if st.session_state.phase == "hitl" and st.session_state.extracted_intent:
        intent = st.session_state.extracted_intent
        st.markdown(f"""
        <div class="hitl-box">
          <div class="hitl-title">🔒 Human-in-the-Loop Confirmation</div>
          <div class="hitl-row"><span class="hitl-key">Ticker</span><span class="hitl-value">{intent.get('ticker')}</span></div>
          <div class="hitl-row"><span class="hitl-key">Strategy</span><span class="hitl-value">{intent.get('strategy_name')}</span></div>
          <div class="hitl-row"><span class="hitl-key">Type</span><span class="hitl-value">{intent.get('strategy_type')}</span></div>
          <div class="hitl-row"><span class="hitl-key">Date Range</span><span class="hitl-value">{intent.get('date_start')} → {intent.get('date_end')}</span></div>
          <div class="hitl-row" style="border:none"><span class="hitl-key">Logic</span><span class="hitl-value">{intent.get('strategy_description','')[:80]}</span></div>
        </div>
        """, unsafe_allow_html=True)

        exec_col1, exec_col2 = st.columns(2)
        with exec_col1:
            execute_clicked = st.button("✅ Approve & Execute Backtest", use_container_width=True)
        with exec_col2:
            cancel_clicked = st.button("✗ Cancel", use_container_width=True)

        if cancel_clicked:
            st.session_state.phase = "idle"
            st.rerun()
    else:
        execute_clicked = False
        cancel_clicked = False

# ═════════════════════════════════════════════════════════════════════
# RIGHT COLUMN — Analytics Panel
# ═════════════════════════════════════════════════════════════════════
with col_right:
    st.markdown('<div class="panel-header">📊 QUANT ANALYTICS</div>', unsafe_allow_html=True)

    if st.session_state.backtest_result:
        result = st.session_state.backtest_result
        
        # Create responsive interactive tabs
        tab_charts, tab_ledger, tab_ai_brain = st.tabs([
            "📈 Equity Curve", 
            "📜 Advanced Trade Ledger", 
            "🤖 AI Explainability Brain"
        ])
        
        # --- TAB 1: MAIN GRAPH & STATS ---
        with tab_charts:
            st.markdown("#### Portfolio Growth Timeline")
            fig = render_equity_chart(result)
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
            st.markdown(render_stat_cards(result), unsafe_allow_html=True)
            
        # --- TAB 2: INTERACTIVE TRADE LEDGER & TABLE ---
        with tab_ledger:
            st.markdown("#### Historical Strategy Executions")
            
            # 1. Advanced Metrics Deck
            c1, c2, c3 = st.columns(3)
            advanced = result.get("advanced_stats", {})
            if not advanced:
                advanced = {"Profit_Factor": 1.0, "Sortino_Ratio": 0.0, "Max_Win_Streak": 0, "Total_Skipped_Signals": 0}
            pf = advanced.get("Profit_Factor", 1.0)
            sr = advanced.get("Sortino_Ratio", 0.0)
            ts = advanced.get("Total_Skipped_Signals", 0)
            
            c1.metric("Profit Factor", f"{pf:.2f}x")
            c2.metric("Sortino Ratio", f"{sr:.2f}")
            c3.metric("AI Filtered Noise", f"{ts} Setups")
            
            st.divider()
            
            # 2. Interactive Data Table
            st.markdown("##### Detailed Execution Audit Trails")
            trade_log = result.get("trade_log", [])
            if trade_log:
                trade_df = pd.DataFrame(trade_log)
                st.dataframe(
                    trade_df, 
                    use_container_width=True,
                    column_config={
                        "PnL_Pct": st.column_config.NumberColumn("PnL (%)", format="%.2f%%"),
                        "Status": st.column_config.SelectboxColumn("Execution State")
                    }
                )
            else:
                st.info("ℹ️ No historical execution entries generated for this configuration.")

        # --- TAB 3: MACHINE LEARNING EXPLAINABILITY ---
        with tab_ai_brain:
            st.markdown("#### Walk-Forward Feature Importance Mapping")
            st.caption("This chart displays exactly which technical signals your Random Forest model relied on to filter out bad market setups.")
            
            features = result.get("feature_importances", {})
            if features:
                feat_df = pd.DataFrame({
                    "Market Metric": list(features.keys()),
                    "Predictive Weight (%)": [float(val) * 100 for val in features.values()]
                }).sort_values(by="Predictive Weight (%)", ascending=True)
                
                st.bar_chart(data=feat_df, x="Market Metric", y="Predictive Weight (%)", horizontal=True)
            else:
                st.warning("⚠️ No machine learning weights found for this layout variation.")

        # Expander code block at the bottom
        if st.session_state.generated_code:
            render_code_block(st.session_state.generated_code)
    else:
        st.markdown("""
        <div style="height:240px;display:flex;align-items:center;justify-content:center;
             background:#111827;border:1px solid #1E293B;border-radius:10px;
             color:#475569;font-size:13px;text-align:center;line-height:2;">
            📈<br>Equity curve and interactive tabs will render<br>after backtest completes
        </div>""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────
# Action Handlers
# ─────────────────────────────────────────────────────────────────────

# Reset
if reset_clicked:
    for k, v in _DEFAULTS.items():
        st.session_state[k] = v
    st.rerun()

# ── Phase 1: Analyze (run analyst only → HITL gate) ──────────────────
if analyze_clicked and prompt.strip():
    st.session_state.phase = "analyzing"
    st.session_state.agent_logs = []
    st.session_state.extracted_intent = None
    st.session_state.backtest_result = None
    st.session_state.generated_code = ""
    st.session_state.last_prompt = prompt.strip()

    with terminal_slot.container():
        st.markdown(
            render_terminal_html([{
                "agent": "SYSTEM", "severity": "INFO",
                "message": "Initializing APEX Quant-Forge pipeline...",
                "timestamp": "",
            }]),
            unsafe_allow_html=True,
        )

    with st.spinner("Analyzing strategy..."):
        result = run_analyst_only(prompt.strip())

    # Merge logs and extracted fields into session state
    st.session_state.agent_logs = result.get("agent_logs", [])
    st.session_state.extracted_intent = {
        "ticker":               result.get("ticker"),
        "strategy_name":        result.get("strategy_name"),
        "strategy_type":        result.get("strategy_type"),
        "date_start":           result.get("date_start"),
        "date_end":             result.get("date_end"),
        "strategy_description": result.get("strategy_description"),
    }
    st.session_state.phase = "hitl"
    st.rerun()

# ── Phase 2: Execute (HITL approved → stream graph) ──────────────────
if execute_clicked and st.session_state.extracted_intent:
    st.session_state.phase = "running"
    intent = st.session_state.extracted_intent

    # Build initial state for execution graph
    exec_state = {
        "user_prompt":          st.session_state.last_prompt,
        "ticker":               intent["ticker"],
        "strategy_name":        intent["strategy_name"],
        "strategy_type":        intent["strategy_type"],
        "date_start":           intent["date_start"],
        "date_end":             intent["date_end"],
        "strategy_description": intent["strategy_description"],
        "generated_code":       "",
        "retry_count":          0,
        "execution_success":    False,
        "last_error":           "",
        "result_json":          {},
        "agent_logs":           st.session_state.agent_logs,
    }

    final_state = exec_state.copy()

    # Stream LangGraph execution — update terminal after each node
    for snapshot in stream_execution(exec_state):
        new_logs = snapshot.get("agent_logs", [])
        # LangGraph values mode: snapshot IS the full state
        st.session_state.agent_logs = new_logs

        # Update terminal live
        with terminal_slot.container():
            st.markdown(
                render_terminal_html(st.session_state.agent_logs),
                unsafe_allow_html=True,
            )

        # Update code panel if code was generated
        if snapshot.get("generated_code"):
            st.session_state.generated_code = snapshot["generated_code"]

        final_state = snapshot
        time.sleep(0.05)  # tiny yield to let Streamlit paint

    # ── Execution complete ────────────────────────────────────────────
    if final_state.get("execution_success") and final_state.get("result_json"):
        result = final_state["result_json"]
        st.session_state.backtest_result = result
        st.session_state.phase = "done"

        # Persist to SQLite
        try:
            sid = save_backtest(
                user_prompt=st.session_state.last_prompt,
                ticker=intent["ticker"],
                strategy_name=intent["strategy_name"],
                generated_code=st.session_state.generated_code,
                result=result,
            )
            save_agent_logs(sid, st.session_state.agent_logs)
        except Exception as db_err:
            pass  # DB failure is non-fatal for demo
    else:
        st.session_state.phase = "error"
        st.session_state.error_msg = final_state.get("last_error", "Unknown execution error.")

    st.rerun()

# ── Error state display ───────────────────────────────────────────────
if st.session_state.phase == "error" and st.session_state.error_msg:
    with col_mid:
        st.error(f"**Execution failed after max retries.**\n\n```\n{st.session_state.error_msg[:400]}\n```")
