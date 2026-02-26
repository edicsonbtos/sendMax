from __future__ import annotations

import logging
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)

_COMMISSION_MIN = 0.0
_COMMISSION_MAX = 50.0


def _clamp_commission(val: float, label: str) -> float:
    if val < _COMMISSION_MIN:
        logger.error("commission_pct '%s' debajo del minimo: %.4f -> clamped a %.1f", label, val, _COMMISSION_MIN)
        return _COMMISSION_MIN
    if val > _COMMISSION_MAX:
        logger.error("commission_pct '%s' encima del maximo: %.4f -> clamped a %.1f", label, val, _COMMISSION_MAX)
        return _COMMISSION_MAX
    return val


class Settings(BaseSettings):
    TELEGRAM_BOT_TOKEN: str
    DATABASE_URL: str
    ENV: str = "SANDBOX"

    WEBHOOK_URL: str | None = None
    PORT: int = 8080  # Railway usa $PORT; este default es solo fallback local

    SUPPORT_WHATSAPP_NUMBER: str = "584242686434"

    ADMIN_TELEGRAM_USER_ID: int | None = None
    ADMIN_TELEGRAM_USER_IDS: str | None = None

    ALERTS_TELEGRAM_CHAT_ID: int | None = None
    PAYMENTS_TELEGRAM_CHAT_ID: int | None = None
    KYC_TELEGRAM_CHAT_ID: int | None = None
    ORIGIN_REVIEW_TELEGRAM_CHAT_ID: int | None = None

    FLOW_DEBUG: int = 0
    ALLOW_REMOTE_RATES_REGEN: bool = False

    PAYMENT_METHODS_VENEZUELA: str | None = None
    PAYMENT_METHODS_USA: str | None = None
    PAYMENT_METHODS_CHILE: str | None = None
    PAYMENT_METHODS_PERU: str | None = None
    PAYMENT_METHODS_COLOMBIA: str | None = None
    PAYMENT_METHODS_MEXICO: str | None = None
    PAYMENT_METHODS_ARGENTINA: str | None = None

    # Fallbacks en formato DECIMAL (0.06 = 6%)
    # Estos valores SOLO se usan si DB y .env fallan
    COMMISSION_VENEZUELA: float = 0.06        # 6%
    COMMISSION_DEFAULT: float = 0.10          # 10%
    COMMISSION_USA_TO_VENEZUELA: float = 0.10 # 10%

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def admin_user_ids(self) -> set[int]:
        ids: set[int] = set()

        if self.ADMIN_TELEGRAM_USER_ID:
            ids.add(int(self.ADMIN_TELEGRAM_USER_ID))

        if self.ADMIN_TELEGRAM_USER_IDS:
            for part in self.ADMIN_TELEGRAM_USER_IDS.split(","):
                part = part.strip()
                if not part:
                    continue
                try:
                    ids.add(int(part))
                except (ValueError, TypeError):
                    logger.error(
                        "ADMIN_TELEGRAM_USER_IDS valor invalido: '%s' (ignorado)", part
                    )

        if not ids:
            logger.warning("No hay admin IDs configurados (funciones admin deshabilitadas)")

        return ids

    def is_admin_id(self, telegram_user_id: int | None) -> bool:
        if telegram_user_id is None:
            return False
        return int(telegram_user_id) in self.admin_user_ids

    def payment_methods_text(self, country: str) -> str | None:
        key = "PAYMENT_METHODS_%s" % country
        raw = getattr(self, key, None)
        if not raw:
            return None
        return raw.replace("\\n", "\n")

    def commission_pct(
        self,
        origin: str,
        dest: str,
        *,
        override_default: float | None = None,
        override_venez: float | None = None,
        override_usa_venez: float | None = None
    ) -> float:
        """
        LEGACY: Solo para compatibilidad con rates_generator.
        NUEVO código debe usar: from src.config.dynamic_settings import dynamic_config
                               pct = await dynamic_config.get_commission_pct(origin, dest)
        """
        origin_u = (origin or "").upper()
        dest_u = (dest or "").upper()

        # Usa overrides (para rates_generator) o fallbacks DECIMALES
        m_default = override_default if override_default is not None else self.COMMISSION_DEFAULT
        m_venez = override_venez if override_venez is not None else self.COMMISSION_VENEZUELA
        m_usa_venez = override_usa_venez if override_usa_venez is not None else self.COMMISSION_USA_TO_VENEZUELA

        if dest_u == "VENEZUELA" and origin_u == "USA":
            return _clamp_commission(m_usa_venez, "usa->venez")
        if dest_u == "VENEZUELA":
            return _clamp_commission(m_venez, "->venez")
        return _clamp_commission(m_default, "default")


settings = Settings()