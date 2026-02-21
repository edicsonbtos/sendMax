from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

from telegram import Update
from telegram.ext import ContextTypes

from src.config.settings import settings
from src.db.repositories.referrals_repo import count_referrals, list_recent_referrals
from src.db.repositories.users_repo import get_user_by_telegram_id
from src.db.repositories.wallet_metrics_repo import get_wallet_metrics
from src.telegram_app.ui.keyboards import main_menu_keyboard
from src.telegram_app.ui.referrals_keyboards import referrals_menu_keyboard


def _is_admin(update: Update) -> bool:
    return settings.is_admin_id(getattr(update.effective_user, 'id', None))


def _ref_link(context: ContextTypes.DEFAULT_TYPE, alias: str) -> str:
    bot_username = context.bot.username
    return f"https://t.me/{bot_username}?start=ref_{alias}" if bot_username else "(link no disponible)"


def _f2(x: Decimal) -> str:
    return f"{Decimal(str(x)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)}"


async def enter_referrals(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    telegram_id = update.effective_user.id
    me = await get_user_by_telegram_id(telegram_id)
    if not me:
        await update.message.reply_text("Primero regístrate con /start.")
        return

    context.user_data["ref_mode"] = True
    context.user_data.pop("pm_mode", None)
    context.user_data.pop("summary_mode", None)
    context.user_data.pop("rates_mode", None)

    await update.message.reply_text(
        "🤝 Referidos\n\nElige una opción 👇",
        reply_markup=referrals_menu_keyboard(),
    )


async def referrals_router(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.user_data.get("ref_mode"):
        return

    telegram_id = update.effective_user.id
    me = await get_user_by_telegram_id(telegram_id)
    if not me:
        context.user_data.pop("ref_mode", None)
        await update.message.reply_text("Primero regístrate con /start.")
        return

    text = (update.message.text or "").strip()

    if text in ("⬅️ Volver", "🔙 Volver", "👈 Volver"):
        context.user_data.pop("ref_mode", None)
        await update.message.reply_text("Listo ✅", reply_markup=main_menu_keyboard(is_admin=_is_admin(update)))
        return

    if text in ("🔗 Mi link", "🧲 Mi link", "🔗 Mi Link"):
        link = _ref_link(context, me.alias)
        await update.message.reply_text(
            "🤝 Gana dinero recomendando operadores.\n\n"
            "Comparte este link con alguien que quiera trabajar con remesas y operar en Sendmax.\n"
            "Cuando se registre y haga envíos, recibirás comisiones automáticamente.\n\n"
            f"Tu link:\n{link}\n\n"
            "Acción rápida: copia el link y envíalo por WhatsApp."
        )
        return

    if text in ("📋 Mis referidos", "🧾 Resumen", "📌 Resumen", "📋 Resumen"):
        total = await count_referrals(me.id)
        recent = await list_recent_referrals(me.id, limit=10)

        lines = []
        lines.append("📋 Mis referidos")
        lines.append(f"Total: {total}")

        if recent:
            lines.append("")
            lines.append("Últimos referidos:")
            for r in recent:
                lines.append(f"- {r.alias}")
        else:
            lines.append("")
            lines.append("Aún no tienes referidos. Comparte tu link.")

        await update.message.reply_text("\n".join(lines))
        return

    if text in ("💰 Ganancias", "💵 Ganancias", "💰 Ganancias (mes)"):
        m = await get_wallet_metrics(me.id)
        await update.message.reply_text(
            "💰 Ganancias por referidos\n\n"
            f"- Referidos (mes): {_f2(m.referrals_month_usdt)} USDT\n\n"
            "Nota: el detalle completo está en 💼 Billetera."
        )
        return

    await update.message.reply_text("Usa los botones del menú de referidos 👇", reply_markup=referrals_menu_keyboard())
