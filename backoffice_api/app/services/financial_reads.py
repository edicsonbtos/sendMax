"""
Financial Read Service — Single source of truth for financial reads.

READ-ONLY queries against wallet_ledger, wallets, and withdrawals.
NO writes, NO transactions, NO mutations.

This module centralizes SQL that was previously copy-pasted across:
  - routers/operator.py
  - routers/users.py
  - routers/metrics.py (leaderboard query)

Canonical for: wallet balance reads, profit metrics, ledger history,
withdrawal history, operator leaderboard.

IMPORTANT: Write operations (ledger entries, withdrawal holds, reversals)
remain in src/db/repositories/wallet_repo.py and withdrawals_repo.py.
Do NOT add write logic here.
"""

from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any

from ..db import fetch_one, fetch_all

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════
# Profit Metrics
# ══════════════════════════════════════════════════════════════

async def get_user_profit_metrics(user_id: int) -> dict[str, Any]:
    """
    Returns profit_today, profit_month, referrals_month, profit_total
    for a given user_id.  All values are Decimal or 0.
    """
    row = await fetch_one(
        """
        SELECT
            COALESCE((
                SELECT SUM(amount_usdt) FROM wallet_ledger
                WHERE user_id = %s AND type = 'ORDER_PROFIT'
                  AND created_at >= date_trunc('day', now())
            ), 0) AS profit_today,
            COALESCE((
                SELECT SUM(amount_usdt) FROM wallet_ledger
                WHERE user_id = %s AND type = 'ORDER_PROFIT'
                  AND created_at >= date_trunc('month', now())
            ), 0) AS profit_month,
            COALESCE((
                SELECT SUM(amount_usdt) FROM wallet_ledger
                WHERE user_id = %s AND type = 'SPONSOR_COMMISSION'
                  AND created_at >= date_trunc('month', now())
            ), 0) AS referrals_month,
            COALESCE((
                SELECT SUM(amount_usdt) FROM wallet_ledger
                WHERE user_id = %s AND type = 'ORDER_PROFIT'
            ), 0) AS profit_total
        """,
        (user_id, user_id, user_id, user_id),
    )
    return row or {
        "profit_today": Decimal(0),
        "profit_month": Decimal(0),
        "referrals_month": Decimal(0),
        "profit_total": Decimal(0),
    }


# ══════════════════════════════════════════════════════════════
# Wallet Ledger
# ══════════════════════════════════════════════════════════════

async def get_user_ledger(user_id: int, limit: int = 15) -> list[dict[str, Any]]:
    """Recent wallet_ledger entries for a user, ordered by most recent first."""
    return await fetch_all(
        """
        SELECT id, amount_usdt, type, ref_order_public_id, memo, created_at
        FROM wallet_ledger
        WHERE user_id = %s
        ORDER BY created_at DESC
        LIMIT %s
        """,
        (user_id, limit),
    )


# ══════════════════════════════════════════════════════════════
# Withdrawals
# ══════════════════════════════════════════════════════════════

async def get_user_withdrawals(user_id: int, limit: int = 10) -> list[dict[str, Any]]:
    """Recent withdrawal records for a user, ordered by most recent first."""
    return await fetch_all(
        """
        SELECT id, amount_usdt, status, dest_text, country,
               fiat, fiat_amount, reject_reason,
               created_at, resolved_at
        FROM withdrawals
        WHERE user_id = %s
        ORDER BY created_at DESC
        LIMIT %s
        """,
        (user_id, limit),
    )


# ══════════════════════════════════════════════════════════════
# Operator Leaderboard
# ══════════════════════════════════════════════════════════════

async def get_operator_leaderboard(limit: int = 10) -> list[dict[str, Any]]:
    """
    Top operators by trust_score + monthly profit.
    Used by both /operator/me/dashboard and /metrics/operator-leaderboard.
    """
    return await fetch_all(
        """
        SELECT u.id, u.alias, u.full_name,
               COALESCE(u.trust_score, 50) AS trust_score,
               u.kyc_status,
               COALESCE((
                   SELECT SUM(wl.amount_usdt) FROM wallet_ledger wl
                   WHERE wl.user_id = u.id AND wl.type = 'ORDER_PROFIT'
                     AND wl.created_at >= date_trunc('month', now())
               ), 0) AS profit_month,
               COALESCE((
                   SELECT COUNT(*) FROM orders o
                   WHERE o.operator_user_id = u.id AND o.status = 'PAGADA'
                     AND o.created_at >= date_trunc('month', now())
               ), 0) AS orders_month
        FROM users u
        WHERE u.role IN ('operator', 'admin')
        ORDER BY u.trust_score DESC NULLS LAST, profit_month DESC
        LIMIT %s
        """,
        (limit,),
    )
