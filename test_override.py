import asyncio
from decimal import Decimal
import os
import sys

# Add src to pythonpath
sys.path.insert(0, os.path.abspath('.'))

from src.integrations.price_override import get_buy_price, _get_manual_price

async def test():
    print("Testing manual fetch for USA/Zelle...")
    try:
        manual = await _get_manual_price("USA", "Zelle")
        print(f"Manual price USA/Zelle: {manual}")
        price = await get_buy_price("USA", "Zelle")
        print(f"Final price USA/Zelle (from override function): {price}")
    except Exception as e:
        print("Error in _get_manual_price USA/Zelle:", e)
        
    print("\nTesting fallback to Binance for COLOMBIA/Bancolombia...")
    try:
        col_price = await get_buy_price("COLOMBIA", "Bancolombia")
        print(f"Price COLOMBIA/Bancolombia (from Binance): {col_price}")
    except Exception as e:
        print("Error in fallback COLOMBIA:", e)

if __name__ == "__main__":
    asyncio.run(test())
