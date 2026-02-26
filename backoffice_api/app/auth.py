"""Autenticacion unificada para backoffice: JWT (principal) + API KEY (legacy/fallback)"""

import logging
from fastapi import Depends, HTTPException, Security, status, Request
from fastapi.security import APIKeyHeader
import jwt
from jwt import InvalidTokenError
from .config import SECRET_KEY, BACKOFFICE_API_KEY, ALGORITHM
from .auth_jwt import oauth2_scheme

logger = logging.getLogger(__name__)

api_key_header = APIKeyHeader(name="X-API-KEY", auto_error=False)

async def get_auth_context(
    request: Request,
    api_key: str = Security(api_key_header),
    token: str = Depends(oauth2_scheme),
) -> dict:
    """
    Retorna el contexto de autenticación: {auth, role, user_id, email}
    """
    # 1) Saltos (Skip)
    if request.url.path == "/health":
        return {"auth": "health", "role": "admin", "user_id": None, "email": None}

    # 2) JWT
    if token and SECRET_KEY:
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            email = payload.get("sub")
            role = payload.get("role")
            user_id = payload.get("user_id")
            if email:
                return {"email": email, "role": role, "user_id": user_id, "auth": "jwt"}
        except InvalidTokenError as e:
            logger.warning("JWT inválido: %s", e)

    # 3) API KEY (interna / legacy)
    if api_key and BACKOFFICE_API_KEY and api_key == BACKOFFICE_API_KEY:
        return {"auth": "api_key", "role": "admin", "user_id": None, "email": "system@local"}

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No autorizado. Envie token JWT o X-API-KEY valido.",
        headers={"WWW-Authenticate": "Bearer"},
    )

def require_admin(auth: dict = Depends(get_auth_context)):
    if (auth.get("role") or "").lower() != "admin" and auth.get("auth") != "api_key":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Se requiere rol de administrador"
        )
    return auth

def require_operator_or_admin(auth: dict = Depends(get_auth_context)):
    role = (auth.get("role") or "").lower()
    if role not in ("admin", "operator") and auth.get("auth") != "api_key":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acceso restringido a operadores o administradores"
        )
    return auth

# Alias para compatibilidad con código existente
verify_api_key = get_auth_context
