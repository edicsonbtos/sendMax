"""
Endpoints de autenticación para operadores
"""
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, EmailStr
from src.utils.crypto import verify_password
from src.utils.jwt import create_access_token
from src.db.connection import get_async_conn
from datetime import timedelta
import logging

router = APIRouter(prefix="/auth/operator", tags=["Operator Auth"])
_logger = logging.getLogger("auth_operators")

class OperatorLoginRequest(BaseModel):
    email: EmailStr
    password: str

class OperatorLoginResponse(BaseModel):
    access_token: str
    token_type: str
    operator_id: int
    alias: str
    email: str

@router.post("/login", response_model=OperatorLoginResponse)
async def operator_login(credentials: OperatorLoginRequest):
    """
    Login para operadores con email y contraseña.
    Retorna JWT válido por 7 días.
    """
    try:
        async with get_async_conn() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    SELECT id, alias, email, hashed_password, kyc_status 
                    FROM users 
                    WHERE LOWER(email) = LOWER(%s) 
                    LIMIT 1
                    """, 
                    (credentials.email.strip(),)
                )
                rows = await cur.fetchall()
                row = rows[0] if rows else None
    except Exception as e:
        _logger.exception(f"DB error during login query: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error de base de datos: {str(e)}"
        )
    
    # Verificar que el usuario existe
    if not row:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales inválidas"
        )
    
    user_id, alias, email, hashed_password, kyc_status = row
    
    # Verificar que tiene contraseña configurada
    if not hashed_password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Tu cuenta no tiene contraseña web configurada. Contacta soporte."
        )
    
    # Verificar que está aprobado
    if kyc_status != 'APPROVED':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tu cuenta aún no está aprobada. Contacta soporte."
        )
    
    # Verificar contraseña
    if not verify_password(credentials.password.strip(), hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales inválidas"
        )
    
    # Generar JWT
    access_token = create_access_token(
        data={"sub": str(user_id), "type": "operator"},
        expires_delta=timedelta(days=7)
    )
    
    return OperatorLoginResponse(
        access_token=access_token,
        token_type="bearer",
        operator_id=user_id,
        alias=alias or "Operador",
        email=email
    )
