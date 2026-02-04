"""
Teclados (ReplyKeyboardMarkup) para una UI fija tipo "app".
"""
from telegram import ReplyKeyboardMarkup, KeyboardButton

from src.telegram_app.ui.labels import (
    BTN_RATES,
    BTN_WALLET,
    BTN_NEW_ORDER,
    BTN_SUMMARY,
    BTN_REFERRALS,
    BTN_PAYMENT_METHODS,
    BTN_HELP,
    BTN_ADMIN,
)


def main_menu_keyboard(is_admin: bool = False) -> ReplyKeyboardMarkup:
    keyboard = [
        [KeyboardButton(BTN_RATES), KeyboardButton(BTN_WALLET)],
        [KeyboardButton(BTN_NEW_ORDER), KeyboardButton(BTN_SUMMARY)],
        [KeyboardButton(BTN_REFERRALS), KeyboardButton(BTN_PAYMENT_METHODS)],
        [KeyboardButton(BTN_HELP)],
    ]
    if is_admin:
        keyboard.append([KeyboardButton(BTN_ADMIN)])

    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
        one_time_keyboard=False,
        input_field_placeholder="Elige una opción…",
    )
