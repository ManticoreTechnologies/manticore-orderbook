"""
Base strategy class for order matching.

This module defines the base strategy interface that all order matching strategies must implement.
"""

import abc
from typing import Dict, List, Any, Optional

from ...book_management.book_manager import BookManager
from ...event_manager import EventManager


class OrderMatchingStrategy(abc.ABC):
    """
    Abstract base class for all order matching strategies.
    
    Each concrete strategy implements the matching logic for a specific order type.
    """
    
    def __init__(self, book_manager: BookManager, event_manager: Optional[EventManager],
                 maker_fee_rate: float = 0.0, taker_fee_rate: float = 0.0):
        """
        Initialize a new order matching strategy.
        
        Args:
            book_manager: BookManager instance to use
            event_manager: EventManager instance to use
            maker_fee_rate: Fee rate for makers (0.001 = 0.1%)
            taker_fee_rate: Fee rate for takers (0.001 = 0.1%)
        """
        self.book_manager = book_manager
        self.event_manager = event_manager
        self.maker_fee_rate = maker_fee_rate
        self.taker_fee_rate = taker_fee_rate
    
    @abc.abstractmethod
    def process(self, order: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Process an order according to this strategy.
        
        Args:
            order: Order dictionary
            
        Returns:
            List of trade dictionaries resulting from the match
        """
        pass
    
    def is_fully_matched(self, order: Dict[str, Any]) -> bool:
        """
        Check if an order is fully matched.
        
        Args:
            order: Order dictionary
            
        Returns:
            True if the order is fully matched, False otherwise
        """
        return order["quantity"] <= 0
    
    def can_match_with_price(self, order: Dict[str, Any], price: float) -> bool:
        """
        Check if an order can match with a given price.
        
        Args:
            order: Order dictionary
            price: Price to check against
            
        Returns:
            True if the order can match with the given price, False otherwise
        """
        side = order["side"].lower()
        order_price = order.get("price")
        
        # Market orders can match with any price
        if order_price is None:
            return True
            
        if side in ("buy", "bid"):
            return order_price >= price
        else:  # side in ("sell", "ask")
            return order_price <= price
    
    def is_crossed(self, order: Dict[str, Any]) -> bool:
        """
        Check if an order is crossed with the current book.
        
        Args:
            order: Order dictionary
            
        Returns:
            True if the order is crossed with the book, False otherwise
        """
        side = order["side"].lower()
        
        if side in ("buy", "bid"):
            best_ask = self.book_manager.get_best_ask()
            if best_ask is None:
                return False
            return self.can_match_with_price(order, best_ask)
        else:  # side in ("sell", "ask")
            best_bid = self.book_manager.get_best_bid()
            if best_bid is None:
                return False
            return self.can_match_with_price(order, best_bid) 