from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes

from src.config.settings import settings
from src.db.connection import get_async_conn
from src.telegram_app.handlers.admin_alert_test import alert_test
from src.telegram_app.handlers.admin_orders import admin_orders
from src.telegram_app.handlers.admin_rates import rates_now
from src.telegram_app.ui.admin_keyboards import (
    BTN_ADMIN_BROADCAST,
    admin_panel_keyboard,
    admin_reset_confirm_keyboard,
)
from src.telegram_app.ui.keyboards import main_menu_keyboard
from src.telegram_app.ui.labels import (
    BTN_ADMIN_ALERT_TEST,
    BTN_ADMIN_MENU,
    BTN_ADMIN_ORDERS,
    BTN_ADMIN_RATES_NOW,
    BTN_ADMIN_TREASURY,
    BTN_ADMIN_RESET,
    BTN_ADMIN_RESET_CANCEL,
    BTN_ADMIN_RESET_YES,
    BTN_ADMIN_WITHDRAWALS,
)


def _is_admin(update: Update) -> bool:
    return settings.is_admin_id(getattr(update.effective_user, "id", None))


async def open_admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Abre el panel admin (solo admin).
    """
    if not _is_admin(update):
        return

    await update.message.reply_text(
        "🛠 Panel Admin\n\nElige una opción:",
        reply_markup=admin_panel_keyboard(),
    )


async def admin_panel_router(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Router de botones del panel admin.
    """
    if not _is_admin(update):
        return

    text = (update.message.text or "").strip()

    if text == BTN_ADMIN_MENU:
        await update.message.reply_text(
            "Listo ✅",
            reply_markup=main_menu_keyboard(is_admin=True),
        )
        return

    if text == BTN_ADMIN_ORDERS:
        await admin_orders(update, context)
        return

    if text == BTN_ADMIN_WITHDRAWALS:
        from src.telegram_app.handlers.admin_withdrawals import admin_withdrawals_list
        await admin_withdrawals_list(update, context)
        return

    if text == BTN_ADMIN_RATES_NOW:
        await rates_now(update, context)
        return

    if text == BTN_ADMIN_ALERT_TEST:
        await alert_test(update, context)
        return

    if text == BTN_ADMIN_TREASURY:
        from src.db.repositories.users_repo import ensure_treasury_user
        from src.db.repositories.wallet_repo import get_balance
        tid = await ensure_treasury_user()
        bal = await get_balance(tid)
        await update.message.reply_text(
            f"💰 **Treasury Wallet**\n\n"
            f"Saldo actual: `{bal:.2f} USDT`\n\n"
            f"Para ajustar use:\n`/adj_treasury <monto> <memo>`\n"
            f"(Ej: `/adj_treasury 1500 Inversion inicial`)",
            parse_mode="Markdown"
        )
        return

    if text == BTN_ADMIN_BROADCAST:
        from src.telegram_app.handlers.admin_broadcast import start_broadcast
        return await start_broadcast(update, context)

    if text == BTN_ADMIN_RESET:
        context.user_data["awaiting_reset_confirm"] = True
        await update.message.reply_text(
            "⚠️ Reset de datos (modo prueba)\n\n"
            "Esto borrará:\n"
            "• Órdenes\n"
            "• Tasas/versiones\n"
            "• Usuarios (excepto admin)\n\n"
            "¿Seguro que deseas resetear TODO?",
            reply_markup=admin_reset_confirm_keyboard(),
        )
        return

    if text == BTN_ADMIN_RESET_YES:
        if not context.user_data.get("awaiting_reset_confirm"):
            await update.message.reply_text(f"Primero pulsa {BTN_ADMIN_RESET}.")
            return

        context.user_data.pop("awaiting_reset_confirm", None)

        admin_telegram = int(settings.ADMIN_TELEGRAM_USER_ID)
        from src.db.repositories.users_repo import ensure_treasury_user
        treasury_id = await ensure_treasury_user()

        try:
            async with get_async_conn() as conn:
                async with conn.cursor() as cur:
                    await cur.execute("DELETE FROM wallet_ledger;")
                    await cur.execute("DELETE FROM order_trades;")
                    await cur.execute("DELETE FROM orders;")
                    await cur.execute("DELETE FROM withdrawals;")
                    await cur.execute("DELETE FROM user_contacts;")

                    # Limpiar tablas de origen (con try/except para robustez ante cambios de esquema)
                    for table in ["origin_sweeps", "origin_wallet_closures", "origin_receipts_daily"]:
                        try:
                            await cur.execute(f"DELETE FROM {table};")
                        except Exception:
                            pass

                    await cur.execute("DELETE FROM route_rates;")
                    await cur.execute("DELETE FROM p2p_country_prices;")
                    await cur.execute("DELETE FROM rate_versions;")

                    # Borrar usuarios (CASCADE borra wallets/ledger si no los borramos antes)
                    # Protegemos admin y treasury
                    await cur.execute(
                        "DELETE FROM users WHERE telegram_user_id <> %s AND alias <> 'TREASURY' AND id <> %s;",
                        (admin_telegram, treasury_id)
                    )

                    # Reset balances de los que quedaron (admin y treasury)
                    await cur.execute("UPDATE wallets SET balance_usdt = 0, updated_at = now();")

                await conn.commit()

            await update.message.reply_text("✅ Reset completo (Hard Reset operativo).", reply_markup=main_menu_keyboard(is_admin=True))

        except Exception as e:
            logger.exception("Reset All failed")
            await update.message.reply_text(f"⚠️ Falló el reset: {e}")

        return

    if text == BTN_ADMIN_RESET_CANCEL:
        context.user_data.pop("awaiting_reset_confirm", None)
        await update.message.reply_text("Reset cancelado ✅", reply_markup=admin_panel_keyboard())
        return
