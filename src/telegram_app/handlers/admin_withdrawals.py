from __future__ import annotations

from decimal import Decimal
import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ConversationHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from src.config.settings import settings
from src.db.repositories.users_repo import get_telegram_id_by_user_id
from src.db.repositories.wallet_repo import get_conn as db_conn
from src.db.repositories.withdrawals_repo import WithdrawalsRepo

logger = logging.getLogger(__name__)

A_WAIT_PROOF, A_WAIT_REJECT_REASON = range(2)

CB_ADMIN_APPROVE = "wd_admin_appr:"
CB_ADMIN_REJECT = "wd_admin_rej:"
CB_LIST = "wd_admin_list"
CB_BACK = "wd_admin_back"


def _is_admin(update: Update) -> bool:
    return settings.is_admin_id(getattr(update.effective_user, "id", None))


def _list_keyboard(items: list) -> InlineKeyboardMarkup:
    rows = []
    for w in items[:10]:
        rows.append(
            [
                InlineKeyboardButton(f"✅ Aprobar {w.id}", callback_data=f"{CB_ADMIN_APPROVE}{w.id}"),
                InlineKeyboardButton(f"❌ Rechazar {w.id}", callback_data=f"{CB_ADMIN_REJECT}{w.id}"),
            ]
        )
    rows.append([InlineKeyboardButton("🔄 Refrescar", callback_data=CB_LIST)])
    return InlineKeyboardMarkup(rows)


def build_admin_withdrawals_conversation_handler() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[
            CommandHandler("withdrawals", admin_withdrawals_list),
            CallbackQueryHandler(admin_withdrawals_list, pattern=f"^({CB_LIST}|{CB_BACK})$"),
        ],
        states={
            A_WAIT_PROOF: [
                # Nota: la foto real se procesa por el router global según admin_mode
                MessageHandler(filters.PHOTO, noop_photo),
                CallbackQueryHandler(admin_withdrawals_list, pattern=f"^{CB_BACK}$"),
            ],
            A_WAIT_REJECT_REASON: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, on_reject_reason),
                CallbackQueryHandler(admin_withdrawals_list, pattern=f"^{CB_BACK}$"),
            ],
        },
        fallbacks=[
            CallbackQueryHandler(admin_withdrawals_list, pattern=f"^{CB_BACK}$"),
            CommandHandler("cancel", admin_withdrawals_list),
        ],
        name="admin_withdrawals",
        persistent=False,
        per_chat=True,
        per_user=True,
        per_message=False,
    )


async def noop_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # El router global consumirá la foto según admin_mode.
    return ConversationHandler.END


async def admin_withdrawals_list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not _is_admin(update):
        return ConversationHandler.END

    context.user_data.pop("admin_withdrawal_action", None)

    target = update.callback_query.message if update.callback_query else update.message
    if update.callback_query:
        try:
            await update.callback_query.answer()
        except Exception:
            pass

    with db_conn() as conn:
        repo = WithdrawalsRepo(conn)
        items = repo.list_withdrawals_by_status("SOLICITADA", limit=20)

    if not items:
        await target.reply_text("✅ No hay retiros SOLICITADOS.")
        return ConversationHandler.END

    lines = ["💼 Retiros SOLICITADOS (últimos 20)\n"]
    for w in items:
        fiat_amount = f"{Decimal(w.fiat_amount):.2f} {w.fiat}" if w.fiat_amount is not None and w.fiat else "N/A"
        lines.append(f"ID {w.id} | user {w.user_id} | {Decimal(w.amount_usdt):.8f} USDT | {w.country} | {fiat_amount}")

    await target.reply_text("\n".join(lines))
    await target.reply_text("Selecciona una acción:", reply_markup=_list_keyboard(items))
    return ConversationHandler.END


