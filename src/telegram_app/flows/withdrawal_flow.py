from __future__ import annotations

import asyncio
import logging
from decimal import Decimal, InvalidOperation

from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardRemove,
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
from src.db.repositories import rates_repo
from src.db.repositories.users_repo import get_payout_method, get_user_by_telegram_id
from src.db.repositories.wallet_repo import get_async_conn as db_async_conn
from src.db.repositories.wallet_repo import get_balance
from src.db.repositories.withdrawals_repo import WithdrawalsRepo
from src.telegram_app.handlers.panic import MENU_BUTTONS_REGEX, panic_handler

logger = logging.getLogger(__name__)


def _reset_withdraw_state(context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data.pop("withdrawal", None)
    context.user_data.pop("withdraw_panel", None)
    context.user_data.pop("withdraw_mode", None)

MIN_WITHDRAW_USDT = Decimal("10")

W_AMOUNT, W_CONFIRM = range(2)

CB_CONFIRM = "wd_confirm"
CB_CANCEL = "wd_cancel"

CB_ADMIN_APPROVE = "wd_admin_appr:"
CB_ADMIN_REJECT = "wd_admin_rej:"


async def _safe_answer(q) -> None:
    try:
        await q.answer()
    except Exception:
        pass


def _kb_cancel_inline() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton("Cancelar", callback_data=CB_CANCEL)]])


def _kb_confirm_cancel() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("✅ Confirmar", callback_data=CB_CONFIRM)],
            [InlineKeyboardButton("Cancelar", callback_data=CB_CANCEL)],
        ]
    )


def _admin_request_keyboard(withdrawal_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [[
            InlineKeyboardButton("✅ Aprobar", callback_data=f"{CB_ADMIN_APPROVE}{withdrawal_id}"),
            InlineKeyboardButton("❌ Rechazar", callback_data=f"{CB_ADMIN_REJECT}{withdrawal_id}"),
        ]]
    )


def _set_panel(context: ContextTypes.DEFAULT_TYPE, chat_id: int, message_id: int) -> None:
    context.user_data["withdraw_panel"] = {"chat_id": chat_id, "message_id": message_id}


def _get_panel(context: ContextTypes.DEFAULT_TYPE) -> tuple[int | None, int | None]:
    panel = context.user_data.get("withdraw_panel") or {}
    return panel.get("chat_id"), panel.get("message_id")


async def _edit_panel(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str, reply_markup=None) -> None:
    chat_id, message_id = _get_panel(context)

    if chat_id and message_id:
        try:
            await context.bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=text,
                reply_markup=reply_markup,
                disable_web_page_preview=True,
            )
            return
        except Exception:
            pass

    target_chat_id = chat_id or (update.effective_chat.id if update.effective_chat else None)
    if target_chat_id is None:
        return
    msg = await context.bot.send_message(chat_id=target_chat_id, text=text, reply_markup=reply_markup)
    _set_panel(context, msg.chat_id, msg.message_id)


def build_withdrawal_conversation_handler() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[
            CommandHandler("withdraw", start_withdrawal),
            CallbackQueryHandler(start_withdrawal, pattern=r"^(withdraw_start|wallet_withdraw)$"),
        ],
        states={
            W_AMOUNT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, on_amount),
                CallbackQueryHandler(on_cancel_cb, pattern=f"^{CB_CANCEL}$"),
            ],
            W_CONFIRM: [
                CallbackQueryHandler(on_confirm_or_cancel, pattern=f"^({CB_CONFIRM}|{CB_CANCEL})$"),
            ],
        },
        fallbacks=[
            CallbackQueryHandler(on_cancel_cb, pattern=f"^{CB_CANCEL}$"),
            CommandHandler(["cancel", "panic"], panic_handler),
            CommandHandler("start", panic_handler),
            MessageHandler(filters.Regex(MENU_BUTTONS_REGEX), panic_handler),
        ],
        name="withdrawal_flow_user",
        persistent=False,
        per_chat=True,
        per_user=True,
        per_message=False,
    )


