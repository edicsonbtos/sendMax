import os, psycopg

url = os.environ["DATABASE_URL"]
with psycopg.connect(url) as c:
    with c.cursor() as cur:
        cur.execute("""
            select public_id, status, created_at, origin_verified_at
            from orders
            where status in ('ORIGEN_VERIFICANDO','ORIGEN_CONFIRMADO')
            order by created_at desc
            limit 5;
        """)
        print(cur.fetchall())
