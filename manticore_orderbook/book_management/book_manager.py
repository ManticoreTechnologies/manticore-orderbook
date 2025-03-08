"""
Book management module for handling order book data structures.

This module contains the BookManager class that is responsible for managing the 
internal data structures that make up the order book, including:
- Adding and removing orders from the book
- Maintaining price levels
- Order cancellation
- Order modification
- Getting snapshots of the book
"""

import collections
import time
import logging
import bisect
from collections import defaultdict, deque
from typing import Dict, List, Optional, Tuple, Any, DefaultDict, Deque, Set
import uuid
import heapq

# Configure logging
logger = logging.getLogger("manticore_orderbook.book_management")

class BookManager:
    """
    Book Manager handles the internal data structures of the order book.
    
    It maintains the order storage, price levels, and provides operations
    to add, remove, and manipulate orders in the book.
    """
    
    def __init__(self, max_trade_history: int = 10000):
        """
        Initialize a new BookManager.
        
        Args:
            max_trade_history: Maximum number of trades to keep in history
        """
        # Initialize book data structures
        self._orders: Dict[str, Dict[str, Any]] = {}  # Map order_id -> order dict
        self._bids: List[float] = []  # List of bid prices (sorted in descending order)
        self._asks: List[float] = []  # List of ask prices (sorted in ascending order)
        self._bids_at_price: DefaultDict[float, Dict[str, Dict[str, Any]]] = defaultdict(dict)
        self._asks_at_price: DefaultDict[float, Dict[str, Dict[str, Any]]] = defaultdict(dict)
        
        # Track trades
        self._trade_history: Deque[Dict[str, Any]] = deque(maxlen=max_trade_history)
        
        # Statistics
        self._num_orders_added = 0
        self._num_orders_cancelled = 0
        self._num_orders_modified = 0
        self._num_trades = 0
        self._total_volume = 0.0
        
    def add_order(self, order: Dict[str, Any]) -> None:
        """
        Add a new order to the order book.
        
        Args:
            order: Dictionary containing order data
        """
        order_id = order.get("order_id") or str(uuid.uuid4())
        order["order_id"] = order_id
        side = order["side"].lower()
        
        # For iceberg orders, use displayed_quantity for the visible amount
        order_type_value = order.get("order_type")
        order_type = order_type_value.upper() if order_type_value is not None else "LIMIT"
        
        # Skip condition-based orders that haven't been triggered
        if order_type in ("STOP_LIMIT", "STOP_MARKET", "TRAILING_STOP") and not order.get("is_triggered", False):
            # Add to orders dictionary but don't place in the order book yet
            self._orders[order_id] = order
            return
            
        # Don't add market orders to the book (they should execute immediately)
        if order_type == "MARKET":
            self._orders[order_id] = order
            return
        
        # Clone the order for the book
        book_order = order.copy()
        
        # For iceberg orders, set the visible quantity
        if order_type == "ICEBERG" and "displayed_quantity" in order:
            book_order["quantity"] = min(order["displayed_quantity"], order["quantity"])
            # Keep track of the total remaining quantity
            book_order["reserve_quantity"] = order["quantity"] - book_order["quantity"]
        
        price = float(order["price"])
        
        # Add to price level dictionaries
        if side in ("buy", "bid"):
            if price not in self._bids_at_price:
                bisect.insort_left(self._bids, price)
                self._bids.sort(reverse=True)  # Keep bids in descending order
            self._bids_at_price[price][order_id] = book_order
        elif side in ("sell", "ask"):
            if price not in self._asks_at_price:
                bisect.insort_left(self._asks, price)
            self._asks_at_price[price][order_id] = book_order
        
        # Store the full order in the orders dictionary
        self._orders[order_id] = order
        
        self._num_orders_added += 1
    
    def remove_order(self, order_id: str) -> Optional[Dict[str, Any]]:
        """
        Remove an order from the book.
        
        Args:
            order_id: ID of order to remove
            
        Returns:
            Removed order dictionary or None if not found
        """
        if order_id not in self._orders:
            return None
            
        order = self._orders[order_id]
        price = order["price"]
        side = order["side"].lower()
        
        # Remove from orders dictionary
        del self._orders[order_id]
        
        # Remove from appropriate price level
        if side == "buy" or side == "bid":
            if price in self._bids_at_price:
                if order_id in self._bids_at_price[price]:
                    del self._bids_at_price[price][order_id]
                # Remove price level if empty
                if not self._bids_at_price[price]:
                    del self._bids_at_price[price]
                    self._bids.remove(price)
        else:  # side == "sell" or side == "ask"
            if price in self._asks_at_price:
                if order_id in self._asks_at_price[price]:
                    del self._asks_at_price[price][order_id]
                # Remove price level if empty
                if not self._asks_at_price[price]:
                    del self._asks_at_price[price]
                    self._asks.remove(price)
        
        return order
    
    def cancel_order(self, order_id: str) -> bool:
        """
        Cancel and remove an order from the book.
        
        Args:
            order_id: ID of order to cancel
            
        Returns:
            True if order was cancelled, False if not found
        """
        order = self.remove_order(order_id)
        if order:
            self._num_orders_cancelled += 1
            return True
        return False
    
    def modify_order(self, order_id: str, new_price: Optional[float] = None,
                    new_quantity: Optional[float] = None,
                    new_expiry_time: Optional[float] = None,
                    new_stop_price: Optional[float] = None,
                    new_trail_value: Optional[float] = None,
                    new_trail_is_percent: Optional[bool] = None,
                    new_displayed_quantity: Optional[float] = None) -> bool:
        """
        Modify an existing order.
        
        Args:
            order_id: ID of the order to modify
            new_price: New price (if None, keep current price)
            new_quantity: New quantity (if None, keep current quantity)
            new_expiry_time: New expiry time (if None, keep current expiry time)
            new_stop_price: New stop price for stop orders
            new_trail_value: New trail value for trailing stop orders
            new_trail_is_percent: New trail_is_percent setting for trailing stops
            new_displayed_quantity: New displayed quantity for iceberg orders
            
        Returns:
            True if order was modified, False if order not found
        """
        # Get original order
        if order_id not in self._orders:
            return False
            
        order = self._orders[order_id]
        side = order["side"].lower() if order.get("side") else "buy"
        old_price = order.get("price")
        
        # Handle potential None values before calling upper()
        order_type_str = order.get("order_type", "LIMIT")
        order_type = order_type_str.upper() if order_type_str is not None else "LIMIT"
        
        # Update the order
        if new_price is not None:
            order["price"] = float(new_price)
        
        if new_quantity is not None:
            order["quantity"] = float(new_quantity)
            
            # Update displayed_quantity for iceberg orders
            if order_type == "ICEBERG" and "displayed_quantity" in order:
                if new_displayed_quantity is not None:
                    order["displayed_quantity"] = float(new_displayed_quantity)
                else:
                    # Keep the same proportion
                    ratio = order["displayed_quantity"] / (order["quantity"] + order["reserve_quantity"])
                    order["displayed_quantity"] = order["quantity"] * ratio
        
        if new_expiry_time is not None:
            order["expiry_time"] = new_expiry_time
            
        if new_stop_price is not None and order_type in ("STOP_LIMIT", "STOP_MARKET"):
            order["stop_price"] = float(new_stop_price)
            
        if new_trail_value is not None and order_type == "TRAILING_STOP":
            order["trail_value"] = float(new_trail_value)
            
        if new_trail_is_percent is not None and order_type == "TRAILING_STOP":
            order["trail_is_percent"] = bool(new_trail_is_percent)
            
        if new_displayed_quantity is not None and order_type == "ICEBERG":
            order["displayed_quantity"] = float(new_displayed_quantity)
            # Calculate the reserve quantity
            total_quantity = order["quantity"]
            order["reserve_quantity"] = max(0.0, total_quantity - new_displayed_quantity)
        
        # If we're modifying a conditional order that hasn't been triggered yet,
        # just update the order dictionary and return
        if order_type in ("STOP_LIMIT", "STOP_MARKET", "TRAILING_STOP") and not order.get("is_triggered", False):
            self._orders[order_id] = order
            return True
        
        # If price changed, remove from old price level and add to new one
        new_price = order["price"]
        if old_price != new_price:
            # Remove from old price level
            if side in ("buy", "bid") and old_price in self._bids_at_price:
                if order_id in self._bids_at_price[old_price]:
                    del self._bids_at_price[old_price][order_id]
                    if not self._bids_at_price[old_price]:
                        del self._bids_at_price[old_price]
                        # Rebuild the heap
                        self._bids.remove(old_price)
                        self._bids.sort(reverse=True)
            elif side in ("sell", "ask") and old_price in self._asks_at_price:
                if order_id in self._asks_at_price[old_price]:
                    del self._asks_at_price[old_price][order_id]
                    if not self._asks_at_price[old_price]:
                        del self._asks_at_price[old_price]
                        # Rebuild the heap
                        self._asks.remove(old_price)
                        self._asks.sort()
            
            # Add to new price level
            if order_type != "MARKET":  # Market orders don't go in the book
                if side in ("buy", "bid"):
                    if new_price not in self._bids_at_price:
                        bisect.insort_left(self._bids, new_price)
                        self._bids.sort(reverse=True)
                    self._bids_at_price[new_price][order_id] = order
                elif side in ("sell", "ask"):
                    if new_price not in self._asks_at_price:
                        bisect.insort_left(self._asks, new_price)
                    self._asks_at_price[new_price][order_id] = order
        else:
            # Just update the order in place at the same price level
            if side in ("buy", "bid") and new_price in self._bids_at_price:
                self._bids_at_price[new_price][order_id] = order
            elif side in ("sell", "ask") and new_price in self._asks_at_price:
                self._asks_at_price[new_price][order_id] = order
        
        # Update the order in the orders dictionary
        self._orders[order_id] = order
        
        self._num_orders_modified += 1
        return True
    
    def get_order(self, order_id: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a specific order.
        
        Args:
            order_id: ID of order to retrieve
            
        Returns:
            Order dictionary if found, None otherwise
        """
        return self._orders.get(order_id)
    
    def get_best_bid(self) -> Optional[float]:
        """
        Get the best (highest) bid price.
        
        Returns:
            Best bid price or None if no bids
        """
        return self._bids[0] if self._bids else None
    
    def get_best_ask(self) -> Optional[float]:
        """
        Get the best (lowest) ask price.
        
        Returns:
            Best ask price or None if no asks
        """
        return self._asks[0] if self._asks else None
    
    def get_orders_at_price(self, side: str, price: float) -> Dict[str, Dict[str, Any]]:
        """
        Get all orders at a specific price level.
        
        Args:
            side: 'buy'/'bid' or 'sell'/'ask'
            price: Price level
            
        Returns:
            Dictionary mapping order IDs to order dictionaries
        """
        side = side.lower()
        if side == "buy" or side == "bid":
            return self._bids_at_price.get(price, {})
        else:  # side == "sell" or side == "ask"
            return self._asks_at_price.get(price, {})
    
    def get_snapshot(self, symbol: str, depth: int = 10) -> Dict[str, Any]:
        """
        Get a snapshot of the current order book.
        
        Args:
            symbol: Trading symbol for the snapshot
            depth: Number of price levels to include
            
        Returns:
            Dictionary containing order book snapshot in the format expected by tests
        """
        # Create snapshot dictionary
        snapshot = {
            "symbol": symbol,
            "timestamp": time.time(),
            "bids": [],
            "asks": []
        }
        
        # Add bid levels (highest first)
        for price in self._bids[:depth]:
            orders = self._bids_at_price[price]
            total_quantity = sum(order["quantity"] for order in orders.values())
            snapshot["bids"].append({
                "price": price,
                "quantity": total_quantity,
                "order_count": len(orders)
            })
        
        # Add ask levels (lowest first)
        for price in self._asks[:depth]:
            orders = self._asks_at_price[price]
            total_quantity = sum(order["quantity"] for order in orders.values())
            snapshot["asks"].append({
                "price": price,
                "quantity": total_quantity,
                "order_count": len(orders)
            })
        
        return snapshot
    
    def add_trade(self, trade: Dict[str, Any]) -> None:
        """
        Add a trade to the trade history.
        
        Args:
            trade: Trade dictionary
        """
        self._trade_history.append(trade)
        self._num_trades += 1
        self._total_volume += trade["quantity"]
    
    def get_trade_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get recent trades from the trade history.
        
        Args:
            limit: Maximum number of trades to return
            
        Returns:
            List of trade dictionaries, oldest first
        """
        trades = list(self._trade_history)
        # No need to reverse - return oldest first
        return trades[:limit]
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get order book statistics.
        
        Returns:
            Dictionary containing statistics about the order book
        """
        return {
            "num_orders_active": len(self._orders),
            "num_orders_added": self._num_orders_added,
            "num_orders_cancelled": self._num_orders_cancelled,
            "num_orders_modified": self._num_orders_modified,
            "num_trades": self._num_trades,
            "total_volume": self._total_volume,
            "num_bid_price_levels": len(self._bids),
            "num_ask_price_levels": len(self._asks),
            "spread": self.get_best_ask() - self.get_best_bid() if self._bids and self._asks else None
        }
    
    def clear(self) -> None:
        """
        Clear all orders and trades from the book.
        """
        self._orders.clear()
        self._bids.clear()
        self._asks.clear()
        self._bids_at_price.clear()
        self._asks_at_price.clear()
        self._trade_history.clear()
        # Reset statistics
        self._num_orders_added = 0
        self._num_orders_cancelled = 0
        self._num_orders_modified = 0
        self._num_trades = 0
        self._total_volume = 0.0
    
    def clear_trade_history(self) -> None:
        """
        Clear only the trade history.
        """
        self._trade_history.clear()
        self._num_trades = 0
        self._total_volume = 0.0
    
    def get_expired_orders(self, current_time: Optional[float] = None) -> List[str]:
        """
        Get list of expired order IDs.
        
        Args:
            current_time: Current time (if None, use current system time)
            
        Returns:
            List of expired order IDs
        """
        current_time = current_time or time.time()
        expired_order_ids = []
        
        for order_id, order in self._orders.items():
            expiry_time = order.get("expiry_time")
            if expiry_time is not None and current_time >= expiry_time:
                expired_order_ids.append(order_id)
                
        return expired_order_ids
    
    def get_bids(self, depth: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get the current bids in the order book.
        
        Args:
            depth: Maximum number of price levels to return (None for all)
            
        Returns:
            List of bid price levels with price and quantity
        """
        result = []
        
        # Get prices, limited by depth if specified
        prices = self._bids[:depth] if depth is not None else self._bids
        
        for price in prices:
            orders = self._bids_at_price.get(price, {})
            total_quantity = sum(order.get("quantity", 0) for order in orders.values())
            
            if total_quantity > 0:
                result.append({
                    "price": price,
                    "quantity": total_quantity,
                    "orderCount": len(orders)
                })
                
        return result
        
    def get_asks(self, depth: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get the current asks in the order book.
        
        Args:
            depth: Maximum number of price levels to return (None for all)
            
        Returns:
            List of ask price levels with price and quantity
        """
        result = []
        
        # Get prices, limited by depth if specified
        prices = self._asks[:depth] if depth is not None else self._asks
        
        for price in prices:
            orders = self._asks_at_price.get(price, {})
            total_quantity = sum(order.get("quantity", 0) for order in orders.values())
            
            if total_quantity > 0:
                result.append({
                    "price": price,
                    "quantity": total_quantity,
                    "orderCount": len(orders)
                })
                
        return result
        
    def get_last_price(self) -> Optional[float]:
        """
        Get the price of the most recent trade.
        
        Returns:
            The price of the last trade, or None if no trades have occurred
        """
        if not self._trade_history:
            return None
            
        return self._trade_history[-1].get("price")
        
    def get_order_count(self) -> int:
        """
        Get the total number of open orders in the book.
        
        Returns:
            Number of open orders
        """
        return len(self._orders)
        
    def get_trades(self) -> List[Dict[str, Any]]:
        """
        Get the trade history.
        
        Returns:
            List of trades from oldest to newest
        """
        return list(self._trade_history) 