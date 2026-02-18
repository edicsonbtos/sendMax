with open('backoffice_web/src/components/Sidebar.tsx', 'r', encoding='utf-8') as f:
    content = f.read()

# Agregar después de Configuracion
content = content.replace(
    '{ text: "Configuracion", path: "/settings", icon: <SettingsIcon />, description: "Reglas y margenes" },',
    '''{ text: "Configuracion", path: "/settings", icon: <SettingsIcon />, description: "Reglas y margenes" },
    { text: "Metodos de Pago", path: "/payment-methods", icon: <WalletIcon />, description: "Metodos por pais" },'''
)

with open('backoffice_web/src/components/Sidebar.tsx', 'w', encoding='utf-8') as f:
    f.write(content)

print("OK 1 - Sidebar: Metodos de Pago agregado")
