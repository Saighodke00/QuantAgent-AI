"""
LRU cache for LLM-generated backtest code.

Key: MD5 of (ticker, strategy_type, date_start, date_end)
Avoids a full 15–25s Gemini call when the user reruns the same
ticker + strategy combination.

Cache is stored as a simple JSON file alongside the DB.
Max 50 entries; oldest are evicted when limit is exceeded.
"""
import hashlib
import json
from pathlib import Path

_CACHE_PATH = Path("quant_forge_code_cache.json")
_MAX_ENTRIES = 50


def _make_key(ticker: str, strategy_type: str, date_start: str, date_end: str, ai_filter_enabled: bool, ai_confidence_threshold: float) -> str:
    raw = f"{ticker.upper()}_{strategy_type}_{date_start}_{date_end}_{ai_filter_enabled}_{ai_confidence_threshold}"
    return hashlib.md5(raw.encode()).hexdigest()


def _load() -> dict:
    if _CACHE_PATH.exists():
        try:
            return json.loads(_CACHE_PATH.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def _save(cache: dict):
    """Persist cache, evicting oldest entries if over the limit."""
    if len(cache) > _MAX_ENTRIES:
        # Drop the oldest keys (dict insertion order is guaranteed in Python 3.7+)
        overflow = len(cache) - _MAX_ENTRIES
        for old_key in list(cache.keys())[:overflow]:
            del cache[old_key]
    try:
        _CACHE_PATH.write_text(json.dumps(cache, indent=2), encoding="utf-8")
    except Exception:
        pass  # Cache write failure is non-fatal


def get_cached_code(
    ticker: str, strategy_type: str, date_start: str, date_end: str, ai_filter_enabled: bool, ai_confidence_threshold: float
) -> str | None:
    """Returns cached generated code string, or None on miss."""
    key = _make_key(ticker, strategy_type, date_start, date_end, ai_filter_enabled, ai_confidence_threshold)
    return _load().get(key)


def save_code(
    ticker: str, strategy_type: str, date_start: str, date_end: str, ai_filter_enabled: bool, ai_confidence_threshold: float, code: str
):
    """Save generated code to cache for future cache hits."""
    key = _make_key(ticker, strategy_type, date_start, date_end, ai_filter_enabled, ai_confidence_threshold)
    cache = _load()
    cache[key] = code
    _save(cache)


def clear_cache():
    """Wipe entire code cache. Useful for debugging."""
    if _CACHE_PATH.exists():
        _CACHE_PATH.unlink(missing_ok=True)
