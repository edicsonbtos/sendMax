# Configuración en Railway - Sistema Sendmax

## Variables de Entorno Requeridas

### 1. Bot de Telegram (Servicio Bot)
- `DATABASE_URL`: URL de conexión a la base de datos Neon.
- `TELEGRAM_TOKEN`: Token obtenido de @BotFather.

### 2. API Backend (`backoffice_api`)
- `DATABASE_URL`: URL de conexión a la base de datos Neon.
- `JWT_SECRET`: Una cadena aleatoria larga para firmar los tokens de sesión.
- `BACKOFFICE_API_KEY`: Una clave secreta que compartirá con el Frontend para acciones administrativas.
- `PORT`: (Asignado automáticamente por Railway).

### 3. Web Frontend (`backoffice_web`)
- `NEXT_PUBLIC_API_URL`: La URL pública de tu servicio de API (ej: `https://api-sendmax.up.railway.app`).
- `BACKOFFICE_API_KEY`: Debe coincidir con la configurada en el Backend.

## Orden de Despliegue Sugerido
1. **Base de Datos**: Asegurar que las migraciones de Alembic se hayan ejecutado (`alembic upgrade head`).
2. **API Backend**: Desplegar primero para que el Frontend pueda conectarse.
3. **Bot**: Puede desplegarse en paralelo.
4. **Web Frontend**: Desplegar al final, asegurando que `NEXT_PUBLIC_API_URL` apunte a la API real.

## Notas Técnicas
- El sistema ahora usa **comisiones en decimal** (0.06 = 6%).
- Las rutas se gestionan jerárquicamente: Ruta Específica > Destino > Origen > Default.
