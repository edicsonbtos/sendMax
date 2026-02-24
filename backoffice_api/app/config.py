import os
import logging
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# --- Secrets ---
SECRET_KEY = os.getenv("SECRET_KEY")
BACKOFFICE_API_KEY = os.getenv("BACKOFFICE_API_KEY")

# --- JWT ---
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "480"))

# --- Rate Limiting ---
RATE_LIMIT_ENABLED = os.getenv("RATE_LIMIT_ENABLED", "true").lower() == "true"
RATE_LIMIT_PER_MINUTE_DEFAULT = int(os.getenv("RATE_LIMIT_PER_MINUTE_DEFAULT", "60"))
RATE_LIMIT_LOGIN_PER_MINUTE = int(os.getenv("RATE_LIMIT_LOGIN_PER_MINUTE", "10"))

# --- Environment ---
ENV = os.getenv("ENV", "SANDBOX").lower()
IS_PRODUCTION = ENV == "production"

# --- CORS ---
raw_origins = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:3000,http://127.0.0.1:3000,https://sendmax-web-production.up.railway.app"
).split(",")
ALLOWED_ORIGINS = [o.strip() for o in raw_origins if o.strip()]

def validate_config():
    """Valida la configuración esencial y loguea advertencias si faltan."""
    degraded = False
    if not SECRET_KEY:
        logger.error("FALTA SECRET_KEY: JWT auth deshabilitada")
        degraded = True
    if not BACKOFFICE_API_KEY:
        logger.error("FALTA BACKOFFICE_API_KEY: API Key auth deshabilitada")
        degraded = True

    return not degraded
