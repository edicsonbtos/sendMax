"""
Handler: Ver más tasas (paginación por callback).

- Excluye rutas populares
- Orden: Venezuela primero, luego destino A->Z, dentro origen A->Z
- 10 rutas por página (menos ruido)
- Formato visual:
    🇨🇴 Colombia → 🇵🇪 Perú
    Tasa: 0.000831
"""

from __future__ import annotations

from typing import List, Tuple

from telegram import Update
from telegram.ext import ContextTypes

from src.db.repositories.rates_repo import (
    get_latest_active_rate_version,
    list_all_route_pairs_for_version,
    list_route_rates_for_version,
)
from src.telegram_app.ui.routes_popular import POPULAR_ROUTES, route_label, format_rate_no_noise
from src.telegram_app.ui.rates_buttons import rates_pagination_buttons

PAGE_SIZE = 9


def _parse_page(data: str) -> int:
    # data esperado: "rates_more:page=2"
    try:
        part = data.split("page=")[1]
        page = int(part)
        return max(1, page)
    except Exception:
        return 1


def _sort_routes_dest_first(routes: List[Tuple[str, str]]) -> List[Tuple[str, str]]:
    """
    Venezuela primero, luego destino asc, dentro origen asc.
    """
    def key_fn(r: Tuple[str, str]):
        origin, dest = r
        venezuela_first = 0 if dest == "VENEZUELA" else 1
        return (venezuela_first, dest, origin)

    return sorted(routes, key=key_fn)


async def handle_rates_more(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    if not q:
        return

    data = q.data or ""

    # Cerrar
    if data == "rates_more:close":
        await q.answer()
        # En privado esto funciona bien para mantener limpio
        await q.message.delete()
        return

    page = _parse_page(data)

    rv = get_latest_active_rate_version()
    if not rv:
        await q.answer("Aún no hay tasas.", show_alert=False)
        return

    all_pairs = list_all_route_pairs_for_version(rate_version_id=rv.id)

    # Excluir populares
    popular_set = set(POPULAR_ROUTES)
    rest = [pair for pair in all_pairs if pair not in popular_set]

    # Ordenar (Venezuela primero)
    rest = _sort_routes_dest_first(rest)

    # Paginación
    total = len(rest)
    start = (page - 1) * PAGE_SIZE
    end = start + PAGE_SIZE

    page_pairs = rest[start:end]
    has_prev = page > 1
    has_next = end < total

    # Cargar tasas de esta página
    rates = list_route_rates_for_version(rate_version_id=rv.id, routes=page_pairs)
    rate_map = {(r.origin_country, r.dest_country): r for r in rates}

    # Texto limpio y fácil de leer
    blocks = []
    for (o, d) in page_pairs:
        rr = rate_map.get((o, d))
        if not rr:
            continue

        blocks.append(
            f"{route_label(o, d)}\n"
            f"Tasa: {format_rate_no_noise(rr.rate_client)}"
        )

    text = (
        "📈 Tasas (Ver más)\n"
        f"Página {page}\n\n"
        + ("\n\n".join(blocks) if blocks else "No hay rutas para mostrar en esta página.")
    )

    await q.answer()
    await q.message.edit_text(
        text=text,
        reply_markup=rates_pagination_buttons(page=page, has_prev=has_prev, has_next=has_next),
    )