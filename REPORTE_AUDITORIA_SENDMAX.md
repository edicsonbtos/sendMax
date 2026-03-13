# AUDITORÍA TÉCNICA SENDMAX

## 1. RESUMEN EJECUTIVO
- **Estado general del sistema**: El sistema se encuentra en una etapa madura de producción (Phase 6 consolidada) con una arquitectura monolítica modular donde subsisten 3 aplicaciones principales interconectadas (Bot, API, y 2 instancias Next.js para administración). El flujo core (creación y procesamiento de remesas) es funcional pero contiene inconsistencias estructurales, especialmente relacionadas al modelo de dominio (p.ej. beneficiario vs cliente).
- **Nivel de madurez técnica**: Media-Alta en el backend asíncrono (FastAPI + Async DB), pero Media-Baja en observabilidad, testing automatizado y resiliencia ante caídas de memoria efímera (Bot state).
- **Riesgos críticos identificados (top 5)**:
  1. Uso de API_KEY hardcodeada (legacy) `BACKOFFICE_API_KEY` como método de autenticación en la API (`auth.py`). Representa una vulnerabilidad severa de bypass de JWT.
  2. Estado efímero del Bot (PTB): Los flujos como `new_order_flow` confían críticamente en `context.user_data`. Una caída o reinicio del contenedor causa la pérdida de sesiones transaccionales en vuelo.
  3. Carencia de Testing E2E: Validaciones financieras (wallets_ledger, profit splits) y concurrencias dependen casi exclusivamente de restricciones de base de datos sin un marco de CI continuo que prevenga regresiones de código.
  4. Deuda estructural en el esquema de órdenes: Mezcla la figura del cliente real (depositante) con el beneficiario, diluyendo los reportes de volumen y compliance.
  5. Acoplamiento y "Single Point of Failure" (SPOF) en la conexión a Neon DB (operaciones sincronizadas dependientes fuertemente del pool `psycopg_pool.AsyncConnectionPool`).
- **Fortalezas principales (top 5)**:
  1. Integridad referencial sólida y uso idempotente en el motor financiero (`idx_ledger_idempotency`, ON CONFLICT).
  2. Separación adecuada entre el núcleo administrativo y el canal transaccional (Bot / Backoffice API).
  3. UI React/Next.js bien modularizada, tipada y con gestión de estados (Zustand).
  4. Base de datos asincrónica performante con `psycopg[binary]` v3 y gestión explícita de transacciones.
  5. Control minucioso sobre versiones de tasas y configuraciones en `dynamic_settings.py`, superando los defaults estáticos de fase temprana.

## 2. ARQUITECTURA Y STACK
- **Mapa de módulos**:
  - `src/`: Core Python, Telegram App (handlers, flows), motor de negocio (DB config, bots, integrations).
  - `backoffice_api/`: Aplicación FastAPI segregada que expone endpoints REST a las interfaces de administración (web).
  - `backoffice_web/` y `operator-web/`: Frontends separados para administradores y operadores, construidos con Next.js.
  - `alembic/`: Gestión de migraciones lineales de base de datos Postgres.
- **Tecnologías core**:
  - Python 3.12, FastAPI, python-telegram-bot (v20+), Uvicorn.
  - Next.js (16.1 y 14.2), React 18/19, Tailwind CSS.
  - PostgreSQL (Neon DB) asíncrono con `psycopg3`.
- **Infraestructura y despliegue**:
  - Despliegue en monorepo de Railway mediante archivos `Dockerfile` individuales (multi-stage para Next.js).
  - Variables de entorno críticas: `DATABASE_URL` (y variables de RO/RW separadas en backend), `JWT_SECRET`, tokens de Telegram y Binance.
  - CI/CD estandarizado es inexistente (no hay GitHub Actions o validadores pre-commit automatizados para tests).
- **Base de datos**:
  - Esquema real bien diseñado con llaves foráneas y constraints fuertes (`chk_wallets_balance_non_negative`).
  - Queries asíncronas optimizadas y uso generalizado de cursores `dict_row`.
  - Peligros: Funciones que traen la tabla completa a memoria en `backoffice_api` si no se aplica paginación estricta con grandes volúmenes.

