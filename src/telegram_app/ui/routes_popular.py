"""
Rutas populares + helpers de UI (banderas, nombres, formato de tasa).

Objetivo:
- Tener un solo lugar para:
  - nombres de países
  - banderas
  - lista de rutas populares
  - formateo de tasa "sin ruido"
"""

from __future__ import annotations

from decimal import Decimal


COUNTRY_LABELS = {
    "USA": "USA",
    "CHILE": "Chile",
    "PERU": "Perú",
    "COLOMBIA": "Colombia",
    "VENEZUELA": "Venezuela",
    "ARGENTINA": "Argentina",
    "MEXICO": "México",
}

COUNTRY_FLAGS = {
    "USA": "🇺🇸",
    "CHILE": "🇨🇱",
    "PERU": "🇵🇪",
    "COLOMBIA": "🇨🇴",
    "VENEZUELA": "🇻🇪",
    "ARGENTINA": "🇦🇷",
    "MEXICO": "🇲🇽",
}

POPULAR_ROUTES = [
    ("USA", "VENEZUELA"),
    ("CHILE", "VENEZUELA"),
    ("PERU", "VENEZUELA"),
    ("USA", "CHILE"),
    ("CHILE", "PERU"),
    ("CHILE", "COLOMBIA"),
    ("USA", "COLOMBIA"),
    ("USA", "MEXICO"),
]


def route_label(origin: str, dest: str) -> str:
    return f"{COUNTRY_FLAGS[origin]} {COUNTRY_LABELS[origin]} -> {COUNTRY_FLAGS[dest]} {COUNTRY_LABELS[dest]}"


def format_rate_no_noise(rate: Decimal) -> str:
    """
    Regla acordada:
    - Si rate >= 1:
      - si entero exacto -> "1"
      - si no -> 2 decimales ("1.03")
    - Si 0 < rate < 1:
      - mostrar 3 dígitos significativos
      - conservar ceros líderes (ej 0.000222 -> "0.000222")
      - ej 0.875377... -> "0.875"
    """
    if rate <= 0:
        return str(rate)

    if rate >= 1:
        # entero exacto
        if rate == rate.to_integral_value():
            return str(rate.quantize(Decimal("1")))
        return f"{rate.quantize(Decimal('0.01'))}"

    # 0 < rate < 1
    s = format(rate, "f")  # decimal sin notación científica
    if "." not in s:
        return s

    int_part, frac = s.split(".", 1)

    # contar ceros líderes en la parte fraccionaria
    zeros = 0
    for ch in frac:
        if ch == "0":
            zeros += 1
        else:
            break

    # tomamos 3 dígitos significativos después de los ceros
    significant = frac[zeros:zeros + 3]
    if not significant:
        # caso extremo: es algo como 0.0000...
        return "0"

    out_frac = frac[:zeros] + significant
    return f"0.{out_frac}".rstrip("0").rstrip(".")