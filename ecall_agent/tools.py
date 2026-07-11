"""
tools.py
External-facing calls the agent uses. Right now there's one tool: calling
the Groq API to analyze a log. Kept separate from nodes.py so the "how do
I talk to the model" logic is isolated from "what does the graph do".
"""

import json
import requests

from .config import (
    LLM_PROVIDER,
    OLLAMA_BASE_URL,
    OLLAMA_MODEL,
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


def _truncate(log_content: str) -> str:
    if len(log_content) > MAX_LOG_CHARS:
        return log_content[:MAX_LOG_CHARS] + "\n[...truncated for length...]"
    return log_content


def _parse_json_content(text: str) -> dict:
    clean = text.strip().replace("```json", "").replace("```", "").strip()
    try:
        return json.loads(clean)
    except json.JSONDecodeError as e:
        raise AnalysisError(f"Model response could not be parsed as JSON: {e}") from e


def call_ollama_analysis(log_content: str) -> dict:
    """
    Send log content to a local Ollama server for analysis. Requires Ollama
    running locally (https://ollama.com) with a model pulled, e.g.:
        ollama pull llama3.1:8b
    No API key needed — this never leaves your machine.
    """
    if not log_content or not log_content.strip():
        raise AnalysisError("No log content provided.")

    truncated = _truncate(log_content)
    url = f"{OLLAMA_BASE_URL.rstrip('/')}/v1/chat/completions"

    try:
        response = requests.post(
            url,
            headers={"Content-Type": "application/json"},
            json={
                "model": OLLAMA_MODEL,
                "temperature": 0.2,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": f"Analyze this eCall log:\n\n{truncated}"},
                ],
                "stream": False,
                "format": "json",  # Ollama's structured-output hint
            },
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
    except requests.RequestException as e:
        raise AnalysisError(
            f"Could not reach Ollama at {url}. Is Ollama running? "
            f"Start it and make sure you've pulled a model (e.g. 'ollama pull {OLLAMA_MODEL}'). "
            f"Original error: {e}"
        ) from e

    if not response.ok:
        raise AnalysisError(f"Ollama returned an error ({response.status_code}): {response.text}")

    data = response.json()
    try:
        text = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError) as e:
        raise AnalysisError(f"Unexpected response shape from Ollama: {e}") from e

    return _parse_json_content(text)


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

    truncated = _truncate(log_content)

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
        text = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError) as e:
        raise AnalysisError(f"Unexpected response shape from Groq API: {e}") from e

    return _parse_json_content(text)


def call_llm_analysis(log_content: str) -> dict:
    """
    Single entry point nodes.py calls — routes to whichever provider is
    configured via LLM_PROVIDER ("ollama" or "groq"), so the rest of the
    agent never needs to know which one is active.
    """
    if LLM_PROVIDER == "ollama":
        return call_ollama_analysis(log_content)
    elif LLM_PROVIDER == "groq":
        return call_groq_analysis(log_content)
    else:
        raise AnalysisError(
            f"Unknown LLM_PROVIDER '{LLM_PROVIDER}'. Use 'ollama' or 'groq'."
        )
