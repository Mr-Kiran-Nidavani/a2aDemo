"""
A2A Demo — Streamlit Chat UI

Chat window with optional live request/response trace.
Toggle "Show request trace" in the sidebar to switch modes.

Run:
    streamlit run ui.py
"""
import asyncio
import streamlit as st
from clientAgent.tracer import run_agent_with_trace  # noqa: E402
from clientAgent.runner import run_agent  # noqa: E402


# ── Page config ───────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="A2A Agent Demo",
    page_icon="🤖",
    layout="wide"
)

# ── Styles ────────────────────────────────────────────────────────────────────

st.markdown(
    """
    <style>
    .trace-box {
        background: #1e1e2e;
        border-left: 3px solid #7c3aed;
        border-radius: 6px;
        padding: 10px 14px;
        margin: 4px 0;
        font-family: monospace;
        font-size: 13px;
        color: #cdd6f4;
    }
    .trace-label {
        font-weight: bold;
        color: #cba6f7;
        font-size: 14px;
    }
    .trace-detail {
        color: #a6e3a1;
        white-space: pre-wrap;
        margin-top: 4px;
        font-size: 12px;
    }
    .step-badge {
        background: #7c3aed;
        color: white;
        border-radius: 10px;
        padding: 1px 8px;
        font-size: 11px;
        margin-right: 6px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ── Session state ─────────────────────────────────────────────────────────────

if "messages" not in st.session_state:
    st.session_state.messages = []   # list of {role, content, traces}

# ── Sidebar ───────────────────────────────────────────────────────────────────

with st.sidebar:
    st.header("Settings")

    show_trace = st.checkbox(
        "Show request trace",
        value=True,
        help="ON — shows live step-by-step flow through the A2A protocol.\nOFF — just returns the answer, faster."
    )

    st.divider()
    st.header("Quick Reference")

    st.markdown("**Try these queries:**")
    st.code("weather in Bangalore")
    st.code("How is the weather in Delhi?")
    st.code("Is it raining in Mumbai?")
    st.code("Give me analysis of AAPL")
    st.code("Should I buy TSLA?")
    st.code("How is NVDA stock doing?")
    st.code("Quick look at RELIANCE")

    st.divider()

    st.markdown("**Cities:**")
    st.markdown("`Bangalore` `Mumbai` `Delhi`  \n`Chennai` `Hyderabad` `Kolkata` `Pune`")

    st.markdown("**Stocks:**")
    st.markdown("`AAPL` `TSLA` `NVDA` `GOOGL`  \n`MSFT` `AMZN` `META` `NFLX`  \n`RELIANCE` `TCS` `INFY`")

    st.divider()

    if st.button("Clear chat"):
        st.session_state.messages = []
        st.rerun()

# ── Helpers ───────────────────────────────────────────────────────────────────

def render_trace(traces: list, container):
    """Renders trace steps into the given Streamlit container."""
    with container.container():
        for t in traces:
            st.markdown(
                f"""
                <div class="trace-box">
                    <div class="trace-label">
                        <span class="step-badge">Step {t['step']}</span>
                        {t['icon']} {t['label']}
                    </div>
                    <div class="trace-detail">{t['detail']}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )


async def process_with_trace(user_message: str, trace_container) -> tuple[str, list]:
    """Runs tracer — yields live steps, returns (answer, traces)."""
    traces = []
    result = {"text": ""}

    async for item in run_agent_with_trace(user_message):
        if item["type"] == "trace":
            traces.append(item)
            render_trace(traces, trace_container)
        elif item["type"] == "result":
            result["text"] = item["text"]

    return result["text"], traces


async def process_simple(user_message: str) -> tuple[str, list]:
    """Runs plain runner — no trace, just the answer."""
    answer = await run_agent(user_message)
    return answer, []


# ── Header ────────────────────────────────────────────────────────────────────

st.title("🌐 A2A Multi-Agent Demo")
st.caption("Client discovers remote agents · routes by skill tags · no orchestrator")

# ── Layout ────────────────────────────────────────────────────────────────────

# Show trace column only when trace mode is on
if show_trace:
    chat_col, trace_col = st.columns([1, 1], gap="large")
else:
    chat_col = st.container()
    trace_col = None

# ── Chat column ───────────────────────────────────────────────────────────────

with chat_col:
    st.subheader("💬 Chat")

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    user_input = st.chat_input(
        "Ask about weather or stocks... e.g. 'weather in Mumbai' or 'analyse AAPL'"
    )

# ── Trace column (only when enabled) ─────────────────────────────────────────

trace_container = None
if show_trace and trace_col:
    with trace_col:
        st.subheader("🔍 Live Request Flow")
        st.caption("Watch how your message travels through the A2A protocol")

        trace_container = st.empty()

        # Keep last trace visible between messages
        if not user_input and st.session_state.messages:
            last = next(
                (m for m in reversed(st.session_state.messages) if m["role"] == "assistant"),
                None
            )
            if last and last.get("traces"):
                render_trace(last["traces"], trace_container)

# ── Process input ─────────────────────────────────────────────────────────────

if user_input:
    with chat_col:
        with st.chat_message("user"):
            st.markdown(user_input)

    with chat_col:
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                if show_trace and trace_container is not None:
                    # Trace mode — live step-by-step flow
                    final_answer, traces = asyncio.run(
                        process_with_trace(user_input, trace_container)
                    )
                else:
                    # Simple mode — direct call, no trace overhead
                    final_answer, traces = asyncio.run(
                        process_simple(user_input)
                    )
            st.markdown(final_answer)

    st.session_state.messages.append({"role": "user",      "content": user_input,   "traces": []})
    st.session_state.messages.append({"role": "assistant", "content": final_answer, "traces": traces})
