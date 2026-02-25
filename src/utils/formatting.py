from __future__ import annotations
from decimal import Decimal, ROUND_HALF_UP

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
