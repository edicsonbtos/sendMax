from __future__ import annotations

import json
import time
from typing import Any

from src.db.connection import get_conn


_cache: dict[str, Any] = {}
_cache_ts: float = 0.0
_TTL_SECONDS = 60


def get_setting_json(key: str) -> dict[str, Any] | None:
    """
    Lee settings(key, value_json) desde Postgres.
    Cache 60s para no golpear DB.
    """
    global _cache_ts, _cache

    now = time.time()
    if (now - _cache_ts) < _TTL_SECONDS and key in _cache:
        return _cache[key]

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT value_json FROM settings WHERE key=%s", (key,))
            row = cur.fetchone()

    val = None
    if row and row[0] is not None:
        if isinstance(row[0], dict):
            val = row[0]
        else:
            try:
                val = json.loads(row[0])
            except Exception:
                val = None

    _cache[key] = val
    _cache_ts = now
    return val


def get_setting_float(key: str, field: str, default: float) -> float:
    data = get_setting_json(key)
    if not data:
        return default
    v = data.get(field)
    try:
        if v is None:
            return default
        return float(v)
    except Exception:
        return default


def get_payment_methods_for_country(country: str) -> str | None:
    """
    Lee metodos de pago desde DB (settings key='payment_methods').
    Retorna texto formateado para Telegram.
    Fallback: None (el caller usa .env como backup).
    Cache: 60s via get_setting_json.
    """
    data = get_setting_json("payment_methods")
    if not data:
        return None

    country_data = data.get(country.upper(), {})
    methods = country_data.get("methods", [])

    active_methods = [m for m in methods if m.get("active", False)]
    active_methods.sort(key=lambda m: m.get("order", 99))

    if not active_methods:
        return None

    lines = []
    for m in active_methods:
        name = m.get("name", "")
        holder = m.get("holder", "")
        details = m.get("details", "")

        lines.append(f"\U0001f4b3 {name}")
        if holder:
            lines.append(f"   Titular: {holder}")
        if details:
            for line in details.split("\n"):
                lines.append(f"   {line.strip()}")
        lines.append("")

    return "\n".join(lines).strip()
