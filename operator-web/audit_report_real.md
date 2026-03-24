# Auditoría Técnica de operator-web

## A. Resumen ejecutivo

**Estado general del operator-web:**
El proyecto está en producción y funcional, ofreciendo las características clave (dashboard, clientes, órdenes, billetera, perfil). Emplea Next.js 14 App Router con TailwindCSS para la interfaz, logrando una presentación moderna y responsiva (Glassmorphism). Sin embargo, bajo la superficie, la aplicación se apoya fuertemente en patrones básicos de React (useEffect, useState) para fetching de datos y gestión de estado local, lo que lleva a código repetitivo, múltiples re-renders, condiciones de carrera potenciales (race conditions) y falta de sincronización global.

**Nivel de madurez del frontend:**
Básico/Intermedio. Funciona como una SPA (Single Page Application) tradicional envuelta en Next.js, pero no aprovecha completamente las capacidades de SSR (Server Side Rendering), caché global de datos o manejo centralizado de estado. La autenticación está frágilmente balanceada entre cookies y localStorage.

**Nota:** 5/10
**Justificación:** Cumple su función en producción (funciona), pero estructuralmente es frágil. La mezcla de mecanismos de autenticación (localStorage + cookies sin sincronización rígida), la ausencia de un manejador de estado global (aunque zustand está instalado, no se usa), y la abundancia de fetching directo en componentes (`useEffect` con `setInterval` sin cancelación adecuada) introducen deuda técnica significativa que dificultará la escalabilidad a corto y mediano plazo.

---

## B. Inventario real

### Páginas (`src/app/`)
*   `/(auth)/login/page.tsx`: Pantalla de login.
*   `/(auth)/recuperar/page.tsx`: Pantalla de recuperación (no analizada a fondo, pero existente).
*   `/(dashboard)/page.tsx`: Dashboard principal con tasas, top clientes, cola de órdenes, ranking.
*   `/(dashboard)/layout.tsx`: Layout principal con sidebar, barra móvil y comprobación de auth (doble check: localStorage y cookies).
*   `/(dashboard)/billetera/page.tsx`: Gestión de retiros e historial.
*   `/(dashboard)/clientes/page.tsx`: Leaderboard y listado de clientes.
*   `/(dashboard)/clientes/nuevo/page.tsx`: Formulario de creación de cliente (no inspeccionado internamente pero referenciado).
*   `/(dashboard)/ordenes/page.tsx`: Listado y filtrado de órdenes.
*   `/(dashboard)/ordenes/[id]/page.tsx`: Detalle de una orden específica.
*   `/(dashboard)/ordenes/nueva/page.tsx`: Flujo (stepper) de 4 pasos para creación de orden con subida de comprobante.
*   `/(dashboard)/perfil/page.tsx`: Resumen del perfil de usuario, trust score y total ganado.

### Componentes Reutilizables (`src/components/dashboard/`)
*   `LiveRatesWidget.tsx` (Uso de `api.get` directo e `interval`).
*   `OrderQueueWidget.tsx`
*   `RankingWidget.tsx`
*   `TopClientsWidget.tsx`
*(Nota: No parecen estar siendo consumidos en `/(dashboard)/page.tsx`, que implementa su propia lógica repetida, o se usan en otras partes de forma aislada).*

### Utilidades Compartidas (`src/lib/`)
*   `api.ts`: Instancia global de Axios, interceptores request (inyecta Bearer desde localStorage) y response (maneja 401 borrando todo y redirigiendo).
*   `utils.ts`: Utilidades menores como `safeToFixed`.

### Middleware (`src/middleware.ts`)
*   Comprueba exclusivamente la existencia de la cookie `auth_token` para proteger rutas. No verifica validez del token, sólo existencia.

