# 📊 REPORTE COMPLETO - SISTEMA DE RANKING DE CLIENTES
**Fecha:** 2026-03-05
**Proyecto:** SendMax

---

## 1. ENDPOINT: Top Clientes del Operador
```sql
@router.get("/dashboard/top-clients", response_model=List[TopClientResponse])
async def get_top_clients(user_id: int = Depends(get_current_operator), limit: int = 5):
    async with get_async_conn() as conn:
        async with conn.cursor() as cur:
            await cur.execute("""
                SELECT 
                    COALESCE(o.beneficiary_text, 'Cliente Manual') as name,
                    SUM(o.profit_real_usdt) as total_volume,
                    COUNT(*) as total_orders
                FROM orders o
                WHERE o.operator_user_id = %s AND o.status IN ('COMPLETADA', 'ORIGEN_CONFIRMADO')
                GROUP BY o.beneficiary_id, o.beneficiary_text
                ORDER BY total_volume DESC LIMIT %s
            """, (user_id, limit))
            rows = await cur.fetchall()
            return [TopClientResponse(name=r[0][:50], total_volume_usdt=r[1], total_orders=r[2]) for r in rows]
```
2. ENDPOINT: Ranking de Operadores
```sql
@router.get("/operators", response_model=List[RankingEntry])
async def get_operator_ranking(limit: int = 10):
    async with get_async_conn() as conn:
        async with conn.cursor() as cur:
            await cur.execute("""
                WITH monthly_stats AS (
                    SELECT operator_user_id, COUNT(*) as orders_count,
                    COALESCE(SUM(profit_real_usdt), 0) as volume
                    FROM orders
                    WHERE DATE_TRUNC('month', created_at) = DATE_TRUNC('month', CURRENT_DATE)
                    AND status IN ('COMPLETADA', 'ORIGEN_CONFIRMADO')
                    GROUP BY operator_user_id
                ),
                ranked AS (
                    SELECT u.id, u.alias, u.trust_score,
                    COALESCE(ms.orders_count, 0) as total_orders,
                    COALESCE(ms.volume, 0) as monthly_volume,
                    ROW_NUMBER() OVER (ORDER BY COALESCE(u.trust_score, 0) DESC, COALESCE(ms.volume, 0) DESC) as position
                    FROM users u
                    LEFT JOIN monthly_stats ms ON u.id = ms.operator_user_id
                    WHERE u.kyc_status = 'APPROVED'
                )
                SELECT * FROM ranked ORDER BY position LIMIT %s
            """, (limit,))
            rows = await cur.fetchall()
            return [RankingEntry(
                position=r[5], user_id=r[0], alias=r[1],
                trust_score=r[2], total_orders=r[3], monthly_volume_usdt=r[4]
            ) for r in rows]
```
3. TABLA: saved_beneficiaries (Schema Completo)
```sql
CREATE TABLE IF NOT EXISTS saved_beneficiaries (
    id              SERIAL PRIMARY KEY,

    -- Dueño de la agenda (operador)
    user_id         INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,

    -- Identificación "humana" del contacto
    alias           TEXT NOT NULL,                  
    full_name       TEXT,                           
    id_number       TEXT,                           

    -- Datos de pago del receptor
    bank_name       TEXT,                           
    account_number  TEXT,                           
    phone           TEXT,                           

    -- País y tipo de destino
    dest_country    TEXT NOT NULL,                  
    payment_method  TEXT,                           

    -- Contexto adicional
    notes           TEXT,                           

    -- Cadena de versiones
    is_active       BOOLEAN NOT NULL DEFAULT true,  
    superseded_by   INTEGER REFERENCES saved_beneficiaries(id),  

    -- Gamificación
    times_used      INTEGER NOT NULL DEFAULT 0,

    -- Timestamps
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Solo un alias activo por usuario y país (evita duplicados accidentales)
CREATE UNIQUE INDEX IF NOT EXISTS uq_beneficiary_alias_active
    ON saved_beneficiaries (user_id, alias, dest_country)
    WHERE is_active = true;

-- Índices de consulta frecuente
CREATE INDEX IF NOT EXISTS idx_beneficiary_user_active
    ON saved_beneficiaries (user_id, dest_country)
    WHERE is_active = true;
```
4. TABLA: orders (Relación con beneficiaries)
```sql
-- ID del beneficiario guardado que se usó al crear esta orden (nullable).
-- Si el operador usó "Manual", este campo es NULL.
-- Si usó "Mis Favoritos", apunta al registro activo en ese momento.
ALTER TABLE orders ADD COLUMN IF NOT EXISTS beneficiary_id INTEGER REFERENCES saved_beneficiaries(id) ON DELETE SET NULL;

-- Flag para el flujo "Smart-Save": marcar órdenes manuales pendientes de guardar
ALTER TABLE orders ADD COLUMN IF NOT EXISTS smart_save_pending BOOLEAN NOT NULL DEFAULT false;

-- Índice para la query "¿Cuántas órdenes exitosas tiene este beneficiario?"
CREATE INDEX IF NOT EXISTS idx_orders_beneficiary_id ON orders (beneficiary_id) WHERE beneficiary_id IS NOT NULL;
```
5. FLUJO ACTUAL: Creación de Orden
```typescript
const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedBeneficiary) return setError("Selecciona un contacto");

    const response = await api.post("/api/operators/orders/create", {
        beneficiary_id: selectedBeneficiary,
        amount_usd: parseFloat(amount),
        payment_method: paymentMethod,
        notes: notes,
    });
    // ...
};
```
6. API: Crear Orden (Backend)
```python
@router.post("/orders/create")
async def create_order_web(
    req: CreateOrderRequest,
    user_id: int = Depends(get_current_operator)
):
    """
    Crea una nueva orden desde la interfaz web.
    """
    async with get_async_conn() as conn:
        async with conn.cursor() as cur:
            # 1. Verificar que el beneficiario existe y pertenece al operador
            await cur.execute(
                """
                SELECT id, full_name, payment_method, account_number
                FROM saved_beneficiaries
                WHERE id = %s AND user_id = %s
                """,
                (req.beneficiary_id, user_id)
            )
            beneficiary = await cur.fetchone()
            
            # ... validaciones ...
            
            # 3. Crear la orden
            order_id = str(uuid4())
            await cur.execute(
                """
                INSERT INTO orders (
                    id, user_id, beneficiary_id, amount_usd,
                    payment_method, status, notes, created_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
                RETURNING id
                """,
                (
                    order_id,
                    user_id,
                    req.beneficiary_id,
                    req.amount_usd,
                    req.payment_method,
                    "PENDING_APPROVAL",  # Requiere aprobación de admin
                    req.notes
                )
            )
```
7. CONCLUSIONES Y GAPS
✅ Lo que YA existe:
Tabla saved_beneficiaries con user_id (llave foránea directa al operador) identificada como "agenda inmutable de contactos"
Tabla orders ligada a beneficiary_id en "Smart-Save" tracking.
Endpoint /api/operators/dashboard/top-clients que hace un `GROUP BY o.beneficiary_id, o.beneficiary_text`.
Widget TopClientsWidget en frontend operativo

❌ Lo que FALTA:
- Si existen "Clientes Manuales", el agrupamiento de `top-clients` podría mezclar varias personas distintas que no están en agenda bajo un mismo nombre "Cliente Manual".  
- No existe un sistema de filtrado robusto o Leaderboard "Global" de clientes en `/clientes` para ver su Top Histórico.

📋 PLAN DE ACCIÓN:
[Paso 1] Promover el "Smart-Save" para todos los clientes para dejar el nombre manual en nulo.
[Paso 2] Actualizar el frontend de `/clientes` para agregar columnas de "Total Vol" y "Ordenes", integrando data de `TopClients`.

FIN DEL REPORTE
