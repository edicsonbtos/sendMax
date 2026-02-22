from __future__ import annotations

import logging

from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    Update,
)
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
)

from src.config.settings import settings
from src.db.connection import get_async_conn
from src.telegram_app.handlers.panic import MENU_BUTTONS_REGEX, panic_handler
from src.telegram_app.ui.admin_keyboards import (
    BTN_ADMIN_BROADCAST,
    admin_panel_keyboard,
)

logger = logging.getLogger(__name__)

# Estados
BROADCAST_TYPE, BROADCAST_CONTENT, BROADCAST_CONFIRM = range(3)

# Botones
BTN_TEXT = "📝 Texto"
BTN_IMAGE = "🖼️ Imagen con texto"
BTN_CONFIRM = "✅ Enviar"
BTN_CANCEL = "❌ Cancelar"


def _is_admin(update: Update) -> bool:
    return settings.is_admin_id(getattr(update.effective_user, "id", None))


async def start_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not _is_admin(update):
        return ConversationHandler.END

    kb = ReplyKeyboardMarkup(
        [[KeyboardButton(BTN_TEXT), KeyboardButton(BTN_IMAGE)], [KeyboardButton(BTN_CANCEL)]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )
    await update.message.reply_text("📢 **Difusión**\n\n¿Qué tipo de difusión deseas realizar?", reply_markup=kb, parse_mode="Markdown")
    return BROADCAST_TYPE


async def on_broadcast_type(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = (update.message.text or "").strip()

    if text == BTN_CANCEL:
        await update.message.reply_text("Difusión cancelada ✅", reply_markup=admin_panel_keyboard())
        return ConversationHandler.END

    if text == BTN_TEXT:
        context.user_data["broadcast_type"] = "text"
        await update.message.reply_text("Escribe el mensaje que deseas enviar a todos los operadores:", reply_markup=ReplyKeyboardMarkup([[KeyboardButton(BTN_CANCEL)]], resize_keyboard=True))
        return BROADCAST_CONTENT

    if text == BTN_IMAGE:
        context.user_data["broadcast_type"] = "image"
        await update.message.reply_text("Envía la imagen con el texto (caption) que deseas difundir:", reply_markup=ReplyKeyboardMarkup([[KeyboardButton(BTN_CANCEL)]], resize_keyboard=True))
        return BROADCAST_CONTENT

    await update.message.reply_text("Por favor, elige una opción válida usando los botones.")
    return BROADCAST_TYPE


async def on_broadcast_content(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message.text == BTN_CANCEL:
        await update.message.reply_text("Difusión cancelada ✅", reply_markup=admin_panel_keyboard())
        return ConversationHandler.END

    b_type = context.user_data.get("broadcast_type")

    if b_type == "text":
        if not update.message.text:
            await update.message.reply_text("Por favor, envía un mensaje de texto.")
            return BROADCAST_CONTENT
        context.user_data["broadcast_text"] = update.message.text

    elif b_type == "image":
        if not update.message.photo:
            await update.message.reply_text("Por favor, envía una imagen.")
            return BROADCAST_CONTENT
        context.user_data["broadcast_photo"] = update.message.photo[-1].file_id
        context.user_data["broadcast_text"] = update.message.caption or ""

    # Preview
    await update.message.reply_text("👀 **Vista previa del mensaje:**", parse_mode="Markdown")

    if b_type == "text":
        await update.message.reply_text(context.user_data["broadcast_text"])
    else:
        await update.message.reply_photo(
            photo=context.user_data["broadcast_photo"],
            caption=context.user_data["broadcast_text"]
        )

    # Contar operadores
    async with get_async_conn() as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT COUNT(*) FROM users WHERE is_active = true;")
            count = (await cur.fetchone())[0]

    context.user_data["broadcast_count"] = count

    kb = ReplyKeyboardMarkup(
        [[KeyboardButton(BTN_CONFIRM)], [KeyboardButton(BTN_CANCEL)]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )
    await update.message.reply_text(
        f"Se enviará a **{count}** operadores registrados y activos.\n\n¿Confirmar envío?",
        reply_markup=kb,
        parse_mode="Markdown"
    )
    return BROADCAST_CONFIRM


async def on_broadcast_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = (update.message.text or "").strip()

    if text == BTN_CANCEL:
        await update.message.reply_text("Difusión cancelada ✅", reply_markup=admin_panel_keyboard())
        return ConversationHandler.END

    if text != BTN_CONFIRM:
        await update.message.reply_text("Por favor, usa los botones para confirmar o cancelar.")
        return BROADCAST_CONFIRM

    b_type = context.user_data.get("broadcast_type")
    b_text = context.user_data.get("broadcast_text")
    b_photo = context.user_data.get("broadcast_photo")

    await update.message.reply_text("🚀 Iniciando difusión... esto puede tardar un poco.")
    import asyncio

    async with get_async_conn() as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT telegram_user_id FROM users WHERE is_active = true;")
            rows = await cur.fetchall()

    success_count = 0
    fail_count = 0

    for row in rows:
        tg_id = row[0]
        if not tg_id:
            continue
        try:
            if b_type == "text":
                await context.bot.send_message(chat_id=int(tg_id), text=b_text)
            else:
                await context.bot.send_photo(chat_id=int(tg_id), photo=b_photo, caption=b_text)
            success_count += 1
            # Rate limiting: 20 msg/sec max por bot policy, somos conservadores
            await asyncio.sleep(0.05)
        except Exception as e:
            logger.warning(f"No pude enviar difusión a {tg_id}: {e}")
            fail_count += 1

    await update.message.reply_text(
        f"✅ Difusión finalizada.\n\n"
        f"Sent: {success_count}\n"
        f"Failed: {fail_count}",
        reply_markup=admin_panel_keyboard()
    )

    # Limpiar
    for k in ["broadcast_type", "broadcast_text", "broadcast_photo", "broadcast_count"]:
        context.user_data.pop(k, None)

    return ConversationHandler.END


async def cancel_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Difusión cancelada ✅", reply_markup=admin_panel_keyboard())
    return ConversationHandler.END


def build_broadcast_handler() -> ConversationHandler:
    from telegram.ext import MessageHandler, filters, CommandHandler
    return ConversationHandler(
        entry_points=[
            CommandHandler("broadcast", start_broadcast),
            MessageHandler(filters.Regex(rf"^{BTN_ADMIN_BROADCAST}$"), start_broadcast),
        ],
        states={
            BROADCAST_TYPE: [MessageHandler(filters.TEXT & ~filters.COMMAND, on_broadcast_type)],
            BROADCAST_CONTENT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, on_broadcast_content),
                MessageHandler(filters.PHOTO, on_broadcast_content),
            ],
            BROADCAST_CONFIRM: [MessageHandler(filters.TEXT & ~filters.COMMAND, on_broadcast_confirm)],
        },
        fallbacks=[
            CommandHandler(["cancel", "panic"], panic_handler),
            MessageHandler(filters.Regex(MENU_BUTTONS_REGEX), panic_handler),
            MessageHandler(filters.Regex(rf"^{BTN_CANCEL}$"), cancel_broadcast),
        ],
        allow_reentry=True,
    )
