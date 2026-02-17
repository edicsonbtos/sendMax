with open('backoffice_api/app/routers/users.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Agregar import secrets al inicio
content = content.replace(
    'from typing import Optional',
    'from typing import Optional\nimport secrets'
)

# Cambiar password fijo por aleatorio
content = content.replace(
    '    temp_pass = "Sendmax2026!"',
    '    temp_pass = secrets.token_urlsafe(10)'
)

with open('backoffice_api/app/routers/users.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("OK - users.py corregido")
