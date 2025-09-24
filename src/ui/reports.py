# src/ui/reports.py
import streamlit as st
import pandas as pd
import plotly.express as px
from src.core.fx import get_shared_rates, eur_factor


def render_reports(all_df, converter):
    st.markdown("---")
    st.subheader("Reports")

    if all_df is None or all_df.empty:
        st.info("Add or import transactions to see reports.")
        return

    df_tx = all_df.copy()
    df_tx["amount_eur"] = pd.to_numeric(df_tx["amount_eur"], errors="coerce").fillna(0.0)
    df_tx["kind"] = df_tx["kind"].str.lower()
    df_tx["signed_eur"] = df_tx.apply(
        lambda r: r["amount_eur"] if r["kind"] == "income" else -r["amount_eur"], axis=1
    )

    try:
        shared = get_shared_rates(converter)
        factor = eur_factor(shared, st.session_state.default_currency)
    except Exception:
        factor = 1.0

    display_curr = st.session_state.default_currency

    # Layout: two columns for charts
    col1, col2 = st.columns(2)

    # Pie: expenses by category
    with col1:
        df_exp = df_tx[df_tx["kind"] == "expense"].copy()
        df_exp["amount_display_abs"] = (df_exp["amount_eur"] * factor).abs()
        if not df_exp.empty and df_exp["amount_display_abs"].sum() > 0:
            fig_pie = px.pie(
                df_exp,
                values="amount_display_abs",
                names="category",
                title=f"Expenses by category ({display_curr})"
            )
            st.plotly_chart(fig_pie, use_container_width=True)
        else:
            st.info("No expense data to chart yet.")

    # Monthly net trend
    with col2:
        df_tx["month"] = pd.to_datetime(df_tx["date"]).dt.to_period("M").astype(str)
        df_month = df_tx.groupby("month", as_index=False)["signed_eur"].sum()
        df_month["signed_display"] = df_month["signed_eur"] * factor
        if not df_month.empty:
            fig_line = px.line(
                df_month.sort_values("month"),
                x="month",
                y="signed_display",
                markers=True,
                title=f"Monthly net balance ({display_curr})"
            )
            st.plotly_chart(fig_line, use_container_width=True)
        else:
            st.info("No monthly data to chart yet.")
