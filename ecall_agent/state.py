"""
state.py
The shared state object that flows through the LangGraph graph. Every node
receives this and returns a partial update that gets merged back in.
"""

from typing import TypedDict, Optional, Dict, Any


class ECallState(TypedDict, total=False):
    log_content: str                    # raw log text submitted by the user
    result: Optional[Dict[str, Any]]    # structured analysis result (see config.SYSTEM_PROMPT schema)
    error: Optional[str]                # populated if analysis failed
