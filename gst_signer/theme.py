"""Light / dark theme toggle for the Streamlit app."""

from __future__ import annotations

import streamlit as st

_LIGHT_CSS = """
.stApp,
[data-testid="stAppViewContainer"],
[data-testid="stAppViewContainer"] > .main {
    background-color: #f8f9fb;
    color: #1a1a1a;
}
section[data-testid="stSidebar"] {
    display: none;
}
h1, h2, h3, h4, h5, h6, p, label, span, .stMarkdown {
    color: #1a1a1a !important;
}
[data-testid="stFileUploader"] section {
    background-color: #ffffff;
    border: 1px dashed #c9cdd3;
}
[data-testid="stCode"] {
    background-color: #eef0f3 !important;
    color: #1a1a1a !important;
}
"""

_DARK_CSS = """
.stApp,
[data-testid="stAppViewContainer"],
[data-testid="stAppViewContainer"] > .main {
    background-color: #0e1117;
    color: #fafafa;
}
section[data-testid="stSidebar"] {
    display: none;
}
h1, h2, h3, h4, h5, h6, p, label, span, .stMarkdown {
    color: #fafafa !important;
}
[data-testid="stFileUploader"] section {
    background-color: #1c2128;
    border: 1px dashed #484f58;
}
[data-testid="stCode"] {
    background-color: #161b22 !important;
    color: #e6edf3 !important;
}
input, textarea {
    background-color: #1c2128 !important;
    color: #fafafa !important;
}
"""


def _apply_theme(is_dark: bool) -> None:
    css = _DARK_CSS if is_dark else _LIGHT_CSS
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)


def render_theme_toggle() -> None:
    """Show a Light/Dark slide toggle at the top of the page."""
    label_col, toggle_col, mode_col = st.columns([1, 1, 10])

    with label_col:
        st.markdown(
            "<p style='margin:0.4rem 0 0;text-align:right;font-weight:600;'>Light</p>",
            unsafe_allow_html=True,
        )

    with toggle_col:
        st.toggle("Theme", key="dark_mode", label_visibility="collapsed")

    with mode_col:
        if st.session_state.get("dark_mode", False):
            st.markdown(
                "<p style='margin:0.4rem 0 0;font-weight:600;'>Dark</p>",
                unsafe_allow_html=True,
            )

    _apply_theme(st.session_state.get("dark_mode", False))
