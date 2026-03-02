from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
import os

router = APIRouter()

class LoginRequest(BaseModel):
    email: str
    password: str

class LoginResponse(BaseModel):
    token: str
    user: dict

@router.post("/login", response_model=LoginResponse)
async def login(req: LoginRequest):
    # Hardcoded admin credentials based on user request
    if req.email == "admin@sendmax.com" and req.password == "Maxi2204#":
        return LoginResponse(
            token="admin_super_secret_token_sendmax",
            user={
                "id": 1,
                "name": "Administrador SendMax",
                "email": req.email,
                "role": "admin"
            }
        )
    raise HTTPException(status_code=401, detail="Credenciales incorrectas")
