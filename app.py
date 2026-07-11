"""
app.py
Streamlit entry point. Run with: streamlit run app.py

Handles: optional password gate, file upload (any text-based format),
calling the agent, and rendering the analysis as a dashboard.
"""

import streamlit as st

from ecall_agent.agent import run_analysis
from ecall_agent.config import APP_PASSWORD

st.set_page_config(
    page_title="eCall Log Analyst",
    page_icon="⚡",
    layout="centered",
)

# ---------------------------------------------------------------------------
# Styling — dark instrument-panel palette to match the automotive/telematics
# domain (amber/green/red mirror real dashboard telltale colors).
# ---------------------------------------------------------------------------
st.markdown(
    """
    <style>
    .stApp { background-color: #0E1420; color: #E8ECF1; }
    section[data-testid="stFileUploaderDropzone"] {
        background-color: #101724; border: 1.5px dashed #2A3341; border-radius: 14px;
    }
    div[data-testid="stMetric"] {
        background-color: #101724; border: 1px solid #2A3341; border-radius: 10px; padding: 10px 14px;
    }
    .stage-card {
        border: 1px solid #2A3341; border-radius: 10px; background: #101724;
        padding: 10px 14px; margin-bottom: 8px;
    }
    .pill {
        display: inline-block; border-radius: 7px; padding: 3px 10px; font-size: 12.5px;
        font-weight: 600; margin-right: 6px; border: 1px solid #2A3341;
    }
    .result-banner {
        border-radius: 12px; padding: 14px 18px; margin-bottom: 18px; border: 1px solid;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

STATUS_COLORS = {"ok": "#3DDC84", "warn": "#F5A623", "fail": "#FF5A5F"}
RESULT_COLORS = {"PASS": "#3DDC84", "FAIL": "#FF5A5F", "WARN": "#F5A623", "UNKNOWN": "#7C8798"}

# ---------------------------------------------------------------------------
# Optional shared-password gate
# ---------------------------------------------------------------------------
if APP_PASSWORD:
    if "unlocked" not in st.session_state:
        st.session_state.unlocked = False

    if not st.session_state.unlocked:
        st.markdown("### 🔒 This tool is password-protected")
        st.caption("Ask your team lead for the shared access password.")
        pw = st.text_input("Password", type="password")
        if st.button("Unlock →"):
            if pw == APP_PASSWORD:
                st.session_state.unlocked = True
                st.rerun()
            else:
                st.error("Incorrect password.")
        st.stop()

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
st.markdown("## ⚡ eCall Log Analyst")
st.caption("Telematics diagnostic agent · EN 16072 / MSD / TS 26.267 · powered by Groq")

# ---------------------------------------------------------------------------
# Upload
# ---------------------------------------------------------------------------
uploaded = st.file_uploader(
    "Drop an eCall log file here",
    type=None,  # accept any format — read as text regardless of extension
    help=".log · .txt · .csv · .json — any format, any source system",
)

if uploaded is not None:
    try:
        log_content = uploaded.read().decode("utf-8", errors="replace")
    except Exception as e:
        st.error(f"Could not read this file: {e}")
        st.stop()

    with st.expander(f"📄 {uploaded.name} — {len(log_content):,} characters", expanded=False):
        st.code(log_content[:1500] + ("\n…" if len(log_content) > 1500 else ""), language="text")

    if st.button("Analyze log →", type="primary"):
        with st.spinner("Reconstructing call flow and cross-checking log layers…"):
            state = run_analysis(log_content)

        if state.get("error"):
            st.error(f"⚠ {state['error']}")
        else:
            result = state["result"]

            # --- Result banner ---
            overall = result.get("overall_result", "UNKNOWN")
            color = RESULT_COLORS.get(overall, "#7C8798")
            scenario = result.get("scenario", {}) or {}
            st.markdown(
                f"""<div class="result-banner" style="border-color:{color};">
                <span style="color:{color};font-size:20px;font-weight:700;">{overall}</span><br/>
                <span style="color:#7C8798;font-size:13px;">
                {scenario.get('trigger_type') or 'eCall'} ·
                {scenario.get('standard') or 'standard n/a'} ·
                {scenario.get('network') or 'network n/a'}
                </span></div>""",
                unsafe_allow_html=True,
            )

            # --- Timeline ---
            timeline = result.get("timeline") or []
            if timeline:
                st.markdown("#### Call flow timeline")
                cols = st.columns(len(timeline))
                for col, stage in zip(cols, timeline):
                    status = stage.get("status", "ok")
                    scolor = STATUS_COLORS.get(status, "#3DDC84")
                    with col:
                        st.markdown(
                            f"""<div class="stage-card">
                            <div style="color:{scolor};font-weight:700;font-size:12px;">{status.upper()}</div>
                            <div style="font-weight:600;font-size:12.5px;margin:4px 0;">{stage.get('stage','')}</div>
                            <div style="color:#7C8798;font-size:10.5px;">{stage.get('timestamp') or ''}</div>
                            </div>""",
                            unsafe_allow_html=True,
                        )
                        with st.expander("detail", expanded=False):
                            st.caption(stage.get("detail", ""))

            # --- Point of failure ---
            pof = result.get("point_of_failure") or {}
            if pof.get("found"):
                st.markdown("#### Point of failure")
                st.error(f"**{pof.get('stage','')}**\n\n{pof.get('evidence','')}")

            # --- Root causes ---
            root_causes = result.get("root_causes") or []
            if root_causes:
                st.markdown("#### Root cause analysis")
                for rc in root_causes:
                    conf = rc.get("confidence", "low")
                    conf_color = {"high": "#3DDC84", "medium": "#F5A623", "low": "#7C8798"}.get(conf, "#7C8798")
                    st.markdown(
                        f"""<div class="stage-card">
                        <b>{rc.get('cause','')}</b>
                        <span style="float:right;color:{conf_color};font-size:11px;font-weight:700;text-transform:uppercase;">{conf}</span>
                        <div style="color:#9AA5B4;font-size:12.5px;margin-top:6px;">{rc.get('evidence','')}</div>
                        </div>""",
                        unsafe_allow_html=True,
                    )

            # --- Classification ---
            classification = result.get("classification") or {}
            if classification:
                st.markdown("#### Classification")
                c1, c2 = st.columns(2)
                c1.metric("Category", classification.get("category", "—"))
                c2.metric("Severity", classification.get("severity", "—"))
                st.caption(classification.get("justification", ""))

            # --- Defect draft ---
            defect = result.get("defect") or {}
            if defect.get("title"):
                st.markdown("#### Defect draft")
                defect_text = (
                    f"Title: {defect.get('title','')}\n\n"
                    f"Category: {classification.get('category','')}\n"
                    f"Severity: {classification.get('severity','')}\n\n"
                    f"Steps to Reproduce:\n{defect.get('steps_to_reproduce','')}\n\n"
                    f"Expected:\n{defect.get('expected','')}\n\n"
                    f"Actual:\n{defect.get('actual','')}\n\n"
                    f"Root Cause:\n"
                    + "\n".join(
                        f"- {rc.get('cause','')} ({rc.get('confidence','')} confidence): {rc.get('evidence','')}"
                        for rc in root_causes
                    )
                )
                st.code(defect_text, language="text")  # st.code has a built-in copy button
                st.caption("Copy icon in the top-right of the box above → paste directly into your defect tool.")

            # --- Missing info ---
            missing = result.get("missing_info") or []
            if missing:
                st.markdown("#### Needed to confirm root cause")
                for m in missing:
                    st.markdown(f"- {m}")

            if overall == "PASS":
                st.success("✓ No defect-worthy deviation found in this log. Safe to close as PASS.")
else:
    st.info("Upload a log file above, then click **Analyze log** to run the agent.")
