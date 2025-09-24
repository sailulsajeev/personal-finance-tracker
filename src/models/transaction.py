from sqlalchemy import Column, Integer, String, Float, DateTime
from sqlalchemy.orm import declarative_base
import datetime

Base = declarative_base()

class Transaction(Base):
    __tablename__ = "transactions"
    id = Column(Integer, primary_key=True)
    date = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    amount = Column(Float, nullable=False)
    currency = Column(String(8), default="USD", nullable=False)
    category = Column(String(64), default="Uncategorized")
    kind = Column(String(16), nullable=False)  # "income" or "expense"
    description = Column(String(256), default="")
    amount_eur = Column(Float, nullable=True) 
