from __future__ import annotations

import streamlit as st

from app.ui.onboarding import render_cards
from app.ui.strings import t


def main() -> None:
    st.set_page_config(page_title=t("app_title"), page_icon=":scroll:")
    st.title(t("app_title"))

    if "onboarded" not in st.session_state:
        render_cards()
        if st.button("Got it"):
            st.session_state["onboarded"] = True
            st.rerun()
        return

    st.caption(t("data_disclosure"))
    question = st.text_area(t("input_placeholder"), height=120)
    if st.button("Ask") and question.strip():
        with st.spinner("Thinking…"):
            import httpx

            r = httpx.post(
                "http://127.0.0.1:8000/ask",
                json={"user_email": st.session_state.get("user_email", "anonymous@example.com"), "question": question},
                timeout=120,
            )
            r.raise_for_status()
            data = r.json()

        if data.get("answer"):
            st.markdown(data["answer"])
        st.markdown("---")
        st.markdown(data.get("authority_block", ""))
        st.info(f"**Confidence:** {data['bucket']} — {data['reason']}")
        for note in data.get("notes", []):
            st.warning(note)
        if data.get("escalated"):
            st.success(t("escalate_framing"))
            with st.expander("Escalation brief"):
                st.code(data["brief"])


if __name__ == "__main__":
    main()
