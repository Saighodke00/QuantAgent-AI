"""
Left panel — Historical Ledger
Renders past backtests fetched from SQLite.
"""
import streamlit as st
from db.crud import get_all_backtests


def render_sidebar_ledger() -> None:
    """Render the history ledger in the left column."""
    st.markdown('<div class="panel-header">📋 STRATEGY LEDGER</div>', unsafe_allow_html=True)

    try:
        history = get_all_backtests()
    except Exception:
        history = []

    if not history:
        st.markdown(
            '<div class="ledger-empty">No strategies run yet.<br>Submit a prompt to begin.</div>',
            unsafe_allow_html=True,
        )
        return

    for row in history:
        ret = row["total_return_percentage"]
        win = row["win_rate_percentage"]
        ret_color = "#34D399" if ret >= 0 else "#F87171"
        ret_icon = "▲" if ret >= 0 else "▼"
        badge_cls = "badge-positive" if ret >= 0 else "badge-negative"

        created = row["created_at"][:10]

        card_html = f"""
        <div class="ledger-card">
            <div class="ledger-top">
                <span class="ledger-ticker">{row['ticker_symbol']}</span>
                <span class="{badge_cls}">{ret_icon} {abs(ret):.1f}%</span>
            </div>
            <div class="ledger-strategy">{row['strategy_name']}</div>
            <div class="ledger-meta">
                Win {win:.0f}% &nbsp;·&nbsp; {created}
            </div>
        </div>"""

        st.markdown(card_html, unsafe_allow_html=True)
