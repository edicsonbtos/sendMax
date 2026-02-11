import re
from pathlib import Path

env_path = Path(".env")

if env_path.exists():
    content = env_path.read_text(encoding="utf-8")
    
    # 1. Recuperar valores clave usando Regex incluso si están pegados
    # Buscamos la URL de postgres (termina antes de que empiece otra mayúscula clave o al final)
    db_match = re.search(r"(postgres(?:ql)?://.+?)(?=(TELEGRAM|ADMIN|PAYMENT|SUPPORT|[A-Z_]+=|$))", content)
    db_url = db_match.group(1).strip() if db_match else ""
    
    # Si la URL quedó sucia con comillas o espacios, limpiamos
    db_url = db_url.replace('"', '').replace("'", "")

    # Valores conocidos (Los recuperamos de tus logs o los definimos default)
    token = "8531719369:AAEu9jP0NpdhPht7KUfA6AykS1pKPkv6L-g"  # Recuperado de tus logs
    admin_ids = "7518903082"
    pay_group = "-5014966232"
    
    # 2. Reconstruir el contenido LIMPIO
    new_content = f"""TELEGRAM_BOT_TOKEN={token}
DATABASE_URL={db_url}
ENV=PROD
ADMIN_TELEGRAM_USER_IDS={admin_ids}
PAYMENTS_TELEGRAM_CHAT_ID={pay_group}
SUPPORT_WHATSAPP_NUMBER=584242686434
# Comisiones y Pagos
COMMISSION_VENEZUELA=6.0
COMMISSION_DEFAULT=10.0
COMMISSION_USA_TO_VENEZUELA=10.0
"""
    
    # 3. Guardar
    env_path.write_text(new_content, encoding="utf-8")
    print("✅ Archivo .env reparado correctamente.")
    print(f"URL DB detectada: {db_url[:20]}...") 
else:
    print("❌ No encontré el archivo .env para reparar.")
