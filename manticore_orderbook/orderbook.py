"""
Exchange-ready OrderBook implementation with price-time priority, efficient matching,
and comprehensive features for production trading systems.

Supports Time-In-Force policies (GTC, IOC, FOK, GTD), order expiry management,
fee calculation, latency monitoring, and atomic operations.
"""

import bisect
import collections
import time
import logging
import threading
import copy
import statistics
from collections import defaultdict, deque
from typing import Dict, List, Optional, Tuple, Any, DefaultDict, Deque, Set, Union, Callable

from .models import Order, Trade, Side, TimeInForce

# Configure logging
logger = logging.getLogger("manticore_orderbook")


class OrderBook:
    """
    High-performance order book implementation with price-time priority.
    
    Features:
    - Fast order insertions, modifications, and cancellations
    - Automatic order matching
    - Order book snapshots
    - Trade history tracking
    - Batch order insertions
    - Atomic order modifications
    - Price improvement matching
    - Order expiry & Time-In-Force support
    - Performance monitoring
    - Detailed logging
    """
    
    def __init__(self, symbol: str, max_trade_history: int = 10000,
                 enable_price_improvement: bool = False,
                 maker_fee_rate: float = 0.0, taker_fee_rate: float = 0.0,
                 enable_logging: bool = True, log_level: int = logging.INFO,
                 check_expiry_interval: float = 1.0):
        """
        Initialize a new order book.
        
        Args:
            symbol: Trading pair symbol (e.g., 'BTC/USD')
            max_trade_history: Maximum number of trades to keep in history
            enable_price_improvement: Whether to enable price improvement matching
            maker_fee_rate: Fee rate for maker orders (e.g., 0.001 for 0.1%)
            taker_fee_rate: Fee rate for taker orders (e.g., 0.002 for 0.2%)
            enable_logging: Whether to enable logging
            log_level: Logging level (from logging module)
            check_expiry_interval: How often to check for expired orders (in seconds)
        """
        self.symbol = symbol
        self.max_trade_history = max_trade_history
        self.enable_price_improvement = enable_price_improvement
        self.maker_fee_rate = maker_fee_rate
        self.taker_fee_rate = taker_fee_rate
        self.check_expiry_interval = check_expiry_interval
        
        # Configure logging
        self.enable_logging = enable_logging
        if enable_logging:
            self._setup_logging(log_level)
        
        # Price levels (sorted for efficient traversal)
        self._bids: List[float] = []  # Descending order for bids
        self._asks: List[float] = []  # Ascending order for asks
        
        # Orders at each price level (price -> {order_id -> order})
        self._bid_orders: DefaultDict[float, Dict[str, Order]] = defaultdict(dict)
        self._ask_orders: DefaultDict[float, Dict[str, Order]] = defaultdict(dict)
        
        # Order lookup by ID (for quick access)
        self._orders: Dict[str, Order] = {}
        
        # Priority queue for order timestamp at each price level (for FIFO execution)
        self._bid_timestamps: DefaultDict[float, List[Tuple[float, str]]] = defaultdict(list)
        self._ask_timestamps: DefaultDict[float, List[Tuple[float, str]]] = defaultdict(list)
        
        # Trade history
        self._trade_history: Deque[Trade] = deque(maxlen=max_trade_history)
        
        # Track deleted price levels to manage _bids and _asks lists
        self._deleted_price_levels: Set[float] = set()
        
        # Lock for thread safety in critical operations
        self._lock = threading.RLock()
        
        # Cache for quick depth queries
        self._bid_depth_cache: List[Dict[str, Any]] = []
        self._ask_depth_cache: List[Dict[str, Any]] = []
        self._cache_valid = False
        
        # Statistics for monitoring
        self._stats = {
            "num_orders_added": 0,
            "num_orders_modified": 0,
            "num_orders_cancelled": 0,
            "num_trades_executed": 0,
            "total_volume_traded": 0.0
        }
        
        # Performance monitoring
        self._latency_metrics = {
            "add_order": [],
            "batch_add_orders": [],
            "modify_order": [],
            "cancel_order": [],
            "match_order": [],
            "get_snapshot": [],
            "clean_expired_orders": []
        }
        self._max_metrics = 1000  # Maximum number of latency metrics to keep
        
        # Start periodic checks for expired orders
        self._start_expiry_checker()
        
        logger.info(f"OrderBook initialized for {symbol} with price improvement {'enabled' if enable_price_improvement else 'disabled'}")
    
    def _setup_logging(self, log_level: int) -> None:
        """Set up logging for the order book."""
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        
        logger.setLevel(log_level)
        if not logger.handlers:
            logger.addHandler(handler)
    
    def _start_expiry_checker(self):
        """Start a background thread to check for expired orders periodically."""
        if self.check_expiry_interval <= 0:
            return  # Disable expiry checking if interval is invalid
            
        def check_expired_orders():
            while True:
                time.sleep(self.check_expiry_interval)
                try:
                    self.clean_expired_orders()
                except Exception as e:
                    if self.enable_logging:
                        logger.error(f"Error in expired orders check: {str(e)}")
        
        thread = threading.Thread(target=check_expired_orders, daemon=True)
        thread.start()
    
    def clean_expired_orders(self) -> int:
        """
        Remove all expired orders from the order book.
        
        Returns:
            Number of orders removed
        """
        start_time = time.time()
        removed_count = 0
        
        try:
            with self._lock:
                current_time = time.time()
                expired_orders = []
                
                # Find all expired orders
                for order_id, order in list(self._orders.items()):
                    if order.time_in_force == TimeInForce.GTD and order.is_expired(current_time):
                        expired_orders.append(order_id)
                
                # Cancel each expired order
                for order_id in expired_orders:
                    if self.cancel_order(order_id):
                        removed_count += 1
                        if self.enable_logging:
                            logger.info(f"Removed expired order: {order_id}")
                
                if removed_count > 0 and self.enable_logging:
                    logger.info(f"Cleaned {removed_count} expired orders")
                
                return removed_count
        finally:
            # Record latency
            elapsed = time.time() - start_time
            self._record_latency("clean_expired_orders", elapsed)
    
    def _record_latency(self, operation: str, latency: float) -> None:
        """Record operation latency for performance monitoring."""
        if operation in self._latency_metrics:
            metrics = self._latency_metrics[operation]
            metrics.append(latency)
            # Keep list size bounded
            if len(metrics) > self._max_metrics:
                metrics.pop(0)
    
    def get_latency_stats(self) -> Dict[str, Dict[str, float]]:
        """
        Get latency statistics for all operations.
        
        Returns:
            Dictionary with operation names mapped to latency statistics
        """
        stats = {}
        
        for op, metrics in self._latency_metrics.items():
            if not metrics:
                stats[op] = {"count": 0}
                continue
                
            stats[op] = {
                "count": len(metrics),
                "min": min(metrics),
                "max": max(metrics),
                "mean": statistics.mean(metrics),
                "p50": statistics.median(metrics),
            }
            
            # Only calculate percentiles if we have enough data
            if len(metrics) >= 10:
                sorted_metrics = sorted(metrics)
                idx_90 = int(len(sorted_metrics) * 0.9)
                idx_99 = int(len(sorted_metrics) * 0.99)
                stats[op]["p90"] = sorted_metrics[idx_90]
                stats[op]["p99"] = sorted_metrics[idx_99]
        
        return stats
    
    def add_order(self, side: str, price: float, quantity: float, order_id: Optional[str] = None,
                 time_in_force: Optional[str] = None, expiry_time: Optional[float] = None,
                 user_id: Optional[str] = None) -> str:
        """
        Add a new limit order to the order book.
        
        Args:
            side: 'buy' or 'sell'
            price: Order price
            quantity: Order quantity
            order_id: Unique order ID (generated if not provided)
            time_in_force: Time-in-force option ('GTC', 'IOC', 'FOK', 'GTD')
            expiry_time: Time when the order expires (required for GTD)
            user_id: User ID who placed the order (for fee tracking)
            
        Returns:
            The order ID
        """
        start_time = time.time()
        
        try:
            with self._lock:
                # Create the order
                order = Order(
                    side=side, 
                    price=price, 
                    quantity=quantity, 
                    order_id=order_id,
                    time_in_force=time_in_force,
                    expiry_time=expiry_time,
                    user_id=user_id
                )
                
                if self.enable_logging:
                    logger.info(f"Adding order: {order.order_id} ({side}) {quantity} @ {price} "
                               f"[TIF: {order.time_in_force.name}]")
                
                # Try to match the order immediately
                trades = self._match_order(order)
                
                # Handle FOK orders - must be fully filled or cancelled
                if order.time_in_force == TimeInForce.FOK and order.quantity > 0:
                    if self.enable_logging:
                        logger.info(f"FOK order {order.order_id} not fully matched, cancelling")
                    return order.order_id
                
                # Handle IOC orders - partial fills allowed, but don't add to book
                if order.time_in_force == TimeInForce.IOC:
                    if self.enable_logging and order.quantity > 0:
                        logger.info(f"IOC order {order.order_id} partially matched, not adding to book")
                    return order.order_id
                
                # If order is fully matched, return the ID without adding to book
                if order.quantity <= 0:
                    if self.enable_logging:
                        logger.info(f"Order {order.order_id} fully matched immediately")
                    return order.order_id
                
                # Add remaining order to the book
                self._add_to_book(order)
                
                # Update statistics
                self._stats["num_orders_added"] += 1
                
                # Invalidate cache
                self._cache_valid = False
                
                return order.order_id
        finally:
            # Record latency
            elapsed = time.time() - start_time
            self._record_latency("add_order", elapsed)
    
    def batch_add_orders(self, orders: List[Dict[str, Any]]) -> List[str]:
        """
        Add multiple orders to the order book in a single batch operation.
        
        Args:
            orders: List of order specifications, each containing:
                   'side', 'price', 'quantity', and optionally 'order_id',
                   'time_in_force', 'expiry_time', 'user_id'
        
        Returns:
            List of order IDs in the same order as the input
        """
        start_time = time.time()
        
        try:
            order_ids = []
            
            with self._lock:
                if self.enable_logging:
                    logger.info(f"Processing batch of {len(orders)} orders")
                
                # First pass: Create all Order objects
                order_objects = []
                for order_spec in orders:
                    order = Order(
                        side=order_spec["side"],
                        price=order_spec["price"],
                        quantity=order_spec["quantity"],
                        order_id=order_spec.get("order_id"),
                        time_in_force=order_spec.get("time_in_force"),
                        expiry_time=order_spec.get("expiry_time"),
                        user_id=order_spec.get("user_id")
                    )
                    order_objects.append(order)
                    order_ids.append(order.order_id)
                
                # Second pass: Match all orders against the book (without adding them yet)
                # This prevents earlier orders in the batch from matching with later ones
                remaining_orders = []
                for order in order_objects:
                    trades = self._match_order(order)
                    
                    # Handle FOK orders - must be fully filled or cancelled
                    if order.time_in_force == TimeInForce.FOK and order.quantity > 0:
                        continue  # Skip adding to book
                    
                    # Handle IOC orders - partial fills allowed, but don't add to book
                    if order.time_in_force == TimeInForce.IOC:
                        continue  # Skip adding to book
                    
                    if order.quantity > 0:
                        remaining_orders.append(order)
                
                # Third pass: Add all remaining orders to the book
                for order in remaining_orders:
                    self._add_to_book(order)
                
                # Update statistics
                self._stats["num_orders_added"] += len(orders)
                
                # Invalidate cache
                self._cache_valid = False
                
                if self.enable_logging:
                    logger.info(f"Batch processing complete: {len(orders) - len(remaining_orders)} orders matched, {len(remaining_orders)} orders added to book")
                
                return order_ids
        finally:
            # Record latency
            elapsed = time.time() - start_time
            self._record_latency("batch_add_orders", elapsed)
    
    def modify_order(self, order_id: str, new_price: Optional[float] = None, 
                     new_quantity: Optional[float] = None,
                     new_expiry_time: Optional[float] = None) -> bool:
        """
        Modify an existing order's price, quantity, and/or expiry time.
        
        Args:
            order_id: ID of the order to modify
            new_price: New price (if None, keep current price)
            new_quantity: New quantity (if None, keep current quantity)
            new_expiry_time: New expiry time (if None, keep current expiry time)
            
        Returns:
            True if order was modified, False if order not found
        """
        start_time = time.time()
        
        try:
            with self._lock:
                if order_id not in self._orders:
                    if self.enable_logging:
                        logger.warning(f"Cannot modify order {order_id}: order not found")
                    return False
                
                # Save original order state for atomic rollback
                original_order = copy.deepcopy(self._orders[order_id])
                
                try:
                    # Get original order
                    order = self._orders[order_id]
                    old_price = order.price
                    
                    if self.enable_logging:
                        logger.info(f"Modifying order {order_id}: price={old_price}->{new_price if new_price is not None else old_price}, "
                                  f"quantity={order.quantity}->{new_quantity if new_quantity is not None else order.quantity}, "
                                  f"expiry={order.expiry_time}->{new_expiry_time if new_expiry_time is not None else order.expiry_time}")
                    
                    # If price changed, treat as cancel and insert
                    if new_price is not None and new_price != old_price:
                        self.cancel_order(order_id)
                        # Create a new order with updated price and/or quantity
                        updated_quantity = new_quantity if new_quantity is not None else order.quantity
                        updated_expiry = new_expiry_time if new_expiry_time is not None else order.expiry_time
                        self.add_order(
                            side=str(order.side),
                            price=new_price,
                            quantity=updated_quantity,
                            order_id=order_id,
                            time_in_force=str(order.time_in_force),
                            expiry_time=updated_expiry,
                            user_id=order.user_id
                        )
                        # Update statistics
                        self._stats["num_orders_modified"] += 1
                        # Invalidate cache
                        self._cache_valid = False
                        return True
                    
                    # If quantity or expiry changed, update in-place
                    if new_quantity is not None or new_expiry_time is not None:
                        # Remove order from book
                        self._remove_from_book(order)
                        
                        # Update order
                        order.update(
                            quantity=new_quantity,
                            expiry_time=new_expiry_time
                        )
                        
                        # Add back to book
                        self._add_to_book(order)
                        
                        # Update statistics
                        self._stats["num_orders_modified"] += 1
                        
                        # Invalidate cache
                        self._cache_valid = False
                        
                        return True
                    
                    return False  # Nothing to modify
                except Exception as e:
                    # Atomic rollback in case of any error
                    if self.enable_logging:
                        logger.error(f"Error modifying order {order_id}: {str(e)}. Rolling back.")
                    
                    # Remove the potentially partially modified order
                    if order_id in self._orders:
                        self._remove_from_book(self._orders[order_id])
                    
                    # Restore original order
                    self._add_to_book(original_order)
                    
                    # Invalidate cache
                    self._cache_valid = False
                    
                    # Re-raise the exception for caller to handle
                    raise
        finally:
            # Record latency
            elapsed = time.time() - start_time
            self._record_latency("modify_order", elapsed)
    
    def cancel_order(self, order_id: str) -> bool:
        """
        Cancel an existing order.
        
        Args:
            order_id: ID of the order to cancel
            
        Returns:
            True if order was cancelled, False if order not found
        """
        start_time = time.time()
        
        try:
            with self._lock:
                if order_id not in self._orders:
                    if self.enable_logging:
                        logger.warning(f"Cannot cancel order {order_id}: order not found")
                    return False
                
                order = self._orders[order_id]
                if self.enable_logging:
                    logger.info(f"Cancelling order {order_id}: {order.side} {order.quantity} @ {order.price}")
                
                self._remove_from_book(order)
                
                # Update statistics
                self._stats["num_orders_cancelled"] += 1
                
                # Invalidate cache
                self._cache_valid = False
                
                return True
        finally:
            # Record latency
            elapsed = time.time() - start_time
            self._record_latency("cancel_order", elapsed)
    
    def batch_cancel_orders(self, order_ids: List[str]) -> Dict[str, bool]:
        """
        Cancel multiple orders in a single batch operation.
        
        Args:
            order_ids: List of order IDs to cancel
        
        Returns:
            Dictionary mapping order IDs to success/failure status
        """
        start_time = time.time()
        
        try:
            results = {}
            
            with self._lock:
                if self.enable_logging:
                    logger.info(f"Processing batch cancellation of {len(order_ids)} orders")
                
                for order_id in order_ids:
                    results[order_id] = self.cancel_order(order_id)
                
                # Invalidate cache
                self._cache_valid = False
                
                return results
        finally:
            # Record latency
            elapsed = time.time() - start_time
            self._record_latency("batch_cancel_orders", elapsed)
    
    def get_snapshot(self, depth: int = 10) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get a snapshot of the current order book state.
        
        Args:
            depth: Number of price levels to include
            
        Returns:
            Dictionary with bids and asks, each containing 
            list of [price, quantity, order_count] entries
        """
        start_time = time.time()
        
        try:
            with self._lock:
                # If the cache is valid and we want the top levels, use the cache
                if self._cache_valid and (depth <= len(self._bid_depth_cache) and depth <= len(self._ask_depth_cache)):
                    return {
                        "bids": self._bid_depth_cache[:depth],
                        "asks": self._ask_depth_cache[:depth]
                    }
                
                bids = []
                asks = []
                
                # Ensure bids are sorted in descending order (highest first)
                sorted_bids = sorted(self._bid_orders.keys(), reverse=True)
                
                # Add bid levels (highest first)
                for price in sorted_bids[:depth]:
                    orders = self._bid_orders[price]
                    if orders:  # Skip empty price levels
                        total_quantity = sum(order.quantity for order in orders.values())
                        bids.append({
                            "price": price,
                            "quantity": total_quantity,
                            "order_count": len(orders)
                        })
                
                # Ensure asks are sorted in ascending order (lowest first)
                sorted_asks = sorted(self._ask_orders.keys())
                
                # Add ask levels (lowest first)
                for price in sorted_asks[:depth]:
                    orders = self._ask_orders[price]
                    if orders:  # Skip empty price levels
                        total_quantity = sum(order.quantity for order in orders.values())
                        asks.append({
                            "price": price,
                            "quantity": total_quantity,
                            "order_count": len(orders)
                        })
                
                # Update the cache with all price levels
                self._bid_depth_cache = bids.copy()
                self._ask_depth_cache = asks.copy()
                self._cache_valid = True
                
                return {
                    "bids": bids,
                    "asks": asks
                }
        finally:
            # Record latency
            elapsed = time.time() - start_time
            self._record_latency("get_snapshot", elapsed)
    
    def get_order_depth_at_price(self, side: str, price: float) -> Dict[str, Any]:
        """
        Get the order depth at a specific price level.
        
        Args:
            side: 'buy' or 'sell'
            price: Price level to query
            
        Returns:
            Dictionary with price, quantity, and order_count
        """
        start_time = time.time()
        
        try:
            with self._lock:
                if side.lower() in ('buy', 'bid'):
                    orders = self._bid_orders.get(price, {})
                else:
                    orders = self._ask_orders.get(price, {})
                
                if not orders:
                    return {"price": price, "quantity": 0.0, "order_count": 0}
                
                total_quantity = sum(order.quantity for order in orders.values())
                return {
                    "price": price,
                    "quantity": total_quantity,
                    "order_count": len(orders)
                }
        finally:
            # Record latency
            elapsed = time.time() - start_time
            self._record_latency("get_snapshot", elapsed)  # Reusing get_snapshot for depth queries
    
    def get_trade_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get recent trades from the trade history.
        
        Args:
            limit: Maximum number of trades to return
            
        Returns:
            List of trades in dictionary form, newest first
        """
        with self._lock:
            trades = list(self._trade_history)
            trades.reverse()  # Newest first
            return [trade.to_dict() for trade in trades[:limit]]
    
    def get_order(self, order_id: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a specific order.
        
        Args:
            order_id: ID of the order to look up
            
        Returns:
            Dictionary with order information or None if not found
        """
        with self._lock:
            if order_id not in self._orders:
                return None
            
            return self._orders[order_id].to_dict()
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about the order book operations.
        
        Returns:
            Dictionary with statistics
        """
        with self._lock:
            # Add current state information
            stats = self._stats.copy()
            stats.update({
                "bid_levels": len(self._bid_orders),
                "ask_levels": len(self._ask_orders),
                "total_orders": len(self._orders),
                "bid_orders": sum(len(orders) for orders in self._bid_orders.values()),
                "ask_orders": sum(len(orders) for orders in self._ask_orders.values()),
                "trade_history_size": len(self._trade_history)
            })
            
            # Add best bid/ask if available
            if self._bids:
                stats["best_bid"] = self._bids[0]
            if self._asks:
                stats["best_ask"] = self._asks[0]
            
            return stats
    
    def clear(self) -> None:
        """Clear the order book, removing all orders."""
        with self._lock:
            if self.enable_logging:
                logger.info(f"Clearing order book for {self.symbol}")
            
            # Reset all internal data structures
            self._bids = []
            self._asks = []
            self._bid_orders = defaultdict(dict)
            self._ask_orders = defaultdict(dict)
            self._orders = {}
            self._bid_timestamps = defaultdict(list)
            self._ask_timestamps = defaultdict(list)
            self._trade_history = deque(maxlen=self.max_trade_history)
            self._deleted_price_levels = set()
            
            # Reset cache
            self._bid_depth_cache = []
            self._ask_depth_cache = []
            self._cache_valid = False
            
            # Reset statistics
            self._stats = {
                "num_orders_added": 0,
                "num_orders_modified": 0,
                "num_orders_cancelled": 0,
                "num_trades_executed": 0,
                "total_volume_traded": 0.0
            }
    
    def _add_to_book(self, order: Order) -> None:
        """Add an order to the book."""
        # Store order in lookup dictionary
        self._orders[order.order_id] = order
        
        # Add to appropriate side
        if order.side == Side.BUY:
            # Add to bid side
            if order.price not in self._bid_orders or not self._bid_orders[order.price]:
                # New price level - insert and maintain descending order
                if order.price not in self._bids:  # Ensure no duplicates
                    self._bids.append(order.price)
                    # Sort bids in descending order (highest price first)
                    self._bids.sort(reverse=True)
            
            # Add order to price level
            self._bid_orders[order.price][order.order_id] = order
            
            # Add to timestamp priority queue for FIFO execution
            bisect.insort_left(self._bid_timestamps[order.price], (order.timestamp, order.order_id))
        else:
            # Add to ask side
            if order.price not in self._ask_orders or not self._ask_orders[order.price]:
                # New price level
                if order.price not in self._asks:  # Ensure no duplicates
                    bisect.insort_left(self._asks, order.price)
            
            # Add order to price level
            self._ask_orders[order.price][order.order_id] = order
            
            # Add to timestamp priority queue for FIFO execution
            bisect.insort_left(self._ask_timestamps[order.price], (order.timestamp, order.order_id))
    
    def _remove_from_book(self, order: Order) -> None:
        """Remove an order from the book."""
        # Remove from lookup dictionary
        if order.order_id in self._orders:
            del self._orders[order.order_id]
        
        # Remove from appropriate side
        if order.side == Side.BUY:
            # Remove from bid side
            if order.price in self._bid_orders and order.order_id in self._bid_orders[order.price]:
                del self._bid_orders[order.price][order.order_id]
                
                # Remove from timestamp queue
                for i, (_, oid) in enumerate(self._bid_timestamps[order.price]):
                    if oid == order.order_id:
                        self._bid_timestamps[order.price].pop(i)
                        break
                
                # Clean up empty price level
                if not self._bid_orders[order.price]:
                    del self._bid_orders[order.price]
                    self._deleted_price_levels.add(order.price)
                    self._bids = [p for p in self._bids if p != order.price]
        else:
            # Remove from ask side
            if order.price in self._ask_orders and order.order_id in self._ask_orders[order.price]:
                del self._ask_orders[order.price][order.order_id]
                
                # Remove from timestamp queue
                for i, (_, oid) in enumerate(self._ask_timestamps[order.price]):
                    if oid == order.order_id:
                        self._ask_timestamps[order.price].pop(i)
                        break
                
                # Clean up empty price level
                if not self._ask_orders[order.price]:
                    del self._ask_orders[order.price]
                    self._deleted_price_levels.add(order.price)
                    self._asks = [p for p in self._asks if p != order.price]
    
    def _match_order(self, order: Order) -> List[Trade]:
        """
        Try to match an incoming order against the book.
        
        Args:
            order: The order to match
            
        Returns:
            List of trades that occurred
        """
        start_time = time.time()
        
        try:
            trades = []
            
            # No matching for immediate-or-cancel orders with quantity 0
            if order.quantity <= 0:
                return trades
            
            # Get opposing side
            if order.side == Side.BUY:
                opposing_levels = self._asks
                opposing_orders = self._ask_orders
                opposing_timestamps = self._ask_timestamps
            else:
                opposing_levels = self._bids
                opposing_orders = self._bid_orders
                opposing_timestamps = self._bid_timestamps
            
            # Continue matching until order is fully filled or no more matches
            while order.quantity > 0 and opposing_levels:
                best_price = opposing_levels[0]
                
                # For buy orders, check if best ask price is acceptable
                # For sell orders, check if best bid price is acceptable
                price_is_acceptable = False
                
                if order.side == Side.BUY:
                    price_is_acceptable = best_price <= order.price or self.enable_price_improvement
                else:
                    price_is_acceptable = best_price >= order.price or self.enable_price_improvement
                
                if not price_is_acceptable:
                    break
                
                # Match against all orders at this price level using FIFO
                timestamp_queue = opposing_timestamps[best_price]
                if not timestamp_queue:
                    # No orders left at this price level, move to next
                    opposing_levels.pop(0)
                    continue
                
                # Process orders in FIFO order
                for i, (_, matched_order_id) in enumerate(timestamp_queue[:]):
                    if matched_order_id not in opposing_orders[best_price]:
                        continue  # Order was removed, skip
                        
                    matched_order = opposing_orders[best_price][matched_order_id]
                    
                    # Determine the trade quantity
                    trade_quantity = min(order.quantity, matched_order.quantity)
                    
                    # Create the trade
                    trade = Trade(
                        maker_order_id=matched_order.order_id,
                        taker_order_id=order.order_id,
                        price=best_price,
                        quantity=trade_quantity,
                        timestamp=time.time(),
                        maker_fee_rate=self.maker_fee_rate,
                        taker_fee_rate=self.taker_fee_rate,
                        maker_user_id=matched_order.user_id,
                        taker_user_id=order.user_id
                    )
                    
                    trades.append(trade)
                    
                    # Add to trade history
                    self._trade_history.append(trade)
                    
                    # Update order quantities
                    order.quantity -= trade_quantity
                    matched_order.quantity -= trade_quantity
                    
                    # Update statistics
                    self._stats["num_trades_executed"] += 1
                    self._stats["total_volume_traded"] += trade_quantity
                    
                    if matched_order.quantity <= 0:
                        # Matched order is fully filled, remove from book
                        self._remove_from_book(matched_order)
                    
                    if order.quantity <= 0:
                        # Original order is fully filled
                        break
                
                # If there are no orders left at this price level, remove it
                if not opposing_orders[best_price]:
                    opposing_levels.pop(0)
            
            return trades
        finally:
            # Record latency
            elapsed = time.time() - start_time
            self._record_latency("match_order", elapsed) 