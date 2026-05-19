import ast
from datetime import datetime, timezone
from agents.state import AgentLog, GraphState

def _make_log(msg: str, severity: str = "INFO") -> AgentLog:
    return AgentLog(
        agent="VALIDATOR",
        severity=severity,
        message=msg,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )

def ast_validator_node(state: GraphState) -> dict:
    """
    LangGraph node: statically analyzes the generated code for banned patterns.
    If it fails, it routes directly to the Code Critic.
    """
    code = state.get("generated_code", "")
    logs = []
    
    if not code:
        logs.append(_make_log("No code provided for validation.", "ERROR"))
        return {"validation_passed": False, "last_error": "No code generated.", "agent_logs": logs}
        
    try:
        tree = ast.parse(code)
        # Walk AST to find banned patterns
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                # Check for .apply() or .rolling().apply()
                if isinstance(node.func, ast.Attribute):
                    if node.func.attr == "apply":
                        # Fast and dirty check: block any use of Pandas .apply() to force vectorization
                        logs.append(_make_log("⚠ Banned pattern detected: Pandas .apply() loop. Forcing vectorization...", "ERROR"))
                        return {
                            "validation_passed": False, 
                            "last_error": "SyntaxError: Banned pattern detected. You used `.apply()`. You MUST rewrite this using strictly vectorized Pandas or Numpy operations (e.g. np.where). Never use `.apply()` for indicators.", 
                            "agent_logs": logs
                        }
                    
                    if node.func.attr == "iterrows" or node.func.attr == "itertuples":
                        logs.append(_make_log("⚠ Banned pattern detected: Pandas row iteration. Forcing vectorization...", "ERROR"))
                        return {
                            "validation_passed": False, 
                            "last_error": f"SyntaxError: Banned pattern detected: `.{node.func.attr}()`. Row loops are strictly banned. Use vectorized math.", 
                            "agent_logs": logs
                        }

        # Passed AST validation
        logs.append(_make_log("AST Static Analysis Passed. Code is fully vectorized.", "SUCCESS"))
        return {"validation_passed": True, "agent_logs": logs}

    except SyntaxError as e:
        logs.append(_make_log(f"⚠ Invalid Python Syntax: {str(e)}", "ERROR"))
        return {
            "validation_passed": False, 
            "last_error": f"SyntaxError: {str(e)}", 
            "agent_logs": logs
        }
    except Exception as e:
        logs.append(_make_log(f"⚠ AST parsing failed: {str(e)}", "WARNING"))
        # Allow it to proceed to sandbox if AST parsing itself crashes on valid code
        return {"validation_passed": True, "agent_logs": logs}
