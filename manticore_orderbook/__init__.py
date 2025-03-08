"""
Manticore OrderBook - A high-performance order book implementation for cryptocurrency exchanges.

This module provides a fast, efficient order book implementation with features designed
for integration with other systems like storage and matching engines.

Main Components:
- OrderBook: Core order book implementation with price-time priority matching
- EventManager: Pub/sub event system for order book events
- Models: Data structures for orders and trades

Copyright (c) 2023 Manticore Technologies
Website: https://manticore.technology
Contact: dev@manticore.technology
GitHub: https://github.com/manticoretechnologies/
"""

__version__ = "1.0.1"

# Core components
from .core.orderbook import OrderBook
from .models import Order, Trade, Side, TimeInForce, OrderType
from .event_manager import EventManager, EventType

# Also expose utility components for advanced usage
from .book_management.book_manager import BookManager
from .matching.matcher import OrderMatcher
from .utils.metrics import LatencyRecorder, PerformanceStats
from .utils.expiry import ExpiryManager

# Define public API
__all__ = [
    # Core components
    "OrderBook",
    "Order",
    "Trade", 
    "Side",
    "TimeInForce",
    "EventManager",
    "EventType",
    
    # Advanced usage components
    "BookManager",
    "OrderMatcher",
    "LatencyRecorder",
    "PerformanceStats",
    "ExpiryManager"
] 