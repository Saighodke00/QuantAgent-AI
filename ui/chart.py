"""
Quant Analytics panel — Plotly equity curve + stat cards HTML.
"""
import plotly.graph_objects as go
import streamlit as st


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
    win_rate = result.get("win_rate", 0)
    max_dd = result.get("max_drawdown", 0)
    sharpe = result.get("sharpe_ratio", 0)
    trades = result.get("total_trades", 0)

    ret_color = "#34D399" if total_ret >= 0 else "#F87171"
    dd_color = "#F87171" if max_dd < -5 else "#FB923C" if max_dd < 0 else "#34D399"
    sharpe_color = "#34D399" if sharpe > 1 else "#FCD34D" if sharpe > 0 else "#F87171"

    cards = "".join([
        _stat_card("Total Return", f"{total_ret:+.2f}%", ret_color, "📈"),
        _stat_card("Win Rate",     f"{win_rate:.1f}%",   "#A5B4FC", "🎯"),
        _stat_card("Max Drawdown", f"{max_dd:.2f}%",     dd_color,  "📉"),
        _stat_card("Sharpe Ratio", f"{sharpe:.3f}",      sharpe_color, "⚡"),
        _stat_card("Total Trades", f"{trades}",           "#CBD5E1", "🔄"),
    ])

    return f'<div class="stat-grid">{cards}</div>'


def render_equity_chart(result: dict) -> go.Figure:
    """Build a dark-theme Plotly equity curve figure."""
    equity = result.get("equity_curve", [])
    if not equity:
        return go.Figure()

    dates = [pt[0] for pt in equity]
    values = [pt[1] for pt in equity]
    initial = values[0] if values else 100_000

    # Colour gradient: green above initial capital, red below
    line_color = "#34D399" if values[-1] >= initial else "#F87171"
    fill_color = "rgba(52,211,153,0.08)" if values[-1] >= initial else "rgba(248,113,113,0.08)"

    fig = go.Figure()
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

    # Starting capital reference line
    fig.add_hline(
        y=initial,
        line_dash="dot",
        line_color="rgba(148,163,184,0.4)",
        annotation_text="Starting Capital",
        annotation_position="bottom right",
        annotation_font_color="rgba(148,163,184,0.6)",
    )

    ticker = result.get("ticker", "")
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


def render_code_block(code: str) -> None:
    """Render the generated Python script in an expandable code block."""
    with st.expander("🛠️ View Generated Backtest Script", expanded=False):
        st.code(code, language="python", line_numbers=True)
