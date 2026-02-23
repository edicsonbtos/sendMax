from __future__ import annotations

import logging
from decimal import ROUND_DOWN, Decimal

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CallbackQueryHandler, ContextTypes, MessageHandler, filters

from src.config.settings import settings
from src.db.connection import get_async_conn
from src.db.repositories import rates_repo
from src.db.repositories.orders_repo import (
    get_order_by_public_id,
    mark_order_paid,
    set_profit_usdt,
)
from src.db.repositories.users_repo import get_telegram_id_by_user_id
from src.db.repositories.wallet_repo import add_ledger_entry

logger = logging.getLogger(__name__)

CB_DM_PAID = "open_dm_paid:"


def _is_admin(update: Update) -> bool:
    return settings.is_admin_id(getattr(update.effective_user, "id", None))


def _q8(x: Decimal) -> Decimal:
    return x.quantize(Decimal("0.00000001"), rounding=ROUND_DOWN)


def dm_paid_button(public_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("📩 Enviar comprobante por privado", callback_data=f"{CB_DM_PAID}{public_id}")]]
    )


async def on_open_dm_paid(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    if not q:
        return

    if not _is_admin(update):
        try:
            await q.answer("No autorizado", show_alert=True)
        except Exception:
            pass
        return

    try:
        await q.answer()
    except Exception:
        pass

    try:
        public_id = int((q.data or "").split(":", 1)[1])
    except Exception:
        await q.message.reply_text("❌ ID inválido.")
        return

    context.user_data["pending_paid_dm_order_id"] = public_id

    try:
        await q.message.reply_text(
            f"✅ Listo. Ahora envía el comprobante por privado al bot para la orden #{public_id}.",
        )
    except Exception:
        pass

    try:
        await context.bot.send_message(
            chat_id=update.effective_user.id,
            text=(
                f"📸 *Comprobante PAGO DESTINO*\n\n"
                f"Orden #{public_id}\n\n"
                "Envía *1 foto* (no álbum, no reenviada, no video).\n"
                "Para cancelar: /cancel_paid"
            ),
            parse_mode="Markdown",
        )
    except Exception as e:
        logger.info(f"DM to admin failed: {e}")


async def cancel_paid_dm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_admin(update):
        return
    context.user_data.pop("pending_paid_dm_order_id", None)
    await update.message.reply_text("✅ Cancelado. Ya no estoy esperando comprobante.")


async def on_paid_dm_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_admin(update):
        return

    if update.effective_chat and update.effective_chat.type != "private":
        return

    pid = context.user_data.get("pending_paid_dm_order_id")
    if not pid:
        return

    msg = update.message
    if not msg:
        return

    if getattr(msg, "media_group_id", None):
        await msg.reply_text("❌ Envía solo 1 foto (no álbum).")
        return

    if getattr(msg, "forward_date", None) or getattr(msg, "forward_origin", None) or getattr(msg, "forward_from", None) or getattr(msg, "forward_from_chat", None):
        await msg.reply_text("❌ No reenvíes la imagen. Súbela como foto nueva (1 sola).")
        return

    if msg.video or msg.animation:
        await msg.reply_text("❌ Debe ser una foto (no video/animación).")
        return

    if not msg.photo:
        await msg.reply_text("❌ Necesito una foto. Intenta de nuevo.")
        return

    file_id = msg.photo[-1].file_id

    ok = await mark_order_paid(int(pid), file_id)
    if not ok:
        await msg.reply_text("❌ No pude marcar la orden como PAGADA. Verifica el ID.")
        context.user_data.pop("pending_paid_dm_order_id", None)
        return

    order = await get_order_by_public_id(int(pid))
    if not order:
        await msg.reply_text("❌ Orden marcada PAGADA, pero no pude cargarla para contabilizar.")
        context.user_data.pop("pending_paid_dm_order_id", None)
        return

    rr = await rates_repo.get_route_rate(
        rate_version_id=int(order.rate_version_id),
        origin_country=str(order.origin_country),
        dest_country=str(order.dest_country),
    )
    if not rr:
        await msg.reply_text("❌ No pude obtener route_rate para calcular profit_usdt.")
        context.user_data.pop("pending_paid_dm_order_id", None)
        return

    amount_origin = Decimal(str(order.amount_origin))
    payout_dest = Decimal(str(order.payout_dest))
    buy_origin = Decimal(str(rr.buy_origin))
    sell_dest = Decimal(str(rr.sell_dest))

    profit_usdt = _q8((amount_origin / buy_origin) - (payout_dest / sell_dest))
    await set_profit_usdt(int(pid), profit_usdt)

    # Sponsor lookup usando async conn
    sponsor_id = None
    try:
        async with get_async_conn() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT sponsor_id FROM users WHERE id=%s LIMIT 1;", (int(order.operator_user_id),))
                rows = await cur.fetchall()
                row = rows[0] if rows else None
                sponsor_id = int(row[0]) if row and row[0] is not None else None
    except Exception:
        sponsor_id = None

    if sponsor_id:
        op_share = _q8(profit_usdt * Decimal("0.45"))
        sp_share = _q8(profit_usdt * Decimal("0.10"))
        await add_ledger_entry(
            user_id=int(order.operator_user_id),
            amount_usdt=op_share,
            entry_type="ORDER_PROFIT",
            ref_order_public_id=int(pid),
            memo="Profit orden (45%)",
            idempotency=True,
        )
        await add_ledger_entry(
            user_id=int(sponsor_id),
            amount_usdt=sp_share,
            entry_type="SPONSOR_COMMISSION",
            ref_order_public_id=int(pid),
            memo="Comisión sponsor (10%)",
            idempotency=True,
        )
    else:
        op_share = _q8(profit_usdt * Decimal("0.50"))
        await add_ledger_entry(
            user_id=int(order.operator_user_id),
            amount_usdt=op_share,
            entry_type="ORDER_PROFIT",
            ref_order_public_id=int(pid),
            memo="Profit orden (50%)",
            idempotency=True,
        )

    operator_tid = await get_telegram_id_by_user_id(int(order.operator_user_id))
    if operator_tid:
        try:
            await context.bot.send_message(
                chat_id=int(operator_tid),
                text=f"✅ Tu orden #{pid} fue marcada como PAGADA.\nAquí está el comprobante de pago destino:",
            )
            await context.bot.send_photo(
                chat_id=int(operator_tid),
                photo=file_id,
                caption=f"Comprobante pago destino (Orden #{pid})",
            )
        except Exception:
            pass

    if settings.PAYMENTS_TELEGRAM_CHAT_ID:
        try:
            await context.bot.send_message(
                chat_id=int(settings.PAYMENTS_TELEGRAM_CHAT_ID),
                text=f"✅ Orden #{pid} PAGADA. profit_usdt={profit_usdt}",
            )
        except Exception:
            pass

    await msg.reply_text(f"✅ Orden #{pid} finalizada como PAGADA.\nprofit_usdt={profit_usdt}")
    context.user_data.pop("pending_paid_dm_order_id", None)


def build_dm_paid_callback_handler() -> CallbackQueryHandler:
    return CallbackQueryHandler(on_open_dm_paid, pattern=r"^open_dm_paid:\d+$")


def build_dm_paid_photo_handler() -> MessageHandler:
    return MessageHandler(filters.PHOTO, on_paid_dm_photo)
