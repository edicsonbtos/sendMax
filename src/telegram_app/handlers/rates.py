"""
Handler: 📈 Tasas (populares) + filtro por país origen
REDISEÑO: Todo en un solo mensaje con botones inline (sin teclado de texto)
"""

from telegram import Update
from telegram.ext import ContextTypes

from src.db.repositories.rates_repo import (
    get_latest_active_rate_version,
    list_route_rates_for_version,
)
from src.telegram_app.ui.routes_popular import POPULAR_ROUTES, route_label, format_rate_no_noise
from src.telegram_app.ui.rates_buttons import rates_main_buttons
from src.telegram_app.ui.labels import BTN_NEW_ORDER


async def show_rates(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Muestra tasas populares con botones inline"""
    # Limpiar cualquier modo anterior
    context.user_data.pop("rates_mode", None)
    context.user_data.pop("rates_message_id", None)

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

    text = (
        "📈 *Tasas de hoy* (Rutas populares)\n\n"
        + "\n\n".join(blocks)
        + f"\n\n¿Listo para enviar? Toca {BTN_NEW_ORDER}."
    )
    
    msg = await update.message.reply_text(
        text=text,
        reply_markup=rates_main_buttons(),
        parse_mode="Markdown"
    )
    
    # Guardar ID del mensaje para poder editarlo después
    context.user_data["rates_message_id"] = msg.message_id


# NOTA: La función rates_country_router ya NO se necesita
# porque todo el flujo ahora es por callbacks inline
