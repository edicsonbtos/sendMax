from pydantic import BaseModel, Field
from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional, Any

class ClosureMetrics(BaseModel):
    total_orders: int
    total_volume_origin: Decimal
    total_profit_real: Decimal
    success_rate: Decimal
    best_operator_alias: Optional[str]
    best_origin_country: Optional[str]
    best_dest_country: Optional[str]

class ClosureWarning(BaseModel):
    type: str
    message: str
    severity: str # 'low', 'medium', 'high'

class DailyClosureExecuteRequest(BaseModel):
    closure_date: date
    notes: Optional[str] = None
    force: bool = False

class DailyClosureResponse(BaseModel):
    id: int
    closure_date: date
    total_orders_count: int
    total_volume_origin: Decimal
    total_profit_usdt: Decimal
    total_profit_real: Decimal
    success_rate: Decimal
    best_operator_alias: Optional[str]
    best_origin_country: Optional[str]
    best_dest_country: Optional[str]
    pending_withdrawals_count: int
    pending_withdrawals_amount: Decimal
    vaults_snapshot: Optional[Any]
    wallet_balances_snapshot: Optional[Any]
    warnings: Optional[List[ClosureWarning]]
    notes: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True
