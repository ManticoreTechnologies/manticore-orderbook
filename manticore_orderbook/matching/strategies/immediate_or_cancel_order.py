"""
Immediate-or-Cancel order matching strategy.

This module implements the matching strategy for immediate-or-cancel orders.
"""

from typing import Dict, List, Any

from ...event_manager import EventType
from .base import OrderMatchingStrategy
from .matching_utils import match_against_book


class ImmediateOrCancelOrderStrategy(OrderMatchingStrategy):
    """
    Strategy for matching immediate-or-cancel (IOC) orders.
    
    IOC orders execute immediately to the extent possible, and any unfilled
    portion is cancelled rather than being placed in the order book.
    """
    
    def process(self, order: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Process an immediate-or-cancel order.
        
        Args:
            order: IOC order dictionary
            
        Returns:
            List of trade dictionaries resulting from the match
        """
        trades = []
        
        # Check if the order crosses the book
        if self.is_crossed(order):
            # Match the order against the book
            trades = match_against_book(
                order=order,
                book_manager=self.book_manager,
                event_manager=self.event_manager,
                maker_fee_rate=self.maker_fee_rate,
                taker_fee_rate=self.taker_fee_rate
            )
            
            # Publish trade events
            if trades and self.event_manager:
                for trade in trades:
                    self.event_manager.publish(EventType.TRADE, trade)
            
            # Check if order was fully matched
            if self.is_fully_matched(order):
                if self.event_manager:
                    self.event_manager.publish(EventType.ORDER_FILLED, {
                        "order_id": order["order_id"]
                    })
            else:
                # For IOC orders, cancel any unfilled portion
                if self.event_manager:
                    self.event_manager.publish(EventType.ORDER_CANCELLED, {
                        "order_id": order["order_id"],
                        "reason": "IOC order partially filled and cancelled"
                    })
        else:
            # If the order doesn't cross the book, cancel it
            if self.event_manager:
                self.event_manager.publish(EventType.ORDER_CANCELLED, {
                    "order_id": order["order_id"],
                    "reason": "IOC order could not be filled"
                })
        
        return trades 