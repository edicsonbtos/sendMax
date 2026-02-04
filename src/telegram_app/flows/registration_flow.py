"""
Flujo de registro (ConversationHandler):

Objetivo:
- Si el usuario no existe, pedir alias (3-15 chars, letras/números/_)
- Opcional: si viene con /start ref_xxx, asociar sponsor (padrino) por alias.
- Guardar en DB.
- Al finalizar, mostrar menú fijo (UI tipo app) usando show_home().
"""

import re
from telegram import Update
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CommandHandler,
    MessageHandler,
    filters,
)

from src.db.repositories.users_repo import (
    get_user_by_telegram_id,
    get_user_by_alias,
    create_user,
)

from src.telegram_app.handlers.menu import show_home

ASK_ALIAS = 1
ALIAS_REGEX = re.compile(r"^[a-zA-Z0-9_]{3,15}$")


def parse_sponsor_alias_from_start_args(context: ContextTypes.DEFAULT_TYPE) -> str | None:
    """
    Lee el argumento de /start:
    - esperado: ref_<alias>
      Ej: /start ref_rigo_01
    """
    if not context.args:
        return None

    raw = (context.args[0] or "").strip()
    if raw.startswith("ref_") and len(raw) > 4:
        return raw.replace("ref_", "", 1).strip()
    return None


async def start_registration(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Entrada al flujo:
    - Si usuario ya existe: mostramos menú directamente.
    - Si no existe: pedimos alias.
    """
    telegram_id = update.effective_user.id
    existing = get_user_by_telegram_id(telegram_id)

    if existing:
        # Experiencia tipo app: no saturar con texto, ir directo al menú
        await show_home(update, context, alias=existing.alias)
        return ConversationHandler.END

    await update.message.reply_text(
        "Bienvenido a *Sendmax*.\n\n"
        "Para comenzar, crea tu alias único.\n"
        "• 3 a 15 caracteres\n"
        "• Solo letras, números y '_' \n"
        "Ejemplo: `rigo_01`",
        parse_mode="Markdown",
    )
    return ASK_ALIAS


async def receive_alias(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    alias = (update.message.text or "").strip()

    # Validación de formato
    if not ALIAS_REGEX.match(alias):
        await update.message.reply_text(
            "Alias inválido.\n\n"
            "Usa 3-15 caracteres y solo letras, números y '_'.\n"
            "Ejemplo: rigo_01\n\n"
            "Intenta de nuevo:"
        )
        return ASK_ALIAS

    # Validación de disponibilidad (case-insensitive por CITEXT en DB)
    if get_user_by_alias(alias):
        await update.message.reply_text("Ese alias ya existe. Escribe otro:")
        return ASK_ALIAS

    telegram_id = update.effective_user.id

    # Sponsor (padrino) si viene en /start ref_xxx
    sponsor_alias = parse_sponsor_alias_from_start_args(context)
    sponsor_id = None
    if sponsor_alias:
        sponsor = get_user_by_alias(sponsor_alias)
        if sponsor:
            sponsor_id = sponsor.id

    # Crear usuario
    user = create_user(
        telegram_user_id=telegram_id,
        alias=alias,
        sponsor_id=sponsor_id,
    )

    # Mostrar menú fijo (sin ruido)
    await show_home(update, context, alias=user.alias)
    return ConversationHandler.END


async def cancel_registration(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Registro cancelado.")
    return ConversationHandler.END


def build_registration_conversation() -> ConversationHandler:
    """
    ConversationHandler para /start:
    - entry_points: /start
    - states: ASK_ALIAS
    - fallbacks: /cancel
    """
    return ConversationHandler(
        entry_points=[CommandHandler("start", start_registration)],
        states={
            ASK_ALIAS: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_alias)]
        },
        fallbacks=[CommandHandler("cancel", cancel_registration)],
        allow_reentry=True,
    )