import os
import psycopg
import bcrypt

EMAIL = "admin@sendmax.com"
NEW_PASSWORD = "Admin123!"

url = os.environ.get("DATABASE_URL")
if not url:
    print("Error: DATABASE_URL not set.")
    exit(1)

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
