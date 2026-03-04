"""
Endpoints de autenticación para operadores
"""
from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, EmailStr
from src.utils.crypto import verify_password
from src.utils.jwt import create_access_token
from src.db.connection import get_async_conn
from datetime import timedelta
import logging
import time
from collections import defaultdict

router = APIRouter(prefix="/auth/operator", tags=["Operator Auth"])
_logger = logging.getLogger("auth_operators")

# ── Rate limiter simple (sin dependencias externas) ──────────
_login_attempts: dict[str, list[float]] = defaultdict(list)
_MAX_ATTEMPTS = 5
_WINDOW_SECONDS = 60

def _check_rate_limit(ip: str) -> None:
    """Limita a 5 intentos por minuto por IP."""
    now = time.time()
    # Limpiar entradas expiradas
    _login_attempts[ip] = [t for t in _login_attempts[ip] if now - t < _WINDOW_SECONDS]
    if len(_login_attempts[ip]) >= _MAX_ATTEMPTS:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Demasiados intentos. Espera 1 minuto.",
        )
    _login_attempts[ip].append(now)

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
async def operator_login(credentials: OperatorLoginRequest, request: Request):
    """
    Login para operadores con email y contraseña.
    Retorna JWT válido por 7 días.
    """
    # Rate limit: 5 intentos/minuto por IP
    client_ip = request.client.host if request.client else "unknown"
    _check_rate_limit(client_ip)

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


# ══════════════════════════════════════════════════════════════
# Recuperación de contraseña vía Telegram
# ══════════════════════════════════════════════════════════════

import secrets
import os
from src.utils.crypto import get_password_hash

# Almacenamiento temporal de códigos (en-memory, OK para single instance Railway)
_reset_codes: dict[int, dict] = {}  # {telegram_user_id: {code, expires_at, attempts, user_id}}

class PasswordResetRequest(BaseModel):
    email: EmailStr

class PasswordResetConfirm(BaseModel):
    email: EmailStr
    code: str
    new_password: str


@router.post("/request-reset")
async def request_password_reset(payload: PasswordResetRequest, request: Request):
    """
    Solicita código de recuperación.
    Envía código de 6 dígitos al Telegram vinculado.
    """
    # Rate limit reutilizado
    client_ip = request.client.host if request.client else "unknown"
    _check_rate_limit(f"reset:{client_ip}")

    async with get_async_conn() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT id, telegram_user_id, alias
                FROM users
                WHERE LOWER(email) = LOWER(%s)
                  AND role IN ('operator', 'admin')
                LIMIT 1
                """,
                (payload.email.strip(),),
            )
            rows = await cur.fetchall()
            user = rows[0] if rows else None

    # Siempre retornar el mismo mensaje (no revelar si email existe)
    msg = "Si el email está registrado, recibirás un código en Telegram."

    if not user:
        return {"message": msg}

    user_id, telegram_id, alias = user

    if not telegram_id:
        _logger.warning("request-reset: user %s has no telegram_user_id", user_id)
        return {"message": msg}

    # Generar código de 6 dígitos
    code = "".join([str(secrets.randbelow(10)) for _ in range(6)])

    from datetime import datetime

    _reset_codes[int(telegram_id)] = {
        "code": code,
        "expires_at": datetime.utcnow() + timedelta(minutes=10),
        "attempts": 0,
        "user_id": user_id,
    }

    # Enviar vía Telegram
    try:
        from telegram import Bot
        bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
        bot = Bot(token=bot_token)
        await bot.send_message(
            chat_id=int(telegram_id),
            text=(
                "🔐 *Recuperación de Contraseña*\n\n"
                f"Tu código de verificación es:\n\n"
                f"`{code}`\n\n"
                "Este código expira en 10 minutos.\n"
                "Si no solicitaste esto, ignora este mensaje."
            ),
            parse_mode="Markdown",
        )
        _logger.info("Password reset code sent to telegram_id=%s for user_id=%s", telegram_id, user_id)
    except Exception as e:
        _logger.error("Error sending reset code via Telegram: %s", e)
        # No fallar — el usuario no debe saber si el envío falló
        del _reset_codes[int(telegram_id)]
        return {"message": msg}

    return {"message": msg}


@router.post("/reset-password")
async def reset_password(payload: PasswordResetConfirm, request: Request):
    """
    Verifica código y cambia contraseña.
    Máximo 3 intentos por código.
    """
    client_ip = request.client.host if request.client else "unknown"
    _check_rate_limit(f"resetpw:{client_ip}")

    # Validar nueva contraseña
    if len(payload.new_password.strip()) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La contraseña debe tener al menos 8 caracteres.",
        )

    async with get_async_conn() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT id, telegram_user_id
                FROM users
                WHERE LOWER(email) = LOWER(%s)
                  AND role IN ('operator', 'admin')
                LIMIT 1
                """,
                (payload.email.strip(),),
            )
            rows = await cur.fetchall()
            user = rows[0] if rows else None

    if not user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email no encontrado.")

    user_id, telegram_id = user

    if not telegram_id or int(telegram_id) not in _reset_codes:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No hay código activo para este email.")

    stored = _reset_codes[int(telegram_id)]

    from datetime import datetime

    # Verificar expiración
    if stored["expires_at"] < datetime.utcnow():
        del _reset_codes[int(telegram_id)]
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Código expirado. Solicita uno nuevo.")

    # Verificar intentos
    if stored["attempts"] >= 3:
        del _reset_codes[int(telegram_id)]
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Demasiados intentos. Solicita un nuevo código.")

    # Verificar código
    if stored["code"] != payload.code.strip():
        stored["attempts"] += 1
        remaining = 3 - stored["attempts"]
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Código incorrecto. {remaining} intentos restantes.",
        )

    # ✅ Código válido — cambiar contraseña
    hashed = get_password_hash(payload.new_password.strip())

    async with get_async_conn() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "UPDATE users SET hashed_password = %s WHERE id = %s",
                (hashed, user_id),
            )
        await conn.commit()

    # Limpiar código usado
    del _reset_codes[int(telegram_id)]

    # Notificar cambio exitoso vía Telegram
    try:
        from telegram import Bot
        bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
        bot = Bot(token=bot_token)
        await bot.send_message(
            chat_id=int(telegram_id),
            text=(
                "✅ Tu contraseña ha sido cambiada exitosamente.\n"
                "Si no fuiste tú, contacta a soporte inmediatamente."
            ),
        )
    except Exception:
        pass  # No fallar si no se envía la notificación

    _logger.info("Password reset completed for user_id=%s", user_id)
    return {"message": "Contraseña cambiada exitosamente."}
