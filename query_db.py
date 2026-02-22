from src.db.connection import get_conn

with get_conn() as conn:
    with conn.cursor() as cur:
        cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' ORDER BY table_name")
        print("--- TABLAS ---")
        for row in cur.fetchall():
            print(f"  {row[0]}")

with get_conn() as conn:
    with conn.cursor() as cur:
        cur.execute("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'users' ORDER BY ordinal_position")
        print("")
        print("--- COLUMNAS USERS ---")
        for row in cur.fetchall():
            print(f"  {row[0]} ({row[1]})")

with get_conn() as conn:
    with conn.cursor() as cur:
        cur.execute("SELECT * FROM users LIMIT 5")
        cols = [d[0] for d in cur.description]
        print("")
        print(f"--- PRIMEROS 5 USERS ---")
        print(f"  Columnas: {cols}")
        for row in cur.fetchall():
            print(f"  {row}")
