from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes

from src.config.settings import settings
from src.db.repositories.orders_repo import list_orders_awaiting_paid_proof


def _is_authorized(update: Update) -> bool:
    user_id = getattr(update.effective_user, "id", None)
    chat_id = getattr(update.effective_chat, "id", None)

    if settings.is_admin_id(user_id):
        return True

    if str(chat_id) == str(settings.PAYMENTS_TELEGRAM_CHAT_ID):
        return True

    return False


async def admin_awaiting_paid(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Lista órdenes que están en estado "awaiting_paid_proof=true".
    Útil si el bot se reinicia o si hay más de una orden esperando comprobante.
    """
    if not _is_authorized(update):
        return

    orders = list_orders_awaiting_paid_proof(limit=15)
    if not orders:
        await update.message.reply_text("✅ No hay órdenes en espera de comprobante.")
        return

    lines = ["📸 <b>Órdenes en espera de comprobante</b>\n"]
    for o in orders:
        lines.append(
            f"🆔 <b>#{o.public_id}</b> — {o.origin_country} -> {o.dest_country} — "
            f"Recibe: {o.amount_origin} — Payout: {o.payout_dest:,.2f}"
        )

    lines.append("\nPara cerrar una, envía la foto en este chat (se tomará la más antigua primero).")

    await update.message.reply_text("\n".join(lines), parse_mode="HTML")
