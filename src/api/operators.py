from fastapi import APIRouter, HTTPException, Depends, Header
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from decimal import Decimal
import logging
from uuid import uuid4
import json

from src.db.connection import get_async_conn

router = APIRouter(prefix="/api/operators", tags=["operators"])
logger = logging.getLogger(__name__)

class OperatorStatsResponse(BaseModel):
    daily_volume_usdt: Decimal
    monthly_volume_usdt: Decimal
    total_orders: int
    pending_orders: int
    trust_score: Decimal
    rank_position: Optional[int]

class TopClientResponse(BaseModel):
    name: str
    total_volume_usdt: Decimal
    total_orders: int

class OrderQueueItem(BaseModel):
    public_id: int
    client_name: str
    amount_origin: Decimal
    origin_country: str
    dest_country: str
    status: str
    created_at: datetime

class EarningsByCountry(BaseModel):
    country: str
    earnings_usdt: Decimal
    order_count: int

from src.utils.jwt import decode_access_token
from fastapi import status

async def get_current_operator(authorization: str = Header(None)) -> int:
    """
    Extrae y valida el JWT del header Authorization.
    Retorna el user_id del operador autenticado.
    
    Raises:
        HTTPException: Si no hay token, es inválido, o no es de operador
    """
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No se proporcionó token de autenticación",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Extraer token del formato "Bearer <token>"
    try:
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Esquema de autenticación inválido. Use Bearer token."
            )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Formato de Authorization header inválido"
        )
    
    # Decodificar y validar JWT
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido o expirado"
        )
    
    # Verificar que sea token de operador
    if payload.get("type") != "operator":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Este endpoint es solo para operadores"
        )
    
    user_id = int(payload.get("sub"))
    return user_id

@router.get("/dashboard/stats", response_model=OperatorStatsResponse)
async def get_dashboard_stats(user_id: int = Depends(get_current_operator)):
    async with get_async_conn() as conn:
        async with conn.cursor() as cur:
            await cur.execute("""
                SELECT COALESCE(SUM(profit_real_usdt), 0)
                FROM orders
                WHERE operator_user_id = %s AND DATE(created_at) = CURRENT_DATE
                AND status IN ('COMPLETADA', 'ORIGEN_CONFIRMADO')
            """, (user_id,))
            daily_vol = (await cur.fetchone())[0]
            
            await cur.execute("""
                SELECT COALESCE(SUM(profit_real_usdt), 0)
                FROM orders
                WHERE operator_user_id = %s
                AND DATE_TRUNC('month', created_at) = DATE_TRUNC('month', CURRENT_DATE)
                AND status IN ('COMPLETADA', 'ORIGEN_CONFIRMADO')
            """, (user_id,))
            monthly_vol = (await cur.fetchone())[0]
            
            await cur.execute("SELECT COUNT(*) FROM orders WHERE operator_user_id = %s", (user_id,))
            total_orders = (await cur.fetchone())[0]
            
            await cur.execute("""
                SELECT COUNT(*) FROM orders WHERE operator_user_id = %s
                AND status IN ('CREADA', 'ORIGEN_VERIFICANDO', 'ORIGEN_CONFIRMADO')
            """, (user_id,))
            pending = (await cur.fetchone())[0]
            
            await cur.execute("SELECT trust_score FROM users WHERE id = %s", (user_id,))
            trust = (await cur.fetchone())[0] or Decimal("50")
            
            await cur.execute("""
                WITH ranked AS (
                    SELECT id, ROW_NUMBER() OVER (ORDER BY trust_score DESC) as rank
                    FROM users WHERE kyc_status = 'APPROVED'
                )
                SELECT rank FROM ranked WHERE id = %s
            """, (user_id,))
            rank_row = await cur.fetchone()
            rank = rank_row[0] if rank_row else None
            
            return OperatorStatsResponse(
                daily_volume_usdt=daily_vol,
                monthly_volume_usdt=monthly_vol,
                total_orders=total_orders,
                pending_orders=pending,
                trust_score=trust,
                rank_position=rank
            )

@router.get("/dashboard/top-clients", response_model=List[TopClientResponse])
async def get_top_clients(user_id: int = Depends(get_current_operator), limit: int = 5):
    async with get_async_conn() as conn:
        async with conn.cursor() as cur:
            await cur.execute("""
                SELECT 
                    COALESCE(o.beneficiary_text, 'Cliente Manual') as name,
                    SUM(o.profit_real_usdt) as total_volume,
                    COUNT(*) as total_orders
                FROM orders o
                WHERE o.operator_user_id = %s AND o.status IN ('COMPLETADA', 'ORIGEN_CONFIRMADO')
                GROUP BY o.beneficiary_id, o.beneficiary_text
                ORDER BY total_volume DESC LIMIT %s
            """, (user_id, limit))
            rows = await cur.fetchall()
            return [TopClientResponse(name=r[0][:50], total_volume_usdt=r[1], total_orders=r[2]) for r in rows]

