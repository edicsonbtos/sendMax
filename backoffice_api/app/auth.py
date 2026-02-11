"""Autenticación compartida para todos los routers"""

import os
from fastapi import Depends, HTTPException, status
from fastapi.security import APIKeyHeader

API_KEY = os.getenv("BACKOFFICE_API_KEY")

api_key_header = APIKeyHeader(name="X-API-KEY", auto_error=False)


async def verify_api_key(api_key: str = Depends(api_key_header)):
    if not API_KEY:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="BACKOFFICE_API_KEY not configured on server"
        )
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-API-KEY header"
        )
    if api_key != API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key"
        )
    return api_key
