import psycopg
conn = psycopg.connect('postgresql://neondb_owner:npg_8Eqh0xcTGVXQ@ep-damp-wave-ahgz5qnw-pooler.c-3.us-east-1.aws.neon.tech/neondb?sslmode=require')
cur = conn.cursor()

print("=== COLUMNAS orders ===")
cur.execute("SELECT column_name, data_type, is_nullable, column_default FROM information_schema.columns WHERE table_name='orders' ORDER BY ordinal_position")
for r in cur.fetchall():
    print(f"  {r[0]:30} {r[1]:25} null={r[2]:3} default={r[3] or '-'}")

print("\n=== COLUMNAS order_trades ===")
cur.execute("SELECT column_name, data_type, is_nullable, column_default FROM information_schema.columns WHERE table_name='order_trades' ORDER BY ordinal_position")
for r in cur.fetchall():
    print(f"  {r[0]:30} {r[1]:25} null={r[2]:3} default={r[3] or '-'}")

print("\n=== COLUMNAS p2p_country_prices ===")
cur.execute("SELECT column_name, data_type, is_nullable FROM information_schema.columns WHERE table_name='p2p_country_prices' ORDER BY ordinal_position")
for r in cur.fetchall():
    print(f"  {r[0]:30} {r[1]:25} null={r[2]}")

print("\n=== EJEMPLO ORDEN RECIENTE ===")
cur.execute("SELECT public_id, status, origin_country, dest_country, amount_origin, payout_dest, profit_usdt, profit_real_usdt FROM orders ORDER BY created_at DESC LIMIT 3")
for r in cur.fetchall():
    print(f"  #{r[0]} {r[1]:20} {r[2]}->{r[3]} origin={r[4]} payout={r[5]} profit_teorico={r[6]} profit_real={r[7]}")

print("\n=== EJEMPLO TRADES ===")
cur.execute("SELECT order_public_id, side, fiat_currency, fiat_amount, price, usdt_amount, fee_usdt FROM order_trades ORDER BY created_at DESC LIMIT 5")
for r in cur.fetchall():
    print(f"  Orden #{r[0]} {r[1]:4} {r[2]} {r[3]:>10.2f} @ {r[4] or 0:>8.4f} = {r[5]:>8.2f} USDT fee={r[6] or 0}")

print("\n=== PRECIOS P2P ===")
cur.execute("SELECT * FROM p2p_country_prices ORDER BY updated_at DESC LIMIT 5")
for r in cur.fetchall():
    print(f"  {r}")

conn.close()
