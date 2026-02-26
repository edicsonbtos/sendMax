from __future__ import annotations
from src.utils.formatting import fmt_money, fmt_public_id
from src.telegram_app.ui.routes_popular import COUNTRY_LABELS
from src.telegram_app.utils.text_escape import esc_html

# Mapping from country code to its fiat currency
ORIGIN_FIAT_CURRENCY = {
    "PERU": "PEN",
    "CHILE": "CLP",
    "VENEZUELA": "VES",
    "COLOMBIA": "COP",
    "USA": "USD",
    "MEXICO": "MXN",
    "ARGENTINA": "ARS",
}

def format_origin_group_message(order) -> str:
    """Template para el grupo de ORIGEN (validación de depósito)"""
    origin = getattr(order, "origin_country", "")
    amount_origin = getattr(order, "amount_origin", 0)
    public_id = getattr(order, "public_id", "0")

    currency = ORIGIN_FIAT_CURRENCY.get(str(origin).upper(), str(origin))
    country_name = COUNTRY_LABELS.get(str(origin).upper(), str(origin))

    return (
        f"ORIGEN: {country_name} {fmt_money(amount_origin)} {currency}\n"
        f"Orden #{fmt_public_id(public_id)}"
    )

def format_payments_group_message(order) -> str:
    """Template para el grupo de PAGOS (ejecución del pago destino)"""
    dest = getattr(order, "dest_country", "")
    payout_dest = getattr(order, "payout_dest", 0)
    beneficiary = (getattr(order, "beneficiary_text", "") or "").strip()
    public_id = getattr(order, "public_id", "0")

    currency = ORIGIN_FIAT_CURRENCY.get(str(dest).upper(), str(dest))

    # Usar esc_html para los datos del beneficiario para evitar romper el parse_mode HTML
    return (
        f"PAGAR: {fmt_money(payout_dest)} {currency}\n"
        f"A: {esc_html(beneficiary)}\n"
        f"Orden #{fmt_public_id(public_id)}"
    )
