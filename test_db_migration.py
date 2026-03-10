import asyncio
import os
from src.db.connection import get_async_conn

async def test_db():
    try:
        async with get_async_conn() as conn:
            async with conn.cursor() as cur:
                print("Running mock migration...")
                await cur.execute("ALTER TABLE vaults ADD COLUMN IF NOT EXISTS type VARCHAR(50);")
                await cur.execute("ALTER TABLE vaults ADD COLUMN IF NOT EXISTS tipo VARCHAR(50);")
                
                await cur.execute("""
                    CREATE TABLE IF NOT EXISTS clients (
                        id SERIAL PRIMARY KEY,
                        operator_user_id INTEGER NOT NULL,
                        full_name VARCHAR(255) NOT NULL,
                        total_orders INTEGER DEFAULT 0,
                        total_volume NUMERIC(16, 2) DEFAULT 0,
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                        updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                    );
                """)
                
                try:
                    await cur.execute('ALTER TABLE clients ADD CONSTRAINT unq_operator_client UNIQUE(operator_user_id, full_name);')
                except Exception as e:
                    print("Constraint exists or error:", e)

                await cur.execute("ALTER TABLE orders ADD COLUMN IF NOT EXISTS client_id INTEGER REFERENCES clients(id) ON DELETE SET NULL;")
                print("Migration successful")
                
                print("Testing upsert...")
                await cur.execute("""
                    INSERT INTO clients (operator_user_id, full_name) 
                    VALUES (%s, %s) 
                    ON CONFLICT (operator_user_id, full_name) 
                    DO UPDATE SET full_name = EXCLUDED.full_name, updated_at = now()
                    RETURNING id;
                """, (1, "Juan Perez Test"))
                c_row = await cur.fetchone()
                print("Upsert result:", c_row)
                
                while await cur.fetchone() is not None:
                    pass
                
                print("Testing top clients...")
                await cur.execute("""
                    SELECT c.id, c.full_name, SUM(o.amount_origin) as total_volume
                    FROM clients c
                    JOIN orders o ON c.id = o.client_id
                    WHERE o.status IN ('PAGADA', 'COMPLETADA')
                    GROUP BY c.id, c.full_name
                    ORDER BY total_volume DESC
                    LIMIT 5;
                """)
                rows = await cur.fetchall()
                print("Top clients:", rows)
                
    except Exception as e:
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    from dotenv import load_dotenv
    load_dotenv('.env.railway') # we don't know the exact env so we fallback to assuming DATABASE_URL is somehow accessible, but if it's not set, this will fail.
    asyncio.run(test_db())