## 3. FLUJOS CRÍTICOS MAPEADOS

### A. Creación de orden
- **Descripción**: El operador registra una remesa (Bot/Web).
- **Archivos involucrados**: `src/telegram_app/flows/new_order_flow.py`, `src/api/operators.py`, `backoffice_web/src/app/ordenes/nueva/page.tsx`.
- **Validaciones**: Cálculo de rates "on the fly" o "smart-save". Aprobaciones automáticas por trust score y límite de monto.
- **Puntos débiles**: Requiere seleccionar obligatoriamente un beneficiario, ocultando al cliente real, lo que compromete auditorías y reportes de volumen (Leaderboard de Clientes falso).

### B. Wallet y ledger
- **Descripción**: Acreditación del profit real a los operadores y registro de movimientos históricos (`wallet_ledger`).
- **Archivos involucrados**: `src/db/repositories/wallet_repo.py`, `alembic/..._create_wallets_ledger_withdrawals.py`.
- **Validaciones**: Constraints de DB (saldos no negativos) e idempotencia (`user_id`, `type`, `ref_order_public_id`).
- **Puntos débiles**: Actualizaciones de saldos basadas en retries de base de datos podrían fallar bajo picos de concurrencia masivos sin colas de mensajes (SQS/RabbitMQ).

### C. Retiros (withdrawals)
- **Descripción**: Operadores solicitan liquidar su `profit_real_usdt` de sus billeteras internas.
- **Archivos involucrados**: `src/telegram_app/handlers/admin_withdrawals.py`.
- **Validaciones**: Flujo manual (Admin Approve/Reject) y captura de comprobantes fotográficos.
- **Puntos débiles**: La reversión de saldos ante un rechazo es manual/directa en el código. Carece de confirmaciones 2FA (TOTP) al solicitar retiros grandes en la web.

### D. Origin wallets y sweeps
- **Descripción**: Módulo de entrada fiat que agrega pagos hasta su cierre diario y sweep hacia bóvedas.
- **Archivos involucrados**: `src/db/repositories/origin_wallet_repo.py`, `src/api/daily_closure.py`.
- **Validaciones**: Restricciones UNIQUE por orden para prevenir asientos contables duplicados (`origin_receipts_ledger`).
- **Puntos débiles**: Procesos altamente manuales en la interfaz de "Cerrar Billetera" que dependen de la diligencia del equipo en horarios fijos.

### E. Rates
- **Descripción**: Subsistema que regenera las tasas de cambio para múltiples países (P2P + manual override).
- **Archivos involucrados**: `src/rates_generator.py`, `src/rates_scheduler.py`.
- **Validaciones**: Bloqueos asíncronos en DB, uso de `X-INTERNAL-KEY` para activaciones inter-servicios.
- **Puntos débiles**: Scheduler desconectado por defecto o implementado como "safe stub" que solo reporta `job executions` pero no regenera activamente.

### F. Bóvedas
- **Descripción**: Agregación centralizada del "efectivo real" y activos digitales del negocio.
- **Archivos involucrados**: `src/db/repositories/wallet_metrics_repo.py`, `backoffice_api/app/routers/vaults.py`.
- **Validaciones**: Capturas de snapshots durante cierres (`daily_closures`).
- **Puntos débiles**: Las bóvedas no se auto-concilian con las APIs bancarias o de Binance, es 100% dependiente de la honestidad de la entrada manual.

## 4. SEGURIDAD
- **Vulnerabilidades detectadas**:
  - *Alta*: Riesgo de Bypass JWT por el API KEY estática `BACKOFFICE_API_KEY` en `get_auth_context` (ver `backoffice_api/app/auth.py`). Si la key se filtra, se obtiene rol `admin` directo.
  - *Media*: Falta de re-autenticación obligatoria antes de acciones destructivas / retiros en el admin web.
  - *Baja*: Mensajes de error y logs ocasionales que pueden exponer fragmentos de consultas transaccionales (`psycopg.OperationalError` traceback).
