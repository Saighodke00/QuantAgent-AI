import json

# Realistic, complete demo trade logs for a high-fidelity presentation
MOCK_RESULTS = {
    "BTC-USD": {
        "ticker": "BTC-USD",
        "strategy": "MACD Crossover",
        "total_return": 34.2,
        "win_rate": 58.3,
        "max_drawdown": 12.1,
        "sharpe_ratio": 1.47,
        "total_trades": 4,
        "equity_curve": [[f"2025-01-{i:02d}", 100000 + i * 800] for i in range(1, 20)],
        "advanced_stats": {"Profit_Factor": 1.72, "Sortino_Ratio": 1.84, "Max_Win_Streak": 5, "Total_Skipped_Signals": 12},
        "trade_log": [
            {"Date": "2025-01-02", "Action": "LONG_ENTRY", "Price": 96200.0, "Status": "Executed", "PnL_Pct": 4.25},
            {"Date": "2025-01-08", "Action": "LONG_ENTRY", "Price": 98500.0, "Status": "Executed", "PnL_Pct": 2.10},
            {"Date": "2025-01-12", "Action": "LONG_ENTRY", "Price": 102400.0, "Status": "Executed", "PnL_Pct": -1.15},
            {"Date": "2025-01-18", "Action": "LONG_ENTRY", "Price": 105800.0, "Status": "Executed", "PnL_Pct": 5.80}
        ],
        "feature_importances": {"RSI": 0.4, "MACD": 0.6},
        "optimized_parameters": "Optimized MACD fast=12, slow=26",
        "_source": "MOCK_FALLBACK"
    },
    "AAPL": {
        "ticker": "AAPL",
        "strategy": "RSI Mean Reversion",
        "total_return": 18.7,
        "win_rate": 62.5,
        "max_drawdown": 8.4,
        "sharpe_ratio": 1.15,
        "total_trades": 4,
        "equity_curve": [[f"2025-01-{i:02d}", 100000 + i * 400] for i in range(1, 20)],
        "advanced_stats": {"Profit_Factor": 1.54, "Sortino_Ratio": 1.42, "Max_Win_Streak": 4, "Total_Skipped_Signals": 8},
        "trade_log": [
            {"Date": "2025-01-03", "Action": "LONG_ENTRY", "Price": 182.50, "Status": "Executed", "PnL_Pct": 3.40},
            {"Date": "2025-01-09", "Action": "LONG_ENTRY", "Price": 185.10, "Status": "Executed", "PnL_Pct": 1.85},
            {"Date": "2025-01-14", "Action": "LONG_ENTRY", "Price": 189.20, "Status": "Executed", "PnL_Pct": -0.90},
            {"Date": "2025-01-19", "Action": "LONG_ENTRY", "Price": 194.50, "Status": "Executed", "PnL_Pct": 2.65}
        ],
        "feature_importances": {"RSI": 0.8, "BB": 0.2},
        "optimized_parameters": "Optimized RSI threshold=30",
        "_source": "MOCK_FALLBACK"
    },
    "CL=F": {
        "ticker": "CL=F",
        "strategy": "Bollinger Breakout",
        "total_return": 22.1,
        "win_rate": 54.2,
        "max_drawdown": 15.6,
        "sharpe_ratio": 1.05,
        "total_trades": 4,
        "equity_curve": [[f"2025-01-{i:02d}", 100000 + i * 500] for i in range(1, 20)],
        "advanced_stats": {"Profit_Factor": 1.41, "Sortino_Ratio": 1.18, "Max_Win_Streak": 3, "Total_Skipped_Signals": 15},
        "trade_log": [
            {"Date": "2025-01-05", "Action": "LONG_ENTRY", "Price": 72.40, "Status": "Executed", "PnL_Pct": 5.10},
            {"Date": "2025-01-10", "Action": "LONG_ENTRY", "Price": 74.80, "Status": "Executed", "PnL_Pct": 2.30},
            {"Date": "2025-01-15", "Action": "LONG_ENTRY", "Price": 77.20, "Status": "Executed", "PnL_Pct": -1.80},
            {"Date": "2025-01-20", "Action": "LONG_ENTRY", "Price": 79.50, "Status": "Executed", "PnL_Pct": 3.90}
        ],
        "feature_importances": {"BB_Width": 0.7, "Volume": 0.3},
        "optimized_parameters": "Optimized BB std=2",
        "_source": "MOCK_FALLBACK"
    }
}

def get_mock_result(ticker: str) -> dict:
    result = MOCK_RESULTS.get(ticker)
    if result:
        return result
    # Generic fallback if ticker not in demo list
    return MOCK_RESULTS["BTC-USD"]
