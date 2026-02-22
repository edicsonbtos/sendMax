from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler, MessageHandler, filters

ASK = 1

async def entry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("DEBUG: Entré a 🚀 Nuevo envío. Escribe cualquier cosa para simular origen.")
    return ASK

async def receive_any(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(f"DEBUG: Origen recibido => {update.message.text!r}")
    return ConversationHandler.END

def build_debug_conversation() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[MessageHandler(filters.Regex(r"^🚀 Nuevo envío$"), entry)],
        states={ASK: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_any)]},
        fallbacks=[],
        allow_reentry=True,
    )
