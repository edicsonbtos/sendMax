from decimal import Decimal

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from src.db.repositories.users_repo import get_user_by_telegram_id
from src.db.repositories.wallet_repo import get_balance
from src.db.repositories.wallet_metrics_repo import get_wallet_metrics


def _fmt8(x: Decimal) -> str:
    try:
        return f"{Decimal(x):.8f}"
    except Exception:
        return str(x)


def _fmt2(x: Decimal) -> str:
    try:
        return f"{Decimal(x):.2f}"
    except Exception:
        return str(x)


async def wallet_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Panel Billetera:
    - Muestra saldo REAL desde wallets.balance_usdt (por users.id).
    - Muestra métricas desde wallet_ledger:
        - Ganancia hoy (ORDER_PROFIT)
        - Ganancia del mes (ORDER_PROFIT)
        - Referidos del mes (SPONSOR_COMMISSION)
    - Botón "Solicitar Retiro" dispara callback withdraw_start (withdrawal_flow).
    """
    user = update.effective_user
    if not user:
        return

    db_user = get_user_by_telegram_id(user.id)
    if not db_user:
        await update.message.reply_text("❌ No estás registrado. Usa /start.")
        return

    balance = get_balance(db_user.id)
    m = get_wallet_metrics(db_user.id)

    text = (
        f"💼 *Billetera*\n\n"
        f"👤 Alias: `{db_user.alias}`\n"
        f"💰 *Saldo disponible:* `{_fmt8(balance)} USDT`\n\n"
        f"📅 *Ganancia hoy:* `{_fmt2(m.profit_today_usdt)} USDT`\n"
        f"🗓️ *Ganancia del mes:* `{_fmt2(m.profit_month_usdt)} USDT`\n"
        f"🤝 *Referidos (mes):* `{_fmt2(m.referrals_month_usdt)} USDT`\n\n"
        f"_Detalle y retiros desde este panel._"
    )

    kb = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("💸 Solicitar retiro", callback_data="withdraw_start")]
        ]
    )

    await update.message.reply_text(text, reply_markup=kb, parse_mode="Markdown")
