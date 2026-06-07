"""
A2A Demo — Streamlit Chat UI

Chat window with live request/response trace.
Shows exactly how the message flows through the A2A protocol
and which agent handled it.

Run:
    streamlit run ui.py
"""
import asyncio
import streamlit as st
from a2a.runner import run_agent_with_trace


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

# ── Helpers ───────────────────────────────────────────────────────────────────

def render_trace(traces: list, container):
    """Renders the trace steps into the given streamlit container."""
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


async def process_query(user_message: str, trace_container) -> tuple[str, list]:
    """
    Runs the agent trace, updates the trace panel live after each step.
    Returns (final_answer, traces).
    Defined at module level to avoid nonlocal scope issues.
    """
    traces = []
    result = {"text": ""}

    async for item in run_agent_with_trace(user_message):
        if item["type"] == "trace":
            traces.append(item)
            render_trace(traces, trace_container)   # update live after each step
        elif item["type"] == "result":
            result["text"] = item["text"]

    return result["text"], traces


# ── Session state ─────────────────────────────────────────────────────────────

if "messages" not in st.session_state:
    st.session_state.messages = []   # list of {role, content, traces}

# ── Header ────────────────────────────────────────────────────────────────────

st.title("🌐 A2A Multi-Agent Demo")
st.caption("One endpoint · Orchestrator routes to Weather Agent or Stock Agent")

# ── Layout — chat left, trace right ──────────────────────────────────────────

chat_col, trace_col = st.columns([1, 1], gap="large")

# ── Chat column ───────────────────────────────────────────────────────────────

with chat_col:
    st.subheader("💬 Chat")

    # Render existing messages
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    user_input = st.chat_input(
        "Ask about weather or stocks... e.g. 'weather in Mumbai' or 'analyse AAPL'"
    )

# ── Trace column ──────────────────────────────────────────────────────────────

with trace_col:
    st.subheader("🔍 Live Request Flow")
    st.caption("Watch how your message travels through the A2A protocol")

    # Show last conversation's trace if no new input
    trace_container = st.empty()
    if not user_input and st.session_state.messages:
        last = next(
            (m for m in reversed(st.session_state.messages) if m["role"] == "assistant"),
            None
        )
        if last and last.get("traces"):
            render_trace(last["traces"], trace_container)

# ── Process new input ─────────────────────────────────────────────────────────

if user_input:
    # Show user message immediately
    with chat_col:
        with st.chat_message("user"):
            st.markdown(user_input)

    # Show spinner while processing, trace updates live in trace_col
    with chat_col:
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                final_answer, traces = asyncio.run(
                    process_query(user_input, trace_container)
                )
            st.markdown(final_answer)

    # Save both messages to history
    st.session_state.messages.append({"role": "user",      "content": user_input,    "traces": []})
    st.session_state.messages.append({"role": "assistant", "content": final_answer,  "traces": traces})

# ── Sidebar ───────────────────────────────────────────────────────────────────

with st.sidebar:
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

    st.markdown("**How it works:**")
    st.markdown(
        """
        1. You type a message  
        2. A2A server receives it  
        3. Orchestrator reads your intent  
        4. Routes to Weather or Stock agent  
        5. Agent calls its tool  
        6. Response comes back  
        """
    )

    if st.button("Clear chat"):
        st.session_state.messages = []
        st.rerun()
