from pathlib import Path
import re

p = Path('src/telegram_app/flows/new_order_flow.py')
s = p.read_text(encoding='utf-8')

print("contiene '🚀 Nuevo envío':", "🚀 Nuevo envío" in s)
print("contiene '📈 Tasas':", "📈 Tasas" in s)

# buscar el primer entry_point Regex del ConversationHandler
m = re.search(r"filters\.Regex\(r""\^(.+?)\$""\)", s)
print("regex encontrado:", bool(m))
if m:
    print("regex:", m.group(1))
