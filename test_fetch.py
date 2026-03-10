import asyncio
from src.db.connection import get_async_conn

async def main():
    try:
        async with get_async_conn() as conn:
            async with conn.cursor() as cur:
                print("executing query...")
                client_name = 'Test Client'
                await cur.execute("SELECT id FROM clients WHERE full_name ILIKE %s LIMIT 1;", (client_name,))
                print("fetching...")
                c_row = await cur.fetchone()
                print("row:", c_row)
    except Exception as e:
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    asyncio.run(main())