- **Autenticación/autorización**: Uso de tokens JWT simétricos (PyJWT) con `user_id` y `role` ("admin", "operator") en el backend.
- **Secretos**: Correctamente trasladados a variables de entorno (no hay hardcoding crítico salvo scripts legacy).
- **Exposición de datos sensibles**: Endpoints públicos adecuadamente protegidos.
- **Recomendaciones críticas**: Retirar o restringir a localhost el `BACKOFFICE_API_KEY` y utilizar OIDC o rotación de secrets para JWT.

## 5. CALIDAD DE CÓDIGO
- **Backend (Python)**:
  - Estructura MVC/Repository adecuada. Los Type Hints son consistentes.
  - Complejidad alta en queries crudas en `backoffice_api/app/routers/daily_closure.py` que superan las 30 líneas de SQL inyectado.
- **Frontend (Next.js)**:
  - Fuerte estandarización con Tailwind y componentes UI (`lucide-react`, `@mui`).
  - Tipos en TypeScript son buenos pero el `any` o conversiones sueltas en respuestas HTTP aún existen.
- **Bot**:
  - Buen uso de `python-telegram-bot` v20+ async/await. Flujos organizados (FSM), pero la memoria es transitoria (diccionarios en memoria RAM local en vez de Redis), exponiendo a caídas abruptas.

## 6. TESTING Y VALIDACIÓN
- **Cobertura actual**: Severamente baja. Se limita a `test_orders_logic.py` y `test_wallet_logic.py` con dependencias fallidas de mocks (`fetchall` vs `fetchone`).
- **Gaps críticos**: Ausencia total de pruebas de regresión End-to-End para el cálculo de tasas y profit splits. No existe validación de componentes de React.
- **Propuesta**:
  - Arreglar tests base (Mock Data de base de datos).
  - Añadir Smoke Tests a los healthchecks (`/health`).
  - Desarrollar suite E2E automatizada con Playwright para Frontend.

## 7. OBSERVABILIDAD
- **Estado actual**: Implementación de Healthchecks obligatorios para despliegue en Railway (`/health` retorna `{"status": "ok"}`). Logs configurados mediante el estándar de Python en `src/config/logging.py`.
- **Gaps**: Falta de correlación (Trace IDs) de peticiones, lo que dificulta seguir una petición HTTP desde Next.js a lo largo del backend. Monitoreo APM ausente.
- **Propuestas**: Implementación de un logger estructurado JSON y Sentry/Datadog para atrapar errores y cuellos de botella en producción.

## 8. DEUDA TÉCNICA
- **Deuda documentada (Fase 6B)**: Error del mock en tests de idempotencia del ledger (`test_add_ledger_entry_tx_idempotency_logic`). Separación funcional de Cliente / Beneficiario omitida pero documentada en `REPORTE_AUDITORIA_FLUJO.md`.
- **Deuda adicional detectada**: Redundancia excesiva de scripts huérfanos y "tests sueltos" en la carpeta raíz (`test_binance.py`, `fix_env.py`, etc.). Fuerte acoplamiento manual del cierre diario.
- **Severidad y prioridad**: La deuda en el modelo Cliente/Beneficiario es Alta, impacta reportes y gamificación. La limpieza de scripts es Baja pero necesaria para higiene del repositorio.

## 9. RIESGOS OPERATIVOS
- **Single points of failure**: Base de datos Neon; una interrupción o latencia alta del pool pausa completamente los Bots y las Web APIs.
- **Falta de redundancia**: La aplicación PTB Bot debe escalar o utilizar Webhooks estrictamente desacoplados, hoy se despliega como instancia única (Polling).
- **Procesos manuales riesgosos**: Cierres de caja diarios y rechazos de retiros sin verificación secundaria (4-eyes principle) para transacciones grandes.
- **Dependencias externas**: Binance P2P como única fuente de verdad para rates sin un pool de fallback automático robusto o caching externo (Redis).

