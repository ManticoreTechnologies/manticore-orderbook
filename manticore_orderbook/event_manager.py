"""
Event management system for Manticore OrderBook.

This module provides an event-driven architecture for the order book system,
enabling integration with external systems through a publish-subscribe pattern.
The EventManager allows other modules to subscribe to specific events and react
to changes in the order book state.
"""

import logging
import threading
import time
from typing import Dict, List, Any, Callable, Set, Optional, Union
from enum import Enum, auto

# Configure logging
logger = logging.getLogger("manticore_orderbook.event_manager")

class EventType(Enum):
    """Event types that can be published by the order book system."""
    # Order lifecycle events
    ORDER_ADDED = auto()
    ORDER_MODIFIED = auto()
    ORDER_CANCELLED = auto()
    ORDER_FILLED = auto()  # Includes partial fills
    ORDER_EXPIRED = auto()
    ORDER_REJECTED = auto() # Order was rejected for some reason
    ORDER_TRIGGERED = auto() # Stop or trailing stop order was triggered
    
    # Trade events
    TRADE = auto()
    TRADE_EXECUTED = auto()
    
    # Price level events
    PRICE_LEVEL_ADDED = auto()
    PRICE_LEVEL_REMOVED = auto()
    PRICE_LEVEL_CHANGED = auto()
    
    # Market events
    MARKET_CREATED = auto()
    MARKET_CLEARED = auto()
    MARKET_DELETED = auto()
    
    # Book events
    BOOK_UPDATED = auto()
    BOOK_CLEARED = auto()
    DEPTH_CHANGED = auto()
    
    # System events
    ERROR = auto()
    SNAPSHOT_CREATED = auto()


# Type for event handlers
EventHandler = Callable[[EventType, Dict[str, Any]], None]


