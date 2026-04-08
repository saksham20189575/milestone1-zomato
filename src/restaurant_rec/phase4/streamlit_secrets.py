"""Map Streamlit Cloud / local `st.secrets` into `os.environ` for Groq and other SDKs."""

from __future__ import annotations

import os


def hydrate_groq_key_from_streamlit_secrets() -> None:
    """Set `GROQ_API_KEY` from `st.secrets` when present (Streamlit Cloud dashboard secrets)."""
    try:
        import streamlit as st
    except ImportError:
        return
    try:
        if "GROQ_API_KEY" in st.secrets:
            os.environ["GROQ_API_KEY"] = str(st.secrets["GROQ_API_KEY"])
    except (RuntimeError, FileNotFoundError, TypeError):
        # No secrets file, or outside a Streamlit script run
        pass
