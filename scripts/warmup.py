"""
Warmup Script — Run this 10 minutes before your hackathon demo.
It silently executes the 3 pre-validated Demo Mode strategies and caches the
results in your SQLite database. This guarantees your presentation runs smoothly.
"""
import os
import sys

# Force UTF-8 encoding for Windows terminals to prevent emoji crashes
sys.stdout.reconfigure(encoding='utf-8')
from dotenv import load_dotenv

# Load API keys from .env
load_dotenv()

# Ensure the root directory is in the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.intent_analyst import run_analyst_only
from agents.graph import stream_execution
from db.crud import save_backtest, save_agent_logs
from ui.demo_mode import DEMO_STRATEGIES

def warmup_demos():
    print("[START] Warming up APEX Quant-Forge Demo Strategies...")
    
    for name, config in DEMO_STRATEGIES.items():
        print(f"\n[RUNNING] Starting execution for: {name}")
        prompt = config["prompt"]
        
        # 1. Run Analyst
        analyst_result = run_analyst_only(prompt)
        if analyst_result.get("last_error"):
            print(f"[FAILED] Failed to analyze intent for {name}: {analyst_result['last_error']}")
            continue
            
        # 2. Build Execution State
        exec_state = {
            "user_prompt": prompt,
            "ai_filter_enabled": True,
            "ai_confidence_threshold": 0.5,
            "ticker": config["ticker"],
            "strategy_name": analyst_result.get("strategy_name", name),
            "strategy_type": config["strategy_type"],
            "date_start": config["date_start"],
            "date_end": config["date_end"],
            "strategy_description": analyst_result.get("strategy_description", prompt),
            "generated_code": "",
            "retry_count": 0,
            "execution_success": False,
            "last_error": "",
            "result_json": {},
            "agent_logs": analyst_result.get("agent_logs", []),
        }

        # 3. Stream through LangGraph
        final_state = exec_state.copy()
        for snapshot in stream_execution(exec_state):
            final_state = snapshot

        # 4. Cache Results
        if final_state.get("execution_success") and final_state.get("result_json"):
            result = final_state["result_json"]
            
            # Persist to SQLite
            sid = save_backtest(
                user_prompt=prompt,
                ticker=config["ticker"],
                strategy_name=analyst_result.get("strategy_name", name),
                generated_code=final_state.get("generated_code", ""),
                result=result,
            )
            save_agent_logs(sid, final_state.get("agent_logs", []))
            
            print(f"[SUCCESS] Successfully cached {name}! Return: {result.get('total_return', 0):.2f}%")
        else:
            print(f"[FAILED] Execution failed for {name}. Error: {final_state.get('last_error')[:100]}")

if __name__ == "__main__":
    warmup_demos()
    print("\n[DONE] Warmup Complete! You are ready for your presentation.")