@router.get("/orders/queue", response_model=List[OrderQueueItem])
async def get_order_queue(user_id: int = Depends(get_current_operator)):
    async with get_async_conn() as conn:
        async with conn.cursor() as cur:
            await cur.execute("""
                SELECT public_id, COALESCE(beneficiary_text, 'Sin nombre') as client_name,
                amount_origin, origin_country, dest_country, status, created_at
                FROM orders WHERE operator_user_id = %s
                AND status IN ('CREADA', 'ORIGEN_VERIFICANDO', 'ORIGEN_CONFIRMADO', 'PAGO_PENDIENTE')
                ORDER BY created_at DESC LIMIT 20
            """, (user_id,))
            rows = await cur.fetchall()
            return [OrderQueueItem(
                public_id=r[0], client_name=r[1][:30], amount_origin=r[2],
                origin_country=r[3], dest_country=r[4], status=r[5], created_at=r[6]
            ) for r in rows]

@router.get("/earnings/by-country", response_model=List[EarningsByCountry])
async def get_earnings_by_country(user_id: int = Depends(get_current_operator), days: int = 30):
    async with get_async_conn() as conn:
        async with conn.cursor() as cur:
            await cur.execute("""
                SELECT dest_country, SUM(profit_real_usdt) as earnings, COUNT(*) as order_count
                FROM orders WHERE operator_user_id = %s
                AND created_at >= CURRENT_DATE - INTERVAL '%s days'
                AND status IN ('COMPLETADA', 'ORIGEN_CONFIRMADO')
                GROUP BY dest_country ORDER BY earnings DESC
            """, (user_id, days))
            rows = await cur.fetchall()
            return [EarningsByCountry(country=r[0], earnings_usdt=r[1], order_count=r[2]) for r in rows]

class OrderListItem(BaseModel):
    public_id: int
    origin_country: str
    dest_country: str
    amount_origin: Decimal
    payout_dest: Decimal
    status: str
    created_at: datetime
    beneficiary_text: str

@router.get("/orders", response_model=list[OrderListItem])
async def list_my_orders(
    limit: int = 50,
    status: Optional[str] = None,
    q: Optional[str] = None,
    user_id: int = Depends(get_current_operator),
):
    async with get_async_conn() as conn:
        async with conn.cursor() as cur:
            where = ["operator_user_id = %s"]
            params = [user_id]

            if status and status.upper() != "TODOS":
                where.append("status = %s")
                params.append(status)

            if q and q.strip():
                qq = f"%{q.strip()}%"
                where.append("(CAST(public_id AS TEXT) ILIKE %s OR COALESCE(beneficiary_text,'') ILIKE %s)")
                params.extend([qq, qq])

            where_sql = " AND ".join(where)
            params.append(limit)

            await cur.execute(
                f"""
                SELECT public_id, origin_country, dest_country, amount_origin, payout_dest,
                       status, created_at, COALESCE(beneficiary_text,'')
                FROM orders
                WHERE {where_sql}
                ORDER BY created_at DESC
                LIMIT %s
                """,
                tuple(params),
            )
            rows = await cur.fetchall()

    return [
        OrderListItem(
            public_id=r[0],
            origin_country=r[1],
            dest_country=r[2],
            amount_origin=r[3],
            payout_dest=r[4],
            status=r[5],
            created_at=r[6],
            beneficiary_text=r[7],
        )
        for r in rows
    ]

class WalletSummaryResponse(BaseModel):
    balance_usdt: Decimal
    lifetime_earnings_usdt: Decimal
    pending_withdrawals_usdt: Decimal

