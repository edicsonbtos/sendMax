from src.api.operators import router as operators_router
from src.api.ranking import router as ranking_router
from src.api.rates_live import router as rates_live_router

__all__ = [
    "operators_router",
    "ranking_router", 
    "rates_live_router",
]
