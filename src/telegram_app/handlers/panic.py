from __future__ import annotations

import logging

from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler

from src.telegram_app.ui.labels import (
    BTN_ADMIN,
    BTN_HELP,
    BTN_NEW_ORDER,
    BTN_PAYMENT_METHODS,
    BTN_RATES,
    BTN_REFERRALS,
    BTN_SUMMARY,
    BTN_WALLET,
)

logger = logging.getLogger(__name__)

# Regex que captura cualquier botón del menú (activos + legacy para safety)
# Los legacy (Wallet, Resumen, Ayuda) se mantienen para interceptar clientes
# con el teclado cacheado en versiones anteriores del bot.
MENU_BUTTONS_REGEX = (
    rf"^({BTN_RATES}|{BTN_NEW_ORDER}|{BTN_REFERRALS}|{BTN_PAYMENT_METHODS}"
    rf"|{BTN_ADMIN}|{BTN_WALLET}|{BTN_SUMMARY}|{BTN_HELP})$"
)

async def panic_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Limpia el user_data y termina la conversación actual.
    Se usa como fallback universal para /cancel y botones de menú.
    """
    user_id = update.effective_user.id
    logger.info(f"Panic handler activado para usuario {user_id}")

    # Limpieza total de estado
    context.user_data.clear()

    if update.message and update.message.text == "/cancel":
        await update.message.reply_text("❌ Operación cancelada. Estado reiniciado.")

    # Retornamos END para romper la FSM del ConversationHandler
    return ConversationHandler.END
