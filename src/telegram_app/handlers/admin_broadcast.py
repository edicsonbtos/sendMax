from __future__ import annotations

import asyncio
import logging
import time

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

# ── Idempotency lock ──────────────────────────────────────────────────────────
# Evita que el administrador lance dos difusiones simultáneas (re-entry).
# Clave: admin telegram_id → timestamp UNIX del inicio de la difusión activa.
_BROADCAST_LOCK: dict[int, float] = {}
_BROADCAST_LOCK_TTL = 300  # 5 minutos máximo por difusión


def _lock_broadcast(admin_id: int) -> bool:
    """Intenta adquirir el lock. Retorna True si tiene éxito (no hay difusión activa)."""
    now = time.time()
    existing = _BROADCAST_LOCK.get(admin_id)
    if existing and (now - existing) < _BROADCAST_LOCK_TTL:
        return False  # Lock activo
    _BROADCAST_LOCK[admin_id] = now
    return True


def _release_broadcast_lock(admin_id: int) -> None:
    _BROADCAST_LOCK.pop(admin_id, None)


def _is_admin(update: Update) -> bool:
    return settings.is_admin_id(getattr(update.effective_user, "id", None))


async def start_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not _is_admin(update):
        return ConversationHandler.END

    admin_id = int(update.effective_user.id)
    if not _lock_broadcast(admin_id):
        await update.message.reply_text(
            "⚠️ Ya hay una difusión en curso. "
            "Espera a que finalice antes de iniciar otra."
        )
        return ConversationHandler.END

    context.user_data["broadcast_admin_id"] = admin_id

    kb = ReplyKeyboardMarkup(
        [[KeyboardButton(BTN_TEXT), KeyboardButton(BTN_IMAGE)], [KeyboardButton(BTN_CANCEL)]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )
    await update.message.reply_text(
        "📢 **Difusión**\n\n¿Qué tipo de difusión deseas realizar?",
        reply_markup=kb,
        parse_mode="Markdown",
    )
    return BROADCAST_TYPE


async def on_broadcast_type(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = (update.message.text or "").strip()

    if text == BTN_CANCEL:
        _release_broadcast_lock(context.user_data.pop("broadcast_admin_id", 0))
        await update.message.reply_text("Difusión cancelada ✅", reply_markup=admin_panel_keyboard())
        return ConversationHandler.END

    if text == BTN_TEXT:
        context.user_data["broadcast_type"] = "text"
        await update.message.reply_text(
            "Escribe el mensaje que deseas enviar a todos los operadores:",
            reply_markup=ReplyKeyboardMarkup([[KeyboardButton(BTN_CANCEL)]], resize_keyboard=True),
        )
        return BROADCAST_CONTENT

    if text == BTN_IMAGE:
        context.user_data["broadcast_type"] = "image"
        await update.message.reply_text(
            "Envía la imagen con el texto (caption) que deseas difundir:",
            reply_markup=ReplyKeyboardMarkup([[KeyboardButton(BTN_CANCEL)]], resize_keyboard=True),
        )
        return BROADCAST_CONTENT

    await update.message.reply_text("Por favor, elige una opción válida usando los botones.")
    return BROADCAST_TYPE


async def on_broadcast_content(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message.text == BTN_CANCEL:
        _release_broadcast_lock(context.user_data.pop("broadcast_admin_id", 0))
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
            caption=context.user_data["broadcast_text"],
        )

    # Contar operadores
    async with get_async_conn() as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT COUNT(*) FROM users WHERE is_active = true;")
            rows = await cur.fetchall()
            count = rows[0][0] if rows else 0

    context.user_data["broadcast_count"] = count

    kb = ReplyKeyboardMarkup(
        [[KeyboardButton(BTN_CONFIRM)], [KeyboardButton(BTN_CANCEL)]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )
    await update.message.reply_text(
        f"Se enviará a **{count}** operadores registrados y activos.\n\n¿Confirmar envío?",
        reply_markup=kb,
        parse_mode="Markdown",
    )
    return BROADCAST_CONFIRM


async def on_broadcast_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = (update.message.text or "").strip()
    admin_id = context.user_data.get("broadcast_admin_id", 0)

    if text == BTN_CANCEL:
        _release_broadcast_lock(admin_id)
        await update.message.reply_text("Difusión cancelada ✅", reply_markup=admin_panel_keyboard())
        return ConversationHandler.END

    if text != BTN_CONFIRM:
        await update.message.reply_text("Por favor, usa los botones para confirmar o cancelar.")
        return BROADCAST_CONFIRM

    b_type = context.user_data.get("broadcast_type")
    b_text = context.user_data.get("broadcast_text")
    b_photo = context.user_data.get("broadcast_photo")

    await update.message.reply_text("🚀 Iniciando difusión... esto puede tardar un poco.")

    async with get_async_conn() as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT telegram_user_id FROM users WHERE is_active = true;")
            rows = await cur.fetchall()

    # Deduplicar IDs — evita enviar dos veces si hay duplicados en DB
    seen_ids: set[int] = set()
    success_count = 0
    fail_count = 0
    blocked_count = 0

    for row in rows:
        tg_id = row[0]
        if not tg_id:
            continue
        tg_id_int = int(tg_id)
        if tg_id_int in seen_ids:
            logger.warning("[Broadcast] ID duplicado en DB omitido: %s", tg_id_int)
            continue
        seen_ids.add(tg_id_int)

        try:
            if b_type == "text":
                await context.bot.send_message(chat_id=tg_id_int, text=b_text)
            else:
                await context.bot.send_photo(chat_id=tg_id_int, photo=b_photo, caption=b_text)
            success_count += 1
            await asyncio.sleep(0.05)  # Telegram: 20 req/sec máximo
        except Exception as e:
            err_str = str(e).lower()
            if "blocked" in err_str or "deactivated" in err_str or "forbidden" in err_str:
                blocked_count += 1
                logger.info("[Broadcast] Operador bloqueó el bot: %s", tg_id_int)
            else:
                logger.warning("[Broadcast] No pude enviar a %s: %s", tg_id_int, e)
                fail_count += 1

    report = (
        f"✅ **Reporte de difusión finalizada**\n\n"
        f"📬 Enviados: {success_count}\n"
        f"🚫 Bloqueados/inactivos: {blocked_count}\n"
        f"❌ Errores técnicos: {fail_count}\n"
        f"👥 Total IDs únicos procesados: {len(seen_ids)}"
    )
    await update.message.reply_text(report, reply_markup=admin_panel_keyboard(), parse_mode="Markdown")

    # Limpiar estado
    for k in ["broadcast_type", "broadcast_text", "broadcast_photo", "broadcast_count", "broadcast_admin_id"]:
        context.user_data.pop(k, None)
    _release_broadcast_lock(admin_id)

    return ConversationHandler.END


async def cancel_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    _release_broadcast_lock(context.user_data.pop("broadcast_admin_id", 0))
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
        allow_reentry=False,  # ← idempotency: previene doble inicio por spam
    )
