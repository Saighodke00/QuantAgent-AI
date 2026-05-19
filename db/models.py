"""
SQLite database schema — mirrors the Supabase PostgreSQL layout from the PRD.
Uses Python's built-in sqlite3 so zero extra installs are needed.
"""
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "quant_forge.db"


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Create tables if they don't exist. Safe to call on every app start."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.executescript("""
        CREATE TABLE IF NOT EXISTS strategy_backtests (
            id          TEXT PRIMARY KEY,
            user_prompt TEXT NOT NULL,
            ticker_symbol TEXT NOT NULL,
            strategy_name TEXT NOT NULL,
            generated_python_code TEXT NOT NULL,
            win_rate_percentage   REAL NOT NULL,
            total_return_percentage REAL NOT NULL,
            max_drawdown_percentage REAL NOT NULL,
            sharpe_ratio REAL DEFAULT 0.0,
            total_trades INTEGER DEFAULT 0,
            equity_curve_points TEXT NOT NULL,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS agent_runtime_logs (
            id TEXT PRIMARY KEY,
            strategy_id TEXT REFERENCES strategy_backtests(id),
            agent_node_name TEXT NOT NULL,
            log_severity TEXT DEFAULT 'INFO',
            log_message TEXT NOT NULL,
            latency_duration_ms INTEGER,
            created_at TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_strategies_ticker
            ON strategy_backtests(ticker_symbol);

        CREATE INDEX IF NOT EXISTS idx_agent_logs_strategy
            ON agent_runtime_logs(strategy_id);
    """)

    # Alter strategy_backtests table to add new columns if they do not exist
    try:
        cursor.execute("ALTER TABLE strategy_backtests ADD COLUMN feature_importances TEXT;")
    except sqlite3.OperationalError:
        pass
    try:
        cursor.execute("ALTER TABLE strategy_backtests ADD COLUMN trade_log TEXT;")
    except sqlite3.OperationalError:
        pass
    try:
        cursor.execute("ALTER TABLE strategy_backtests ADD COLUMN advanced_stats TEXT;")
    except sqlite3.OperationalError:
        pass
    try:
        cursor.execute("ALTER TABLE strategy_backtests ADD COLUMN share_token TEXT;")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_strategies_share ON strategy_backtests(share_token);")
    except sqlite3.OperationalError:
        pass

    conn.commit()
    conn.close()
