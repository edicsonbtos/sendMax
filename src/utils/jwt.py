"""
Utilidades para manejo de JWT (JSON Web Tokens)
"""
from datetime import datetime, timedelta
from jose import jwt, JWTError
from src.config.settings import settings

ALGORITHM = "HS256"

# Usar clave secreta del entorno o una por defecto
# IMPORTANTE: Asegúrate de tener JWT_SECRET en Railway variables
SECRET_KEY = getattr(settings, "JWT_SECRET", "sendmax_secret_key_change_in_production")

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
        expire = datetime.utcnow() + timedelta(days=7)
    
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