### Configuración
*   `package.json`: Dependencias: Next 14, Axios, Zustand (instalado pero no usado), Recharts, Lucide-react. Tailwind y PostCSS presentes.
*   `tsconfig.json`: TypeScript activo.
*   `Dockerfile`: Build multi-stage para producción, maneja variables de entorno (`NEXT_PUBLIC_API_URL`) inyectadas vía ARG/ENV y se salta npm install a favor de `npm ci`.

### Archivos Importantes
*   `README.md`: Boilerplate de `create-next-app` (basura técnica).
*   `globals.css`: Define variables CSS y utilidades para glassmorphism (funcional y en uso).

### Archivos sospechosos o basura
*   `README.md`: Contiene el texto de `create-next-app`, no provee contexto del proyecto.
*   Componentes en `src/components/dashboard/` parecen ser código muerto o refactorizaciones a medias, dado que `/(dashboard)/page.tsx` incluye una implementación monolítica de los mismos widgets.

---

## C. Auth real actual

### Flujo exacto actual
1.  **Login:** Usuario entra en `/login`. El form hace un `fetch` (no usa `api.ts`) a `/auth/operator/login`.
2.  **Almacenamiento:** Si es exitoso, guarda en `localStorage` (`token`, `operator_id`, `operator_alias`, `operator_email`) **Y** crea una cookie `auth_token` usando `document.cookie` (sin httpOnly, accesible por JS).
3.  **Redirección:** Usa `window.location.replace("/")`.
4.  **Middleware (Next.js):** En cada navegación, revisa si la cookie `auth_token` existe. Si existe, permite paso. Si no, redirige a `/login`.
5.  **Peticiones API:** `src/lib/api.ts` usa Axios. Un interceptor lee el `localStorage` (NO la cookie) e inyecta `Authorization: Bearer <token>`.
6.  **Expiración/401:** Si la API responde 401, el interceptor de `api.ts` borra `localStorage`, borra la cookie, y redirige a `/login`.
7.  **Logout Manual:** `/(dashboard)/layout.tsx` y `/(dashboard)/perfil/page.tsx` implementan su propia función de limpieza (borrando items manuales y la cookie) y hacen reload/replace.

### Fortalezas
*   Funciona. Bloquea rutas en el cliente/servidor gracias al middleware de Next.js.
*   El interceptor centralizado para el 401 previene bucles infinitos usando un flag (`isRedirecting`).

### Debilidades
*   **Dualidad peligrosa:** El middleware confía en la cookie, pero las peticiones HTTP confían en el `localStorage`. Si se desincronizan (ej. pestaña limpia localStorage pero la cookie sigue viva), la app entrará en un ciclo roto: el middleware te deja pasar a `/`, la página hace fetch, falla (no hay token o 401), el interceptor borra la cookie y redirige a `/login`.
*   **Seguridad:** El token viaja en `localStorage` y en una cookie accesible por JS. Esto expone la app a XSS completo.
*   **Lógica duplicada:** La lógica de logout está duplicada en el interceptor, en el layout y en la página de perfil.
*   **Lectura síncrona:** El perfil lee datos (`operator_email`, `operator_alias`) directamente del `localStorage` como fuente de verdad, lo que puede causar problemas de hidratación en SSR/Next.js o desincronización si los datos cambian.

### ¿Está bien para hoy o no?
**Solo funciona.** Para un sistema que mueve dinero/transacciones, almacenar datos de sesión expuestos a XSS y depender de dos fuentes de verdad desincronizadas no es ideal, pero no está crítico (roto). Requiere un rediseño posterior (hacia HttpOnly cookies), pero se puede mantener si no se toca nada de inmediato.

---

## D. API real consumida

### Tabla de endpoints realmente usados por el frontend

