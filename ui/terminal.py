"""
Agent terminal log renderer.
Builds a scrollable HTML terminal block from the agent_logs list.
Color-coded by agent role.

Changes:
  - Added VALIDATOR to _AGENT_COLORS and _AGENT_LABEL (item 6)
  - Replaced broken JavaScript scroll with CSS flex auto-scroll (item 15)
  - render_critic_panel already present; kept intact
"""
import textwrap


# ── Agent color map ───────────────────────────────────────────────────
_AGENT_COLORS = {
    "SYSTEM":    "#A5B4FC",   # Light indigo
    "ANALYST":   "#00F5D4",   # Teal
    "CODER":     "#FCD34D",   # Amber
    "SANDBOX":   "#CBD5E1",   # Slate-300
    "CRITIC":    "#F87171",   # Red
    "OPTIMIZER": "#0EA5E9",   # Blue
    "VALIDATOR": "#C084FC",   # Purple — item 6: was missing, showed as plain grey
}

_SEVERITY_COLORS = {
    "INFO":    "",          # Use agent color
    "WARNING": "#FB923C",   # Orange
    "ERROR":   "#F87171",   # Red
    "SUCCESS": "#34D399",   # Emerald green
}

_AGENT_LABEL = {
    "SYSTEM":    "MANAGER",
    "ANALYST":   "ANALYST",
    "CODER":     "CODER",
    "SANDBOX":   "SANDBOX",
    "CRITIC":    "CRITIC",
    "OPTIMIZER": "OPTIMIZER",
    "VALIDATOR": "VALIDATOR",  # item 6: added
}


def _entry_to_html(log: dict, index: int) -> str:
    agent    = log.get("agent", "SYSTEM")
    severity = log.get("severity", "INFO")
    message  = log.get("message", "")
    ts       = log.get("timestamp", "")[:19].replace("T", " ")

    label = _AGENT_LABEL.get(agent, agent)
    color = _SEVERITY_COLORS.get(severity) or _AGENT_COLORS.get(agent, "#CBD5E1")

    delay = min(index * 0.03, 0.5)

    return f"""
    <div class="log-entry" style="animation-delay:{delay:.2f}s">
        <span class="log-ts">{ts}</span>
        <span class="log-badge" style="color:{color};border-color:{color}40;">[{label}]</span>
        <span class="log-msg" style="color:{color};">{message}</span>
    </div>"""


def render_terminal_html(logs: list[dict]) -> str:
    """
    Returns a complete HTML block for the agent terminal.
    Call via st.markdown(render_terminal_html(logs), unsafe_allow_html=True)
    """
    if not logs:
        return textwrap.dedent("""
            <div class="terminal-wrap">
                <div class="terminal-empty">
                    <span style="color:#475569;">⬡ System idle — awaiting strategy prompt...</span>
                </div>
            </div>""")

    entries = "".join(_entry_to_html(log, i) for i, log in enumerate(logs))

    # Item 15: CSS flex auto-scroll instead of broken JavaScript.
    # justify-content:flex-end keeps newest entries visible at the bottom
    # without JS (which doesn't reliably execute in Streamlit iframes).
    return textwrap.dedent(f"""
        <div class="terminal-wrap">
            <div class="terminal-header">
                <span class="terminal-dot red"></span>
                <span class="terminal-dot yellow"></span>
                <span class="terminal-dot green"></span>
                <span class="terminal-title">AGENT MATRIX STREAM</span>
            </div>
            <div class="terminal-body" id="terminal-body"
                 style="display:flex;flex-direction:column;
                        justify-content:flex-end;overflow-y:auto;
                        max-height:360px;">
                {entries}
            </div>
        </div>""")


def render_critic_panel(diff: str, reasoning: str) -> str:
    """
    Renders the Critic's autonomous bug fix diff and reasoning.
    Called from app.py after the streaming loop if critic_diff is present.
    """
    if not diff and not reasoning:
        return ""

    html_parts = [
        '<div style="background:#1e1e1e; border-left:4px solid #00F5D4; '
        'padding:16px; margin:16px 0; border-radius:4px;">'
    ]
    html_parts.append(
        '<h4 style="color:#00F5D4; margin-top:0;">🔍 Critic Agent — Autonomous Fix</h4>'
    )

    if reasoning:
        html_parts.append(
            f'<div style="color:#A5B4FC; margin-bottom:12px; font-style:italic;">'
            f'💡 <b>Why it failed:</b><br>{reasoning}</div>'
        )

    if diff:
        colored_diff = ""
        for line in diff.split("\n"):
            line = line.replace("<", "&lt;").replace(">", "&gt;")
            if line.startswith("+") and not line.startswith("+++"):
                colored_diff += f'<span style="color:#34D399">{line}</span>\n'
            elif line.startswith("-") and not line.startswith("---"):
                colored_diff += f'<span style="color:#F87171">{line}</span>\n'
            elif line.startswith("@@"):
                colored_diff += f'<span style="color:#0EA5E9">{line}</span>\n'
            else:
                colored_diff += f'<span style="color:#CBD5E1">{line}</span>\n'

        html_parts.append(
            f'<pre style="background:#0F172A; padding:12px; border-radius:6px; '
            f'font-size:12px; overflow-x:auto;">{colored_diff}</pre>'
        )

    html_parts.append("</div>")
    return "\n".join(html_parts)
