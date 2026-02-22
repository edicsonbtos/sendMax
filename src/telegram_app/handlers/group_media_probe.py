from __future__ import annotations

import logging

from telegram import Update
from telegram.ext import ContextTypes

from src.config.settings import settings

logger = logging.getLogger(__name__)


async def group_media_probe(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Diagnóstico: confirma si el bot está recibiendo fotos/documentos en el grupo de pagos.
    Solo loguea, no responde.
    """
    msg = update.message
    if not msg or not update.effective_chat:
        return

    if not settings.PAYMENTS_TELEGRAM_CHAT_ID:
        return

    if int(update.effective_chat.id) != int(settings.PAYMENTS_TELEGRAM_CHAT_ID):
        return

    has_photo = bool(msg.photo)
    has_doc = bool(msg.document)
    mime = getattr(msg.document, "mime_type", None) if msg.document else None
    mgid = getattr(msg, "media_group_id", None)

    logger.info(
        f"[PROBE][payments_group] chat_id={update.effective_chat.id} "
        f"from={update.effective_user.id if update.effective_user else None} "
        f"has_photo={has_photo} has_doc={has_doc} mime={mime} media_group_id={mgid}"
    )