async def on_click_approve(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not _is_admin(update):
        return ConversationHandler.END

    q = update.callback_query
    try:
        await q.answer()
    except Exception:
        pass

    withdrawal_id = int(q.data.split(":", 1)[1])
    context.user_data["admin_withdrawal_action"] = {"id": withdrawal_id, "mode": "approve"}
    context.user_data["admin_mode"] = "withdrawal_proof"

    kb = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Volver", callback_data=CB_BACK)]])
    await q.message.reply_text(f"Envía la foto del comprobante para el retiro ID {withdrawal_id}.", reply_markup=kb)
    return A_WAIT_PROOF


async def process_withdrawal_proof_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Procesa la foto cuando admin_mode == withdrawal_proof.
    """
    if not _is_admin(update):
        return

    action = context.user_data.get("admin_withdrawal_action") or {}
    withdrawal_id = int(action.get("id") or 0)
    if not withdrawal_id:
        return

    if not update.message.photo:
        return

    proof_file_id = update.message.photo[-1].file_id

    with db_conn() as conn:
        wrepo = WithdrawalsRepo(conn)
        wd = wrepo.get_withdrawal_by_id(withdrawal_id)
        if not wd:
            return

        wrepo.set_withdrawal_resolved(withdrawal_id, proof_file_id)
        conn.commit()

    # limpiar modo
    context.user_data.pop("admin_withdrawal_action", None)
    context.user_data.pop("admin_mode", None)

    tg_id = get_telegram_id_by_user_id(wd.user_id)
    if tg_id:
        await context.bot.send_message(chat_id=int(tg_id), text="✅ Retiro exitoso. Ya fue procesado.")
        await context.bot.send_photo(chat_id=int(tg_id), photo=proof_file_id, caption="Comprobante")

    try:
        await update.message.reply_text(f"✅ Retiro {withdrawal_id} marcado como RESUELTO.")
    except Exception:
        pass


async def on_click_reject(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not _is_admin(update):
        return ConversationHandler.END

    q = update.callback_query
    try:
        await q.answer()
    except Exception:
        pass

    withdrawal_id = int(q.data.split(":", 1)[1])
    context.user_data["admin_withdrawal_action"] = {"id": withdrawal_id, "mode": "reject"}

    kb = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Volver", callback_data=CB_BACK)]])
    await q.message.reply_text(f"Escribe el motivo de rechazo para el retiro ID {withdrawal_id}.", reply_markup=kb)
    return A_WAIT_REJECT_REASON


async def on_reject_reason(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not _is_admin(update):
        return ConversationHandler.END

    reason = (update.message.text or "").strip()
    if len(reason) < 3:
        await update.message.reply_text("Motivo muy corto. Intenta de nuevo.")
        return A_WAIT_REJECT_REASON

    action = context.user_data.get("admin_withdrawal_action") or {}
    withdrawal_id = int(action.get("id") or 0)
    if not withdrawal_id:
        await update.message.reply_text("Sesión expirada. Usa /withdrawals.")
        return ConversationHandler.END

    with db_conn() as conn:
        wrepo = WithdrawalsRepo(conn)
        wd = wrepo.get_withdrawal_by_id(withdrawal_id)
        if not wd:
            await update.message.reply_text("No encontré ese retiro.")
            return ConversationHandler.END

        wrepo.set_withdrawal_rejected(withdrawal_id, reason)
        conn.commit()

    tg_id = get_telegram_id_by_user_id(wd.user_id)
    if tg_id:
        await context.bot.send_message(chat_id=int(tg_id), text=f"❌ Tu retiro fue rechazado.\nMotivo: {reason}")

    await update.message.reply_text(f"❌ Retiro {withdrawal_id} RECHAZADO y saldo revertido.")
    context.user_data.pop("admin_withdrawal_action", None)
    return ConversationHandler.END


admin_withdrawals_callbacks = [
    CallbackQueryHandler(on_click_approve, pattern=f"^{CB_ADMIN_APPROVE}"),
    CallbackQueryHandler(on_click_reject, pattern=f"^{CB_ADMIN_REJECT}"),
]

