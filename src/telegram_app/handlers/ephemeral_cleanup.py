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

# Botones del menú principal (si el usuario presiona cualquiera, consideramos que "salió" del módulo)
MENU_BUTTONS = {
    "📈 Tasas",
    "💼 Billetera",
    "🚀 Nuevo envío",
    "📊 Resumen",
    "👥 Referidos",
    "💸 Retirar",
    "🏦 Métodos de pago",
    "🆘 Ayuda",
}

BTN_BACK = "⬅️ Volver"


async def _best_effort_delete(update: Update, context: ContextTypes.DEFAULT_TYPE, message_id: int) -> None:
    try:
        await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=message_id)
    except Exception:
        pass


async def cleanup_ephemeral(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Corre antes del menu_router.

    Regla:
    - Si NO estamos en pm_mode, no hacemos nada.
    - Si estamos en pm_mode:
        - Si el usuario presiona un botón del menú principal o "Volver", entonces:
            - borramos el último mensaje de métodos (si existe)
            - salimos de pm_mode
        - Si el usuario presiona un país (ej: "🇻🇪 Venezuela"), NO hacemos nada (dejamos que lo maneje el módulo).
    """
    if not update.message or not update.message.text:
        return

    text = (update.message.text or "").strip()

    if not context.user_data.get("pm_mode"):
        return

    # Si está navegando dentro del módulo (seleccionando país), NO limpiamos ni salimos
    if text not in MENU_BUTTONS and text != BTN_BACK:
        return

    # Si presionó "Volver" o cambió a otro botón del menú, limpiamos y salimos
    mid = context.user_data.get("pm_last_message_id")
    if mid:
        await _best_effort_delete(update, context, int(mid))
        context.user_data.pop("pm_last_message_id", None)

    context.user_data.pop("pm_mode", None)