from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from src.db.connection import get_async_conn
from src.api.operators import get_current_operator

router = APIRouter(prefix="/api/operators/clients", tags=["clients"])

class ClientCreate(BaseModel):
    full_name: str
    phone: Optional[str] = None
    email: Optional[str] = None
    notes: Optional[str] = None

class ClientResponse(BaseModel):
    id: int
    full_name: str
    phone: Optional[str]
    email: Optional[str]
    total_orders: int
    total_volume: float

class ClientSearch(BaseModel):
    id: int
    full_name: str
    phone: Optional[str]
    total_orders: int

@router.get("/search", response_model=List[ClientSearch])
async def search_clients(
    q: str = "",
    user_id: int = Depends(get_current_operator)
):
    """Buscar clientes por nombre o teléfono con autocomplete"""
    async with get_async_conn() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT id, full_name, phone, total_orders
                FROM clients
                WHERE operator_id = %s 
                AND (full_name ILIKE %s OR phone ILIKE %s)
                ORDER BY total_orders DESC, full_name ASC
                LIMIT 10
                """,
                (user_id, f"%{q}%", f"%{q}%")
            )
            rows = await cur.fetchall()
            return [ClientSearch(
                id=r[0], full_name=r[1], phone=r[2], total_orders=r[3]
            ) for r in rows]

@router.post("/", response_model=ClientResponse)
async def create_client(
    req: ClientCreate,
    user_id: int = Depends(get_current_operator)
):
    """Crear nuevo cliente"""
    async with get_async_conn() as conn:
        async with conn.cursor() as cur:
            # Verificar si ya existe
            await cur.execute(
                """
                SELECT id FROM clients 
                WHERE operator_id = %s AND full_name = %s AND COALESCE(phone, '') = COALESCE(%s, '')
                """,
                (user_id, req.full_name.strip(), req.phone)
            )
            existing = await cur.fetchone()
            if existing:
                raise HTTPException(status_code=400, detail="Ya existe un cliente con ese nombre y teléfono")
            
            await cur.execute(
                """
                INSERT INTO clients (operator_id, full_name, phone, email, notes)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id, full_name, phone, email, total_orders, total_volume
                """,
                (user_id, req.full_name.strip(), req.phone, req.email, req.notes)
            )
            row = await cur.fetchone()
            await conn.commit()
            
            return ClientResponse(
                id=row[0], full_name=row[1], phone=row[2], 
                email=row[3], total_orders=row[4], total_volume=float(row[5] or 0)
            )

@router.get("/leaderboard", response_model=List[ClientResponse])
async def get_client_leaderboard(
    user_id: int = Depends(get_current_operator),
    limit: int = 50
):
    """Ranking de clientes por volumen"""
    async with get_async_conn() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT id, full_name, phone, email, total_orders, total_volume
                FROM clients
                WHERE operator_id = %s AND total_orders > 0
                ORDER BY total_volume DESC, total_orders DESC
                LIMIT %s
                """,
                (user_id, limit)
            )
            rows = await cur.fetchall()
            return [ClientResponse(
                id=r[0], full_name=r[1], phone=r[2], email=r[3],
                total_orders=r[4], total_volume=float(r[5] or 0)
            ) for r in rows]
