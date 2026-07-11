"""
nodes.py
Graph nodes. Each node is a plain function: (state) -> partial state update.
Currently there's a single node, but this is the place to add more later
(e.g. a validation node before analysis, or a follow-up node that drafts
the defect ticket in a different tone).
"""

from .state import ECallState
from .tools import call_groq_analysis, AnalysisError


def analyze_log_node(state: ECallState) -> ECallState:
    """Run the log through the model and store the structured result (or error) in state."""
    try:
        result = call_groq_analysis(state["log_content"])
        return {"result": result, "error": None}
    except AnalysisError as e:
        return {"result": None, "error": str(e)}
    except Exception as e:  # belt-and-braces: never let an unexpected error crash the graph
        return {"result": None, "error": f"Unexpected error: {e}"}
