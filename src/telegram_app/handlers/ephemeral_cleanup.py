"""
Limpieza de mensajes efímeros.

Objetivo:
- Mantener el chat limpio sin romper módulos.
- Borrar (best effort) el último mensaje de "Métodos de pago" SOLO cuando el usuario
  sale del módulo (no cuando está seleccionando un país).
"""

from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes
from src.telegram_app.ui.labels import (
    BTN_RATES,
    BTN_WALLET,
    BTN_NEW_ORDER,
    BTN_SUMMARY,
    BTN_REFERRALS,
    BTN_PAYMENT_METHODS,
    BTN_HELP,
    BTN_ADMIN,
)

# Botones del menú principal (si el usuario presiona cualquiera, consideramos que "salió" del módulo)
MENU_BUTTONS = {
    BTN_RATES,
    BTN_WALLET,
    BTN_NEW_ORDER,
    BTN_SUMMARY,
    BTN_REFERRALS,
    BTN_PAYMENT_METHODS,
    BTN_HELP,
    BTN_ADMIN,
}

BTN_BACK = "⬅️ Volver"


async def _best_effort_delete(update: Update, context: ContextTypes.DEFAULT_TYPE, message_id: int) -> None:
    try:
        await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=message_id)
    except Exception:
        pass


async def track_message(message, context: ContextTypes.DEFAULT_TYPE):
    """Registrar un mensaje del bot para futura limpieza."""
    if not message:
        return
    if "bot_messages" not in context.user_data:
        context.user_data["bot_messages"] = []

    # Evitar duplicados
    if message.message_id not in context.user_data["bot_messages"]:
        context.user_data["bot_messages"].append(message.message_id)


async def cleanup_bot_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Borrar todos los mensajes previos del bot en este chat."""
    messages = context.user_data.get("bot_messages", [])
    chat_id = update.effective_chat.id

    for msg_id in messages:
        try:
            await context.bot.delete_message(chat_id=chat_id, message_id=msg_id)
        except Exception:
            pass  # Mensaje ya borrado o no accesible

    context.user_data["bot_messages"] = []


async def cleanup_ephemeral(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Corre antes del menu_router.

    Regla:
    - Si el usuario presiona un botón del menú principal, borramos todos los mensajes trackeados.
    - Maneja también la salida de pm_mode heredada.
    """
    if not update.message or not update.message.text:
        return

    text = (update.message.text or "").strip()

    # Si presiona un botón del menú, limpieza total
    if text in MENU_BUTTONS:
        await cleanup_bot_messages(update, context)
        # Salir de modos específicos
        context.user_data.pop("pm_mode", None)
        context.user_data.pop("pm_last_message_id", None)
        return

    # Lógica específica de pm_mode para el botón "Volver"
    if context.user_data.get("pm_mode") and text == BTN_BACK:
        await cleanup_bot_messages(update, context)
        context.user_data.pop("pm_mode", None)
        context.user_data.pop("pm_last_message_id", None)