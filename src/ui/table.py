# src/ui/table.py
import streamlit as st
import pandas as pd
from datetime import datetime
from src.models.transaction import Transaction
from src.core.optimistic import reconcile_with_db, merge_frames

def render_table(session) -> pd.DataFrame:
    st.subheader("Recent transactions")
    reconcile_with_db(session)

    rows = session.query(Transaction).order_by(Transaction.date.desc()).limit(500).all()
    db_df = pd.DataFrame([{
        "id": r.id,
        "date": r.date,
        "amount": float(r.amount or 0.0),
        "currency": (r.currency or "").upper(),
        "amount_eur": float(getattr(r, "amount_eur", 0.0) or 0.0) if hasattr(r, "amount_eur") else None,
        "category": r.category or "Uncategorized",
        "kind": (r.kind or "expense").lower(),
        "description": r.description or "",
    } for r in rows])

    opt_df = pd.DataFrame(st.session_state.optimistic_tx) if st.session_state.optimistic_tx else pd.DataFrame()
    all_df = merge_frames(opt_df, db_df)

    if all_df.empty:
        st.info("No transactions found. Add or import transactions to get started.")
        return all_df

    # Filters
    mf1, mf2, mf3 = st.columns([1, 1, 2])
    with mf1:
        txt = st.text_input("Search (description/category)", value="")
    with mf2:
        sel_kind = st.selectbox("Type", options=["all", "expense", "income"], index=0)
    with mf3:
        date_default_start = pd.to_datetime(all_df["date"]).min().date()
        date_default_end = datetime.today().date()
        date_range = st.date_input("Date range", value=(date_default_start, date_default_end))

    df_filtered = all_df.copy()
    if txt:
        df_filtered = df_filtered[
            df_filtered["description"].str.contains(txt, case=False, na=False)
            | df_filtered["category"].str.contains(txt, case=False, na=False)
        ]
    if sel_kind in ("expense", "income"):
        df_filtered = df_filtered[df_filtered["kind"] == sel_kind]

    try:
        start_date, end_date = date_range
    except Exception:
        start_date = date_range
        end_date = date_range
    df_filtered = df_filtered[
        (pd.to_datetime(df_filtered["date"]).dt.date >= start_date)
        & (pd.to_datetime(df_filtered["date"]).dt.date <= end_date)
    ]

    st.dataframe(df_filtered.sort_values("date", ascending=False).reset_index(drop=True))
    return all_df
