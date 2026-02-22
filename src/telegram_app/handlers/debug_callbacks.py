from __future__ import annotations

import logging

from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

async def debug_any_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    if not q:
        return
    try:
        logger.debug(f"[DEBUG][callback] from_user={q.from_user.id} chat_id={q.message.chat_id} data={q.data}")
        await q.answer()
    except Exception:
        pass
