with open('src/telegram_app/handlers/debug_callbacks.py', 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace('logger.info(f"[DEBUG]', 'logger.debug(f"[DEBUG]')

with open('src/telegram_app/handlers/debug_callbacks.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("OK - debug_callbacks.py corregido")
