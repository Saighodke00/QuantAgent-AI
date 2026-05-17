"""
Agent terminal log renderer.
Builds a scrollable HTML terminal block from the agent_logs list.
Color-coded by agent role per the PRD spec.
"""
import textwrap


# ── Agent color map ───────────────────────────────────────────────────
_AGENT_COLORS = {
    "SYSTEM":  "#A5B4FC",   # Light indigo
    "ANALYST": "#00F5D4",   # Teal
    "CODER":   "#FCD34D",   # Amber
    "SANDBOX": "#CBD5E1",   # Slate-300
    "CRITIC":  "#F87171",   # Red (overridden to green on SUCCESS)
    "OPTIMIZER": "#0EA5E9", # Blue
}

_SEVERITY_COLORS = {
    "INFO":    "",          # Use agent color
    "WARNING": "#FB923C",   # Orange
    "ERROR":   "#F87171",   # Red
    "SUCCESS": "#34D399",   # Emerald green
}

_AGENT_LABEL = {
    "SYSTEM":  "MANAGER",
    "ANALYST": "ANALYST",
    "CODER":   "CODER",
    "SANDBOX": "SANDBOX",
    "CRITIC":  "CRITIC",
    "OPTIMIZER": "OPTIMIZER",
}


def _entry_to_html(log: dict, index: int) -> str:
    agent = log.get("agent", "SYSTEM")
    severity = log.get("severity", "INFO")
    message = log.get("message", "")
    ts = log.get("timestamp", "")[:19].replace("T", " ")

    label = _AGENT_LABEL.get(agent, agent)
    color = _SEVERITY_COLORS.get(severity) or _AGENT_COLORS.get(agent, "#CBD5E1")

    # Fade-in animation offset for staggered effect
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

    return textwrap.dedent(f"""
        <div class="terminal-wrap">
            <div class="terminal-header">
                <span class="terminal-dot red"></span>
                <span class="terminal-dot yellow"></span>
                <span class="terminal-dot green"></span>
                <span class="terminal-title">AGENT MATRIX STREAM</span>
            </div>
            <div class="terminal-body" id="terminal-body">
                {entries}
            </div>
        </div>
        <script>
            // Auto-scroll terminal to bottom
            var tb = document.getElementById("terminal-body");
            if (tb) tb.scrollTop = tb.scrollHeight;
        </script>""")
