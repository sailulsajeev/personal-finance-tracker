# src/ui/summary.py
import streamlit as st
import pandas as pd
from src.core.fx import get_shared_rates, eur_factor

def render_summary(all_df: pd.DataFrame | None, converter) -> None:
    """Right-side summary panel. Expects a DataFrame with columns:
       ['amount','currency','amount_eur','category','kind','description','date'].
       Totals are computed in EUR and displayed in the user's display currency.
    """
    st.subheader("Summary")

    if all_df is None or all_df.empty:
        st.info("No transactions to summarize.")
        return

    df_tot = all_df.copy()
    # ensure numeric + normalized sign
    df_tot["amount_eur"] = pd.to_numeric(df_tot["amount_eur"], errors="coerce").fillna(0.0)
    df_tot["kind"] = df_tot["kind"].str.lower()
    df_tot["signed_eur"] = df_tot.apply(
        lambda r: r["amount_eur"] if r["kind"] == "income" else -r["amount_eur"], axis=1
    )

    total_eur = float(df_tot["signed_eur"].sum())
    total_inc_eur = float(df_tot[df_tot["kind"] == "income"]["amount_eur"].sum())
    total_exp_eur = float(df_tot[df_tot["kind"] == "expense"]["amount_eur"].sum())

    # original-currency breakdown
    by_curr = all_df.copy()
    by_curr["kind"] = by_curr["kind"].str.lower()
    by_curr["signed_amt"] = by_curr.apply(
        lambda r: r["amount"] if r["kind"] == "income" else -r["amount"], axis=1
    )
    totals_by_currency = by_curr.groupby("currency", as_index=False)["signed_amt"].sum()

    # convert EUR net to display currency
    default_curr = st.session_state.default_currency
    converted_total = total_eur
    failure_details = []
    shared_rates = None

    try:
        shared_rates = get_shared_rates(converter)
        factor = eur_factor(shared_rates, default_curr)
        converted_total = total_eur * factor
    except Exception as exc:
        failure_details.append(str(exc))

    st.metric(label=f"Total balance ({default_curr})", value=f"{converted_total:,.2f}")
    st.write(f"- Net (EUR): {total_eur:,.2f}")
    st.write(f"- Income (EUR): {total_inc_eur:,.2f}")
    st.write(f"- Expense (EUR): {total_exp_eur:,.2f}")

    if not totals_by_currency.empty:
        st.markdown("**Original-currency breakdown**")
        for _, row in totals_by_currency.iterrows():
            st.write(f"- {row['currency']}: {row['signed_amt']:,.2f}")

    if shared_rates:
        st.caption(f"Rate(EUR→{default_curr}) = {eur_factor(shared_rates, default_curr):.6f}")

    if failure_details:
        with st.expander("Why some conversions failed?"):
            for line in failure_details:
                st.write("•", line)