| Endpoint | Dónde se llama | Método | Cliente | Notas |
| :--- | :--- | :--- | :--- | :--- |
| `/auth/operator/login` | `/(auth)/login/page.tsx` | POST | `fetch` puro | Fuera de `api.ts` |
| `/api/rates/current` | `/(dashboard)/page.tsx` | GET | `axios` (api.ts) | Se llama cada 30s |
| `/api/operators/dashboard/top-clients?limit=5` | `/(dashboard)/page.tsx` | GET | `axios` | |
| `/api/operators/orders/queue` | `/(dashboard)/page.tsx` | GET | `axios` | |
| `/api/operators/dashboard/stats` | `/(dashboard)/page.tsx`, `/(dashboard)/perfil/page.tsx` | GET | `axios` | Llamado por ambos componentes al montar |
| `/api/ranking/operators?limit=10` | `/(dashboard)/page.tsx` | GET | `axios` | |
| `/api/operators/orders` | `/(dashboard)/ordenes/page.tsx` | GET | `axios` | |
| `/api/operators/orders/{id}` | `/(dashboard)/ordenes/[id]/page.tsx` | GET | `axios` | |
| `/api/operators/clients/ranking?limit=50` | `/(dashboard)/clientes/page.tsx` | GET | `axios` | |
| `/api/operators/clients/stats` | `/(dashboard)/clientes/page.tsx` | GET | `axios` | |
| `/api/operators/clients/search?q={query}` | `/(dashboard)/ordenes/nueva/page.tsx` | GET | `axios` | Debounced manual (300ms) |
| `/api/operators/clients/` | `/(dashboard)/ordenes/nueva/page.tsx` | POST | `axios` | Creación rápida |
| `/api/operators/beneficiaries` | `/(dashboard)/ordenes/nueva/page.tsx` | GET | `axios` | |
| `/api/operators/orders/create` | `/(dashboard)/ordenes/nueva/page.tsx` | POST | `axios` | Envía notas, client_id, etc. |
| `/api/operators/wallet/summary` | `/(dashboard)/billetera/page.tsx` | GET | `axios` | Polling cada 30s |
| `/api/operators/wallet/withdrawals` | `/(dashboard)/billetera/page.tsx` | GET | `axios` | Polling cada 30s |
| `/api/operators/wallet/withdraw-info` | `/(dashboard)/billetera/page.tsx` | GET | `axios` | Antes de abrir form |
| `/api/operators/wallet/withdraw` | `/(dashboard)/billetera/page.tsx` | POST | `axios` | |

### Inconsistencias detectadas
*   El login usa `fetch` mientras todo lo demás usa Axios a través de `api.ts`.
*   Las rutas a veces tienen trailing slash (`/api/operators/clients/`) y a veces no.
*   En `/(dashboard)/billetera/page.tsx` el polling de 30s hace dos llamadas GET separadas (`summary` y `withdrawals`) usando `Promise.all`. No hay un endpoint consolidado, lo cual está bien, pero el re-render es costoso si la tabla es grande.

---

## E. Hallazgos confirmados

### Crítico
*   Ninguno inminente que rompa producción hoy. El sistema funciona tal como está cableado.

### Importante
*   **Falta de State Management Global (Zustand está muerto):** El paquete `zustand` está instalado (`package.json`), pero `grep` confirma que no se usa. Cada página hace un `fetch` de sus propios datos (Dashboard pide Stats, Perfil pide Stats de nuevo).
*   **Doble fuente de Auth (Cookies vs LocalStorage):** El middleware lee cookies, axios lee localStorage. El logout manual borra ambos en lugares distintos del código. Un fallo en uno deja la app en un estado inconsistente.
*   **Componentes Monolíticos:** `/(dashboard)/page.tsx` hace 5 peticiones simultáneas, maneja estado local de tasas, clientes, cola, stats y ranking, y renderiza toda la vista. Tiene más de 300 líneas de lógica acoplada, ignorando componentes creados en `src/components/dashboard/`.

