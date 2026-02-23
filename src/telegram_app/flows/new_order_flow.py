from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    Update,
)
from telegram.ext import (
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from src.config.settings import settings
from src.db.connection import get_async_conn
from src.db.repositories.orders_repo import (
    create_order_tx,
    update_order_status_tx,
)
from src.db.repositories.rates_repo import (
    get_latest_active_rate_version,
    get_route_rate,
)
from src.db.repositories.users_repo import get_user_by_telegram_id
from src.telegram_app.handlers.panic import MENU_BUTTONS_REGEX, panic_handler
from src.telegram_app.ui.labels import BTN_NEW_ORDER
from src.telegram_app.ui.routes_popular import (
    COUNTRY_FLAGS,
    COUNTRY_LABELS,
    format_rate_no_noise,
)
from src.telegram_app.utils.text_escape import esc_html

logger = logging.getLogger(__name__)

"""
Flujo: 📤 Nuevo envío (PRO)  FIAT -> FIAT (coherente con profit puente)

Regla de negocio (unit consistency):
- orders.amount_origin = FIAT del país de origen
- orders.payout_dest   = FIAT del país de destino
- route_rates.rate_client = (FIAT_dest / FIAT_origin) ya incluye comisión
- profit_usdt se calcula al pagar con snapshot:
    (amount_origin / buy_origin) - (payout_dest / sell_dest)

UX:
- Pantalla única (edit_message_text) best-effort
- Aislamiento con context.user_data["order_mode"]=True
"""

# Estados
ASK_ORIGIN, ASK_DEST, ASK_AMOUNT, ASK_BENEF, ASK_PROOF, ASK_CONFIRM, ASK_EDIT, ASK_EDIT_FIELD = range(8)

# Botones
BTN_CANCEL = "Cancelar"
BTN_CONFIRM = "Confirmar ✅"
BTN_EDIT = "Editar ✏️"
BTN_EDIT_AMOUNT = "Editar monto"
BTN_EDIT_BENEF = "Editar beneficiario"
BTN_BACK = "Volver"
BTN_CONTINUE = "Continuar ➡️"
BTN_KEEP_EDITING = "Seguir editando 🔄"


def _flow_dbg(msg: str) -> None:
    if getattr(settings, "FLOW_DEBUG", 0):
        logger.info(f"[FLOW][new_order] {msg}")


def _fmt_money(x: Decimal) -> str:
    q = Decimal(str(x)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    s = format(q, "f")
    whole, frac = s.split(".")
    parts = []
    while whole:
        parts.append(whole[-3:])
        whole = whole[:-3]
    return f"{'.'.join(reversed(parts))},{frac}"


def _fmt_rate(x: Decimal) -> str:
    return format_rate_no_noise(Decimal(str(x)))


def _fmt_public_id(public_id: int) -> str:
    year = datetime.now().year
    return f"{year}-{public_id:06d}"


def _country_keyboard() -> ReplyKeyboardMarkup:
    rows = []
    for code in ["USA", "CHILE", "PERU", "COLOMBIA", "VENEZUELA", "MEXICO", "ARGENTINA"]:
        rows.append([KeyboardButton(f"{COUNTRY_FLAGS[code]} {COUNTRY_LABELS[code]}")])
    return ReplyKeyboardMarkup(rows, resize_keyboard=True, one_time_keyboard=True)


def _cancel_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup([[KeyboardButton(BTN_CANCEL)]], resize_keyboard=True, one_time_keyboard=True)


def _confirm_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [[KeyboardButton(BTN_CONFIRM)], [KeyboardButton(BTN_EDIT)], [KeyboardButton(BTN_CANCEL)]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def _edit_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton(BTN_EDIT_AMOUNT)],
            [KeyboardButton(BTN_EDIT_BENEF)],
            [KeyboardButton(BTN_BACK)],
            [KeyboardButton(BTN_CANCEL)],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def _after_edit_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [[KeyboardButton(BTN_CONTINUE)], [KeyboardButton(BTN_KEEP_EDITING)], [KeyboardButton(BTN_CANCEL)]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def _parse_country(text: str) -> str | None:
    t = (text or "").strip()
    for code, label in COUNTRY_LABELS.items():
        if t == f"{COUNTRY_FLAGS[code]} {label}":
            return code
    return None



async def _screen_send_or_edit(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    text: str,
    *,
    reply_markup=None,
    parse_mode: str | None = None,
) -> int:
    chat_id = update.effective_chat.id
    screen_id = context.user_data.get("screen_message_id")
    is_reply_kb = isinstance(reply_markup, ReplyKeyboardMarkup)

    if screen_id and not is_reply_kb:
        try:
            await context.bot.edit_message_text(
                chat_id=chat_id,
                message_id=screen_id,
                text=text,
                reply_markup=reply_markup,
                parse_mode=parse_mode,
                disable_web_page_preview=True,
            )
            return screen_id
        except Exception as e:
            logger.warning("edit_message_text fall (screen_id=%s): %s", screen_id, e)
            await _best_effort_delete(update, context, screen_id)
            context.user_data.pop("screen_message_id", None)

    if screen_id and is_reply_kb:
        await _best_effort_delete(update, context, screen_id)
        context.user_data.pop("screen_message_id", None)

    msg = await context.bot.send_message(
        chat_id=chat_id,
        text=text,
        reply_markup=reply_markup,
        parse_mode=parse_mode,
        disable_web_page_preview=True,
    )
    context.user_data["screen_message_id"] = msg.message_id
    return msg.message_id


async def _best_effort_delete(update: Update, context: ContextTypes.DEFAULT_TYPE, message_id: int) -> None:
    try:
        await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=message_id)
    except Exception:
        pass


def _reset_flow_memory(context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data.pop("order", None)
    context.user_data.pop("edit_target", None)
    context.user_data.pop("screen_message_id", None)
    context.user_data.pop("order_mode", None)


def _build_summary_text(order: dict, rr) -> str:
    origin = order["origin"]
    dest = order["dest"]

    amount_fiat: Decimal = order["amount_origin"]  # FIAT origen
    beneficiary_text: str = order["beneficiary_text"]

    payout_dest = (amount_fiat * rr.rate_client)

    benef_short = (beneficiary_text or "").strip()
    if len(benef_short) > 260:
        benef_short = benef_short[:260].rstrip() + "..."

    comm = Decimal(str(settings.commission_pct(origin, dest)))

    return (
        "Listo ✅ Revisa tu envío:\n\n"
        f"Ruta: {COUNTRY_FLAGS[origin]} {COUNTRY_LABELS[origin]} -> {COUNTRY_FLAGS[dest]} {COUNTRY_LABELS[dest]}\n"
        f"Monto (origen): {_fmt_money(amount_fiat)} {origin}\n"
        f"Tasa: {_fmt_rate(rr.rate_client)}\n"
        f"Comisión: {_fmt_money(comm)}%\n"
        f"Recibe aprox (destino): {_fmt_money(payout_dest)} {dest}\n\n"
        "Beneficiario:\n"
        f"{benef_short}\n\n"
        "¿Confirmamos?"
    )


async def _notify_admin_new_order(context: ContextTypes.DEFAULT_TYPE, order) -> None:
    target_chat_id = settings.ORIGIN_REVIEW_TELEGRAM_CHAT_ID or settings.ADMIN_TELEGRAM_USER_ID
    if not target_chat_id:
        return
    target_chat_id = int(target_chat_id)

    origin = order.origin_country
    dest = order.dest_country

    summary = (
        "📦 <b>NUEVA ORDEN</b>\n\n"
        f"🆔 <b>#{_fmt_public_id(order.public_id)}</b>\n"
        f"Ruta: {COUNTRY_FLAGS[origin]} {COUNTRY_LABELS[origin]} -> {COUNTRY_FLAGS[dest]} {COUNTRY_LABELS[dest]}\n"
        f"Monto Origen: <b>{_fmt_money(order.amount_origin)} {origin}</b>\n"
        f"Tasa: {_fmt_rate(order.rate_client)}\n"
        f"Pago Destino: <b>{_fmt_money(order.payout_dest)} {dest}</b>\n"
        f"Estado: {order.status}"
    )

    kb = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("✅ ORIGEN RECIBIDO", callback_data=f"ord:orig_ok:{order.public_id}"),
                InlineKeyboardButton("❌ ORIGEN RECHAZADO", callback_data=f"ord:orig_rej:{order.public_id}"),
            ]
        ]
    )

    await context.bot.send_message(
        chat_id=target_chat_id,
        text=summary,
        parse_mode="HTML",
        reply_markup=kb,
        disable_web_page_preview=True,
    )

    if (order.beneficiary_text or "").strip():
        await context.bot.send_message(
            chat_id=target_chat_id,
            text="👤 <b>Datos Beneficiario:</b>\n" + esc_html(order.beneficiary_text or ""),
            parse_mode="HTML",
        )

    if order.origin_payment_proof_file_id:
        await context.bot.send_photo(
            chat_id=target_chat_id,
            photo=order.origin_payment_proof_file_id,
            caption=f"📄 Comprobante Origen #{_fmt_public_id(order.public_id)}",
        )