class Event:
    """
    Represents an event in the system.
    
    Attributes:
        event_type: Type of the event
        data: Event payload data
        timestamp: When the event occurred
        symbol: Market symbol the event relates to (if applicable)
    """
    
    def __init__(self, event_type: EventType, data: Dict[str, Any], 
                 timestamp: Optional[float] = None, symbol: Optional[str] = None):
        """
        Initialize a new event.
        
        Args:
            event_type: Type of the event
            data: Event payload data
            timestamp: Event timestamp (current time if not provided)
            symbol: Market symbol this event relates to
        """
        self.event_type = event_type
        self.data = data
        self.timestamp = timestamp or time.time()
        self.symbol = symbol
        
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert event to dictionary representation.
        
        Returns:
            Dict containing event data in a serializable format
        """
        return {
            "event_type": self.event_type.name,
            "data": self.data,
            "timestamp": self.timestamp,
            "symbol": self.symbol
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Event':
        """
        Create an event from a dictionary.
        
        Args:
            data: Dictionary containing event data
            
        Returns:
            Event object
        """
        return cls(
            event_type=EventType[data["event_type"]],
            data=data["data"],
            timestamp=data["timestamp"],
            symbol=data.get("symbol")
        )


class EventManager:
    """
    Manages events for the order book system.
    
    The EventManager provides a publish-subscribe interface for order book events,
    allowing external systems to react to changes in the order book state.
    """
    
    def __init__(self, enable_logging: bool = True, log_level: int = logging.INFO,
                 max_history_size: int = 1000):
        """
        Initialize a new event manager.
        
        Args:
            enable_logging: Whether to enable logging
            log_level: Log level to use
            max_history_size: Maximum number of events to keep in history
        """
        # Initialize event subscribers
        self._subscribers = {event_type: set() for event_type in EventType}
        self._global_subscribers = set()
        
        # Event history
        self._event_history = []
        self._max_history_size = max_history_size
        
        # Thread safety
        self._lock = threading.RLock()
        
        # Logging
        self._enable_logging = enable_logging
        if enable_logging:
            self._setup_logging(log_level)
            
        logger.info("EventManager initialized")
    
    def _setup_logging(self, log_level: int) -> None:
        """Set up logging configuration."""
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(log_level)
    
    def subscribe(self, event_type: EventType, handler: EventHandler) -> None:
        """
        Subscribe a handler to a specific event type.
        
        Args:
            event_type: Event type to subscribe to
            handler: Function to call when event occurs
        """
        with self._lock:
            self._subscribers[event_type].add(handler)
            logger.debug(f"Handler {handler.__name__} subscribed to {event_type.name}")
    
    def unsubscribe(self, event_type: EventType, handler: EventHandler) -> bool:
        """
        Unsubscribe a handler from a specific event type.
        
        Args:
            event_type: Event type to unsubscribe from
            handler: Handler to unsubscribe
            
        Returns:
            True if handler was unsubscribed, False if it wasn't subscribed
        """
        with self._lock:
            if handler in self._subscribers[event_type]:
                self._subscribers[event_type].remove(handler)
                logger.debug(f"Handler {handler.__name__} unsubscribed from {event_type.name}")
                return True
            else:
                logger.debug(f"Handler {handler.__name__} was not subscribed to {event_type.name}")
                return False
    
    def publish(self, event_type: EventType, data: Dict[str, Any], symbol: Optional[str] = None) -> None:
        """
        Publish an event to all subscribers.
        
        Args:
            event_type: Type of event to publish
            data: Event data
            symbol: Symbol associated with the event (if applicable)
        """
        with self._lock:
            # Create event
            event = Event(event_type, data, symbol=symbol)
            
            # Add to history
            self._event_history.append(event.to_dict())
            if len(self._event_history) > self._max_history_size:
                self._event_history.pop(0)
            
            # Get handlers to notify
            handlers = set(self._subscribers[event_type]) | self._global_subscribers
            
            # Log event
            if self._enable_logging:
                logger.debug(f"Event published: {event_type.name}, symbol: {symbol}")
            
        # Notify subscribers outside the lock to avoid deadlocks
        for handler in handlers:
            try:
                handler(event_type, data)
            except Exception as e:
                logger.error(f"Error in event handler {handler.__name__}: {str(e)}")
    
    def subscribe_all(self, handler: EventHandler) -> None:
        """
        Subscribe a handler to all event types.
        
        Args:
            handler: Function to call for all events
        """
        with self._lock:
            self._global_subscribers.add(handler)
            logger.debug(f"Handler {handler.__name__} subscribed to all events")
    
    def unsubscribe_all(self, handler: EventHandler) -> bool:
        """
        Unsubscribe a handler from all event types.
        
        Args:
            handler: Handler to unsubscribe
            
        Returns:
            True if handler was unsubscribed, False if it wasn't subscribed
        """
        with self._lock:
            was_subscribed = False
            
            # Check global subscribers
            if handler in self._global_subscribers:
                self._global_subscribers.remove(handler)
                was_subscribed = True
            
            # Check event-specific subscribers
            for event_type in EventType:
                if handler in self._subscribers[event_type]:
                    self._subscribers[event_type].remove(handler)
                    was_subscribed = True
            
            if was_subscribed:
                logger.debug(f"Handler {handler.__name__} unsubscribed from all events")
                
            return was_subscribed
    
    def get_event_history(self, limit: int = 100, event_type: Optional[EventType] = None,
                         symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get recent events from history.
        
        Args:
            limit: Maximum number of events to return
            event_type: Filter events by type
            symbol: Filter events by symbol
            
        Returns:
            List of recent events
        """
        with self._lock:
            events = self._event_history.copy()
            
        # Apply filters
        if event_type:
            events = [e for e in events if e["event_type"] == event_type.name]
        if symbol:
            events = [e for e in events if e.get("symbol") == symbol]
            
        # Return most recent events first
        return sorted(events, key=lambda e: e["timestamp"], reverse=True)[:limit]
    
    def clear_history(self) -> None:
        """
        Clear event history.
        """
        with self._lock:
            self._event_history.clear()
            logger.debug("Event history cleared")
    
    def set_max_history_size(self, size: int) -> None:
        """
        Set maximum event history size.
        
        Args:
            size: Maximum number of events to store
        """
        if size < 0:
            raise ValueError("History size cannot be negative")
            
        with self._lock:
            self._max_history_size = size
            
            # Trim history if needed
            if len(self._event_history) > size:
                self._event_history = self._event_history[-size:]
                
            logger.debug(f"Max history size set to {size}")
    
    def get_subscriber_count(self, event_type: Optional[EventType] = None) -> Dict[str, int]:
        """
        Get count of subscribers.
        
        Args:
            event_type: Event type to get count for (all events if None)
            
        Returns:
            Dictionary with subscriber counts
        """
        with self._lock:
            if event_type:
                return {event_type.name: len(self._subscribers[event_type])}
            else:
                return {
                    "global": len(self._global_subscribers),
                    **{et.name: len(self._subscribers[et]) for et in EventType}
                } 