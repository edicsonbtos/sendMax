"""
Tests de regresión para los fixes quirúrgicos:
  - PR-1: vault query usa status = 'RESUELTA' (no ILIKE '%%PAID%%')
  - PR-2: ledger integrity check usa user_id (no wallet_id)

Estrategia: se parchean fetch_one/fetch_all para capturar el SQL
ejecutado por el endpoint y validarlo directamente.
No se usa inspect.getsource (frágil), no se necesita DB real.
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_auth(role="admin"):
    return {"role": role, "auth": "api_key", "user_id": 1}


# ---------------------------------------------------------------------------
# PR-1 — Vault: withdrawal query usa 'RESUELTA'
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_vault_withdrawal_query_uses_resuelta():
    """
    Verifica que admin_metrics_vault llama fetch_one con status = 'RESUELTA'
    y que no usa PAID ni PAGADO.
    """
    captured_sqls = []

    async def fake_fetch_one(sql, *args, **kwargs):
        captured_sqls.append(sql)
        # Primer call: profit query -> devolver total_profit
        # Segundo call: withdrawals query -> devolver total_withdrawals
        if "profit" in sql.lower():
            return {"total_profit": "500.00"}
        return {"total_withdrawals": "100.00"}

    with patch("backoffice_api.app.routers.metrics.fetch_one", side_effect=fake_fetch_one):
        from backoffice_api.app.routers.metrics import admin_metrics_vault
        result = await admin_metrics_vault(auth=_make_auth())

    withdrawal_sqls = [s for s in captured_sqls if "withdrawals" in s.lower()]
    assert withdrawal_sqls, "No se ejecutó ningún query sobre withdrawals"

    wq = withdrawal_sqls[0]
    assert "RESUELTA" in wq, f"Query no contiene 'RESUELTA': {wq}"
    assert "PAID" not in wq.upper(), f"Query todavía contiene 'PAID': {wq}"
    assert "PAGADO" not in wq.upper(), f"Query todavía contiene 'PAGADO': {wq}"


@pytest.mark.asyncio
async def test_vault_balance_calculation():
    """
    Verifica que vault_balance = total_profit - total_withdrawals.
    """
    async def fake_fetch_one(sql, *args, **kwargs):
        if "profit" in sql.lower():
            return {"total_profit": "1000.00"}
        return {"total_withdrawals": "300.00"}

    with patch("backoffice_api.app.routers.metrics.fetch_one", side_effect=fake_fetch_one):
        from backoffice_api.app.routers.metrics import admin_metrics_vault
        result = await admin_metrics_vault(auth=_make_auth())

    assert result["ok"] is True
    assert result["total_profit"] == pytest.approx(1000.0)
    assert result["total_withdrawals"] == pytest.approx(300.0)
    assert result["vault_balance"] == pytest.approx(700.0)


@pytest.mark.asyncio
async def test_vault_rejects_non_admin():
    """
    Verifica que operadores no pueden acceder al vault.
    """
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc_info:
        from backoffice_api.app.routers.metrics import admin_metrics_vault
        await admin_metrics_vault(auth={"role": "operator", "user_id": 99})
    assert exc_info.value.status_code == 403


# ---------------------------------------------------------------------------
# PR-2 — Executive risk: ledger integrity check usa user_id
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_ledger_integrity_check_uses_user_id():
    """
    Verifica que executive_risk llama fetch_all con GROUP BY user_id
    y que no usa wallet_id.
    """
    captured_sqls = []

    async def fake_fetch_one(sql, *args, **kwargs):
        captured_sqls.append(("fetch_one", sql))
        # stuck orders, pending withdrawals, anomalies (fetch_one variant)
        if "SOLICITADA" in sql:
            return {"count": 0, "total": "0.00"}
        if "profit_usdt" in sql:
            return None  # sin anomalías
        return {"count": 0}

    async def fake_fetch_all(sql, *args, **kwargs):
        captured_sqls.append(("fetch_all", sql))
        return []

    # get_stuck_orders también usa fetch_all; devolver vacío
    with (
        patch("backoffice_api.app.routers.executive.fetch_one", side_effect=fake_fetch_one),
        patch("backoffice_api.app.routers.executive.fetch_all", side_effect=fake_fetch_all),
        patch("backoffice_api.app.routers.executive.get_stuck_orders", new=AsyncMock(return_value={})),
    ):
        from backoffice_api.app.routers.executive import executive_risk
        result = await executive_risk(auth=_make_auth())

    ledger_sqls = [
        sql for (kind, sql) in captured_sqls
        if "wallet_ledger" in sql
    ]
    assert ledger_sqls, "No se ejecutó ningún query sobre wallet_ledger"

    lq = ledger_sqls[0]
    assert "user_id" in lq, f"Query no contiene 'user_id': {lq}"
    assert "wallet_id" not in lq, f"Query todavía contiene 'wallet_id': {lq}"


@pytest.mark.asyncio
async def test_executive_risk_returns_health_score():
    """
    Verifica que executive_risk devuelve un health_score entre 0 y 100.
    """
    async def fake_fetch_one(sql, *_a, **_kw):
        if "SOLICITADA" in sql:
            return {"count": 0, "total": "0.00"}
        if "profit_usdt" in sql:
            return None
        return {"count": 0}

    with (
        patch("backoffice_api.app.routers.executive.fetch_one", side_effect=fake_fetch_one),
        patch("backoffice_api.app.routers.executive.fetch_all", new=AsyncMock(return_value=[])),
        patch("backoffice_api.app.routers.executive.get_stuck_orders", new=AsyncMock(return_value={})),
    ):
        from backoffice_api.app.routers.executive import executive_risk
        result = await executive_risk(auth=_make_auth())

    assert result["ok"] is True
    score = result["data"]["health_score"]
    assert 0 <= score <= 100, f"health_score fuera de rango: {score}"
