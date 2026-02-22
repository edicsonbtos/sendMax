from __future__ import annotations

import sys
from decimal import Decimal
from datetime import datetime
import psycopg

from src.config.settings import settings

# Helpers
def fail(msg: str) -> None:
    print(f"[FAIL] {msg}")
    raise SystemExit(1)

def ok(msg: str) -> None:
    print(f"[OK] {msg}")

def fetchone(cur, q: str, params=()):
    cur.execute(q, params)
    return cur.fetchone()

def fetchall(cur, q: str, params=()):
    cur.execute(q, params)
    return cur.fetchall()

def ensure_wallet(cur, user_id: int):
    cur.execute("SELECT 1 FROM wallets WHERE user_id=%s;", (user_id,))
    if not cur.fetchone():
        cur.execute("INSERT INTO wallets (user_id, balance_usdt) VALUES (%s, 0);", (user_id,))

def main() -> int:
    # 0) Basic env
    if not settings.DATABASE_URL:
        fail("DATABASE_URL missing")
    ok("DATABASE_URL present")

    with psycopg.connect(settings.DATABASE_URL) as conn:
        with conn.cursor() as cur:
            # 1) Tables exist
            tables = {r[0] for r in fetchall(cur, "SELECT table_name FROM information_schema.tables WHERE table_schema='public';")}
            for t in ["users", "orders", "wallets", "wallet_ledger", "withdrawals"]:
                if t not in tables:
                    fail(f"missing table: {t}")
            ok("Core tables exist")

            # 2) Users sanity
            row = fetchone(cur, "SELECT id, telegram_user_id, alias FROM users ORDER BY id ASC LIMIT 1;")
            if not row:
                fail("No users in DB (need at least 1 registered user)")
            user_id = int(row[0])
            ok(f"User exists: id={user_id}, alias={row[2]}")

            # 3) Wallet balance is numeric
            ensure_wallet(cur, user_id)
            row = fetchone(cur, "SELECT balance_usdt FROM wallets WHERE user_id=%s;", (user_id,))
            bal = Decimal(str(row[0]))
            ok(f"Wallet balance readable: {bal}")

            # 4) Ledger idempotency (ORDER_PROFIT) check for last paid order
            last_paid = fetchone(cur, "SELECT public_id, operator_user_id, profit_usdt FROM orders WHERE status='PAGADA' AND profit_usdt IS NOT NULL ORDER BY public_id DESC LIMIT 1;")
            if last_paid:
                pid, op_uid, profit = int(last_paid[0]), int(last_paid[1]), Decimal(str(last_paid[2]))
                led = fetchall(cur, "SELECT id, amount_usdt, type FROM wallet_ledger WHERE ref_order_public_id=%s AND user_id=%s AND type='ORDER_PROFIT' ORDER BY id;", (pid, op_uid))
                if len(led) == 0:
                    fail(f"Paid order {pid} has profit_usdt but no ORDER_PROFIT ledger")
                if len(led) > 1:
                    fail(f"Paid order {pid} has duplicated ORDER_PROFIT ledger rows: {len(led)}")
                ok(f"ORDER_PROFIT ledger exists and not duplicated for order {pid}")
            else:
                ok("No paid orders with profit_usdt found (skipping profit ledger check)")

            # 5) Withdrawals HOLD integrity check
            wrows = fetchall(cur, "SELECT id, user_id, amount_usdt, status FROM withdrawals ORDER BY id DESC LIMIT 20;")
            for wid, wuid, amt, status in wrows:
                wid = int(wid); wuid = int(wuid); amt = Decimal(str(amt)); status = str(status)
                # For SOLICITADA/RESUELTA/RECHAZADA we expect at least one ledger entry memo=withdrawal_id=...
                led = fetchall(cur, "SELECT amount_usdt, type FROM wallet_ledger WHERE memo=%s;", (f"withdrawal_id={wid}",))
                if status in ("SOLICITADA", "RESUELTA"):
                    if not any(t == "WITHDRAWAL_HOLD" and Decimal(str(a)) == -amt for a, t in led):
                        fail(f"Withdrawal {wid} ({status}) missing WITHDRAWAL_HOLD -{amt}")
                if status == "RECHAZADA":
                    if not any(t == "WITHDRAWAL_HOLD_REVERSAL" and Decimal(str(a)) == amt for a, t in led):
                        fail(f"Withdrawal {wid} (RECHAZADA) missing WITHDRAWAL_HOLD_REVERSAL +{amt}")
            ok("Withdrawals ledger integrity looks OK (last 20)")

            # 6) Balance non-negative policy check (optional)
            neg = fetchall(cur, "SELECT user_id, balance_usdt FROM wallets WHERE balance_usdt < 0 LIMIT 5;")
            if neg:
                fail(f"Found negative balances (should be impossible with HOLD atomic): {neg}")
            ok("No negative wallet balances")

    ok("SELF-TEST PASSED")
    return 0

if __name__ == "__main__":
    sys.exit(main())
