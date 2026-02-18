import os

# FIX 1: metrics.py - Agregar constantes de estados
with open('backoffice_api/app/routers/metrics.py', 'r', encoding='utf-8') as f:
    content = f.read()

states_const = '''"""Router: Metricas y Dashboard"""

# Estados de órdenes (fuente única)
ST_CREADA = "CREADA"
ST_ORIGEN = "ORIGEN_VERIFICANDO"
ST_PROCESO = "EN_PROCESO"
ST_PAGADA = "PAGADA"
ST_CANCELADA = "CANCELADA"

from fastapi import APIRouter, Depends, Query'''

content = content.replace(
    '\"\"\"Router: Metricas y Dashboard\"\"\"\n\nfrom fastapi import APIRouter, Depends, Query',
    states_const
)

with open('backoffice_api/app/routers/metrics.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("OK 1/3 - metrics.py: constantes de estados agregadas")


# FIX 2: orders.py - Agregar try/except en endpoints
with open('backoffice_api/app/routers/orders.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Agregar import logging
content = content.replace(
    '\"\"\"Router: Ordenes y Trades\"\"\"\n\nfrom fastapi import APIRouter, Depends, Query, HTTPException',
    '\"\"\"Router: Ordenes y Trades\"\"\"\n\nimport logging\nfrom fastapi import APIRouter, Depends, Query, HTTPException\n\nlogger = logging.getLogger(__name__)'
)

with open('backoffice_api/app/routers/orders.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("OK 2/3 - orders.py: logging agregado")


# FIX 3: menu.py - Ya tiene rate limit, solo agregar logging
with open('src/telegram_app/handlers/menu.py', 'r', encoding='utf-8') as f:
    content = f.read()

if 'import logging' not in content:
    content = content.replace(
        'import time',
        'import time\nimport logging\n\nlogger = logging.getLogger(__name__)'
    )

with open('src/telegram_app/handlers/menu.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("OK 3/3 - menu.py: logging agregado")