## 10. PERFORMANCE Y ESCALABILIDAD
- **Cuellos de botella potenciales**:
  - `backoffice_api` ejecutando agrupaciones mensuales complejas (e.g. `SELECT ... GROUP BY DATE_TRUNC('month')`) que penalizan la carga del dashboard sin un Materialized View.
- **Consultas (Queries) problemáticas**: Queries N+1 no explícitos, pero sub-óptimos en la reportería de Cierres Diarios sin índices temporales compuestos en fechas y `status`.
- **Assets/bundle**: El peso del bundle frontend es aceptable bajo las optimizaciones integradas de Next.js pero requiere cuidado con librerías de reportes pesadas (`jspdf`, `xlsx`).

## 11. OPORTUNIDADES DE MEJORA (top 20)
1. **Separar modelo de Cliente y Beneficiario:** Implementar campo `client_name` o tabla pivot. (Alto, Corto, Urgente)
2. **Eliminar autenticación Legacy:** Retirar el uso de `BACKOFFICE_API_KEY` para logins manuales.
3. **Persistencia FSM del Bot:** Implementar Redis (`RedisPersistence`) en `python-telegram-bot` en lugar de RAM.
4. **CI/CD Automatizado:** Introducir GitHub Actions para tests y validación lint/types.
5. **Índices compuestos en DB:** Optimizar `orders (status, created_at)`.
6. **Manejo de errores mejorado:** Estandarizar respuestas JSON de fallos en FastAPI en vez de Tracebacks asíncronos en texto.
7. **APM / Sentry:** Implementar herramientas de observabilidad para tracking de operaciones lentas.
8. **Tests de integración E2E:** Desarrollar suite básica con Pytest y Playwright.
9. **Limpieza del Repositorio:** Mover scripts sueltos (`patch_notification.py`, etc.) a una subcarpeta /scripts.
10. **Aprobación de Retiros 2FA:** Requerir OTP para admins aprobando Withdrawals grandes.
11. **Caching API Externa:** Cachear Binance P2P durante 5 mins para tolerar caídas.
12. **Background Jobs / Colas:** Migrar cierres diarios y notificaciones pesadas a Celery/Redis.
13. **Healthchecks de DB Reales:** Expandir `/health` para medir latencia y timeouts del Pool.
14. **Materialized Views:** Para dashboards pesados del panel administrativo.
15. **Migración de Next.js:** Continuar el esfuerzo de transición hacia `App Router` estricto en las apps front.
16. **Validación Zod (Frontend):** Proteger respuestas de FastAPI con un schema exacto en JS.
17. **Replica de solo lectura DB:** Usar un read-replica en `get_db_url_ro()` en producción en vez del fallback actual.
18. **Eliminación de Warnings PTB:** Configurar logging explícito para evadir `PTBUserWarning`.
19. **Fallback Automático de Tasas:** Disparar notificación crítica a grupo Admin si el rate generator falla 3 veces seguidas.
20. **Separación de roles granulares:** Ampliar de `admin/operator` a roles de `audit`, `finance` y `superadmin`.

## 12. MATRIZ DE PRIORIZACIÓN
- **AHORA (Crítico / Alto impacto / Bajo esfuerzo)**:
  - Añadir columna `client_name` a tabla `orders` y aislarlo del beneficiario.
  - Revocar vulnerabilidad de `BACKOFFICE_API_KEY` o limitarlo estrictamente a roles subyacentes/microservicios sin bypass humano.
  - Limpieza y organización de scripts huérfanos del repositorio.
- **PLANIFICAR (Crítico / Alto impacto / Alto esfuerzo)**:
  - Implementar Redis Persistence para Telegram FSM.
  - Pipeline de CI/CD integral (Testing & Build automatizado).
- **BACKLOG (Medio impacto)**:
  - Generar índices compuestos `orders` e introducir OpenTelemetry/Sentry.
  - Colas de tareas (Celery/RQ) para cierres masivos nocturnos.
- **NICE TO HAVE (Bajo impacto)**:
  - Views materializadas para analíticas en Backoffice.
  - Roles de operador granulares (auditoría / finanzas separadas).
