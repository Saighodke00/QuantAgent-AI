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
from ui.chart import render_equity_chart, render_stat_cards, render_code_block, render_drawdown_chart
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
    "ai_filter_enabled": True,
    "ai_confidence_threshold": 0.5,
}
for k, v in _DEFAULTS.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ── URL Router for Shared Backtests ──────────────────────────────────
if "share" in st.query_params:
    token = st.query_params["share"]
    from db.crud import get_backtest_by_share_token
    shared_result = get_backtest_by_share_token(token)
    if shared_result:
        st.session_state.backtest_result = shared_result
        st.session_state.phase = "done"
        st.session_state.extracted_intent = {
            "ticker": shared_result.get("ticker_symbol", ""),
            "strategy_name": shared_result.get("strategy_name", ""),
            "strategy_type": "Shared",
            "date_start": "Historical",
            "date_end": "Historical",
            "strategy_description": shared_result.get("user_prompt", "")
        }
        st.session_state.last_prompt = shared_result.get("user_prompt", "")
        st.session_state.generated_code = shared_result.get("generated_python_code", "")
        st.success("📊 Loaded shared backtest successfully!")
        st.query_params.clear()
    else:
        st.error("❌ Shared link expired or invalid.")
        st.query_params.clear()

# ─────────────────────────────────────────────────────────────────────
# Header
# ─────────────────────────────────────────────────────────────────────
def _active_providers() -> str:
    """Returns a badge string showing which LLM providers are configured."""
    check = [
        ("GEMINI_API_KEY",     "Gemini"),
        ("CEREBRAS_API_KEY",   "Cerebras"),
        ("GROQ_API_KEY",       "Groq"),
        ("OPENROUTER_API_KEY", "OpenRouter"),
        ("MISTRAL_API_KEY",    "Mistral"),
    ]
    active = [label for env, label in check if os.environ.get(env)]
    return " · ".join(active) if active else "No providers"