### Medio
*   **Fugas de Memoria en Polling:** En `/(dashboard)/page.tsx` y `/(dashboard)/billetera/page.tsx`, hay un `setInterval` cada 30s. Si la request tarda más de 30s por latencia, se apilarán requests. Aunque usan un flag `mounted`, las promesas en curso no se abortan al desmontar el componente (falta AbortController).
*   **Cálculo Fake en Frontend:** En `/(dashboard)/ordenes/nueva/page.tsx`, la conversión de la tasa es un placeholder codificado: `const rate = destCountry === "VE" ? 45.2 : 4100; // Fake rate`. La tasa real no viene de la API para ese preview.
*   **Logs y placeholders:** Existe un `console.log("Datos del backend:", res.data); // <-- AGREGADO POR ANTIGRAVITI` en `/(dashboard)/page.tsx` que llega a producción. El `README.md` es el genérico de Next.js.

### Bajo
*   No hay Global Error Boundary. Si ocurre una excepción en React (no capturada por un bloque try-catch asíncrono), la página quedará en blanco.
*   Sin `react-query` o SWR: Todo se maneja con `useState` y `useEffect`, provocando re-renders "flash de cargando" si cambias de página y vuelves.

---

## F. Cosas que parecen problema pero NO lo son

*   **Next.js App Router usando `"use client"` por todas partes:** Esto anula SSR, pero para un dashboard privado B2B detrás de un login, SSR no aporta beneficios reales en SEO y sólo complica el manejo de sesión JWT. Convertirlo a SPA (Single Page App) con App Router (lo que está haciendo ahora) es una decisión técnica válida y funciona bien.
*   **Falta de `react-hook-form` o validadores tipo Zod:** Los formularios (`/login`, `/billetera`, `/ordenes/nueva`) son muy simples y la validación manual local y en el backend actual es suficiente por ahora. No es urgente migrarlo.

---

## G. Deuda técnica real

1.  **Sincronización de Sesión:** Lógica de cierre de sesión dispersa (Interceptor API, Layout, Perfil).
2.  **Duplicación de peticiones (Data Fetching):** `dashboard` y `perfil` piden la misma data en paralelo. Al navegar entre ellos, vuelven a pedir todo a la base de datos (0% caché).
3.  **Código Muerto (Dead Code):** Componentes en `src/components/dashboard/` (como `LiveRatesWidget.tsx`) existen pero aparentemente la página principal no los usa, reimplementando la misma lógica (polling y fetching).
4.  **Cálculo de tasas en duro (Hardcoded):** El Stepper de nueva orden no usa las verdaderas tasas dinámicas del backend.

---

## H. Recomendaciones posteriores (Por orden de impacto)

1.  **Limpieza Menor y Remoción de Código Muerto (Bajo Riesgo, Alto Retorno):**
    *   Eliminar el `console.log`.
    *   Verificar si `src/components/dashboard/*` se puede borrar (si la página dashboard no los usa) o refactorizar el dashboard monolítico para usarlos y limpiar el archivo.
2.  **Implementar React Query (SWR) o Zustand (Medio Riesgo, Alto Retorno de UX):**
    *   Reemplazar los `useEffect` de data fetching (especialmente los polling cada 30s) por un gestor de caché. Esto aliviará la carga al servidor, prevendrá condiciones de carrera, eliminará fugas de memoria y dará una experiencia más fluida.
3.  **Endurecer y Unificar la Autenticación (Medio Riesgo):**
    *   Crear un único `authProvider` o hook (`useAuth`) que encapsule login, logout y lectura de token.
    *   Asegurar que `api.ts`, el `Layout` y `middleware` confíen en el mismo patrón de limpieza de sesión.
4.  **Corregir la cotización Fake en el form de órdenes:**
    *   Hacer que `/(dashboard)/ordenes/nueva/page.tsx` consulte al endpoint `/api/rates/current` real en lugar de usar variables harcodeadas (`45.2`).

### Conclusión Final

**operator-web está:**
Estable con deuda controlable.

**El siguiente paso correcto es:**
Hacer limpieza menor (quitar logs, código muerto, corregir el rate "fake" del stepper) y después ordenar la capa de API (introducir un sistema de caché como React Query / Zustand antes de que el frontend crezca más). No tocar Auth de momento si no está causando bugs reales.