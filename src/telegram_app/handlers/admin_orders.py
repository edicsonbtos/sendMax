from __future__ import annotations

import logging
from decimal import Decimal, ROUND_HALF_UP

import psycopg
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from src.config.settings import settings
from src.telegram_app.ui.routes_popular import COUNTRY_FLAGS, format_rate_no_noise
from src.db.repositories import rates_repo
from src.db.repositories.orders_repo import (
    list_orders_by_status,
    update_order_status,
    mark_origin_verified,
    get_order_by_public_id,
    cancel_order,
    mark_order_paid,
    mark_order_paid_tx,
    set_profit_usdt,
    set_profit_usdt_tx,
    set_awaiting_paid_proof,
    clear_awaiting_paid_proof,
    clear_awaiting_paid_proof_tx,
    list_orders_awaiting_paid_proof_by,
)
from src.db.repositories.users_repo import get_telegram_id_by_user_id
from src.db.repositories.wallet_repo import add_ledger_entry, add_ledger_entry_tx

logger = logging.getLogger(__name__)


def _q8(d: Decimal) -> Decimal:
    """Mantiene la precisión de 8 decimales para cálculos internos"""
    return d.quantize(Decimal("0.00000001"), rounding=ROUND_HALF_UP)


def _is_authorized(update: Update) -> bool:
    """
    Autoriza si es Admin Global O si la acción ocurre en el Grupo de Pagos.
    """
    user_id = getattr(update.effective_user, "id", None)
    chat_id = getattr(update.effective_chat, "id", None)

    if settings.is_admin_id(user_id):
        return True

    if str(chat_id) == str(settings.PAYMENTS_TELEGRAM_CHAT_ID):
        return True

    if str(chat_id) == str(settings.ORIGIN_REVIEW_TELEGRAM_CHAT_ID):
        return True

    return False


def _order_actions_kb(public_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("⏳ EN PROCESO", callback_data=f"ord:proc:{public_id}"),
                InlineKeyboardButton("✅ PAGADA", callback_data=f"ord:paid:{public_id}"),
            ],
            [InlineKeyboardButton("❌ CANCELAR", callback_data=f"ord:cancel:{public_id}")],
        ]
    )


