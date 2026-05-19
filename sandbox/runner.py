"""
Sandbox runner — executes LLM-generated Python scripts in a subprocess.
Parses the RESULT_JSON: prefix line from stdout.

Perf improvements applied:
  Fix 6 — _warmup_subprocess() pre-loads heavy packages into OS disk cache
           at import time, saving ~1-2s on the first real execution.
  Fix 7 — sanitize_code() and temp-file write run concurrently via
           ThreadPoolExecutor, shaving ~0.1s for free.
"""
import json
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Tuple

from sandbox.sanitizer import sanitize_code


_TIMEOUT_SECONDS = 45


# ── Fix 6: Subprocess Pre-warm ──────────────────────────────────────────
def _warmup_subprocess():
    """
    Runs once at import time. Starts Python and imports the heaviest
    packages so the OS disk cache is hot before the first real execution.
    Saves 1-2s on the first sandbox run. Failure is completely non-fatal.
    """
    try:
        subprocess.run(
            [
                sys.executable,
                "-c",
                "import yfinance, pandas, numpy, sklearn, json; print('warm')",
            ],
            capture_output=True,
            timeout=20,
        )
    except Exception:
        pass  # warmup failure must never crash the app


# Fire warmup at module import asynchronously in a background thread to prevent blocking
import threading
threading.Thread(target=_warmup_subprocess, daemon=True).start()


def execute_code(code: str) -> Tuple[bool, dict | None, str]:
    """
    Run `code` in an isolated subprocess.

    Returns:
        (success, result_dict, error_message)

    Fix 7: sanitize_code() and the temp-file write now run concurrently
    inside a ThreadPoolExecutor so neither blocks the other.
    """
    # ── Automatic High-Fidelity Stats Injection ──
    idx = code.rfind('print("RESULT_JSON: "')
    if idx == -1:
        idx = code.rfind("print('RESULT_JSON: '")
    if idx != -1:
        injection = (
            "\n# --- AUTOMATIC HIGH-FIDELITY STATS INJECTION ---\n"
            "try:\n"
            "    import numpy as np\n"
            "    import pandas as pd\n"
            "    import math\n"
            "    gross_profits = float(df.loc[df['Strategy_Return'] > 0, 'Strategy_Return'].sum()) if 'Strategy_Return' in df.columns else 0.0\n"
            "    gross_losses  = float(abs(df.loc[df['Strategy_Return'] < 0, 'Strategy_Return'].sum())) if 'Strategy_Return' in df.columns else 0.0\n"
            "    profit_factor = gross_profits / gross_losses if gross_losses > 0 else 1.0\n"
            "    if math.isnan(profit_factor) or math.isinf(profit_factor):\n"
            "        profit_factor = 1.0\n"
            "    downside_returns = df['Strategy_Return'].clip(upper=0) if 'Strategy_Return' in df.columns else pd.Series()\n"
            "    downside_std = downside_returns.std()\n"
            "    sortino_ratio = float(df['Strategy_Return'].mean() / downside_std * np.sqrt(252)) if downside_std > 0 else 0.0\n"
            "    if math.isnan(sortino_ratio) or math.isinf(sortino_ratio):\n"
            "        sortino_ratio = 0.0\n"
            "    streak = df['Strategy_Return'].gt(0).astype(int) if 'Strategy_Return' in df.columns else pd.Series()\n"
            "    streak_groups = (streak != streak.shift()).cumsum() if len(streak) > 0 else pd.Series()\n"
            "    max_win_streak = int(streak.groupby(streak_groups).sum().max()) if len(streak) > 0 else 0\n"
            "    total_skipped = 0\n"
            "    if 'Signal' in df.columns and 'ML_Prediction' in df.columns:\n"
            "        total_skipped = int(((df['Signal'] == 1) & (df['ML_Prediction'] == 0)).sum())\n"
            "    elif 'trade_log' in locals() or 'best_trade_log' in locals():\n"
            "        tlog = best_trade_log if 'best_trade_log' in locals() else trade_log\n"
            "        total_skipped = len([t for t in tlog if isinstance(t, dict) and t.get('Status') == 'ML_FILTERED'])\n"
            "    best_advanced_stats = {\n"
            "        'Profit_Factor': round(profit_factor, 2),\n"
            "        'Sortino_Ratio': round(sortino_ratio, 2),\n"
            "        'Max_Win_Streak': max_win_streak,\n"
            "        'Total_Skipped_Signals': total_skipped\n"
            "    }\n"
            "except Exception:\n"
            "    pass\n\n"
        )
        code = code[:idx] + injection + code[idx:]
    # 1 + 2. Security check AND file write — run concurrently (Fix 7)
    with ThreadPoolExecutor(max_workers=2) as executor:
        sanitize_future = executor.submit(sanitize_code, code)

        # Write temp file while sanitizer is running in the other thread
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", delete=False, encoding="utf-8"
        ) as f:
            # Standard Imports Prepend — guarantees packages are ALWAYS imported
            standard_imports = (
                "import sys\n"
                "import os\n"
                "import json\n"
                "import math\n"
                "import random\n"
                "import warnings\n"
                "warnings.filterwarnings('ignore')\n"
                "from pathlib import Path\n"
                "import tempfile\n"
                "import pandas as pd\n"
                "import numpy as np\n"
                "import yfinance as yf\n"
                "from sklearn.ensemble import RandomForestClassifier\n"
                "from sklearn.model_selection import train_test_split\n\n"
            )
            prepended_code = standard_imports + code
            
            f.write(prepended_code)
            tmp_path = f.name

        is_safe, reason = sanitize_future.result()  # collect sanitizer result

    if not is_safe:
        Path(tmp_path).unlink(missing_ok=True)
        return False, None, f"[SECURITY BLOCK] {reason}"

    try:
        # 3. Run in subprocess with timeout
        proc = subprocess.run(
            [sys.executable, tmp_path],
            capture_output=True,
            text=True,
            timeout=_TIMEOUT_SECONDS,
            cwd=Path(tmp_path).parent,
        )

        stdout = proc.stdout.strip()
        stderr = proc.stderr.strip()

        if proc.returncode != 0:
            error_detail = stderr if stderr else stdout
            # Print full execution error detail to terminal
            print(f"\n[SANDBOX EXCEPTION] Execution failed!\nERROR:\n{error_detail}\n", file=sys.stderr)
            
            # Save failed code for debugging
            with open("failed_script.py", "w", encoding="utf-8") as debug_file:
                debug_file.write(code)
                
            return False, None, error_detail

        # 4. Parse RESULT_JSON line
        result_json = _parse_result_json(stdout)
        if result_json is None:
            return (
                False,
                None,
                f"Script succeeded but no RESULT_JSON found in output.\nStdout:\n{stdout[:500]}",
            )

        return True, result_json, ""

    except subprocess.TimeoutExpired:
        return False, None, f"Execution timed out after {_TIMEOUT_SECONDS}s."
    except Exception as e:
        return False, None, str(e)
    finally:
        Path(tmp_path).unlink(missing_ok=True)


def _parse_result_json(stdout: str) -> dict | None:
    """Extract the RESULT_JSON payload from script stdout."""
    for line in stdout.splitlines():
        if line.startswith("RESULT_JSON:"):
            payload = line[len("RESULT_JSON:"):].strip()
            try:
                return json.loads(payload)
            except json.JSONDecodeError:
                return None
    return None
