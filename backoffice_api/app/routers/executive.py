"""
Router: Executive Aggregators - Evolution (Phase 5)
Consolida vistas de Control Center, Treasury, Vaults, Risk y Audit con logs de actividad.
"""

from __future__ import annotations
import asyncio
import datetime
from typing import Any, Dict
from fastapi import APIRouter, Depends, Query, HTTPException
from ..db import fetch_one, fetch_all
from ..auth import require_operator_or_admin, require_admin
from .metrics import metrics_overview, admin_metrics_vault, metrics_operator_leaderboard, _is_admin
from .origin_wallets import origin_wallets_current_balances
from .vaults import vault_radar, list_vaults
from ..audit import get_stuck_orders
from decimal import Decimal

router = APIRouter(prefix="/executive", tags=["Executive"])

def _ser(row: dict | Any) -> Any:
    if not isinstance(row, dict):
        return row
    out = {}
    for k, v in row.items():
        if v is None:
            out[k] = None
        elif isinstance(v, Decimal):
            out[k] = float(v)
        elif hasattr(v, "isoformat"):
            out[k] = v.isoformat()
        else:
            out[k] = v
    return out

def _ser_list(rows: list[dict] | None) -> list[dict]:
    return [_ser(r) for r in (rows or [])]

# ============================================================
# GET /executive/control-center
# ============================================================

@router.get("/control-center")
async def executive_control_center(auth: dict = Depends(require_operator_or_admin)):
    """Vista de alto nivel del sistema."""
    is_admin_user = _is_admin(auth)
    
    tasks = [
        metrics_overview(auth),
        metrics_operator_leaderboard(limit=5, auth=auth)
    ]
    
    if is_admin_user:
        tasks.append(admin_metrics_vault(auth))
        tasks.append(get_stuck_orders())

    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Mapeo seguro de resultados
    overview = results[0] if len(results) > 0 and not isinstance(results[0], Exception) else {}
    leaderboard = results[1] if len(results) > 1 and not isinstance(results[1], Exception) else {"leaderboard": []}
    
    vault = None
    risk_summary = None
    
    # Si es admin, los índices 2 y 3 corresponden a vault y stuck
    if is_admin_user:
        if len(results) > 2:
            vault = results[2] if not isinstance(results[2], Exception) else None
        if len(results) > 3:
            risk_summary = results[3] if not isinstance(results[3], Exception) else None

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
            "recent_activity": _ser_list(recent_orders),
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
    
    by_country = {}
    for item in orig_balances.get("items", []):
        country = item["origin_country"]
        if country not in by_country:
            by_country[country] = {"country": country, "total_balance_usd": 0.0, "currencies": []}
        
        by_country[country]["currencies"].append(item)
        by_country[country]["total_balance_usd"] += float(item["current_balance"])

    return {
        "ok": True,
        "data": {
            "balances": _ser_list(orig_balances.get("items", [])),
            "by_country": _ser_list(list(by_country.values()))
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
            "central_vault": _ser(central),
            "radar": _ser(radar),
            "vaults": _ser_list(vaults_list.get("vaults", []))
        }
    }

# ============================================================
# GET /executive/risk
# ============================================================

