# 🔍 AUDITORÍA - FLUJO DE CLIENTES EN ÓRDENES

## 1️⃣ ESTADO DEL FRONTEND

### Archivo: `ordenes/nueva/page.tsx`
- **¿Pide nombre del cliente?** NO.
- **¿Cómo lo captura?** El formulario solo permite seleccionar un "Contacto / Beneficiario" de una lista preexistente obtenida del backend. No existe un input de texto para ingresar el nombre del cliente real (remitente).
- **Campo actual:** `selectedBeneficiary` (que almacena el `id` numérico del beneficiario seleccionado).

### Código relevante:
```typescript
interface Beneficiary { id: number; full_name: string; ... }

const [selectedBeneficiary, setSelectedBeneficiary] = useState<number | null>(null);

// En el submit:
const response = await api.post("/api/operators/orders/create", {
    beneficiary_id: selectedBeneficiary,
    amount_usd: parseFloat(amount),
    payment_method: paymentMethod,
    notes: notes,
});
```

## 2️⃣ ESTADO DEL BACKEND
### Endpoint: `POST /api/operators/orders/create` (en `src/api/operators.py`)
- **¿Acepta nombre de cliente?** NO.
- **Campo utilizado:** Solo acepta `beneficiary_id`.
- **¿Es obligatorio?** SÍ.

### Código relevante:
```python
class CreateOrderRequest(BaseModel):
    beneficiary_id: int  # ID del contacto guardado
    amount_usd: Decimal
    payment_method: str
    notes: str = ""

@router.post("/orders/create")
async def create_order_web(req: CreateOrderRequest, user_id: int = Depends(get_current_operator)):
    # ...
    await cur.execute(
        """
        INSERT INTO orders (
            id, user_id, beneficiary_id, amount_usd,
            payment_method, status, notes, created_at
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
        RETURNING id
        """,
        (order_id, user_id, req.beneficiary_id, req.amount_usd, req.payment_method, "PENDING_APPROVAL", req.notes)
    )
```

## 3️⃣ ESQUEMA DE BASE DE DATOS
### Tabla: `orders`
Campos relacionados con cliente:
- **beneficiary_id:** `INTEGER` - FK a `saved_beneficiaries` (Añadido en migraciones posteriores al MVP).
- **beneficiary_text:** `TEXT NOT NULL` - Este campo existe desde la migración inicial (`8249dc838371_create_orders.py`), diseñado originalmente para "texto manual", pero **actualmente el endpoint web NO lo está llenando/usando.**
- **client_name:** **NO EXISTE**. La base de datos asume actualmente que el "Beneficiario" (a quien le llega el dinero) es el único actor relevante a registrar, omitiendo la figura del "Cliente/Remitente" real.

## 4️⃣ CÓMO FUNCIONA EL RANKING ACTUAL
### Query SQL del ranking (`src/api/routes/client_ranking.py`):
```sql
WITH client_stats AS (
    SELECT 
        sb.id as beneficiary_id,
        COALESCE(sb.full_name, sb.alias) as name,
        -- ...
    FROM saved_beneficiaries sb
    LEFT JOIN orders o ON o.beneficiary_id = sb.id
    WHERE sb.user_id = %s AND sb.is_active = true
    GROUP BY sb.id, sb.full_name, sb.alias, sb.phone, sb.dest_country
)
```
### Lógica:
- **Filtra por:** Contactos (`saved_beneficiaries`) que pertenecen al operador logueado (`user_id`).
- **Agrupa por:** El ID del **Beneficiario** (`sb.id`).
- **Nombre viene de:** El nombre guardado en la libreta de contactos del operador (`saved_beneficiaries.full_name` o su `alias`).
- **Si `beneficiary_id` es NULL en una orden:** Dado que el query parte de `saved_beneficiaries` haciendo un `LEFT JOIN`, cualquier orden huerfana (sin `beneficiary_id`) **es ignorada por completo** y no suma volumen ni operaciones a ningún cliente en el Leaderboard.

## 5️⃣ FLUJO COMPLETO ACTUAL

┌─────────────────────────────────────────────┐
│ PASO 1: Operador va a /ordenes/nueva        │
└─────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────┐
│ PASO 2: Visualiza el formulario             │
│ - SÍ hay lista de contactos guardados.      │
│ - NO hay campo para nombre manual del       │
│   cliente real (quien envía el dinero).     │
│ - NO puede crear orden sin seleccionar un   │
│   contacto (es obligatorio).                │
└─────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────┐
│ PASO 3: Hace clic en un contacto de la lista│
│ e ingresa monto y método de pago.           │
└─────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────┐
│ PASO 4: Submit → Backend                    │
│ Datos enviados:                             │
│ {                                           │
│   "beneficiary_id": 12,                     │
│   "amount_usd": 150,                        │
│   "payment_method": "Zelle",                │
│   "notes": ""                               │
│ }                                           │
└─────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────┐
│ PASO 5: Insertar en tabla orders            │
│ - beneficiary_id: 12                        │
│ - beneficiary_text: [NO SE INSERTA NADA]*   │
│ - user_id: [del token]                      │
│ *Ojo: si la DB exige NOT NULL, esto podría  │
│ fallar o estar usando un default/trigger.   │
└─────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────┐
│ PASO 6: Aparece en /clientes                │
│ - SÍ, porque la orden quedó vinculada a un  │
│   beneficiary_id válido, el ranking suma su │
│   volumen al contacto seleccionado.         │
└─────────────────────────────────────────────┘

## 6️⃣ GAPS IDENTIFICADOS
❌ **Lo que NO funciona:**
- El sistema **funde la figura de "Cliente" y "Beneficiario" en una sola**. Si "María" le envía dinero a 3 familiares distintos en Venezuela (3 beneficiarios), el Leaderboard actual mostrará a los 3 familiares como "clientes" separados, diluyendo el volumen real de "María".
- No hay rastro de quién entregó el Zelle o el efectivo, solo hacia dónde va destinado.

⚠️ **Lo que está incompleto:**
- El endpoint ignora el campo heredado `beneficiary_text`.
- Si se hiciera una integración directa desde Telegram donde las órdenes lleguen sin `beneficiary_id` (forma manual), esas órdenes jamás aparecerán en el Leaderboard bajo la arquitectura actual.

## 7️⃣ PROPUESTA SIMPLE
### Solución Mínima: Separar Cliente de Beneficiario (Añadir `client_name`)
Permitir que el operador escriba el "Nombre del Cliente" en la orden, de forma independiente al destino (beneficiario).

**Cambios necesarios:**

1. **Base de datos:**
   - Crear una migración Alembic rápida: `ALTER TABLE orders ADD COLUMN client_name VARCHAR(255) NULL;`
2. **Backend (`src/api/operators.py`):**
   - Actualizar el DTO `CreateOrderRequest` añadiendo `client_name: Optional[str] = None`.
   - Incluirlo en el `INSERT` dentro de `create_order_web`.
3. **Frontend (`ordenes/nueva/page.tsx`):**
   - Agregar un input superior simple: "Nombre del Cliente / Remitente (Opcional)".
   - Mandar el valor en el payload del POST.

*(Nota sobre el Leaderboard)*: Si implementamos esto, más adelante el Leaderboard podría evolucionar para agrupar por `client_name` en vez de `beneficiary_id` para ver el peso real del cliente remitente.

**Tiempo estimado:** 10-15 minutos.

FIN DEL REPORTE
