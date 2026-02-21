from __future__ import annotations

import logging
from pydantic_settings import BaseSettings, SettingsConfigDict
from src.db.settings_store import get_setting_float

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

    PAYMENT_METHODS_VENEZUELA: str | None = None
    PAYMENT_METHODS_USA: str | None = None
    PAYMENT_METHODS_CHILE: str | None = None
    PAYMENT_METHODS_PERU: str | None = None
    PAYMENT_METHODS_COLOMBIA: str | None = None
    PAYMENT_METHODS_MEXICO: str | None = None
    PAYMENT_METHODS_ARGENTINA: str | None = None

    COMMISSION_VENEZUELA: float = 6.0
    COMMISSION_DEFAULT: float = 10.0
    COMMISSION_USA_TO_VENEZUELA: float = 10.0

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

    def commission_pct(self, origin: str, dest: str) -> float:
        origin_u = (origin or "").upper()
        dest_u = (dest or "").upper()

        default_margin = float(self.COMMISSION_DEFAULT)
        vene_margin = float(self.COMMISSION_VENEZUELA)
        usa_ve_margin = float(self.COMMISSION_USA_TO_VENEZUELA)

        default_margin = get_setting_float("margin_default", "percent", default_margin)
        vene_margin = get_setting_float("margin_dest_venez", "percent", vene_margin)
        usa_ve_margin = get_setting_float("margin_route_usa_venez", "percent", usa_ve_margin)

        if dest_u == "VENEZUELA" and origin_u == "USA":
            return _clamp_commission(float(usa_ve_margin), "usa->venez")
        if dest_u == "VENEZUELA":
            return _clamp_commission(float(vene_margin), "->venez")
        return _clamp_commission(float(default_margin), "default")


settings = Settings()