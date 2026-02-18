with open('backoffice_web/src/app/settings/page.tsx', 'r', encoding='utf-8') as f:
    content = f.read()

# Cambiar [apiKey] por [token]
content = content.replace(
    'React.useEffect(() => { if (token) load(); }, [apiKey]);',
    'React.useEffect(() => { if (token) load(); }, [token]);'
)

with open('backoffice_web/src/app/settings/page.tsx', 'w', encoding='utf-8') as f:
    f.write(content)

print("OK - settings/page.tsx corregido")
