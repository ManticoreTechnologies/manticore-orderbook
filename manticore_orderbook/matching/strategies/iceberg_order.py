"""
Iceberg order matching strategy.

This module implements the matching strategy for iceberg orders.
"""

from typing import Dict, List, Any

from ...event_manager import EventType
from .base import OrderMatchingStrategy
from .matching_utils import match_against_book


class IcebergOrderStrategy(OrderMatchingStrategy):
    """
    Strategy for matching iceberg orders.
    
    Iceberg orders show only a portion of the total quantity to the market,
    while keeping the rest hidden. As the visible portion is filled, more
    of the order is revealed.
    """
    
    def process(self, order: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Process an iceberg order.
        
        Args:
            order: Iceberg order dictionary
            
        Returns:
            List of trade dictionaries resulting from the match
        """
        # Initialize iceberg order fields if not already set
        if "displayed_quantity" not in order:
            # Default to 10% of total quantity if not specified
            order["displayed_quantity"] = order["quantity"] * 0.1
        
        if "reserve_quantity" not in order:
            order["reserve_quantity"] = 0
        
        # If this is a new order or we've used up the visible quantity,
        # set up the visible quantity for matching
        total_quantity = order["quantity"] + order["reserve_quantity"]
        if order["quantity"] <= 0 and order["reserve_quantity"] > 0:
            # Move some quantity from reserve to visible
            visible_qty = min(order["displayed_quantity"], order["reserve_quantity"])
            order["quantity"] = visible_qty
            order["reserve_quantity"] -= visible_qty
        
        trades = []
        
        # Check if the order crosses the book
        if self.is_crossed(order):
            # Match the visible portion against the book
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
            
            # If visible portion is used up but we have reserve, refresh the visible quantity
            if order["quantity"] <= 0 and order["reserve_quantity"] > 0:
                # Move some quantity from reserve to visible
                visible_qty = min(order["displayed_quantity"], order["reserve_quantity"])
                order["quantity"] = visible_qty
                order["reserve_quantity"] -= visible_qty
            
            # Check if the entire order was filled
            if order["quantity"] <= 0 and order["reserve_quantity"] <= 0:
                if self.event_manager:
                    self.event_manager.publish(EventType.ORDER_FILLED, {
                        "order_id": order["order_id"]
                    })
                return trades
        
        # Add any remaining quantity to the book
        if order["quantity"] > 0 or order["reserve_quantity"] > 0:
            self.book_manager.add_order(order)
            
            if self.event_manager:
                self.event_manager.publish(EventType.ORDER_ADDED, {
                    "order_id": order["order_id"]
                })
        
        return trades 