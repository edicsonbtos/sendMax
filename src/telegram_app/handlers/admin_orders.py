from __future__ import annotations

import asyncio
import logging
import os
from decimal import ROUND_HALF_UP, Decimal

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from src.config.settings import settings
from src.db.connection import get_async_conn
from src.db.repositories import rates_repo
from src.db.repositories.orders_repo import (
    cancel_order,
    clear_awaiting_paid_proof_tx,
    get_order_by_public_id,
    list_orders_awaiting_paid_proof_by,
    list_orders_by_status,
    mark_order_paid_tx,
    mark_origin_verified_tx,
    set_awaiting_paid_proof,
    update_order_status,
)
from src.db.repositories.origin_wallet_repo import add_origin_receipt_daily
from src.db.repositories.users_repo import get_telegram_id_by_user_id
from src.db.repositories.wallet_repo import add_ledger_entry_tx
from src.integrations.binance_p2p import BinanceP2PClient
from src.integrations.p2p_config import COUNTRIES
from src.telegram_app.ui.routes_popular import format_rate_no_noise

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
                InlineKeyboardButton("⚙️ EN PROCESO", callback_data=f"ord:proc:{public_id}"),
                InlineKeyboardButton("✅ PAGADA", callback_data=f"ord:paid:{public_id}"),
            ],
            [InlineKeyboardButton("❌ CANCELAR", callback_data=f"ord:cancel:{public_id}")],
        ]
    )


