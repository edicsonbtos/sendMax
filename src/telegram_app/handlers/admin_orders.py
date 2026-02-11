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
from src.db.repositories.origin_wallet_repo import add_origin_receipt_daily
from src.integrations.binance_p2p import BinanceP2PClient
from src.integrations.p2p_config import COUNTRIES

logger = logging.getLogger(__name__)

ORIGIN_FIAT_CURRENCY = {
    "PERU": "PEN",
    "CHILE": "CLP",
    "VENEZUELA": "VES",
    "COLOMBIA": "COP",
    "USA": "USD",
    "MEXICO": "MXN",
    "ARGENTINA": "ARS",
}


def _q8(d: Decimal) -> Decimal:
    return d.quantize(Decimal("0.00000001"), rounding=ROUND_HALF_UP)


def _is_authorized(update: Update) -> bool:
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
                InlineKeyboardButton("⚙ EN PROCESO", callback_data=f"ord:proc:{public_id}"),
                InlineKeyboardButton("✅ PAGADA", callback_data=f"ord:paid:{public_id}"),
            ],
            [InlineKeyboardButton("❌ CANCELAR", callback_data=f"ord:cancel:{public_id}")],
        ]
    )


def _fetch_realtime_prices(origin_country: str, dest_country: str):
    """Consulta precios actuales de Binance P2P para calcular profit real"""
    origin_cfg = COUNTRIES.get(origin_country)
    dest_cfg = COUNTRIES.get(dest_country)
    
    if not origin_cfg or not dest_cfg:
        return None, None
    
    client = BinanceP2PClient()
    try:
        buy_quote = client.fetch_first_price(
            fiat=origin_cfg.fiat,
            trade_type="BUY",
            pay_methods=origin_cfg.buy_methods,
            trans_amount=origin_cfg.trans_amount,
        )
        sell_quote = client.fetch_first_price(
            fiat=dest_cfg.fiat,
            trade_type="SELL",
            pay_methods=dest_cfg.sell_methods,
            trans_amount=dest_cfg.trans_amount,
        )
        return Decimal(str(buy_quote.price)), Decimal(str(sell_quote.price))
    except Exception as e:
        logger.warning(f"No pude obtener precios real-time de Binance: {e}")
        return None, None
    finally:
        client.close()


