import os
import psycopg
from datetime import date

url = os.environ["DATABASE_URL"]

with psycopg.connect(url) as conn:
    with conn.cursor() as cur:
        # 1) última versión activa de tasas (usa tu tabla rates)
        cur.execute("""
            SELECT id, created_at
            FROM rate_versions
            WHERE is_active = true
            ORDER BY id DESC
            LIMIT 1;
        """)
        rv = cur.fetchone()
        if not rv:
            print("No hay rate_versions activas.")
            raise SystemExit(0)

        rv_id, rv_created = rv
        print(f"rate_version_id={rv_id} created_at={rv_created}")
        print("")

        # 2) listar rutas y tasa cliente del día (todas las rutas en esa versión)
        cur.execute("""
            SELECT origin_country, dest_country, rate_client, buy_origin, sell_dest, updated_at
            FROM route_rates
            WHERE rate_version_id = %s
            ORDER BY origin_country, dest_country;
        """, (rv_id,))
        rows = cur.fetchall()

        for o,d,rate_client,buy_origin,sell_dest,upd in rows:
            print(f"{o:10} -> {d:10} | rate_client={rate_client} | buy_origin={buy_origin} | sell_dest={sell_dest} | updated_at={upd}")
