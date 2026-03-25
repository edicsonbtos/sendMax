# SendMax — Modelo Financiero Canónico

Documento de referencia para las métricas financieras del sistema.
Última validación contra datos de producción: 2026-03-24.

---

## Métricas Canónicas

### `gross_profit` — Utilidad Bruta
- **Definición:** Suma total de ganancias generadas por órdenes terminadas, antes de repartir comisiones a operadores.
- **Fuente:** `orders.profit_real_usdt` donde `status IN ('PAGADA', 'COMPLETADA')`
- **Query:**
  ```sql
  SELECT COALESCE(SUM(profit_real_usdt), 0) FROM orders WHERE status IN ('PAGADA', 'COMPLETADA');
  ```
- **Qué NO significa:** No es caja libre, no es saldo bancario, no es dinero gastable. Incluye la porción que pertenece a los operadores.
- **Nota:** `COMPLETADA` concentra el histórico observado; se mantiene `PAGADA` por prudencia ante posibles flujos intermedios.

### `operator_commissions` — Comisiones Acreditadas
- **Definición:** Suma total acreditada a operadores en el ledger por concepto de ganancias por órdenes.
- **Fuente:** `wallet_ledger.amount_usdt` donde `type = 'ORDER_PROFIT'`
- **Query:**
  ```sql
  SELECT COALESCE(SUM(amount_usdt), 0) FROM wallet_ledger WHERE type = 'ORDER_PROFIT';
  ```
- **Qué NO significa:** No es caja del negocio. Es un gasto de venta ya comprometido.

### `operator_liabilities` — Obligaciones con Operadores
- **Definición:** Saldo total en wallets de operadores que puede ser retirado en cualquier momento. Es un pasivo exigible.
- **Fuente:** `wallets.balance_usdt`
- **Query:**
  ```sql
  SELECT COALESCE(SUM(balance_usdt), 0) FROM wallets;
  ```
- **Qué NO significa:** No es dinero del negocio. El negocio lo custodia pero pertenece a los operadores.

### `resolved_payouts` — Retiros Pagados
- **Definición:** Suma total de retiros ya materializados (dinero que salió del sistema hacia wallets externas de operadores).
- **Fuente:** `withdrawals.amount_usdt` donde `status = 'RESUELTA'`
- **Query:**
  ```sql
  SELECT COALESCE(SUM(amount_usdt), 0) FROM withdrawals WHERE status = 'RESUELTA';
  ```
- **Qué NO significa:** No incluye retiros pendientes ni rechazados.
- **Nota:** Estado observado en producción: RESUELTA, SOLICITADA, RECHAZADA. No se observaron estados PAID/PAGADO.

### `business_retained_profit` — Utilidad Retenida del Negocio
- **Definición:** Estimación interna de la porción de la utilidad bruta que no fue acreditada a operadores.
- **Fórmula:** `gross_profit - operator_commissions`
- **Qué NO significa:** No es caja libre confirmada. No se cruza con saldo bancario/cripto externo. No descuenta gastos operativos fuera del sistema.
- **Riesgo:** Si existen gastos no registrados en el sistema, la utilidad real será menor.

### `withdrawal_coverage_estimate` — Estimación de Cobertura de Retiros
- **Definición:** Proxy teórica de cuántas veces el remanente bruto retenido cubre las obligaciones con operadores.
- **Fórmula:** `(gross_profit - resolved_payouts) / operator_liabilities`
- **Qué NO significa:** No reemplaza una conciliación de caja real. No considera fondos externos.
- **Riesgo:** Si < 1.0, el sistema podría no tener liquidez teórica para cubrir todos los retiros pendientes. Verificar siempre contra saldo externo.
- **Caso especial:** Si `operator_liabilities = 0`, devolver `null` (no hay operadores con saldo).
