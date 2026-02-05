from fastapi import Request, HTTPException, status
import os

API_KEY = os.getenv("BACKOFFICE_API_KEY", "dev-key-12345")

async def verify_api_key(request: Request):
    """Middleware para verificar X-API-KEY en headers"""
    # Skip health check
    if request.url.path == "/health":
        return
    
    api_key = request.headers.get("x-api-key")  # lowercase por FastAPI
    
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
