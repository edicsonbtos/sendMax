"""
Teclados (ReplyKeyboardMarkup) — Menú Principal v1.2.
6 botones: Tasas, Nuevo envío, Métodos de pago, Referidos, Billetera, Soporte.
Admin añade 7.º botón si procede.
"""
from telegram import ReplyKeyboardMarkup, KeyboardButton

from src.telegram_app.ui.labels import (
    BTN_RATES,
    BTN_NEW_ORDER,
    BTN_PAYMENT_METHODS,
    BTN_REFERRALS,
    BTN_WALLET,
    BTN_HELP,
    BTN_ADMIN,
)


def main_menu_keyboard(is_admin: bool = False) -> ReplyKeyboardMarkup:
    keyboard = [
        [KeyboardButton(BTN_RATES),           KeyboardButton(BTN_NEW_ORDER)],
        [KeyboardButton(BTN_PAYMENT_METHODS), KeyboardButton(BTN_REFERRALS)],
        [KeyboardButton(BTN_WALLET),          KeyboardButton(BTN_HELP)],
    ]
    if is_admin:
        keyboard.append([KeyboardButton(BTN_ADMIN)])

    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
        one_time_keyboard=False,
        input_field_placeholder="Tasas · Nuevo envío · Billetera · Soporte",
    )
