from src.services.db import init_db, get_session
from src.models.transaction import Transaction

def test_insert_transaction(tmp_path, monkeypatch):
    # point DB to temp file
    monkeypatch.setenv("DB_PATH", str(tmp_path / "test.db"))
    init_db()
    session = get_session()
    tx = Transaction(amount=10, currency="USD", category="Test", kind="expense")
    session.add(tx)
    session.commit()
    got = session.query(Transaction).filter_by(category="Test").one()
    assert got.amount == 10
