import os
import psycopg

def main():
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        print("DATABASE_URL is not set")
        return
    
    # Strip asyncpg scheme if present for sync psycopg
    if db_url.startswith("postgresql+asyncpg://"):
        db_url = db_url.replace("postgresql+asyncpg://", "postgresql://")

    try:
        with psycopg.connect(db_url) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'wallet_ledger'")
                print(cur.fetchall())
    except Exception as e:
        print(f"Error querying db: {e}")

if __name__ == "__main__":
    main()
