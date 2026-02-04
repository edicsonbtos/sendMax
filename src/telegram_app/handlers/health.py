from telegram import Update
from telegram.ext import ContextTypes

from src.db.connection import ping_db
from src.config.settings import settings

async def health(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    telegram_id = update.effective_user.id

    if settings.ADMIN_TELEGRAM_USER_ID and telegram_id != settings.ADMIN_TELEGRAM_USER_ID:
        await update.message.reply_text("No autorizado.")
        return

    db_ok = ping_db()
    await update.message.reply_text(
        f"ENV: {settings.ENV}\nDB: {'OK' if db_ok else 'FAIL'}"
    )