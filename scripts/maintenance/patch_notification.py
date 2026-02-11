import re
from pathlib import Path

target_file = Path("src/telegram_app/flows/new_order_flow.py")
text = target_file.read_text(encoding="utf-8")

# 1. Agregar Imports faltantes (para los botones) sin borrar los existentes
if "InlineKeyboardMarkup" not in text:
    text = text.replace(
        "from telegram import Update, ReplyKeyboardMarkup, KeyboardButton",
        "from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton"
    )

# 2. Definimos la NUEVA función de notificación (Envía al grupo + Botones)
new_function = '''async def _notify_admin_new_order(context: ContextTypes.DEFAULT_TYPE, order) -> None:
    # PRIORIDAD: Grupo de pagos. Si no, Admin personal.
    target_chat_id = settings.PAYMENTS_TELEGRAM_CHAT_ID or settings.ADMIN_TELEGRAM_USER_ID
    if not target_chat_id:
        return

    origin = order.origin_country
    dest = order.dest_country

    summary = (
        "🔔 <b>NUEVA ORDEN</b>\\n\\n"
        f"🆔 <b>#{_fmt_public_id(order.public_id)}</b>\\n"
        f"Ruta: {COUNTRY_FLAGS[origin]} {COUNTRY_LABELS[origin]} -> {COUNTRY_FLAGS[dest]} {COUNTRY_LABELS[dest]}\\n"
        f"Monto: <b>{_fmt_money(order.amount_origin)}</b>\\n"
        f"Tasa: {_fmt_rate(order.rate_client)}\\n"
        f"Pago Destino: <b>{_fmt_money(order.payout_dest)}</b>\\n"
        f"Estado: {order.status}"
    )

    benef_only = f"📋 <b>Datos Beneficiario:</b>\\n{order.beneficiary_text or ''}"

    # Botones de acción directa (coinciden con admin_orders.py)
    kb = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("⏳ EN PROCESO", callback_data=f"ord:proc:{order.public_id}"),
            InlineKeyboardButton("✅ PAGADA", callback_data=f"ord:paid:{order.public_id}"),
        ],
        [
            InlineKeyboardButton("❌ CANCELAR", callback_data=f"ord:cancel:{order.public_id}"),
        ]
    ])

    try:
        # 1. Foto Comprobante
        if order.origin_payment_proof_file_id:
             await context.bot.send_photo(
                chat_id=target_chat_id,
                photo=order.origin_payment_proof_file_id,
                caption=f"🧾 Comprobante Origen #{_fmt_public_id(order.public_id)}"
            )
        
        # 2. Resumen con botones
        await context.bot.send_message(
            chat_id=target_chat_id, 
            text=summary, 
            parse_mode="HTML",
            reply_markup=kb
        )

        # 3. Beneficiario (mensaje aparte para copiar fácil)
        await context.bot.send_message(
            chat_id=target_chat_id, 
            text=benef_only,
            parse_mode="HTML"
        )
    except Exception as e:
        print(f"Error notificando nueva orden: {e}")
'''

# 3. Aplicar el reemplazo usando Regex
# Buscamos desde "async def _notify_admin_new_order" hasta justo antes de "async def _show_confirm_screen"
pattern = r"(async def _notify_admin_new_order[\s\S]*?)(?=\nasync def _show_confirm_screen)"

updated_text = re.sub(pattern, new_function, text, count=1)

if updated_text != text:
    target_file.write_text(updated_text, encoding="utf-8")
    print("✅ Parche aplicado: new_order_flow.py actualizado con éxito.")
else:
    print("⚠️ No se encontró la función antigua o el archivo ya estaba modificado.")
