"""
Quant Analytics panel — Plotly equity curve + stat cards + drawdown chart.

Changes:
  - Item 10: Buy/sell entry markers added to equity chart
  - Item 11: render_drawdown_chart() added as second chart in Tab 1
  - Item 12: max_drawdown displayed as positive with leading minus sign
"""
import plotly.graph_objects as go
import streamlit as st
import pandas as pd


# ── Stat card HTML ────────────────────────────────────────────────────
def _stat_card(label: str, value: str, color: str, icon: str) -> str:
    return f"""
    <div class="stat-card">
        <div class="stat-icon">{icon}</div>
        <div class="stat-body">
            <div class="stat-label">{label}</div>
            <div class="stat-value" style="color:{color};">{value}</div>
        </div>
    </div>"""


def render_stat_cards(result: dict) -> str:
    total_ret = result.get("total_return", 0)
    win_rate  = result.get("win_rate", 0)
    sharpe    = result.get("sharpe_ratio", 0)
    trades    = result.get("total_trades", 0)

    # Item 12: store as positive; display with a minus sign prefix
    max_dd = abs(result.get("max_drawdown", 0))

    ret_color    = "#34D399" if total_ret >= 0 else "#F87171"
    dd_color     = "#F87171" if max_dd > 15 else "#FB923C" if max_dd > 5 else "#34D399"
    sharpe_color = "#34D399" if sharpe > 1 else "#FCD34D" if sharpe > 0 else "#F87171"

    cards = "".join([
        _stat_card("Total Return",  f"{total_ret:+.2f}%",  ret_color,    "📈"),
        _stat_card("Win Rate",      f"{win_rate:.1f}%",    "#A5B4FC",    "🎯"),
        _stat_card("Max Drawdown",  f"-{max_dd:.2f}%",     dd_color,     "📉"),
        _stat_card("Sharpe Ratio",  f"{sharpe:.3f}",       sharpe_color, "⚡"),
        _stat_card("Total Trades",  f"{trades}",           "#CBD5E1",    "🔄"),
    ])

    return f'<div class="stat-grid">{cards}</div>'


def render_equity_chart(result: dict) -> go.Figure:
    """Build a dark-theme Plotly equity curve with trade entry markers (item 10)."""
    equity = result.get("equity_curve", [])
    if not equity:
        return go.Figure()

    dates  = [pt[0] for pt in equity]
    values = [pt[1] for pt in equity]
    initial = values[0] if values else 100_000

    line_color = "#34D399" if values[-1] >= initial else "#F87171"
    fill_color = "rgba(52,211,153,0.08)" if values[-1] >= initial else "rgba(248,113,113,0.08)"

    fig = go.Figure()

    # Main equity curve
    fig.add_trace(go.Scatter(
        x=dates,
        y=values,
        mode="lines",
        name="Portfolio Value",
        line=dict(color=line_color, width=2.5, shape="spline", smoothing=0.6),
        fill="tozeroy",
        fillcolor=fill_color,
        hovertemplate="<b>%{x}</b><br>₹%{y:,.0f}<extra></extra>",
    ))

    # Item 10: Buy/sell entry markers
    trade_log = result.get("trade_log", [])
    if trade_log and equity:
        # Build a quick date→equity dict for O(1) lookup
        eq_map = {pt[0]: pt[1] for pt in equity}

        entry_dates  = [t["Date"] for t in trade_log if "ENTRY" in t.get("Action", "")]
        entry_values = [eq_map.get(d) for d in entry_dates if eq_map.get(d) is not None]
        entry_dates  = [d for d in entry_dates if eq_map.get(d) is not None]

        if entry_dates:
            fig.add_trace(go.Scatter(
                x=entry_dates,
                y=entry_values,
                mode="markers",
                name="Trade Entry",
                marker=dict(
                    symbol="triangle-up",
                    size=9,
                    color="#34D399",
                    line=dict(color="#0F172A", width=1),
                ),
                hovertemplate="<b>Entry</b><br>%{x}<br>₹%{y:,.0f}<extra></extra>",
            ))

    # Starting capital reference line
    fig.add_hline(
        y=initial,
        line_dash="dot",
        line_color="rgba(148,163,184,0.4)",
        annotation_text="Starting Capital",
        annotation_position="bottom right",
        annotation_font_color="rgba(148,163,184,0.6)",
    )

    ticker   = result.get("ticker", "")
    strategy = result.get("strategy", "Strategy")

    fig.update_layout(
        title=dict(
            text=f"<b>{strategy}</b> — {ticker}",
            font=dict(color="#E2E8F0", size=15, family="Inter, sans-serif"),
        ),
        paper_bgcolor="#111827",
        plot_bgcolor="#111827",
        font=dict(color="#94A3B8", family="Inter, sans-serif"),
        xaxis=dict(
            showgrid=True, gridcolor="rgba(51,65,85,0.6)",
            showline=False, zeroline=False,
            tickfont=dict(color="#64748B"),
        ),
        yaxis=dict(
            showgrid=True, gridcolor="rgba(51,65,85,0.6)",
            showline=False, zeroline=False,
            tickprefix="₹",
            tickfont=dict(color="#64748B"),
            tickformat=",.0f",
        ),
        margin=dict(l=10, r=10, t=50, b=10),
        hovermode="x unified",
        legend=dict(font=dict(color="#94A3B8")),
    )

    return fig


def render_drawdown_chart(result: dict) -> go.Figure:
    """
    Item 11 — Drawdown timeline chart.
    Standard in every professional backtest report.
    """
    equity = result.get("equity_curve", [])
    if not equity:
        return go.Figure()

    dates  = [pt[0] for pt in equity]
    values = pd.Series([pt[1] for pt in equity])
    peak   = values.cummax()
    dd     = ((values - peak) / peak * 100)  # negative percentages

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=dates,
        y=dd.tolist(),
        fill="tozeroy",
        fillcolor="rgba(248,113,113,0.12)",
        line=dict(color="#F87171", width=1.5),
        name="Drawdown %",
        hovertemplate="<b>%{x}</b><br>Drawdown: %{y:.2f}%<extra></extra>",
    ))

    fig.update_layout(
        paper_bgcolor="#111827",
        plot_bgcolor="#111827",
        font=dict(color="#94A3B8", family="Inter, sans-serif"),
        title=dict(
            text="<b>Drawdown Timeline</b>",
            font=dict(color="#E2E8F0", size=13),
        ),
        yaxis=dict(
            ticksuffix="%",
            gridcolor="rgba(51,65,85,0.6)",
            showline=False, zeroline=True,
            zerolinecolor="rgba(148,163,184,0.3)",
            tickfont=dict(color="#64748B"),
        ),
        xaxis=dict(
            showgrid=False,
            tickfont=dict(color="#64748B"),
        ),
        margin=dict(l=10, r=10, t=40, b=10),
        hovermode="x unified",
    )

    return fig


def render_code_block(code: str) -> None:
    """Render the generated Python script in an expandable code block."""
    with st.expander("🛠️ View Generated Backtest Script", expanded=False):
        st.code(code, language="python", line_numbers=True)