async def admin_orders(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_authorized(update):
        return

    orders = list_orders_by_status("CREADA", limit=10)
    if not orders:
        await update.message.reply_text("📭 No hay órdenes pendientes por procesar.")
        return

    await update.message.reply_text(
        f"📋 <b>Órdenes Pendientes ({len(orders)})</b>\nToca una acción 👇",
        parse_mode="HTML"
    )

    for o in orders:
        text = (
            f"🆔 <b>#{o.public_id}</b>\n"
            f"➡️ {o.origin_country} -> {o.dest_country}\n"
            f"💵 Recibe: {o.amount_origin}\n"
            f"💸 Payout: {o.payout_dest:,.2f}\n"
        )
        await update.message.reply_text(text, reply_markup=_order_actions_kb(o.public_id), parse_mode="HTML")


async def admin_awaiting_paid(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_authorized(update):
        return

    orders = list_orders_awaiting_paid_proof_by(update.effective_user.id, limit=5)
    if not orders:
        await update.message.reply_text("No tienes órdenes esperando comprobante.")
        return

    for o in orders:
        await update.message.reply_text(
            f"⏳ Orden #{o.public_id} esperando comprobante de pago.\nSube la foto aquí."
        )


async def handle_admin_order_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    if not q:
        return

    if not _is_authorized(update):
        try:
            await q.answer("⛔ Acceso denegado.", show_alert=True)
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

    # ORIGIN REVIEW callbacks
    if action in ("orig_ok", "orig_rej"):
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

            try:
                from datetime import datetime, timedelta, timezone
                VET = timezone(timedelta(hours=-4))
                day_vet = datetime.now(tz=timezone.utc).astimezone(VET).date()

                fiat_currency = ORIGIN_FIAT_CURRENCY.get(str(order.origin_country), str(order.origin_country))
                add_origin_receipt_daily(
                    day=day_vet,
                    origin_country=str(order.origin_country),
                    fiat_currency=str(fiat_currency),
                    amount_fiat=Decimal(str(order.amount_origin)),
                    approved_by_telegram_id=getattr(update.effective_user, "id", None),
                    approved_note=f"ORIGEN OK por {(getattr(update.effective_user, 'full_name', None) or getattr(update.effective_user, 'username', None) or 'operador')}",
                    ref_order_public_id=int(public_id),
                )
            except Exception:
                logger.exception("orig_ok: no pude insertar origin_receipts_daily para orden %s", public_id)

            try:
                target_chat_id = int(settings.PAYMENTS_TELEGRAM_CHAT_ID)
                origin = str(order.origin_country)
                dest = str(order.dest_country)

                summary = (
                    "📦 <b>ORDEN LISTA PARA PAGOS</b>\n\n"
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

                if (order.beneficiary_text or "").strip():
                    from src.telegram_app.utils.text_escape import esc_html
                    await context.bot.send_message(
                        chat_id=target_chat_id,
                        text="📝 <b>Datos Beneficiario:</b>\n" + esc_html(order.beneficiary_text or ""),
                        parse_mode="HTML",
                    )
            except Exception:
                logger.exception("orig_ok: fallo notificando a PAYMENTS para orden %s", public_id)

            return

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
            await q.answer("⚙ Marcada en Proceso")
            if ok:
                new_text = q.message.text + "\n\n⚙️ Estado: EN PROCESO"
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
                            text=f"⚙ Tu orden #{public_id} está siendo procesada...",
                        )
                    except Exception:
                        pass
        return

    if action == "paid":
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
            await q.message.reply_text(f"📝 Escribe el motivo de cancelación para la #{public_id}:")
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
    MEJORA: Consulta precios ACTUALES de Binance para profit_real_usdt.
    Operación atómica: order(PAGADA/profit/awaiting) + ledger + wallet en 1 transacción.
    """
    if not _is_authorized(update):
        return

    if not update.message or not update.message.photo:
        return

    public_id = _pick_pending_order_id_from_db(update.effective_user.id)
    if not public_id:
        await update.message.reply_text("⚠️ No hay órdenes en espera de comprobante.")
        return

    proof_file_id = update.message.photo[-1].file_id

    try:
        order = get_order_by_public_id(public_id)
        if not order:
            await update.message.reply_text("❌ Error: Orden no encontrada.")
            return

        # 1. Profit TEÓRICO (con tasa de cuando se creó la orden)
        rr = rates_repo.get_route_rate(
            rate_version_id=int(order.rate_version_id),
            origin_country=str(order.origin_country),
            dest_country=str(order.dest_country),
        )
        if not rr:
            await update.message.reply_text("❌ No pude obtener route_rate para calcular profit.")
            return

        amount_origin = Decimal(str(order.amount_origin))
        payout_dest = Decimal(str(order.payout_dest))
        buy_origin_snapshot = Decimal(str(rr.buy_origin))
        sell_dest_snapshot = Decimal(str(rr.sell_dest))
        profit_usdt = _q8((amount_origin / buy_origin_snapshot) - (payout_dest / sell_dest_snapshot))

        # 2. Profit REAL (con precios actuales de Binance)
        exec_buy, exec_sell = _fetch_realtime_prices(
            str(order.origin_country), str(order.dest_country)
        )
        
        if exec_buy and exec_sell:
            profit_real = _q8((amount_origin / exec_buy) - (payout_dest / exec_sell))
            logger.info(
                f"Orden #{public_id}: profit_teorico={profit_usdt}, profit_real={profit_real}, "
                f"buy_snap={buy_origin_snapshot}, buy_real={exec_buy}, "
                f"sell_snap={sell_dest_snapshot}, sell_real={exec_sell}"
            )
        else:
            # Fallback: si Binance falla, usar precios del snapshot
            profit_real = profit_usdt
            exec_buy = buy_origin_snapshot
            exec_sell = sell_dest_snapshot
            logger.warning(f"Orden #{public_id}: Binance no disponible, usando snapshot para profit_real")

        # 3. Sponsor split (usa profit TEÓRICO para pagar al operador - consistente)
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

        # 4. ATÓMICO: order + profit + execution_data + ledger + wallet
        with psycopg.connect(settings.DATABASE_URL) as conn:
            with conn.transaction():
                ok_paid = mark_order_paid_tx(conn, int(public_id), proof_file_id)
                if not ok_paid:
                    raise RuntimeError("No pude marcar la orden como PAGADA (tx)")

                ok_profit = set_profit_usdt_tx(conn, int(public_id), profit_usdt)
                if not ok_profit:
                    raise RuntimeError("No pude guardar profit_usdt (tx)")

                # Guardar datos de ejecución real
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        UPDATE orders 
                        SET execution_price_buy = %s,
                            execution_price_sell = %s,
                            profit_real_usdt = %s
                        WHERE public_id = %s
                        """,
                        (exec_buy, exec_sell, profit_real, int(public_id))
                    )

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

        # 5. Confirmación con ambos profits
        diff = profit_real - profit_usdt
        diff_icon = "📈" if diff >= 0 else "📉"

        lines = [
            f"✅ <b>ORDEN #{public_id} CERRADA</b>",
            "",
            f"💰 Profit estimado: {profit_usdt:,.4f} USDT",
            f"💰 Profit real: {profit_real:,.4f} USDT",
            f"{diff_icon} Diferencia: {diff:,.4f} USDT",
            "",
            f"👤 Operador: {op_share:,.4f} USDT",
        ]
        if sponsor_id and sp_share != 0:
            lines.append(f"🤝 Sponsor: {sp_share:,.4f} USDT")

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
                text=f"✅ Orden #{public_id} PAGADA.\n¡Gracias! 🎉",
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
