"""
Utilidades para manejo de JWT (JSON Web Tokens)
"""
import os
from datetime import datetime, timedelta
from jose import jwt, JWTError
from src.config.settings import settings

ALGORITHM = "HS256"

# Clave secreta desde variables de entorno — OBLIGATORIA
# FAIL-FAST: Si JWT_SECRET no está configurada, el servicio no debe firmar tokens
_jwt_secret = getattr(settings, "JWT_SECRET", None) or os.environ.get("JWT_SECRET") or os.environ.get("SECRET_KEY")
if not _jwt_secret:
    import logging as _log
    _log.getLogger("jwt").critical(
        "JWT_SECRET no configurada. Los tokens no podrán ser firmados. "
        "Configure JWT_SECRET en las variables de entorno de Railway."
    )
SECRET_KEY = _jwt_secret or ""

def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """
    Crea un JWT con los datos proporcionados.
    
    Args:
        data: Diccionario con datos a incluir en el token (ej: {"sub": "user_id", "type": "operator"})
        expires_delta: Tiempo de expiración opcional (default: 7 días)
    
    Returns:
        Token JWT firmado
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(hours=24)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def decode_access_token(token: str) -> dict | None:
    """
    Decodifica y valida un JWT.
    
    Args:
        token: Token JWT a decodificar
    
    Returns:
        Diccionario con los datos del token si es válido, None si es inválido o expirado
    """
    try:
        decoded_data = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return decoded_data
    except JWTError:
        return None
