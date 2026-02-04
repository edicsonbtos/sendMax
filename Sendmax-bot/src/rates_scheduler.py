import logging

logger = logging.getLogger("rates_scheduler")


class RatesScheduler:
    """
    Scheduler de tasas usando JobQueue de python-telegram-bot.
    Inicialmente: solo logs (stub seguro).
    Luego: Binance + DB + regla 3%.
    """

    def __init__(self, app):
        self.app = app

    async def run_9am_baseline(self) -> None:
        logger.info("[rates] 9am baseline job ejecutado (stub)")

    async def run_30m_check(self) -> None:
        logger.info("[rates] 30m check job ejecutado (stub)")