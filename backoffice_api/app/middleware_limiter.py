import time
import logging
from collections import defaultdict
from fastapi import Request, HTTPException, status
from .config import (
    RATE_LIMIT_ENABLED,
    RATE_LIMIT_PER_MINUTE_DEFAULT,
    RATE_LIMIT_LOGIN_PER_MINUTE
)

logger = logging.getLogger(__name__)

# Almacén simple en memoria (MVP)
# En un sistema multi-instancia real usaríamos Redis.
_hits = defaultdict(list)

async def rate_limit_middleware(request: Request, call_next):
    if not RATE_LIMIT_ENABLED:
        return await call_next(request)

    # Saltos (Skip)
    if request.url.path == "/health":
        return await call_next(request)

    now = time.time()
    ip = request.client.host if request.client else "unknown"
    path = request.url.path

    # Determinar límite
    limit = RATE_LIMIT_PER_MINUTE_DEFAULT
    if path == "/auth/login":
        limit = RATE_LIMIT_LOGIN_PER_MINUTE
    elif path.startswith("/api/v1/config"):
        limit = 30

    # Clave de rate limit (IP + Path simplificado)
    key = f"{ip}:{path}"

    # Limpiar viejos
    _hits[key] = [h for h in _hits[key] if h > now - 60]

    if len(_hits[key]) >= limit:
        logger.warning(f"Rate limit exceeded for {key}")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Demasiadas peticiones. Intente en un minuto."
        )

    _hits[key].append(now)

    return await call_next(request)
