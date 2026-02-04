from __future__ import annotations

import psycopg
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler

from src.config.settings import settings


def _is_admin(update: Update) -> bool:
    return settings.is_admin_id(getattr(update.effective_user, "id", None))


async def set_sponsor_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_admin(update):
        return

    if not context.args or len(context.args) < 2:
        await update.message.reply_text("Uso: /set_sponsor <alias_hijo> <alias_padrino>")
        return

    child_alias = (context.args[0] or "").strip()
    sponsor_alias = (context.args[1] or "").strip()

    if not child_alias or not sponsor_alias:
        await update.message.reply_text("Alias inválidos.")
        return

    if child_alias.lower() == sponsor_alias.lower():
        await update.message.reply_text("No puedes asignar un usuario como su propio padrino.")
        return

    with psycopg.connect(settings.DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id, alias FROM users WHERE alias=%s LIMIT 1;", (child_alias,))
            child = cur.fetchone()
            if not child:
                await update.message.reply_text(f"No encontré al hijo con alias: {child_alias}")
                return
            child_id, child_alias_db = int(child[0]), child[1]

            cur.execute("SELECT id, alias FROM users WHERE alias=%s LIMIT 1;", (sponsor_alias,))
            sp = cur.fetchone()
            if not sp:
                await update.message.reply_text(f"No encontré al padrino con alias: {sponsor_alias}")
                return
            sponsor_id, sponsor_alias_db = int(sp[0]), sp[1]

            cur.execute(
                "UPDATE users SET sponsor_id=%s, updated_at=now() WHERE id=%s;",
                (sponsor_id, child_id),
            )
        conn.commit()

    await update.message.reply_text(
        f"✅ Sponsor actualizado.\nHijo: {child_alias_db} (id={child_id})\nPadrino: {sponsor_alias_db} (id={sponsor_id})"
    )


def build_set_sponsor_handler() -> CommandHandler:
    return CommandHandler("set_sponsor", set_sponsor_cmd)
