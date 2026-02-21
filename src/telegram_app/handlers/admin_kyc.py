from __future__ import annotations

import logging

from telegram import Update
from telegram.ext import ContextTypes

from src.config.settings import settings
from src.db.connection import get_async_conn
from src.db.repositories.users_repo import get_telegram_id_by_user_id, set_kyc_status

logger = logging.getLogger(__name__)


def _is_kyc_chat(update: Update) -> bool:
    chat_id = getattr(update.effective_chat, "id", None)
    return settings.KYC_TELEGRAM_CHAT_ID is not None and str(chat_id) == str(settings.KYC_TELEGRAM_CHAT_ID)


def _is_admin(update: Update) -> bool:
    return settings.is_admin_id(getattr(update.effective_user, "id", None))


async def _reset_kyc_fields(user_id: int) -> None:
    """
    Limpia campos KYC para permitir re-registro.
    """
    sql = """
    UPDATE users
    SET
      kyc_status='PENDING',
      kyc_submitted_at=NULL,
      kyc_reviewed_at=NULL,
      kyc_review_reason=NULL,
      kyc_doc_file_id=NULL,
      kyc_selfie_file_id=NULL,
      full_name=NULL,
      phone=NULL,
      address_short=NULL,
      payout_country=NULL,
      payout_method_text=NULL,
      updated_at=now()
    WHERE id=%s;
    """
    async with get_async_conn() as conn:
        async with conn.cursor() as cur:
            await cur.execute(sql, (int(user_id),))
        await conn.commit()


async def handle_kyc_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    if not q:
        return

    data = q.data or ""
    if not data.startswith("kyc:"):
        return

    if not _is_admin(update) or not _is_kyc_chat(update):
        try:
            await q.answer("🚫 No autorizado.", show_alert=True)
        except Exception:
            pass
        return

    try:
        await q.answer()
    except Exception:
        pass

    parts = data.split(":")
    if len(parts) != 3:
        return

    _, action, user_id_str = parts
    try:
        user_id = int(user_id_str)
    except Exception:
        return

    if action == "approve":
        ok = await set_kyc_status(user_id=user_id, new_status="APPROVED", reason=None)

        if ok:
            tg_id = await get_telegram_id_by_user_id(user_id)
            if tg_id:
                try:
                    await context.bot.send_message(
                        chat_id=int(tg_id),
                        text="✅ Tu verificación fue aprobada. Ya puedes usar el bot.",
                    )
                except Exception:
                    pass

            try:
                await q.message.reply_text(f"✅ Usuario {user_id} aprobado.")
            except Exception:
                pass
        else:
            try:
                await q.message.reply_text("❌ No pude aprobar (user_id no encontrado).")
            except Exception:
                pass
        return

    if action == "reject":
        context.user_data["kyc_reject_user_id"] = user_id
        try:
            await q.message.reply_text("✍️ Escribe el motivo del rechazo (1 mensaje):")
        except Exception:
            pass
        return


async def handle_kyc_reject_reason(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Captura el motivo de rechazo en el grupo KYC.
    """
    if not _is_admin(update) or not _is_kyc_chat(update):
        return

    user_id = context.user_data.get("kyc_reject_user_id")
    if not user_id:
        return

    reason = (update.message.text or "").strip()
    if len(reason) < 3:
        await update.message.reply_text("Motivo muy corto. Intenta de nuevo:")
        return

    await set_kyc_status(user_id=int(user_id), new_status="REJECTED", reason=reason)
    await _reset_kyc_fields(int(user_id))

    tg_id = await get_telegram_id_by_user_id(int(user_id))
    if tg_id:
        try:
            await context.bot.send_message(
                chat_id=int(tg_id),
                text=f"❌ Tu verificación fue rechazada.\nMotivo: {reason}\n\nEscribe /start para registrarte de nuevo.",
            )
        except Exception:
            pass

    context.user_data.pop("kyc_reject_user_id", None)

    await update.message.reply_text(f"✅ Rechazo aplicado al usuario {user_id}.")
