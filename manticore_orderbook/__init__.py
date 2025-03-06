"""
Manticore OrderBook - A high-performance order book implementation for cryptocurrency exchanges.

This module provides a fast, efficient order book implementation with features designed
for integration with other systems like storage and matching engines.

Main Components:
- OrderBook: Core order book implementation with price-time priority matching
- EventManager: Pub/sub event system for order book events
- Models: Data structures for orders and trades
"""

__version__ = "1.0.0"

# Core components
from .orderbook import OrderBook
from .models import Order, Trade, Side, TimeInForce
from .event_manager import EventManager, EventType

# Define public API
__all__ = [
    "OrderBook",
    "Order",
    "Trade", 
    "Side",
    "TimeInForce",
    "EventManager",
    "EventType"
] 