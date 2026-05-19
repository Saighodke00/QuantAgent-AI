"""
Strategist agent — proactively suggests alternative strategies.

Changes (item 13):
  - Richer JSON schema: adds expected_edge and risk_level fields
  - Hardcoded fallback suggestions when LLM call fails, so the panel
    is never blank during rate-limit periods
"""
import json
import re
from langchain_core.messages import HumanMessage, SystemMessage
from agents.llm import get_llm, clean_response_content

STRATEGIST_PROMPT = """You are an expert quantitative strategist.
The user requested: "{user_prompt}"
You identified: ticker={ticker}, strategy={strategy_name}

Without being asked, suggest 2 alternative strategy variations on the same ticker
that a quant researcher might also want to test for comparison.

Respond in strict JSON only:
{{
  "suggestions": [
    {{
      "name": "RSI Mean Reversion",
      "prompt": "full prompt string the user can paste and run",
      "rationale": "Why this complements the original strategy",
      "expected_edge": "What market condition this exploits differently",
      "risk_level": "Low"
    }},
    {{
      "name": "Bollinger Band Breakout",
      "prompt": "...",
      "rationale": "...",
      "expected_edge": "...",
      "risk_level": "High"
    }}
  ]
}}
"""


def _fallback_suggestions(ticker: str, strategy_name: str) -> list:
    """
    Item 13: Hardcoded fallback so the panel is never blank during
    rate-limit periods. Contextualised to the ticker in the session.
    """
    return [
        {
            "name": f"{ticker} RSI Oversold Bounce",
            "prompt": (
                f"RSI mean reversion on {ticker} — buy when RSI falls below 30, "
                f"sell when RSI rises above 70, test over the past 2 years"
            ),
            "rationale": "Tests momentum exhaustion as a complement to your current approach.",
            "expected_edge": "Captures capitulation bounces in high-volatility regimes.",
            "risk_level": "Medium",
        },
        {
            "name": f"{ticker} Bollinger Band Breakout",
            "prompt": (
                f"Bollinger Band 2-sigma breakout on {ticker} for the past 18 months"
            ),
            "rationale": "Captures volatility expansion instead of mean reversion.",
            "expected_edge": "Profits from trend continuation after low-volatility squeezes.",
            "risk_level": "High",
        },
    ]


def generate_suggestions(user_prompt: str, ticker: str, strategy_name: str) -> list:
    """Proactively suggests alternative strategies using the LLM."""
    llm = get_llm(temperature=0.7)
    prompt = STRATEGIST_PROMPT.format(
        user_prompt=user_prompt,
        ticker=ticker,
        strategy_name=strategy_name,
    )

    try:
        response = llm.invoke([
            SystemMessage(content="You are an expert quant AI. Always respond with valid JSON only."),
            HumanMessage(content=prompt),
        ])
        content = clean_response_content(response.content)

        # Strip markdown fences if present
        content = re.sub(r"^```(?:json)?\s*", "", content.strip())
        content = re.sub(r"\s*```$", "", content.strip())

        parsed = json.loads(content.strip())
        suggestions = parsed.get("suggestions", [])
        return suggestions if suggestions else _fallback_suggestions(ticker, strategy_name)

    except Exception as e:
        print(f"[SYSTEM] Strategist LLM failed: {e}. Using hardcoded fallback.")
        return _fallback_suggestions(ticker, strategy_name)
