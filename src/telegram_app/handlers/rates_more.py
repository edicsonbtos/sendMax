"""
Handler: Ver más tasas (paginación y filtros por callback inline)
Con manejo robusto de errores en todos los callbacks.
"""

from __future__ import annotations
import logging
from typing import List, Tuple
from telegram import Update
from telegram.error import BadRequest
from telegram.ext import ContextTypes

from src.db.repositories.rates_repo import (
    get_latest_active_rate_version,
    list_all_route_pairs_for_version,
    list_route_rates_for_version,
    list_route_rates_by_origin,
)
from src.telegram_app.ui.routes_popular import POPULAR_ROUTES, route_label, format_rate_no_noise
from src.telegram_app.ui.rates_buttons import (
    rates_main_buttons,
    rates_pagination_buttons,
    rates_country_select_buttons,
    rates_country_result_buttons,
)

logger = logging.getLogger(__name__)
PAGE_SIZE = 9
AVAILABLE_COUNTRIES = ["USA", "VENEZUELA", "CHILE", "PERU", "COLOMBIA", "MEXICO", "ARGENTINA"]


def _parse_page(data: str) -> int:
    try:
        part = data.split("page=")[1]
        return max(1, int(part)) if part.isdigit() else 1
    except Exception:
        return 1


def _parse_origin(data: str) -> str:
    try:
        return data.split("origin=")[1].upper()
    except Exception:
        return ""


def _sort_routes_dest_first(routes: List[Tuple[str, str]]) -> List[Tuple[str, str]]:
    def key_fn(r: Tuple[str, str]):
        origin, dest = r
        venezuela_first = 0 if dest == "VENEZUELA" else 1
        return (venezuela_first, dest, origin)
    return sorted(routes, key=key_fn)


async def _safe_edit(q, text: str, reply_markup=None):
    """Edita mensaje con protección contra 'message is not modified'"""
    try:
        await q.message.edit_text(
            text=text,
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
    except BadRequest as e:
        if "message is not modified" not in str(e).lower():
            raise


async def handle_rates_more(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    if not q:
        return

    try:
        await q.answer()
        data = q.data or ""

        # 1. VOLVER AL MENÚ PRINCIPAL
        if data == "rates_more:home":
            from src.telegram_app.handlers.menu import main_menu_keyboard, _is_admin
            try:
                await q.message.delete()
            except Exception:
                pass
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="Elige una opción del menú 👇",
                reply_markup=main_menu_keyboard(is_admin=_is_admin(update)),
                parse_mode="Markdown",
            )
            return

        # 2. VOLVER A TASAS INICIALES
        if data == "rates_more:back":
            rv = get_latest_active_rate_version()
            if not rv:
                await _safe_edit(q, "Aún no hay tasas.")
                return

            rates = list_route_rates_for_version(rate_version_id=rv.id, routes=POPULAR_ROUTES)
            rate_map = {(r.origin_country, r.dest_country): r for r in rates}

            blocks = []
            for (o, d) in POPULAR_ROUTES:
                rr = rate_map.get((o, d))
                if not rr:
                    continue
                blocks.append(f"{route_label(o, d)}\nTasa: {format_rate_no_noise(rr.rate_client)}")

            text = "📈 *Tasas de hoy* (Rutas populares)\n\n" + "\n\n".join(blocks)
            await _safe_edit(q, text, rates_main_buttons())
            return

        # 3. SELECCIONAR PAÍS
        if data == "rates_more:by_country":
            await _safe_edit(q, "🌎 *Selecciona el país de ORIGEN:*", rates_country_select_buttons(AVAILABLE_COUNTRIES))
            return

        # 4. MOSTRAR TASAS POR PAÍS
        if data.startswith("rates_more:origin="):
            origin = _parse_origin(data)
            rv = get_latest_active_rate_version()
            if not rv:
                await _safe_edit(q, "No hay tasas activas.")
                return

            rates = list_route_rates_by_origin(rate_version_id=rv.id, origin_country=origin)
            if not rates:
                await _safe_edit(
                    q,
                    f"❌ No encontré tasas para *{origin}*.\n\nIntenta con otro país.",
                    rates_country_select_buttons(AVAILABLE_COUNTRIES)
                )
                return

            blocks = []
            for rr in rates:
                blocks.append(f"{route_label(rr.origin_country, rr.dest_country)}\nTasa: {format_rate_no_noise(rr.rate_client)}")

            text = f"🌎 *Tasas desde {origin}*\n\n" + "\n\n".join(blocks)
            await _safe_edit(q, text, rates_country_result_buttons())
            return

        # 5. PAGINACIÓN
        if data.startswith("rates_more:page="):
            page = _parse_page(data)
            rv = get_latest_active_rate_version()
            if not rv:
                await _safe_edit(q, "Aún no hay tasas.")
                return

            all_pairs = list_all_route_pairs_for_version(rate_version_id=rv.id)
            popular_set = set(POPULAR_ROUTES)
            rest = [pair for pair in all_pairs if pair not in popular_set]
            rest = _sort_routes_dest_first(rest)

            total = len(rest)
            start = (page - 1) * PAGE_SIZE
            end = start + PAGE_SIZE
            page_pairs = rest[start:end]
            has_prev = page > 1
            has_next = end < total

            rates = list_route_rates_for_version(rate_version_id=rv.id, routes=page_pairs)
            rate_map = {(r.origin_country, r.dest_country): r for r in rates}

            blocks = []
            for (o, d) in page_pairs:
                rr = rate_map.get((o, d))
                if not rr:
                    continue
                blocks.append(f"{route_label(o, d)}\nTasa: {format_rate_no_noise(rr.rate_client)}")

            text = f"📋 *Todas las tasas* (Página {page})\n\n" + ("\n\n".join(blocks) if blocks else "No hay rutas.")
            await _safe_edit(q, text, rates_pagination_buttons(page=page, has_prev=has_prev, has_next=has_next))
            return

    except Exception as e:
        logger.error(f"Error en rates callback: {e}", exc_info=True)
        try:
            await q.answer("⚠️ Error temporal. Intenta de nuevo.", show_alert=True)
        except Exception:
            pass
