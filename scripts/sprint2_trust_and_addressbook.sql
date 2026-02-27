-- ============================================================
-- Sendmax — Sprint 2 + 2.5 Migration
-- Trust Score (reputación) + Agenda de Contactos Inteligente
--
-- IMPORTANTE: Ejecuta en Neon ANTES del git push del código.
-- Todo es idempotente (IF NOT EXISTS / ON CONFLICT).
-- ============================================================


-- ────────────────────────────────────────────────────────────
-- BLOQUE 1: Trust Score en users
-- ────────────────────────────────────────────────────────────

-- Puntuación acumulada del operador (0-100, default neutro 50)
ALTER TABLE users ADD COLUMN IF NOT EXISTS trust_score NUMERIC(5,2) NOT NULL DEFAULT 50;

-- Timestamp del último cambio (útil para mostrar "actualizado hace X días")
ALTER TABLE users ADD COLUMN IF NOT EXISTS trust_score_updated_at TIMESTAMPTZ;

-- Índice para ordenar leaderboard
CREATE INDEX IF NOT EXISTS idx_users_trust_score ON users (trust_score DESC);


-- ────────────────────────────────────────────────────────────
-- BLOQUE 2: Log de movimientos de Trust Score
-- Registro inmutable de cada evento que cambia el score.
-- ────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS trust_score_log (
    id                   SERIAL PRIMARY KEY,
    user_id              INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    delta                NUMERIC(5,2) NOT NULL,          -- positivo suma, negativo resta
    score_after          NUMERIC(5,2),                   -- snapshot del score luego del movimiento
    reason               TEXT NOT NULL,                  -- 'ORDER_COMPLETED', 'ORDER_CANCELLED', etc.
    ref_order_public_id  INTEGER,                        -- orden que generó el evento (nullable)
    ref_beneficiary_id   INTEGER,                        -- si fue por orden hacia favorito
    created_at           TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_trust_log_user ON trust_score_log (user_id, created_at DESC);

COMMENT ON TABLE trust_score_log IS 'Historial de variaciones del Trust Score por operador.';
COMMENT ON COLUMN trust_score_log.delta IS 'Positivo = suma puntos. Negativo = resta puntos.';


-- ────────────────────────────────────────────────────────────
-- BLOQUE 3: Agenda de Contactos (saved_beneficiaries)
--
-- DISEÑO CLAVE — Inmutabilidad con cadena de versiones:
--
--   Problema: Si el operador "edita" un beneficiario (ej: cambió
--   de cuenta bancaria), las órdenes pasadas apuntarían a datos
--   incorrectos si actualizamos en-place.
--
--   Solución: Nunca se edita un registro existente.
--   Al "actualizar", se crea un registro nuevo y el anterior
--   queda marcado como is_active=false con el campo
--   superseded_by apuntando al nuevo. Así:
--
--   ✅ Las órdenes pasadas siempre apuntan al snapshot correcto.
--   ✅ La UI muestra solo los activos.
--   ✅ El admin puede auditar el historial completo.
-- ────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS saved_beneficiaries (
    id              SERIAL PRIMARY KEY,

    -- Dueño de la agenda (operador)
    user_id         INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,

    -- Identificación "humana" del contacto
    alias           TEXT NOT NULL,                  -- 'Mi Papá', 'Cliente Habitual Lima'
    full_name       TEXT,                           -- Nombre completo del receptor
    id_number       TEXT,                           -- Cédula/DNI/Pasaporte

    -- Datos de pago del receptor
    bank_name       TEXT,                           -- 'BCP', 'Bancolombia', 'Zinli'
    account_number  TEXT,                           -- Número de cuenta / CBU / CLABE
    phone           TEXT,                           -- Teléfono para Yape/Nequi/Bizum

    -- País y tipo de destino
    dest_country    TEXT NOT NULL,                  -- 'PERU', 'COLOMBIA', 'VENEZUELA'...
    payment_method  TEXT,                           -- 'Transferencia', 'Yape', 'Nequi', 'Efectivo'

    -- Contexto adicional
    notes           TEXT,                           -- Notas internas del operador

    -- ── Cadena de versiones (control de cambios elegante) ──
    is_active       BOOLEAN NOT NULL DEFAULT true,  -- false = registro antiguo/reemplazado
    superseded_by   INTEGER REFERENCES saved_beneficiaries(id),  -- apunta a la versión nueva

    -- Gamificación: cuántas órdenes se han creado usando este contacto
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

COMMENT ON TABLE saved_beneficiaries IS 'Agenda de contactos del operador. Inmutable: nunca se edita en-place; se crea nueva versión y la anterior queda superseded.';
COMMENT ON COLUMN saved_beneficiaries.superseded_by IS 'FK al registro que reemplazó a éste. NULL = versión actual.';
COMMENT ON COLUMN saved_beneficiaries.times_used IS 'Contador de órdenes creadas usando este contacto (incrementado atómicamente).';


-- ────────────────────────────────────────────────────────────
-- BLOQUE 4: Columnas nuevas en orders
-- Vincula la orden con el beneficiario guardado (snapshot_id)
-- ────────────────────────────────────────────────────────────

-- ID del beneficiario guardado que se usó al crear esta orden (nullable).
-- Si el operador usó "Manual", este campo es NULL.
-- Si usó "Mis Favoritos", apunta al registro activo en ese momento.
ALTER TABLE orders ADD COLUMN IF NOT EXISTS beneficiary_id INTEGER REFERENCES saved_beneficiaries(id) ON DELETE SET NULL;

-- Flag para el flujo "Smart-Save": marcar órdenes manuales pendientes de guardar
ALTER TABLE orders ADD COLUMN IF NOT EXISTS smart_save_pending BOOLEAN NOT NULL DEFAULT false;

-- Índice para la query "¿Cuántas órdenes exitosas tiene este beneficiario?"
CREATE INDEX IF NOT EXISTS idx_orders_beneficiary_id ON orders (beneficiary_id) WHERE beneficiary_id IS NOT NULL;


-- ────────────────────────────────────────────────────────────
-- BLOQUE 5: Settings para la auto-aprobación (Sprint 3, adelantamos)
-- ────────────────────────────────────────────────────────────

INSERT INTO settings (key, value, description)
VALUES
    ('auto_approve_enabled',       'false', 'Activa auto-aprobación para operadores de alta confianza'),
    ('auto_approve_min_trust',     '90',    'Trust score mínimo para auto-aprobar una orden'),
    ('auto_approve_max_amount_usd','500',   'Monto máximo USD para auto-aprobar (monto origen en USD equivalente)')
ON CONFLICT (key) DO NOTHING;


-- ────────────────────────────────────────────────────────────
-- VERIFICACIÓN FINAL (corre esto para confirmar)
-- ────────────────────────────────────────────────────────────

SELECT 'trust_score en users' AS check,
       COUNT(*) AS ok
FROM information_schema.columns
WHERE table_name = 'users' AND column_name = 'trust_score'

UNION ALL

SELECT 'trust_score_log existe',
       COUNT(*) FROM information_schema.tables
WHERE table_name = 'trust_score_log'

UNION ALL

SELECT 'saved_beneficiaries existe',
       COUNT(*) FROM information_schema.tables
WHERE table_name = 'saved_beneficiaries'

UNION ALL

SELECT 'orders.beneficiary_id existe',
       COUNT(*) FROM information_schema.columns
WHERE table_name = 'orders' AND column_name = 'beneficiary_id'

UNION ALL

SELECT 'auto_approve settings', COUNT(*)
FROM settings WHERE key LIKE 'auto_approve%';
