"""
SQLite cache for yfinance market data.

Avoids re-downloading the same ticker + date range on every run.
Cache entries expire after 24 hours so data stays fresh.

Uses the existing quant_forge.db — just adds a new table.
"""
import json
import sqlite3
from datetime import datetime, timezone, timedelta
from pathlib import Path

# Reuse the same DB as the rest of the app
_DB_PATH = Path(__file__).parent.parent / "quant_forge.db"
_CACHE_TTL_HOURS = 24


def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(_DB_PATH, check_same_thread=False)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS market_data_cache (
            cache_key   TEXT PRIMARY KEY,
            data_json   TEXT NOT NULL,
            cached_at   TEXT NOT NULL
        )
    """)
    conn.commit()
    return conn


def _make_key(ticker: str, date_start: str, date_end: str) -> str:
    return f"{ticker.upper()}_{date_start}_{date_end}"


def get_cached_data(ticker: str, date_start: str, date_end: str) -> dict | None:
    """
    Returns cached OHLCV data as a dict (suitable for pd.DataFrame.from_dict),
    or None if the entry is missing or older than _CACHE_TTL_HOURS.
    """
    key = _make_key(ticker, date_start, date_end)
    try:
        conn = _get_conn()
        row = conn.execute(
            "SELECT data_json, cached_at FROM market_data_cache WHERE cache_key = ?",
            (key,),
        ).fetchone()
        conn.close()
    except Exception:
        return None  # DB error is non-fatal — just re-download

    if not row:
        return None

    try:
        cached_at = datetime.fromisoformat(row[1])
        # Ensure timezone-aware comparison
        if cached_at.tzinfo is None:
            cached_at = cached_at.replace(tzinfo=timezone.utc)
        age = datetime.now(timezone.utc) - cached_at
        if age > timedelta(hours=_CACHE_TTL_HOURS):
            return None  # Expired — let caller re-download
        return json.loads(row[0])
    except Exception:
        return None


def save_cached_data(ticker: str, date_start: str, date_end: str, df_dict: dict):
    """
    Saves a DataFrame serialized as a dict (df.to_dict()) to cache.
    Fails silently so a cache write error never crashes the pipeline.
    """
    key = _make_key(ticker, date_start, date_end)
    try:
        conn = _get_conn()
        conn.execute(
            """INSERT OR REPLACE INTO market_data_cache
               (cache_key, data_json, cached_at) VALUES (?, ?, ?)""",
            (key, json.dumps(df_dict), datetime.now(timezone.utc).isoformat()),
        )
        conn.commit()
        conn.close()
    except Exception:
        pass  # Non-fatal — pipeline continues without cache


def invalidate(ticker: str, date_start: str, date_end: str):
    """Force-expire a specific cache entry."""
    key = _make_key(ticker, date_start, date_end)
    try:
        conn = _get_conn()
        conn.execute("DELETE FROM market_data_cache WHERE cache_key = ?", (key,))
        conn.commit()
        conn.close()
    except Exception:
        pass
