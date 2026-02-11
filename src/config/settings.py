from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict
from src.db.settings_store import get_setting_float


class Settings(BaseSettings):
    # Core
    TELEGRAM_BOT_TOKEN: str
    DATABASE_URL: str
    ENV: str = "SANDBOX"

    # Soporte / Admin
    SUPPORT_WHATSAPP_NUMBER: str = "584242686434"

    # Legacy (mantener)
    ADMIN_TELEGRAM_USER_ID: int | None = None

    # Nuevo: lista de admins (CSV en .env)
    # Ej: ADMIN_TELEGRAM_USER_IDS=7518903082,123456789
    ADMIN_TELEGRAM_USER_IDS: str | None = None

    # Alertas (tasas/sistema)
    ALERTS_TELEGRAM_CHAT_ID: int | None = None

    # Nuevo: grupo de pagos (órdenes/pendientes)
    PAYMENTS_TELEGRAM_CHAT_ID: int | None = None

    # Nuevo: grupo KYC (solicitudes de ingreso)
    KYC_TELEGRAM_CHAT_ID: int | None = None

    # Nuevo: grupo verificación ORIGEN (comprobante origen)
    ORIGIN_REVIEW_TELEGRAM_CHAT_ID: int | None = None

    # Debug de flujos (0/1)
    FLOW_DEBUG: int = 0

    # Métodos de pago
    PAYMENT_METHODS_VENEZUELA: str | None = None
    PAYMENT_METHODS_USA: str | None = None
    PAYMENT_METHODS_CHILE: str | None = None
    PAYMENT_METHODS_PERU: str | None = None
    PAYMENT_METHODS_COLOMBIA: str | None = None
    PAYMENT_METHODS_MEXICO: str | None = None
    PAYMENT_METHODS_ARGENTINA: str | None = None

    # Comisiones
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
                except Exception:
                    continue

        return ids

    def is_admin_id(self, telegram_user_id: int | None) -> bool:
        if telegram_user_id is None:
            return False
        return int(telegram_user_id) in self.admin_user_ids

    def payment_methods_text(self, country: str) -> str | None:
        key = f"PAYMENT_METHODS_{country}"
        raw = getattr(self, key, None)
        if not raw:
            return None
        return raw.replace("\\n", "\n")

    def commission_pct(self, origin: str, dest: str) -> float:
        """
        Comisión (%):
        1) intenta leer desde tabla settings (backoffice):
           - margin_route_usa_venez.percent
           - margin_dest_venez.percent
           - margin_default.percent
        2) fallback a .env (COMMISSION_*)
        """
        origin_u = (origin or "").upper()
        dest_u = (dest or "").upper()

        # Defaults desde .env
        default_margin = float(self.COMMISSION_DEFAULT)
        vene_margin = float(self.COMMISSION_VENEZUELA)
        usa_ve_margin = float(self.COMMISSION_USA_TO_VENEZUELA)

        # Overrides desde DB (settings)
        default_margin = get_setting_float("margin_default", "percent", default_margin)
        vene_margin = get_setting_float("margin_dest_venez", "percent", vene_margin)
        usa_ve_margin = get_setting_float("margin_route_usa_venez", "percent", usa_ve_margin)

        if dest_u == "VENEZUELA" and origin_u == "USA":
            return float(usa_ve_margin)
        if dest_u == "VENEZUELA":
            return float(vene_margin)
        return float(default_margin)


settings = Settings()


