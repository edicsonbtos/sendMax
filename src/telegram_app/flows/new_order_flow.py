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
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from src.config.settings import settings
from src.config.dynamic_settings import dynamic_config
from src.db.connection import get_async_conn
from src.utils.formatting import fmt_percent
from src.db.repositories.orders_repo import (
    create_order_tx,
    update_order_status_tx,
)
from src.db.repositories.rates_repo import (
    get_latest_active_rate_version,
    get_route_rate,
    get_country_price_for_version,
)
from src.db.repositories.users_repo import get_user_by_telegram_id
from src.telegram_app.utils.templates import format_origin_group_message
from src.telegram_app.handlers.panic import MENU_BUTTONS_REGEX, panic_handler
from src.telegram_app.ui.labels import BTN_NEW_ORDER
from src.telegram_app.ui.routes_popular import (
    COUNTRY_FLAGS,
    COUNTRY_LABELS,
    DEST_ONLY_CODES,
    format_rate_no_noise,
)
from src.telegram_app.utils.text_escape import esc_html
from src.db.repositories.beneficiary_repo import (
    list_active as list_saved_beneficiaries,
    get_by_id as get_saved_beneficiary,
    save as save_beneficiary,
    increment_uses,
    link_order_to_beneficiary,
    mark_smart_save_pending,
)
from src.db.repositories.trust_repo import get_trust_score

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
ASK_ORIGIN, ASK_DEST, ASK_BENEF_MODE, ASK_AMOUNT, ASK_BENEF, ASK_PROOF, ASK_CONFIRM, ASK_EDIT, ASK_EDIT_FIELD, ASK_SAVE_ALIAS = range(10)

# Botones
BTN_CANCEL = "Cancelar"
BTN_CONFIRM = "Confirmar ✅"
BTN_EDIT = "Editar ✏️"
BTN_EDIT_AMOUNT = "Editar monto"
BTN_EDIT_BENEF = "Editar beneficiario"
BTN_BACK = "Volver"
BTN_CONTINUE = "Continuar ➡️"
BTN_KEEP_EDITING = "Seguir editando 🔄"

# Callbacks de Address Book
CB_BENEF_NEW = "ab:new"
CB_BENEF_MANUAL = "ab:manual"
CB_BENEF_PREFIX = "ab:fav:"
CB_SAVE_YES = "ab:save_yes"
CB_SAVE_NO = "ab:save_no"


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


# Paises validos como ORIGEN (nunca псевдо-destinos)
_ORIGIN_CODES = [c for c in ["USA", "CHILE", "PERU", "COLOMBIA", "VENEZUELA", "MEXICO", "ARGENTINA"] if c not in DEST_ONLY_CODES]
# Paises validos como DESTINO (incluye pseudo-destinos)
_DEST_CODES = ["USA", "CHILE", "PERU", "COLOMBIA", "VENEZUELA", "ARGENTINA", "MEXICO", "VENEZUELA_CASH"]


def _origin_keyboard() -> ReplyKeyboardMarkup:
    rows = []
    for code in _ORIGIN_CODES:
        rows.append([KeyboardButton(f"{COUNTRY_FLAGS[code]} {COUNTRY_LABELS[code]}")])
    return ReplyKeyboardMarkup(rows, resize_keyboard=True, one_time_keyboard=True)


def _dest_keyboard(origin: str) -> ReplyKeyboardMarkup:
    rows = []
    for code in _DEST_CODES:
        if code == origin:
            continue  # No auto-ruta
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


