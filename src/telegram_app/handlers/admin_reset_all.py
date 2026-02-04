from __future__ import annotations

import asyncio
import psycopg
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler

from src.config.settings import settings
from src.db.repositories.user_contacts_repo import list_all_telegram_ids


ADMIN_TG_ID = 7518903082


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
    ids = list_all_telegram_ids()
    msg = "🔄 Sendmax se reinició.\n\nEscribe /start para registrarte de nuevo."
    sent = 0
    failed = 0

    for tid in ids:
        try:
            await context.bot.send_message(chat_id=int(tid), text=msg)
            sent += 1
            await asyncio.sleep(0.05)  # micro-throttle
        except Exception:
            failed += 1

    # 2) Reset DB (sin borrar tablas)
    with psycopg.connect(settings.DATABASE_URL) as conn:
        with conn.cursor() as cur:
            # withdrawals dependen de wallets en lógica, pero por FK pueden estar independientes:
            cur.execute("DELETE FROM withdrawals;")

            # ledger primero, luego wallets
            cur.execute("DELETE FROM wallet_ledger;")
            cur.execute("DELETE FROM wallets;")

            # orders
            cur.execute("DELETE FROM orders;")

            # Reiniciar secuencia public_id (para volver a empezar desde 1)
            cur.execute("ALTER SEQUENCE orders_public_id_seq RESTART WITH 1;")

            # users: borrar todos menos admin
            cur.execute("DELETE FROM users WHERE telegram_user_id <> %s;", (ADMIN_TG_ID,))

            # limpiar admin: sponsor + kyc + payout
            cur.execute(
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
                (ADMIN_TG_ID,),
            )

        conn.commit()

    await update.message.reply_text(
        "✅ RESET TOTAL completado.\n\n"
        f"Broadcast: sent={sent} failed={failed}\n"
        "La base quedó limpia (sin borrar tablas ni tasas)."
    )


def build_reset_all_handler() -> CommandHandler:
    return CommandHandler("reset_all", reset_all)