st.markdown(f"""
<div class="apex-header">
  <div class="apex-logo">⚡ APEX <span>Quant-Forge</span></div>
  <div style="display:flex;gap:8px;align-items:center;">
    <span class="apex-badge">🟢 {_active_providers()}</span>
    <span class="apex-badge">⬡ LangGraph</span>
    <span class="apex-badge">📊 yfinance</span>
  </div>
</div>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────
# API Key Guard
# ─────────────────────────────────────────────────────────────────────
SUPPORTED_KEYS = ["GROQ_API_KEY", "GEMINI_API_KEY", "CEREBRAS_API_KEY", "OPENROUTER_API_KEY", "MISTRAL_API_KEY"]
has_any_key = any(os.environ.get(k) for k in SUPPORTED_KEYS)

if not has_any_key:
    st.warning("⚠️ No active LLM API keys found (GROQ, GEMINI, CEREBRAS, etc.). APEX Quant-Forge is running in **Demo / Mock Mode**.")

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

    # ── Demo Mode ────────────────────────────────────────────────────
    st.markdown('<div class="panel-header">💬 STRATEGY PROMPT</div>', unsafe_allow_html=True)
    
    st.sidebar.markdown("### 🎮 Demo Mode")
    demo_toggle = st.sidebar.toggle("Enable Demo Mode", value=False)
    
    if demo_toggle:
        from ui.demo_mode import DEMO_STRATEGIES
        selected = st.sidebar.selectbox(
            "Pick a pre-validated strategy",
            options=list(DEMO_STRATEGIES.keys())
        )
        demo = DEMO_STRATEGIES[selected]
        
        prompt = st.text_area(
            label="strategy_input",
            label_visibility="collapsed",
            value=demo["prompt"],
            disabled=True,
            height=100,
            key="prompt_input",
        )
        st.sidebar.success(f"Expected Return: {demo['expected_return']}")
        
        # Override Intent Extraction to bypass Analyst LLM in Demo Mode
        st.session_state.demo_intent_override = demo
    else:
        st.session_state.demo_intent_override = None
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

    # ── AI Engine Settings Expander ──────────────────────────────────
    with st.expander("🤖 AI Engine Settings", expanded=True):
        st.session_state.ai_filter_enabled = st.toggle(
            "Enable ML Alpha Filter", 
            value=st.session_state.ai_filter_enabled,
            help="Turn off to see raw technical signals without AI protection."
        )
        st.session_state.ai_confidence_threshold = st.slider(
            "AI Confidence Threshold", 
            min_value=0.3, 
            max_value=0.7, 
            value=st.session_state.ai_confidence_threshold, 
            step=0.05,
            help="Minimum prediction probability required to allow a signal."
        )

    btn_col1, btn_col2, btn_col3 = st.columns([2, 1.2, 1])

    with btn_col1:
        analyze_clicked = st.button(
            "🔍 Analyze Strategy",
            width="stretch",
            disabled=st.session_state.phase in ("analyzing", "running"),
        )

    with btn_col2:
        reset_clicked = st.button("↺ Reset", width="stretch")

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
            execute_clicked = st.button("✅ Approve & Execute Backtest", width="stretch")
        with exec_col2:
            cancel_clicked = st.button("✗ Cancel", width="stretch")

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
            st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
            st.markdown(render_stat_cards(result), unsafe_allow_html=True)
            # Item 11: drawdown chart below equity curve
            st.markdown("#### Drawdown Timeline")
            fig_dd = render_drawdown_chart(result)
            st.plotly_chart(fig_dd, width="stretch", config={"displayModeBar": False})
            
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
                    width="stretch",
                    column_config={
                        "PnL_Pct": st.column_config.NumberColumn("PnL (%)", format="%.2f%%"),
                        "Status": st.column_config.TextColumn("Execution State")
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
            
        # ── Shareable URL Button ──
        if "share_token" in result:
            share_token = result["share_token"]
            # Item 8: read base URL from env so share links work on ngrok/HuggingFace
            base_url = os.environ.get("APP_BASE_URL", "http://localhost:8501").rstrip("/")
            share_url = f"{base_url}/?share={share_token}"
            st.markdown(f"""
            <div style="background:#1e1e1e; padding:16px; border-radius:8px; border:1px solid #334155; margin-top:16px; display:flex; justify-content:space-between; align-items:center;">
                <code style="background:#0F172A; padding:8px; border-radius:4px; color:#A5B4FC; font-size:12px;">{share_url}</code>
                <a href="javascript:navigator.clipboard.writeText('{share_url}')" style="background:#00F5D4; color:#0F172A; text-decoration:none; padding:8px 16px; border-radius:6px; font-weight:bold; font-size:13px;">📋 Copy Link</a>
            </div>
            """, unsafe_allow_html=True)
            
        # ── Proactive AI Suggestions (Fix 1: now pre-computed, no spinner needed) ──
        st.markdown("<br><hr class='apex-divider'>", unsafe_allow_html=True)
        if "proactive_suggestions" not in st.session_state:
            # Fallback: suggestions weren't ready (e.g. page loaded from share link)
            with st.spinner("🤖 Strategist finalising suggestions..."):
                from agents.strategist import generate_suggestions
                intent = st.session_state.extracted_intent
                st.session_state.proactive_suggestions = generate_suggestions(
                    st.session_state.last_prompt,
                    intent.get("ticker", ""),
                    intent.get("strategy_name", "")
                )
                st.rerun()
                
        if st.session_state.proactive_suggestions:
            st.markdown("### 🤖 Agent Also Suggests Testing:")
            cols = st.columns(2)
            for i, suggestion in enumerate(st.session_state.proactive_suggestions):
                with cols[i % 2]:
                    risk = suggestion.get('risk_level', '')
                    risk_color = {"Low": "#34D399", "Medium": "#FCD34D", "High": "#F87171"}.get(risk, "#CBD5E1")
                    edge = suggestion.get('expected_edge', '')
                    st.markdown(f"""
                        <div style='background:#1e1e1e; border:1px solid #00F5D4;
                                    border-radius:8px; padding:16px; margin-bottom:16px;'>
                            <div style='display:flex;justify-content:space-between;align-items:center;'>
                                <h4 style='color:#00F5D4; margin:0;'>{suggestion.get('name', 'Alternative Strategy')}</h4>
                                <span style='background:{risk_color}22; color:{risk_color}; font-size:11px;
                                             padding:2px 8px; border-radius:4px; border:1px solid {risk_color}44;'>
                                    {risk} Risk</span>
                            </div>
                            <p style='color:#CBD5E1; font-size:13px; margin:8px 0 4px;'>{suggestion.get('rationale', '')}</p>
                            {f'<p style="color:#94A3B8; font-size:12px; font-style:italic; margin:0 0 8px;">Edge: {edge}</p>' if edge else ''}
                            <code style='color:#FCD34D; font-size:11px; background:#0F172A;'>{suggestion.get('prompt', '')[:90]}...</code>
                        </div>
                    """, unsafe_allow_html=True)
                    if st.button(f"▶ Run Variation", key=f"sugg_btn_{i}", width="stretch"):
                        # Reset state and inject suggestion
                        st.session_state.last_prompt = suggestion.get("prompt", "")
                        st.session_state.phase = "analyzing"
                        st.session_state.agent_logs = []
                        st.session_state.extracted_intent = None
                        st.session_state.backtest_result = None
                        del st.session_state.proactive_suggestions
                        st.rerun()

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

    with col_mid:
        with st.spinner("Analyzing strategy..."):
            result = run_analyst_only(prompt.strip())

    # Merge logs and extracted fields into session state
    st.session_state.agent_logs = result.get("agent_logs", [])
    extracted = {
        "ticker":               result.get("ticker"),
        "strategy_name":        result.get("strategy_name"),
        "strategy_type":        result.get("strategy_type"),
        "date_start":           result.get("date_start"),
        "date_end":             result.get("date_end"),
        "strategy_description": result.get("strategy_description"),
    }
    st.session_state.extracted_intent = extracted

    # Item 9: quick ticker validation before showing the HITL box
    ticker_sym = extracted.get("ticker", "")
    if ticker_sym:
        try:
            import yfinance as yf
            hist = yf.Ticker(ticker_sym).history(period="5d")
            if hist.empty:
                st.warning(
                    f"⚠️ Ticker **'{ticker_sym}'** returned no market data. "
                    f"Please refine your prompt (check the symbol or date range)."
                )
                st.session_state.phase = "idle"
                st.rerun()
        except Exception:
            pass  # network error — let the pipeline attempt it

    st.session_state.phase = "hitl"
    st.rerun()

# ── Phase 2: Execute (HITL approved → stream graph) ────────────────────────────
if execute_clicked and st.session_state.extracted_intent:
    st.session_state.phase = "running"
    intent = st.session_state.extracted_intent

    # ── Fix 1: Fire Strategist in background immediately ───────────────────
    # It runs concurrently while Coder + Sandbox are working, so by the time
    # charts render the suggestions are already computed — no visible spinner.
    from agents.parallel_runner import BackgroundTask
    from agents.strategist import generate_suggestions
    strategist_task = BackgroundTask().start(
        generate_suggestions,
        st.session_state.last_prompt,
        intent.get("ticker", ""),
        intent.get("strategy_name", ""),
    )

    # Build initial state for execution graph
    exec_state = {
        "user_prompt":             st.session_state.last_prompt,
        "ai_filter_enabled":       st.session_state.ai_filter_enabled,
        "ai_confidence_threshold": st.session_state.ai_confidence_threshold,
        "ticker":                  intent["ticker"],
        "strategy_name":           intent["strategy_name"],
        "strategy_type":           intent["strategy_type"],
        "date_start":              intent["date_start"],
        "date_end":                intent["date_end"],
        "strategy_description":    intent["strategy_description"],
        "generated_code":          "",
        "retry_count":             0,
        "max_retries":             3,      # item 4: was missing → KeyError
        "token_budget_used":       0,      # item 4: was missing → KeyError
        "validation_passed":       False,  # item 4: was missing → KeyError
        "critic_diff":             "",    # item 4: was missing
        "critic_reasoning":        "",    # item 4: was missing
        "execution_success":       False,
        "last_error":              "",
        "result_json":             {},
        "agent_logs":              st.session_state.agent_logs,
    }

    final_state = exec_state.copy()

    with col_mid:
        # Dynamic status container to prevent screen freezing look during LLM invocations
        with st.status("🤖 Initializing Agentic Core Execution...", expanded=True) as status:
            status.write("🔍 Strategy context loaded. Building LangGraph orchestration...")
            
            # Stream LangGraph execution — update terminal after each node with robust exception guard
            try:
                for snapshot in stream_execution(exec_state):
                    new_logs = snapshot.get("agent_logs", [])
                    # LangGraph values mode: snapshot IS the full state
                    st.session_state.agent_logs = new_logs

                    # Update st.status with the latest log dynamically
                    if new_logs:
                        latest = new_logs[-1]
                        status.write(f"📡 **[{latest['agent']}]** {latest['message']}")

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
            except Exception as graph_err:
                final_state = exec_state.copy()
                final_state["execution_success"] = False
                final_state["last_error"] = f"LLM Router Error: {str(graph_err)}"

            # Dynamically change status style depending on result
            if final_state.get("execution_success"):
                status.update(label="✅ Backtest Complete! Metrics Loaded Below.", state="complete", expanded=False)
            else:
                status.update(label="❌ Pipeline Execution Failed. Check logs above.", state="error", expanded=False)

        # Item 5: Render Critic diff panel if the Critic ran
        if final_state.get("critic_diff") or final_state.get("critic_reasoning"):
            from ui.terminal import render_critic_panel
            with col_mid:
                st.markdown(
                    render_critic_panel(
                        final_state.get("critic_diff", ""),
                        final_state.get("critic_reasoning", ""),
                    ),
                    unsafe_allow_html=True,
                )

    # ── Execution complete ────────────────────────────────────────────
    if final_state.get("execution_success") and final_state.get("result_json"):
        result = final_state["result_json"]
        st.session_state.backtest_result = result
        st.session_state.phase = "done"

        # ── Fix 1: Collect Strategist result (already done in background) ──
        suggestions = strategist_task.wait(timeout=10.0)
        st.session_state.proactive_suggestions = suggestions or []

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
        err_msg = final_state.get("last_error", "Unknown execution error.")
        # Collect strategist result even on failure (short timeout)
        try:
            st.session_state.proactive_suggestions = strategist_task.wait(timeout=2.0) or []
        except Exception:
            pass
        # If API keys completely exhaust, seamlessly serve mock data!
        if "exhausted" in err_msg.lower() or "no active llm" in err_msg.lower() or "429" in err_msg or "rate" in err_msg.lower():
            from agents.mock_fallback import get_mock_result
            st.session_state.backtest_result = get_mock_result(intent["ticker"])
            st.session_state.phase = "done"
            st.toast("⚠️ Live APIs exhausted! Displaying cached Mock Fallback data.")
        else:
            st.session_state.phase = "error"
            st.session_state.error_msg = err_msg

    st.rerun()

# ── Error state display ───────────────────────────────────────────────
if st.session_state.phase == "error" and st.session_state.error_msg:
    with col_mid:
        st.error(f"**Execution failed after max retries.**\n\n```\n{st.session_state.error_msg[:400]}\n```")
