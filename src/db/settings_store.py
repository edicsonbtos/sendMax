from __future__ import annotations

import json
import time
from typing import Any

import psycopg


_cache: dict[str, Any] = {}
_cache_ts: float = 0.0
_TTL_SECONDS = 60


def _get_db_url() -> str:
    # Import local para evitar ciclos
    from src.config.settings import settings
    return settings.DATABASE_URL


def get_setting_json(key: str) -> dict[str, Any] | None:
    """
    Lee settings(key, value_json) desde Postgres.
    Cache 60s para no golpear DB.
    """
    global _cache_ts, _cache

    now = time.time()
    if (now - _cache_ts) < _TTL_SECONDS and key in _cache:
        return _cache[key]

    db_url = _get_db_url()
    with psycopg.connect(db_url) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT value_json FROM settings WHERE key=%s", (key,))
            row = cur.fetchone()

    val = None
    if row and row[0] is not None:
        # psycopg puede devolver dict o string según config
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
