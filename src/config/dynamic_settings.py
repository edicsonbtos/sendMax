"""
Sistema de configuración dinámico con jerarquía:
1. DB (settings table) - PRIORIDAD MÁXIMA
2. Variables de entorno (.env)
3. Fallback hardcoded (settings.py)

Cache: 60s por configuración
Audit log: todos los cambios quedan registrados
"""

from __future__ import annotations
from decimal import Decimal
from typing import Literal
import logging
from src.db.settings_store import get_setting_json
from src.config.settings import settings as static_settings

logger = logging.getLogger(__name__)

CommissionType = Literal["default", "venezuela", "usa_to_venezuela"]

class DynamicConfig:
    """Gestor de configuración dinámica con jerarquía."""

    async def get_commission_pct(
        self,
        origin: str,
        dest: str,
    ) -> Decimal:
        """
        Obtiene % comisión con jerarquía:
        1. Ruta específica (DB: commission_routes → {CHILE_VENEZUELA: 0.02})
        2. Por destino (DB: margin_dest_venez → {"percent": 0.03})
        3. Por origen (DB: margin_origin_chile → {"percent": 0.04})
        4. Default (DB: margin_default → {"percent": 0.05})
        5. Fallback hardcoded (settings.COMMISSION_DEFAULT)

        Retorna SIEMPRE decimal (0.06 = 6%)
        """
        origin_u = origin.upper()
        dest_u = dest.upper()

        # 1. Ruta específica (nueva funcionalidad)
        route_key = f"{origin_u}_{dest_u}"
        routes_config = await get_setting_json("commission_routes")
        if routes_config and route_key in routes_config:
            try:
                val = Decimal(str(routes_config[route_key]))
                logger.info(f"Commission route {route_key}: {val} (from DB)")
                return self._clamp(val, f"route:{route_key}")
            except Exception as e:
                logger.warning(f"Invalid route commission {route_key}: {e}")

        # 2. Por destino (legacy compatible)
        if dest_u == "VENEZUELA":
            if origin_u == "USA":
                val = await self._get_from_db("margin_route_usa_venez", "percent",
                                               static_settings.COMMISSION_USA_TO_VENEZUELA)
                return self._clamp(val, "usa->venez")
            val = await self._get_from_db("margin_dest_venez", "percent",
                                          static_settings.COMMISSION_VENEZUELA)
            return self._clamp(val, "dest:venezuela")

        # 3. Por origen (nueva funcionalidad)
        origin_key = f"margin_origin_{origin_u.lower()}"
        origin_val = await self._get_from_db(origin_key, "percent", None)
        if origin_val is not None:
            return self._clamp(origin_val, f"origin:{origin_u}")

        # 4. Default
        val = await self._get_from_db("margin_default", "percent",
                                      static_settings.COMMISSION_DEFAULT)
        return self._clamp(val, "default")

    async def _get_from_db(self, key: str, field: str, fallback: float | None) -> Decimal | None:
        """Lee valor de settings.value_json con fallback."""
        try:
            from src.db.settings_store import get_setting_float
            val = await get_setting_float(key, field, fallback if fallback is not None else 0.0)
            if fallback is None and val == 0.0:
                # Verificar si realmente es 0 o si no existe
                data = await get_setting_json(key)
                if not data or field not in data:
                    return None
            return Decimal(str(val))
        except Exception as e:
            logger.warning(f"Error reading {key}.{field} from DB: {e}")
            return Decimal(str(fallback)) if fallback is not None else None

    def _clamp(self, val: Decimal, label: str) -> Decimal:
        """Valida que comisión esté en rango [0, 0.50]."""
        MIN_COMMISSION = Decimal("0.0")
        MAX_COMMISSION = Decimal("0.50")  # 50% máximo

        if val < MIN_COMMISSION:
            logger.error(f"Commission '{label}' below minimum: {val} -> clamped to {MIN_COMMISSION}")
            return MIN_COMMISSION
        if val > MAX_COMMISSION:
            logger.error(f"Commission '{label}' above maximum: {val} -> clamped to {MAX_COMMISSION}")
            return MAX_COMMISSION
        return val

    async def get_profit_split(self) -> dict[str, Decimal]:
        """
        Lee split de profit desde DB.
        Fallback: 45% op / 10% sponsor / 45% empresa
        """
        config = await get_setting_json("profit_split")
        if config:
            try:
                return {
                    "operator_with_sponsor": Decimal(str(config.get("operator_with_sponsor", "0.45"))),
                    "sponsor": Decimal(str(config.get("sponsor", "0.10"))),
                    "operator_solo": Decimal(str(config.get("operator_solo", "0.50"))),
                }
            except Exception as e:
                logger.warning(f"Invalid profit_split config: {e}")

        # Fallback hardcoded
        return {
            "operator_with_sponsor": Decimal("0.45"),
            "sponsor": Decimal("0.10"),
            "operator_solo": Decimal("0.50"),
        }

# Singleton global
dynamic_config = DynamicConfig()
