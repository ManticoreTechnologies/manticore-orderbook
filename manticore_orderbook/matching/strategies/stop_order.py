"""
Stop order matching strategy.

This module implements the matching strategy for stop orders (stop-limit and stop-market).
"""

from typing import Dict, List, Any

from ...event_manager import EventType
from .base import OrderMatchingStrategy


class StopOrderStrategy(OrderMatchingStrategy):
    """
    Strategy for matching stop orders.
    
    Stop orders are triggered when the market price reaches the stop price.
    Once triggered, they become either market orders (stop-market) or
    limit orders (stop-limit) and are processed accordingly.
    """
    
    def process(self, order: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Process a stop order.
        
        Args:
            order: Stop order dictionary
            
        Returns:
            List of trade dictionaries resulting from the match
        """
        # Check if the stop conditions are met
        is_triggered = self._check_stop_conditions(order)
        
        if is_triggered:
            # Convert to the appropriate order type
            if order.get("order_type", "").upper() == "STOP_MARKET":
                # Convert to market order
                order["order_type"] = "MARKET"
                order["is_triggered"] = True
                
                # Delegate to market order strategy
                from .market_order import MarketOrderStrategy
                market_strategy = MarketOrderStrategy(
                    book_manager=self.book_manager,
                    event_manager=self.event_manager,
                    maker_fee_rate=self.maker_fee_rate,
                    taker_fee_rate=self.taker_fee_rate
                )
                return market_strategy.process(order)
            else:  # STOP_LIMIT
                # Already has a limit price, just process as limit order
                order["order_type"] = "LIMIT"
                order["is_triggered"] = True
                
                # Delegate to limit order strategy
                from .limit_order import LimitOrderStrategy
                limit_strategy = LimitOrderStrategy(
                    book_manager=self.book_manager,
                    event_manager=self.event_manager,
                    maker_fee_rate=self.maker_fee_rate,
                    taker_fee_rate=self.taker_fee_rate
                )
                return limit_strategy.process(order)
        else:
            # Add to book but don't match yet (it will be triggered later)
            self.book_manager.add_order(order)
            
            if self.event_manager:
                self.event_manager.publish(EventType.ORDER_ADDED, {
                    "order_id": order["order_id"]
                })
            
            return []
    
    def _check_stop_conditions(self, order: Dict[str, Any]) -> bool:
        """
        Check if the stop conditions for an order are met.
        
        Args:
            order: Stop order dictionary
            
        Returns:
            True if the stop conditions are met, False otherwise
        """
        # If the order has already been triggered, return True
        if order.get("is_triggered", False):
            return True
            
        side = order["side"].lower()
        stop_price = order.get("stop_price")
        
        # If no stop price, can't be triggered
        if stop_price is None:
            return False
            
        # For buy stop orders, trigger when the best ask is at or below the stop price
        # For sell stop orders, trigger when the best bid is at or above the stop price
        if side in ("buy", "bid"):
            best_ask = self.book_manager.get_best_ask()
            return best_ask is not None and best_ask <= stop_price
        else:  # side in ("sell", "ask")
            best_bid = self.book_manager.get_best_bid()
            return best_bid is not None and best_bid >= stop_price 