@router.get("/wallet/summary", response_model=WalletSummaryResponse)
async def get_wallet_summary(user_id: int = Depends(get_current_operator)):
    summary = WalletSummaryResponse(balance_usdt=Decimal("0"), lifetime_earnings_usdt=Decimal("0"), pending_withdrawals_usdt=Decimal("0"))
    try:
        async with get_async_conn() as conn:
            async with conn.cursor() as cur:
                await cur.execute("""
                    SELECT 
                        COALESCE(SUM(amount_usdt), 0) as balance 
                    FROM wallet_ledger 
                    WHERE user_id = %s
                """, (user_id,))
                res_balance = await cur.fetchone()
                if res_balance:
                    summary.balance_usdt = res_balance[0]

                await cur.execute("""
                    SELECT 
                        COALESCE(SUM(amount_usdt), 0) as lifetime 
                    FROM wallet_ledger 
                    WHERE user_id = %s AND amount_usdt > 0 AND type = 'EARNING'
                """, (user_id,))
                res_life = await cur.fetchone()
                if res_life:
                    summary.lifetime_earnings_usdt = res_life[0]

                await cur.execute("""
                    SELECT 
                        COALESCE(SUM(ABS(amount_usdt)), 0) as pending 
                    FROM wallet_ledger 
                    WHERE user_id = %s AND type = 'WITHDRAWAL_PENDING'
                """, (user_id,))
                res_pend = await cur.fetchone()
                if res_pend:
                    summary.pending_withdrawals_usdt = res_pend[0]
    except Exception as e:
        logger.warning(f"Wallet ledger table info failed (might not exist): {e}")

    return summary

class LedgerItem(BaseModel):
    id: int
    amount_usdt: Decimal
    type: str
    description: str
    created_at: datetime

@router.get("/wallet/ledger", response_model=List[LedgerItem])
async def get_wallet_ledger(limit: int = 50, user_id: int = Depends(get_current_operator)):
    items = []
    try:
        async with get_async_conn() as conn:
            async with conn.cursor() as cur:
                await cur.execute("""
                    SELECT id, amount_usdt, type, memo, created_at 
                    FROM wallet_ledger 
                    WHERE user_id = %s 
                    ORDER BY created_at DESC LIMIT %s
                """, (user_id, limit))
                rows = await cur.fetchall()
                for r in rows:
                    items.append(LedgerItem(
                        id=r[0],
                        amount_usdt=r[1],
                        type=r[2],
                        description=r[3] if r[3] else "",
                        created_at=r[4]
                    ))
    except Exception as e:
        logger.warning(f"Wallet ledger table read failed: {e}")
    return items

class WithdrawRequest(BaseModel):
    """Modelo para solicitud de retiro"""
    amount_usdt: Decimal
    withdrawal_method: str  # "bank_transfer", "crypto_usdt", "paypal", etc.
    account_info: str  # Número de cuenta, dirección wallet, email PayPal, etc.
    notes: str = ""  # Notas opcionales

@router.post("/wallet/withdraw")
async def request_withdrawal(
    req: WithdrawRequest,
    user_id: int = Depends(get_current_operator)
):
    """
    Solicita un retiro de fondos de la billetera del operador.
    
    Validaciones:
    - El monto debe ser mayor a 0
    - El operador debe tener saldo suficiente
    - El método de retiro debe ser válido
    - KYC debe estar aprobado
    """
    async with get_async_conn() as conn:
        async with conn.cursor() as cur:
            # 1. Verificar saldo disponible
            await cur.execute(
                """
                SELECT COALESCE(SUM(
                    CASE 
                        WHEN type IN ('ORDER_COMMISSION', 'BONUS', 'ADJUSTMENT_CREDIT') THEN amount_usdt
                        WHEN type IN ('WITHDRAWAL_APPROVED', 'WITHDRAWAL_PENDING', 'ADJUSTMENT_DEBIT') THEN -amount_usdt
                        ELSE 0
                    END
                ), 0) as available_balance
                FROM wallet_ledger
                WHERE operator_id = %s
                """,
                (user_id,)
            )
            row = await cur.fetchone()
            available_balance = row[0] if row else Decimal("0")
            
            # 2. Validar monto
            if req.amount_usdt <= 0:
                raise HTTPException(
                    status_code=400,
                    detail="El monto debe ser mayor a 0"
                )
            
            if req.amount_usdt > available_balance:
                raise HTTPException(
                    status_code=400,
                    detail=f"Saldo insuficiente. Disponible: ${available_balance:.2f} USDT"
                )
            
            # 3. Validar método
            valid_methods = ["bank_transfer", "crypto_usdt", "paypal", "zelle", "binance"]
            if req.withdrawal_method not in valid_methods:
                raise HTTPException(
                    status_code=400,
                    detail=f"Método inválido. Use: {', '.join(valid_methods)}"
                )
            
            # 4. Verificar KYC
            await cur.execute(
                "SELECT kyc_status FROM users WHERE id = %s",
                (user_id,)
            )
            kyc_row = await cur.fetchone()
            if not kyc_row or kyc_row[0] != 'APPROVED':
                raise HTTPException(
                    status_code=403,
                    detail="KYC no aprobado. Contacta soporte."
                )
            
            # 5. Crear registro de retiro en wallet_ledger
            await cur.execute(
                """
                INSERT INTO wallet_ledger (
                    user_id, type, amount_usdt, 
                    memo, created_at
                )
                VALUES (%s, %s, %s, %s, NOW())
                RETURNING id
                """,
                (
                    user_id,
                    "WITHDRAWAL_PENDING",
                    req.amount_usdt,
                    json.dumps({
                        "method": req.withdrawal_method,
                        "account": req.account_info,
                        "notes": req.notes,
                        "status": "pending",
                        "text": f"Retiro solicitado vía {req.withdrawal_method}"
                    })
                )
            )
            
            new_id_row = await cur.fetchone()
            withdrawal_id = str(new_id_row[0]) if new_id_row else ""

            
            await conn.commit()
            
            return {
                "status": "success",
                "message": "Solicitud de retiro enviada. Será procesada en 24-48 horas.",
                "withdrawal_id": withdrawal_id,
                "amount": float(req.amount_usdt),
                "new_balance": float(available_balance - req.amount_usdt)
            }

