# SendMax — Sources of Truth

> **Last updated**: 2026-03-18 (Phase B Consolidation)  
> **Rule**: New code MUST use the canonical source. Do NOT create parallel implementations.

## Fuentes canónicas por dominio

| Dominio | Fuente canónica | Estado | Deprecated / Legacy |
|---|---|---|---|
| **Auth admin (login)** | `backoffice_api/app/routers/auth.py` | ✅ Activo | `src/api/auth.py` — DEPRECATED |
| **Auth operator (login)** | `src/api/auth_operators.py` | ✅ Activo | — |
| **Auth middleware (JWT decode)** | `backoffice_api/app/auth.py` + `auth_jwt.py` | ✅ Activo | — |
| **Operator dashboard** | `backoffice_api/app/routers/operator.py` | ✅ Canónico | `src/api/operators.py` reads — DEPRECATED |
| **Operator writes (create order, withdraw)** | `src/api/operators.py` | ✅ Activo | — (usa repos transaccionales) |
| **Wallet reads (balance, profit, ledger)** | `backoffice_api/app/services/financial_reads.py` | ✅ **NUEVO** | SQL directo en routers — migrado |
| **Wallet writes (ledger, hold, reversal)** | `src/db/repositories/wallet_repo.py` | 🔒 CONGELADO | — NO TOCAR |
| **Withdrawals writes (request, resolve, reject)** | `src/db/repositories/withdrawals_repo.py` | 🔒 CONGELADO | — NO TOCAR |
| **Withdrawals reads** | `backoffice_api/app/services/financial_reads.py` | ✅ **NUEVO** | — |
| **Ranking / Leaderboard** | `backoffice_api/app/routers/metrics.py` | ✅ Canónico | `src/api/ranking.py` — DEPRECATED |
| **Settings** | `backoffice_api/app/routers/settings.py` | ✅ Activo | — |
| **Payment methods** | `backoffice_api/app/routers/settings.py` | ✅ Activo | — |
| **Metrics admin** | `backoffice_api/app/routers/metrics.py` | ✅ Activo | — |
| **Orders CRUD** | `backoffice_api/app/routers/orders.py` | ✅ Activo | — |
| **Users admin** | `backoffice_api/app/routers/users.py` | ✅ Activo | — |

## Módulos congelados (NO modificar)

- `src/db/repositories/wallet_repo.py` — Lógica transaccional de wallets
- `src/db/repositories/withdrawals_repo.py` — Lógica de retiros con HOLD atómico
- `src/telegram_app/` — Bot de Telegram completo

## Frontend → Backend mapping

| Frontend | Backend API | Auth |
|---|---|---|
| `backoffice_web` (admin panel) | `backoffice_api` | JWT en localStorage + Bearer header |
| `operator-web` (operator panel) | `src/api` (bot process) | JWT en HttpOnly cookie |
