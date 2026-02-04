"""
Handler: 📈 Tasas (populares) + filtro por país origen

- Muestra rutas populares (si existen)
- Botón inline "Ver más" (paginado)
- Botón de texto: 🌍 Ver por país (pide ORIGEN y lista todas las rutas salientes)
"""

from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ContextTypes

from src.db.repositories.rates_repo import (
    get_latest_active_rate_version,
    list_route_rates_for_version,
    list_route_rates_by_origin,
)
from src.telegram_app.ui.routes_popular import POPULAR_ROUTES, route_label, format_rate_no_noise
from src.telegram_app.ui.rates_buttons import rates_more_button
from src.telegram_app.ui.labels import BTN_NEW_ORDER


BTN_BY_COUNTRY = "🌍 Ver por país"
BTN_BACK = "⬅️ Volver"


def _rates_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [[KeyboardButton(BTN_BY_COUNTRY)], [KeyboardButton(BTN_BACK)]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


async def show_rates(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # si venimos de modo filtro, lo limpiamos
    context.user_data.pop("rates_mode", None)

    rv = get_latest_active_rate_version()
    if not rv:
        await update.message.reply_text("Aún no tengo tasas listas. Vuelve en unos minutos.")
        return

    rates = list_route_rates_for_version(rate_version_id=rv.id, routes=POPULAR_ROUTES)
    rate_map = {(r.origin_country, r.dest_country): r for r in rates}

    blocks = []
    for (o, d) in POPULAR_ROUTES:
        rr = rate_map.get((o, d))
        if not rr:
            continue
        blocks.append(
            f"{route_label(o, d)}\n"
            f"Tasa: {format_rate_no_noise(rr.rate_client)}"
        )

    if not blocks:
        await update.message.reply_text(
            "Todavía no tengo tasas para las rutas populares.\nIntenta nuevamente en un momento."
        )
        return

    text = "📈 Tasas de hoy\n\n" + "\n\n".join(blocks) + f"\n\n¿Listo para enviar? Toca {BTN_NEW_ORDER}."
    await update.message.reply_text(
        text=text,
        reply_markup=rates_more_button(page=1),
    )
    await update.message.reply_text(
        "Opciones:",
        reply_markup=_rates_keyboard(),
    )


async def rates_country_router(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Router simple para el modo tasas por país (usa context.user_data).
    Se engancha desde menu_router cuando el usuario presiona BTN_BY_COUNTRY o cuando está en rates_mode.
    """
    text = (update.message.text or "").strip()

    if text == BTN_BY_COUNTRY:
        context.user_data["rates_mode"] = "await_origin"
        await update.message.reply_text("Escribe el país de ORIGEN (ej: CHILE):")
        return

    if text == BTN_BACK:
        context.user_data.pop("rates_mode", None)
        from src.telegram_app.handlers.menu import show_home  # import local para evitar circular
        await show_home(update, context)
        return

    mode = context.user_data.get("rates_mode")
    if mode != "await_origin":
        return

    origin = text.upper().strip()
    rv = get_latest_active_rate_version()
    if not rv:
        await update.message.reply_text("No tengo tasas activas ahora mismo.")
        context.user_data.pop("rates_mode", None)
        return

    rates = list_route_rates_by_origin(rate_version_id=rv.id, origin_country=origin)
    if not rates:
        await update.message.reply_text(
            "No encontré tasas para ese origen.\n"
            "Verifica el nombre (ej: CHILE, USA, PERU, COLOMBIA, VENEZUELA, MEXICO, ARGENTINA)."
        )
        return

    blocks = []
    for rr in rates:
        blocks.append(f"{route_label(rr.origin_country, rr.dest_country)}\nTasa: {format_rate_no_noise(rr.rate_client)}")

    await update.message.reply_text(
        f"📈 Tasas por país — ORIGEN {origin}\n\n" + "\n\n".join(blocks)
    )
    context.user_data.pop("rates_mode", None)
