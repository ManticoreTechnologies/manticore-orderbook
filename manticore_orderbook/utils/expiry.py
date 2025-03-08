"""
Order expiry utilities for Manticore OrderBook.

This module contains utilities for managing order expiration.
"""

import logging
import threading
import time
from typing import Optional

from ..book_management.book_manager import BookManager
from ..event_manager import EventType

# Configure logging
logger = logging.getLogger("manticore_orderbook.utils.expiry")

class ExpiryManager:
    """
    Manages order expiration, including scheduled expiry checks.
    """
    
    def __init__(self, book_manager: BookManager, check_interval: float = 1.0, event_manager=None):
        """
        Initialize a new ExpiryManager.
        
        Args:
            book_manager: BookManager instance to use
            check_interval: How often to check for expired orders (seconds)
            event_manager: EventManager instance to use for notifications
        """
        self.book_manager = book_manager
        self.check_interval = check_interval
        self.event_manager = event_manager
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
    
    def start(self) -> None:
        """
        Start the expiry checker thread.
        """
        if self._running:
            return
            
        self._running = True
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_expiry_checker)
        self._thread.daemon = True
        self._thread.start()
        
        logger.info(f"Started order expiry checker (interval: {self.check_interval}s)")
    
    def stop(self) -> None:
        """
        Stop the expiry checker thread.
        """
        if not self._running:
            return
            
        self._running = False
        self._stop_event.set()
        
        if self._thread:
            self._thread.join(timeout=2.0)
            
        logger.info("Stopped order expiry checker")
    
    def _run_expiry_checker(self) -> None:
        """
        Run the expiry checker loop.
        """
        while self._running and not self._stop_event.is_set():
            try:
                self.clean_expired_orders()
            except Exception as e:
                logger.error(f"Error in expiry checker: {e}")
                
            # Sleep until next check
            self._stop_event.wait(self.check_interval)
    
    def clean_expired_orders(self) -> int:
        """
        Remove expired orders from the book.
        
        Returns:
            Number of orders removed
        """
        current_time = time.time()
        expired_order_ids = self.book_manager.get_expired_orders(current_time)
        
        count = 0
        for order_id in expired_order_ids:
            order = self.book_manager.get_order(order_id)
            if order and self.book_manager.cancel_order(order_id):
                count += 1
                # Publish event if event_manager is available
                if self.event_manager:
                    self.event_manager.publish(EventType.ORDER_EXPIRED, {
                        "order_id": order_id, 
                        "side": order.get("side"),
                        "price": order.get("price"),
                        "quantity": order.get("quantity"),
                        "timestamp": current_time
                    })
                
        if count > 0:
            logger.info(f"Removed {count} expired orders")
            
        return count 