@router.get("/wallet/withdrawals")
async def get_withdrawals(
    limit: int = 50,
    user_id: int = Depends(get_current_operator)
):
    """
    Obtiene el historial de retiros del operador.
    
    Retorna lista de retiros ordenados por fecha (más recientes primero).
    """
    async with get_async_conn() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT 
                    id,
                    amount_usdt,
                    type,
                    description,
                    metadata,
                    created_at
                FROM wallet_ledger
                WHERE operator_id = %s 
                  AND type IN ('WITHDRAWAL_PENDING', 'WITHDRAWAL_APPROVED', 'WITHDRAWAL_REJECTED')
                ORDER BY created_at DESC
                LIMIT %s
                """,
                (user_id, limit)
            )
            
            rows = await cur.fetchall()
            
            withdrawals = []
            for row in rows:
                metadata = json.loads(row[4]) if row[4] else {}
                
                # Determinar estado
                status_map = {
                    "WITHDRAWAL_PENDING": "pending",
                    "WITHDRAWAL_APPROVED": "approved",
                    "WITHDRAWAL_REJECTED": "rejected"
                }
                
                withdrawals.append({
                    "id": row[0],
                    "amount": float(row[1]),
                    "status": status_map.get(row[2], "unknown"),
                    "method": metadata.get("method", "N/A"),
                    "account": metadata.get("account", "N/A"),
                    "notes": metadata.get("notes", ""),
                    "created_at": row[5].isoformat(),
                    "description": row[3]
                })
            
            return {
                "withdrawals": withdrawals,
                "total": len(withdrawals)
            }

class CreateOrderRequest(BaseModel):
    """Modelo para crear una orden desde la web"""
    beneficiary_id: int  # ID del contacto guardado
    amount_usd: Decimal
    payment_method: str  # "Zelle", "Bank Transfer", etc.
    notes: str = ""

@router.post("/orders/create")
async def create_order_web(
    req: CreateOrderRequest,
    user_id: int = Depends(get_current_operator)
):
    """
    Crea una nueva orden desde la interfaz web.
    
    Similar al flujo de Telegram pero adaptado para web.
    """
    async with get_async_conn() as conn:
        async with conn.cursor() as cur:
            # 1. Verificar que el beneficiario existe y pertenece al operador
            await cur.execute(
                """
                SELECT id, full_name, payment_method, account_number
                FROM saved_beneficiaries
                WHERE id = %s AND user_id = %s
                """,
                (req.beneficiary_id, user_id)
            )
            beneficiary = await cur.fetchone()
            
            if not beneficiary:
                raise HTTPException(
                    status_code=404,
                    detail="Contacto no encontrado"
                )
            
            # 2. Validar monto
            if req.amount_usd <= 0:
                raise HTTPException(
                    status_code=400,
                    detail="El monto debe ser mayor a 0"
                )
            
            if req.amount_usd > 10000:
                raise HTTPException(
                    status_code=400,
                    detail="El monto máximo por orden es $10,000 USD"
                )
            
            # 3. Crear la orden
            order_id = str(uuid4())
            await cur.execute(
                """
                INSERT INTO orders (
                    id, user_id, beneficiary_id, amount_usd,
                    payment_method, status, notes, created_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
                RETURNING id
                """,
                (
                    order_id,
                    user_id,
                    req.beneficiary_id,
                    req.amount_usd,
                    req.payment_method,
                    "PENDING_APPROVAL",  # Requiere aprobación de admin
                    req.notes
                )
            )
            
            await conn.commit()
            
            return {
                "status": "success",
                "message": "Orden creada exitosamente. Pendiente de aprobación.",
                "order_id": order_id,
                "beneficiary_name": beneficiary[1],
                "amount": float(req.amount_usd)
            }
