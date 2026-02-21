from __future__ import annotations

import logging
from telegram import Update
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.request import HTTPXRequest

from src.config.settings import settings

from src.telegram_app.flows.kyc_flow import build_kyc_conversation
from src.telegram_app.flows.new_order_flow import build_new_order_conversation
from src.telegram_app.flows.withdrawal_flow import build_withdrawal_conversation_handler

from src.telegram_app.handlers.admin_rates import rates_now
from src.telegram_app.handlers.admin_chatid import chat_id
from src.telegram_app.handlers.admin_alert_test import alert_test
from src.telegram_app.handlers.admin_orders import (
    admin_orders,
    handle_admin_order_action,
    handle_cancel_reason_text,
)
from src.telegram_app.handlers.admin_withdrawals import (
    build_admin_withdrawals_conversation_handler,
    admin_withdrawals_callbacks,
)
from src.telegram_app.handlers.admin_media_router import admin_photo_router
from src.telegram_app.handlers.admin_awaiting_paid import admin_awaiting_paid
from src.telegram_app.handlers.admin_kyc import handle_kyc_callback, handle_kyc_reject_reason
from src.telegram_app.handlers.admin_reset_all import build_reset_all_handler
from src.telegram_app.handlers.admin_kyc_resend import build_kyc_resend_handler
from src.telegram_app.handlers.admin_set_sponsor import build_set_sponsor_handler

from src.telegram_app.handlers.rates_more import handle_rates_more
from src.telegram_app.handlers.summary import build_summary_callback_handler
from src.telegram_app.handlers.menu import menu_router
from src.telegram_app.handlers.panic import panic_handler

logger = logging.getLogger(__name__)


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.exception("UNHANDLED ERROR: %s", context.error)


# --- SNIFFER DEBUG (solo si FLOW_DEBUG=1) ---
async def universal_sniffer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message:
        user = getattr(update.effective_user, "first_name", "")
        chat = getattr(update.effective_chat, "id", None)
        tipo = "TEXTO" if update.message.text else "OTRO (Foto/Doc)"
        if update.message.text:
            print("   [SNIFFER_TEXT]=", repr(update.message.text))
        print(f"\n[SNIFFER] Chat: {chat} | User: {user} | Tipo: {tipo}")
        if update.message.photo:
            print("   [SNIFFER] FOTO")
# -------------------------------------------


def build_bot() -> Application:
    request = HTTPXRequest(connect_timeout=20.0, read_timeout=30.0, write_timeout=30.0, pool_timeout=30.0)
    app = Application.builder().token(settings.TELEGRAM_BOT_TOKEN).request(request).build()

    app.add_error_handler(error_handler)

    if int(getattr(settings, "FLOW_DEBUG", 0) or 0) == 1:
        app.add_handler(MessageHandler(filters.ALL, universal_sniffer), group=-1)

    # /start = KYC. /cancel = Pánico.
    app.add_handler(CommandHandler("cancel", panic_handler), group=0)
    app.add_handler(build_kyc_conversation(), group=0)

    # Flujos operativos
    app.add_handler(build_new_order_conversation(), group=1)
    app.add_handler(build_withdrawal_conversation_handler(), group=1)

    # Comandos admin
    app.add_handler(CommandHandler("rates_now", rates_now), group=2)
    app.add_handler(CommandHandler("chat_id", chat_id), group=2)
    app.add_handler(CommandHandler("alert_test", alert_test), group=2)
    app.add_handler(CommandHandler("admin_orders", admin_orders), group=2)
    app.add_handler(CommandHandler("awaiting_paid", admin_awaiting_paid), group=2)
    app.add_handler(build_admin_withdrawals_conversation_handler(), group=2)
    app.add_handler(build_reset_all_handler(), group=2)
    app.add_handler(build_kyc_resend_handler(), group=2)
    app.add_handler(build_set_sponsor_handler(), group=2)

    # Callbacks
    app.add_handler(CallbackQueryHandler(handle_rates_more, pattern=r"^rates_more:"), group=4)
    app.add_handler(CallbackQueryHandler(handle_admin_order_action, pattern=r"^ord:"), group=4)
    app.add_handler(CallbackQueryHandler(handle_kyc_callback, pattern=r"^kyc:"), group=4)
    app.add_handler(build_summary_callback_handler(), group=4)

    for h in admin_withdrawals_callbacks:
        app.add_handler(h, group=4)

    # Fotos admin
    app.add_handler(MessageHandler(filters.PHOTO, admin_photo_router), group=5)

    # Texto admin (cancel reason orden + motivo rechazo KYC)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_cancel_reason_text), group=5)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_kyc_reject_reason), group=5)

    # Menú (solo APPROVED)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, menu_router), group=6)

    logger.info("Bot listo: KYC + órdenes + retiros + admin")
    return app
