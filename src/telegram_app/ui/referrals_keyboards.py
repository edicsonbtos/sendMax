from telegram import ReplyKeyboardMarkup, KeyboardButton


def referrals_menu_keyboard() -> ReplyKeyboardMarkup:
    keyboard = [
        [KeyboardButton("🔗 Mi link"), KeyboardButton("📊 Resumen")],
        [KeyboardButton("💰 Ganancias"), KeyboardButton("⬅️ Volver")],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
