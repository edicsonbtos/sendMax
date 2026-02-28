"""
wallet.py v1.1 — Web-redirect only.
El balance, ganancias y retiros se gestionan exclusivamente en el User Office (web).
Este handler redirige al usuario a la web para no bloquear el bot con queries pesadas.
"""
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from src.config.settings import settings
from src.db.repositories.users_repo import get_user_by_telegram_id


async def wallet_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Stub de billetera — redirige al panel web.
    Mantenido para retrocompatibilidad; ya no se muestra en el menú principal.
    """
    db_user = await get_user_by_telegram_id(update.effective_user.id) if update.effective_user else None
    alias = db_user.alias if db_user else "tu cuenta"

    backoffice_url = getattr(settings, "BACKOFFICE_URL", "https://office.sendmax.app")

    kb = InlineKeyboardMarkup([[
        InlineKeyboardButton("💼 Abrir User Office", url=backoffice_url)
    ]])

    await update.message.reply_text(
        f"💼 *Billetera de {alias}*\n\n"
        "Tu saldo, ganancias, historial de retiros y desglose de referidos "
        "están disponibles en tu panel web con información en tiempo real.\n\n"
        "👇 Ábrelo con el botón:",
        reply_markup=kb,
        parse_mode="Markdown",
    )