async def admin_orders(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_authorized(update):
        return

    orders = list_orders_by_status("CREADA", limit=10)
    if not orders:
        await update.message.reply_text("✅ No hay órdenes pendientes por procesar.")
        return

    await update.message.reply_text(
        f"📋 <b>Órdenes Pendientes ({len(orders)})</b>\nToca una acción 👇",
        parse_mode="HTML"
    )

    for o in orders:
        text = (
            f"🆔 <b>#{o.public_id}</b>\n"
            f"🏳️ {o.origin_country} -> {o.dest_country}\n"
            f"💰 Recibe: {o.amount_origin}\n"
            f"💵 Payout: {o.payout_dest:,.2f}\n"
        )
        await update.message.reply_text(text, reply_markup=_order_actions_kb(o.public_id), parse_mode="HTML")


async def handle_admin_order_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    if not q:
        return

    if not _is_authorized(update):
        try:
            await q.answer("🚫 Acceso denegado.", show_alert=True)
        except Exception:
            pass
        return

    data = q.data or ""
    parts = data.split(":")
    if len(parts) != 3:
        return

    _, action, pid_str = parts
    try:
        public_id = int(pid_str)
    except Exception:
        return


    # ORIGIN REVIEW (nuevo grupo): callbacks de verificación de comprobante ORIGEN
    if action in ("orig_ok", "orig_rej"):
        # Solo aceptar estas acciones desde el chat ORIGIN_REVIEW
        chat_id = getattr(update.effective_chat, "id", None)
        if str(chat_id) != str(settings.ORIGIN_REVIEW_TELEGRAM_CHAT_ID):
            try:
                await q.answer("Acción solo válida en el grupo de verificación de origen.", show_alert=True)
            except Exception:
                pass
            return

        order = get_order_by_public_id(public_id)
        if not order:
            try:
                await q.answer("Orden no encontrada.", show_alert=True)
            except Exception:
                pass
            return

        if action == "orig_ok":
            ok = mark_origin_verified(
                public_id,
                by_telegram_user_id=getattr(update.effective_user, "id", None),
                by_name=(getattr(update.effective_user, "full_name", None) or getattr(update.effective_user, "username", None)),
            )
            try:
                await q.answer("✅ Origen confirmado" if ok else "⚠️ No pude actualizar estado", show_alert=not ok)
            except Exception:
                pass

            # Notificar a PAYMENTS: enviar resumen (sin comprobante origen) con teclado actual
            try:
                target_chat_id = int(settings.PAYMENTS_TELEGRAM_CHAT_ID)
                origin = str(order.origin_country)
                dest = str(order.dest_country)
                origin_flag = COUNTRY_FLAGS.get(origin, origin)
                dest_flag = COUNTRY_FLAGS.get(dest, dest)

                summary = (
                    "🆕 <b>ORDEN LISTA PARA PAGOS</b>\n\n"
                    f"🆔 <b>#{public_id}</b>\n"
                    f"Monto Origen: <b>{order.amount_origin} {origin}</b>\n"
                    f"Tasa: {format_rate_no_noise(order.rate_client)}\n"
                    f"Pago Destino: <b>{order.payout_dest} {dest}</b>\n"
                )

                await context.bot.send_message(
                    chat_id=target_chat_id,
                    text=summary,
                    parse_mode="HTML",
                    reply_markup=_order_actions_kb(public_id),
                    disable_web_page_preview=True,
                )

                # Beneficiario (ya escapado en new_order_flow cuando se envía, pero aquí es nuevo envío)
                if (order.beneficiary_text or "").strip():
                    from src.telegram_app.utils.text_escape import esc_html
                    await context.bot.send_message(
                        chat_id=target_chat_id,
                        text="👤 <b>Datos Beneficiario:</b>\n" + esc_html(order.beneficiary_text or ""),
                        parse_mode="HTML",
                    )
            except Exception:
                logger.exception("orig_ok: fallo notificando a PAYMENTS para orden %s", public_id)

            return

        # action == orig_rej (por ahora cancela sin motivo; luego pedimos motivo con flow)
        if action == "orig_rej":
            ok = cancel_order(public_id, "ORIGEN RECHAZADO")
            try:
                await q.answer("❌ Origen rechazado" if ok else "⚠️ No pude cancelar", show_alert=not ok)
            except Exception:
                pass
            try:
                await q.message.reply_text(f"Orden #{public_id} cancelada por ORIGEN RECHAZADO.")
            except Exception:
                pass
            return


    if action == "proc":
        ok = update_order_status(public_id, "EN_PROCESO")
        try:
            await q.answer("✅ Marcada en Proceso")
            if ok:
                new_text = q.message.text + "\n\n🔄 Estado: EN PROCESO"
                await q.edit_message_text(new_text, reply_markup=_order_actions_kb(public_id))
        except Exception:
            pass

        if ok:
            order = get_order_by_public_id(public_id)
            if order:
                op_tid = get_telegram_id_by_user_id(int(order.operator_user_id))
                if op_tid:
                    try:
                        await context.bot.send_message(
                            chat_id=int(op_tid),
                            text=f"⏳ Tu orden #{public_id} está siendo procesada...",
                        )
                    except Exception:
                        pass
        return

    if action == "paid":
        # Seguridad: evita que un mismo operador tenga 2 órdenes en espera de comprobante
        already = list_orders_awaiting_paid_proof_by(getattr(update.effective_user, "id", 0) or 0, limit=2)
        if already and int(already[0].public_id) != int(public_id):
            try:
                await q.answer("⚠️ Ya tienes una orden en espera. Sube ese comprobante primero.", show_alert=True)
            except Exception:
                pass
            await q.message.reply_text(
                f"⚠️ Ya tienes una orden en espera de comprobante: #{int(already[0].public_id)}.\n"
                f"Cierra esa primero antes de marcar otra como PAGADA."
            )
            return
        # Persistir en DB (anti-caídas)
        ok = set_awaiting_paid_proof(
            public_id,
            by_telegram_user_id=getattr(update.effective_user, "id", None),
        )
        try:
            await q.answer("📸 Sube la foto" if ok else "❌ No pude dejar la orden en espera")
        except Exception:
            pass

        await q.message.reply_text(
            f"📸 <b>PAGO ORDEN #{public_id}</b>\n"
            f"Envía la captura del pago aquí para cerrar la orden.\n\n"
            f"(Si el bot se reinicia, la orden seguirá en espera en la DB.)",
            parse_mode="HTML"
        )
        return

    if action == "cancel":
        context.user_data["awaiting_cancel_reason_for"] = public_id
        try:
            await q.answer()
            await q.message.reply_text(f"✍️ Escribe el motivo de cancelación para la #{public_id}:")
        except Exception:
            pass
        return


def _pick_pending_order_id_from_db(by_telegram_user_id: int) -> int | None:
    pending = list_orders_awaiting_paid_proof_by(by_telegram_user_id, limit=1)
    if not pending:
        return None
    return int(pending[0].public_id)




async def process_paid_proof_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Cierre de orden con comprobante de pago destino.
    Seguridad/Consistencia:
    - Selecciona pendiente por operador (awaiting_paid_proof_by).
    - Operación atómica: order(PAGADA/profit/awaiting) + ledger + wallet en 1 transacción.
    """
    if not _is_authorized(update):
        return

    if not update.message or not update.message.photo:
        return

    public_id = _pick_pending_order_id_from_db(update.effective_user.id)
    if not public_id:
        await update.message.reply_text("ℹ️ No hay órdenes en espera de comprobante.")
        return

    proof_file_id = update.message.photo[-1].file_id

    try:
        order = get_order_by_public_id(public_id)
        if not order:
            await update.message.reply_text("❌ Error: Orden no encontrada. (No limpio la espera para poder reintentar)")
            return

        rr = rates_repo.get_route_rate(
            rate_version_id=int(order.rate_version_id),
            origin_country=str(order.origin_country),
            dest_country=str(order.dest_country),
        )
        if not rr:
            await update.message.reply_text("❌ No pude obtener route_rate para calcular profit_usdt.")
            return

        amount_origin = Decimal(str(order.amount_origin))
        payout_dest = Decimal(str(order.payout_dest))
        buy_origin = Decimal(str(rr.buy_origin))
        sell_dest = Decimal(str(rr.sell_dest))
        profit_usdt = _q8((amount_origin / buy_origin) - (payout_dest / sell_dest))

        # sponsor split (lectura fuera de la tx financiera principal)
        sponsor_id = None
        try:
            with psycopg.connect(settings.DATABASE_URL) as rconn:
                with rconn.cursor() as cur:
                    cur.execute("SELECT sponsor_id FROM users WHERE id=%s LIMIT 1;", (int(order.operator_user_id),))
                    row = cur.fetchone()
                    sponsor_id = int(row[0]) if row and row[0] is not None else None
        except Exception:
            sponsor_id = None

        if sponsor_id:
            op_share = _q8(profit_usdt * Decimal("0.45"))
            sp_share = _q8(profit_usdt * Decimal("0.10"))
            memo_op = "Profit orden (45%)"
            memo_sp = "Comisión sponsor (10%)"
        else:
            op_share = _q8(profit_usdt * Decimal("0.50"))
            sp_share = Decimal("0")
            memo_op = "Profit orden (50%)"
            memo_sp = None

        # ---- ATÓMICO: order + ledger + wallet ----
        with psycopg.connect(settings.DATABASE_URL) as conn:
            with conn.transaction():
                ok_paid = mark_order_paid_tx(conn, int(public_id), proof_file_id)
                if not ok_paid:
                    raise RuntimeError("No pude marcar la orden como PAGADA (tx)")

                ok_profit = set_profit_usdt_tx(conn, int(public_id), profit_usdt)
                if not ok_profit:
                    raise RuntimeError("No pude guardar profit_usdt (tx)")

                if op_share != 0:
                    add_ledger_entry_tx(
                        conn,
                        user_id=int(order.operator_user_id),
                        amount_usdt=op_share,
                        entry_type="ORDER_PROFIT",
                        ref_order_public_id=int(public_id),
                        memo=memo_op,
                        idempotency=True,
                    )

                if sponsor_id and sp_share != 0:
                    add_ledger_entry_tx(
                        conn,
                        user_id=int(sponsor_id),
                        amount_usdt=sp_share,
                        entry_type="SPONSOR_COMMISSION",
                        ref_order_public_id=int(public_id),
                        memo=memo_sp,
                        idempotency=True,
                    )

                ok_clear = clear_awaiting_paid_proof_tx(conn, int(public_id))
                if not ok_clear:
                    raise RuntimeError("No pude limpiar awaiting_paid_proof (tx)")

        # Confirmación en grupo
        lines = [
            f"✅ <b>ORDEN #{public_id} CERRADA</b>",
            "",
            f"💰 Profit: {profit_usdt:,.2f} USDT",
            f"👤 Operador: {op_share:,.2f} USDT",
        ]
        if sponsor_id and sp_share != 0:
            lines.append(f"🤝 Sponsor: {sp_share:,.2f} USDT")

        await update.message.reply_text("\n".join(lines), parse_mode="HTML")

    except Exception as e:
        logger.exception("process_paid_proof_photo: fallo cerrando orden %s: %s", public_id, e)
        await update.message.reply_text("❌ Error interno cerrando la orden. Reintenta subiendo la foto nuevamente.")
        return

    # Notificación operador (best-effort)
    op_tid = get_telegram_id_by_user_id(int(order.operator_user_id))
    if op_tid:
        try:
            await context.bot.send_message(
                chat_id=int(op_tid),
                text=f"✅ Orden #{public_id} PAGADA.\n¡Gracias! 🚀",
            )
            await context.bot.send_photo(
                chat_id=int(op_tid),
                photo=proof_file_id,
                caption=f"Comprobante Orden #{public_id}",
            )
        except Exception:
            pass


async def handle_cancel_reason_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_authorized(update):
        return

    public_id = context.user_data.get("awaiting_cancel_reason_for")
    if not public_id:
        return

    reason = (update.message.text or "").strip()
    if len(reason) < 3:
        await update.message.reply_text("Motivo muy corto.")
        return

    ok = cancel_order(int(public_id), reason)
    context.user_data.pop("awaiting_cancel_reason_for", None)

    if ok:
        await update.message.reply_text(f"❌ Orden #{public_id} cancelada.\nMotivo: {reason}")

        # Notificar al operador (best-effort)
        try:
            order = get_order_by_public_id(int(public_id))
            if order:
                op_tid = get_telegram_id_by_user_id(int(order.operator_user_id))
                if op_tid:
                    await context.bot.send_message(
                        chat_id=int(op_tid),
                        text=(
                            f"❌ Orden #{public_id} CANCELADA\n"
                            f"Motivo: {reason}"
                        ),
                    )
        except Exception:
            logger.exception("cancel_order: no pude notificar al operador para orden %s", public_id)
    else:
        await update.message.reply_text("Error al cancelar.")
