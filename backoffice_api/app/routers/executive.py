"""
Router: Executive Aggregators (Phase 4)
Consolida vistas de Control Center, Treasury, Vaults, Risk y Audit.
"""

from __future__ import annotations
import asyncio
import datetime
from fastapi import APIRouter, Depends, Query, HTTPException
from ..db import fetch_one, fetch_all
from ..auth import require_operator_or_admin, require_admin
from .metrics import metrics_overview, admin_metrics_vault, metrics_operator_leaderboard, _is_admin
from .origin_wallets import origin_wallets_current_balances
from .vaults import vault_radar, list_vaults
from ..audit import get_stuck_orders

router = APIRouter(prefix="/executive", tags=["Executive"])

# ============================================================
# GET /executive/control-center
# ============================================================

@router.get("/control-center")
async def executive_control_center(auth: dict = Depends(require_operator_or_admin)):
    """Vista de alto nivel del sistema."""
    is_admin_user = _is_admin(auth)
    
    # Tareas base (Overview y Leaderboard)
    tasks = [
        metrics_overview(auth),
        metrics_operator_leaderboard(limit=5, auth=auth)
    ]
    
    # Solo admin ve Vault y Alertas de riesgo
    if is_admin_user:
        tasks.append(admin_metrics_vault(auth))
        tasks.append(get_stuck_orders())

    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Procesar resultados
    overview = results[0] if not isinstance(results[0], Exception) else {}
    leaderboard = results[1] if not isinstance(results[1], Exception) else {"leaderboard": []}
    
    vault = None
    risk_summary = None
    if is_admin_user:
        vault = results[2] if len(results) > 2 and not isinstance(results[2], Exception) else None
        risk_summary = results[3] if len(results) > 3 and not isinstance(results[3], Exception) else None

    # Fetch recent orders (real activity)
    recent_orders = await fetch_all(
        "SELECT public_id, status, created_at, amount_origin, origin_country, dest_country "
        "FROM orders ORDER BY created_at DESC LIMIT 10"
    )

    return {
        "ok": True,
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        "data": {
            "overview": overview,
            "leaderboard": leaderboard.get("leaderboard", []),
            "vault": vault,
            "recent_activity": recent_orders,
            "risk_alerts": risk_summary,
            "config": {
                "role": auth.get("role"),
                "is_admin": is_admin_user
            }
        }
    }

# ============================================================
# GET /executive/treasury
# ============================================================

@router.get("/treasury")
async def executive_treasury(auth: dict = Depends(require_admin)):
    """Vista consolidada de tesorería origen."""
    orig_balances = await origin_wallets_current_balances(auth)
    
    # Agregado por país
    by_country = {}
    for item in orig_balances.get("items", []):
        country = item["origin_country"]
        if country not in by_country:
            by_country[country] = {"country": country, "total_balance_usd": 0.0, "currencies": []}
        
        # En una versión real se usaría tasa de cambio, aquí asumimos balance o agregamos balances
        by_country[country]["currencies"].append(item)
        by_country[country]["total_balance_usd"] += float(item["current_balance"])

    return {
        "ok": True,
        "data": {
            "balances": orig_balances.get("items", []),
            "by_country": list(by_country.values())
        }
    }

# ============================================================
# GET /executive/vaults
# ============================================================

@router.get("/vaults")
async def executive_vaults(auth: dict = Depends(require_admin)):
    """Vista de liquidez central."""
    radar = await vault_radar(auth)
    vaults_list = await list_vaults(auth)
    central = await admin_metrics_vault(auth)

    return {
        "ok": True,
        "data": {
            "central_vault": central,
            "radar": radar,
            "vaults": vaults_list.get("vaults", [])
        }
    }

# ============================================================
# GET /executive/risk
# ============================================================

@router.get("/risk")
async def executive_risk(auth: dict = Depends(require_admin)):
    """Monitor de riesgo operativo."""
    stuck = await get_stuck_orders()
    
    # Retiros pendientes
    pending_withdrawals = await fetch_one(
        "SELECT COUNT(*) as count, SUM(amount_usdt) as total FROM withdrawals WHERE status = 'SOLICITADA'"
    )
    
    # Anomalías: Órdenes con profit negativo (si existieran) o cancelaciones masivas recientes
    anomalies = await fetch_all(
        "SELECT public_id, status, profit_usdt FROM orders WHERE profit_usdt < 0 OR (status = 'CANCELADA' AND updated_at > NOW() - INTERVAL '2 hours') LIMIT 10"
    )

    return {
        "ok": True,
        "data": {
            "stuck_orders": stuck,
            "pending_withdrawals": {
                "count": int(pending_withdrawals["count"]) if pending_withdrawals else 0,
                "amount": float(pending_withdrawals["total"]) if pending_withdrawals and pending_withdrawals["total"] else 0.0
            },
            "anomalies": anomalies,
            "health_score": 100 - (int(stuck.get("stuck_origin_verification_count", 0)) * 2) - (len(anomalies) * 5)
        }
    }

# ============================================================
# GET /executive/audit
# ============================================================

@router.get("/audit")
async def executive_audit_feed(auth: dict = Depends(require_admin)):
    """Feed de trazabilidad ejecutiva."""
    # Eventos: Cierres, Sweeps, Toggles de Usuarios
    closures = await fetch_all(
        "SELECT closure_date as date, 'DAILY_CLOSE' as type, notes as detail, executed_by as actor FROM daily_closures ORDER BY created_at DESC LIMIT 10"
    )
    sweeps = await fetch_all(
        "SELECT created_at as date, 'SWEEP' as type, note as detail, created_by_telegram_id as actor FROM origin_sweeps ORDER BY created_at DESC LIMIT 15"
    )
    
    # Combinar y ordenar
    feed = []
    for c in closures:
        feed.append({"date": c["date"].isoformat() if hasattr(c["date"], "isoformat") else str(c["date"]), "type": c["type"], "detail": c["detail"], "actor": str(c["actor"])})
    for s in sweeps:
        feed.append({"date": s["date"].isoformat(), "type": s["type"], "detail": s["detail"], "actor": str(s["actor"])})
    
    feed.sort(key=lambda x: x["date"], reverse=True)

    return {
        "ok": True,
        "data": {
            "feed": feed[:20]
        }
    }
