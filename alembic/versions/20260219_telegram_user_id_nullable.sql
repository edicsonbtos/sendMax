-- ============================================================
-- Migracion: telegram_user_id NOT NULL -> NULLABLE
-- Ejecutar directamente en la DB de produccion
-- ============================================================

BEGIN;

-- Paso 1: Convertir IDs negativos sinteticos a NULL
UPDATE users
SET    telegram_user_id = NULL,
       updated_at = now()
WHERE  telegram_user_id < 0;

-- Paso 2: Hacer columna nullable
ALTER TABLE users
    ALTER COLUMN telegram_user_id DROP NOT NULL;

-- Paso 3: Prevenir IDs negativos futuros
ALTER TABLE users
    ADD CONSTRAINT chk_telegram_user_id_positive
    CHECK (telegram_user_id IS NULL OR telegram_user_id > 0);

-- Paso 4: Documentar
COMMENT ON COLUMN users.telegram_user_id IS
    'Telegram user ID real (>0). NULL para usuarios creados desde backoffice.';

COMMIT;