"""Router: Alertas de órdenes atascadas"""

from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends
from ..db import fetch_all
from ..auth import verify_api_key

router = APIRouter(tags=["alerts"])


@router.get("/alerts/stuck")
def alerts_stuck(api_key: str = Depends(verify_api_key)):
    from ..audit import get_stuck_orders
    return get_stuck_orders()


@router.get("/alerts/stuck-30m")
def alerts_stuck_30m(api_key: str = Depends(verify_api_key)):
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(minutes=30)

    origin_rows = fetch_all(
        """
        SELECT public_id, origin_country, dest_country, status, created_at, updated_at
        FROM orders
        WHERE status='ORIGEN_VERIFICANDO'
          AND created_at < %s
        ORDER BY created_at ASC
        LIMIT 100
        """,
        (cutoff,),
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
        LIMIT 100
        """,
        (cutoff,),
    )

    def iso(x):
        return x.isoformat() if x else None

    return {
        "ok": True,
        "cutoff_utc": cutoff.isoformat(),
        "origin_verificando_stuck": [
            {
                "public_id": r["public_id"],
                "origin_country": r["origin_country"],
                "dest_country": r["dest_country"],
                "status": r["status"],
                "created_at": iso(r["created_at"]),
                "updated_at": iso(r["updated_at"]),
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
            }
            for r in pay_rows
        ],
    }
