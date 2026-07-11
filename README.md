# eCall Log Analyst — Streamlit Agent

A LangGraph-based agent, wrapped in a Streamlit UI, that analyzes eCall
telematics test logs (any text format) and produces a call-flow timeline,
root cause analysis, severity classification, and a ready-to-paste defect
draft — so a tester can go from "here's a log" to "here's the defect" in
one step.

It supports two interchangeable LLM providers, switched with one setting:
- **Ollama** (default) — runs entirely on your own machine. No API key,
  no rate limits, no cost, no internet needed once the model is downloaded.
- **Groq** — cloud API. Faster to set up, but subject to Groq's rate limits
  and requires an API key.

This is the same agent from earlier in this project, rebuilt as a proper
Python package (LangGraph `agent.py` / `nodes.py` / `state.py` / `tools.py`
/ `config.py`) instead of a single JS/HTML file, and served through
Streamlit instead of a hand-built Express + HTML frontend.

## What each file does

```
ecall-streamlit-analyzer/
├── app.py                     Streamlit UI — file upload, password gate, renders results
├── ecall_agent/
│   ├── __init__.py            Public API of the package (run_analysis, build_graph)
│   ├── state.py                ECallState — the shared state passed through the graph
│   ├── config.py                Settings: Groq API key/model, app password, the system prompt
│   ├── tools.py                  The actual Groq API call + JSON parsing (the "tool" the agent uses)
│   ├── nodes.py                   One graph node: analyze_log_node, calls tools.py, fills state
│   └── agent.py                    Builds the LangGraph graph: START -> analyze_log -> END
├── requirements.txt
├── .env.example                For local dev (copy to .env)
└── .streamlit/secrets.toml.example   For Streamlit Cloud deploy (see below)
```

**Why a graph for a single step?** Right now the graph is intentionally
minimal — one node, `analyze_log`, that does everything. It's built this
way (rather than just calling `tools.py` directly from `app.py`) so it's
trivial to extend later without restructuring: e.g. add a node that routes
manual vs. automatic eCall logs to different prompts, a validation node
that checks the log actually looks like an eCall log before spending an
API call, or a retry node if the model's JSON fails to parse.

## How the analysis works

1. `app.py` reads the uploaded file as raw text (works for `.log`, `.txt`,
   `.csv`, `.json`, or any other text-based export).
2. It calls `ecall_agent.agent.run_analysis(log_text)`.
3. That runs the graph: `analyze_log_node` sends the log to Groq
   (`tools.call_groq_analysis`) with a system prompt (`config.SYSTEM_PROMPT`)
   that knows eCall's protocol stages (EN 16072 / MSD / TS 26.267) and
   forces a structured JSON response.
4. The result lands back in `ECallState["result"]`, and `app.py` renders it
   as a dashboard: PASS/FAIL/WARN banner, a stage-by-stage timeline, root
   causes ranked by confidence, classification, and a defect draft you can
   copy straight into Jira/ADO.

## 0. Set up Ollama (default provider — skip this if using Groq instead)

1. Download and install Ollama: **https://ollama.com/download** (Windows, Mac, Linux).
2. Open a terminal and pull a model (one-time download, a few GB):
   ```bash
   ollama pull llama3.1:8b
   ```
3. That's it — Ollama runs a local server automatically in the background
   after install (`http://localhost:11434`). No further setup needed.

**Hardware note:** `llama3.1:8b` wants roughly 8GB+ of RAM. If your machine
struggles, try a smaller model instead, e.g. `ollama pull llama3.2:3b`, and
set `OLLAMA_MODEL=llama3.2:3b` in your `.env`.

**Limitation:** Ollama only works for **local** use — Streamlit Community
Cloud's servers don't have Ollama installed, so a Cloud-deployed app must
use `LLM_PROVIDER=groq` instead (see section 2 below). Ollama is for running
the app on your own laptop only.

## 1. Run it locally

Requires Python 3.10+.

```bash
cd ecall-streamlit-analyzer
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# .env already defaults to LLM_PROVIDER=ollama — no key needed if you did step 0.
# To use Groq instead, set LLM_PROVIDER=groq and paste in your GROQ_API_KEY.

python -m streamlit run app.py
```

This opens `http://localhost:8501` in your browser — that's the app running locally.

## 2. Get a public URL (Streamlit Community Cloud — free, easiest)

**Important:** Ollama can't run on Streamlit Community Cloud (their servers
don't have it installed) — a deployed app must use `LLM_PROVIDER=groq`.
Ollama is for local use only; Groq is what makes this work as a public URL.

This is the simplest way to get a URL you can access from anywhere,
purpose-built for Streamlit apps:

1. Push this folder to a GitHub repo (public or private).
2. Go to **https://share.streamlit.io** and sign in with GitHub.
3. Click **New app**, pick your repo/branch, and set the main file path to `app.py`.
4. Before/after deploying, open **Settings → Secrets** on the app and paste
   in the contents of `.streamlit/secrets.toml.example`, filled in with your
   real values:
   ```toml
   LLM_PROVIDER = "groq"
   GROQ_API_KEY = "gsk_..."
   APP_PASSWORD = "choose-a-shared-password"
   ```
5. Deploy. You'll get a URL like `https://your-app-name.streamlit.app` —
   share that with your team.

No server management, no Dockerfile, no billing setup beyond your Groq key.

### Alternative hosts
If you'd rather not use Streamlit Community Cloud, this app also runs fine
on **Render**, **Railway**, or a VPS — same idea as any Python web app:
`pip install -r requirements.txt` then `streamlit run app.py --server.port $PORT --server.address 0.0.0.0`.
Set `LLM_PROVIDER=groq`, `GROQ_API_KEY`, and `APP_PASSWORD` as environment
variables on whichever host you pick (they're read via `.env`/`os.getenv` as
a fallback if `st.secrets` isn't available). If your host is actually a VPS
you control (not a shared platform like Render/Railway), you could instead
install Ollama on that VPS itself and keep `LLM_PROVIDER=ollama` — just
know you're then responsible for that server's uptime and resources.

## 3. Access control

Same idea as the earlier Node version, adapted to Streamlit:

- Set `APP_PASSWORD` (in `.env` locally, or Streamlit secrets when deployed)
  and visitors must enter it once before the uploader appears.
- It's stored in `st.session_state`, so it persists for that browser tab's
  session but isn't remembered permanently like a cookie — closing the tab
  and reopening the app will ask again. That's a deliberate simpler/safer
  default than the localStorage approach used in the Node version.
- Leave `APP_PASSWORD` unset to disable the gate entirely (local dev only).
- This is one shared password for the team, not individual logins — no
  per-user audit trail. For that, put real auth (SSO) in front of it instead.

## 4. Customizing

- Change the model: set `GROQ_MODEL` (defaults to `openai/gpt-oss-120b`;
  `openai/gpt-oss-20b` is faster/cheaper if you want to try it).
- Tune the analysis behavior: edit `SYSTEM_PROMPT` in `ecall_agent/config.py`
  — e.g. add your specific DTC codes, your defect tool's exact field names,
  or a different regional eCall standard (ERA-GLONASS, etc.).
- Extend the graph: add a new function to `nodes.py` and wire it into
  `agent.py`'s `build_graph()` with `add_node` / `add_edge`.
