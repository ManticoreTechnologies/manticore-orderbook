"""
Core implementation of the OrderBook class.

This module contains the main OrderBook class that serves as the primary interface
for interacting with the order book functionality. It integrates and delegates to 
specialized components for specific functions.
"""

import logging
import threading
import time
from typing import Dict, List, Optional, Any, Tuple

from ..matching.matcher import OrderMatcher
from ..book_management.book_manager import BookManager
from ..utils.metrics import LatencyRecorder, PerformanceStats
from ..utils.expiry import ExpiryManager
from ..event_manager import EventManager, EventType

# Configure logging
logger = logging.getLogger("manticore_orderbook.core")

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
    - Immediate execution for favorable limit orders
    - Order expiry & Time-In-Force support
    - Performance monitoring
    - Detailed logging
    """
    
    def __init__(self, symbol: str, max_trade_history: int = 10000,
                maker_fee_rate: float = 0.0, taker_fee_rate: float = 0.0,
                enable_logging: bool = True, log_level: int = logging.INFO,
                check_expiry_interval: float = 1.0,
                event_manager: Optional[EventManager] = None,
                enable_price_improvement: bool = True):
        """
        Initialize a new orderbook.
        
        Args:
            symbol: Market symbol (e.g. "BTC/USD")
            max_trade_history: Maximum number of trades to keep in memory
            maker_fee_rate: Fee rate for makers (0.001 = 0.1%)
            taker_fee_rate: Fee rate for takers (0.001 = 0.1%)
            enable_logging: Whether to enable logging
            log_level: Logging level (INFO, DEBUG, etc.)
            check_expiry_interval: How often to check for expired orders (seconds)
            event_manager: Event manager instance (creates a new one if None)
            enable_price_improvement: Whether to enable price improvement for limit orders
        """
        self.symbol = symbol
        self.event_manager = event_manager or EventManager()
        self.book_manager = BookManager(max_trade_history=max_trade_history)
        self.matcher = OrderMatcher(
            enable_price_improvement=enable_price_improvement,
            maker_fee_rate=maker_fee_rate,
            taker_fee_rate=taker_fee_rate,
            book_manager=self.book_manager,
            event_manager=self.event_manager
        )
        
        # Store rates for test access
        self.maker_fee_rate = maker_fee_rate
        self.taker_fee_rate = taker_fee_rate
        
        # Initialize logger
        self.logger = logging.getLogger("manticore_orderbook.core")
        if enable_logging:
            self._setup_logging(log_level)
        
        # Mutex for thread-safety
        self._lock = threading.RLock()
        
        # Setup expiry manager
        self.expiry_manager = ExpiryManager(
            book_manager=self.book_manager,
            check_interval=check_expiry_interval,
            event_manager=self.event_manager
        )
        self.expiry_manager.start()
        
        # Performance metrics
        self.latency_recorder = LatencyRecorder()
        
        self.logger.info(f"OrderBook initialized for {symbol}")
        
    def _setup_logging(self, log_level: int) -> None:
        """
        Set up logging for the order book.
        
        Args:
            log_level: Log level to use
        """
        handler = logging.StreamHandler()
        handler.setLevel(log_level)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        
        logger.setLevel(log_level)
        if not logger.handlers:
            logger.addHandler(handler)
            
    def add_order(self, side: str, price: float, quantity: float, order_id: Optional[str] = None,
                time_in_force: Optional[str] = None, expiry_time: Optional[float] = None,
                user_id: Optional[str] = None, order_type: Optional[str] = None,
                stop_price: Optional[float] = None, trail_value: Optional[float] = None,
                trail_is_percent: bool = False, displayed_quantity: Optional[float] = None) -> str:
        """
        Add a new order to the book.
        
        Args:
            side: 'buy' or 'sell'
            price: Order price (can be None for market orders)
            quantity: Order quantity
            order_id: Unique order ID (generated if not provided)
            time_in_force: Time-in-force option ('GTC', 'IOC', 'FOK', 'GTD')
            expiry_time: Time when the order expires (required for GTD)
            user_id: User ID who placed the order
            order_type: Type of order ('LIMIT', 'MARKET', 'STOP_LIMIT', etc.)
            stop_price: Price at which stop orders are triggered
            trail_value: Value or percentage for trailing stop orders
            trail_is_percent: Whether trail_value is a percentage
            displayed_quantity: Visible quantity for iceberg orders
            
        Returns:
            Order ID of the added order
        """
        start_time = time.time()
        
        try:
            with self._lock:
                order = {
                    "symbol": self.symbol,
                    "side": side,
                    "price": price,
                    "quantity": quantity,
                    "timestamp": time.time(),
                    "order_id": order_id,
                    "time_in_force": time_in_force,
                    "expiry_time": expiry_time,
                    "user_id": user_id,
                    "order_type": order_type,
                    "stop_price": stop_price,
                    "trail_value": trail_value,
                    "trail_is_percent": trail_is_percent,
                    "displayed_quantity": displayed_quantity
                }
                
                # Process the order through the matcher
                order_id = self.matcher.process_order(order)
                
                # Record latency for add operation
                self.latency_recorder.record_latency("add_order", time.time() - start_time)
                
                return order_id
        except Exception as e:
            self.logger.error(f"Error adding order: {e}")
            if self.event_manager:
                self.event_manager.publish(EventType.ERROR, {
                    "operation": "add_order",
                    "error": str(e)
                })
            # Re-throw the exception for proper error handling in tests
            raise
    
    def batch_add_orders(self, orders: List[Dict[str, Any]]) -> List[str]:
        """
        Add multiple orders in a batch operation.
        
        Args:
            orders: List of order dictionaries
            
        Returns:
            List of order IDs for added orders
        """
        start_time = time.time()
        order_ids = []
        
        with self._lock:
            for order in orders:
                order_id = self.matcher.process_order(order)
                order_ids.append(order_id)
        
        elapsed = time.time() - start_time
        self.latency_recorder.record_latency("batch_add_orders", elapsed)
        
        logger.info(f"Added {len(orders)} orders in batch")
        return order_ids
        
    def cancel_order(self, order_id: str) -> bool:
        """
        Cancel an existing order.
        
        Args:
            order_id: ID of the order to cancel
            
        Returns:
            True if order was cancelled, False if not found
        """
        start_time = time.time()
        
        with self._lock:
            success = self.book_manager.cancel_order(order_id)
            
        elapsed = time.time() - start_time
        self.latency_recorder.record_latency("cancel_order", elapsed)
        
        if success:
            logger.info(f"Cancelled order {order_id}")
            self.event_manager.publish(EventType.ORDER_CANCELLED, {"order_id": order_id})
        else:
            logger.warning(f"Failed to cancel order {order_id}: not found")
            
        return success
    
    def batch_cancel_orders(self, order_ids: List[str]) -> Dict[str, bool]:
        """
        Cancel multiple orders in a batch operation.
        
        Args:
            order_ids: List of order IDs to cancel
            
        Returns:
            Dictionary mapping order IDs to cancellation success status
        """
        start_time = time.time()
        results = {}
        
        with self._lock:
            for order_id in order_ids:
                results[order_id] = self.book_manager.cancel_order(order_id)
                if results[order_id]:
                    self.event_manager.publish(EventType.ORDER_CANCELLED, {"order_id": order_id})
        
        elapsed = time.time() - start_time
        self.latency_recorder.record_latency("batch_cancel_orders", elapsed)
        
        logger.info(f"Batch cancelled {sum(results.values())}/{len(order_ids)} orders")
        return results
        
    def modify_order(self, order_id: str, new_price: Optional[float] = None, 
                    new_quantity: Optional[float] = None,
                    new_expiry_time: Optional[float] = None,
                    new_stop_price: Optional[float] = None,
                    new_trail_value: Optional[float] = None,
                    new_trail_is_percent: Optional[bool] = None,
                    new_displayed_quantity: Optional[float] = None) -> bool:
        """
        Modify an existing order in the book.
        
        Args:
            order_id: ID of the order to modify
            new_price: New price (if None, keep current price)
            new_quantity: New quantity (if None, keep current quantity)
            new_expiry_time: New expiry time (if None, keep current expiry time)
            new_stop_price: New stop price for stop orders
            new_trail_value: New trail value for trailing stop orders
            new_trail_is_percent: New trail_is_percent setting
            new_displayed_quantity: New displayed quantity for iceberg orders
            
        Returns:
            True if order was modified, False if order not found
        """
        start_time = time.time()
        
        try:
            with self._lock:
                result = self.book_manager.modify_order(
                    order_id, 
                    new_price=new_price, 
                    new_quantity=new_quantity, 
                    new_expiry_time=new_expiry_time,
                    new_stop_price=new_stop_price,
                    new_trail_value=new_trail_value,
                    new_trail_is_percent=new_trail_is_percent,
                    new_displayed_quantity=new_displayed_quantity
                )
                
                if result and self.event_manager:
                    order = self.book_manager.get_order(order_id)
                    if order:
                        self.event_manager.publish(EventType.ORDER_MODIFIED, {
                            "order_id": order_id,
                            "price": order.get("price"),
                            "quantity": order.get("quantity"),
                            "expiry_time": order.get("expiry_time"),
                            "stop_price": order.get("stop_price"),
                            "trail_value": order.get("trail_value"),
                            "trail_is_percent": order.get("trail_is_percent"),
                            "displayed_quantity": order.get("displayed_quantity"),
                            "new_quantity": order.get("quantity") if new_quantity is not None else None,
                            "new_price": order.get("price") if new_price is not None else None
                        })
                
                # After modifying the order, check if the book is crossed
                self.matcher._correct_crossed_book()
                
                # Record latency
                self.latency_recorder.record_latency("modify_order", time.time() - start_time)
                
                return result
        except Exception as e:
            self.logger.error(f"Error modifying order {order_id}: {e}")
            if self.event_manager:
                self.event_manager.publish(EventType.ERROR, {
                    "operation": "modify_order",
                    "order_id": order_id,
                    "error": str(e)
                })
            return False
    
    def get_snapshot(self, depth: int = None) -> Dict[str, Any]:
        """
        Get a snapshot of the current orderbook state.
        
        Args:
            depth: Maximum number of price levels to include (None for all)
            
        Returns:
            Dictionary containing bid and ask arrays and orderbook metadata
        """
        start_time = time.time()
        
        with self._lock:
            # Get order book state
            bids = self.book_manager.get_bids(depth)
            asks = self.book_manager.get_asks(depth)
            last_price = self.book_manager.get_last_price()
            
            # Calculate mid price and spread if possible
            best_bid_price = bids[0]['price'] if bids else None
            best_ask_price = asks[0]['price'] if asks else None
            
            mid_price = None
            spread = None
            spread_percentage = None
            
            if best_bid_price is not None and best_ask_price is not None:
                mid_price = (best_bid_price + best_ask_price) / 2
                spread = best_ask_price - best_bid_price
                spread_percentage = (spread / mid_price) * 100 if mid_price else None
            
            # Get trades for volume calculation
            trades = self.book_manager.get_trades()
            volume_24h = 0
            
            # Get current timestamp for 24h cutoff
            current_time = time.time()
            cutoff_time = current_time - 86400  # 24 hours
            
            # Calculate 24h volume
            for trade in trades:
                if trade.get('timestamp', 0) >= cutoff_time:
                    volume_24h += trade.get('quantity', 0) * trade.get('price', 0)
            
            # Calculate change from 24h ago (simplified)
            change_24h = 0
            if trades and last_price:
                oldest_price = None
                for trade in reversed(trades):
                    if trade.get('timestamp', 0) <= cutoff_time:
                        oldest_price = trade.get('price')
                        break
                
                if oldest_price:
                    change_24h = ((last_price - oldest_price) / oldest_price) * 100
            
            # Get order counts
            open_orders_count = self.book_manager.get_order_count()
            
            # Collect all bid and ask quantities
            bid_quantity = sum(level.get('quantity', 0) for level in bids)
            ask_quantity = sum(level.get('quantity', 0) for level in asks)
            
            # Build the snapshot
            snapshot = {
                'symbol': self.symbol,
                'timestamp': current_time,
                'bids': bids,
                'asks': asks,
                'stats': {
                    'bestBid': best_bid_price,
                    'bestAsk': best_ask_price,
                    'lastPrice': last_price,
                    'midPrice': mid_price,
                    'spread': spread,
                    'spreadPercentage': spread_percentage,
                    'volume24h': volume_24h,
                    'change24h': change_24h,
                    'openOrders': open_orders_count,
                    'bidQuantity': bid_quantity,
                    'askQuantity': ask_quantity
                }
            }
            
        # Record latency
        self.latency_recorder.record_latency("get_snapshot", time.time() - start_time)
        
        return snapshot
    
    def get_order(self, order_id: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a specific order.
        
        Args:
            order_id: ID of order to retrieve
            
        Returns:
            Order dictionary if found, None otherwise
        """
        with self._lock:
            return self.book_manager.get_order(order_id)
    
    def get_trade_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get recent trades from the trade history.
        
        Args:
            limit: Maximum number of trades to return
            
        Returns:
            List of trades in dictionary form, newest first
        """
        with self._lock:
            return self.book_manager.get_trade_history(limit)
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get order book statistics.
        
        Returns:
            Dictionary containing statistics about the order book
        """
        with self._lock:
            stats = self.book_manager.get_statistics()
            
        stats["latency_stats"] = self.latency_recorder.get_statistics()
        return stats
    
    def get_latency_stats(self) -> Dict[str, Dict[str, float]]:
        """
        Get operation latency statistics.
        
        Returns:
            Dictionary mapping operation names to latency statistics
        """
        return self.latency_recorder.get_statistics()
    
    def clean_expired_orders(self) -> int:
        """
        Remove orders that have expired.
        
        Returns:
            Number of orders removed
        """
        if self.expiry_manager:
            return self.expiry_manager.clean_expired_orders()
        else:
            self.logger.warning("Expiry manager not configured, cannot check expired orders")
            return 0
            
    def check_stop_orders(self) -> int:
        """
        Check all stop orders and trigger them if their conditions are met.
        
        Returns:
            Number of stop orders triggered
        """
        with self._lock:
            return self.matcher.check_stop_orders()
            
    def update_trailing_stops(self) -> int:
        """
        Update all trailing stop orders based on current market prices.
        
        Returns:
            Number of trailing stops updated
        """
        with self._lock:
            return self.matcher.update_trailing_stops()
    
    def clear(self) -> None:
        """
        Clear all orders and trades from the order book.
        """
        with self._lock:
            self.book_manager.clear()
            self.latency_recorder.clear()
            
        logger.info(f"Cleared order book for {self.symbol}")
        self.event_manager.publish(EventType.BOOK_CLEARED, {"symbol": self.symbol})
    
    def __del__(self):
        """
        Clean up resources when the order book is deleted.
        """
        if hasattr(self, 'expiry_manager'):
            self.expiry_manager.stop()
            
    # Properties for backward compatibility with tests
    @property
    def _bid_orders(self):
        """
        Get the internal bid orders dictionary from the BookManager.
        This is primarily for testing compatibility.
        """
        return self.book_manager._bids_at_price
        
    @property
    def _ask_orders(self):
        """
        Get the internal ask orders dictionary from the BookManager.
        This is primarily for testing compatibility.
        """
        return self.book_manager._asks_at_price
        
    @property
    def _bids(self):
        """
        Get the internal bids price list from the BookManager.
        This is primarily for testing compatibility.
        """
        return self.book_manager._bids
        
    @property
    def _asks(self):
        """
        Get the internal asks price list from the BookManager.
        This is primarily for testing compatibility.
        """
        return self.book_manager._asks
        
    def get_orders(self):
        """
        Get all orders in the book.
        
        Returns:
            Dictionary mapping order IDs to order dictionaries
        """
        with self._lock:
            return dict(self.book_manager._orders) 