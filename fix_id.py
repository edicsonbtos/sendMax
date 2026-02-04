import re
from pathlib import Path

env_path = Path(".env")
if env_path.exists():
    content = env_path.read_text(encoding="utf-8")
    # Reemplaza cualquier ID de pagos anterior por el nuevo correcto
    new_content = re.sub(r"PAYMENTS_TELEGRAM_CHAT_ID=.*", "PAYMENTS_TELEGRAM_CHAT_ID=-1003872323253", content)
    env_path.write_text(new_content, encoding="utf-8")
    print("✅ ID de Grupo corregido a: -1003872323253")
else:
    print("❌ No encontré el archivo .env")
