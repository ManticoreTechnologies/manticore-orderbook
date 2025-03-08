"""
Good-Till-Date (GTD) order matching strategy.

This module implements the matching strategy for GTD orders, which are
basically limit orders that automatically expire at a specified time.
"""

import logging
from typing import Dict, List, Any, Optional

from .limit_order import LimitOrderStrategy
from ...event_manager import EventManager, EventType
from ...book_management.book_manager import BookManager

logger = logging.getLogger("manticore_orderbook.matching")

class GoodTillDateOrderStrategy(LimitOrderStrategy):
    """
    Good-Till-Date (GTD) order matching strategy.
    
    GTD orders are limit orders that automatically expire at a specified time.
    This strategy extends the LimitOrderStrategy and adds expiry time checking.
    """
    
    def __init__(self, book_manager: BookManager, event_manager: Optional[EventManager],
                 maker_fee_rate: float = 0.0, taker_fee_rate: float = 0.0):
        """
        Initialize a new GTD order matching strategy.
        
        Args:
            book_manager: BookManager instance to use
            event_manager: EventManager instance to use
            maker_fee_rate: Fee rate for makers (0.001 = 0.1%)
            taker_fee_rate: Fee rate for takers (0.001 = 0.1%)
        """
        super().__init__(book_manager, event_manager, maker_fee_rate, taker_fee_rate)
    
    def process(self, order: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Process a GTD order.
        
        This works the same as a limit order but requires an expiry time.
        
        Args:
            order: Order dictionary
            
        Returns:
            List of trade dictionaries resulting from the match
        """
        # Ensure an expiry time is set
        if "expiry_time" not in order:
            raise ValueError("GTD orders require an expiry_time")
        
        # Process as a regular limit order
        return super().process(order) 