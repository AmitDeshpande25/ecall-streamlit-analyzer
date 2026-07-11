"""
agent.py
Assembles the LangGraph graph and exposes a simple run_analysis() function
for the Streamlit app to call. Same pattern as a minimal single-node graph:

    START -> analyze_log -> END

Kept as a graph (rather than just calling tools.py directly) so it's easy
to extend later — e.g. add a routing node that picks a different prompt
for manual vs. automatic eCall logs, or a retry node on parse failure.
"""

from langgraph.graph import StateGraph, END

from .state import ECallState
from .nodes import analyze_log_node


def build_graph():
    builder = StateGraph(ECallState)
    builder.add_node("analyze_log", analyze_log_node)
    builder.set_entry_point("analyze_log")
    builder.add_edge("analyze_log", END)
    return builder.compile()


_graph = None  # built lazily and cached so Streamlit doesn't rebuild it on every rerun


def get_graph():
    global _graph
    if _graph is None:
        _graph = build_graph()
    return _graph


def run_analysis(log_content: str) -> ECallState:
    """Entry point used by the Streamlit UI."""
    graph = get_graph()
    return graph.invoke({"log_content": log_content})
