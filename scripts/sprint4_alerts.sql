-- ============================================================
-- Sprint 4: Alert Copilot — Vault alert thresholds
--
-- Ejecuta en Neon ANTES del git push.
-- ============================================================

-- Columna alert_threshold en vaults (0 = sin alerta configurada)
ALTER TABLE vaults ADD COLUMN IF NOT EXISTS alert_threshold NUMERIC(18,8) NOT NULL DEFAULT 0;

-- Umbrales iniciales (ajusta según tus vaults reales en producción)
-- Para setear umbrales, actualiza con los nombres exactos en tu tabla vaults.
-- Ejemplos (ajusta como corresponda):
UPDATE vaults SET alert_threshold = 500 WHERE name ILIKE '%zelle%' AND alert_threshold = 0;
UPDATE vaults SET alert_threshold = 200 WHERE name ILIKE '%teques%' AND alert_threshold = 0;
UPDATE vaults SET alert_threshold = 300 WHERE name ILIKE '%efectivo%' AND alert_threshold = 0;

-- Verificación
SELECT name, balance, alert_threshold,
       CASE WHEN alert_threshold > 0 AND balance < alert_threshold
            THEN '⚠️ BAJO MÍNIMO' ELSE '✅ OK' END AS estado
FROM vaults
ORDER BY name;