async def _fetch_realtime_prices(origin_country: str, dest_country: str):
    """Consulta precios actuales de Binance P2P (ASYNC) para calcular profit real"""
    origin_cfg = COUNTRIES.get(origin_country)
    dest_cfg = COUNTRIES.get(dest_country)

    if not origin_cfg or not dest_cfg:
        return None, None

    client = BinanceP2PClient()
    try:
        buy_quote = await client.fetch_first_price(
            fiat=origin_cfg.fiat,
            trade_type="BUY",
            pay_methods=origin_cfg.buy_methods,
            trans_amount=origin_cfg.trans_amount,
        )
        sell_quote = await client.fetch_first_price(
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
        await client.close()


def _get_fiat_currency(country: str) -> str:
    """Obtiene la moneda fiat de un pais"""
    return ORIGIN_FIAT_CURRENCY.get(country, country)


async def admin_orders(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_authorized(update):
        return

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    try:
        orders = await asyncio.wait_for(list_orders_by_status("CREADA", limit=10), timeout=5.0)
    except asyncio.TimeoutError:
        await update.message.reply_text("⏳ La base de datos está tardando demasiado. Reintenta en unos segundos.")
        return

    if not orders:
        await update.message.reply_text("📨 No hay ordenes pendientes por procesar.")
        return

    await update.message.reply_text(
        f"📋 <b>Ordenes Pendientes ({len(orders)})</b>\nToca una accion ⬇️",
        parse_mode="HTML"
    )

    for o in orders:
        text = (
            f"📦 <b>#{o.public_id}</b>\n"
            f"🌎 {o.origin_country} -> {o.dest_country}\n"
            f"💵 Recibe: {o.amount_origin}\n"
            f"💰 Payout: {o.payout_dest:,.2f}\n"
        )
        await update.message.reply_text(text, reply_markup=_order_actions_kb(o.public_id), parse_mode="HTML")


async def admin_awaiting_paid(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_authorized(update):
        return

    try:
        orders = await asyncio.wait_for(list_orders_awaiting_paid_proof_by(update.effective_user.id, limit=5), timeout=5.0)
    except asyncio.TimeoutError:
        await update.message.reply_text("⏳ Timeout DB. Reintenta.")
        return

    if not orders:
        await update.message.reply_text("No tienes ordenes esperando comprobante.")
        return

    for o in orders:
        await update.message.reply_text(
            f"⏳ Orden #{o.public_id} esperando comprobante de pago.\nSube la foto aqui."
        )


async def handle_admin_order_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    if not q:
        return

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    # Mantenemos el answer() lo más arriba posible para evitar lag UI
    if not _is_authorized(update):
        try:
            await q.answer("⛔ No tienes permiso para esta acción.", show_alert=True)
        except Exception:
            pass
        return

    try:
        await q.answer()
    except Exception:
        pass

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
    if action in ("orig_ok", "orig_rej", "orig_rej_confirm", "orig_rej_cancel"):
        chat_id = getattr(update.effective_chat, "id", None)
        if str(chat_id) != str(settings.ORIGIN_REVIEW_TELEGRAM_CHAT_ID):
            try:
                await q.answer("Accion solo valida en el grupo de verificacion de origen.", show_alert=True)
            except Exception:
                pass
            return

        order = await get_order_by_public_id(public_id)
        if not order:
            try:
                await q.answer("Orden no encontrada.", show_alert=True)
            except Exception:
                pass
            return

        if action == "orig_ok":
            # MEJORA 1: Prevenir doble confirmación (Pre-check)
            if order.status == "ORIGEN_CONFIRMADO":
                try:
                    await q.answer("⚠️ Este origen ya fue confirmado anteriormente", show_alert=True)
                    await q.edit_message_text(
                        q.message.text + "\n\n✅ Origen ya confirmado (anteriormente)",
                        reply_markup=None,
                        parse_mode="HTML"
                    )
                except Exception:
                    pass
                return

            try:
                from datetime import datetime, timedelta, timezone
                from src.db.repositories.origin_wallet_repo import add_origin_receipt_ledger_tx, add_origin_receipt_daily_tx
                VET = timezone(timedelta(hours=-4))
                day_vet = datetime.now(tz=timezone.utc).astimezone(VET).date()
                fiat_currency = ORIGIN_FIAT_CURRENCY.get(str(order.origin_country), str(order.origin_country))

                async with get_async_conn() as conn:
                    async with conn.transaction():
                        # 1. Confirmar orden (Atómico)
                        ok = await mark_origin_verified_tx(
                            conn,
                            public_id,
                            by_telegram_user_id=getattr(update.effective_user, "id", None),
                            by_name=(getattr(update.effective_user, "full_name", None) or getattr(update.effective_user, "username", None)),
                        )

                        if not ok:
                            # Si no se actualizó, pudo ser por cambio de estado concurrente
                            raise RuntimeError("No se pudo actualizar el estado de la orden (ya confirmada o cancelada)")

                        # 2. Registrar ingreso contable (Atómico)
                        inserted = await add_origin_receipt_ledger_tx(
                            conn,
                            ref_order_public_id=int(public_id),
                            day=day_vet,
                            origin_country=str(order.origin_country),
                            fiat_currency=str(fiat_currency),
                            amount_fiat=Decimal(str(order.amount_origin)),
                            approved_by_telegram_id=getattr(update.effective_user, "id", None),
                            approved_note=f"ORIGEN OK por {(getattr(update.effective_user, 'full_name', None) or getattr(update.effective_user, 'username', None) or 'operador')}",
                        )

                        if inserted:
                            await add_origin_receipt_daily_tx(
                                conn,
                                day=day_vet,
                                origin_country=str(order.origin_country),
                                fiat_currency=str(fiat_currency),
                                amount_fiat=Decimal(str(order.amount_origin)),
                                approved_by_telegram_id=getattr(update.effective_user, "id", None),
                                approved_note=f"Agregado desde orden #{public_id}",
                                ref_order_public_id=int(public_id),
                            )

                # Si llegamos aquí, la transacción fue exitosa
                try:
                    await q.edit_message_text(
                        q.message.text + "\n\n✅ Origen confirmado",
                        reply_markup=None,
                        parse_mode="HTML"
                    )
                    await q.answer("✅ Origen confirmado")
                except Exception:
                    pass

                # Notificación al operador
                op_tid = await get_telegram_id_by_user_id(int(order.operator_user_id))
                if op_tid:
                    try:
                        await context.bot.send_message(
                            chat_id=int(op_tid),
                            text=f"✅ Origen confirmado para orden #{public_id}",
                        )
                    except Exception:
                        pass

            except Exception as e:
                logger.exception("orig_ok: fallo atómico en orden %s: %s", public_id, e)
                try:
                    await q.answer("❌ Error al confirmar origen. Reintenta.", show_alert=True)
                except Exception:
                    pass
                return

            try:
                target_chat_id = int(settings.PAYMENTS_TELEGRAM_CHAT_ID)
                origin = str(order.origin_country)
                dest = str(order.dest_country)

                summary = (
                    "📧 <b>ORDEN LISTA PARA PAGOS</b>\n\n"
                    f"📦 <b>#{public_id}</b>\n"
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
                        text="👤 <b>Datos Beneficiario:</b>\n" + esc_html(order.beneficiary_text or ""),
                        parse_mode="HTML",
                    )
            except Exception:
                logger.exception("orig_ok: fallo notificando a PAYMENTS para orden %s", public_id)

            return

        if action == "orig_rej":
            # MEJORA 2: Confirmación antes de rechazar
            kb = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("✅ Sí, rechazar origen", callback_data=f"ord:orig_rej_confirm:{public_id}"),
                    InlineKeyboardButton("❌ No, cancelar", callback_data=f"ord:orig_rej_cancel:{public_id}"),
                ]
            ])
            try:
                await q.edit_message_text(
                    q.message.text + f"\n\n⚠️ ¿Estás seguro de rechazar el origen de la orden #{public_id}?",
                    reply_markup=kb,
                    parse_mode="HTML"
                )
            except Exception:
                pass
            return

        if action == "orig_rej_confirm":
            ok = await cancel_order(public_id, "ORIGEN RECHAZADO")
            try:
                await q.answer("❌ Origen rechazado" if ok else "⚠️ No pude cancelar", show_alert=not ok)
                if ok:
                    await q.edit_message_text(
                        q.message.text + "\n\n❌ Origen RECHAZADO y orden cancelada",
                        reply_markup=None,
                        parse_mode="HTML"
                    )
                    # Notificar operador
                    op_tid = await get_telegram_id_by_user_id(int(order.operator_user_id))
                    if op_tid:
                        try:
                            await context.bot.send_message(
                                chat_id=int(op_tid),
                                text=f"❌ Tu orden #{public_id} fue cancelada por ORIGEN RECHAZADO.",
                            )
                        except Exception:
                            pass
            except Exception:
                pass
            return

        if action == "orig_rej_cancel":
            # Volver al estado anterior
            kb = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("✅ ORIGEN RECIBIDO", callback_data=f"ord:orig_ok:{public_id}"),
                    InlineKeyboardButton("❌ ORIGEN RECHAZADO", callback_data=f"ord:orig_rej:{public_id}"),
                ]
            ])
            try:
                # Limpiar la pregunta de confirmación
                clean_text = q.message.text.split("\n\n⚠️ ¿Estás seguro")[0]
                await q.edit_message_text(clean_text, reply_markup=kb, parse_mode="HTML")
            except Exception:
                pass
            return

    if action == "proc":
        ok = await update_order_status(public_id, "EN_PROCESO")
        try:
            await q.answer("✅ Marcada en Proceso")
            if ok:
                new_text = q.message.text + "\n\n🔄 Estado: EN PROCESO"
                await q.edit_message_text(new_text, reply_markup=_order_actions_kb(public_id))
        except Exception:
            pass

        if ok:
            order = await get_order_by_public_id(public_id)
            if order:
                op_tid = await get_telegram_id_by_user_id(int(order.operator_user_id))
                if op_tid:
                    try:
                        await context.bot.send_message(
                            chat_id=int(op_tid),
                            text=f"⏳ Tu orden #{public_id} esta siendo procesada...",
                        )
                    except Exception:
                        pass
        return

    if action == "paid":
        max_pending = int(os.environ.get("ADMIN_MAX_PENDING_PROOFS", 10))
        already = await list_orders_awaiting_paid_proof_by(getattr(update.effective_user, "id", 0) or 0, limit=max_pending + 1)

        is_already_pending = any(int(o.public_id) == int(public_id) for o in already)

        if not is_already_pending and len(already) >= max_pending:
            try:
                await q.answer(f"⚠️ Límite de {max_pending} órdenes en espera alcanzado.", show_alert=True)
            except Exception:
                pass
            await q.message.reply_text(
                f"⚠️ Tienes demasiadas órdenes en espera ({len(already)}). "
                "Sube los comprobantes de las anteriores antes de marcar más."
            )
            return

        ok = await set_awaiting_paid_proof(
            public_id,
            by_telegram_user_id=getattr(update.effective_user, "id", None),
        )
        if ok:
            context.user_data["active_paid_order_id"] = public_id

        try:
            await q.answer("📸 Sube la foto" if ok else "❌ No pude dejar la orden en espera")
        except Exception:
            pass

        await q.message.reply_text(
            f"📸 <b>PAGO ORDEN #{public_id}</b>\n"
            f"Envia la captura del pago aqui para cerrar la orden.\n\n"
            f"<i>(Se asociará a esta orden por ser la última en la que tocaste PAGADA)</i>",
            parse_mode="HTML"
        )
        return

    if action == "cancel":
        context.user_data["awaiting_cancel_reason_for"] = public_id
        try:
            await q.answer()
            await q.message.reply_text(f"🖋️ Escribe el motivo de cancelacion para la #{public_id}:")
        except Exception:
            pass
        return


