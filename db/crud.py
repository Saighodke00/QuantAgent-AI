"""
CRUD helpers for SQLite persistence.
Saves completed backtests and agent logs; fetches historical ledger.
"""
import json
import uuid
from datetime import datetime, timezone
from typing import Any

from db.models import get_connection, init_db

# Ensure tables exist at import time
init_db()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def save_backtest(
    user_prompt: str,
    ticker: str,
    strategy_name: str,
    generated_code: str,
    result: dict,
) -> str:
    """Persist a completed backtest. Returns the new UUID."""
    import secrets
    strategy_id = str(uuid.uuid4())
    share_token = secrets.token_urlsafe(8)  # item 14: cryptographically random, URL-safe
    
    conn = get_connection()
    conn.execute(
        """
        INSERT INTO strategy_backtests
            (id, user_prompt, ticker_symbol, strategy_name,
             generated_python_code, win_rate_percentage,
             total_return_percentage, max_drawdown_percentage,
             sharpe_ratio, total_trades, equity_curve_points,
             feature_importances, trade_log, advanced_stats, share_token, created_at)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """,
        (
            strategy_id,
            user_prompt,
            ticker,
            strategy_name,
            generated_code,
            result.get("win_rate", 0.0),
            result.get("total_return", 0.0),
            result.get("max_drawdown", 0.0),
            result.get("sharpe_ratio", 0.0),
            result.get("total_trades", 0),
            json.dumps(result.get("equity_curve", [])),
            json.dumps(result.get("feature_importances", {})),
            json.dumps(result.get("trade_log", [])),
            json.dumps(result.get("advanced_stats", {})),
            share_token,
            _now(),
        ),
    )
    conn.commit()
    conn.close()
    
    # Store share_token on the result dict so Streamlit can access it right away
    result["share_token"] = share_token
    
    return strategy_id

def get_backtest_by_share_token(share_token: str) -> dict | None:
    """Fetch a single backtest via share token."""
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM strategy_backtests WHERE share_token = ?", (share_token,)
    ).fetchone()
    conn.close()
    if not row:
        return None
    d = dict(row)
    d["equity_curve_points"] = json.loads(d["equity_curve_points"])
    d["feature_importances"] = json.loads(d["feature_importances"]) if d.get("feature_importances") else {}
    d["trade_log"] = json.loads(d["trade_log"]) if d.get("trade_log") else []
    d["advanced_stats"] = json.loads(d["advanced_stats"]) if d.get("advanced_stats") else {
        "Profit_Factor": 1.0, "Sortino_Ratio": 0.0, "Max_Win_Streak": 0, "Total_Skipped_Signals": 0
    }
    return d


def save_agent_logs(strategy_id: str, logs: list[dict]) -> None:
    """Bulk-insert agent runtime logs after a completed run."""
    conn = get_connection()
    rows = [
        (
            str(uuid.uuid4()),
            strategy_id,
            log.get("agent", "SYSTEM"),
            log.get("severity", "INFO"),
            log.get("message", ""),
            None,
            _now(),
        )
        for log in logs
    ]
    conn.executemany(
        """
        INSERT INTO agent_runtime_logs
            (id, strategy_id, agent_node_name, log_severity,
             log_message, latency_duration_ms, created_at)
        VALUES (?,?,?,?,?,?,?)
        """,
        rows,
    )
    conn.commit()
    conn.close()


def get_all_backtests() -> list[dict[str, Any]]:
    """Fetch all backtests ordered newest first for the history ledger."""
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT id, ticker_symbol, strategy_name,
               total_return_percentage, win_rate_percentage,
               max_drawdown_percentage, sharpe_ratio, created_at
        FROM strategy_backtests
        ORDER BY created_at DESC
        LIMIT 50
        """
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_backtest_detail(strategy_id: str) -> dict[str, Any] | None:
    """Fetch a single backtest with full equity curve for chart reload."""
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM strategy_backtests WHERE id = ?", (strategy_id,)
    ).fetchone()
    conn.close()
    if row is None:
        return None
    d = dict(row)
    d["equity_curve_points"] = json.loads(d["equity_curve_points"])
    
    # Load advanced structures if they exist in SQLite
    d["feature_importances"] = json.loads(d["feature_importances"]) if d.get("feature_importances") else {}
    d["trade_log"] = json.loads(d["trade_log"]) if d.get("trade_log") else []
    d["advanced_stats"] = json.loads(d["advanced_stats"]) if d.get("advanced_stats") else {
        "Profit_Factor": 1.0, "Sortino_Ratio": 0.0, "Max_Win_Streak": 0, "Total_Skipped_Signals": 0
    }
    return d
