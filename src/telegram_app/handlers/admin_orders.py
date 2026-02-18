from __future__ import annotations

import logging
from decimal import Decimal, ROUND_HALF_UP

import psycopg
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from src.config.settings import settings
from src.db.connection import get_conn
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
                InlineKeyboardButton("\u2699 EN PROCESO", callback_data=f"ord:proc:{public_id}"),
                InlineKeyboardButton("\u2705 PAGADA", callback_data=f"ord:paid:{public_id}"),
            ],
            [InlineKeyboardButton("\u274c CANCELAR", callback_data=f"ord:cancel:{public_id}")],
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


def _get_fiat_currency(country: str) -> str:
    """Obtiene la moneda fiat de un pais"""
    return ORIGIN_FIAT_CURRENCY.get(country, country)


async def admin_orders(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_authorized(update):
        return

    orders = list_orders_by_status("CREADA", limit=10)
    if not orders:
        await update.message.reply_text("\U0001f4ed No hay ordenes pendientes por procesar.")
        return

    await update.message.reply_text(
        f"\U0001f4cb <b>Ordenes Pendientes ({len(orders)})</b>\nToca una accion \u2b07\ufe0f",
        parse_mode="HTML"
    )

    for o in orders:
        text = (
            f"\U0001f4e6 <b>#{o.public_id}</b>\n"
            f"\U0001f30e {o.origin_country} -> {o.dest_country}\n"
            f"\U0001f4b5 Recibe: {o.amount_origin}\n"
            f"\U0001f4b0 Payout: {o.payout_dest:,.2f}\n"
        )
        await update.message.reply_text(text, reply_markup=_order_actions_kb(o.public_id), parse_mode="HTML")


async def admin_awaiting_paid(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_authorized(update):
        return

    orders = list_orders_awaiting_paid_proof_by(update.effective_user.id, limit=5)
    if not orders:
        await update.message.reply_text("No tienes ordenes esperando comprobante.")
        return

    for o in orders:
        await update.message.reply_text(
            f"\u23f3 Orden #{o.public_id} esperando comprobante de pago.\nSube la foto aqui."
        )


async def handle_admin_order_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    if not q:
        return

    if not _is_authorized(update):
        try:
            await q.answer("\u26d4 Acceso denegado.", show_alert=True)
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
                await q.answer("Accion solo valida en el grupo de verificacion de origen.", show_alert=True)
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
                await q.answer("\u2705 Origen confirmado" if ok else "\u26a0\ufe0f No pude actualizar estado", show_alert=not ok)
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
                    "\U0001f4e8 <b>ORDEN LISTA PARA PAGOS</b>\n\n"
                    f"\U0001f4e6 <b>#{public_id}</b>\n"
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
                        text="\U0001f464 <b>Datos Beneficiario:</b>\n" + esc_html(order.beneficiary_text or ""),
                        parse_mode="HTML",
                    )
            except Exception:
                logger.exception("orig_ok: fallo notificando a PAYMENTS para orden %s", public_id)

            return

        if action == "orig_rej":
            ok = cancel_order(public_id, "ORIGEN RECHAZADO")
            try:
                await q.answer("\u274c Origen rechazado" if ok else "\u26a0\ufe0f No pude cancelar", show_alert=not ok)
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
            await q.answer("\u2705 Marcada en Proceso")
            if ok:
                new_text = q.message.text + "\n\n\U0001f504 Estado: EN PROCESO"
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
                            text=f"\u23f3 Tu orden #{public_id} esta siendo procesada...",
                        )
                    except Exception:
                        pass
        return

    if action == "paid":
        already = list_orders_awaiting_paid_proof_by(getattr(update.effective_user, "id", 0) or 0, limit=2)
        if already and int(already[0].public_id) != int(public_id):
            try:
                await q.answer("\u26a0\ufe0f Ya tienes una orden en espera. Sube ese comprobante primero.", show_alert=True)
            except Exception:
                pass
            await q.message.reply_text(
                f"\u26a0\ufe0f Ya tienes una orden en espera de comprobante: #{int(already[0].public_id)}.\n"
                f"Cierra esa primero antes de marcar otra como PAGADA."
            )
            return

        ok = set_awaiting_paid_proof(
            public_id,
            by_telegram_user_id=getattr(update.effective_user, "id", None),
        )
        try:
            await q.answer("\U0001f4f8 Sube la foto" if ok else "\u274c No pude dejar la orden en espera")
        except Exception:
            pass

        await q.message.reply_text(
            f"\U0001f4f8 <b>PAGO ORDEN #{public_id}</b>\n"
            f"Envia la captura del pago aqui para cerrar la orden.\n\n"
            f"(Si el bot se reinicia, la orden seguira en espera en la DB.)",
            parse_mode="HTML"
        )
        return

    if action == "cancel":
        context.user_data["awaiting_cancel_reason_for"] = public_id
        try:
            await q.answer()
            await q.message.reply_text(f"\u270f\ufe0f Escribe el motivo de cancelacion para la #{public_id}:")
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
    Consulta precios ACTUALES de Binance para profit_real_usdt.
    Auto-crea trades BUY/SELL en order_trades para el backoffice.
    Operacion atomica: order(PAGADA/profit/awaiting) + trades + ledger + wallet en 1 transaccion.
    """
    if not _is_authorized(update):
        return

    if not update.message or not update.message.photo:
        return

    public_id = _pick_pending_order_id_from_db(update.effective_user.id)
    if not public_id:
        await update.message.reply_text("\u26a0\ufe0f No hay ordenes en espera de comprobante.")
        return

    proof_file_id = update.message.photo[-1].file_id

    try:
        order = get_order_by_public_id(public_id)
        if not order:
            await update.message.reply_text("\u274c Error: Orden no encontrada.")
            return

        # 1. Profit TEORICO (con tasa de cuando se creo la orden)
        rr = rates_repo.get_route_rate(
            rate_version_id=int(order.rate_version_id),
            origin_country=str(order.origin_country),
            dest_country=str(order.dest_country),
        )
        if not rr:
            await update.message.reply_text("\u274c No pude obtener route_rate para calcular profit.")
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
            profit_real = profit_usdt
            exec_buy = buy_origin_snapshot
            exec_sell = sell_dest_snapshot
            logger.warning(f"Orden #{public_id}: Binance no disponible, usando snapshot para profit_real")

        # Calcular USDT amounts para los trades
        usdt_buy = _q8(amount_origin / exec_buy)
        usdt_sell = _q8(payout_dest / exec_sell)
        origin_fiat = _get_fiat_currency(str(order.origin_country))
        dest_fiat = _get_fiat_currency(str(order.dest_country))

        # 3. Sponsor split (usa profit REAL para pagar al operador)
        sponsor_id = None
        try:
            with get_conn() as rconn:
                with rconn.cursor() as cur:
                    cur.execute("SELECT sponsor_id FROM users WHERE id=%s LIMIT 1;", (int(order.operator_user_id),))
                    row = cur.fetchone()
                    sponsor_id = int(row[0]) if row and row[0] is not None else None
        except Exception:
            sponsor_id = None

        profit_para_distribuir = profit_real

        if sponsor_id:
            op_share = _q8(profit_para_distribuir * Decimal("0.45"))
            sp_share = _q8(profit_para_distribuir * Decimal("0.10"))
            memo_op = "Profit orden (45%)"
            memo_sp = "Comision sponsor (10%)"
        else:
            op_share = _q8(profit_para_distribuir * Decimal("0.50"))
            sp_share = Decimal("0")
            memo_op = "Profit orden (50%)"
            memo_sp = None

        # 4. ATOMICO: order + profit + trades + ledger + wallet
        with get_conn() as conn:
            with conn.transaction():
                ok_paid = mark_order_paid_tx(conn, int(public_id), proof_file_id)
                if not ok_paid:
                    raise RuntimeError("No pude marcar la orden como PAGADA (tx)")

                ok_profit = set_profit_usdt_tx(conn, int(public_id), profit_usdt)
                if not ok_profit:
                    raise RuntimeError("No pude guardar profit_usdt (tx)")

                # Guardar datos de ejecucion real
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

                    # Auto-crear trade BUY (compra USDT con fiat origen)
                    cur.execute(
                        """
                        INSERT INTO order_trades
                            (order_public_id, side, fiat_currency, fiat_amount, price, usdt_amount, fee_usdt, source, note)
                        VALUES (%s, 'BUY', %s, %s, %s, %s, 0, 'binance_p2p_auto', 'Auto-generado al marcar PAGADA')
                        """,
                        (int(public_id), origin_fiat, amount_origin, exec_buy, usdt_buy)
                    )

                    # Auto-crear trade SELL (venta USDT por fiat destino)
                    cur.execute(
                        """
                        INSERT INTO order_trades
                            (order_public_id, side, fiat_currency, fiat_amount, price, usdt_amount, fee_usdt, source, note)
                        VALUES (%s, 'SELL', %s, %s, %s, %s, 0, 'binance_p2p_auto', 'Auto-generado al marcar PAGADA')
                        """,
                        (int(public_id), dest_fiat, payout_dest, exec_sell, usdt_sell)
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

        # 5. Confirmacion con ambos profits y trades
        diff = profit_real - profit_usdt
        diff_icon = "\U0001f4c8" if diff >= 0 else "\U0001f4c9"

        lines = [
            f"\u2705 <b>ORDEN #{public_id} CERRADA</b>",
            "",
            f"\U0001f4b0 Profit estimado: {profit_usdt:,.4f} USDT",
            f"\U0001f4b0 Profit real: {profit_real:,.4f} USDT",
            f"{diff_icon} Diferencia: {diff:,.4f} USDT",
            "",
            f"\U0001f4b1 BUY: {amount_origin:,.2f} {origin_fiat} @ {exec_buy:,.2f} = {usdt_buy:,.2f} USDT",
            f"\U0001f4b1 SELL: {payout_dest:,.2f} {dest_fiat} @ {exec_sell:,.2f} = {usdt_sell:,.2f} USDT",
            "",
            f"\U0001f464 Operador: {op_share:,.4f} USDT",
        ]
        if sponsor_id and sp_share != 0:
            lines.append(f"\U0001f91d Sponsor: {sp_share:,.4f} USDT")

        await update.message.reply_text("\n".join(lines), parse_mode="HTML")

    except Exception as e:
        logger.exception("process_paid_proof_photo: fallo cerrando orden %s: %s", public_id, e)
        await update.message.reply_text("\u274c Error interno cerrando la orden. Reintenta subiendo la foto nuevamente.")
        return

    # Notificacion operador (best-effort)
    op_tid = get_telegram_id_by_user_id(int(order.operator_user_id))
    if op_tid:
        try:
            await context.bot.send_message(
                chat_id=int(op_tid),
                text=f"\u2705 Orden #{public_id} PAGADA.\n\u00a1Gracias! \U0001f389",
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
        await update.message.reply_text(f"\u274c Orden #{public_id} cancelada.\nMotivo: {reason}")

        try:
            order = get_order_by_public_id(int(public_id))
            if order:
                op_tid = get_telegram_id_by_user_id(int(order.operator_user_id))
                if op_tid:
                    await context.bot.send_message(
                        chat_id=int(op_tid),
                        text=(
                            f"\u274c Orden #{public_id} CANCELADA\n"
                            f"Motivo: {reason}"
                        ),
                    )
        except Exception:
            logger.exception("cancel_order: no pude notificar al operador para orden %s", public_id)
    else:
        await update.message.reply_text("Error al cancelar.")
