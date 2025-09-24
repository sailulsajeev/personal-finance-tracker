# src/app.py
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import streamlit as st

from src.services.db import (
    init_db,
    get_session,
    clear_transactions,   # <-- added
    reset_database,       # <-- added
    vacuum,               # <-- optional, added
)
from src.services.settings import load_settings, save_settings
from src.services.currency_converter import CurrencyConverter
from src.services import file_handler

from src.core.state import init_session_state
from src.core.schema import ensure_amount_eur_column_and_backfill
from src.ui.modals import show_add_tx, show_settings
from src.ui.table import render_table
from src.ui.summary import render_summary
from src.ui.reports import render_reports

# -----------------------
# Bootstrap
# -----------------------
st.set_page_config(page_title="Personal Finance Tracker", layout="wide")
init_db()
session = get_session()
_settings_file = load_settings()

# session state defaults + flash handler
init_session_state(default_currency=_settings_file.get("default_currency", "EUR"))

# converter
converter = CurrencyConverter(api_url=_settings_file.get("exchange_api_url"))

# CSS
st.markdown(
    "<style>.main > div.block-container{max-width:1200px; padding:1rem 2rem;}</style>",
    unsafe_allow_html=True,
)

# Modal support
DIALOG_DECORATOR = getattr(st, "dialog", None) or getattr(st, "experimental_dialog", None)
HAS_MODAL = DIALOG_DECORATOR is not None

# Ensure schema/backfill
ensure_amount_eur_column_and_backfill(session, converter)

# -----------------------
# Top bar
# -----------------------
col_left, col_right = st.columns([3, 1])
with col_left:
    st.title("💼 Personal Finance Tracker")
    st.caption("Transactions stored in original currency + normalized EUR. Totals computed in EUR.")
with col_right:
    st.selectbox(
        "Display currency",
        options=[st.session_state.default_currency],
        index=0,
        disabled=True,
        help="Totals are computed in EUR and displayed here converted to this currency.",
    )

    # Mutually exclusive buttons -> only one dialog flag at a time
    if st.button("➕ Add transaction"):
        st.session_state.show_add_tx = True
        st.session_state.show_settings = False

    if st.button("⚙️ Settings"):
        st.session_state.show_settings = True
        st.session_state.show_add_tx = False

# Safety: enforce single-dialog invariant before rendering
if st.session_state.get("show_add_tx") and st.session_state.get("show_settings"):
    # Keep Settings open by default if both somehow became True
    st.session_state.show_add_tx = False

# Render dialogs (each checks the other flag internally too)
show_add_tx(session, converter, HAS_MODAL, DIALOG_DECORATOR)
show_settings(_settings_file, save_settings, HAS_MODAL, DIALOG_DECORATOR)

# -----------------------
# Sidebar import/export
# -----------------------
st.sidebar.header("Data import / export")

uploaded_csv = st.sidebar.file_uploader("Upload transactions CSV", type=["csv"])
if uploaded_csv is not None:
    inserted, skipped, errors = file_handler.import_transactions_from_csv_filelike(uploaded_csv, session)
    st.sidebar.success(f"Inserted: {inserted}, Skipped: {skipped}")
    if errors:
        st.sidebar.error("Some rows had errors (see details).")
        for e in errors:
            st.sidebar.write("-", e)
    ensure_amount_eur_column_and_backfill(session, converter)
    st.session_state._flash_success = "Import finished."
    st.rerun()

uploaded_json = st.sidebar.file_uploader("Upload transactions JSON", type=["json"])
if uploaded_json is not None:
    inserted, skipped, errors = file_handler.import_transactions_from_json_filelike(uploaded_json, session)
    st.sidebar.success(f"Inserted: {inserted}, Skipped: {skipped}")
    if errors:
        st.sidebar.error("Some rows had errors (see details).")
        for e in errors:
            st.sidebar.write("-", e)
    ensure_amount_eur_column_and_backfill(session, converter)
    st.session_state._flash_success = "Import finished."
    st.rerun()

if st.sidebar.button("Export CSV"):
    csv_bytes = file_handler.export_transactions_to_csv_bytes(session)
    st.sidebar.download_button(
        "Download CSV", data=csv_bytes, file_name="transactions_export.csv", mime="text/csv"
    )

if st.sidebar.button("Export JSON"):
    json_bytes = file_handler.export_transactions_to_json_bytes(session)
    st.sidebar.download_button(
        "Download JSON", data=json_bytes, file_name="transactions_export.json", mime="application/json"
    )

# -----------------------
# Sidebar danger zone (Clear data)
# -----------------------
st.sidebar.markdown("---")
with st.sidebar.expander("⚠️ Danger zone: Clear data", expanded=False):
    st.write("Choose a destructive action below. These cannot be undone.")

    # Clear all transactions (keep schema/database file)
    st.markdown("**Clear all transactions (keep schema)**")
    confirm_clear = st.text_input("Type CLEAR to confirm", key="confirm_clear")
    if st.button("Delete all transactions"):
        if confirm_clear.strip().upper() == "CLEAR":
            try:
                clear_transactions()
                # also clear in-memory optimistic buffer if present
                if "optimistic_tx" in st.session_state:
                    st.session_state.optimistic_tx = []
                st.success("All transactions cleared.")
                st.rerun()
            except Exception as e:
                st.error(f"Failed to clear transactions: {e}")
        else:
            st.warning("Confirmation text did not match. Type CLEAR to proceed.")

    st.markdown("---")

    # Factory reset (delete DB file and recreate)
    st.markdown("**Factory reset (delete DB file & recreate)**")
    st.caption("Use this for a full reset during development.")
    confirm_reset = st.text_input("Type RESET to confirm", key="confirm_reset")
    if st.button("Factory reset database"):
        if confirm_reset.strip().upper() == "RESET":
            try:
                reset_database(drop_file=True)
                # clear optimistic buffer
                if "optimistic_tx" in st.session_state:
                    st.session_state.optimistic_tx = []
                vacuum()  # optional; compacts file if recreated
                st.success("Database reset. Fresh start!")
                st.rerun()
            except Exception as e:
                st.error(f"Failed to reset database: {e}")
        else:
            st.warning("Confirmation text did not match. Type RESET to proceed.")

# -----------------------
# Main content
# -----------------------
st.markdown("---")
left_col, right_col = st.columns([2, 1])

with left_col:
    all_df = render_table(session)

with right_col:
    render_summary(all_df, converter)

# Reports
render_reports(all_df, converter)

# Footer
st.markdown("---")
st.caption(
    "All totals are normalized to EUR at save/import time. Change the display currency in Settings to view totals in another currency."
)
