import re

path = 'src/main.py'
with open(path, 'r', encoding='utf-8') as f:
    c = f.read()

# 1) asegurar import asyncio
if '\nimport asyncio\n' not in c and not c.startswith('import asyncio'):
    c = c.replace('from __future__ import annotations', 'from __future__ import annotations\n\nimport asyncio')

# 2) reemplazar el cuerpo del endpoint para:
# - loggear update_id
# - meter update a update_queue
pattern = r'@app\.post\(f"/\{settings\.TELEGRAM_BOT_TOKEN\}"\)\s*async def telegram_webhook\(request: Request\):.*?return Response\(status_code=200\)'
replacement = '''@app.post(f"/{settings.TELEGRAM_BOT_TOKEN}")
async def telegram_webhook(request: Request):
    \"\"\"Endpoint to receive Telegram updates.\"\"\"
    data = await request.json()
    try:
        upd_id = data.get("update_id")
        logger.info(f"[WEBHOOK] update_id={upd_id}")
    except Exception:
        pass

    update = Update.de_json(data, bot_app.bot)

    # Encolar para que PTB lo procese en su loop normal
    await bot_app.update_queue.put(update)

    # Responder rápido a Telegram
    return Response(status_code=200)'''

c2, n = re.subn(pattern, replacement, c, flags=re.S)
if n != 1:
    raise SystemExit(f"No pude reemplazar el endpoint (matches={n}). Pega src/main.py para ajustarlo.")

# 3) habilitar access_log en uvicorn.run (para ver cada POST entrante)
c2 = c2.replace(
    'uvicorn.run(app, host="0.0.0.0", port=settings.PORT, log_level="info")',
    'uvicorn.run(app, host="0.0.0.0", port=settings.PORT, log_level="info", access_log=True)'
)

with open(path, 'w', encoding='utf-8') as f:
    f.write(c2)

print("OK - Webhook ahora usa update_queue + logs")
