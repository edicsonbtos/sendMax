import os, psycopg
url = os.environ["DATABASE_URL"]
with psycopg.connect(url) as c:
    with c.cursor() as cur:
        cur.execute("select public_id,status,created_at from orders order by created_at desc limit 1;")
        print(cur.fetchone())
