import os
import httpx
from dotenv import load_dotenv

load_dotenv()
token = os.getenv("TELEGRAM_BOT_TOKEN")
if not token:
    raise RuntimeError("TELEGRAM_BOT_TOKEN no está en .env")

url = f"https://api.telegram.org/bot{token}/getUpdates"
params = {"limit": 100, "timeout": 0, "allowed_updates": ["message", "edited_message"]}
r = httpx.get(url, params=params, timeout=20)
r.raise_for_status()
data = r.json()

print("updates:", len(data.get("result", [])))

for item in data.get("result", []):
    msg = item.get("message") or item.get("edited_message")
    if not msg:
        continue
    chat = msg.get("chat") or {}
    title = chat.get("title")
    if title:
        print("FOUND:", {"chat_id": chat.get("id"), "title": title, "type": chat.get("type"), "text": msg.get("text")})
