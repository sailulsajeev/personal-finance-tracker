# src/core/state.py
import streamlit as st

DEFAULT_DISPLAY_CURRENCY = "EUR"

def init_session_state(default_currency: str | None = None):
    if "default_currency" not in st.session_state:
        st.session_state.default_currency = (default_currency or DEFAULT_DISPLAY_CURRENCY).upper()
    if "show_settings" not in st.session_state:
        st.session_state.show_settings = False
    if "show_add_tx" not in st.session_state:
        st.session_state.show_add_tx = False
    if "optimistic_tx" not in st.session_state:
        st.session_state.optimistic_tx = []
    # flash support after rerun
    if st.session_state.get("_flash_success"):
        st.success(st.session_state._flash_success)
        del st.session_state["_flash_success"]
