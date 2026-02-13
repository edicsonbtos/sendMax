import psycopg
conn = psycopg.connect('postgresql://neondb_owner:npg_8Eqh0xcTGVXQ@ep-damp-wave-ahgz5qnw-pooler.c-3.us-east-1.aws.neon.tech/neondb?sslmode=require')
cur = conn.cursor()

print("=== PRECIOS P2P RECIENTES ===")
cur.execute("SELECT country, fiat, buy_price, sell_price, source, captured_at FROM p2p_country_prices ORDER BY captured_at DESC LIMIT 10")
for r in cur.fetchall():
    print(f"  {r[0]:12} {r[1]:5} buy={r[2]:>10.2f} sell={r[3]:>10.2f} src={r[4]:10} {r[5]}")

print("\n=== RATE_VERSIONS RECIENTES ===")
cur.execute("SELECT id, created_at FROM rate_versions ORDER BY id DESC LIMIT 5")
for r in cur.fetchall():
    print(f"  version={r[0]} created={r[1]}")

print("\n=== ORDEN #20 COMPLETA (sin profit_real) ===")
cur.execute("SELECT public_id, origin_country, dest_country, origin_currency, dest_currency, amount_origin, payout_dest, rate_client, commission_pct, profit_usdt, profit_real_usdt, execution_price_buy, execution_price_sell, rate_version_id FROM orders WHERE public_id=20")
r = cur.fetchone()
if r:
    print(f"  ID: #{r[0]}")
    print(f"  Ruta: {r[1]} -> {r[2]}")
    print(f"  Monedas: {r[3]} -> {r[4]}")
    print(f"  Monto origen: {r[5]}")
    print(f"  Payout destino: {r[6]}")
    print(f"  Rate cliente: {r[7]}")
    print(f"  Comision %: {r[8]}")
    print(f"  Profit teorico: {r[9]}")
    print(f"  Profit real: {r[10]}")
    print(f"  Precio buy: {r[11]}")
    print(f"  Precio sell: {r[12]}")
    print(f"  Rate version: {r[13]}")

print("\n=== TRADES DE ORDEN #20 ===")
cur.execute("SELECT side, fiat_currency, fiat_amount, price, usdt_amount, fee_usdt FROM order_trades WHERE order_public_id=20")
rows = cur.fetchall()
if not rows:
    print("  SIN TRADES - por eso profit_real es None")
else:
    for r in rows:
        print(f"  {r[0]:4} {r[1]} {r[2]:>10.2f} @ {r[3] or 0:>8.4f} = {r[4]:>8.2f} USDT fee={r[5] or 0}")

print("\n=== FORMULA EXPLICADA ===")
print("  profit_teorico = se calcula al crear la orden con rate_client")
print("  profit_real = BUY_USDT - SELL_USDT - FEES (de order_trades)")
print("  Si no hay trades, profit_real = None")

conn.close()
