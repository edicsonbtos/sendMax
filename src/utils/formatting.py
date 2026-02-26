from __future__ import annotations
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime

def fmt_money(x: Decimal | float) -> str:
    """Formatea monto con separador de miles (.) y decimales (,) - Estilo ES"""
    if x is None:
        return "0,00"
    q = Decimal(str(x)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    s = format(q, "f")
    whole, frac = s.split(".")
    parts = []
    while whole:
        parts.append(whole[-3:])
        whole = whole[:-3]
    return f"{'.'.join(reversed(parts))},{frac}"


def fmt_public_id(public_id: int | str) -> str:
    """Formatea ID público con año: YYYY-XXXXXX"""
    try:
        pid = int(public_id)
    except (ValueError, TypeError):
        return str(public_id)
    year = datetime.now().year
    return f"{year}-{pid:06d}"


def fmt_percent(val: float | Decimal | None) -> str:
    """
    Formatea decimal como porcentaje visible.
    0.06 → "6.00%"
    6.0 → "6.00%" (auto-detección de escala)
    """
    if val is None:
        return "0.00%"

    f_val = float(val)
    # Si es mayor a 1, probablemente ya viene como porcentaje (6.0 en vez de 0.06)
    if f_val > 1:
        f_val = f_val / 100

    percent = Decimal(str(f_val)) * 100
    q = percent.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return f"{format(q, 'f')}%"
