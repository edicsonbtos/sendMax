"""
Auth endpoint LEGACY — ahora redirige al sistema JWT del backoffice.

ANTES: Credenciales hardcodeadas (admin@sendmax.com / Maxi2204#)
AHORA: Valida contra la DB con bcrypt + retorna JWT firmado.
"""
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from src.utils.crypto import verify_password
from src.utils.jwt import create_access_token
from src.db.connection import get_async_conn
from datetime import timedelta
import logging

router = APIRouter()
_logger = logging.getLogger("auth")


class LoginRequest(BaseModel):
    email: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    role: str
    full_name: str


@router.post("/login", response_model=LoginResponse)
async def login(req: LoginRequest):
    """
    Login para administradores.
    Valida contra la DB (users table) con bcrypt.
    Retorna JWT firmado (NO token estático).
    """
    email = req.email.strip().lower()
    pwd = req.password.strip()

    if not email or not pwd:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email y contraseña son requeridos",
        )

    try:
        async with get_async_conn() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    SELECT id, alias, email, hashed_password, role, full_name
                    FROM users
                    WHERE LOWER(email) = LOWER(%s)
                      AND role IN ('admin', 'ADMIN', 'superadmin')
                    LIMIT 1
                    """,
                    (email,),
                )
                rows = await cur.fetchall()
                row = rows[0] if rows else None
    except Exception as e:
        _logger.exception("DB error during admin login: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno del servidor",
        )

    if not row:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales incorrectas",
        )

    user_id, alias, user_email, hashed_password, role, full_name = row

    if not hashed_password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Cuenta sin contraseña configurada. Contacta soporte.",
        )

    if not verify_password(pwd, hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales incorrectas",
        )

    # Generar JWT firmado (expira en 8 horas)
    access_token = create_access_token(
        data={"sub": str(user_id), "type": "admin", "role": role},
        expires_delta=timedelta(hours=8),
    )

    display_name = full_name or alias or "Administrador"

    return LoginResponse(
        access_token=access_token,
        role=role or "admin",
        full_name=display_name,
    )
