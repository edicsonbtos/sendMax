import pytest
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from src.db.repositories.orders_repo import VALID_STATUSES, VALID_TRANSITIONS

def test_status_validity():
    assert "CREADA" in VALID_STATUSES
    assert "ORIGEN_VERIFICANDO" in VALID_STATUSES
    assert "COMPLETADA" in VALID_STATUSES

def test_transitions():
    assert "ORIGEN_VERIFICANDO" in VALID_TRANSITIONS["CREADA"]
    assert "ORIGEN_CONFIRMADO" in VALID_TRANSITIONS["ORIGEN_VERIFICANDO"]
    assert "COMPLETADA" in VALID_TRANSITIONS["EN_PROCESO"]
    assert "COMPLETADA" in VALID_TRANSITIONS["PAGADA"]

@pytest.mark.asyncio
async def test_create_order_params():
    from src.db.repositories import orders_repo
    assert callable(orders_repo.create_order)
    assert callable(orders_repo.set_awaiting_paid_proof)
