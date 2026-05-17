"""
Sandbox runner — executes LLM-generated Python scripts in a subprocess.
Parses the RESULT_JSON: prefix line from stdout.
"""
import json
import subprocess
import sys
import tempfile
import textwrap
from pathlib import Path
from typing import Tuple

from sandbox.sanitizer import sanitize_code


_TIMEOUT_SECONDS = 45


def execute_code(code: str) -> Tuple[bool, dict | None, str]:
    """
    Run `code` in an isolated subprocess.

    Returns:
        (success, result_dict, error_message)
    """
    # 1. Security check
    is_safe, reason = sanitize_code(code)
    if not is_safe:
        return False, None, f"[SECURITY BLOCK] {reason}"

    # 2. Write to temp file
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".py", delete=False, encoding="utf-8"
    ) as f:
        f.write(code)
        tmp_path = f.name

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
