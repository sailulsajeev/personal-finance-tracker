# src/services/settings.py
import json
import os
from typing import Dict, Any

SETTINGS_PATH = os.getenv("SETTINGS_PATH", "data/settings.json")
DEFAULTS: Dict[str, Any] = {
    "default_currency": "USD",
    "exchange_api_url": "https://api.exchangerate.host/latest"
}

def load_settings() -> Dict[str, Any]:
    if not os.path.exists(SETTINGS_PATH):
        save_settings(DEFAULTS)
        return DEFAULTS.copy()
    try:
        with open(SETTINGS_PATH, "r", encoding="utf-8") as fh:
            data = json.load(fh)
            # merge defaults
            out = DEFAULTS.copy()
            out.update(data or {})
            return out
    except Exception:
        # if file is corrupted, overwrite with defaults
        save_settings(DEFAULTS)
        return DEFAULTS.copy()

def save_settings(settings: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(SETTINGS_PATH), exist_ok=True)
    with open(SETTINGS_PATH, "w", encoding="utf-8") as fh:
        json.dump(settings, fh, indent=2)
