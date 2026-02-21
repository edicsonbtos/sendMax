from __future__ import annotations

import asyncio
import logging
import re

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from src.config.settings import settings
from src.db.repositories.user_contacts_repo import touch_contact
from src.db.repositories.users_repo import (
    check_email_exists,
    create_user,
    get_user_by_alias,
    get_user_by_telegram_id,
    get_user_kyc_by_telegram_id,
    submit_kyc,
    update_kyc_draft,
)
from src.telegram_app.handlers.menu import show_home
from src.telegram_app.handlers.panic import MENU_BUTTONS_REGEX, panic_handler
from src.utils.crypto import get_password_hash

logger = logging.getLogger(__name__)

# Estados
ASK_ALIAS = 1
ASK_SPONSOR = 2
ASK_FULL_NAME = 3
ASK_PHONE = 4
ASK_ADDRESS = 5
ASK_EMAIL = 6
ASK_PASSWORD = 7
ASK_PAYOUT_COUNTRY = 8
ASK_PAYOUT_METHOD = 9
ASK_DOC_PHOTO = 10
ASK_SELFIE_PHOTO = 11

ALIAS_REGEX = re.compile(r"^[a-zA-Z0-9_]{3,15}$")
EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")


def parse_sponsor_alias_from_start_args(context: ContextTypes.DEFAULT_TYPE) -> str | None:
    if not getattr(context, "args", None):
        return None
    raw = (context.args[0] or "").strip()
    if raw.startswith("ref_") and len(raw) > 4:
        return raw.replace("ref_", "", 1).strip()
    return None


def _kyc_review_kb(user_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [[
            InlineKeyboardButton("✅ Aprobar", callback_data=f"kyc:approve:{user_id}"),
            InlineKeyboardButton("❌ Rechazar", callback_data=f"kyc:reject:{user_id}"),
        ]]
    )


def _next_kyc_step(ukyc) -> int:
    if not (ukyc.full_name or "").strip():
        return ASK_FULL_NAME
    if not (ukyc.phone or "").strip():
        return ASK_PHONE
    if not (ukyc.address_short or "").strip():
        return ASK_ADDRESS
    if not (ukyc.email or "").strip():
        return ASK_EMAIL
    if not (ukyc.hashed_password or "").strip():
        return ASK_PASSWORD
    if not (ukyc.payout_country or "").strip():
        return ASK_PAYOUT_COUNTRY
    if not (ukyc.payout_method_text or "").strip():
        return ASK_PAYOUT_METHOD
    if not (ukyc.kyc_doc_file_id or "").strip():
        return ASK_DOC_PHOTO
    if not (ukyc.kyc_selfie_file_id or "").strip():
        return ASK_SELFIE_PHOTO
    return ASK_SELFIE_PHOTO


async def _prompt_for_step(update: Update, step: int) -> None:
    if step == ASK_FULL_NAME:
        await update.message.reply_text("1/8) 👤 Nombre y apellido completo:")
    elif step == ASK_PHONE:
        await update.message.reply_text("2/8) 📞 Teléfono (con código país, ej: +58424...):")
    elif step == ASK_ADDRESS:
        await update.message.reply_text("3/8) 📍 Dirección (ciudad/estado):")
    elif step == ASK_EMAIL:
        await update.message.reply_text(
            "4/8) 📧 Email para acceso web\n\n"
            "Este email lo usarás para iniciar sesión en el panel web.\n"
            "Ejemplo: tu_nombre@gmail.com"
        )
    elif step == ASK_PASSWORD:
        await update.message.reply_text(
            "5/8) 🔐 Contraseña para acceso web\n\n"
            "Crea una contraseña segura (mínimo 8 caracteres).\n"
            "⚠️ No la compartas con nadie.\n\n"
            "Escribe tu contraseña ahora:"
        )
    elif step == ASK_PAYOUT_COUNTRY:
        await update.message.reply_text("6/8) 🏳️ País donde cobrarás ganancias (ej: VENEZUELA):")
    elif step == ASK_PAYOUT_METHOD:
        await update.message.reply_text("7/8) 🏦 Método de pago (1 mensaje con todos los datos):")
    elif step == ASK_DOC_PHOTO:
        await update.message.reply_text("8/8) 🪪 Foto del documento de identidad (1 sola foto):")
    elif step == ASK_SELFIE_PHOTO:
        await update.message.reply_text("Último paso 😊\n🤳 Selfie sosteniendo el documento a un costado:")


