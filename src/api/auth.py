from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
import os

router = APIRouter()

class LoginRequest(BaseModel):
    email: str
    password: str

class LoginResponse(BaseModel):
    access_token: str
    role: str
    full_name: str

@router.post("/login", response_model=LoginResponse)
async def login(req: LoginRequest):
    # Strip spaces to prevent accidental "Maxi2204# " typing errors
    email = req.email.strip().lower()
    pwd = req.password.strip()
    
    if email == "admin@sendmax.com" and pwd == "Maxi2204#":
        return LoginResponse(
            access_token="admin_super_secret_token_sendmax",
            role="superadmin",
            full_name="Administrador SendMax"
        )
    raise HTTPException(status_code=401, detail="Credenciales incorrectas")
