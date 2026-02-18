"""
Métodos de pago (UX pro):

- Al tocar "🏦 Métodos de pago": mostrar selector de países (teclado temporal).
- Al elegir país: mostrar métodos desde settings (ENV) con saltos de línea.
- Guardar el message_id mostrado para borrarlo cuando el usuario salga del módulo (cleanup handler).
"""

from __future__ import annotations

from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ContextTypes

from src.config.settings import settings
from src.db.settings_store import get_payment_methods_for_country
from src.telegram_app.ui.keyboards import main_menu_keyboard
from src.telegram_app.ui.routes_popular import COUNTRY_FLAGS, COUNTRY_LABELS

# Países activos (UPPERCASE estándar del proyecto)
COUNTRIES = ["USA", "CHILE", "PERU", "COLOMBIA", "VENEZUELA", "MEXICO", "ARGENTINA"]

BTN_BACK = "⬅️ Volver"


def _country_select_keyboard() -> ReplyKeyboardMarkup:
    rows = []
    for c in COUNTRIES:
        label = f"{COUNTRY_FLAGS[c]} {COUNTRY_LABELS[c]}"
        rows.append([KeyboardButton(label)])
    rows.append([KeyboardButton(BTN_BACK)])
    return ReplyKeyboardMarkup(rows, resize_keyboard=True, one_time_keyboard=True)


def _parse_country_choice(text: str) -> str | None:
    t = (text or "").strip()
    for c in COUNTRIES:
        candidate = f"{COUNTRY_FLAGS[c]} {COUNTRY_LABELS[c]}"
        if t == candidate:
            return c
    return None


async def enter_payment_methods(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Entrada al módulo: mostrar selector de país.
    """
    context.user_data["pm_mode"] = True
    # Exclusividad: salir de otros modos de menú
    context.user_data.pop("summary_mode", None)
    context.user_data.pop("rates_mode", None)
    context.user_data.pop("ref_mode", None)


    await update.message.reply_text(
        "🏦 Métodos de pago\n\nSelecciona el país para ver los datos 👇",
        reply_markup=_country_select_keyboard(),
    )


async def handle_payment_methods_country(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Maneja selección de país dentro del módulo.
    """
    text = (update.message.text or "").strip()

    if text == BTN_BACK:
        # Salimos del modo y volvemos al menú principal
        context.user_data.pop("pm_mode", None)
        await update.message.reply_text(
            "Listo ✅",
            reply_markup=main_menu_keyboard(is_admin=settings.is_admin_id(getattr(update.effective_user, "id", None))),
        )
        return

    country = _parse_country_choice(text)
    if not country:
        await update.message.reply_text(
            "Selecciona un país usando los botones 👇",
            reply_markup=_country_select_keyboard(),
        )
        return

    # Lee desde DB primero, fallback a .env
    pm = get_payment_methods_for_country(country)
    if not pm:
        pm = settings.payment_methods_text(country)

    header = f"🏦 Métodos de pago ({COUNTRY_FLAGS[country]} {COUNTRY_LABELS[country]})"

    if not pm:
        msg = (
            f"{header}\n\n"
            "Aún no están configurados.\n"
            "Si necesitas los datos hoy, usa 🆘 Ayuda 🙂"
        )
    else:
        msg = f"{header}\n\n{pm}"

    sent = await update.message.reply_text(
        msg,
        reply_markup=_country_select_keyboard(),
    )

    # Guardamos el último mensaje mostrado para borrarlo cuando el usuario salga del módulo
    context.user_data["pm_last_message_id"] = sent.message_id