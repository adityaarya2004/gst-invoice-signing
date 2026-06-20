"""Light / dark theme styles for the Streamlit app."""

from __future__ import annotations

import streamlit as st

THEME_OPTIONS = ("Auto (System)", "Light", "Dark")

_LIGHT_CSS = """
.stApp,
[data-testid="stAppViewContainer"],
[data-testid="stAppViewContainer"] > .main {
    background-color: #f8f9fb;
    color: #1a1a1a;
}
section[data-testid="stSidebar"] {
    background-color: #ffffff;
}
section[data-testid="stSidebar"] * {
    color: #1a1a1a !important;
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
    background-color: #161b22;
}
section[data-testid="stSidebar"] * {
    color: #fafafa !important;
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

_AUTO_CSS = f"""
@media (prefers-color-scheme: light) {{
    {_LIGHT_CSS}
}}
@media (prefers-color-scheme: dark) {{
    {_DARK_CSS}
}}
"""

_THEME_CSS = {
    "Light": _LIGHT_CSS,
    "Dark": _DARK_CSS,
    "Auto (System)": _AUTO_CSS,
}


def render_theme_selector() -> str:
    """Show theme control in the sidebar and apply selected styles."""
    with st.sidebar:
        st.header("Appearance")
        theme = st.radio(
            "Background theme",
            THEME_OPTIONS,
            index=0,
            help="Auto follows your device light/dark setting.",
        )

    css = _THEME_CSS[theme]
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)
    return theme
