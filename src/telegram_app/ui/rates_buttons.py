"""
Botones inline para paginar "Ver más" en tasas.
"""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def rates_more_button(page: int = 1) -> InlineKeyboardMarkup:
    keyboard = [[InlineKeyboardButton("Ver más", callback_data=f"rates_more:page={page}")]]
    return InlineKeyboardMarkup(keyboard)


def rates_pagination_buttons(page: int, has_prev: bool, has_next: bool) -> InlineKeyboardMarkup:
    row = []
    if has_prev:
        row.append(InlineKeyboardButton("⬅️ Anterior", callback_data=f"rates_more:page={page-1}"))
    if has_next:
        row.append(InlineKeyboardButton("Siguiente ➡️", callback_data=f"rates_more:page={page+1}"))
    keyboard = [row] if row else []
    keyboard.append([InlineKeyboardButton("Cerrar", callback_data="rates_more:close")])
    return InlineKeyboardMarkup(keyboard)