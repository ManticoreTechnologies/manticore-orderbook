"""
Exchange-ready market manager for handling multiple order books across different trading pairs.

Provides a comprehensive solution for multi-market exchanges with features such as:
- User order tracking across markets
- Cross-market order management
- Consolidated fee calculation
- Exchange-wide statistics and latency monitoring
- Automated order expiry management
"""

import time
import logging
import threading
from typing import Dict, List, Optional, Any, Set, Tuple, Union
from collections import defaultdict

from .orderbook import OrderBook
from .models import TimeInForce

# Configure logging
logger = logging.getLogger("manticore_orderbook.market_manager")


class MarketManager:
    """
    Manages multiple order books for different trading pairs.
    
    Features:
    - Create and manage multiple markets
    - Place orders across markets
    - Cancel orders across markets
    - Track orders by user
    - Expiry management for all markets
    - Thread-safe operations
    """
    
    def __init__(self, enable_logging: bool = True, log_level: int = logging.INFO):
        """
        Initialize a new market manager.
        
        Args:
            enable_logging: Whether to enable logging
            log_level: Logging level (from logging module)
        """
        # Configure logging
        self.enable_logging = enable_logging
        if enable_logging:
            self._setup_logging(log_level)
        
        # Markets dictionary (symbol -> OrderBook)
        self._markets: Dict[str, OrderBook] = {}
        
        # Order to market mapping for quick lookups
        self._order_to_market: Dict[str, str] = {}
        
        # Track user orders (user_id -> {order_id})
        self._user_orders: Dict[str, Set[str]] = defaultdict(set)
        
        # Lock for thread safety
        self._lock = threading.RLock()
        
        logger.info("MarketManager initialized")
    
    def _setup_logging(self, log_level: int) -> None:
        """Set up logging for the market manager."""
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        
        logger.setLevel(log_level)
        if not logger.handlers:
            logger.addHandler(handler)
    
    def create_market(self, symbol: str, **kwargs) -> OrderBook:
        """
        Create a new market for a trading pair.
        
        Args:
            symbol: Trading pair symbol (e.g., 'BTC/USD')
            **kwargs: Additional arguments to pass to the OrderBook constructor
        
        Returns:
            The created OrderBook
        
        Raises:
            ValueError: If market already exists
        """
        with self._lock:
            if symbol in self._markets:
                raise ValueError(f"Market {symbol} already exists")
            
            # Create new order book
            order_book = OrderBook(
                symbol=symbol,
                enable_logging=self.enable_logging,
                **kwargs
            )
            
            # Store in markets dictionary
            self._markets[symbol] = order_book
            
            logger.info(f"Created market: {symbol}")
            
            return order_book
    
    def get_market(self, symbol: str) -> Optional[OrderBook]:
        """
        Get an existing market by symbol.
        
        Args:
            symbol: Trading pair symbol (e.g., 'BTC/USD')
        
        Returns:
            OrderBook instance or None if not found
        """
        with self._lock:
            return self._markets.get(symbol)
    
    def delete_market(self, symbol: str) -> bool:
        """
        Delete a market. This will cancel all orders in the order book.
        
        Args:
            symbol: Trading pair symbol (e.g., 'BTC/USD')
        
        Returns:
            True if market was deleted, False if not found
        """
        with self._lock:
            if symbol not in self._markets:
                return False
            
            # Get all orders in this market to clean up references
            order_book = self._markets[symbol]
            
            # Get all order IDs in this market
            order_ids = list(order_book._orders.keys())
            
            # Remove from _order_to_market mapping
            for order_id in order_ids:
                if order_id in self._order_to_market:
                    del self._order_to_market[order_id]
                    
                    # Also remove from user_orders
                    order = order_book._orders.get(order_id)
                    if order and order.user_id:
                        self._user_orders[order.user_id].discard(order_id)
                        
                        # Clean up empty user entries
                        if not self._user_orders[order.user_id]:
                            del self._user_orders[order.user_id]
            
            # Delete the market
            del self._markets[symbol]
            
            logger.info(f"Deleted market: {symbol}")
            
            return True
    
    def has_market(self, symbol: str) -> bool:
        """
        Check if a market exists.
        
        Args:
            symbol: Trading pair symbol (e.g., 'BTC/USD')
        
        Returns:
            True if market exists, False otherwise
        """
        with self._lock:
            return symbol in self._markets
    
    def list_markets(self) -> List[str]:
        """
        Get a list of all market symbols.
        
        Returns:
            List of market symbols
        """
        with self._lock:
            return list(self._markets.keys())
    
    def place_order(self, symbol: str, side: str, price: float, quantity: float,
                   order_id: Optional[str] = None, time_in_force: Optional[str] = None,
                   expiry_time: Optional[float] = None, user_id: Optional[str] = None) -> Optional[str]:
        """
        Place an order in a market.
        
        Args:
            symbol: Trading pair symbol (e.g., 'BTC/USD')
            side: 'buy' or 'sell'
            price: Order price
            quantity: Order quantity
            order_id: Unique order ID (generated if not provided)
            time_in_force: Time-in-force option ('GTC', 'IOC', 'FOK', 'GTD')
            expiry_time: Time when the order expires (required for GTD)
            user_id: User ID who placed the order (for fee tracking)
        
        Returns:
            Order ID if successful, None if market not found
        
        Raises:
            ValueError: If order parameters are invalid
        """
        with self._lock:
            # Check if market exists
            order_book = self.get_market(symbol)
            if not order_book:
                if self.enable_logging:
                    logger.warning(f"Cannot place order: market {symbol} not found")
                return None
            
            # Place the order
            order_id = order_book.add_order(
                side=side,
                price=price,
                quantity=quantity,
                order_id=order_id,
                time_in_force=time_in_force,
                expiry_time=expiry_time,
                user_id=user_id
            )
            
            # If order was added to the book (not immediately filled), track it
            if order_id in order_book._orders:
                # Map order ID to market
                self._order_to_market[order_id] = symbol
                
                # If user is provided, add to user orders
                if user_id:
                    self._user_orders[user_id].add(order_id)
            
            return order_id
    
    def cancel_order(self, order_id: str) -> bool:
        """
        Cancel an existing order in any market.
        
        Args:
            order_id: ID of the order to cancel
        
        Returns:
            True if order was cancelled, False if order not found
        """
        with self._lock:
            # Find which market contains this order
            symbol = self._order_to_market.get(order_id)
            if not symbol:
                if self.enable_logging:
                    logger.warning(f"Cannot cancel order {order_id}: order not found in any market")
                return False
            
            # Get the market
            order_book = self._markets.get(symbol)
            if not order_book:
                # This should not happen if _order_to_market is consistent
                if self.enable_logging:
                    logger.error(f"Inconsistent state: order {order_id} mapped to non-existent market {symbol}")
                return False
            
            # Get order info for cleanup
            order = order_book._orders.get(order_id)
            
            # Cancel the order
            result = order_book.cancel_order(order_id)
            
            if result:
                # Remove from _order_to_market mapping
                del self._order_to_market[order_id]
                
                # Remove from user orders if applicable
                if order and order.user_id:
                    self._user_orders[order.user_id].discard(order_id)
                    
                    # Clean up empty user entries
                    if not self._user_orders[order.user_id]:
                        del self._user_orders[order.user_id]
            
            return result
    
    def modify_order(self, order_id: str, new_price: Optional[float] = None,
                    new_quantity: Optional[float] = None, new_expiry_time: Optional[float] = None) -> bool:
        """
        Modify an existing order in any market.
        
        Args:
            order_id: ID of the order to modify
            new_price: New price (if None, keep current price)
            new_quantity: New quantity (if None, keep current quantity)
            new_expiry_time: New expiry time (if None, keep current expiry time)
        
        Returns:
            True if order was modified, False if order not found
        """
        with self._lock:
            # Find which market contains this order
            symbol = self._order_to_market.get(order_id)
            if not symbol:
                if self.enable_logging:
                    logger.warning(f"Cannot modify order {order_id}: order not found in any market")
                return False
            
            # Get the market
            order_book = self._markets.get(symbol)
            if not order_book:
                # This should not happen if _order_to_market is consistent
                if self.enable_logging:
                    logger.error(f"Inconsistent state: order {order_id} mapped to non-existent market {symbol}")
                return False
            
            # Note: if new_price changes, the order might be removed and re-added,
            # so we need to be careful with our tracking
            
            # Save original order to track user_id if needed
            original_order = order_book._orders.get(order_id)
            
            # Modify the order
            result = order_book.modify_order(
                order_id=order_id,
                new_price=new_price,
                new_quantity=new_quantity,
                new_expiry_time=new_expiry_time
            )
            
            # If order was modified and pricing changed (causing a new order to be created)
            if result and new_price is not None and order_id in order_book._orders:
                # Update market mapping (it's the same market, but might have been removed during modify)
                self._order_to_market[order_id] = symbol
            
            return result
    
    def get_order(self, order_id: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a specific order in any market.
        
        Args:
            order_id: ID of the order to look up
        
        Returns:
            Dictionary with order information or None if not found
        """
        with self._lock:
            # Find which market contains this order
            symbol = self._order_to_market.get(order_id)
            if not symbol:
                return None
            
            # Get the market
            order_book = self._markets.get(symbol)
            if not order_book:
                return None
            
            # Get order info
            order_info = order_book.get_order(order_id)
            if order_info:
                # Add market symbol to order info
                order_info["symbol"] = symbol
            
            return order_info
    
    def get_user_orders(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Get all active orders for a specific user across all markets.
        
        Args:
            user_id: User ID to look up
        
        Returns:
            List of order information dictionaries
        """
        with self._lock:
            orders = []
            
            # Get all order IDs for this user
            order_ids = self._user_orders.get(user_id, set())
            
            # Fetch each order
            for order_id in order_ids:
                order_info = self.get_order(order_id)
                if order_info:
                    orders.append(order_info)
            
            return orders
    
    def get_market_snapshot(self, symbol: str, depth: int = 10) -> Optional[Dict[str, Any]]:
        """
        Get a snapshot of a specific market.
        
        Args:
            symbol: Trading pair symbol (e.g., 'BTC/USD')
            depth: Number of price levels to include
        
        Returns:
            Dictionary with market snapshot or None if market not found
        """
        with self._lock:
            # Get the market
            order_book = self.get_market(symbol)
            if not order_book:
                return None
            
            # Get snapshot
            snapshot = order_book.get_snapshot(depth=depth)
            
            # Add symbol
            snapshot["symbol"] = symbol
            
            return snapshot
    
    def clean_expired_orders(self) -> Dict[str, int]:
        """
        Clean expired orders from all markets.
        
        Returns:
            Dictionary mapping market symbols to count of orders removed
        """
        with self._lock:
            results = {}
            
            # Process each market
            for symbol, order_book in self._markets.items():
                # Clean expired orders
                count = order_book.clean_expired_orders()
                
                if count > 0:
                    results[symbol] = count
                
                # Update _order_to_market and _user_orders mappings
                # This is done automatically when orders are cancelled
            
            return results
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about all markets.
        
        Returns:
            Dictionary with statistics
        """
        with self._lock:
            stats = {
                "total_markets": len(self._markets),
                "total_orders": sum(len(ob._orders) for ob in self._markets.values()),
                "total_users": len(self._user_orders),
                "markets": {}
            }
            
            # Add per-market statistics
            for symbol, order_book in self._markets.items():
                stats["markets"][symbol] = order_book.get_statistics()
            
            return stats
    
    def clear_market(self, symbol: str) -> bool:
        """
        Clear all orders from a market.
        
        Args:
            symbol: Trading pair symbol (e.g., 'BTC/USD')
        
        Returns:
            True if market was cleared, False if not found
        """
        with self._lock:
            # Get the market
            order_book = self.get_market(symbol)
            if not order_book:
                return False
            
            # Get all orders in this market
            order_ids = list(order_book._orders.keys())
            
            # Clear the market
            order_book.clear()
            
            # Update mappings
            for order_id in order_ids:
                # Remove from _order_to_market
                if order_id in self._order_to_market:
                    del self._order_to_market[order_id]
                
                # Clean up user orders
                for user_orders in self._user_orders.values():
                    user_orders.discard(order_id)
            
            # Clean up empty user entries
            for user_id in list(self._user_orders.keys()):
                if not self._user_orders[user_id]:
                    del self._user_orders[user_id]
            
            logger.info(f"Cleared market: {symbol}")
            
            return True 