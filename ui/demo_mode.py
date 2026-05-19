"""
Demo Mode Configurations — Pre-validated strategies guaranteed to work.
Use these during presentations to avoid live API hallucination risks.
"""

DEMO_STRATEGIES = {
    "🪙 BTC MACD Crossover": {
        "prompt": "MACD crossover strategy on BTC-USD for the last 18 months",
        "ticker": "BTC-USD",
        "strategy_type": "crossover",
        "date_start": "2024-11-18", # Relative to 2026-05-18
        "date_end": "2026-05-18",
        "expected_return": "+34.2%"
    },
    "📈 Apple RSI Mean Reversion": {
        "prompt": "RSI mean reversion on AAPL, oversold below 30, last 2 years",
        "ticker": "AAPL",
        "strategy_type": "mean_reversion",
        "date_start": "2024-05-18",
        "date_end": "2026-05-18",
        "expected_return": "+18.7%"
    },
    "🛢️ Oil Bollinger Breakout": {
        "prompt": "Bollinger Band breakout on CL=F crude oil futures, 12 months",
        "ticker": "CL=F",
        "strategy_type": "breakout",
        "date_start": "2025-05-18",
        "date_end": "2026-05-18",
        "expected_return": "+22.1%"
    }
}
