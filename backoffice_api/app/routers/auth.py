"""
Router de autenticacion para Backoffice.
Endpoint: POST /auth/login
Permite login de admin y operator.
"""

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from datetime import timedelta

from ..auth_jwt import (
    verify_password,
    create_access_token,
    ACCESS_TOKEN_EXPIRE_MINUTES,
)
from ..db import fetch_one

router = APIRouter(prefix="/auth", tags=["Auth"])


class LoginRequest(BaseModel):
    email: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    role: str
    full_name: str
    user_id: int


@router.post("/login", response_model=LoginResponse)
def login(data: LoginRequest):
    user = fetch_one(
        """
        SELECT id, email, hashed_password, role, is_active, full_name, alias
        FROM users
        WHERE email = %s
        LIMIT 1
        """,
        (data.email,),
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email o password incorrectos",
        )

    if user["role"] not in ("admin", "ADMIN", "operator"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acceso no permitido para este rol",
        )

    if not user["is_active"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cuenta desactivada",
        )

    if not user["hashed_password"]:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario sin password configurado",
        )

    if not verify_password(data.password, user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email o password incorrectos",
        )

    token = create_access_token(
        data={
            "sub": user["email"],
            "role": user["role"],
            "user_id": user["id"],
        },
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    )

    display_name = user["full_name"] or user["alias"] or "Usuario"

    return LoginResponse(
        access_token=token,
        token_type="bearer",
        role=user["role"],
        full_name=display_name,
        user_id=user["id"],
    )
