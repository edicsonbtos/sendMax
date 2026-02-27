-- =================================================================
-- Módulo USD Efectivo — Script SQL de Inicialización
-- Ejecutar en Neon SQL (o Railway console) UNA SOLA VEZ antes del deploy.
--
-- Inserta la configuración de entrega en efectivo con valores por defecto.
-- Si ya existe, actualiza los valores por defecto.
-- =================================================================

INSERT INTO settings (key, value_json)
VALUES (
    'cash_delivery',
    '{
        "zelle_usdt_cost": 1.03,
        "margin_cash_zelle": 12.0,
        "margin_cash_general": 10.0
    }'::jsonb
)
ON CONFLICT (key) DO UPDATE
    SET value_json = EXCLUDED.value_json,
        updated_at = NOW()
WHERE settings.key = 'cash_delivery';

-- Verificar la inserción
SELECT key, value_json, updated_at
FROM settings
WHERE key = 'cash_delivery';

-- =================================================================
-- NOTAS:
-- * zelle_usdt_cost: Cuántos USD Zelle cuesta 1 USDT. Default 1.03
--   Fórmula: tasa_cliente = (1/zelle_usdt_cost) * (1 - margin_cash_zelle/100)
--   Ejemplo: (1/1.03) * (1 - 0.12) = 0.9709 * 0.88 ≈ 0.854 USD por 1 USD enviado
--
-- * margin_cash_zelle: Margen (%) para ruta USA(Zelle) → Efectivo. Default 12%
--
-- * margin_cash_general: Margen (%) para otras rutas Fiat → Efectivo. Default 10%
--   Fórmula: tasa_cliente = (1/buy_binance_origen) * (1 - margin_cash_general/100)
--
-- * El bot y el motor de tasas leen estos valores con cache de 60s.
--   Para aplicar cambios inmediatamente: regenerar tasas desde Settings.
-- =================================================================
