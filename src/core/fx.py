# src/core/fx.py
import streamlit as st
from src.services.currency_converter import CurrencyConverter
from typing import Dict, Any

@st.cache_data(ttl=600)
def get_shared_rates(converter: CurrencyConverter) -> Dict[str, float]:
    """Cached FX table (single base table with cross-rate math)."""
    return converter.fetch_rates()

def eur_factor(shared: Dict[str, float], to_currency: str) -> float:
    """Factor to convert EUR -> to_currency given shared rates."""
    r_to = shared.get(to_currency.upper())
    r_from_eur = shared.get("EUR", 1.0)
    if isinstance(r_to, (int, float)) and isinstance(r_from_eur, (int, float)) and r_from_eur != 0:
        return r_to / r_from_eur
    return 1.0

def to_eur(shared: Dict[str, float], amount: float, currency: str) -> float | None:
    """Convert an amount from currency -> EUR using shared table. Returns None if unavailable."""
    currency = (currency or "EUR").upper()
    r_from = shared.get(currency)
    r_to_eur = shared.get("EUR", 1.0)
    if isinstance(r_from, (int, float)) and isinstance(r_to_eur, (int, float)) and r_from != 0:
        return amount * (r_to_eur / r_from)
    if currency == "EUR":
        return amount
    return None
