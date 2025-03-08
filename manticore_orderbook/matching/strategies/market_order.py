"""
Market order matching strategy.

This module implements the matching strategy for market orders.
"""

from typing import Dict, List, Any

from ...event_manager import EventType
from .base import OrderMatchingStrategy
from .matching_utils import match_against_book


class MarketOrderStrategy(OrderMatchingStrategy):
    """
    Strategy for matching market orders.
    
    Market orders execute immediately at the best available price, regardless of what that price is.
    Any unfilled portion of a market order is cancelled.
    """
    
    def process(self, order: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Process a market order, which must be executed immediately at the best available price.
        
        Args:
            order: Market order to process
            
        Returns:
            List of trade dictionaries resulting from the match
        """
        # For a market order, set price to ensure it crosses the book
        side = order["side"].lower()
        if side in ("buy", "bid"):
            # For a buy, set price extremely high to cross all asks
            best_ask = self.book_manager.get_best_ask()
            if best_ask:
                # Use a price that will definitely cross the book (max price)
                order["price"] = float('inf')
            else:
                # No asks to match against
                if self.event_manager:
                    self.event_manager.publish(EventType.ORDER_REJECTED, {
                        "order_id": order["order_id"],
                        "reason": "No asks available for market buy order"
                    })
                return []
        else:  # "sell" or "ask"
            # For a sell, set price extremely low to cross all bids
            best_bid = self.book_manager.get_best_bid()
            if best_bid:
                # Use a price that will definitely cross the book (min price)
                order["price"] = 0.0
            else:
                # No bids to match against
                if self.event_manager:
                    self.event_manager.publish(EventType.ORDER_REJECTED, {
                        "order_id": order["order_id"],
                        "reason": "No bids available for market sell order"
                    })
                return []
        
        # Match against the book - market orders don't get added to the book
        trades = match_against_book(
            order=order,
            book_manager=self.book_manager,
            event_manager=self.event_manager,
            maker_fee_rate=self.maker_fee_rate,
            taker_fee_rate=self.taker_fee_rate
        )
        
        # If the order wasn't completely filled, it's rejected (market orders must fill immediately)
        if order["quantity"] > 0:
            if self.event_manager:
                self.event_manager.publish(EventType.ORDER_REJECTED, {
                    "order_id": order["order_id"],
                    "reason": "Market order could not be completely filled"
                })
        else:
            # Order fully filled
            if self.event_manager:
                self.event_manager.publish(EventType.ORDER_FILLED, {
                    "order_id": order["order_id"]
                })
        
        return trades 