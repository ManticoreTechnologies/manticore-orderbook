"""
Matching engine for the Manticore OrderBook.

This module provides the order matching functionality, implementing price-time priority, and handling order executions.
"""

from .matcher import OrderMatcher
from .strategies import (
    OrderMatchingStrategy,
    LimitOrderStrategy,
    MarketOrderStrategy,
    FillOrKillOrderStrategy,
    ImmediateOrCancelOrderStrategy,
    StopOrderStrategy,
    PostOnlyOrderStrategy,
    IcebergOrderStrategy
)

__all__ = [
    'OrderMatcher',
    'OrderMatchingStrategy',
    'LimitOrderStrategy',
    'MarketOrderStrategy',
    'FillOrKillOrderStrategy',
    'ImmediateOrCancelOrderStrategy',
    'StopOrderStrategy',
    'PostOnlyOrderStrategy',
    'IcebergOrderStrategy'
] 