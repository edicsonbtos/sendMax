"""
Módulo para manejar overrides de precios manuales vs Binance P2P
"""
from __future__ import annotations

import logging
from decimal import Decimal
from typing import Optional, Tuple

from src.config.dynamic_settings import dynamic_config
from src.integrations.binance_p2p import BinanceP2PClient

logger = logging.getLogger(__name__)

# ============================================================================
# CONFIGURACIÓN DE OVERRIDES
# ============================================================================

MANUAL_PRICE_OVERRIDES = {
    # Key format: "COUNTRY|PAYMENT_METHOD"
    "USA|Zelle": "cash_delivery_rate",  # Usaremos dict access a admin_settings
}

# ============================================================================
# FUNCIONES PRINCIPALES
# ============================================================================

async def get_buy_price(
    country: str,
    payment_method: str,
    fallback_to_binance: bool = True
) -> Decimal:
    """
    Obtiene precio de compra con soporte para override manual.
    """
    manual_price = await _get_manual_price(country, payment_method)
    
    if manual_price:
        logger.info(
            f"💰 Using MANUAL price for {country}/{payment_method}: {manual_price}"
        )
        return manual_price
    
    if fallback_to_binance:
        logger.info(
            f"🌐 No manual price for {country}/{payment_method}, using Binance"
        )
        
        client = BinanceP2PClient()
        try:
            # Replicar la estructura de busqueda de binance de la app
            from src.integrations.p2p_config import COUNTRIES
            cfg = COUNTRIES.get(country)
            if not cfg:
                raise ValueError(f"Country {country} not configured in p2p_config")
                
            quote = await client.fetch_first_price(
                fiat=cfg.fiat,
                trade_type="BUY",
                pay_methods=[payment_method],
                trans_amount=cfg.trans_amount,
            )
            return Decimal(str(quote.price))
        except Exception as e:
            logger.error(f"❌ Error fetching from Binance: {e}")
            raise ValueError(f"No manual price and Binance failed for {country}/{payment_method}")
        finally:
            await client.close()
    else:
        raise ValueError(f"No manual price configured for {country}/{payment_method}")


async def _get_manual_price(country: str, payment_method: str) -> Optional[Decimal]:
    """
    Busca precio manual usando dynamic_settings para compatibilidad.
    """
    if country == "USA" and payment_method == "Zelle":
        try:
            cash_cfg = await dynamic_config.get_cash_delivery_config()
            val = cash_cfg.get("zelle_usdt_cost")
            if val:
                precio = Decimal(str(val))
                if precio > 0:
                    logger.info(f"✅ Found manual price in cash_delivery config: {precio}")
                    return precio
        except Exception as e:
            logger.warning(f"⚠️ Could not parse manual price for Zelle: {e}")
            
    # Generic extension (opcional)
    return None

async def get_sell_price(
    country: str,
    payment_method: str,
    apply_margin: bool = True
) -> Decimal:
    """
    Obtiene precio de venta. Sigue usando Binance por defecto para SELL.
    """
    client = BinanceP2PClient()
    try:
        from src.integrations.p2p_config import COUNTRIES
        cfg = COUNTRIES.get(country)
        if not cfg:
            raise ValueError(f"Country {country} not configured in p2p_config")
            
        quote = await client.fetch_first_price(
            fiat=cfg.fiat,
            trade_type="SELL",
            pay_methods=[payment_method],
            trans_amount=cfg.trans_amount,
        )
        return Decimal(str(quote.price))
        
    except Exception as e:
        logger.error(f"❌ Error fetching sell price from Binance: {e}")
        raise
    finally:
        await client.close()
