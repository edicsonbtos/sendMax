from __future__ import annotations

from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ContextTypes, ConversationHandler, MessageHandler, filters

from src.config.settings import settings
from src.telegram_app.ui.routes_popular import COUNTRY_FLAGS, COUNTRY_LABELS
from src.telegram_app.ui.keyboards import main_menu_keyboard

ASK_COUNTRY = 1
BTN_BACK = "⬅️ Volver"

COUNTRIES = ["USA", "CHILE", "PERU", "COLOMBIA", "VENEZUELA", "MEXICO", "ARGENTINA"]


def _country_keyboard() -> ReplyKeyboardMarkup:
    rows = []
    for c in COUNTRIES:
        rows.append([KeyboardButton(f"{COUNTRY_FLAGS[c]} {COUNTRY_LABELS[c]}")])
    rows.append([KeyboardButton(BTN_BACK)])
    return ReplyKeyboardMarkup(rows, resize_keyboard=True, one_time_keyboard=True)


def _parse_country(text: str) -> str | None:
    t = (text or "").strip()
    for c in COUNTRIES:
        if t == f"{COUNTRY_FLAGS[c]} {COUNTRY_LABELS[c]}":
            return c
    return None


async def entry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        "🏦 Métodos de pago\n\nSelecciona el país 👇",
        reply_markup=_country_keyboard(),
    )
    return ASK_COUNTRY


async def receive_country(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = (update.message.text or "").strip()

    if text == BTN_BACK:
        await update.message.reply_text("Listo ✅", reply_markup=main_menu_keyboard())
        return ConversationHandler.END

    country = _parse_country(text)
    if not country:
        await update.message.reply_text("Selecciona un país usando los botones 👇", reply_markup=_country_keyboard())
        return ASK_COUNTRY

    pm = settings.payment_methods_text(country)
    header = f"🏦 Métodos de pago ({COUNTRY_FLAGS[country]} {COUNTRY_LABELS[country]})"

    if not pm:
        msg = f"{header}\n\nPendiente. Solicítalo por WhatsApp soporte: +{settings.SUPPORT_WHATSAPP_NUMBER}"
    else:
        msg = f"{header}\n\n{pm}"

    await update.message.reply_text(msg, reply_markup=_country_keyboard())
    return ASK_COUNTRY


def build_payment_methods_conversation() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[MessageHandler(filters.Regex(r"^🏦 Métodos de pago$"), entry)],
        states={ASK_COUNTRY: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_country)]},
        fallbacks=[],
        allow_reentry=True,
    )