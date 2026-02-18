with open('src/telegram_app/handlers/payment_methods.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Agregar import
content = content.replace(
    'from src.config.settings import settings',
    'from src.config.settings import settings\nfrom src.db.settings_store import get_payment_methods_for_country'
)

# Cambiar lectura: DB primero, fallback a .env
content = content.replace(
    '    # Lee desde ENV: PAYMENT_METHODS_{COUNTRY} con \\n (settings lo convierte a saltos reales)\n    pm = settings.payment_methods_text(country)',
    '    # Lee desde DB primero, fallback a .env\n    pm = get_payment_methods_for_country(country)\n    if not pm:\n        pm = settings.payment_methods_text(country)'
)

with open('src/telegram_app/handlers/payment_methods.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("OK 2b/3 - payment_methods.py: Lee de DB con fallback a .env")