async def _pick_pending_order_id_from_db(by_telegram_user_id: int) -> int | None:
    pending = await list_orders_awaiting_paid_proof_by(by_telegram_user_id, limit=1)
    if not pending:
        return None
    return int(pending[0].public_id)


async def process_paid_proof_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Cierre de orden con comprobante de pago destino.
    """
    if not _is_authorized(update):
        return

    if not update.message or not update.message.photo:
        return

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

    # Intentar obtener de context (lo más reciente que tocó el admin)
    public_id = context.user_data.get("active_paid_order_id")

    # Verificar que esa orden realmente esté esperando comprobante
    if public_id:
        order_check = await get_order_by_public_id(public_id)
        if not order_check or not getattr(order_check, "awaiting_paid_proof", False):
            public_id = None # No es válida o ya se cerró
            context.user_data.pop("active_paid_order_id", None)

    # Si no hay en context o no era válida, buscar la más antigua en DB
    if not public_id:
        public_id = await _pick_pending_order_id_from_db(update.effective_user.id)

    if not public_id:
        await update.message.reply_text("⚠️ No hay ordenes en espera de comprobante para ti.")
        return

    proof_file_id = update.message.photo[-1].file_id

    try:
        order = await get_order_by_public_id(public_id)
        if not order:
            await update.message.reply_text("❌ Error: Orden no encontrada.")
            return

        if order.status != "EN_PROCESO":
            await update.message.reply_text("ℹ️ Esta orden ya fue gestionada previamente por otro administrador o su estado cambió.")
            return

        # 1. Profit TEORICO
        rr = await rates_repo.get_route_rate(
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

        # 2. Profit REAL (ASYNC)
        exec_buy, exec_sell = await _fetch_realtime_prices(
            str(order.origin_country),
            str(order.dest_country)
        )

        if exec_buy and exec_sell:
            profit_real = _q8((amount_origin / exec_buy) - (payout_dest / exec_sell))
        else:
            profit_real = profit_usdt
            exec_buy = buy_origin_snapshot
            exec_sell = sell_dest_snapshot

        usdt_buy = _q8(amount_origin / exec_buy)
        usdt_sell = _q8(payout_dest / exec_sell)
        origin_fiat = _get_fiat_currency(str(order.origin_country))
        dest_fiat = _get_fiat_currency(str(order.dest_country))

        # 3. Sponsor split
        sponsor_id = None
        try:
            async with get_async_conn() as rconn:
                async with rconn.cursor() as cur:
                    await cur.execute("SELECT sponsor_id FROM users WHERE id=%s LIMIT 1;", (int(order.operator_user_id),))
                    rows = await cur.fetchall()
                    row = rows[0] if rows else None
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

        # 4. ATOMICO
        async with get_async_conn() as conn:
            async with conn.transaction():
                ok_paid = await mark_order_paid_tx(conn, int(public_id), proof_file_id)
                if not ok_paid:
                    raise RuntimeError("No pude marcar la orden como COMPLETADA (tx)")

                # Guardar datos de ejecucion real
                async with conn.cursor() as cur:
                    await cur.execute(
                        """
                        UPDATE orders
                        SET execution_price_buy = %s,
                            execution_price_sell = %s,
                            profit_real_usdt = %s,
                            profit_usdt = %s,
                            updated_at = now()
                        WHERE public_id = %s
                        """,
                        (exec_buy, exec_sell, profit_real, profit_usdt, int(public_id))
                    )

                    await cur.execute(
                        """
                        INSERT INTO order_trades
                            (order_public_id, side, fiat_currency, fiat_amount, price, usdt_amount, fee_usdt, source, note)
                        VALUES (%s, 'BUY', %s, %s, %s, %s, 0, 'binance_p2p_auto', 'Auto-generado al completar orden')
                        """,
                        (int(public_id), origin_fiat, amount_origin, exec_buy, usdt_buy)
                    )

                    await cur.execute(
                        """
                        INSERT INTO order_trades
                            (order_public_id, side, fiat_currency, fiat_amount, price, usdt_amount, fee_usdt, source, note)
                        VALUES (%s, 'SELL', %s, %s, %s, %s, 0, 'binance_p2p_auto', 'Auto-generado al completar orden')
                        """,
                        (int(public_id), dest_fiat, payout_dest, exec_sell, usdt_sell)
                    )

                if op_share != 0:
                    await add_ledger_entry_tx(
                        conn,
                        user_id=int(order.operator_user_id),
                        amount_usdt=op_share,
                        entry_type="ORDER_PROFIT",
                        ref_order_public_id=int(public_id),
                        memo=memo_op,
                        idempotency=True,
                    )

                if sponsor_id and sp_share != 0:
                    await add_ledger_entry_tx(
                        conn,
                        user_id=int(sponsor_id),
                        amount_usdt=sp_share,
                        entry_type="SPONSOR_COMMISSION",
                        ref_order_public_id=int(public_id),
                        memo=memo_sp,
                        idempotency=True,
                    )

                await clear_awaiting_paid_proof_tx(conn, int(public_id))

        # Limpiar context
        if context.user_data.get("active_paid_order_id") == public_id:
            context.user_data.pop("active_paid_order_id", None)

        # 5. Confirmacion
        diff = profit_real - profit_usdt
        diff_icon = "📈" if diff >= 0 else "📉"

        lines = [
            f"✅ <b>ORDEN #{public_id} CERRADA</b>",
            "",
            f"💰 Profit estimado: {profit_usdt:,.4f} USDT",
            f"💰 Profit real: {profit_real:,.4f} USDT",
            f"{diff_icon} Diferencia: {diff:,.4f} USDT",
            "",
            f"💱 BUY: {amount_origin:,.2f} {origin_fiat} @ {exec_buy:,.2f} = {usdt_buy:,.2f} USDT",
            f"💱 SELL: {payout_dest:,.2f} {dest_fiat} @ {exec_sell:,.2f} = {usdt_sell:,.2f} USDT",
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

    # Notificacion operador (MEJORA 3)
    op_tid = await get_telegram_id_by_user_id(int(order.operator_user_id))
    if op_tid:
        try:
            await context.bot.send_message(
                chat_id=int(op_tid),
                text=f"💰 Pago confirmado para orden #{public_id}\n¡Gracias! 🎉",
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

    ok = await cancel_order(int(public_id), reason)
    context.user_data.pop("awaiting_cancel_reason_for", None)

    if ok:
        await update.message.reply_text(f"❌ Orden #{public_id} cancelada.\nMotivo: {reason}")

        try:
            order = await get_order_by_public_id(int(public_id))
            if order:
                op_tid = await get_telegram_id_by_user_id(int(order.operator_user_id))
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
