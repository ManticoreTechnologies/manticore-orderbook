"""
Manticore OrderBook - High-performance order book management for trading systems
"""

from .orderbook import OrderBook
from .models import Order, Trade, TimeInForce, Side
from .market_manager import MarketManager

__all__ = ["OrderBook", "Order", "Trade", "TimeInForce", "Side", "MarketManager"]
__version__ = "0.3.0" 