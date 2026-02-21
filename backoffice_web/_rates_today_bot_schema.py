import os
import psycopg

url = os.environ["postgresql://neondb_owner:npg_8Eqh0xcTGVXQ@ep-damp-wave-ahgz5qnw-pooler.c-3.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require&keepalives=1&keepalives_idle=30&keepalives_interval=10&keepalives_count=5&connect_timeout=10"]

with psycopg.connect(url) as conn:
    with conn.cursor() as cur:
        cur.execute("""
            SELECT id, kind, created_at, effective_from
            FROM rate_versions
            WHERE is_active = true
            ORDER BY effective_from DESC
            LIMIT 1;
        """)
        rv = cur.fetchone()
        if not rv:
            print("No hay rate_versions activas.")
            raise SystemExit(0)

        rv_id, kind, created_at, effective_from = rv
        print(f"ACTIVE RATE VERSION: id={rv_id} kind={kind} created_at={created_at} effective_from={effective_from}\n")

        cur.execute("""
            SELECT origin_country, dest_country, commission_pct, rate_client, buy_origin, sell_dest
            FROM route_rates
            WHERE rate_version_id = %s
            ORDER BY origin_country, dest_country;
        """, (rv_id,))
        rows = cur.fetchall()

        for o,d,comm,rate_client,buy_origin,sell_dest in rows:
            print(f"{o} -> {d} | rate_client={rate_client} | comm%={comm} | buy_origin={buy_origin} | sell_dest={sell_dest}")