async def start_withdrawal(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # Lock: evita doble inicio por spam
    if context.user_data.get("withdraw_mode"):
        if update.callback_query:
            try:
                await update.callback_query.answer("⏳ Ya tienes un retiro en curso.", show_alert=True)
            except Exception:
                pass
        else:
            await update.message.reply_text("⏳ Ya tienes un retiro en curso. Pulsa Cancelar para salir.")
        return W_AMOUNT
    context.user_data["withdraw_mode"] = True
    context.user_data.pop("withdrawal", None)

    if update.callback_query:
        q = update.callback_query
        await _safe_answer(q)
        _set_panel(context, q.message.chat_id, q.message.message_id)
    else:
        msg = await update.message.reply_text("Cargando retiro…")
        _set_panel(context, msg.chat_id, msg.message_id)

    try:
        db_user = await asyncio.wait_for(get_user_by_telegram_id(update.effective_user.id), timeout=5.0)
    except asyncio.TimeoutError:
        await _edit_panel(update, context, "⏳ Error DB. Reintenta.")
        context.user_data.pop("withdraw_mode", None)
        return ConversationHandler.END

    if not db_user:
        await _edit_panel(update, context, "❌ No estás registrado. Usa /start.")
        context.user_data.pop("withdraw_mode", None)
        return ConversationHandler.END

    payout_country, payout_method_text = await get_payout_method(db_user.id)
    if not payout_country or not payout_method_text:
        await _edit_panel(
            update,
            context,
            "❌ No tienes método de cobro configurado.\n\n"
            "Completa tu verificación KYC para registrar el método de pago.",
        )
        context.user_data.pop("withdraw_mode", None)
        return ConversationHandler.END

    balance = await get_balance(db_user.id)

    context.user_data["withdrawal"] = {
        "country": payout_country,
        "dest_text": payout_method_text,
    }

    await _edit_panel(
        update,
        context,
        "💸 Retiro\n\n"
        f"País cobro: {payout_country}\n"
        f"Saldo disponible: {balance:.8f} USDT\n\n"
        f"Escribe el monto a retirar en USDT.\nMínimo: {MIN_WITHDRAW_USDT} USDT.",
        reply_markup=_kb_cancel_inline(),
    )
    if update.effective_message:
        await update.effective_message.reply_text("Escribe el monto (ej: 25)", reply_markup=ReplyKeyboardRemove())

    return W_AMOUNT


async def on_cancel_cb(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    q = update.callback_query
    await _safe_answer(q)

    context.user_data.pop("withdrawal", None)
    context.user_data.pop("withdraw_panel", None)
    context.user_data.pop("withdraw_mode", None)

    await q.message.reply_text("Operación cancelada.")
    return ConversationHandler.END


async def on_amount(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    wd = context.user_data.get("withdrawal") or {}
    if not wd.get("country") or not wd.get("dest_text"):
        await update.message.reply_text("Sesión expirada. Vuelve a intentar desde 💼 Billetera.")
        context.user_data.pop("withdraw_mode", None)
        return ConversationHandler.END

    txt = (update.message.text or "").strip().replace(",", ".")
    try:
        amount = Decimal(txt)
    except InvalidOperation:
        await _edit_panel(update, context, "Monto inválido. Ingresa un nuevo monto o cancela.", reply_markup=_kb_cancel_inline())
        return W_AMOUNT

    if amount <= 0:
        await _edit_panel(update, context, "Monto inválido. Debe ser mayor a 0.", reply_markup=_kb_cancel_inline())
        return W_AMOUNT

    if amount < MIN_WITHDRAW_USDT:
        await _edit_panel(update, context, f"Monto inválido. El mínimo es {MIN_WITHDRAW_USDT} USDT.", reply_markup=_kb_cancel_inline())
        return W_AMOUNT

    db_user = await get_user_by_telegram_id(update.effective_user.id)
    if not db_user:
        await update.message.reply_text("No estás registrado. Usa /start.")
        context.user_data.pop("withdraw_mode", None)
        return ConversationHandler.END

    balance = await get_balance(db_user.id)
    if amount > balance:
        await _edit_panel(update, context, f"Saldo insuficiente. Tu balance es {balance:.8f} USDT.", reply_markup=_kb_cancel_inline())
        return W_AMOUNT

    country = wd["country"]

    result = await rates_repo.get_latest_active_country_sell(country=country)
    if not result:
        await _edit_panel(update, context, f"No tengo tasa activa para {country}. Intenta más tarde.")
        context.user_data.pop("withdraw_mode", None)
        return ConversationHandler.END

    fiat, sell_price = result
    sell_price = Decimal(str(sell_price))
    fiat_amount = (amount * sell_price).quantize(Decimal("0.01"))

    wd["amount_usdt"] = str(amount)
    wd["fiat"] = fiat
    wd["fiat_amount"] = str(fiat_amount)
    context.user_data["withdrawal"] = wd

    await _edit_panel(
        update,
        context,
        "Confirma tu retiro:\n\n"
        f"• País: {country}\n"
        f"• Monto: {amount:.8f} USDT\n"
        f"• Estimado: {fiat_amount:.2f} {fiat}\n\n"
        f"Destino (KYC):\n{wd['dest_text']}\n",
        reply_markup=_kb_confirm_cancel(),
    )
    return W_CONFIRM


async def on_confirm_or_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    q = update.callback_query
    await _safe_answer(q)

    if q.data == CB_CANCEL:
        context.user_data.pop("withdrawal", None)
        context.user_data.pop("withdraw_panel", None)
        context.user_data.pop("withdraw_mode", None)
        await q.message.reply_text("Operación cancelada.")
        return ConversationHandler.END

    wd = context.user_data.get("withdrawal") or {}
    if not wd:
        await q.message.reply_text("Sesión expirada. Intenta de nuevo.")
        context.user_data.pop("withdraw_mode", None)
        return ConversationHandler.END

    db_user = await get_user_by_telegram_id(q.from_user.id)
    if not db_user:
        context.user_data.pop("withdrawal", None)
        context.user_data.pop("withdraw_panel", None)
        context.user_data.pop("withdraw_mode", None)
        await q.message.reply_text("No estás registrado. Usa /start.")
        return ConversationHandler.END

    amount = Decimal(wd["amount_usdt"])
    country = wd["country"]
    fiat = wd["fiat"]
    fiat_amount = Decimal(wd["fiat_amount"])
    dest_text = wd["dest_text"]

    try:
        async with db_async_conn() as conn:
            repo = WithdrawalsRepo(conn)
            try:
                withdrawal_id = await asyncio.wait_for(
                    repo.create_withdrawal_request_fiat(
                        user_id=db_user.id,
                        amount_usdt=amount,
                        country=country,
                        fiat=fiat,
                        fiat_amount=fiat_amount,
                        dest_text=dest_text,
                    ),
                    timeout=5.0
                )
                await conn.commit()
            except ValueError as e:
                await _edit_panel(update, context, f"❌ {str(e)}", reply_markup=_kb_cancel_inline())
                return W_AMOUNT
    except asyncio.TimeoutError:
        await q.message.reply_text("⏳ Timeout registrando retiro. Reintenta.")
        return W_CONFIRM

    context.user_data.pop("withdrawal", None)
    context.user_data.pop("withdraw_panel", None)
    context.user_data.pop("withdraw_mode", None)

    await q.message.reply_text("✅ Solicitud creada. Te avisaré cuando sea procesada.")

    try:
        admin_chat_id = settings.PAYMENTS_TELEGRAM_CHAT_ID
        if not admin_chat_id:
            admin_ids = settings.admin_user_ids
            if not admin_ids:
                logger.error("No hay admin IDs ni PAYMENTS_TELEGRAM_CHAT_ID configurado para notificar retiro %s", withdrawal_id)
                return ConversationHandler.END
            admin_chat_id = next(iter(admin_ids))
        admin_chat_id = int(admin_chat_id)

        admin_text = (
            "💸 Retiro SOLICITADO\n\n"
            f"Operador: {db_user.alias}\n"
            f"País: {country}\n"
            f"Monto: {amount:.8f} USDT\n"
            f"Estimado: {fiat_amount:.2f} {fiat}\n"
            f"Destino (KYC): {dest_text}\n"
            f"ID: {withdrawal_id}"
        )
        await context.bot.send_message(chat_id=admin_chat_id, text=admin_text, reply_markup=_admin_request_keyboard(withdrawal_id))
    except Exception:
        logger.exception("Error notificando admin sobre retiro %s (retiro ya registrado)", withdrawal_id)
    return ConversationHandler.END


async def cancel_withdrawal(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.pop("withdrawal", None)
    context.user_data.pop("withdraw_panel", None)
    context.user_data.pop("withdraw_mode", None)
    await update.message.reply_text("Operación cancelada.")
    return ConversationHandler.END
