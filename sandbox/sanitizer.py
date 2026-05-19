"""
Sandbox security layer — regex-based allowlist validator.
Strips/blocks dangerous imports before any code reaches subprocess.
"""
import re
from typing import Tuple

# ── Banned patterns ──────────────────────────────────────────────────
_BANNED = [
    r"\bimport\s+os\b",
    r"\bimport\s+shutil\b",
    r"\bimport\s+subprocess\b",
    r"\bimport\s+socket\b",
    r"\bimport\s+pickle\b",
    r"\bimport\s+ctypes\b",
    r"\bfrom\s+os\b",
    r"\bfrom\s+subprocess\b",
    r"\bfrom\s+socket\b",
    r"\b__import__\s*\(",
    r"\beval\s*\(",
    r"\bexec\s*\(",
    r"\bcompile\s*\(",
    r"open\s*\([^)]*['\"][wa]['\"]",   # block file writes
    r"\bgetattr\s*\(\s*__builtins__",
]

_COMPILED = [re.compile(p) for p in _BANNED]


def sanitize_code(code: str) -> Tuple[bool, str]:
    """
    Returns (is_safe, reason).
    If is_safe is False, reason contains the blocked pattern AND the matched text
    so the Critic agent can understand exactly what was flagged.
    """
    for pattern, compiled in zip(_BANNED, _COMPILED):
        match = compiled.search(code)
        if match:
            # Item 16: show the actual matched text, not just the regex
            return False, (
                f"Banned pattern detected: `{pattern}` "
                f"— matched: `{match.group(0)}`"
            )
    return True, "OK"
