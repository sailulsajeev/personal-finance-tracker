# src/core/optimistic.py
from datetime import datetime
import pandas as pd
import streamlit as st
from src.models.transaction import Transaction

def build_optimistic(date, amount, currency, amount_eur, category, kind, description):
    """Create an optimistic transaction dict shaped like DB rows."""
    return {
        "id": None,
        "date": date,
        "amount": float(amount or 0.0),
        "currency": (currency or "EUR").upper(),
        "amount_eur": float(amount_eur or 0.0) if amount_eur is not None else None,
        "category": category or "Uncategorized",
        "kind": (kind or "expense").lower(),
        "description": description or "",
    }

def reconcile_with_db(session):
    """Remove optimistic entries that now exist in DB (avoid duplicates)."""
    if not st.session_state.get("optimistic_tx"):
        return
    rows = session.query(Transaction).order_by(Transaction.date.desc()).limit(500).all()
    db_sigs = {
        (
            (r.date.date() if isinstance(r.date, datetime) else r.date),
            float(r.amount or 0.0),
            (r.currency or "").upper(),
            (r.description or ""),
            (r.category or ""),
            (r.kind or "").lower(),
        )
        for r in rows
    }
    new_buf = []
    for o in st.session_state.optimistic_tx:
        sig = (
            (o["date"].date() if isinstance(o["date"], datetime) else o["date"]),
            float(o["amount"] or 0.0),
            (o["currency"] or "").upper(),
            (o["description"] or ""),
            (o["category"] or ""),
            (o["kind"] or "").lower(),
        )
        if sig not in db_sigs:
            new_buf.append(o)
    st.session_state.optimistic_tx = new_buf

def merge_frames(opt_df: pd.DataFrame, db_df: pd.DataFrame) -> pd.DataFrame:
    """Merge optimistic + DB rows and drop duplicates by row signature."""
    if not opt_df.empty and not db_df.empty:
        all_df = pd.concat([opt_df, db_df], ignore_index=True, sort=False)
        all_df.drop_duplicates(
            subset=["date", "amount", "currency", "category", "kind", "description"],
            keep="first",
            inplace=True,
        )
    elif not opt_df.empty:
        all_df = opt_df.copy()
    else:
        all_df = db_df.copy()
    return all_df
