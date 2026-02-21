import os
import psycopg
import bcrypt

EMAIL = "admin@sendmax.com"
NEW_PASSWORD = "Admin123!"

url = os.environ["postgresql://neondb_owner:npg_8Eqh0xcTGVXQ@ep-damp-wave-ahgz5qnw-pooler.c-3.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=requirea"]
hashed = bcrypt.hashpw(NEW_PASSWORD.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

with psycopg.connect(url) as conn:
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE users SET hashed_password=%s WHERE email=%s RETURNING id, email, role;",
            (hashed, EMAIL),
        )
        row = cur.fetchone()
    conn.commit()

print("UPDATED:", row)
