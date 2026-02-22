from __future__ import annotations

import asyncio

from telegram import Update
from telegram.ext import CommandHandler, ContextTypes

from src.config.settings import settings
from src.db.connection import get_async_conn
from src.db.repositories.user_contacts_repo import list_all_telegram_ids


def _is_admin(update: Update) -> bool:
    return settings.is_admin_id(getattr(update.effective_user, "id", None))


async def reset_all(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_admin(update):
        return

    await update.message.reply_text(
        "⚠️ RESET TOTAL\n\n"
        "Voy a:\n"
        "1) Avisar a todos: 'Escribe /start'\n"
        "2) Borrar órdenes, retiros, billeteras/ledger\n"
        "3) Borrar usuarios (excepto admin)\n"
        "4) Limpiar sponsor y KYC del admin\n\n"
        "Ejecutando..."
    )

    # 1) Broadcast
    ids = await list_all_telegram_ids()
    msg = "🔄 Sendmax se reinició.\n\nEscribe /start para registrarte de nuevo."
    sent = 0
    failed = 0

    for tid in ids:
        try:
            await context.bot.send_message(chat_id=int(tid), text=msg)
            sent += 1
            await asyncio.sleep(0.05)
        except Exception:
            failed += 1

    # 2) Reset DB
    admin_ids = settings.admin_user_ids
    admin_tg_id = next(iter(admin_ids)) if admin_ids else None

    from src.db.repositories.users_repo import ensure_treasury_user
    treasury_id = await ensure_treasury_user()

    async with get_async_conn() as conn:
        async with conn.cursor() as cur:
            await cur.execute("DELETE FROM wallet_ledger;")
            await cur.execute("DELETE FROM order_trades;")
            await cur.execute("DELETE FROM orders;")
            await cur.execute("DELETE FROM withdrawals;")
            await cur.execute("DELETE FROM user_contacts;")

            # Origen
            for table in ["origin_sweeps", "origin_wallet_closures", "origin_receipts_daily"]:
                try: await cur.execute(f"DELETE FROM {table};")
                except: pass

            await cur.execute("ALTER SEQUENCE orders_public_id_seq RESTART WITH 1;")

            if admin_tg_id:
                # Borrar usuarios excepto admin y treasury
                await cur.execute("DELETE FROM users WHERE telegram_user_id <> %s AND alias <> 'TREASURY' AND id <> %s;", (admin_tg_id, treasury_id))

                # Reset balances
                await cur.execute("UPDATE wallets SET balance_usdt = 0, updated_at = now();")

                await cur.execute(
                    """
                    UPDATE users
                    SET sponsor_id=NULL,
                        full_name=NULL,
                        phone=NULL,
                        address_short=NULL,
                        payout_country=NULL,
                        payout_method_text=NULL,
                        kyc_doc_file_id=NULL,
                        kyc_selfie_file_id=NULL,
                        kyc_status='PENDING',
                        kyc_submitted_at=NULL,
                        kyc_reviewed_at=NULL,
                        kyc_review_reason=NULL,
                        updated_at=now()
                    WHERE telegram_user_id=%s;
                    """,
                    (admin_tg_id,),
                )

        await conn.commit()

    await update.message.reply_text(
        "✅ RESET TOTAL completado.\n\n"
        f"Broadcast: sent={sent} failed={failed}\n"
        "La base quedó limpia (sin borrar tablas ni tasas)."
    )


def build_reset_all_handler() -> CommandHandler:
    return CommandHandler("reset_all", reset_all)
