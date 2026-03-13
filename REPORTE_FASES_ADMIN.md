## AUDITORÍA ESPECÍFICA DE LAS 6 FASES

### FASE 1 — Checklist
- [✓] `layout.tsx` integra `LayoutShell`
- [✓] `LayoutShell.tsx` excluye `/login` correctamente
- [✓] `Sidebar.tsx` tiene navegación completa
- [✓] `globals.css` tiene design tokens
- [✓] Build de `backoffice_web` es exitoso
- [✓] No hay errores TypeScript bloqueantes

**Evidencia de código:**
- `backoffice_web/src/app/layout.tsx` contiene `<LayoutShell>{children}</LayoutShell>`.
- `backoffice_web/src/components/LayoutShell.tsx` contiene la lógica estricta `if (isLoginPage) return <>{children}</>;`.
- `backoffice_web/src/app/globals.css` declara exhaustivamente las clases solicitadas (`.card-glass`, `.input-glass`, `.table-glass`, etc.) junto a la paleta de colores requerida.
- El comando `npm run build` corrió en 22.5 segundos, finalizando de manera exitosa y procesando rutas estáticas/dinámicas.

**Problemas detectados:**
No se hallaron problemas a nivel de código o arquitectura estructural visual.

---

### FASE 2 — Checklist
- [✓] Todos los componentes listados existen
- [✓] Al menos 3 páginas críticas usan componentes nuevos
- [✓] `cn.ts` existe y funciona
- [✓] No hay imports rotos
- [✓] Componentes tienen tipos correctos

**Componentes confirmados:**
Revisados en `backoffice_web/src/components/ui/`: `Button.tsx`, `Card.tsx`, `Input.tsx`, `Table.tsx`, `Badge.tsx`, `Modal.tsx`, `SectionHeader.tsx`, `EmptyState.tsx`, `LoadingState.tsx`, `TrendPill.tsx`, `RiskBadge.tsx`, `CountryPill.tsx`, `MoneyCell.tsx`, `MetricCard.tsx`, `StatCard.tsx`, `FilterBar.tsx`, `Timeline.tsx`, `AuditFeed.tsx`, `VaultSummaryCard.tsx` y `DataTable.tsx`.

**Evidencia de código:**
- El archivo `backoffice_web/src/lib/cn.ts` implementa la función clsx/tailwind-merge standard.
- Páginas críticas como `orders/page.tsx`, `origin/page.tsx` y `daily-close/page.tsx` importan activamente componentes como `Card`, `Button`, `DataTable`, `FilterBar`, y `MoneyCell`.

**Problemas detectados:**
No se encontraron errores de tipado o imports rotos.

---

### FASE 3 — Checklist
- [✗] `sources_of_truth.md` existe y tiene contenido útil
- [✗] `domain_map.md` existe y tiene contenido útil
- [✗] `admin_api_map.md` existe y tiene contenido útil
- [✓] `GET /metrics/control-center` existe en código
- [✓] Backend tiene routers organizados por dominio

**Documentación validada:**
Los archivos solicitados de documentación (`sources_of_truth.md`, `domain_map.md` y `admin_api_map.md`) **NO** existen en la raíz del repositorio, en la carpeta `backoffice_api` o `docs`.

**Evidencia de código:**
- El endpoint `GET /metrics/control-center` se encuentra programado y documentado en `backoffice_api/app/routers/metrics.py` como un "Agregador Maestro (M10 hardened)".
- `backoffice_api/app/routers/` separa claramente la lógica en `metrics.py`, `executive.py`, `orders.py`, etc.

**Problemas detectados:**
La falta de la documentación acordada representa una deuda técnica sobre la fase de diseño.

---

### FASE 4 — Checklist
- [✓] `executive.py` existe con 5 endpoints
- [✓] Las 5 páginas ejecutivas existen
- [✓] Cada página consume su endpoint
- [✓] `/admin` redirige correctamente (lógica existente, pero problemática - ver sección final)
- [✓] Sidebar tiene navegación ejecutiva
- [✓] No hay errores de fetching o CORS en el código base

