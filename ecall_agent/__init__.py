"""
eCall Log Analyst agent package.

Usage:
    from ecall_agent.agent import run_analysis
    result_state = run_analysis(log_text)
    if result_state.get("error"):
        ...
    else:
        analysis = result_state["result"]
"""

from .agent import run_analysis, build_graph, get_graph
from .state import ECallState

__all__ = ["run_analysis", "build_graph", "get_graph", "ECallState"]
