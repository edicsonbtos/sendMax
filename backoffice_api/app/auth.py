"""Autenticacion para backoffice: JWT (principal) + API KEY (legacy/fallback)"""

import os
from fastapi import Depends, HTTPException, Security, status, Request
from fastapi.security import APIKeyHeader, OAuth2PasswordBearer
import jwt
from jwt import InvalidTokenError
from dotenv import load_dotenv

load_dotenv()

EXPECTED_API_KEY = os.getenv("BACKOFFICE_API_KEY")
SECRET_KEY = os.getenv("SECRET_KEY", "supersecretkey_cambiar_en_prod")
ALGORITHM = os.getenv("ALGORITHM", "HS256")

api_key_header = APIKeyHeader(name="X-API-KEY", auto_error=False)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)


async def verify_api_key(
    request: Request,
    api_key: str = Security(api_key_header),
    token: str = Depends(oauth2_scheme),
):
    if request.url.path == "/health":
        return {"auth": "health", "role": "admin", "user_id": None, "email": None}

    # 1) JWT
    if token:
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            email = payload.get("sub")
            role = payload.get("role")
            user_id = payload.get("user_id")
            if email:
                return {"email": email, "role": role, "user_id": user_id, "auth": "jwt"}
        except InvalidTokenError:
            pass

    # 2) API KEY (legacy)
    if api_key and EXPECTED_API_KEY and api_key == EXPECTED_API_KEY:
        return {"auth": "api_key", "role": "admin", "user_id": None, "email": None}

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No autorizado. Envie token JWT o X-API-KEY valido.",
        headers={"WWW-Authenticate": "Bearer"},
    )