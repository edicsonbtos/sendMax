from fastapi import APIRouter, HTTPException, Depends, Header
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import logging

from src.db.connection import get_async_conn
from src.api.operators import get_current_operator

router = APIRouter(prefix="/api/operators/beneficiaries", tags=["beneficiaries"])
logger = logging.getLogger(__name__)

class BeneficiaryResponse(BaseModel):
    id: int
    alias: str
    full_name: str
    dest_country: str
    bank_name: Optional[str]
    account_number: Optional[str]
    phone: Optional[str]
    payment_method: Optional[str]
    notes: Optional[str]
    uses_count: int
    created_at: datetime

class CreateBeneficiaryRequest(BaseModel):
    alias: str
    full_name: str
    dest_country: str
    bank_name: Optional[str] = None
    account_number: Optional[str] = None
    phone: Optional[str] = None
    payment_method: Optional[str] = None
    notes: Optional[str] = None

@router.get("", response_model=List[BeneficiaryResponse])
async def list_beneficiaries(user_id: int = Depends(get_current_operator)):
    async with get_async_conn() as conn:
        async with conn.cursor() as cur:
            await cur.execute("""
                SELECT 
                    id, alias, full_name, dest_country, bank_name, 
                    account_number, phone, payment_method, notes,
                    uses_count, created_at
                FROM saved_beneficiaries
                WHERE user_id = %s AND is_active = true
                ORDER BY uses_count DESC, created_at DESC
            """, (user_id,))
            rows = await cur.fetchall()
            
            return [BeneficiaryResponse(
                id=r[0], alias=r[1], full_name=r[2], dest_country=r[3],
                bank_name=r[4], account_number=r[5], phone=r[6],
                payment_method=r[7], notes=r[8], uses_count=r[9], created_at=r[10]
            ) for r in rows]

@router.post("", response_model=BeneficiaryResponse)
async def create_beneficiary(req: CreateBeneficiaryRequest, user_id: int = Depends(get_current_operator)):
    if not req.alias or not req.alias.strip():
        raise HTTPException(status_code=400, detail="El alias es mandatorio")
        
    async with get_async_conn() as conn:
        async with conn.cursor() as cur:
            # check alias duplication
            await cur.execute("SELECT id FROM saved_beneficiaries WHERE user_id = %s AND alias = %s", (user_id, req.alias.strip()))
            if await cur.fetchone():
                raise HTTPException(status_code=400, detail="Ya existe un beneficiario con este alias")

            await cur.execute("""
                INSERT INTO saved_beneficiaries (
                    user_id, alias, full_name, dest_country, 
                    bank_name, account_number, phone, payment_method, notes
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id, created_at, uses_count
            """, (
                user_id, req.alias.strip(), req.full_name.strip(), req.dest_country,
                req.bank_name, req.account_number, req.phone, req.payment_method, req.notes
            ))
            row = await cur.fetchone()
            await conn.commit()
            
            return BeneficiaryResponse(
                id=row[0], alias=req.alias, full_name=req.full_name, dest_country=req.dest_country,
                bank_name=req.bank_name, account_number=req.account_number, phone=req.phone,
                payment_method=req.payment_method, notes=req.notes,
                uses_count=row[2], created_at=row[1]
            )
