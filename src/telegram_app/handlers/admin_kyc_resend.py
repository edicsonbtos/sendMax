from __future__ import annotations

import html
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler

from src.config.settings import settings
from src.db.connection import get_conn


def _is_admin(update: Update) -> bool:
    return settings.is_admin_id(getattr(update.effective_user, "id", None))


def _esc(x) -> str:
    return html.escape("" if x is None else str(x))


async def kyc_resend(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_admin(update):
        return

    if not context.args:
        await update.message.reply_text("Uso: /kyc_resend <user_id>")
        return

    try:
        user_id = int(context.args[0])
    except Exception:
        await update.message.reply_text("user_id inválido.")
        return

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, alias, full_name, phone, address_short,
                       payout_country, payout_method_text,
                       kyc_doc_file_id, kyc_selfie_file_id, kyc_status
                FROM users
                WHERE id=%s
                LIMIT 1;
            """, (user_id,))
            row = cur.fetchone()

    if not row:
        await update.message.reply_text("Usuario no encontrado.")
        return

    (uid, alias, full_name, phone, address_short,
     payout_country, payout_method_text, doc_id, selfie_id, kyc_status) = row

    if not settings.KYC_TELEGRAM_CHAT_ID:
        await update.message.reply_text("KYC_TELEGRAM_CHAT_ID no configurado.")
        return

    from src.telegram_app.flows.kyc_flow import _kyc_review_kb

    text = (
        "🆕 <b>Nuevo ingreso (KYC) [REENVIADO]</b>\n\n"
        f"🆔 <b>User ID:</b> <code>{_esc(uid)}</code>\n"
        f"👤 <b>Alias:</b> <code>{_esc(alias)}</code>\n"
        f"📛 <b>Nombre:</b> {_esc(full_name)}\n"
        f"📞 <b>Tel:</b> {_esc(phone)}\n"
        f"📍 <b>Dir:</b> {_esc(address_short)}\n"
        f"🏳️ <b>País payout:</b> {_esc(payout_country)}\n"
        f"🏦 <b>Método payout:</b>\n<pre>{_esc(payout_method_text)}</pre>\n"
        f"📌 <b>Status:</b> {_esc(kyc_status)}\n"
    )

    await context.bot.send_message(
        chat_id=int(settings.KYC_TELEGRAM_CHAT_ID),
        text=text,
        parse_mode="HTML",
        reply_markup=_kyc_review_kb(int(uid)),
        disable_web_page_preview=True,
    )

    if doc_id:
        await context.bot.send_photo(
            chat_id=int(settings.KYC_TELEGRAM_CHAT_ID),
            photo=str(doc_id),
            caption=f"Documento (Alias: {alias})",
        )
    if selfie_id:
        await context.bot.send_photo(
            chat_id=int(settings.KYC_TELEGRAM_CHAT_ID),
            photo=str(selfie_id),
            caption=f"Selfie con documento (Alias: {alias})",
        )

    await update.message.reply_text(f"✅ Reenviado KYC de user_id={uid} al grupo.")


def build_kyc_resend_handler() -> CommandHandler:
    return CommandHandler("kyc_resend", kyc_resend)
