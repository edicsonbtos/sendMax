"""
menu.py — Menú principal v1.1 (Bot Ligero).
Solo maneja: Tasas, Nuevo Envío, Métodos de Pago, Referidos.
Resumen/Billetera eliminados del bot → solo disponibles en el User Office (web).
"""

from __future__ import annotations

import logging
import time

from telegram import Update
from telegram.ext import ContextTypes

from src.config.settings import settings
from src.db.repositories.users_repo import get_user_kyc_by_telegram_id
from src.telegram_app.handlers.admin_panel import admin_panel_router, open_admin_panel
from src.telegram_app.handlers.ephemeral_cleanup import (
    cleanup_ephemeral,
    track_message,
)
from src.telegram_app.handlers.payment_methods import (
    enter_payment_methods,
    handle_payment_methods_country,
)
from src.telegram_app.handlers.rates import show_rates
from src.telegram_app.handlers.referrals import enter_referrals
from src.telegram_app.ui.keyboards import main_menu_keyboard
from src.telegram_app.ui.labels import (
    BTN_ADMIN,
    BTN_ADMIN_ALERT_TEST,
    BTN_ADMIN_BROADCAST,
    BTN_ADMIN_MENU,
    BTN_ADMIN_ORDERS,
    BTN_ADMIN_RATES_NOW,
    BTN_ADMIN_RESET,
    BTN_ADMIN_RESET_CANCEL,
    BTN_ADMIN_RESET_YES,
    BTN_ADMIN_WITHDRAWALS,
    BTN_NEW_ORDER,
    BTN_PAYMENT_METHODS,
    BTN_RATES,
    BTN_REFERRALS,
)

logger = logging.getLogger(__name__)

# Todos los botones que el rate-limiter y el gate KYC deben conocer
MENU_BUTTONS = {
    BTN_RATES,
    BTN_NEW_ORDER,
    BTN_REFERRALS,
    BTN_PAYMENT_METHODS,
    BTN_ADMIN,
    BTN_ADMIN_ORDERS,
    BTN_ADMIN_WITHDRAWALS,
    BTN_ADMIN_RATES_NOW,
    BTN_ADMIN_ALERT_TEST,
    BTN_ADMIN_BROADCAST,
    BTN_ADMIN_RESET,
    BTN_ADMIN_RESET_YES,
    BTN_ADMIN_RESET_CANCEL,
    BTN_ADMIN_MENU,
}


def _is_admin(update: Update) -> bool:
    return settings.is_admin_id(getattr(update.effective_user, "id", None))


async def _kyc_status(update: Update) -> str | None:
    u = await get_user_kyc_by_telegram_id(update.effective_user.id)
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
    sent = await update.message.reply_text(
        msg,
        reply_markup=main_menu_keyboard(is_admin=_is_admin(update)),
        parse_mode="Markdown",
    )
    await track_message(sent, context)


async def menu_router(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (update.message.text or "").strip()

    await cleanup_ephemeral(update, context)

    # Solo DM
    if update.effective_chat and update.effective_chat.type != "private":
        return

    # No interceptar durante flows activos
    if context.user_data.get("withdraw_mode") or context.user_data.get("order_mode"):
        return

    # Rate-limit anti-spam (1 s entre taps)
    if text in MENU_BUTTONS:
        now = time.time()
        last = float(context.user_data.get("menu_last_ts") or 0)
        if (now - last) < 1.0:
            return
        context.user_data["menu_last_ts"] = now

    # Gate KYC
    st = await _kyc_status(update)
    if st != "APPROVED":
        if text in MENU_BUTTONS:
            await update.message.reply_text(
                "⚠️ Verificación requerida.\n\n"
                "Completa tu verificación paso a paso.\n"
                "Si no ves preguntas, escribe /start."
            )
        return

    def _clear_modes() -> None:
        for k in ("pm_mode", "ref_mode"):
            context.user_data.pop(k, None)

    # ── Botones del menú principal ──────────────────────────────────
    if text == BTN_ADMIN:
        if _is_admin(update):
            _clear_modes()
            await open_admin_panel(update, context)
        return

    if text == BTN_REFERRALS:
        _clear_modes()
        await enter_referrals(update, context)
        return

    if text == BTN_PAYMENT_METHODS:
        _clear_modes()
        await enter_payment_methods(update, context)
        return

    if text == BTN_RATES:
        _clear_modes()
        await show_rates(update, context)
        return

    if context.user_data.get("pm_mode"):
        await handle_payment_methods_country(update, context)
        return

    # Admin panel router (broadcast, órdenes, etc.)
    if _is_admin(update):
        if text in {
            BTN_ADMIN_ORDERS, BTN_ADMIN_WITHDRAWALS, BTN_ADMIN_RATES_NOW,
            BTN_ADMIN_ALERT_TEST, BTN_ADMIN_BROADCAST,
            BTN_ADMIN_RESET, BTN_ADMIN_RESET_YES,
            BTN_ADMIN_RESET_CANCEL, BTN_ADMIN_MENU,
        }:
            await admin_panel_router(update, context)
            return
        if context.user_data.get("awaiting_reset_confirm"):
            await admin_panel_router(update, context)
            return

    # Nuevo envío lo maneja el ConversationHandler
    if text == BTN_NEW_ORDER:
        return

    await update.message.reply_text(
        "Usa los botones del menú 👇",
        reply_markup=main_menu_keyboard(is_admin=_is_admin(update)),
    )
