import os

# ═══════════════════════════════════════════
# FIX 1: api.ts - Quitar URL hardcodeada
# ═══════════════════════════════════════════
path1 = 'backoffice_web/src/lib/api.ts'
with open(path1, 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace(
    "const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'https://apii-maxx-production.up.railway.app';",
    '''const API_BASE = process.env.NEXT_PUBLIC_API_URL;
if (!API_BASE) {
  throw new Error('NEXT_PUBLIC_API_URL no configurada');
}'''
)

with open(path1, 'w', encoding='utf-8') as f:
    f.write(content)
print("OK 1/5 - api.ts: URL hardcodeada eliminada")


# ═══════════════════════════════════════════
# FIX 2: login/page.tsx - Importar API_BASE de api.ts
# ═══════════════════════════════════════════
path2 = 'backoffice_web/src/app/login/page.tsx'
with open(path2, 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace(
    "import { useAuth } from '@/components/AuthProvider';\n\nconst API_BASE = process.env.NEXT_PUBLIC_API_URL || 'https://apii-maxx-production.up.railway.app';",
    "import { useAuth } from '@/components/AuthProvider';\nimport { API_BASE } from '@/lib/api';"
)

with open(path2, 'w', encoding='utf-8') as f:
    f.write(content)
print("OK 2/5 - login/page.tsx: API_BASE importado de api.ts")


# ═══════════════════════════════════════════
# FIX 3: daily-close - Zona horaria local
# ═══════════════════════════════════════════
path3 = 'backoffice_web/src/app/daily-close/page.tsx'
with open(path3, 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace(
    "yesterday.toISOString().split('T')[0]",
    "yesterday.toLocaleDateString('en-CA')"
)

with open(path3, 'w', encoding='utf-8') as f:
    f.write(content)
print("OK 3/5 - daily-close: Zona horaria corregida")


# ═══════════════════════════════════════════
# FIX 4: origin - Zona horaria local
# ═══════════════════════════════════════════
path4 = 'backoffice_web/src/app/origin/page.tsx'
with open(path4, 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace(
    "new Date().toISOString().split('T')[0]",
    "new Date().toLocaleDateString('en-CA')"
)

with open(path4, 'w', encoding='utf-8') as f:
    f.write(content)
print("OK 4/5 - origin: Zona horaria corregida")


# ═══════════════════════════════════════════
# FIX 5: Verificar que NEXT_PUBLIC_API_URL existe en .env
# ═══════════════════════════════════════════
env_path = 'backoffice_web/.env'
env_local = 'backoffice_web/.env.local'

has_var = False
for p in [env_path, env_local]:
    if os.path.exists(p):
        with open(p, 'r') as f:
            if 'NEXT_PUBLIC_API_URL' in f.read():
                has_var = True

if not has_var:
    target = env_local if os.path.exists(env_local) else env_path
    with open(target, 'a', encoding='utf-8') as f:
        f.write('\nNEXT_PUBLIC_API_URL=https://apii-maxx-production.up.railway.app\n')
    print("OK 5/5 - .env: NEXT_PUBLIC_API_URL agregada")
else:
    print("OK 5/5 - .env: NEXT_PUBLIC_API_URL ya existe")

print("\n=== TODOS LOS FIXES APLICADOS ===")
