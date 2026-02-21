from telegram import Update
from telegram.ext import ContextTypes

from src.config.settings import settings


async def chat_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    telegram_id = update.effective_user.id
    admin_id = int(settings.ADMIN_TELEGRAM_USER_ID) if settings.ADMIN_TELEGRAM_USER_ID else None
    if admin_id is None or telegram_id != admin_id:
        return
    await update.message.reply_text(f"chat_id: {update.effective_chat.id}")
