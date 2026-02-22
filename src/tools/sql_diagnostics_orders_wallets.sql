-- Duplicados ledger por orden
SELECT user_id, type, ref_order_public_id, amount_usdt, count(*)
FROM wallet_ledger
WHERE ref_order_public_id IS NOT NULL
GROUP BY user_id, type, ref_order_public_id, amount_usdt
HAVING count(*) > 1;

-- Órdenes awaiting_paid_proof true y status inesperado
SELECT public_id, status, awaiting_paid_proof, awaiting_paid_proof_at
FROM orders
WHERE awaiting_paid_proof = true
  AND status NOT IN ('EN_PROCESO', 'PAGADA');

-- Órdenes CREADA antiguas sin ORIGEN_VERIFICANDO (posible fallo oculto)
SELECT public_id, status, created_at
FROM orders
WHERE status = 'CREADA'
ORDER BY created_at ASC
LIMIT 50;

-- Órdenes ORIGEN_CONFIRMADO que no avanzan
SELECT public_id, status, origin_verified_at
FROM orders
WHERE status = 'ORIGEN_CONFIRMADO'
ORDER BY origin_verified_at DESC
LIMIT 50;

-- Wallets sin ledger / ledger sin wallet (consistencia)
SELECT l.user_id
FROM wallet_ledger l
LEFT JOIN wallets w ON w.user_id = l.user_id
WHERE w.user_id IS NULL
GROUP BY l.user_id;
