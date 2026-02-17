import bcrypt
import psycopg, os
from dotenv import load_dotenv

load_dotenv()

hashed = bcrypt.hashpw("Edicson2026!".encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

url = os.getenv("DATABASE_URL_RW") or os.getenv("DATABASE_URL")
conn = psycopg.connect(url)
cur = conn.cursor()

cur.execute(
    "UPDATE users SET email = %s, hashed_password = %s WHERE id = %s",
    ("edicson@sendmax.com", hashed, 1)
)
conn.commit()
print("Operador edicson actualizado")
print("Email: edicson@sendmax.com")
print("Password: Edicson2026!")

cur.close()
conn.close()
