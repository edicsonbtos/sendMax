from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes

from src.config.settings import settings
from src.db.repositories.users_repo import get_user_by_telegram_id
from src.telegram_app.ui.keyboards import main_menu_keyboard


def _is_admin(update: Update) -> bool:
    return settings.is_admin_id(getattr(update.effective_user, 'id', None))


def _ref_link(context: ContextTypes.DEFAULT_TYPE, alias: str) -> str:
    bot_username = context.bot.username
    return f"https://t.me/{bot_username}?start=ref_{alias}" if bot_username else "(link no disponible)"


async def enter_referrals(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Referidos v1.1 — Link-only.
    El historial completo (quién se registró, cuánto generó) se consulta
    exclusivamente en el Operator Office (panel web).
    """
    telegram_id = update.effective_user.id
    me = await get_user_by_telegram_id(telegram_id)
    if not me:
        await update.message.reply_text("Primero regístrate con /start.")
        return

    link = _ref_link(context, me.alias)

    await update.message.reply_text(
        "🤝 *Tu Link de Referido*\n\n"
        "Comparte este link con cualquier persona que quiera operar en Sendmax.\n"
        "Cuando se registre y haga envíos, recibirás comisiones automáticamente.\n\n"
        f"`{link}`\n\n"
        "📊 _El historial completo de referidos y ganancias está disponible en tu panel web._",
        parse_mode="Markdown",
        reply_markup=main_menu_keyboard(is_admin=_is_admin(update)),
    )


# Stub para compatibilidad inversa (menu.py lo importa)
async def referrals_router(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """No-op: ya no existe flujo de sub-menú en referidos."""
    context.user_data.pop("ref_mode", None)
    await enter_referrals(update, context)
