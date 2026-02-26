import logging

from telegram import Update
from telegram.ext import ContextTypes

from src.config.settings import settings
from src.rates_generator import generate_rates_full

logger = logging.getLogger("admin_rates")


async def rates_now(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Admin only: genera tasas ahora (baseline/manual) sin esperar 9am (ASYNC).
    """
    telegram_id = update.effective_user.id

    if not settings.is_admin_id(telegram_id):
        await update.message.reply_text("No autorizado.")
        return

    await update.message.reply_text("🔄 Actualizando tasas ahora…")

    try:
        # generate_rates_full ya es async
        res = await generate_rates_full(
            kind="auto_9am",
            reason="Admin forced baseline",
        )

        msg = (
            f"✅ Tasas actualizadas.\n"
            f"Versión: #{res.version_id}\n"
            f"Países OK: {len(res.countries_ok)} | Fallaron: {len(res.countries_failed)}"
        )
        await update.message.reply_text(msg)

        if res.any_unverified:
            await update.message.reply_text("⚠️ Aviso: se usó al menos un anuncio NO verificado (fallback).")

        if res.countries_failed:
            await update.message.reply_text(f"⚠️ Países sin datos: {', '.join(res.countries_failed)}")

    except Exception as e:
        logger.exception("Error en rates_now: %s", e)
        await update.message.reply_text("No pude obtener las tasas actuales, intenta de nuevo en unos segundos.")
