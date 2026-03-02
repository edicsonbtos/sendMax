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
BROADCAST_CONTENT, BROADCAST_CONFIRM = range(2)

# Botones
BTN_CONFIRM = "✅ Enviar"
BTN_CANCEL = "❌ Cancelar"

# ── Idempotency lock ──────────────────────────────────────────────────────────
# Evita que el administrador lance dos difusiones simultáneas (re-entry).
# Clave: admin telegram_id → timestamp UNIX del inicio de la difusión activa.
_BROADCAST_LOCK: dict[int, float] = {}
_BROADCAST_LOCK_TTL = 300  # 5 minutos máximo por difusión

# Bloqueo por ID de mensaje de confirmación
_PROCESSED_BROADCAST_MSGS: set[int] = set()


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
        [[KeyboardButton(BTN_CANCEL)]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )
    await update.message.reply_text(
        "📢 **Modo Difusión Iniciado**\n\n"
        "Envía ahora mismo el mensaje que deseas difundir a todos los operadores.\n\n"
        "💡 _Tip: Puedes enviar Texto, Fotos, Videos, GIFs o Documentos._",
        reply_markup=kb,
        parse_mode="Markdown",
    )
    return BROADCAST_CONTENT


async def on_broadcast_content(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message.text == BTN_CANCEL:
        _release_broadcast_lock(context.user_data.pop("broadcast_admin_id", 0))
        await update.message.reply_text("Difusión cancelada ✅", reply_markup=admin_panel_keyboard())
        return ConversationHandler.END

    # Guardar ID del chat original y del mensaje para usar copy_message
    context.user_data["broadcast_from_chat_id"] = update.effective_chat.id
    context.user_data["broadcast_message_id"] = update.message.message_id

    # Vista previa usando copy_message hacia el admin
    await update.message.reply_text("👀 **Vista previa del mensaje a difundir:**", parse_mode="Markdown")
    await context.bot.copy_message(
        chat_id=update.effective_chat.id,
        from_chat_id=update.effective_chat.id,
        message_id=update.message.message_id
    )

    # Contar operadores
    async with get_async_conn() as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT COUNT(*) FROM users WHERE is_active = true;")
            rows = await cur.fetchall()
            count = rows[0][0] if rows else 0

    context.user_data["broadcast_count"] = count

    kb = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("✅ Confirmar y Enviar", callback_data="bc_confirm")],
            [InlineKeyboardButton("❌ Cancelar Difusión", callback_data="bc_cancel")]
        ]
    )
    await update.message.reply_text(
        f"Se enviará a **{count}** operadores registrados y activos.\n\n¿Deseas enviar este mensaje ahora?",
        reply_markup=kb,
        parse_mode="Markdown",
    )
    return BROADCAST_CONFIRM


async def on_broadcast_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    
    action = query.data
    admin_id = context.user_data.get("broadcast_admin_id", 0)

    # Bloqueo doble click en inline buttons
    if query.message.message_id in _PROCESSED_BROADCAST_MSGS:
        logger.warning("[Broadcast] Ignorando doble clic en botón inline ID: %s", query.message.message_id)
        return ConversationHandler.END
    _PROCESSED_BROADCAST_MSGS.add(query.message.message_id)

    if action == "bc_cancel":
        _release_broadcast_lock(admin_id)
        await query.edit_message_text("Difusión cancelada ✅")
        await query.message.reply_text("Volviendo al Panel Admin...", reply_markup=admin_panel_keyboard())
        return ConversationHandler.END

    if action != "bc_confirm":
        return BROADCAST_CONFIRM

    # Idempotency Lock
    if context.user_data.get("is_broadcasting"):
        logger.warning("[Broadcast] Ignorando doble sesión de difusión activa.")
        return ConversationHandler.END
    context.user_data["is_broadcasting"] = True

    from_chat_id = context.user_data.get("broadcast_from_chat_id")
    message_id = context.user_data.get("broadcast_message_id")

    await query.edit_message_text("🚀 Iniciando difusión... esto puede tardar unos minutos. Por favor no envíes más comandos.")

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
            await context.bot.copy_message(
                chat_id=tg_id_int,
                from_chat_id=from_chat_id,
                message_id=message_id
            )
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
    await query.message.reply_text(report, reply_markup=admin_panel_keyboard(), parse_mode="Markdown")

    # Limpiar estado
    for k in ["broadcast_from_chat_id", "broadcast_message_id", "broadcast_count", "broadcast_admin_id", "is_broadcasting"]:
        context.user_data.pop(k, None)
    _release_broadcast_lock(admin_id)

    return ConversationHandler.END


async def cancel_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    _release_broadcast_lock(context.user_data.pop("broadcast_admin_id", 0))
    await update.message.reply_text("Difusión cancelada ✅", reply_markup=admin_panel_keyboard())
    return ConversationHandler.END


def build_broadcast_handler() -> ConversationHandler:
    from telegram.ext import MessageHandler, filters, CommandHandler, CallbackQueryHandler
    return ConversationHandler(
        entry_points=[
            CommandHandler("broadcast", start_broadcast),
            MessageHandler(filters.Regex(rf"^{BTN_ADMIN_BROADCAST}$"), start_broadcast),
        ],
        states={
            BROADCAST_CONTENT: [
                MessageHandler(filters.ALL & ~filters.COMMAND, on_broadcast_content),
            ],
            BROADCAST_CONFIRM: [
                CallbackQueryHandler(on_broadcast_confirm, pattern="^bc_(confirm|cancel)$")
            ],
        },
        fallbacks=[
            CommandHandler(["cancel", "panic"], panic_handler),
            MessageHandler(filters.Regex(MENU_BUTTONS_REGEX), panic_handler),
            MessageHandler(filters.Regex(rf"^{BTN_CANCEL}$"), cancel_broadcast),
        ],
        allow_reentry=False,  # ← idempotency: previene doble inicio por spam
        name="admin_broadcast",
        persistent=True,
    )
