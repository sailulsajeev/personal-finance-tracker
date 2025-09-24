# src/services/currency_converter.py
import os
import time
import json
import requests
from typing import Dict, Optional, Tuple

# PRIMARY can be any free provider; we'll try all in order automatically.
PROVIDERS = [
    # (url, params-fn)  -> must return (url, params_dict)
    (lambda base: ("https://api.exchangerate.host/latest", {"base": base} if base else {})),
    (lambda base: ("https://api.frankfurter.app/latest", {"from": base} if base else {})),  # uses 'from' instead of 'base'
    (lambda base: (f"https://open.er-api.com/v6/latest/{base or 'EUR'}", {})),             # path param base
]

CACHE_TTL = int(os.getenv("EXCHANGE_CACHE_TTL", 60 * 60))  # seconds
CACHE_PATH = os.getenv("EXCHANGE_CACHE_PATH", "data/rates_cache.json")

# very small built-in seed for emergencies (update if you need more currencies)
SEED_BASE = "EUR"
SEED_RATES = {
    "EUR": 1.0,
    "USD": 1.08,
    "GBP": 0.85,
    "INR": 90.0,
    "AUD": 1.60,
    "CAD": 1.47,
    "JPY": 160.0,
    "CNY": 7.8,
}

class CurrencyAPIError(RuntimeError):
    pass

class CurrencyConverter:
    """
    Robust converter that:
      1) Fetches ONE table (whichever provider works),
      2) Converts via cross-rates: amt * (rate[to] / rate[from]),
      3) Falls back to disk cache, then to a tiny built-in seed.
    """

    def __init__(self, api_url: Optional[str] = None, ttl: Optional[int] = None,
                 cache_path: Optional[str] = None, base: Optional[str] = None):
        # api_url is ignored now (we auto-try providers). Kept for backward-compat.
        self.ttl = ttl or CACHE_TTL
        self.cache_path = cache_path or CACHE_PATH
        self.preferred_base = (base or "").upper() or None
        self._cache: Dict[str, Dict] = self._load_disk_cache()  # {"_single": {"ts":..., "base":..., "rates": {...}}}

    # ---------- disk cache ----------
    def _load_disk_cache(self) -> Dict[str, Dict]:
        try:
            if os.path.exists(self.cache_path):
                with open(self.cache_path, "r", encoding="utf-8") as fh:
                    data = json.load(fh)
                    if isinstance(data, dict):
                        return data
        except Exception:
            pass
        return {}

    def _save_disk_cache(self) -> None:
        try:
            os.makedirs(os.path.dirname(self.cache_path), exist_ok=True)
            with open(self.cache_path, "w", encoding="utf-8") as fh:
                json.dump(self._cache, fh)
        except Exception:
            pass

    # ---------- helpers ----------
    def _is_fresh(self) -> bool:
        entry = self._cache.get("_single")
        return bool(entry) and (time.time() - entry.get("ts", 0)) < self.ttl

    @staticmethod
    def _parse_rates(provider_name: str, data: dict) -> Tuple[str, Dict[str, float]]:
        """
        Normalize different provider shapes into (base, rates).
        Must return rates that include base with 1.0.
        """
        if not isinstance(data, dict):
            raise CurrencyAPIError(f"{provider_name}: Non-JSON or unexpected payload")

        # exchangerate.host & frankfurter usually: {"base": "EUR", "rates": {...}}
        if "rates" in data and isinstance(data["rates"], dict):
            base = (data.get("base") or data.get("from") or SEED_BASE)
            base = base.upper() if isinstance(base, str) else SEED_BASE
            rates = {k.upper(): float(v) for k, v in data["rates"].items() if isinstance(v, (int, float))}
            rates[base] = 1.0
            return base, rates

        # open.er-api.com: {"result":"success","base_code":"EUR","rates":{...}}
        if data.get("result") == "success" and "rates" in data and isinstance(data["rates"], dict):
            base = data.get("base_code", SEED_BASE)
            base = base.upper() if isinstance(base, str) else SEED_BASE
            rates = {k.upper(): float(v) for k, v in data["rates"].items() if isinstance(v, (int, float))}
            rates[base] = 1.0
            return base, rates

        # nothing matched
        raise CurrencyAPIError(f"{provider_name}: Unexpected API response format: missing 'rates' dict")

    def _try_fetch_from_providers(self) -> Tuple[str, Dict[str, float]]:
        base = self.preferred_base or SEED_BASE  # try to fetch with this base first
        errors = []
        for maker in PROVIDERS:
            url, params = maker(base)
            name = url.split("/")[2]
            try:
                resp = requests.get(url, params=params, timeout=10)
                resp.raise_for_status()
                data = resp.json()
                b, rates = self._parse_rates(name, data)
                return b, rates
            except Exception as exc:
                errors.append(f"{name}: {exc}")

        # All providers failed. Try ANY cached table (even stale).
        entry = self._cache.get("_single")
        if entry and "rates" in entry and isinstance(entry["rates"], dict):
            return entry.get("base", SEED_BASE), entry["rates"]

        # Final fallback: built-in seed
        return SEED_BASE, SEED_RATES.copy()

    # ---------- public API ----------
    def fetch_rates(self) -> Dict[str, float]:
        """
        Returns one normalized rates table (dict) for cross-rate conversions.
        """
        if self._is_fresh():
            return self._cache["_single"]["rates"]

        # allow moderately stale cache if online fails
        entry = self._cache.get("_single")
        if entry and (time.time() - entry.get("ts", 0)) < (self.ttl * 12):
            try:
                # best effort online refresh; if it fails we return disk
                base, rates = self._try_fetch_from_providers()
                self._cache["_single"] = {"ts": time.time(), "base": base, "rates": rates}
                self._save_disk_cache()
                return rates
            except Exception:
                return entry["rates"]

        # fetch fresh (or seed)
        base, rates = self._try_fetch_from_providers()
        self._cache["_single"] = {"ts": time.time(), "base": base, "rates": rates}
        self._save_disk_cache()
        return rates

    def get_base(self) -> str:
        entry = self._cache.get("_single")
        if entry and "base" in entry:
            return entry["base"]
        self.fetch_rates()
        entry = self._cache.get("_single", {})
        return entry.get("base", SEED_BASE)

    def convert(self, amount: float, from_currency: str, to_currency: str,
                rates: Optional[Dict[str, float]] = None) -> float:
        if amount is None:
            return 0.0
        from_currency = (from_currency or "USD").upper()
        to_currency = (to_currency or "USD").upper()
        if from_currency == to_currency:
            return float(amount)

        rates = rates or self.fetch_rates()

        def _get(sym: str) -> Optional[float]:
            sym = sym.upper().strip()
            v = rates.get(sym)
            return float(v) if isinstance(v, (int, float)) else None

        r_from = _get(from_currency)
        r_to = _get(to_currency)
        if r_from is None:
            raise CurrencyAPIError(f"Missing rate for '{from_currency}' (base={self.get_base()}).")
        if r_to is None:
            raise CurrencyAPIError(f"Missing rate for '{to_currency}' (base={self.get_base()}).")
        return float(amount) * (r_to / r_from)
