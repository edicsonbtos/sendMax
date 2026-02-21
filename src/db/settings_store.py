from __future__ import annotations

import json
import time
from typing import Any

from src.db.connection import get_async_conn


# Cache por llave con su propio timestamp de expiración
_cache: dict[str, tuple[Any, float]] = {}
_TTL_SECONDS = 60


async def get_setting_json(key: str) -> dict[str, Any] | None:
    """
    Lee settings(key, value_json) desde Postgres (ASYNC).
    Cache 60s por llave.
    """
    now = time.time()
    if key in _cache:
        val, ts = _cache[key]
        if (now - ts) < _TTL_SECONDS:
            return val

    try:
        async with get_async_conn() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT value_json FROM settings WHERE key=%s", (key,))
                row = await cur.fetchone()
    except Exception:
        # Si falla la DB, intentamos usar cache expirada como fallback
        if key in _cache:
            return _cache[key][0]
        return None

    val = None
    if row and row[0] is not None:
        raw_val = row[0]
        if isinstance(raw_val, dict):
            val = raw_val
        elif isinstance(raw_val, str):
            try:
                val = json.loads(raw_val)
            except Exception:
                # Si es un string pero no JSON, lo envolvemos si parece útil
                # o lo dejamos como None si se espera dict.
                val = None
        else:
            val = None

    _cache[key] = (val, now)
    return val


async def get_setting_float(key: str, field: str, default: float) -> float:
    data = await get_setting_json(key)
    if not data:
        return default
    v = data.get(field)
    try:
        if v is None:
            return default
        return float(v)
    except Exception:
        return default


async def get_payment_methods_for_country(country: str) -> str | None:
    """
    Lee metodos de pago desde DB.
    """
    data = await get_setting_json("payment_methods")
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

        lines.append(f"💳 {name}")
        if holder:
            lines.append(f"   Titular: {holder}")
        if details:
            for line in details.split("\n"):
                lines.append(f"   {line.strip()}")
        lines.append("")

    return "\n".join(lines).strip()
