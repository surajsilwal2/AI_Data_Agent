"""Streamlit interface for the Data Agent."""

import json
from html import escape
from datetime import datetime

import pandas as pd
import streamlit as st

from agents.sql_analyst import sql_analyst


st.set_page_config(
    page_title="Insight — Data Agent",
    page_icon="✦",
    layout="wide",
    initial_sidebar_state="expanded",
)


def inject_styles() -> None:
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Manrope:wght@400;500;600;700;800&display=swap');
        :root { --ink:#e9edff; --muted:#9ba6c6; --line:rgba(158,174,224,.15); --panel:rgba(19,25,49,.76); --violet:#8873ff; --aqua:#54e1cb; }
        .stApp { background: radial-gradient(circle at 82% -10%, #26365f 0, transparent 30%), radial-gradient(circle at 2% 15%, #24204b 0, transparent 25%), #0b1022; color:var(--ink); font-family:'Manrope', sans-serif; }
        [data-testid="stSidebar"] { background:rgba(10,14,31,.8); border-right:1px solid var(--line); }
        [data-testid="stSidebar"] > div:first-child { padding-top:2rem; }
        h1,h2,h3,p { font-family:'Manrope', sans-serif; }
        .brand { font-size:1.35rem; font-weight:800; letter-spacing:-.05em; display:flex; align-items:center; gap:.6rem; }
        .spark { display:inline-grid; place-items:center; height:28px; width:28px; border-radius:9px; color:#0c1030; background:linear-gradient(135deg,var(--aqua),#a994ff); }
        .eyebrow { color:var(--aqua); font:500 .72rem 'DM Mono',monospace; letter-spacing:.12em; text-transform:uppercase; margin-bottom:.75rem; }
        .hero { max-width:800px; padding:3.1rem 0 1.8rem; }
        .hero h1 { font-size:clamp(2rem,4vw,3.5rem); line-height:1.08; letter-spacing:-.06em; margin:0 0 .9rem; }
        .hero p { color:var(--muted); font-size:1.05rem; line-height:1.7; max-width:620px; }
        .glass { background:var(--panel); border:1px solid var(--line); border-radius:18px; padding:1.15rem 1.25rem; box-shadow:0 15px 50px rgba(0,0,0,.12); }
        .metric-label { font:500 .68rem 'DM Mono',monospace; letter-spacing:.11em; color:var(--muted); text-transform:uppercase; }
        .metric-value { font-size:1.5rem; font-weight:800; margin-top:.25rem; }
        .answer-card { background:linear-gradient(135deg,rgba(56,57,120,.38),rgba(19,25,49,.9)); border:1px solid rgba(136,115,255,.34); border-radius:18px; padding:1.3rem 1.45rem; margin:.6rem 0 1rem; }
        .answer-card p { margin:0; line-height:1.7; color:#edf0ff; }
        .question { color:#c7d0f5; font-size:.91rem; margin:1.2rem 0 .35rem; }
        .status { font:500 .72rem 'DM Mono',monospace; color:var(--aqua); letter-spacing:.08em; text-transform:uppercase; }
        .stChatInput { border:1px solid rgba(136,115,255,.36)!important; border-radius:15px!important; background:rgba(20,26,51,.92)!important; }
        .stButton button { border-radius:10px; border:1px solid var(--line); background:rgba(255,255,255,.04); color:var(--ink); font-weight:600; }
        .stButton button:hover { border-color:var(--violet); color:white; }
        code { font-family:'DM Mono',monospace!important; }
        [data-testid="stDataFrame"] { border:1px solid var(--line); border-radius:12px; overflow:hidden; }
        </style>
        """,
        unsafe_allow_html=True,
    )


def initial_state() -> dict:
    return {
        "messages": [],
        "user_question": "",
        "curated_ques": "",
        "prompt_query_Context": "",
        "generated_sql_query": "",
        "is_safe": "unsafe",
        "comments": "",
        "sql_query_execution_result": "",
        "final_answer": "",
    }


def run_agent(question: str) -> dict:
    state = initial_state()
    state["user_question"] = question
    return sql_analyst.invoke(state)


def show_result(item: dict) -> None:
    result = item["result"]
    question = escape(item["question"])
    answer = escape(result.get("final_answer", "No answer was returned.")).replace("\n", "<br>")
    st.markdown(f'<div class="question">You asked · {question}</div>', unsafe_allow_html=True)
    safety = result.get("is_safe", "unsafe")
    st.markdown(
        f'<div class="status">● {"Query verified" if safety == "safe" else "Query not executed"}</div>',
        unsafe_allow_html=True,
    )
    st.markdown(f'<div class="answer-card"><p>{answer}</p></div>', unsafe_allow_html=True)

    if safety == "safe":
        try:
            execution = json.loads(result.get("sql_query_execution_result", "{}"))
        except json.JSONDecodeError:
            execution = {}
        if execution.get("success"):
            st.caption(f"{execution.get('row_count', 0)} rows returned")
            st.dataframe(pd.DataFrame(execution.get("data", [])), use_container_width=True, hide_index=True)
        elif execution.get("error"):
            st.warning(f"The query could not run: {execution['error']}")
    with st.expander("View generated SQL"):
        st.code(result.get("generated_sql_query", "No SQL generated."), language="sql")
        if result.get("comments"):
            st.caption(f"Safety review: {result['comments']}")


inject_styles()

if "history" not in st.session_state:
    st.session_state.history = []

with st.sidebar:
    st.markdown('<div class="brand"><span class="spark">✦</span> Insight</div>', unsafe_allow_html=True)
    st.caption("Natural-language analytics for your PostgreSQL data.")
    st.divider()
    st.markdown("##### Quick start")
    st.caption("Ask a business question. The agent maps it to read-only SQL, validates it, and explains the result.")
    if st.button("＋ New conversation", use_container_width=True):
        st.session_state.history = []
        st.rerun()
    st.divider()
    st.markdown("##### Example questions")
    examples = [
        "What payment methods do we have?",
        "Show the 10 most highly rated drivers",
        "Which cities have the most rides?",
    ]
    selected_example = None
    for example in examples:
        if st.button(example, key=example, use_container_width=True):
            selected_example = example
    st.divider()
    st.markdown("<span class='status'>● Read-only queries only</span>", unsafe_allow_html=True)

st.markdown(
    """
    <div class="hero">
      <div class="eyebrow">Data analyst · online</div>
      <h1>Answers, directly from your data.</h1>
      <p>Explore your database in plain English. Insight writes and safety-checks SQL before it ever runs.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

metrics = st.columns(3)
metrics[0].markdown('<div class="glass"><div class="metric-label">Mode</div><div class="metric-value">Analysis</div></div>', unsafe_allow_html=True)
metrics[1].markdown('<div class="glass"><div class="metric-label">Safety</div><div class="metric-value">Read-only</div></div>', unsafe_allow_html=True)
metrics[2].markdown(f'<div class="glass"><div class="metric-label">Questions this session</div><div class="metric-value">{len(st.session_state.history):02d}</div></div>', unsafe_allow_html=True)

for entry in st.session_state.history:
    show_result(entry)

question = st.chat_input("Ask anything about your data…") or selected_example
if question:
    with st.spinner("Reviewing your question, preparing a safe query, and analyzing the result…"):
        try:
            response = run_agent(question)
            st.session_state.history.append({
                "question": question,
                "result": response,
                "time": datetime.now().isoformat(),
            })
        except Exception as exc:
            st.error(f"I couldn't complete that analysis: {exc}")
    st.rerun()
