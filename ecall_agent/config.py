"""
config.py
Central place for settings, environment variables, and the system prompt
used to instruct the model. Keeping this separate from the rest of the
agent makes it easy to swap models, providers, or tune the prompt without
touching the graph logic.
"""

import os

try:
    import streamlit as st
except ImportError:  # config.py may be imported outside a Streamlit context (e.g. tests)
    st = None

from dotenv import load_dotenv

load_dotenv()


def _get_setting(key: str, default: str = "") -> str:
    """
    Look up a setting from Streamlit secrets first (used on Streamlit
    Community Cloud), then fall back to environment variables (used for
    local development via .env).
    """
    if st is not None:
        try:
            if key in st.secrets:
                return st.secrets[key]
        except Exception:
            pass  # no secrets.toml present locally — that's fine
    return os.getenv(key, default)


# --- Groq API settings ---
GROQ_API_KEY = _get_setting("GROQ_API_KEY", "")
GROQ_MODEL = _get_setting("GROQ_MODEL", "openai/gpt-oss-120b")
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

# --- Optional shared-password gate ---
APP_PASSWORD = _get_setting("APP_PASSWORD", "")

# --- Analysis limits ---
MAX_LOG_CHARS = 20000
MAX_OUTPUT_TOKENS = 2000
REQUEST_TIMEOUT_SECONDS = 60

# --- System prompt fed to the model for every analysis ---
SYSTEM_PROMPT = """You are an expert Telematics Test Engineer specialized in analyzing eCall (Emergency Call) system logs (EN 16072 / EN 15722 MSD / 3GPP TS 26.267 in-band modem / ERA-GLONASS variants).

You will receive raw log content in ANY format (plain text, .log, .csv-like, .json, structured or unstructured). Parse it regardless of exact format. Reconstruct the call flow (trigger -> network registration -> call setup -> MSD transmission -> PSAP ack -> clear-down), find the point of deviation if any, and produce a defect-ready summary.

Respond with ONLY a single valid JSON object. No markdown fences, no preamble, no trailing text. Keep every string field short and concise. Use only evidence present in the log. If a value cannot be determined, use null (or [] for arrays). Do not fabricate timestamps or values.

JSON schema:
{
  "overall_result": "PASS" | "FAIL" | "WARN" | "UNKNOWN",
  "scenario": { "trigger_type": string|null, "standard": string|null, "network": string|null },
  "timeline": [ { "stage": string, "timestamp": string|null, "status": "ok"|"warn"|"fail", "detail": string } ],
  "point_of_failure": { "found": boolean, "stage": string|null, "evidence": string|null },
  "root_causes": [ { "cause": string, "confidence": "high"|"medium"|"low", "evidence": string } ],
  "classification": {
    "category": "Network"|"GNSS"|"MSD"|"Modem"|"Application"|"Hardware"|"Config"|"Test Environment"|"None",
    "severity": "Critical"|"Major"|"Minor"|"None",
    "justification": string
  },
  "defect": { "title": string|null, "steps_to_reproduce": string|null, "expected": string|null, "actual": string|null },
  "missing_info": [string]
}

Limit timeline to at most 8 key stages. Limit root_causes to at most 3, ranked by evidence strength. If overall_result is PASS, defect fields should be null and root_causes/point_of_failure should reflect no failure found."""
