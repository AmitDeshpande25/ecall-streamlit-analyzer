"""
tools.py
External-facing calls the agent uses. Right now there's one tool: calling
the Groq API to analyze a log. Kept separate from nodes.py so the "how do
I talk to the model" logic is isolated from "what does the graph do".
"""

import json
import requests

from .config import (
    GROQ_API_KEY,
    GROQ_MODEL,
    GROQ_API_URL,
    SYSTEM_PROMPT,
    MAX_LOG_CHARS,
    MAX_OUTPUT_TOKENS,
    REQUEST_TIMEOUT_SECONDS,
)


class AnalysisError(Exception):
    """Raised when the log analysis call fails or returns something unusable."""


def call_groq_analysis(log_content: str) -> dict:
    """
    Send log content to Groq's chat completions API and return the parsed
    structured JSON result. Raises AnalysisError on any failure.
    """
    if not GROQ_API_KEY:
        raise AnalysisError(
            "GROQ_API_KEY is not set. Add it to your .env file (local) "
            "or Streamlit secrets (deployed)."
        )
    if not log_content or not log_content.strip():
        raise AnalysisError("No log content provided.")

    truncated = log_content
    if len(log_content) > MAX_LOG_CHARS:
        truncated = log_content[:MAX_LOG_CHARS] + "\n[...truncated for length...]"

    try:
        response = requests.post(
            GROQ_API_URL,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {GROQ_API_KEY}",
            },
            json={
                "model": GROQ_MODEL,
                "temperature": 0.2,
                "max_completion_tokens": MAX_OUTPUT_TOKENS,
                "response_format": {"type": "json_object"},
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": f"Analyze this eCall log:\n\n{truncated}"},
                ],
            },
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
    except requests.RequestException as e:
        raise AnalysisError(f"Could not reach Groq API: {e}") from e

    if not response.ok:
        try:
            detail = response.json().get("error", {}).get("message", response.text)
        except Exception:
            detail = response.text
        raise AnalysisError(f"Groq API error ({response.status_code}): {detail}")

    data = response.json()
    try:
        text = data["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError) as e:
        raise AnalysisError(f"Unexpected response shape from Groq API: {e}") from e

    clean = text.replace("```json", "").replace("```", "").strip()
    try:
        return json.loads(clean)
    except json.JSONDecodeError as e:
        raise AnalysisError(
            f"Model response could not be parsed as JSON: {e}"
        ) from e
