from telegram import Update
from telegram.ext import ContextTypes

from src.config.settings import settings


async def alert_test(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Solo admin
    admin_id = int(settings.ADMIN_TELEGRAM_USER_ID) if settings.ADMIN_TELEGRAM_USER_ID else None
    if admin_id is None or update.effective_user.id != admin_id:
        return

    chat_id = int(settings.ALERTS_TELEGRAM_CHAT_ID) if settings.ALERTS_TELEGRAM_CHAT_ID else admin_id
    await context.bot.send_message(chat_id=chat_id, text="✅ Sendmax Alerts: prueba de alerta (test).")
    await update.message.reply_text("Listo ✅ envié una alerta de prueba al canal/grupo de alertas.")
