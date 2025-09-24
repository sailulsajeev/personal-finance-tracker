# src/services/file_handler.py
import pandas as pd
from io import BytesIO, StringIO
from datetime import datetime
from typing import Tuple
from src.models.transaction import Transaction
from sqlalchemy.orm import Session

CSV_REQUIRED_COLS = {"date", "amount", "currency", "category", "kind", "description"}

def _parse_date(value):
    """Try a few common date formats, fallback to pandas parser."""
    if pd.isna(value):
        return None
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(str(value), fmt)
        except Exception:
            pass
    # fallback
    try:
        return pd.to_datetime(value)
    except Exception:
        return None

def export_transactions_to_csv_bytes(session: Session) -> bytes:
    """Query transactions and return CSV bytes."""
    rows = session.query(Transaction).order_by(Transaction.date.asc()).all()
    data = [{
        "date": r.date.isoformat() if r.date else "",
        "amount": r.amount,
        "currency": r.currency,
        "category": r.category,
        "kind": r.kind,
        "description": r.description or ""
    } for r in rows]
    df = pd.DataFrame(data)
    csv_bytes = df.to_csv(index=False).encode("utf-8")
    return csv_bytes

def export_transactions_to_json_bytes(session: Session) -> bytes:
    rows = session.query(Transaction).order_by(Transaction.date.asc()).all()
    data = [{
        "date": r.date.isoformat() if r.date else None,
        "amount": r.amount,
        "currency": r.currency,
        "category": r.category,
        "kind": r.kind,
        "description": r.description or ""
    } for r in rows]
    json_bytes = pd.DataFrame(data).to_json(orient="records", date_format="iso").encode("utf-8")
    return json_bytes

def import_transactions_from_csv_filelike(filelike, session: Session) -> Tuple[int, int, list]:
    """
    Read CSV filelike (bytes/stream), insert new transactions to DB.
    Returns (inserted_count, skipped_count, errors_list)
    """
    errors = []
    try:
        # pandas accepts file-like; streamlit.uploaded_file is fine
        df = pd.read_csv(filelike)
    except Exception as exc:
        errors.append(f"Failed to read CSV: {exc}")
        return 0, 0, errors

    # Normalize columns
    cols = set([c.strip() for c in df.columns])
    if not CSV_REQUIRED_COLS.issubset(cols):
        missing = CSV_REQUIRED_COLS - cols
        errors.append(f"Missing required columns: {', '.join(sorted(missing))}")
        return 0, 0, errors

    inserted = 0
    skipped = 0
    for idx, row in df.iterrows():
        try:
            date_val = _parse_date(row.get("date"))
            if date_val is None:
                errors.append(f"Row {idx+1}: invalid date -> {row.get('date')}")
                skipped += 1
                continue
            amount = float(row.get("amount"))
            currency = str(row.get("currency")).upper().strip()
            category = str(row.get("category")).strip()
            kind = str(row.get("kind")).strip().lower()
            description = str(row.get("description") if not pd.isna(row.get("description")) else "")

            # Duplicate detection: same date (day), amount, currency, description
            dup = session.query(Transaction).filter(
                Transaction.amount == amount,
                Transaction.currency == currency,
                Transaction.description == description,
                # compare date by date part only
            ).all()
            is_dup = False
            for d in dup:
                if d.date.date() == date_val.date():
                    is_dup = True
                    break
            if is_dup:
                skipped += 1
                continue

            tx = Transaction(
                date=date_val,
                amount=amount,
                currency=currency,
                category=category or "Uncategorized",
                kind=kind if kind in ("income", "expense") else "expense",
                description=description
            )
            session.add(tx)
            inserted += 1
        except Exception as exc:
            skipped += 1
            errors.append(f"Row {idx+1} error: {exc}")

    try:
        session.commit()
    except Exception as exc:
        session.rollback()
        errors.append(f"DB commit failed: {exc}")
        return inserted, skipped, errors

    return inserted, skipped, errors

def import_transactions_from_json_filelike(filelike, session: Session) -> Tuple[int, int, list]:
    """
    filelike contains JSON array of records.
    Records must contain same keys as CSV_REQUIRED_COLS (date, amount, currency, category, kind, description).
    """
    try:
        df = pd.read_json(filelike)
    except Exception as exc:
        return 0, 0, [f"Failed to read JSON: {exc}"]

    # Reuse CSV importer by converting df -> csv buffer
    buf = StringIO()
    df.to_csv(buf, index=False)
    buf.seek(0)
    return import_transactions_from_csv_filelike(buf, session)
