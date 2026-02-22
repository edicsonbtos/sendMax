from __future__ import annotations

import logging
from decimal import Decimal

from telegram import Update
from telegram.ext import ContextTypes

from src.config.settings import settings
from src.db.repositories.users_repo import ensure_treasury_user
from src.db.repositories.wallet_repo import add_ledger_entry, get_balance

logger = logging.getLogger(__name__)

def _is_admin(update: Update) -> bool:
    return settings.is_admin_id(getattr(update.effective_user, "id", None))

async def adj_treasury(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Comando admin para ajustar saldo de treasury.
    Uso: /adj_treasury <monto> <memo>
    """
    if not _is_admin(update):
        return

    if not context.args or len(context.args) < 1:
        await update.message.reply_text("Uso: `/adj_treasury <monto> <memo>`", parse_mode="Markdown")
        return

    try:
        amount = Decimal(context.args[0])
    except Exception:
        await update.message.reply_text("Monto inválido.")
        return

    memo = " ".join(context.args[1:]) if len(context.args) > 1 else "Ajuste manual"

    try:
        treasury_id = await ensure_treasury_user()
        await add_ledger_entry(
            user_id=treasury_id,
            amount_usdt=amount,
            entry_type="ADJUSTMENT",
            memo=memo
        )

        new_bal = await get_balance(treasury_id)

        await update.message.reply_text(
            f"✅ Ajuste realizado en Treasury.\n"
            f"Monto: `{amount:+.2f} USDT`\n"
            f"Nuevo saldo: `{new_bal:.2f} USDT`",
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.exception("adj_treasury failed")
        await update.message.reply_text(f"❌ Error: {e}")
