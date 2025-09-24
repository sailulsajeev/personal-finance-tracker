# src/core/schema.py
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session

from src.models.transaction import Transaction
from src.services.currency_converter import CurrencyConverter


def ensure_amount_eur_column_and_backfill(session: Session, converter: CurrencyConverter) -> None:
    """
    1) Ensure 'amount_eur' REAL column exists on the transactions table.
    2) Backfill amount_eur for rows where it's NULL using current FX rates.

    This version uses ORM rows for backfill (avoids tuple-index issues),
    and falls back to a raw UPDATE if needed.
    """
    # 1) Ensure the column exists
    tbl = getattr(Transaction, "__tablename__", "transactions")
    cols = session.execute(text(f"PRAGMA table_info({tbl})")).fetchall()
    colnames = {c[1] for c in cols}  # (cid, name, type, notnull, dflt_value, pk)
    if "amount_eur" not in colnames:
        session.execute(text(f"ALTER TABLE {tbl} ADD COLUMN amount_eur REAL"))
        session.commit()

    # 2) Backfill missing values
    try:
        rates = converter.fetch_rates()  # single-table cross rates, e.g. {"EUR": 1.0, "USD": 1.08, ...}
    except Exception:
        rates = None

    # Nothing we can do without rates; skip quietly
    if not rates:
        return

    r_to_eur = rates.get("EUR", 1.0)

    # Query ORM rows with missing amount_eur
    missing = (
        session.query(Transaction)
        .filter(text("amount_eur IS NULL"))
        .all()
    )

    if not missing:
        return

    for row in missing:
        try:
            amount = float(row.amount or 0.0)
            curr = (row.currency or "EUR").upper()
            r_from = rates.get(curr)
            if isinstance(r_from, (int, float)) and isinstance(r_to_eur, (int, float)):
                amount_eur = amount * (r_to_eur / r_from)
            else:
                amount_eur = amount if curr == "EUR" else None

            # Preferred: set via ORM if mapped
            try:
                setattr(row, "amount_eur", float(amount_eur) if amount_eur is not None else None)
            except Exception:
                # Fallback: write via raw SQL (in case model mapping is missing)
                session.execute(
                    text(f"UPDATE {tbl} SET amount_eur = :val WHERE id = :id"),
                    {"val": float(amount_eur) if amount_eur is not None else None, "id": row.id},
                )
        except Exception:
            # Continue with other rows; avoid aborting entire backfill
            continue

    # Commit backfilled values
    session.commit()
