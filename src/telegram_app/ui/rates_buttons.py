"""
Botones inline para paginar "Ver más" en tasas.
REDISEÑO: Todos los botones en un solo mensaje inline.
"""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def rates_main_buttons() -> InlineKeyboardMarkup:
    """Botones iniciales: Ver más y Ver por país"""
    keyboard = [
        [InlineKeyboardButton("📋 Ver más tasas", callback_data="rates_more:page=1")],
        [InlineKeyboardButton("🌎 Ver por país", callback_data="rates_more:by_country")],
        [InlineKeyboardButton("🏠 Volver al menú", callback_data="rates_more:home")]
    ]
    return InlineKeyboardMarkup(keyboard)


def rates_pagination_buttons(page: int, has_prev: bool, has_next: bool) -> InlineKeyboardMarkup:
    """Botones de paginación con navegación"""
    rows = []
    
    # Fila de navegación
    nav_row = []
    if has_prev:
        nav_row.append(InlineKeyboardButton("⬅️ Anterior", callback_data=f"rates_more:page={page-1}"))
    if has_next:
        nav_row.append(InlineKeyboardButton("Siguiente ➡️", callback_data=f"rates_more:page={page+1}"))
    if nav_row:
        rows.append(nav_row)
    
    # Fila de acciones
    rows.append([InlineKeyboardButton("🔙 Volver a tasas", callback_data="rates_more:back")])
    rows.append([InlineKeyboardButton("🏠 Menú principal", callback_data="rates_more:home")])
    
    return InlineKeyboardMarkup(rows)


def rates_country_select_buttons(countries: list[str]) -> InlineKeyboardMarkup:
    """Botones para seleccionar país de origen"""
    rows = []
    # Crear filas de 2 países cada una
    for i in range(0, len(countries), 2):
        row = []
        for country in countries[i:i+2]:
            row.append(InlineKeyboardButton(country, callback_data=f"rates_more:origin={country}"))
        rows.append(row)
    
    rows.append([InlineKeyboardButton("🔙 Volver a tasas", callback_data="rates_more:back")])
    return InlineKeyboardMarkup(rows)


def rates_country_result_buttons() -> InlineKeyboardMarkup:
    """Botones después de mostrar tasas por país"""
    keyboard = [
        [InlineKeyboardButton("🌎 Otro país", callback_data="rates_more:by_country")],
        [InlineKeyboardButton("🔙 Volver a tasas", callback_data="rates_more:back")],
        [InlineKeyboardButton("🏠 Menú principal", callback_data="rates_more:home")]
    ]
    return InlineKeyboardMarkup(keyboard)
