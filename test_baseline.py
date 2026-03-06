import asyncio
from decimal import Decimal
import os
import sys

# Add src to pythonpath
sys.path.insert(0, os.path.abspath('.'))

from src.rates_scheduler import RatesScheduler

class MockApp:
    class MockBot:
        pass
    bot = MockBot()

async def test():
    print("Forzando recálculo de tasas 9am_baseline...")
    scheduler = RatesScheduler(MockApp())
    await scheduler.run_9am_baseline()
    print("Recálculo disparado.")

if __name__ == "__main__":
    asyncio.run(test())
