"""
Handlers del menú principal (botones fijos).
Regla: el menú de operador SOLO funciona si kyc_status == APPROVED.
Usa labels.py como fuente única de textos (evita bugs de encoding).
Incluye rate-limit anti-spam para taps de menú.
"""

import time
from telegram import Update
from telegram.ext import ContextTypes

from src.config.settings import settings
from src.telegram_app.ui.keyboards import main_menu_keyboard
from src.telegram_app.ui.inline_buttons import support_whatsapp_button
from src.telegram_app.handlers.rates import show_rates, rates_country_router
from src.telegram_app.handlers.payment_methods import enter_payment_methods, handle_payment_methods_country
from src.telegram_app.handlers.admin_panel import open_admin_panel, admin_panel_router
from src.telegram_app.handlers.referrals import enter_referrals, referrals_router
from src.telegram_app.handlers.summary import enter_summary, summary_router
from src.telegram_app.handlers.wallet import wallet_menu

from src.db.repositories.users_repo import get_user_kyc_by_telegram_id

from src.telegram_app.ui.labels import (
    BTN_RATES,
    BTN_WALLET,
    BTN_NEW_ORDER,
    BTN_SUMMARY,
    BTN_REFERRALS,
    BTN_PAYMENT_METHODS,
    BTN_HELP,
    BTN_ADMIN,
    BTN_ADMIN_ORDERS,
    BTN_ADMIN_WITHDRAWALS,
    BTN_ADMIN_RATES_NOW,
    BTN_ADMIN_ALERT_TEST,
    BTN_ADMIN_RESET,
    BTN_ADMIN_RESET_YES,
    BTN_ADMIN_RESET_CANCEL,
    BTN_ADMIN_MENU,
)

MENU_BUTTONS = {
    BTN_RATES,
    BTN_WALLET,
    BTN_NEW_ORDER,
    BTN_SUMMARY,
    BTN_REFERRALS,
    BTN_PAYMENT_METHODS,
    BTN_HELP,
    BTN_ADMIN,
    BTN_ADMIN_ORDERS,
    BTN_ADMIN_WITHDRAWALS,
    BTN_ADMIN_RATES_NOW,
    BTN_ADMIN_ALERT_TEST,
    BTN_ADMIN_RESET,
    BTN_ADMIN_RESET_YES,
    BTN_ADMIN_RESET_CANCEL,
    BTN_ADMIN_MENU,
    # botones del mini-modo de tasas
    "🌍 Ver por país",
    "⬅️ Volver",
}


def _is_admin(update: Update) -> bool:
    return settings.is_admin_id(getattr(update.effective_user, "id", None))


def _kyc_status(update: Update) -> str | None:
    u = get_user_kyc_by_telegram_id(update.effective_user.id)
    return getattr(u, "kyc_status", None) if u else None


async def show_home(update: Update, context: ContextTypes.DEFAULT_TYPE, alias: str | None = None, *, silent: bool = False) -> None:
    if silent:
        return
    msg = (
        f"{('Hola, ' + alias + '.') if alias else 'Hola.'}\n\n"
        "Bienvenido a *Sendmax*.\n"
        "Remesas rápidas y seguras con tasa competitiva.\n\n"
        "Elige una opción del menú 👇"
    )
    await update.message.reply_text(
        msg,
        reply_markup=main_menu_keyboard(is_admin=_is_admin(update)),
        parse_mode="Markdown",
    )


async def menu_router(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (update.message.text or "").strip()

    # No interceptar durante retiro/orden
    if context.user_data.get("withdraw_mode") or context.user_data.get("order_mode"):
        return

    # RATE LIMIT: solo para taps del menú (no texto libre en flows)
    if text in MENU_BUTTONS:
        now = time.time()
        last = float(context.user_data.get("menu_last_ts") or 0)
        if (now - last) < 1.0:
            return
        context.user_data["menu_last_ts"] = now

    # Gate KYC: menú solo si APPROVED
    st = _kyc_status(update)
    if st != "APPROVED":
        if text in MENU_BUTTONS:
            await update.message.reply_text(
                "🧾 Verificación requerida.\n\n"
                "Completa tu verificación paso a paso.\n"
                "Si no ves preguntas, escribe /start."
            )
        return

    # Routers de estado
    # Tasas por país (mini-modo)
    if context.user_data.get("rates_mode") or text in {"🌍 Ver por país", "⬅️ Volver"}:
        await rates_country_router(update, context)
        # si el router consume el flujo, salimos
        if context.user_data.get("rates_mode"):
            return
        if text in {"🌍 Ver por país", "⬅️ Volver"}:
            return

    if context.user_data.get("ref_mode"):
        await referrals_router(update, context)
        return

    if context.user_data.get("summary_mode"):
        await summary_router(update, context)
        return

    if context.user_data.get("pm_mode"):
        await handle_payment_methods_country(update, context)
        return

    # Admin panel router
    if _is_admin(update):
        if text in {
            BTN_ADMIN_ORDERS, BTN_ADMIN_WITHDRAWALS, BTN_ADMIN_RATES_NOW,
            BTN_ADMIN_ALERT_TEST, BTN_ADMIN_RESET, BTN_ADMIN_RESET_YES,
            BTN_ADMIN_RESET_CANCEL, BTN_ADMIN_MENU
        }:
            await admin_panel_router(update, context)
            return

    # Botones principales
    if text == BTN_ADMIN:
        if not _is_admin(update):
            return
        await open_admin_panel(update, context)
        return

    if text == BTN_REFERRALS:
        await enter_referrals(update, context)
        return

    if text == BTN_SUMMARY:
        await enter_summary(update, context)
        return

    if text == BTN_PAYMENT_METHODS:
        await enter_payment_methods(update, context)
        return

    if text == BTN_HELP:
        await update.message.reply_text(
            "Soporte Sendmax\nPulsa el botón para abrir WhatsApp:",
            reply_markup=support_whatsapp_button(settings.SUPPORT_WHATSAPP_NUMBER),
        )
        return

    if text == BTN_RATES:
        await show_rates(update, context)
        return

    if text == BTN_WALLET:
        await wallet_menu(update, context)
        return

    # Nuevo envío lo maneja el ConversationHandler por regex
    if text == BTN_NEW_ORDER:
        return

    await update.message.reply_text(
        "Usa los botones del menú 👇",
        reply_markup=main_menu_keyboard(is_admin=_is_admin(update)),
    )
