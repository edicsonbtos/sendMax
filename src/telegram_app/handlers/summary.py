from __future__ import annotations

import asyncio
from decimal import ROUND_HALF_UP, Decimal

from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    Update,
)
from telegram.ext import CallbackQueryHandler, ContextTypes

from src.config.settings import settings
from src.db.connection import get_async_conn
from src.db.repositories.operator_summary_repo import list_recent_orders_for_operator
from src.db.repositories.users_repo import get_user_by_telegram_id
from src.db.repositories.wallet_metrics_repo import get_wallet_metrics
from src.telegram_app.ui.keyboards import main_menu_keyboard
from src.telegram_app.ui.routes_popular import COUNTRY_FLAGS, COUNTRY_LABELS

BTN_DASH = "📊 Dashboard"
BTN_HISTORY = "🧾 Historial (8)"
BTN_PROOF = "🧾 Comprobante"
BTN_PROFIT = "💰 Ganancias"
BTN_BACK = "⬅️ Volver"


def _is_admin(update: Update) -> bool:
    return settings.is_admin_id(getattr(update.effective_user, 'id', None))


def _fmt_money_latam(x: Decimal) -> str:
    q = Decimal(str(x)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    s = format(q, "f")
    whole, frac = s.split(".")
    parts = []
    while whole:
        parts.append(whole[-3:])
        whole = whole[:-3]
    return f"{'.'.join(reversed(parts))},{frac}"


def _status_dot(status: str) -> str:
    return {
        "CREADA": "🆕",
        "EN_PROCESO": "⏳",
        "PAGADA": "✅",
        "CANCELADA": "❌",
    }.get(status, "❔")


def _short_id(public_id: int) -> str:
    return f"{public_id % 1000:03d}"


def _summary_keyboard() -> ReplyKeyboardMarkup:
    keyboard = [
        [KeyboardButton(BTN_DASH), KeyboardButton(BTN_HISTORY)],
        [KeyboardButton(BTN_PROFIT), KeyboardButton(BTN_BACK)],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)


def _history_keyboard() -> ReplyKeyboardMarkup:
    keyboard = [
        [KeyboardButton(BTN_HISTORY), KeyboardButton(BTN_PROOF)],
        [KeyboardButton(BTN_DASH), KeyboardButton(BTN_BACK)],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)


async def _count_orders(operator_user_id: int, *, only_today: bool) -> dict[str, int]:
    if only_today:
        sql = """
            SELECT status, COUNT(*)
            FROM orders
            WHERE operator_user_id = %s
              AND created_at::date = CURRENT_DATE
            GROUP BY status;
        """
    else:
        sql = """
            SELECT status, COUNT(*)
            FROM orders
            WHERE operator_user_id = %s
            GROUP BY status;
        """

    out = {"CREADA": 0, "EN_PROCESO": 0, "PAGADA": 0, "CANCELADA": 0}
    async with get_async_conn() as conn:
        async with conn.cursor() as cur:
            await cur.execute(sql, (operator_user_id,))
            rows = await cur.fetchall()
            for status, cnt in rows:
                out[str(status)] = int(cnt)
    return out


async def _latest_paid(operator_user_id: int, limit: int = 3):
    sql = """
        SELECT public_id, origin_country, dest_country, amount_origin, payout_dest
        FROM orders
        WHERE operator_user_id = %s AND status = 'PAGADA'
        ORDER BY updated_at DESC
        LIMIT %s;
    """
    async with get_async_conn() as conn:
        async with conn.cursor() as cur:
            await cur.execute(sql, (operator_user_id, limit))
            return await cur.fetchall()


def _build_dashboard_text(user_alias: str, today_counts: dict[str, int], all_counts: dict[str, int], latest_paid_rows) -> str:
    total_today = sum(today_counts.values())
    total_all = sum(all_counts.values())

    lines = []
    lines.append("📊 Resumen (Dashboard)")
    lines.append(f"Operador: {user_alias}")
    lines.append("")
    lines.append("Hoy:")
    lines.append(f"- Total: {total_today}")
    lines.append(f"- 🆕 CREADA: {today_counts['CREADA']}")
    lines.append(f"- ⏳ EN PROCESO: {today_counts['EN_PROCESO']}")
    lines.append(f"- ✅ PAGADA: {today_counts['PAGADA']}")
    lines.append(f"- ❌ CANCELADA: {today_counts['CANCELADA']}")
    lines.append("")
    lines.append("Histórico:")
    lines.append(f"- Total: {total_all}")
    lines.append(f"- ✅ PAGADA: {all_counts['PAGADA']} | ⏳ EN PROCESO: {all_counts['EN_PROCESO']} | 🆕 CREADA: {all_counts['CREADA']} | ❌ CANCELADA: {all_counts['CANCELADA']}")
    lines.append("")

    if latest_paid_rows:
        lines.append("Últimas pagadas:")
        for public_id, o, d, amt, pay in latest_paid_rows:
            route = f"{COUNTRY_FLAGS[o]}->{COUNTRY_FLAGS[d]}"
            lines.append(f"- {_short_id(int(public_id))} {route} {_fmt_money_latam(Decimal(str(amt)))}→{_fmt_money_latam(Decimal(str(pay)))}")
    else:
        lines.append("Últimas pagadas: (aún no tienes)")

    lines.append("")
    lines.append("Tip: abre 🧾 Historial para ver comprobantes.")
    return "\n".join(lines)


async def _build_profit_text(me_id: int, alias: str) -> str:
    m = await get_wallet_metrics(me_id)
    def f2(x: Decimal) -> str:
        return f"{Decimal(str(x)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)}"

    lines = []
    lines.append("💰 Ganancias")
    lines.append(f"Operador: {alias}")
    lines.append("")
    lines.append(f"- Hoy: {f2(m.profit_today_usdt)} USDT")
    lines.append(f"- Mes: {f2(m.profit_month_usdt)} USDT")
    lines.append(f"- Referidos (mes): {f2(m.referrals_month_usdt)} USDT")
    return "\n".join(lines)


def _build_history_text(rows) -> str:
    lines = []
    lines.append("🧾 Historial (últimas 8)")
    lines.append("")
    for i, o in enumerate(rows, start=1):
        sid = _short_id(int(o.public_id))
        origin = o.origin_country
        dest = o.dest_country
        route = f"{COUNTRY_FLAGS[origin]} {COUNTRY_LABELS[origin]} -> {COUNTRY_FLAGS[dest]} {COUNTRY_LABELS[dest]}"
        money = f"{_fmt_money_latam(o.amount_origin)} -> {_fmt_money_latam(o.payout_dest)}"
        lines.append(f"{_status_dot(o.status)} {sid}  {route}")
        lines.append(f"   {money}")
        if i % 2 == 0 and i != len(rows):
            lines.append("")
    lines.append("")
    lines.append("Para ver un comprobante: pulsa '🧾 Comprobante'.")
    return "\n".join(lines)


def _proof_buttons(rows) -> InlineKeyboardMarkup:
    kb = []
    for o in rows:
        sid = _short_id(int(o.public_id))
        kb.append([InlineKeyboardButton(f"🧾 {sid}", callback_data=f"sum:proof:{int(o.public_id)}")])
    kb.append([InlineKeyboardButton("Cerrar", callback_data="sum:close")])
    return InlineKeyboardMarkup(kb)


async def enter_summary(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data.pop("pm_mode", None)
    context.user_data.pop("rates_mode", None)
    context.user_data.pop("ref_mode", None)

    telegram_id = update.effective_user.id
    me = await get_user_by_telegram_id(telegram_id)
    if not me:
        await update.message.reply_text("Primero regístrate con /start.")
        return

    context.user_data["summary_mode"] = True
    await update.message.reply_text("📊 Resumen\n\nElige una opción 👇", reply_markup=_summary_keyboard())


async def summary_router(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.user_data.get("summary_mode"):
        return

    telegram_id = update.effective_user.id
    me = await get_user_by_telegram_id(telegram_id)
    if not me:
        context.user_data.pop("summary_mode", None)
        await update.message.reply_text("Primero regístrate con /start.")
        return

    text = (update.message.text or "").strip()

    if text == BTN_BACK:
        context.user_data.pop("summary_mode", None)
        context.user_data.pop("summary_cache", None)
        await update.message.reply_text("Listo ✅", reply_markup=main_menu_keyboard(is_admin=_is_admin(update)))
        return

    if text == BTN_DASH:
        try:
            today_counts = await asyncio.wait_for(_count_orders(me.id, only_today=True), timeout=5.0)
            all_counts = await asyncio.wait_for(_count_orders(me.id, only_today=False), timeout=5.0)
            latest_paid_rows = await asyncio.wait_for(_latest_paid(me.id, limit=3), timeout=5.0)
            await update.message.reply_text(_build_dashboard_text(me.alias, today_counts, all_counts, latest_paid_rows), reply_markup=_summary_keyboard())
        except asyncio.TimeoutError:
            await update.message.reply_text("⏳ Timeout cargando dashboard.")
        return

    if text == BTN_HISTORY:
        try:
            rows = await asyncio.wait_for(list_recent_orders_for_operator(me.id, limit=8), timeout=5.0)
            if not rows:
                await update.message.reply_text("Aún no tienes operaciones 🧾", reply_markup=_summary_keyboard())
                return
            context.user_data["summary_cache"] = {int(o.public_id): o for o in rows}
            await update.message.reply_text(_build_history_text(rows), reply_markup=_history_keyboard())
        except asyncio.TimeoutError:
            await update.message.reply_text("⏳ Timeout cargando historial.")
        return

    if text == BTN_PROOF:
        try:
            rows = await asyncio.wait_for(list_recent_orders_for_operator(me.id, limit=8), timeout=5.0)
            if not rows:
                await update.message.reply_text("Aún no tienes operaciones 🧾", reply_markup=_summary_keyboard())
                return
            context.user_data["summary_cache"] = {int(o.public_id): o for o in rows}
            await update.message.reply_text("Elige la operación (últimos 3 dígitos) 👇", reply_markup=_proof_buttons(rows))
        except asyncio.TimeoutError:
            await update.message.reply_text("⏳ Timeout cargando comprobantes.")
        return

    if text == BTN_PROFIT:
        try:
            text_profit = await asyncio.wait_for(_build_profit_text(me.id, me.alias), timeout=5.0)
            await update.message.reply_text(text_profit, reply_markup=_summary_keyboard())
        except asyncio.TimeoutError:
            await update.message.reply_text("⏳ Timeout cargando ganancias.")
        return

    await update.message.reply_text("Usa los botones del resumen 👇", reply_markup=_summary_keyboard())


async def handle_summary_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    if not q:
        return

    data = q.data or ""
    if not data.startswith("sum:"):
        return

    await q.answer()

    if data == "sum:close":
        try:
            await q.message.delete()
        except Exception:
            pass
        return

    parts = data.split(":")
    if len(parts) != 3:
        return

    _, action, pid_str = parts
    if action != "proof":
        return

    try:
        public_id = int(pid_str)
    except Exception:
        return

    cache = context.user_data.get("summary_cache") or {}
    o = cache.get(public_id)
    if not o:
        await q.message.reply_text("No encontré esa operación. Vuelve a 🧾 Comprobante.")
        return

    if o.dest_payment_proof_file_id:
        await q.message.reply_photo(photo=o.dest_payment_proof_file_id, caption=f"Comprobante pago destino (#{_short_id(public_id)})")
    else:
        await q.message.reply_photo(photo=o.origin_payment_proof_file_id, caption=f"Comprobante pago origen (#{_short_id(public_id)})")


def build_summary_callback_handler() -> CallbackQueryHandler:
    return CallbackQueryHandler(handle_summary_callbacks, pattern=r"^sum:")
