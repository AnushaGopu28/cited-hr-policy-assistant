
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import streamlit as st
from app.retrieval import retrieve
from app.answer import answer_question

st.set_page_config(
    page_title="Cited HR Policy Assistant",
    page_icon="📚",
    layout="wide"
)

st.title("Cited HR Policy Assistant")

st.caption(
    "Fictional training demo. General information only; "
    "not legal, tax, or immigration advice."
)

question = st.text_area(
    "Ask an onboarding or HR policy question",
    placeholder="How do I submit my timesheet?"
)

if st.button(
    "Ask assistant",
    type="primary",
    disabled=not question.strip()
):
    with st.spinner("Searching approved documents..."):
        passages = retrieve(question)
        response = answer_question(question, passages)

    st.subheader("Answer")
    st.write(response)

    if passages:
        st.subheader("Retrieved references")

        for p in passages:
            with st.expander(
                f"{p['source_title']} — "
                f"{p['section_or_page']} "
                f"(score {p['score']:.3f})"
            ):
                st.write(p["text"])

                if p["source_url"] != "fictional":
                    st.link_button(
                        "Open source",
                        p["source_url"]
                    )

    feedback = st.radio(
        "Was this answer helpful?",
        [
            "No feedback",
            "👍 Yes",
            "👎 No / Report a problem"
        ],
        horizontal=True
    )

    if feedback != "No feedback":
        st.info(
            "Feedback captured for this demo session. "
            "Add persistent storage before production use."
        )
