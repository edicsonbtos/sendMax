import logging

from telegram import Update
from telegram.ext import ContextTypes

from src.config.settings import settings

logger = logging.getLogger(__name__)


def _is_authorized(update: Update) -> bool:
    """
    Router de fotos: SOLO debe actuar en el Grupo de Pagos (PAYMENTS),
    para no interceptar fotos de KYC/ORIGIN_REVIEW u otros chats.
    Admin global también permitido.
    """
    user_id = getattr(update.effective_user, "id", None)
    chat_id = getattr(update.effective_chat, "id", None)

    if settings.is_admin_id(user_id):
        return True

    return str(chat_id) == str(settings.PAYMENTS_TELEGRAM_CHAT_ID)


async def admin_photo_router(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Router central de fotos (aislamiento real).

    Nuevo comportamiento:
    - Si hay órdenes en espera (awaiting_paid_proof=true) en DB, esta foto se usa para cerrar la más antigua.
    - Si no hay órdenes en espera, entonces se usa para retiro (si el flow lo espera).
    """
    if not _is_authorized(update):
        return

    # 1) Prioridad: órdenes en espera en DB (anti-caídas)
    try:
        from src.db.repositories.orders_repo import list_orders_awaiting_paid_proof_by

        pending = list_orders_awaiting_paid_proof_by(update.effective_user.id, limit=1)
        if pending:
            from src.telegram_app.handlers.admin_orders import process_paid_proof_photo
            await process_paid_proof_photo(update, context)
            return
    except Exception as e:
        logger.exception("admin_photo_router: error checking awaiting_paid_proof: %s", e)

    # 2) Fallback: modo legacy por memoria (retiros u otros flujos)
    mode = context.user_data.get("admin_mode")

    if mode == "withdrawal_proof":
        from src.telegram_app.handlers.admin_withdrawals import (
            process_withdrawal_proof_photo,
        )
        await process_withdrawal_proof_photo(update, context)
        return

    # Si llega una foto y no hay contexto, no hacemos nada.
    return
