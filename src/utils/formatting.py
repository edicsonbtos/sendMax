from __future__ import annotations
from decimal import Decimal, ROUND_HALF_UP

def fmt_percent(x: Decimal) -> str:
    """
    Formatea decimal como porcentaje visible.
    0.06 → "6.00"
    0.025 → "2.50"
    """
    percent = Decimal(str(x)) * 100
    q = percent.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return format(q, "f")
