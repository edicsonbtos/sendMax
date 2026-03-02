"""
Botones inline (aparecen debajo de un mensaje).

Útil para links: no ensucia el chat con URLs largas.
"""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def whatsapp_url(number: str, text: str) -> str:
    safe_text = text.replace(" ", "%20")
    return f"https://wa.me/{number}?text={safe_text}"


def support_whatsapp_button(number: str) -> InlineKeyboardMarkup:
    tg_url = "https://t.me/edicsonbtos"
    wa_url = whatsapp_url("584242686434", "Hola Soporte Sendmax, necesito ayuda...")
    
    keyboard = [
        [InlineKeyboardButton("💬 SOPORTE WHATSAPP", url=wa_url)],
        [InlineKeyboardButton("✈️ SOPORTE TELEGRAM", url=tg_url)]
    ]
    return InlineKeyboardMarkup(keyboard)