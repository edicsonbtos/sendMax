from telegram import ReplyKeyboardMarkup, KeyboardButton


def admin_panel_keyboard() -> ReplyKeyboardMarkup:
    """
    Panel admin (solo admin lo verá).
    """
    keyboard = [
        [KeyboardButton("📋 Órdenes (CREADA)"), KeyboardButton("💸 Retiros (pendientes)")],
        [KeyboardButton("🔄 Tasas ahora"), KeyboardButton("🧪 Alerta test")],
        [KeyboardButton("🧨 Reset (modo prueba)"), KeyboardButton("⬅️ Menú")],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)


def admin_reset_confirm_keyboard() -> ReplyKeyboardMarkup:
    keyboard = [
        [KeyboardButton("✅ Sí, resetear TODO")],
        [KeyboardButton("❌ Cancelar reset")],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
