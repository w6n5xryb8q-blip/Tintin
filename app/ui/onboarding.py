from __future__ import annotations

from app.ui.strings import t

CARDS = [
    {
        "title": "What I do",
        "body": (
            "I help you find the right IRS publication and section for a question. "
            "I quote the publication and list the law and court cases behind it."
        ),
    },
    {
        "title": "What I don't do",
        "body": (
            "No state or local tax. No reading specific client returns. No legal advice. "
            "Anything outside my scope goes to a tax pro with a ready-made brief."
        ),
    },
    {
        "title": "How confidence works",
        "body": (
            "Every answer has a label: Solid, Mostly solid, Use with caution, or Escalate. "
            "The label is built from real signals (retrieval match, quote check, "
            "consistency, currency). It is not a fake percentage."
        ),
    },
    {
        "title": "Privacy",
        "body": t("data_disclosure"),
    },
]


def render_cards():
    """Streamlit hook — imported lazily by the chat surface so tests don't need streamlit."""
    import streamlit as st

    st.subheader("Welcome")
    for card in CARDS:
        with st.container(border=True):
            st.markdown(f"**{card['title']}**")
            st.write(card["body"])
