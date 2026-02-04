from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes

from src.config.settings import settings
from src.telegram_app.ui.admin_keyboards import admin_panel_keyboard, admin_reset_confirm_keyboard
from src.telegram_app.ui.keyboards import main_menu_keyboard

from src.telegram_app.handlers.admin_orders import admin_orders
from src.telegram_app.handlers.admin_rates import rates_now
from src.telegram_app.handlers.admin_alert_test import alert_test

import psycopg


def _is_admin(update: Update) -> bool:
    return settings.is_admin_id(getattr(update.effective_user, "id", None))


def _db_conn():
    return psycopg.connect(settings.DATABASE_URL)


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
    (Solo se usa si el usuario es admin y presiona botones del panel.)
    """
    if not _is_admin(update):
        return

    text = (update.message.text or "").strip()

    if text == "⬅️ Menú":
        await update.message.reply_text(
            "Listo ✅",
            reply_markup=main_menu_keyboard(is_admin=True),
        )
        return

    if text == "📋 Órdenes (CREADA)":
        # reutiliza el handler existente
        await admin_orders(update, context)
        return

    if text == "🔄 Tasas ahora":
        # reutiliza /rates_now como función
        await rates_now(update, context)
        return

    if text == "🧪 Alerta test":
        await alert_test(update, context)
        return

    if text == "🧨 Reset (modo prueba)":
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

    if text == "✅ Sí, resetear TODO":
        if not context.user_data.get("awaiting_reset_confirm"):
            await update.message.reply_text("Primero pulsa 🧨 Reset (modo prueba).")
            return

        context.user_data.pop("awaiting_reset_confirm", None)

        # Reset seguro: borrar en orden para no romper FKs
        admin_telegram = int(settings.ADMIN_TELEGRAM_USER_ID)

        try:
            with _db_conn() as conn:
                with conn.cursor() as cur:
                    # 1) órdenes
                    cur.execute("DELETE FROM orders;")

                    # 2) tasas (rutas y precios dependen de rate_versions)
                    cur.execute("DELETE FROM route_rates;")
                    cur.execute("DELETE FROM p2p_country_prices;")
                    cur.execute("DELETE FROM rate_versions;")

                    # 3) usuarios (mantener admin)
                    cur.execute("DELETE FROM users WHERE telegram_user_id <> %s;", (admin_telegram,))

                conn.commit()

            await update.message.reply_text("✅ Reset completo. Base lista para producción.", reply_markup=main_menu_keyboard(is_admin=True))

        except Exception as e:
            await update.message.reply_text(f"⚠️ Falló el reset: {e}")

        return

    if text == "❌ Cancelar reset":
        context.user_data.pop("awaiting_reset_confirm", None)
        await update.message.reply_text("Reset cancelado ✅", reply_markup=admin_panel_keyboard())
        return