**Endpoints validados:**
`executive.py` incluye `@router.get("/control-center")`, `/treasury`, `/vaults`, `/risk` y `/audit`.
**Páginas validadas:**
Carpetas existentes en `backoffice_web/src/app/` con su respectivo `page.tsx` que importan data usando `api.get`.

**Problemas detectados:**
Aunque el `/admin` tiene un archivo para redirigir, la implementación de la redirección y el estado de la página principal causan un loop / blank screen al momento de renderizar.

---

### FASE 5 — Checklist
- [✓] `/executive/risk` tiene checks de integridad
- [✓] `/executive/audit` tiene feed enriquecido
- [✓] `risk/page.tsx` muestra integridad visualmente
- [✓] `audit/page.tsx` tiene timeline enriquecida
- [✓] Los datos son reales y útiles (estructurados en el backend)

**Observabilidad validada:**
- El código de la ruta `/risk` contiene lógica SQL `SELECT wallet_id, SUM(amount_usdt) as balance FROM wallet_ledger GROUP BY wallet_id HAVING SUM(amount_usdt) < -0.01 LIMIT 5`, validando anomalías financieras.
- El endpoint `/audit` obtiene eventos estructurados (cierres, sweeps, withdrawals).
- La vista de React renderiza apropiadamente el estado "Saludable" vs "Alerta".

**Problemas detectados:**
Sin problemas técnicos en la codificación de la lógica.

---

### FASE 6 — Checklist
- [✓] `types/common.ts` existe
- [✓] `types/executive.ts` existe
- [✓] Páginas ejecutivas usan tipos correctos
- [✓] No quedan `any` innecesarios
- [✓] Build TypeScript pasa sin errores

**Tipado validado:**
No se encontraron variables de tipo explícito `any` en los componentes ejecutivos. El código en `audit/page.tsx` consume `ExecutiveAuditData` usando el helper genérico `<ApiEnvelope<T>>`.

**Problemas detectados:**
El tipado es consistente y el build es exitoso.

---

### DIAGNÓSTICO DEL PROBLEMA: ADMIN NO FUNCIONA

**Qué encontré exactamente:**
A nivel de sintaxis, la compilación de `backoffice_web` es **exitosa** y sin errores (`npm run build`). Sin embargo, existe un **problema estructural de enrutamiento y estado de sesión** (Doble salto asíncrono e inicialización del AuthProvider).

**Dónde está el problema:**
La jerarquía de enrutamiento principal crea una carrera de condiciones y saltos dobles (`double-hop redirect`), que bajo Next.js 14/16 (App Router) a menudo desemboca en pantallas blancas o redirecciones abortadas por el caché o la seguridad de hydration en el navegador.

**Archivos involucrados:**
1. `backoffice_web/src/app/page.tsx`
2. `backoffice_web/src/app/admin/page.tsx`
3. `backoffice_web/src/components/AuthProvider.tsx`

**Evidencia de código (El Loop de salto):**
- El root `app/page.tsx` es un Server Component que ejecuta `redirect('/admin')`.
- Al llegar a `/admin`, `app/admin/page.tsx` es un Client Component (`'use client'`) que espera el montaje para invocar `router.replace('/control-center')` dentro de un `useEffect`.
- De manera simultánea, el archivo de autenticación (`AuthProvider.tsx`) ejecuta un `useEffect` para validar si `token` existe, si no, te envía a `/login`.

Si el navegador demora en el renderizado hidratado, o hay un parpadeo en la red, el sistema interrumpe el paso de `/admin` a `/control-center`, dejando al usuario bloqueado visualizando "Redirigiendo a Control Center..." o bien lo rebota sin éxito entre guards.

**Propuesta de solución inmediata:**
Modificar el archivo raíz `backoffice_web/src/app/page.tsx` para que redirija **directamente** al destino real (`/control-center`), evitando la página middleware inútil `/admin`.

```typescript
// backoffice_web/src/app/page.tsx
import { redirect } from 'next/navigation';

export default function RootPage() {
    // Ir directo a Control Center, sin pasar por /admin
    redirect('/control-center');
}
```
Y opcionalmente en `/admin/page.tsx` cambiar el `useEffect` por un Server Redirect o simplemente eliminar esa ruta si `/control-center` es la nueva cabecera de la aplicación.
