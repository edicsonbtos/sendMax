"""Router: Alertas de ordenes atascadas - Modulo 8 hardened (10x)"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Query

from ..auth import verify_api_key
from ..db import fetch_all, fetch_one

router = APIRouter(tags=["alerts"])


@router.get("/alerts/stuck")
def alerts_stuck(auth: dict = Depends(verify_api_key)):
    from ..audit import get_stuck_orders
    return get_stuck_orders()


@router.get("/alerts/stuck-30m")
def alerts_stuck_30m(
    minutes: int = Query(default=30, ge=5, le=1440),
    limit: int = Query(default=200, ge=10, le=1000),
    auth: dict = Depends(verify_api_key),
):
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(minutes=minutes)

    total_origin = fetch_one(
        """
        SELECT COUNT(*) AS cnt
        FROM orders
        WHERE status = 'ORIGEN_VERIFICANDO'
          AND COALESCE(updated_at, created_at) < %s
        """,
        (cutoff,),
    )

    total_pay = fetch_one(
        """
        SELECT COUNT(*) AS cnt
        FROM orders
        WHERE awaiting_paid_proof = true
          AND awaiting_paid_proof_at IS NOT NULL
          AND awaiting_paid_proof_at < %s
        """,
        (cutoff,),
    )

    origin_rows = fetch_all(
        """
        SELECT public_id, origin_country, dest_country, status,
               created_at, updated_at
        FROM orders
        WHERE status = 'ORIGEN_VERIFICANDO'
          AND COALESCE(updated_at, created_at) < %s
        ORDER BY COALESCE(updated_at, created_at) ASC
        LIMIT %s
        """,
        (cutoff, limit),
    )

    pay_rows = fetch_all(
        """
        SELECT public_id, origin_country, dest_country, status,
               awaiting_paid_proof_at, updated_at
        FROM orders
        WHERE awaiting_paid_proof = true
          AND awaiting_paid_proof_at IS NOT NULL
          AND awaiting_paid_proof_at < %s
        ORDER BY awaiting_paid_proof_at ASC
        LIMIT %s
        """,
        (cutoff, limit),
    )

    def iso(x: Any) -> Optional[str]:
        return x.isoformat() if x else None

    def minutes_since(ts: Any) -> Optional[int]:
        if not ts:
            return None
        try:
            return int((now - ts).total_seconds() // 60)
        except Exception:
            return None

    cnt_origin_total = int((total_origin or {}).get("cnt") or 0)
    cnt_pay_total = int((total_pay or {}).get("cnt") or 0)

    return {
        "ok": True,
        "cutoff_minutes": minutes,
        "cutoff_utc": cutoff.isoformat(),
        "limit": limit,
        "counts": {
            "origin_verificando_total": cnt_origin_total,
            "awaiting_paid_proof_total": cnt_pay_total,
            "origin_verificando_returned": len(origin_rows),
            "awaiting_paid_proof_returned": len(pay_rows),
            "grand_total": cnt_origin_total + cnt_pay_total,
        },
        "origin_verificando_stuck": [
            {
                "public_id": r["public_id"],
                "origin_country": r["origin_country"],
                "dest_country": r["dest_country"],
                "status": r["status"],
                "created_at": iso(r["created_at"]),
                "updated_at": iso(r["updated_at"]),
                "stuck_since": iso(r.get("updated_at") or r.get("created_at")),
                "stuck_minutes": minutes_since(r.get("updated_at") or r.get("created_at")),
            }
            for r in origin_rows
        ],
        "awaiting_paid_proof_stuck": [
            {
                "public_id": r["public_id"],
                "origin_country": r["origin_country"],
                "dest_country": r["dest_country"],
                "status": r["status"],
                "awaiting_paid_proof_at": iso(r["awaiting_paid_proof_at"]),
                "updated_at": iso(r["updated_at"]),
                "stuck_minutes": minutes_since(r.get("awaiting_paid_proof_at")),
            }
            for r in pay_rows
        ],
    }