def _parse_country(text: str, allowed: list[str] | None = None) -> str | None:
    t = (text or "").strip()
    codes = allowed if allowed is not None else list(COUNTRY_LABELS.keys())
    for code in codes:
        if t == f"{COUNTRY_FLAGS[code]} {COUNTRY_LABELS[code]}":
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

    # Usar comisión del snapshot de tasas
    comm_decimal = getattr(rr, "commission_pct", order.get("commission_pct", Decimal("0.06")))

    return (
        "Listo ✅ Revisa tu envío:\n\n"
        f"Ruta: {COUNTRY_FLAGS[origin]} {COUNTRY_LABELS[origin]} -> {COUNTRY_FLAGS[dest]} {COUNTRY_LABELS[dest]}\n"
        f"Monto (origen): {_fmt_money(amount_fiat)} {origin}\n"
        f"Tasa: {_fmt_rate(rr.rate_client)}\n"
        f"Comisión: {fmt_percent(comm_decimal)}%\n"
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

    summary = format_origin_group_message(order)

    kb = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("✅ Aprobar", callback_data=f"ord:orig_ok:{order.public_id}"),
                InlineKeyboardButton("❌ Rechazar", callback_data=f"ord:orig_rej:{order.public_id}"),
                InlineKeyboardButton("⚙️ En Proceso", callback_data=f"ord:proc:{order.public_id}"),
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

    if order.origin_payment_proof_file_id:
        from src.utils.formatting import fmt_public_id
        await context.bot.send_photo(
            chat_id=target_chat_id,
            photo=order.origin_payment_proof_file_id,
            caption=f"📄 Comprobante Origen #{fmt_public_id(order.public_id)}",
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
        reply_markup=_origin_keyboard(),
        parse_mode="Markdown",
    )
    return ASK_ORIGIN


async def receive_origin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    code = _parse_country(update.message.text, allowed=_ORIGIN_CODES)
    if not code:
        await _screen_send_or_edit(update, context, "Selecciona un país usando los botones 👇", reply_markup=_origin_keyboard())
        return ASK_ORIGIN

    context.user_data["order"]["origin"] = code  # save first
    await _screen_send_or_edit(
        update,
        context,
        "Perfecto ✅ Ahora elige el país/método de *destino*:",
        reply_markup=_dest_keyboard(code),
        parse_mode="Markdown",
    )
    return ASK_DEST


async def receive_dest(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    code = _parse_country(update.message.text, allowed=_DEST_CODES)
    origin = context.user_data["order"].get("origin", "")
    if not code:
        await _screen_send_or_edit(update, context, "Selecciona un destino usando los botones 👇", reply_markup=_dest_keyboard(origin))
        return ASK_DEST

    if code == origin:
        await _screen_send_or_edit(update, context, "Esa ruta no es válida. Elige un destino diferente 👇", reply_markup=_dest_keyboard(origin))
        return ASK_DEST

    context.user_data["order"]["dest"] = code

    # ── Address Book: mostrar menú de contactos ────────────────────
    try:
        telegram_id = update.effective_user.id
        from src.db.repositories.users_repo import get_user_by_telegram_id
        db_user = await get_user_by_telegram_id(telegram_id)
        favorites = []
        if db_user:
            favorites = await list_saved_beneficiaries(db_user.id, dest_country=code)
    except Exception:
        favorites = []

    if favorites:
        # Hay favoritos: mostrar menú completo con botones inline
        rows = []
        for fav in favorites[:5]:  # max 5 botones de favoritos
            label = f"👤 {fav.alias}"
            if fav.dest_country:
                label += f" (🏳️ {fav.dest_country})"
            rows.append([InlineKeyboardButton(label, callback_data=f"{CB_BENEF_PREFIX}{fav.id}")])
        rows.append([
            InlineKeyboardButton("➕ Nuevo contacto", callback_data=CB_BENEF_NEW),
            InlineKeyboardButton("⌨️ Manual", callback_data=CB_BENEF_MANUAL),
        ])
        kb = InlineKeyboardMarkup(rows)
        msg = await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=(
                f"📖 *Agenda de Contactos* — {code}\n\n"
                "Selecciona un favorito para auto-completar,\n"
                "o elige \"Nuevo\" / \"Manual\"."
            ),
            reply_markup=kb,
            parse_mode="Markdown",
        )
        context.user_data["ab_menu_msg_id"] = msg.message_id
        return ASK_BENEF_MODE
    else:
        # Sin favoritos: ir directo a monto (nuevo flujo manual)
        context.user_data["order"]["benef_mode"] = "manual"
        await _screen_send_or_edit(
            update, context,
            f"Escribe el *monto exacto* en {origin} (ej: 10000):",
            reply_markup=_cancel_keyboard(), parse_mode="Markdown",
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
        update, context,
        "Perfecto ✅ Ahora pega los *datos del beneficiario* (como lo enviarás por WhatsApp).\n\n"
        "Incluye al menos:\n"
        " Nombre\n"
        " Cédula\n"
        " N cuenta\n"
        " Tipo\n\n"
        "Envíalo en un solo mensaje.",
        reply_markup=_cancel_keyboard(), parse_mode="Markdown",
    )
    return ASK_BENEF


# ── Address Book handlers ──────────────────────────────────────────────────

async def receive_benef_mode(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Handler para el menú de Address Book (callback_query inline).
    - ab:fav:<id>  → auto-fill + saltar a monto
    - ab:new       → ir directo a monto (guardará después)
    - ab:manual    → flujo manual clásico
    """
    q = update.callback_query
    if not q:
        return ASK_BENEF_MODE

    try:
        await q.answer()
    except Exception:
        pass

    data = q.data or ""
    order = context.user_data.setdefault("order", {})
    origin = order.get("origin", "?")

    def _close_menu():
        """Elimina el menú inline del chat de forma best-effort."""
        try:
            context.application.create_task(
                q.message.delete()
            )
        except Exception:
            pass

    if data.startswith(CB_BENEF_PREFIX):
        # — Usuario eligió un favorito —
        try:
            fav_id = int(data[len(CB_BENEF_PREFIX):])
            beneficiary = await get_saved_beneficiary(fav_id)
        except Exception:
            beneficiary = None

        if not beneficiary:
            try:
                await q.edit_message_text("⚠️ Contacto no encontrado. Usa la opción Manual.")
            except Exception:
                pass
            return ASK_BENEF_MODE

        # Construir el beneficiary_text como snapshot inmutable
        parts = []
        if beneficiary.full_name:    parts.append(f"Nombre: {beneficiary.full_name}")
        if beneficiary.id_number:    parts.append(f"Cédula: {beneficiary.id_number}")
        if beneficiary.bank_name:    parts.append(f"Banco: {beneficiary.bank_name}")
        if beneficiary.account_number: parts.append(f"Cuenta: {beneficiary.account_number}")
        if beneficiary.phone:        parts.append(f"Teléfono: {beneficiary.phone}")
        if beneficiary.payment_method: parts.append(f"Método: {beneficiary.payment_method}")
        if beneficiary.notes:        parts.append(f"Nota: {beneficiary.notes}")
        snapshot = "\n".join(parts) if parts else beneficiary.alias

        order["beneficiary_text"] = snapshot
        order["beneficiary_id"] = fav_id    # snapshot FK
        order["benef_mode"] = "saved"
        _close_menu()

        # Saltar directo al monto
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=(
                f"✅ *{beneficiary.alias}* seleccionado.\n\n"
                f"Escribe el *monto exacto* en {origin} (ej: 10000):"
            ),
            reply_markup=_cancel_keyboard(),
            parse_mode="Markdown",
        )
        return ASK_AMOUNT

    elif data == CB_BENEF_NEW or data == CB_BENEF_MANUAL:
        # — Nuevo o Manual —
        order["benef_mode"] = "manual"
        _close_menu()
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=(
                f"Escribe el *monto exacto* en {origin} (ej: 10000):"
            ),
            reply_markup=_cancel_keyboard(),
            parse_mode="Markdown",
        )
        return ASK_AMOUNT

    return ASK_BENEF_MODE


async def receive_save_alias(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Handler para recibir el alias del Smart-Save.
    Se llama después de que el operador confirma guardar el beneficiario.
    """
    q = update.callback_query
    if q:
        # Primer toque: preguntó si quiere guardar
        try:
            await q.answer()
        except Exception:
            pass
        data = q.data or ""
        if data == CB_SAVE_NO:
            try:
                await q.edit_message_text("👍 Listo, no se guardó el contacto.")
            except Exception:
                pass
            return ConversationHandler.END
        if data == CB_SAVE_YES:
            try:
                await q.edit_message_text(
                    "📝 ¿Cómo quieres llamar a este contacto? (Ej: \"Mi Papá\", \"Cliente Lima\")\n"
                    "Escribe el alias ahora ↓"
                )
            except Exception:
                pass
            context.user_data["smart_save_waiting_alias"] = True
            return ASK_SAVE_ALIAS
        return ConversationHandler.END

    # Mensaje de texto con el alias
    if not context.user_data.get("smart_save_waiting_alias"):
        return ConversationHandler.END

    alias = (update.message.text or "").strip() if update.message else ""
    if not alias or len(alias) < 2:
        await update.message.reply_text("⚠️ Escribe un nombre válido (mínimo 2 caracteres).")
        return ASK_SAVE_ALIAS

    order_data = context.user_data.get("smart_save_data", {})
    if not order_data:
        await update.message.reply_text("❌ No se encontraron datos de la orden para guardar.")
        context.user_data.pop("smart_save_waiting_alias", None)
        return ConversationHandler.END

    try:
        saved = await save_beneficiary(
            user_id=order_data["user_id"],
            alias=alias,
            dest_country=order_data["dest_country"],
            full_name=None,
            bank_name=None,
            account_number=None,
            phone=None,
            notes=order_data.get("beneficiary_text", "")[:500],
        )
        # Vincular retroactivamente la orden con el nuevo beneficiario
        if order_data.get("public_id"):
            await link_order_to_beneficiary(int(order_data["public_id"]), saved.id)

        await update.message.reply_text(
            f"✅ ¡Guardado como *{alias}*! La próxima vez aparecerá en tus Favoritos.",
            parse_mode="Markdown",
        )
    except Exception as e:
        logger.warning("smart_save failed: %s", e)
        await update.message.reply_text("⚠️ No se pudo guardar el contacto. Intenta desde el menú de Agenda.")

    context.user_data.pop("smart_save_waiting_alias", None)
    context.user_data.pop("smart_save_data", None)
    return ConversationHandler.END


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


async def _compute_cash_rate_on_the_fly(
    rate_version_id: int,
    origin: str,
) -> "RouteRate | None":
    """
    Calcula la tasa VENEZUELA_CASH al vuelo cuando no está en route_rates todavía.
    Usa los precios Binance ya almacenados en p2p_country_prices para esta versión.
    """
    try:
        from src.db.repositories.rates_repo import RouteRate
        cash_cfg = await dynamic_config.get_cash_delivery_config()
        zelle_cost: Decimal = cash_cfg["zelle_usdt_cost"]
        margin_zelle: Decimal = cash_cfg["margin_cash_zelle"]
        margin_general: Decimal = cash_cfg["margin_cash_general"]

        if origin == "USA":
            buy_origin = zelle_cost
            comm_pct = margin_zelle
        else:
            cp = await get_country_price_for_version(
                rate_version_id=rate_version_id, country=origin
            )
            if not cp:
                return None
            buy_origin = cp.buy_price
            comm_pct = margin_general

        sell_dest = Decimal("1")  # 1 USD efectivo
        rate_base = sell_dest / buy_origin
        rate_client = rate_base * (Decimal("1") - comm_pct)

        return RouteRate(
            origin_country=origin,
            dest_country="VENEZUELA_CASH",
            commission_pct=comm_pct,
            buy_origin=buy_origin,
            sell_dest=sell_dest,
            rate_base=rate_base,
            rate_client=rate_client,
        )
    except Exception as e:
        logger.warning("_compute_cash_rate_on_the_fly failed origin=%s: %s", origin, e)
        return None


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
        # Si la ruta no está en DB (ej: primera vez con VENEZUELA_CASH antes de regenerar tasas),
        # intentamos calcularla al vuelo desde los precios disponibles.
        if dest == "VENEZUELA_CASH":
            rr = await _compute_cash_rate_on_the_fly(rv.id, origin)
        if not rr:
            await _screen_send_or_edit(update, context, "Esa ruta no está disponible ahora mismo. Intenta otra ruta.")
            _reset_flow_memory(context)
            return ConversationHandler.END

    # Leer comisión de DB (ASYNC - fuera del flow sync)
    comm_pct = await dynamic_config.get_commission_pct(origin, dest)

    context.user_data["order"]["rate_version_id"] = rv.id
    context.user_data["order"]["rate_client"] = rr.rate_client
    context.user_data["order"]["commission_pct"] = comm_pct  # Almacenar como decimal (0.06)

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


async def _try_auto_approve(
    *,
    order,
    operator_user_id: int,
    amount_origin_fiat,
    rate_client,
    context: ContextTypes.DEFAULT_TYPE,
) -> bool:
    """
    Sprint 3 — Piloto Automático.
    Auto-aprueba la orden si:
      1. auto_approve_enabled = 'true' en settings
      2. trust_score del operador >= auto_approve_min_trust (default 90)
      3. monto estimado en USD < auto_approve_max_amount_usd (default 500)

    Retorna True si fue auto-aprobado (para suprimir la notificación manual al admin).
    Nunca lanza excepción — cualquier fallo deja el flujo normal intacto.
    """
    try:
        # Leer configuración desde DB
        async with get_async_conn() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    SELECT key, value FROM settings
                    WHERE key IN (
                        'auto_approve_enabled',
                        'auto_approve_min_trust',
                        'auto_approve_max_amount_usd'
                    );
                    """,
                )
                rows = await cur.fetchall()

        cfg = {r[0]: r[1] for r in rows}
        if cfg.get("auto_approve_enabled", "false").lower() != "true":
            return False  # Feature flag OFF → flujo normal

        min_trust = float(cfg.get("auto_approve_min_trust", "90"))
        max_usd   = float(cfg.get("auto_approve_max_amount_usd", "500"))

        # Obtener trust score del operador
        score = float(await get_trust_score(operator_user_id))
        if score < min_trust:
            return False

        # Estimar monto en USD (amount_origin_fiat × rate_client ≈ USD payout)
        from decimal import Decimal
        estimated_usd = float(Decimal(str(amount_origin_fiat)) * Decimal(str(rate_client)))
        if estimated_usd >= max_usd:
            return False

        # ✅ Condiciones cumplidas — Auto-aprobar
        async with get_async_conn() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "UPDATE orders SET status = 'ORIGEN_CONFIRMADO', updated_at = now() "
                    "WHERE public_id = %s AND status = 'ORIGEN_VERIFICANDO';",
                    (int(order.public_id),),
                )
                await conn.commit()

        logger.info(
            "[AutoPilot] Orden #%s auto-aprobada — operador=%s score=%.1f usd_est=%.2f",
            order.public_id, operator_user_id, score, estimated_usd,
        )

        # Notificar al admin con mensaje especial 🚀
        target_chat_id = settings.ORIGIN_REVIEW_TELEGRAM_CHAT_ID or settings.ADMIN_TELEGRAM_USER_ID
        if target_chat_id:
            await context.bot.send_message(
                chat_id=int(target_chat_id),
                text=(
                    f"🚀 <b>Orden #{order.public_id} AUTO-APROBADA</b>\n\n"
                    f"✅ Historial de confianza del operador verificado\n"
                    f"⭐ Trust Score: <b>{score:.0f}/100</b>\n"
                    f"💰 Monto est. USD: <b>${estimated_usd:.2f}</b>\n\n"
                    "La orden avanzó directamente a <b>ORIGEN CONFIRMADO</b>. "
                    "No requiere aprobación manual."
                ),
                parse_mode="HTML",
            )
        return True

    except Exception as e:
        logger.warning("[AutoPilot] Error al intentar auto-aprobar orden #%s: %s", getattr(order, "public_id", "?"), e)
        return False


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

    # Usar valor ya calculado en receive_proof (evita segunda consulta DB)
    commission_pct = order_data.get("commission_pct", Decimal("0.06"))

    # LOG para auditoría
    logger.info(f"Order creation - Route: {origin}→{dest}, Commission: {commission_pct} ({fmt_percent(commission_pct)}%)")

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

    # ── Sprint 3: Auto-aprobación inteligente ─────────────────────────────
    auto_approved = await _try_auto_approve(
        order=order,
        operator_user_id=int(user.id),
        amount_origin_fiat=amount_origin,
        rate_client=rate_client,
        context=context,
    )

    try:
        if not auto_approved:
            await _notify_admin_new_order(context, order)
    except Exception as e:
        logger.exception(f"Error al notificar admin de nueva orden #{order.public_id}")

    # ── Snapshot de beneficiario guardado ──────────────────────────────────
    benef_mode = order_data.get("benef_mode", "manual")
    saved_benef_id = order_data.get("beneficiary_id")

    if benef_mode == "saved" and saved_benef_id:
        # Usó un favorito → vincular orden + incrementar contador
        try:
            await link_order_to_beneficiary(int(order.public_id), saved_benef_id)
            await increment_uses(saved_benef_id)
        except Exception as e:
            logger.warning("link_beneficiary failed: %s", e)
    elif benef_mode == "manual":
        # Smart-Save: ofrecer guardar el contacto
        try:
            await mark_smart_save_pending(int(order.public_id))
            # Guardar datos para el handler de alias
            context.user_data["smart_save_data"] = {
                "user_id": user.id,
                "dest_country": dest,
                "beneficiary_text": beneficiary_text,
                "public_id": int(order.public_id),
            }
            kb_save = InlineKeyboardMarkup([[
                InlineKeyboardButton("💾 Sí, guardar contacto", callback_data=CB_SAVE_YES),
                InlineKeyboardButton("❌ No, gracias", callback_data=CB_SAVE_NO),
            ]])
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=(
                    f"✅ ¡Listo! Orden #{_fmt_public_id(order.public_id)} registrada.\n"
                    "En breve Pagos la procesa.\n\n"
                    "📍 ¿Deseas guardar este beneficiario en tu agenda para la próxima vez?"
                ),
                reply_markup=kb_save,
                parse_mode="Markdown",
            )
        except Exception as e:
            logger.warning("smart_save_pending failed: %s", e)
            await update.message.reply_text(
                f"✅ ¡Listo! Orden #{_fmt_public_id(order.public_id)} registrada.\n"
                "En breve Pagos la procesa. Puedes ver tus operaciones en 📊 Resumen."
            )
    else:
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
            # Address Book menu (callback inline)
            ASK_BENEF_MODE: [
                CallbackQueryHandler(receive_benef_mode, pattern=r"^ab:(fav:\d+|new|manual)$"),
            ],
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
            # Smart-Save alias
            ASK_SAVE_ALIAS: [
                CallbackQueryHandler(receive_save_alias, pattern=r"^ab:(save_yes|save_no)$"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_save_alias),
            ],
        },
        fallbacks=[
            CommandHandler(["cancel", "panic"], panic_handler),
            CommandHandler("start", panic_handler),
            MessageHandler(filters.Regex(MENU_BUTTONS_REGEX), panic_handler),
        ],
        allow_reentry=True,
    )