@router.get("/risk")
async def executive_risk(auth: dict = Depends(require_admin)):
    """Monitor de riesgo operativo y checks de integridad (Fase 5)."""
    stuck = await get_stuck_orders()
    
    # Retiros pendientes
    pending_withdrawals = await fetch_one(
        "SELECT COUNT(*) as count, SUM(amount_usdt) as total FROM withdrawals WHERE status = 'SOLICITADA'"
    )
    
    # Anomalías severas
    anomalies = await fetch_all(
        "SELECT public_id, status, profit_usdt FROM orders WHERE profit_usdt < 0 OR (status = 'CANCELADA' AND updated_at > NOW() - INTERVAL '4 hours') LIMIT 10"
    )

    # Check de integridad de Ledger (lectura simple)
    # Detectar si hay wallets con balance != suma de ledger (si aplica)
    # Por ahora detectamos balances negativos anómalos en ledger
    ledger_anomalies = await fetch_all(
        "SELECT wallet_id, SUM(amount_usdt) as balance FROM wallet_ledger GROUP BY wallet_id HAVING SUM(amount_usdt) < -0.01 LIMIT 5"
    )

    # Detección de liquidez estacionada (> 48h sin sweep en origin)
    stagnant_liquidity = await fetch_all(
        "SELECT origin_country, current_balance FROM origin_wallets WHERE current_balance > 100 AND (last_sweep_at < NOW() - INTERVAL '48 hours' OR last_sweep_at IS NULL)"
    )

    health_score = 100
    health_score -= (int(stuck.get("stuck_origin_verification_count", 0)) * 2)
    health_score -= (len(anomalies) * 5)
    health_score -= (len(ledger_anomalies) * 10)
    health_score = max(0, health_score)

    return {
        "ok": True,
        "data": {
            "stuck_orders": _ser(stuck),
            "pending_withdrawals": {
                "count": int(pending_withdrawals["count"]) if pending_withdrawals else 0,
                "amount": float(pending_withdrawals["total"]) if pending_withdrawals and pending_withdrawals["total"] else 0.0
            },
            "anomalies": _ser_list(anomalies),
            "integrity": {
                "ledger_anomalies": _ser_list(ledger_anomalies),
                "stagnant_liquidity": _ser_list(stagnant_liquidity)
            },
            "health_score": health_score
        }
    }

# ============================================================
# GET /executive/audit
# ============================================================

@router.get("/audit")
async def executive_audit_feed(auth: dict = Depends(require_admin)):
    """Feed de trazabilidad ejecutiva rica (Fase 5)."""
    # 1. Cierres
    closures = await fetch_all(
        "SELECT closure_date as date, 'DAILY_CLOSE' as type, notes as detail, executed_by as actor, 'INFO' as severity FROM daily_closures ORDER BY created_at DESC LIMIT 10"
    )
    # 2. Sweeps
    sweeps = await fetch_all(
        "SELECT created_at as date, 'SWEEP' as type, note as detail, created_by_telegram_id as actor, 'INFO' as severity FROM origin_sweeps ORDER BY created_at DESC LIMIT 15"
    )
    # 3. Retiros (Aprobaciones/Rechazos)
    withdrawals = await fetch_all(
        "SELECT updated_at as date, 'WITHDRAWAL' as type, (status || ' - ' || public_id) as detail, processed_by as actor, "
        "CASE WHEN status = 'RECHAZADA' THEN 'WARNING' ELSE 'INFO' END as severity "
        "FROM withdrawals WHERE status != 'SOLICITADA' ORDER BY updated_at DESC LIMIT 15"
    )
    # 4. Usuarios (Toggles de estado)
    user_changes = await fetch_all(
        "SELECT updated_at as date, 'USER_CONFIG' as type, (alias || ' status changed') as detail, 'SYSTEM' as actor, 'WARNING' as severity "
        "FROM users WHERE updated_at > NOW() - INTERVAL '7 days' ORDER BY updated_at DESC LIMIT 10"
    )
    
    feed = []
    for c in closures:
        feed.append({"date": str(c["date"]), "type": c["type"], "detail": c["detail"], "actor": str(c["actor"]), "severity": c["severity"]})
    for s in sweeps:
        feed.append({"date": s["date"].isoformat(), "type": s["type"], "detail": s["detail"], "actor": str(s["actor"]), "severity": s["severity"]})
    for w in withdrawals:
        feed.append({"date": w["date"].isoformat(), "type": w["type"], "detail": w["detail"], "actor": str(w["actor"]), "severity": w["severity"]})
    for u in user_changes:
        feed.append({"date": u["date"].isoformat(), "type": u["type"], "detail": u["detail"], "actor": u["actor"], "severity": u["severity"]})
    
    feed.sort(key=lambda x: x["date"], reverse=True)

    return {
        "ok": True,
        "data": {
            "feed": feed[:40]
        }
    }