async def entry_from_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    # Lock: evita doble inicio por spam
    if context.user_data.get("order_mode"):
        await update.message.reply_text("⏳ Ya tienes un envío en curso. Si deseas salir, escribe Cancelar.")
        return ASK_ORIGIN
    context.user_data["order_mode"] = True
    context.user_data["order"] = {}
    context.user_data.pop("edit_target", None)
    context.user_data.pop("screen_message_id", None)

    await _screen_send_or_edit(
        update,
        context,
        "📤 Nuevo envío\n\nElige el país de *origen*:",
        reply_markup=_country_keyboard(),
        parse_mode="Markdown",
    )
    return ASK_ORIGIN


async def receive_origin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    code = _parse_country(update.message.text)
    if not code:
        await _screen_send_or_edit(update, context, "Selecciona un país usando los botones 👇", reply_markup=_country_keyboard())
        return ASK_ORIGIN

    context.user_data["order"]["origin"] = code

    await _screen_send_or_edit(
        update,
        context,
        "Perfecto ✅ Ahora elige el país de *destino*:",
        reply_markup=_country_keyboard(),
        parse_mode="Markdown",
    )
    return ASK_DEST


async def receive_dest(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    code = _parse_country(update.message.text)
    if not code:
        await _screen_send_or_edit(update, context, "Selecciona un país usando los botones 👇", reply_markup=_country_keyboard())
        return ASK_DEST

    origin = context.user_data["order"].get("origin")
    if code == origin:
        await _screen_send_or_edit(update, context, "Esa ruta no es válida. Elige un destino diferente 👇", reply_markup=_country_keyboard())
        return ASK_DEST

    context.user_data["order"]["dest"] = code

    await _screen_send_or_edit(
        update,
        context,
        f"Escribe el *monto exacto* en {origin} (ej: 10000):",
        reply_markup=_cancel_keyboard(),
        parse_mode="Markdown",
    )
    return ASK_AMOUNT


async def receive_amount(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = (update.message.text or "").strip()

    if text.lower() == BTN_CANCEL.lower():
        await _screen_send_or_edit(update, context, "Listo, cancelado ✅")
        _reset_flow_memory(context)
        return ConversationHandler.END

    try:
        amount = Decimal(text.replace(",", "."))
        if amount <= 0:
            raise InvalidOperation()
    except Exception:
        await _screen_send_or_edit(update, context, "Monto inválido. Escribe solo el número (ej: 10000).", reply_markup=_cancel_keyboard())
        return ASK_AMOUNT

    await _best_effort_delete(update, context, update.message.message_id)

    context.user_data["order"]["amount_origin"] = amount  # FIAT origen

    edit_target = context.user_data.get("edit_target")
    if edit_target == "amount":
        context.user_data.pop("edit_target", None)
        await _screen_send_or_edit(update, context, "Listo ✅ ¿Quieres seguir editando o continuar?", reply_markup=_after_edit_keyboard())
        return ASK_EDIT_FIELD

    await _screen_send_or_edit(
        update,
        context,
        "Perfecto ✅ Ahora pega los *datos del beneficiario* (como lo enviaras por WhatsApp).\n\n"
        "Incluye al menos:\n"
        " Nombre\n"
        " Cédula\n"
        " N cuenta\n"
        " Tipo\n\n"
        "Envíalo en un solo mensaje.",
        reply_markup=_cancel_keyboard(),
        parse_mode="Markdown",
    )
    return ASK_BENEF


async def receive_benef(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message and (update.message.photo or update.message.document):
        await _screen_send_or_edit(
            update,
            context,
            "⚠️ Recibí una imagen, pero primero necesito que escribas los datos solicitados en texto. Por favor, ingrésalos para continuar.",
            reply_markup=_cancel_keyboard(),
        )
        return ASK_BENEF

    text = (update.message.text or "").strip()

    if text.lower() == BTN_CANCEL.lower():
        await _screen_send_or_edit(update, context, "Listo, cancelado ✅")
        _reset_flow_memory(context)
        return ConversationHandler.END

    if len(text) < 10:
        await _screen_send_or_edit(update, context, "Parece muy corto. Pega los datos completos, por favor.", reply_markup=_cancel_keyboard())
        return ASK_BENEF

    await _best_effort_delete(update, context, update.message.message_id)

    edit_target = context.user_data.get("edit_target")
    if edit_target == "beneficiary":
        context.user_data["order"]["beneficiary_text"] = text
        context.user_data.pop("edit_target", None)
        await _screen_send_or_edit(update, context, "Perfecto ✅ ¿Quieres seguir editando o continuar?", reply_markup=_after_edit_keyboard())
        return ASK_EDIT_FIELD

    context.user_data["order"]["beneficiary_text"] = text

    await _screen_send_or_edit(
        update,
        context,
        "Excelente ✅ Ahora envía el *comprobante de pago* en foto.",
        reply_markup=_cancel_keyboard(),
        parse_mode="Markdown",
    )
    return ASK_PROOF


async def receive_proof(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # Caso: Llega texto en lugar de foto
    if update.message and update.message.text:
        if update.message.text.lower() == BTN_CANCEL.lower():
            await _screen_send_or_edit(update, context, "Listo, cancelado ✅")
            _reset_flow_memory(context)
            return ConversationHandler.END

        await _screen_send_or_edit(
            update,
            context,
            "⚠️ Por favor, adjunta la foto o captura del comprobante de pago para poder finalizar tu orden.",
            reply_markup=_cancel_keyboard(),
        )
        return ASK_PROOF

    # Acepta comprobante como FOTO o como DOCUMENTO (imagen/archivo)
    file_id = None
    if update.message and update.message.photo:
        file_id = update.message.photo[-1].file_id
    elif update.message and update.message.document:
        file_id = update.message.document.file_id

    if not file_id:
        await _screen_send_or_edit(
            update,
            context,
            "⚠️ Por favor, adjunta la foto o captura del comprobante de pago para poder finalizar tu orden.",
            reply_markup=_cancel_keyboard()
        )
        return ASK_PROOF
    context.user_data["order"]["proof_file_id"] = file_id
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

    try:
        rv = await asyncio.wait_for(get_latest_active_rate_version(), timeout=5.0)
    except asyncio.TimeoutError:
        await _screen_send_or_edit(update, context, "⏳ Error de conexión. Reintenta en un momento.")
        return ASK_PROOF

    if not rv:
        await _screen_send_or_edit(update, context, "No tengo tasas activas ahora mismo. Intenta de nuevo en unos minutos.")
        _reset_flow_memory(context)
        return ConversationHandler.END

    origin = context.user_data["order"]["origin"]
    dest = context.user_data["order"]["dest"]

    rr = await get_route_rate(rate_version_id=rv.id, origin_country=origin, dest_country=dest)
    if not rr:
        await _screen_send_or_edit(update, context, "Esa ruta no está disponible ahora mismo. Intenta otra ruta.")
        _reset_flow_memory(context)
        return ConversationHandler.END

    context.user_data["order"]["rate_version_id"] = rv.id
    context.user_data["order"]["rate_client"] = rr.rate_client
    context.user_data["order"]["commission_pct"] = Decimal(str(settings.commission_pct(origin, dest)))

    summary = _build_summary_text(context.user_data["order"], rr)
    await _screen_send_or_edit(update, context, summary, reply_markup=_confirm_keyboard())
    return ASK_CONFIRM


async def _show_confirm_screen(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    order_data = context.user_data.get("order") or {}
    rv_id = order_data.get("rate_version_id")
    origin = order_data.get("origin")
    dest = order_data.get("dest")

    rr = await get_route_rate(rate_version_id=rv_id, origin_country=origin, dest_country=dest)
    if not rr:
        await _screen_send_or_edit(update, context, "No pude reconstruir la ruta ahora mismo. Intenta de nuevo.")
        _reset_flow_memory(context)
        return ConversationHandler.END

    summary = _build_summary_text(order_data, rr)
    await _screen_send_or_edit(update, context, summary, reply_markup=_confirm_keyboard())
    return ASK_CONFIRM


async def receive_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = (update.message.text or "").strip()

    if text.lower() == BTN_CANCEL.lower():
        await _screen_send_or_edit(update, context, "Envío cancelado ✅")
        _reset_flow_memory(context)
        return ConversationHandler.END

    if text == BTN_EDIT:
        await _screen_send_or_edit(update, context, "¿Qué quieres editar?", reply_markup=_edit_keyboard())
        return ASK_EDIT

    if text != BTN_CONFIRM:
        await _screen_send_or_edit(update, context, "Selecciona una opción usando los botones 👇", reply_markup=_confirm_keyboard())
        return ASK_CONFIRM

    telegram_id = update.effective_user.id
    user = await get_user_by_telegram_id(telegram_id)
    if not user:
        await _screen_send_or_edit(update, context, "No estás registrado. Escribe /start para registrarte.")
        _reset_flow_memory(context)
        return ConversationHandler.END

    order_data = context.user_data.get("order") or {}

    origin = order_data["origin"]
    dest = order_data["dest"]
    amount_origin: Decimal = order_data["amount_origin"]  # FIAT origen
    beneficiary_text = order_data["beneficiary_text"]
    file_id = order_data["proof_file_id"]
    rate_version_id = order_data["rate_version_id"]
    rate_client = order_data["rate_client"]
    commission_pct = Decimal(str(settings.commission_pct(origin, dest)))

    payout_dest = (amount_origin * rate_client)
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

    order = None
    try:
        async with get_async_conn() as conn:
            async with conn.transaction():
                # 1. Crear orden (nace como CREADA en DB por defecto)
                order = await create_order_tx(
                    conn,
                    operator_user_id=user.id,
                    origin_country=origin,
                    dest_country=dest,
                    amount_origin=amount_origin,
                    rate_version_id=rate_version_id,
                    commission_pct=commission_pct,
                    rate_client=rate_client,
                    payout_dest=payout_dest,
                    beneficiary_text=beneficiary_text,
                    origin_payment_proof_file_id=file_id,
                    initial_status="CREADA",
                )

                # 2. Cambiar estado inmediatamente (Atómico)
                await update_order_status_tx(conn, int(order.public_id), "ORIGEN_VERIFICANDO")

    except Exception as e:
        logger.exception(f"Error critico al crear orden para user {user.id}")
        await update.message.reply_text("❌ Error al registrar la orden. Por favor intenta de nuevo.")
        return ConversationHandler.END

    try:
        await _notify_admin_new_order(context, order)
    except Exception as e:
        logger.exception(f"Error al notificar admin de nueva orden #{order.public_id}")

    await update.message.reply_text(
        f"✅ ¡Listo! Orden #{_fmt_public_id(order.public_id)} registrada.\n"
        "En breve Pagos la procesa. Puedes ver tus operaciones en 📊 Resumen."
    )

    _reset_flow_memory(context)
    return ConversationHandler.END


async def receive_edit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = (update.message.text or "").strip()

    if text.lower() == BTN_CANCEL.lower():
        await _screen_send_or_edit(update, context, "Envío cancelado ✅")
        _reset_flow_memory(context)
        return ConversationHandler.END

    if text == BTN_BACK:
        return await _show_confirm_screen(update, context)

    if text == BTN_EDIT_AMOUNT:
        context.user_data["edit_target"] = "amount"
        await _screen_send_or_edit(update, context, "Escribe el nuevo monto (ej: 10000):", reply_markup=_cancel_keyboard())
        return ASK_AMOUNT

    if text == BTN_EDIT_BENEF:
        context.user_data["edit_target"] = "beneficiary"
        await _screen_send_or_edit(update, context, "Pega nuevamente los datos del beneficiario:", reply_markup=_cancel_keyboard())
        return ASK_BENEF

    await _screen_send_or_edit(update, context, "Selecciona una opción usando los botones 👇", reply_markup=_edit_keyboard())
    return ASK_EDIT


async def receive_after_edit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = (update.message.text or "").strip()

    if text.lower() == BTN_CANCEL.lower():
        await _screen_send_or_edit(update, context, "Envío cancelado ✅")
        _reset_flow_memory(context)
        return ConversationHandler.END

    if text == BTN_KEEP_EDITING:
        await _screen_send_or_edit(update, context, "¿Qué quieres editar?", reply_markup=_edit_keyboard())
        return ASK_EDIT

    if text == BTN_CONTINUE:
        return await _show_confirm_screen(update, context)

    await _screen_send_or_edit(update, context, "Selecciona una opción usando los botones 👇", reply_markup=_after_edit_keyboard())
    return ASK_EDIT_FIELD


def build_new_order_conversation() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[MessageHandler(filters.Regex(rf"^{BTN_NEW_ORDER}$"), entry_from_menu)],
        states={
            ASK_ORIGIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_origin)],
            ASK_DEST: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_dest)],
            ASK_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_amount)],
            ASK_BENEF: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_benef),
                MessageHandler(filters.PHOTO | filters.Document.ALL, receive_benef),
            ],
            ASK_PROOF: [
                MessageHandler(filters.PHOTO | filters.Document.ALL, receive_proof),
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_proof),
            ],
            ASK_CONFIRM: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_confirm)],
            ASK_EDIT: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_edit)],
            ASK_EDIT_FIELD: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_after_edit)],
        },
        fallbacks=[
            CommandHandler(["cancel", "panic"], panic_handler),
            CommandHandler("start", panic_handler),
            MessageHandler(filters.Regex(MENU_BUTTONS_REGEX), panic_handler),
        ],
        allow_reentry=True,
    )
