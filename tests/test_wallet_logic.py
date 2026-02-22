import pytest
from decimal import Decimal
from unittest.mock import AsyncMock, patch, MagicMock
from src.db.repositories import wallet_repo

@pytest.mark.asyncio
async def test_add_ledger_entry_tx_logic():
    mock_conn = MagicMock()
    mock_cur = AsyncMock()

    mock_conn.cursor.return_value.__aenter__.return_value = mock_cur

    # Simulate first time insert (RETURNING id returns something)
    mock_cur.fetchone.side_effect = [
        (123,), # RETURNING id for ledger
    ]

    await wallet_repo.add_ledger_entry_tx(
        mock_conn,
        user_id=1,
        amount_usdt=Decimal("10.5"),
        entry_type="ORDER_PROFIT",
        ref_order_public_id=100
    )

    calls = mock_cur.execute.call_args_list
    assert any("INSERT INTO wallets" in str(c[0][0]) for c in calls)
    assert any("INSERT INTO wallet_ledger" in str(c[0][0]) for c in calls)
    assert any("UPDATE wallets" in str(c[0][0]) for c in calls)

@pytest.mark.asyncio
async def test_add_ledger_entry_tx_idempotency_logic():
    mock_conn = MagicMock()
    mock_cur = AsyncMock()

    mock_conn.cursor.return_value.__aenter__.return_value = mock_cur

    # Simulate conflict (RETURNING id returns None)
    mock_cur.fetchone.side_effect = [
        None, # INSERT ledger (conflict DO NOTHING returning nothing)
    ]

    await wallet_repo.add_ledger_entry_tx(
        mock_conn,
        user_id=1,
        amount_usdt=Decimal("10.5"),
        entry_type="ORDER_PROFIT",
        ref_order_public_id=100
    )

    calls = mock_cur.execute.call_args_list
    assert any("INSERT INTO wallet_ledger" in str(c[0][0]) for c in calls)
    assert not any("UPDATE wallets" in str(c[0][0]) for c in calls)
