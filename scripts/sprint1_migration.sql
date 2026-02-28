-- ============================================================
-- Sendmax 2.0 — Sprint 1 Migration
-- Ejecutar en Neon (SQL Editor) ANTES del git push del código.
-- Todo es idempotente: IF NOT EXISTS + safe defaults.
-- ============================================================

-- ────────────────────────────────────────────────────────────
-- BLOQUE 1: Tabla vaults (Radar de Bóvedas)
-- ────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS vaults (
    id           SERIAL PRIMARY KEY,
    name         TEXT NOT NULL,                         -- "Zelle Fernanda", "Los Teques Cash", "BCP Peru"
    vault_type   TEXT NOT NULL DEFAULT 'Digital',       -- Digital | Physical | Crypto
    currency     TEXT NOT NULL DEFAULT 'USD',           -- USD, USDT, VES, CLP, COP, PEN...
    balance      NUMERIC(18, 8) NOT NULL DEFAULT 0,     -- Saldo actual (ajuste manual)
    description  TEXT,                                  -- Notas internas (banco, titular, etc.)
    is_active    BOOLEAN NOT NULL DEFAULT true,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT vaults_name_unique UNIQUE (name)
);

COMMENT ON TABLE vaults IS 'Bóvedas de liquidez de Sendmax: wallets digitales, efectivo físico y billeteras cripto.';
COMMENT ON COLUMN vaults.vault_type IS 'Digital=cuenta bancaria/digital, Physical=efectivo en ubicación, Crypto=wallet cripto';

-- Datos iniciales de ejemplo (puedes editar o borrar)
INSERT INTO vaults (name, vault_type, currency, description)
VALUES
    ('Zelle Principal',    'Digital',  'USD',  'Cuenta Zelle principal de pagos USA'),
    ('Los Teques Cash',    'Physical', 'USD',  'Efectivo USD en la sede Los Teques'),
    ('Caracas Cash',       'Physical', 'USD',  'Efectivo USD en la sede Caracas'),
    ('USDT Wallet Hot',    'Crypto',   'USDT', 'Billetera USDT para liquidaciones rápidas'),
    ('BCP Peru',           'Digital',  'PEN',  'Cuenta BCP para pagos a Peru'),
    ('Bancolombia',        'Digital',  'COP',  'Cuenta Bancolombia para pagos a Colombia')
ON CONFLICT (name) DO NOTHING;


-- ────────────────────────────────────────────────────────────
-- BLOQUE 2: Columnas nuevas en orders (provider_fee waterfall)
-- Todas nullable con DEFAULT 0 → cero riesgo en producción.
-- ────────────────────────────────────────────────────────────

-- ID del proveedor de cuenta (usuario interno de Sendmax que prestó su cuenta)
ALTER TABLE orders ADD COLUMN IF NOT EXISTS provider_id INTEGER REFERENCES users(id) ON DELETE SET NULL;

-- Porcentaje de comisión del proveedor (ej: 0.03 = 3%)
ALTER TABLE orders ADD COLUMN IF NOT EXISTS provider_fee_pct NUMERIC(6, 4) NOT NULL DEFAULT 0;

-- Monto en USDT efectivamente pagado al proveedor en esta orden
ALTER TABLE orders ADD COLUMN IF NOT EXISTS provider_fee_usdt NUMERIC(18, 8) NOT NULL DEFAULT 0;

-- Utilidad repartible real = profit_real_usdt - provider_fee_usdt
-- (sobre este valor se aplica el split 45/45/10 o 50/50)
ALTER TABLE orders ADD COLUMN IF NOT EXISTS distributable_profit NUMERIC(18, 8) NOT NULL DEFAULT 0;

-- Índice para queries de liquidación por proveedor
CREATE INDEX IF NOT EXISTS idx_orders_provider_id ON orders (provider_id) WHERE provider_id IS NOT NULL;


-- ────────────────────────────────────────────────────────────
-- BLOQUE 3: Ledger type nuevo para fees de proveedor
-- (wallet_ledger ya acepta cualquier TEXT en 'type', no hay enum)
-- Solo documentamos los valores nuevos:
--   PROVIDER_FEE      → débito en la cuenta del proveedor (lo que Sendmax le debe)
--   PROVIDER_PAYMENT  → cuando se le paga al proveedor
-- ────────────────────────────────────────────────────────────

-- No se requiere ninguna DDL adicional para wallet_ledger.


-- ────────────────────────────────────────────────────────────
-- VERIFICACIÓN  (opcional, corre esto para confirmar)
-- ────────────────────────────────────────────────────────────

SELECT 'vaults' AS tabla, COUNT(*) AS filas FROM vaults
UNION ALL
SELECT 'orders.provider_id existe' AS tabla,
       COUNT(*) AS filas
FROM information_schema.columns
WHERE table_name = 'orders' AND column_name = 'provider_id'
UNION ALL
SELECT 'orders.provider_fee_pct existe' AS tabla,
       COUNT(*) AS filas
FROM information_schema.columns
WHERE table_name = 'orders' AND column_name = 'provider_fee_pct';
