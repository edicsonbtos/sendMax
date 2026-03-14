import asyncio
from src.db.connection import get_async_conn

async def main():
    async with get_async_conn() as conn:
        async with conn.cursor() as cur:
            await cur.execute("""
                SELECT column_name, data_type, column_default 
                FROM information_schema.columns 
                WHERE table_name = 'clients';
            """)
            rows = await cur.fetchall()
            for r in rows:
                print(r)

if __name__ == '__main__':
    asyncio.run(main())
