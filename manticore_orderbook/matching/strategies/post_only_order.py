"""
Post-Only order matching strategy.

This module implements the matching strategy for post-only orders.
"""

from typing import Dict, List, Any

from ...event_manager import EventType
from .base import OrderMatchingStrategy


class PostOnlyOrderStrategy(OrderMatchingStrategy):
    """
    Strategy for matching post-only orders.
    
    Post-only orders are limit orders that are guaranteed to be the maker in a transaction.
    If the order would cross the book and take liquidity, it is rejected.
    """
    
    def process(self, order: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Process a post-only order.
        
        Args:
            order: Post-only order dictionary
            
        Returns:
            List of trade dictionaries resulting from the match
        """
        # Check if the order would cross the book
        if self.is_crossed(order):
            # If it would cross and take liquidity, reject it
            if self.event_manager:
                self.event_manager.publish(EventType.ORDER_REJECTED, {
                    "order_id": order["order_id"],
                    "reason": "POST_ONLY order would take liquidity"
                })
            return []
        
        # Add the order to the book
        self.book_manager.add_order(order)
        
        if self.event_manager:
            self.event_manager.publish(EventType.ORDER_ADDED, {
                "order_id": order["order_id"]
            })
        
        return [] 