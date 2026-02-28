"""
wallet.py v1.2 — Billetera Inteligente (Balance-Only).
Muestra únicamente el saldo USDT disponible + botón web para historial detallado.
Sin carga de métricas pesadas en el bot.
"""
from decimal import Decimal

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from src.config.settings import settings
from src.db.repositories.users_repo import get_user_by_telegram_id
from src.db.repositories.wallet_repo import get_balance
from src.telegram_app.handlers.ephemeral_cleanup import track_message


def _fmt(x: Decimal) -> str:
    try:
        return f"{Decimal(x):.2f}"
    except Exception:
        return str(x)


async def wallet_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Panel Billetera ligero:
    - Consulta solo get_balance() (una query simple sobre wallets).
    - Botón URL al User Office para movimientos y retiros.
    """
    if not update.effective_user:
        return

    db_user = await get_user_by_telegram_id(update.effective_user.id)
    if not db_user:
        await update.message.reply_text("❌ No estás registrado. Usa /start.")
        return

    balance = await get_balance(db_user.id)
    backoffice_url = getattr(settings, "BACKOFFICE_URL", "https://office.sendmax.app").rstrip('/')
    target_url = f"{backoffice_url}/operator-office"

    kb = InlineKeyboardMarkup([[
        InlineKeyboardButton("🌐 Ver Movimientos en la Web", url=target_url)
    ]])

    msg = await update.message.reply_text(
        f"💼 *Billetera* — @{db_user.alias}\n\n"
        f"💰 Saldo disponible: `{_fmt(balance)} USDT`\n\n"
        "_Historial de ganancias, referidos y retiros en tu panel web._",
        reply_markup=kb,
        parse_mode="Markdown",
    )
    await track_message(msg, context)
