import pytest
from unittest.mock import patch
from fastapi import HTTPException
import asyncio

from backoffice_api.app.routers.metrics import admin_metrics_daily_snapshot

# Mocks
AUTH_ADMIN = {"role": "ADMIN", "user_id": 1}
AUTH_OPERATOR = {"role": "OPERATOR", "user_id": 2}

@pytest.mark.asyncio
async def test_admin_metrics_daily_snapshot_admin_only():
    """Test: debe rechazar si no es admin."""
    with pytest.raises(HTTPException) as exc_info:
        await admin_metrics_daily_snapshot("2026-03-24", auth=AUTH_OPERATOR)
    assert exc_info.value.status_code == 403

@pytest.mark.asyncio
@patch("backoffice_api.app.routers.metrics.fetch_one")
async def test_admin_metrics_daily_snapshot_success(mock_fetch_one):
    """Test: validando response shape completo y cálculo de net_retained_today."""
    mock_fetch_one.side_effect = [
        {"orders_completed": 5, "volume_usd": 1200.0, "gross_profit_today": 48.50},  
        {"commissions_today": 24.25},  
        {"payouts_today": 0.0},  
        {"new_withdrawal_requests": 1}   
    ]
    res = await admin_metrics_daily_snapshot("2026-03-24", auth=AUTH_ADMIN)

    assert res["date"] == "2026-03-24"
    assert res["orders_completed"] == 5
    assert res["volume_usd"] == 1200.0
    assert res["gross_profit_today"] == 48.50
    assert res["commissions_today"] == 24.25
    assert res["net_retained_today"] == 24.25  # Requerimiento: gross_profit_today - commissions_today
    assert res["payouts_today"] == 0.0
    assert res["new_withdrawal_requests"] == 1
    assert "restringidos" not in res["disclaimer"]  # Just minor check to ensure disclaimer exists
    
    assert isinstance(res["orders_completed"], int)
    assert isinstance(res["volume_usd"], float)

@pytest.mark.asyncio
@patch("backoffice_api.app.routers.metrics.fetch_one")
async def test_admin_metrics_daily_snapshot_no_data(mock_fetch_one):
    """Test: base de datos devuelve None por falta de datos, todo debe ser 0 para un json seguro."""
    mock_fetch_one.side_effect = [None, None, None, None]
    
    res = await admin_metrics_daily_snapshot("2026-03-24", auth=AUTH_ADMIN)

    assert res["date"] == "2026-03-24"
    assert res["orders_completed"] == 0
    assert res["volume_usd"] == 0.0
    assert res["gross_profit_today"] == 0.0
    assert res["commissions_today"] == 0.0
    assert res["net_retained_today"] == 0.0
    assert res["payouts_today"] == 0.0
    assert res["new_withdrawal_requests"] == 0
    assert "disclaimer" in res
