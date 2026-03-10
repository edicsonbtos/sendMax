from sqlalchemy import Column, BigInteger, Integer, String, Numeric, Date, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class DailyClosure(Base):
    __tablename__ = 'daily_closures'

    id = Column(BigInteger, primary_key=True)
    closure_date = Column(Date, nullable=False, unique=True, index=True)
    total_orders_count = Column(Integer, nullable=False, default=0)
    total_volume_origin = Column(Numeric(20, 2), nullable=False, default=0)
    total_profit_usdt = Column(Numeric(20, 8), nullable=False, default=0)
    total_profit_real = Column(Numeric(20, 8), nullable=False, default=0)
    success_rate = Column(Numeric(5, 2), nullable=False, default=100.00)
    
    # Performer Rankings
    best_operator_id = Column(BigInteger, ForeignKey('users.id'))
    best_operator_alias = Column(String(100))
    best_origin_country = Column(String(50))
    best_dest_country = Column(String(50))
    
    # Withdrawals
    pending_withdrawals_count = Column(Integer, nullable=False, default=0)
    pending_withdrawals_amount = Column(Numeric(20, 8), nullable=False, default=0)
    
    # Snapshots
    vaults_snapshot = Column(JSONB)
    wallet_balances_snapshot = Column(JSONB)
    
    # Metadata
    warnings = Column(JSONB)
    notes = Column(Text)
    executed_by = Column(BigInteger, nullable=False) # Store user_id
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

# Mirror models for SQLAlchemy queries (if needed by the router)
class OrderMirror(Base):
    __tablename__ = 'orders'
    id = Column(BigInteger, primary_key=True)
    status = Column(String)
    amount_origin = Column(Numeric)
    profit_usdt = Column(Numeric)
    profit_real_usdt = Column(Numeric)
    operator_user_id = Column(BigInteger)
    origin_country = Column(String)
    dest_country = Column(String)
    created_at = Column(DateTime(timezone=True))
    paid_at = Column(DateTime(timezone=True))

class UserMirror(Base):
    __tablename__ = 'users'
    id = Column(BigInteger, primary_key=True)
    alias = Column(String)
    role = Column(String)
