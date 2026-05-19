import sys
import os
from dotenv import load_dotenv
sys.path.insert(0, os.path.abspath('.'))

load_dotenv()
from agents.state import GraphState
from agents.quant_coder import quant_coder_node

state = GraphState(
    ticker="AMD",
    strategy_name="Hybrid Bollinger Band MACD Mean Reversion",
    strategy_type="mean_reversion",
    date_start="2024-01-01",
    date_end="2026-05-17",
    strategy_description="Run a hybrid Bollinger Band and MACD mean-reversion strategy on AMD from 2024-01-01",
    user_prompt="",
    generated_code="",
    retry_count=0,
    execution_success=False,
    last_error="",
    result_json={},
    agent_logs=[]
)

print("Invoking quant_coder_node...")
result = quant_coder_node(state)
code = result.get("generated_code", "")

print("Result dictionary:")
import pprint
pprint.pprint(result)
