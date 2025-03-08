"""
Limit order matching strategy.

This module implements the matching strategy for limit orders.
"""

from typing import Dict, List, Any

from ...event_manager import EventType
from .base import OrderMatchingStrategy
from .matching_utils import match_against_book


class LimitOrderStrategy(OrderMatchingStrategy):
    """
    Strategy for matching limit orders.
    
    Limit orders execute at the specified price or better, and any unfilled
    portion remains in the order book.
    """
    
    def process(self, order: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Process a limit order, matching it against the book if possible.
        
        Args:
            order: Limit order to process
            
        Returns:
            List of trade dictionaries resulting from the match
        """
        # Check if the order crosses the book
        trades = []
        side = order["side"].lower()
        price = order["price"]
        initial_quantity = order["quantity"]
        
        if self.is_crossed(order):
            # First match the order against the book
            trades = match_against_book(
                order=order,
                book_manager=self.book_manager,
                event_manager=self.event_manager,
                maker_fee_rate=self.maker_fee_rate,
                taker_fee_rate=self.taker_fee_rate
            )
            
            # If the order is fully matched, publish filled event
            if order["quantity"] <= 0:
                if self.event_manager:
                    self.event_manager.publish(EventType.ORDER_FILLED, {
                        "order_id": order["order_id"]
                    })
                return trades
        
        # Add remaining quantity to the book if not fully matched
        if order["quantity"] > 0:
            # Make a copy of the order for the book to avoid modifying the original
            book_order = order.copy()
            self.book_manager.add_order(book_order)
            
            # If this is a partially filled order, make sure the _orders dictionary is updated too
            if initial_quantity != order["quantity"] and order["order_id"] in self.book_manager._orders:
                self.book_manager._orders[order["order_id"]]["quantity"] = order["quantity"]
            
            # Publish event
            if self.event_manager:
                # If partially filled, publish a modified event
                if initial_quantity != order["quantity"]:
                    self.event_manager.publish(EventType.ORDER_MODIFIED, {
                        "order_id": order["order_id"],
                        "quantity": order["quantity"]
                    })
                
                # Always publish added event
                self.event_manager.publish(EventType.ORDER_ADDED, {
                    "order_id": order["order_id"],
                    "side": side,
                    "price": price,
                    "quantity": order["quantity"]
                })
        
        return trades 