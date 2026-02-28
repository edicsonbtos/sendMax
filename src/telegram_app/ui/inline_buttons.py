"""
Botones inline (aparecen debajo de un mensaje).

Útil para links: no ensucia el chat con URLs largas.
"""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def whatsapp_url(number: str, text: str) -> str:
    safe_text = text.replace(" ", "%20")
    return f"https://wa.me/{number}?text={safe_text}"


def support_whatsapp_button(number: str) -> InlineKeyboardMarkup:
    # Usamos Telegram como soporte en vez de WA para conectar con Admin
    url = "https://t.me/edicsonbtos"
    keyboard = [[InlineKeyboardButton("Abrir Soporte (Telegram)", url=url)]]
    return InlineKeyboardMarkup(keyboard)