from telegram import Update
from telegram.ext import ContextTypes

from src.db.repositories.users_repo import get_user_kyc_by_telegram_id
from src.telegram_app.handlers.menu import show_home


async def menu_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    u = get_user_kyc_by_telegram_id(update.effective_user.id)
    if not u or u.kyc_status != "APPROVED":
        await update.message.reply_text("🧾 Verificación requerida. Usa /start para completar KYC.")
        return
    await show_home(update, context, alias=u.alias)