async def start_kyc(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    print(f"\n--- HANDLER /start triggered for user {update.effective_user.id} ---")
    logger.info(f"start_kyc called for user_id={update.effective_user.id}")

    try:
        tg_id = int(update.effective_user.id)
        await touch_contact(tg_id)

        # FIX H-01: capturar sponsor aqui donde context.args existe
        sponsor_alias = parse_sponsor_alias_from_start_args(context)
        if sponsor_alias:
            context.user_data["sponsor_from_link"] = sponsor_alias

        ukyc = await get_user_kyc_by_telegram_id(tg_id)
        if ukyc:
            if ukyc.kyc_status == "APPROVED":
                await show_home(update, context, alias=ukyc.alias)
                return ConversationHandler.END

            if ukyc.kyc_status == "SUBMITTED":
                await update.message.reply_text("📨 Tu verificación ya fue enviada. ⏳ Está en revisión.")
                return ConversationHandler.END

            if ukyc.kyc_status == "REJECTED":
                reason = (ukyc.kyc_review_reason or "").strip()
                msg = "❌ Tu verificación fue rechazada."
                if reason:
                    msg += f"\nMotivo: {reason}"
                msg += "\n\nVamos a enviarla nuevamente."
                await update.message.reply_text(msg)
                ukyc = await get_user_kyc_by_telegram_id(tg_id)

            await update.message.reply_text("🧾 Verificación requerida. Vamos paso a paso.")
            step = _next_kyc_step(ukyc)
            await _prompt_for_step(update, step)
            return step

        await update.message.reply_text(
            "👋 Bienvenido a Sendmax.\n\n"
            "Crea tu alias (nombre de operador):\n"
            "• 3 a 15 caracteres\n"
            "• Solo letras, números y _\n"
            "Ejemplo: rigo_01\n\n"
            "Escribe tu alias ahora:"
        )
        return ASK_ALIAS
    except Exception as e:
        print(f"CRITICAL ERROR in start_kyc: {e}")
        logger.error(f"Structural error in start_kyc: {e}", exc_info=True)
        await update.message.reply_text("❌ Hubo un error al iniciar el proceso. Por favor, intenta de nuevo en unos momentos.")
        return ConversationHandler.END


async def receive_alias(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    alias = (update.message.text or "").strip()

    if not ALIAS_REGEX.match(alias):
        await update.message.reply_text("❌ Alias inválido. Debe tener 3-15 caracteres (letras, números, _). Intenta de nuevo:")
        return ASK_ALIAS

    if await get_user_by_alias(alias):
        await update.message.reply_text("❌ Ese alias ya existe. Escribe otro:")
        return ASK_ALIAS

    context.user_data["pending_alias"] = alias

    # FIX H-01: leer sponsor desde user_data (guardado en start_kyc)
    sponsor_alias = context.user_data.pop("sponsor_from_link", None)
    if sponsor_alias:
        sponsor = await get_user_by_alias(sponsor_alias)
        sponsor_id = sponsor.id if sponsor else None

        # FIX M-01: try/except en create_user
        try:
            await create_user(
                telegram_user_id=int(update.effective_user.id),
                alias=alias,
                sponsor_id=sponsor_id,
            )
        except Exception:
            logger.exception("create_user failed (deep-link) alias=%s tg=%s", alias, update.effective_user.id)
            await update.message.reply_text(
                "❌ No se pudo crear tu cuenta. El alias puede estar tomado.\n"
                "Intenta con otro alias:"
            )
            return ASK_ALIAS

        context.user_data.pop("pending_alias", None)
        await update.message.reply_text("✅ Alias creado. Ahora vamos con tu verificación 👇")
        await _prompt_for_step(update, ASK_FULL_NAME)
        return ASK_FULL_NAME

    await update.message.reply_text(
        "🤝 Padrino (opcional)\n\n"
        "Si tienes padrino, escribe su alias.\n"
        "Si NO tienes padrino, escribe: 2\n\n"
        "Escribe ahora (alias o 2):"
    )
    return ASK_SPONSOR


async def receive_sponsor(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    raw = (update.message.text or "").strip()
    alias = context.user_data.get("pending_alias")
    if not alias:
        await update.message.reply_text("❌ Sesión expirada. Escribe /start de nuevo.")
        return ConversationHandler.END

    sponsor_id = None
    if raw == "2":
        sponsor_id = None
    else:
        sponsor = await get_user_by_alias(raw)
        if not sponsor:
            await update.message.reply_text("❌ No encontré ese padrino. Intenta de nuevo o escribe 2:")
            return ASK_SPONSOR
        sponsor_id = sponsor.id

    # FIX M-01: try/except en create_user
    try:
        await create_user(
            telegram_user_id=int(update.effective_user.id),
            alias=alias,
            sponsor_id=sponsor_id,
        )
    except Exception:
        logger.exception("create_user failed (sponsor) alias=%s tg=%s", alias, update.effective_user.id)
        await update.message.reply_text("❌ Error al crear tu cuenta. Escribe /start para reiniciar.")
        return ConversationHandler.END

    context.user_data.pop("pending_alias", None)
    await update.message.reply_text("✅ Alias creado. Ahora vamos con tu verificación 👇")
    await _prompt_for_step(update, ASK_FULL_NAME)
    return ASK_FULL_NAME


async def receive_full_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    v = (update.message.text or "").strip()
    if len(v) < 5:
        await update.message.reply_text("❌ Nombre muy corto. Intenta de nuevo:")
        return ASK_FULL_NAME
    await update_kyc_draft(telegram_user_id=int(update.effective_user.id), full_name=v)
    await _prompt_for_step(update, ASK_PHONE)
    return ASK_PHONE


async def receive_phone(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    v = (update.message.text or "").strip()
    if len(v) < 7:
        await update.message.reply_text("❌ Teléfono inválido. Intenta de nuevo:")
        return ASK_PHONE
    await update_kyc_draft(telegram_user_id=int(update.effective_user.id), phone=v)
    await _prompt_for_step(update, ASK_ADDRESS)
    return ASK_ADDRESS


async def receive_address(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    v = (update.message.text or "").strip()
    if len(v) < 4:
        await update.message.reply_text("❌ Dirección muy corta. Intenta de nuevo:")
        return ASK_ADDRESS
    await update_kyc_draft(telegram_user_id=int(update.effective_user.id), address_short=v)
    await _prompt_for_step(update, ASK_EMAIL)
    return ASK_EMAIL


async def receive_email(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    v = (update.message.text or "").strip().lower()

    if not EMAIL_REGEX.match(v):
        await update.message.reply_text("❌ Email inválido. Debe ser algo como: nombre@gmail.com\n\nIntenta de nuevo:")
        return ASK_EMAIL

    if await check_email_exists(v):
        await update.message.reply_text("❌ Este email ya está registrado. Usa otro email:")
        return ASK_EMAIL

    await update_kyc_draft(telegram_user_id=int(update.effective_user.id), email=v)
    await _prompt_for_step(update, ASK_PASSWORD)
    return ASK_PASSWORD


async def receive_password(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    v = (update.message.text or "").strip()

    if len(v) < 8:
        await update.message.reply_text("❌ Contraseña muy corta. Debe tener mínimo 8 caracteres.\n\nIntenta de nuevo:")
        return ASK_PASSWORD

    hashed = get_password_hash(v)
    await update_kyc_draft(telegram_user_id=int(update.effective_user.id), hashed_password=hashed)

    try:
        await update.message.delete()
    except Exception:
        pass

    await update.effective_chat.send_message("✅ Contraseña guardada de forma segura.")
    await _prompt_for_step(update, ASK_PAYOUT_COUNTRY)
    return ASK_PAYOUT_COUNTRY


async def receive_payout_country(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    v = (update.message.text or "").strip().upper()
    if len(v) < 3:
        await update.message.reply_text("❌ País inválido. Intenta de nuevo:")
        return ASK_PAYOUT_COUNTRY
    await update_kyc_draft(telegram_user_id=int(update.effective_user.id), payout_country=v)
    await _prompt_for_step(update, ASK_PAYOUT_METHOD)
    return ASK_PAYOUT_METHOD


async def receive_payout_method(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    v = (update.message.text or "").strip()
    if len(v) < 8:
        await update.message.reply_text("❌ Método muy corto. Intenta de nuevo:")
        return ASK_PAYOUT_METHOD
    await update_kyc_draft(telegram_user_id=int(update.effective_user.id), payout_method_text=v)
    await _prompt_for_step(update, ASK_DOC_PHOTO)
    return ASK_DOC_PHOTO


async def receive_doc_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not update.message.photo:
        await update.message.reply_text("❌ Necesito una foto. Intenta de nuevo:")
        return ASK_DOC_PHOTO
    doc_id = update.message.photo[-1].file_id
    await update_kyc_draft(telegram_user_id=int(update.effective_user.id), kyc_doc_file_id=doc_id)
    await _prompt_for_step(update, ASK_SELFIE_PHOTO)
    return ASK_SELFIE_PHOTO


async def receive_selfie_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not update.message.photo:
        await update.message.reply_text("❌ Necesito una foto. Intenta de nuevo:")
        return ASK_SELFIE_PHOTO

    tg_id = int(update.effective_user.id)
    selfie_id = update.message.photo[-1].file_id
    await update_kyc_draft(telegram_user_id=tg_id, kyc_selfie_file_id=selfie_id)

    ukyc = await get_user_kyc_by_telegram_id(tg_id)
    if not ukyc:
        await update.message.reply_text("❌ Error. Escribe /start de nuevo.")
        return ConversationHandler.END

    # FIX M-02: validar campos completos antes de submit
    required_fields = {
        "full_name": ukyc.full_name,
        "phone": ukyc.phone,
        "address_short": ukyc.address_short,
        "email": ukyc.email,
        "hashed_password": ukyc.hashed_password,
        "payout_country": ukyc.payout_country,
        "payout_method_text": ukyc.payout_method_text,
        "kyc_doc_file_id": ukyc.kyc_doc_file_id,
        "kyc_selfie_file_id": ukyc.kyc_selfie_file_id,
    }
    missing = [k for k, v in required_fields.items() if not (v or "").strip()]
    if missing:
        logger.warning("KYC submit aborted — missing fields %s for tg_id=%s", missing, tg_id)
        step = _next_kyc_step(ukyc)
        await update.message.reply_text("⚠️ Faltan datos en tu verificación. Vamos a completarlos:")
        await _prompt_for_step(update, step)
        return step

    # FIX M-02: pasar valores directos sin str() + try/except
    try:
        ok = await asyncio.wait_for(
            submit_kyc(
                telegram_user_id=tg_id,
                full_name=ukyc.full_name,
                phone=ukyc.phone,
                address_short=ukyc.address_short,
                email=ukyc.email,
                hashed_password=ukyc.hashed_password,
                payout_country=ukyc.payout_country,
                payout_method_text=ukyc.payout_method_text,
                kyc_doc_file_id=ukyc.kyc_doc_file_id,
                kyc_selfie_file_id=ukyc.kyc_selfie_file_id,
            ),
            timeout=5.0
        )
    except asyncio.TimeoutError:
        await update.message.reply_text("⏳ Timeout enviando verificación. Reintenta.")
        return ASK_SELFIE_PHOTO
    except Exception:
        logger.exception("submit_kyc DB error for tg_id=%s", tg_id)
        await update.message.reply_text("❌ Error al enviar verificación. Intenta /start de nuevo.")
        return ConversationHandler.END

    if not ok:
        await update.message.reply_text("❌ No pude enviar tu verificación. Intenta /start.")
        return ConversationHandler.END

    if settings.KYC_TELEGRAM_CHAT_ID:
        try:
            db_user = await get_user_by_telegram_id(tg_id)
            if not db_user:
                raise ValueError(f"User not found after submit for tg_id={tg_id}")
            text = (
                "🆕 Nuevo ingreso (KYC)\n\n"
                f"User ID: {db_user.id}\n"
                f"Alias: {db_user.alias}\n"
                f"Nombre: {ukyc.full_name}\n"
                f"Email: {ukyc.email}\n"
                f"Tel: {ukyc.phone}\n"
                f"Dir: {ukyc.address_short}\n"
                f"País payout: {ukyc.payout_country}\n"
                f"Método payout:\n{ukyc.payout_method_text}\n"
            )
            await context.bot.send_message(
                chat_id=int(settings.KYC_TELEGRAM_CHAT_ID),
                text=text,
                reply_markup=_kyc_review_kb(int(db_user.id)),
            )
            await context.bot.send_photo(chat_id=int(settings.KYC_TELEGRAM_CHAT_ID), photo=ukyc.kyc_doc_file_id)
            await context.bot.send_photo(chat_id=int(settings.KYC_TELEGRAM_CHAT_ID), photo=ukyc.kyc_selfie_file_id)
        except Exception as e:
            logger.exception("KYC send failed: %s", e)

    await update.message.reply_text(
        "✅ Verificación enviada correctamente.\n\n"
        "📧 Recibirás notificación cuando tu cuenta sea aprobada.\n"
        "⏳ Un administrador revisará tu solicitud pronto."
    )
    return ConversationHandler.END


async def _photo_state_text_fallback_doc(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        "⚠️ Necesito una foto, no texto.\n"
        "📸 Envía la foto de tu documento de identidad como imagen (no como archivo)."
    )
    return ASK_DOC_PHOTO


async def _photo_state_text_fallback_selfie(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        "⚠️ Necesito una foto, no texto.\n"
        "🤳 Envía tu selfie sosteniendo el documento como imagen."
    )
    return ASK_SELFIE_PHOTO


async def cancel_kyc(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Proceso cancelado. Usa /start para comenzar de nuevo.")
    return ConversationHandler.END


def build_kyc_conversation() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[CommandHandler("start", start_kyc), CommandHandler("kyc", start_kyc)],
        states={
            ASK_ALIAS: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_alias)],
            ASK_SPONSOR: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_sponsor)],
            ASK_FULL_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_full_name)],
            ASK_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_phone)],
            ASK_ADDRESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_address)],
            ASK_EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_email)],
            ASK_PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_password)],
            ASK_PAYOUT_COUNTRY: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_payout_country)],
            ASK_PAYOUT_METHOD: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_payout_method)],
            ASK_DOC_PHOTO: [
                MessageHandler(filters.PHOTO, receive_doc_photo),
                MessageHandler(filters.TEXT & ~filters.COMMAND, _photo_state_text_fallback_doc),
            ],
            ASK_SELFIE_PHOTO: [
                MessageHandler(filters.PHOTO, receive_selfie_photo),
                MessageHandler(filters.TEXT & ~filters.COMMAND, _photo_state_text_fallback_selfie),
            ],
        },
        fallbacks=[
            CommandHandler(["cancel", "panic"], panic_handler),
            MessageHandler(filters.Regex(MENU_BUTTONS_REGEX), panic_handler),
        ],
        allow_reentry=True,
    )
