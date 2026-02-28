"""
Teclados (ReplyKeyboardMarkup) — Menú Ligero v1.1.
Menú operador: solo 4 funciones core + Admin (si aplica).
Las métricas detalladas se consultan en el User Office (web).
"""
from telegram import ReplyKeyboardMarkup, KeyboardButton

from src.telegram_app.ui.labels import (
    BTN_RATES,
    BTN_NEW_ORDER,
    BTN_REFERRALS,
    BTN_PAYMENT_METHODS,
    BTN_ADMIN,
)


def main_menu_keyboard(is_admin: bool = False) -> ReplyKeyboardMarkup:
    keyboard = [
        [KeyboardButton(BTN_RATES), KeyboardButton(BTN_NEW_ORDER)],
        [KeyboardButton(BTN_PAYMENT_METHODS), KeyboardButton(BTN_REFERRALS)],
    ]
    if is_admin:
        keyboard.append([KeyboardButton(BTN_ADMIN)])

    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
        one_time_keyboard=False,
        input_field_placeholder="Tasas · Nuevo envío · Métodos · Referido",
    )
