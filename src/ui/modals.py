# src/ui/modals.py
import streamlit as st
from datetime import datetime, time

from src.models.transaction import Transaction
from src.core.fx import get_shared_rates, to_eur
from src.core.optimistic import build_optimistic

# Central place to manage default categories
DEFAULT_CATEGORIES = [
    "General",
    "Food & Dining",
    "Transport",
    "Housing",
    "Utilities",
    "Healthcare",
    "Entertainment",
    "Shopping",
    "Education",
    "Travel",
    "Salary",
    "Other (custom)",
]


def show_add_tx(session, converter, has_modal, DIALOG_DECORATOR):
    """Add Transaction modal/expander with Category as a dropdown."""
    def body():
        st.subheader("Add a new transaction")

        with st.form("add_tx_form", clear_on_submit=True):
            c1, c2 = st.columns(2)

            with c1:
                d = st.date_input("Date", datetime.today())
                amt = st.number_input("Amount", value=0.0, format="%.2f")
                cur = st.text_input("Currency", value="EUR", max_chars=8)

            with c2:
                # Category dropdown + optional custom input
                cat_choice = st.selectbox("Category", options=DEFAULT_CATEGORIES, index=0)
                custom_cat = ""
                if cat_choice == "Other (custom)":
                    custom_cat = st.text_input("Custom category", value="")
                kind = st.selectbox("Type", ["expense", "income"])
                desc = st.text_input("Description", value="")

            save_tx = st.form_submit_button("Save transaction")

        if save_tx:
            try:
                dt = d if isinstance(d, datetime) else datetime.combine(d, time.min)
                currency = (cur or "EUR").upper().strip()
                amount = float(amt or 0.0)

                # Final category value
                category = (custom_cat.strip() or cat_choice or "Uncategorized")
                if category == "Other (custom)":
                    category = "Uncategorized"

                # Compute amount_eur (normalize at write-time)
                try:
                    shared = get_shared_rates(converter)
                    amount_eur = to_eur(shared, amount, currency)
                    if amount_eur is None and currency == "EUR":
                        amount_eur = amount
                except Exception:
                    amount_eur = amount if currency == "EUR" else None

                tx = Transaction(
                    date=dt,
                    amount=amount,
                    currency=currency,
                    category=category,
                    kind=kind,
                    description=desc,
                )
                if hasattr(tx, "amount_eur"):
                    tx.amount_eur = float(amount_eur) if amount_eur is not None else None

                session.add(tx)
                session.commit()
                session.expire_all()

                # Optimistic echo + fast rerun
                st.session_state.optimistic_tx.append(
                    build_optimistic(dt, amount, currency, amount_eur, category, kind, desc)
                )
                st.session_state._flash_success = "Transaction saved ✅"
                st.session_state.show_add_tx = False
                st.rerun()

            except Exception as exc:
                try:
                    session.rollback()
                except Exception:
                    pass
                st.error(f"Failed to save transaction: {exc}")

    # Open as dialog only if the other dialog is not open
    if has_modal and st.session_state.show_add_tx and not st.session_state.get("show_settings", False):
        @DIALOG_DECORATOR("➕ Add transaction")
        def _dlg():
            body()
        _dlg()
    elif st.session_state.show_add_tx:
        with st.expander("➕ Add transaction", expanded=True):
            body()


def show_settings(_settings_file, save_settings_fn, has_modal, DIALOG_DECORATOR):
    """Settings modal/expander (display currency only; API URL read-only)."""
    def body():
        st.subheader("Settings")
        st.write("Totals are stored & computed in EUR; change the *display currency* here.")

        with st.form("settings_form", clear_on_submit=False):
            common = ["EUR", "USD", "GBP", "INR", "AUD", "CAD", "JPY", "CNY"]
            try:
                idx = common.index(st.session_state.default_currency)
            except ValueError:
                idx = 0

            chosen_currency = st.selectbox(
                "Display currency (converts from EUR)",
                options=common,
                index=idx,
                key="settings_currency",
            )
            st.text_input(
                "Exchange API URL",
                value=_settings_file.get("exchange_api_url", ""),
                disabled=True,
            )
            save_btn = st.form_submit_button("Save Settings")

        if save_btn:
            _settings_file["default_currency"] = chosen_currency
            save_settings_fn(_settings_file)
            st.session_state.default_currency = chosen_currency.upper()
            st.session_state._flash_success = f"Display currency set to {st.session_state.default_currency}"
            st.session_state.show_settings = False
            st.rerun()

    # Open as dialog only if the other dialog is not open
    if has_modal and st.session_state.show_settings and not st.session_state.get("show_add_tx", False):
        @DIALOG_DECORATOR("⚙️ Settings")
        def _dlg():
            body()
        _dlg()
    elif st.session_state.show_settings:
        with st.expander("⚙️ Settings", expanded=True):
            body()
