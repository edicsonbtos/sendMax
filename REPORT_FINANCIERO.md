# 📊 AUDITORÍA - MÓDULO FINANCIERO Y CIERRES

## 1️⃣ UBICACIÓN DEL MÓDULO
- Frontend: `backoffice_web/src/app/daily-close/` (asumido por la ruta `/daily-close` en Sidebar), `backoffice_web/src/app/daily-snapshot/`
- Backend: `backoffice_api/app/routers/daily_closure.py`, `backoffice_api/app/services/financial_reads.py`
- Endpoints:
  - `GET /daily_closure/pending` (Verificar día pendiente)
  - `POST /daily_closure/execute` (Generar cierre)
  - `POST /daily_closure/close` (Alias de execute para UI)
  - `GET /daily_closure/report` (Reporte de entradas/salidas por país)
  - `GET /daily_closure/history` (Historial de cierres)
  - `GET /daily_closure/{closure_date}` (Detalles de un cierre)
  - `POST /daily_closure/{closure_date}/export-csv` (Exportar a CSV)

## 2️⃣ FLUJO ACTUAL DE CIERRE MANUAL

### Paso a paso:
1. Admin va a `/daily-close` o `/daily-snapshot`.
2. Click en "Generar Cierre" o endpoint envía POST a `/daily_closure/execute` o `/daily_closure/close`.
3. Sistema calcula: Órdenes completadas/canceladas, volumen total, ganancia (profit) estimada y real, mejor operador, mejores países (origen y destino), y retiros pendientes, basados en un rango de fechas (00:00 a 23:59 VET del día indicado).
4. Guarda en tabla: `daily_closures` junto con un snapshot JSON de los `vaults` y los `wallets` de los operadores.
5. Muestra resultado en: UI (Dashboard/Tablas) o mediante descarga de archivo `.csv` vía `/export-csv`.

## 3️⃣ DATOS QUE RECOPILA
- Total de órdenes (completadas y canceladas)
- Volumen transaccionado (origen)
- Comisiones generadas (`profit_usdt` estimado y `profit_real_usdt`)
- Tasa de éxito (`success_rate`)
- Mejor Operador y País (origen y destino) con mayor movimiento
- Retiros pendientes (cantidad y total USDT)
- Snapshots JSON: Balance de bóvedas (`vaults_snapshot`) y balances de billeteras (`wallet_balances_snapshot`)

## 4️⃣ ARQUITECTURA TÉCNICA
Base de datos:
Tabla: `daily_closures`
Campos: `id`, `closure_date`, `total_orders_count`, `total_volume_origin`, `total_profit_usdt`, `total_profit_real`, `success_rate`, `best_operator_id`, `best_operator_alias`, `best_origin_country`, `best_dest_country`, `pending_withdrawals_count`, `pending_withdrawals_amount`, `vaults_snapshot` (JSONB), `wallet_balances_snapshot` (JSONB), `warnings` (JSONB), `notes`, `executed_by`, `created_at`.
Librerías disponibles:
PDF: Ninguna encontrada (solo hay exportación nativa a CSV usando `csv` module de python stdlib).
Scheduler: Ninguna de tareas financieras (solo existe un bot rates_scheduler.py que es un stub safe).

## 5️⃣ PROPUESTA DE AUTOMATIZACIÓN
Opción A: Celery + Beat (Recomendada)
- Tarea programada diaria a las 23:59 VET.
- Genera el cierre de manera automática usando la lógica actual.
- Genera PDF visual con ReportLab u otra librería de reportes.
- Envía email al Admin (via SMTP integrado con SendGrid o similar).

Opción B: APScheduler
- Más simple, embebido en el FastAPI lifespan event.
- No requiere Redis ni workers separados, ideal para entornos como Railway con recursos limitados, pero menos robusto frente a reinicios inesperados.

Opción C: Cron nativo / Railway Cron
- Ejecuta un script de python standalone mediante `curl` a un endpoint seguro `/internal/daily_closure` con un `X-INTERNAL-KEY`.
- Menos cambios al stack, se apoya en Railway cron jobs.

## 6️⃣ DISEÑO DEL PDF
Secciones propuestas:
- Header: Logo SendMax, "Reporte de Cierre Diario", y Fecha de Cierre.
- Resumen ejecutivo: Total transaccionado, Ganancia neta (Real Profit), Tasa de éxito, y órdenes completadas vs canceladas.
- Desglose Operacional: Mejor operador del día, rutas más usadas (Origen y Destino).
- Estado de Fondos (Snapshot): Balances de bóvedas (Vaults) y resumen consolidado de billeteras de operadores.
- Pendientes: Retiros solicitados sin procesar.

## 7️⃣ PLAN DE IMPLEMENTACIÓN
- Fase 1: Setup scheduler (10 min) - Usar un script standalone gatillado por cron/Railway Jobs, o APScheduler embebido para no requerir Redis en Railway.
- Fase 2: Automatización Endpoint (15 min) - Mover lógica actual a un método core y exponer un endpoint `/internal/daily_closure/auto` protegido por la API Key interna.
- Fase 3: Generación PDF (20 min) - Instalar `reportlab` o `weasyprint`, crear un template que consuma el objeto de cierre y renderice el reporte PDF a memoria (`io.BytesIO()`).
- Fase 4: Envío email (10 min) - Integrar `aiosmtplib` u otra librería nativa para enviar un correo SMTP con el archivo PDF adjunto a la dirección del super-administrador.

TIEMPO TOTAL: ~55 min

## 8️⃣ RECOMENDACIONES
Actualmente el cierre se hace manual y se puede exportar en CSV. Automatizar este proceso usando la Opción C (Railway Cron + script interno FastAPI) es la ruta más pragmática para la arquitectura actual porque no requiere nuevos contenedores (Workers) y reutiliza toda la infraestructura de red inter-servicio actual. Además, introducir ReportLab para PDFs generará un alto valor agregado en los reportes contables que hoy son meramente CSV.
