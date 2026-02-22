from telegram import ReplyKeyboardMarkup, KeyboardButton
from src.telegram_app.ui.labels import (
    BTN_ADMIN_ORDERS,
    BTN_ADMIN_WITHDRAWALS,
    BTN_ADMIN_RATES_NOW,
    BTN_ADMIN_ALERT_TEST,
    BTN_ADMIN_RESET,
    BTN_ADMIN_RESET_YES,
    BTN_ADMIN_RESET_CANCEL,
    BTN_ADMIN_MENU,
)

BTN_ADMIN_BROADCAST = "📢 Difusión"


def admin_panel_keyboard() -> ReplyKeyboardMarkup:
    """
    Panel admin (solo admin lo verá).
    Usamos labels.py para consistencia.
    """
    keyboard = [
        [KeyboardButton(BTN_ADMIN_ORDERS), KeyboardButton(BTN_ADMIN_WITHDRAWALS)],
        [KeyboardButton(BTN_ADMIN_RATES_NOW), KeyboardButton(BTN_ADMIN_ALERT_TEST)],
        [KeyboardButton(BTN_ADMIN_BROADCAST), KeyboardButton(BTN_ADMIN_RESET)],
        [KeyboardButton(BTN_ADMIN_MENU)],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)


def admin_reset_confirm_keyboard() -> ReplyKeyboardMarkup:
    keyboard = [
        [KeyboardButton(BTN_ADMIN_RESET_YES)],
        [KeyboardButton(BTN_ADMIN_RESET_CANCEL)],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
