-- ============================================================
-- Sendmax Web Panel - Migraciones adicionales
-- ============================================================

-- Tabla para borradores de órdenes (pre-carga)
CREATE TABLE IF NOT EXISTS order_drafts (
    id SERIAL PRIMARY KEY,
    operator_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    customer_name TEXT,
    customer_phone TEXT,
    origin VARCHAR(50),
    dest VARCHAR(50),
    estimated_amount NUMERIC(18,8),
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL DEFAULT (NOW() + INTERVAL '24 hours')
);

CREATE INDEX IF NOT EXISTS idx_drafts_operator ON order_drafts(operator_id, created_at DESC);

-- Tabla para metas diarias
CREATE TABLE IF NOT EXISTS daily_goals (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    target_usdt NUMERIC(18,8) NOT NULL DEFAULT 100,
    current_usdt NUMERIC(18,8) NOT NULL DEFAULT 0,
    date DATE NOT NULL DEFAULT CURRENT_DATE,
    UNIQUE(user_id, date)
);

-- Agregar campos para password web en users
ALTER TABLE users ADD COLUMN IF NOT EXISTS password_hash TEXT;
ALTER TABLE users ADD COLUMN IF NOT EXISTS email TEXT UNIQUE;

-- Índices de performance para queries del dashboard
CREATE INDEX IF NOT EXISTS idx_orders_operator_status_date 
    ON orders(operator_id, status, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_orders_operator_monthly 
    ON orders(operator_id, DATE_TRUNC('month', created_at));
