"""
Test suite for order book event emission.

Tests that events are properly emitted during order operations.
"""

import unittest
import time
from threading import Thread
from typing import Dict, List, Any

from manticore_orderbook import OrderBook, EventManager, EventType


class EventCollector:
    """Helper class to collect and inspect events."""
    
    def __init__(self):
        """Initialize event collector."""
        self.events = []
        self.event_counts = {event_type: 0 for event_type in EventType}
    
    def on_event(self, event_type, data):
        """Event handler that records events."""
        self.events.append((event_type, data))
        self.event_counts[event_type] += 1
    
    def reset(self):
        """Reset event collector."""
        self.events = []
        self.event_counts = {event_type: 0 for event_type in EventType}
    
    def get_events_by_type(self, event_type):
        """Return events of a specific type."""
        return [data for typ, data in self.events if typ == event_type]
    
    def get_event_count(self, event_type):
        """Return count of events of a specific type."""
        return self.event_counts.get(event_type, 0)
    
    def has_event(self, event_type, predicate=None):
        """
        Check if an event of the given type exists.
        
        Args:
            event_type: Type of event to check for
            predicate: Optional function that takes event data and returns True/False
        
        Returns:
            True if matching event exists, False otherwise
        """
        for typ, data in self.events:
            if typ == event_type:
                if predicate is None or predicate(data):
                    return True
        return False


class TestOrderBookEvents(unittest.TestCase):
    """Test case for order book event emission."""
    
    def setUp(self):
        """Set up test case."""
        self.event_manager = EventManager(enable_logging=False)
        self.collector = EventCollector()
        
        # Subscribe to all events
        self.event_manager.subscribe_all(self.collector.on_event)
        
        # Create order book
        self.orderbook = OrderBook(
            symbol="BTC/USD", 
            enable_logging=False,
            event_manager=self.event_manager
        )
    
    def tearDown(self):
        """Clean up test case."""
        self.orderbook.clear()
        self.collector.reset()
    
    def test_add_order_event(self):
        """Test that adding an order emits an event."""
        # Add order
        order_id = self.orderbook.add_order(
            side="buy",
            price=10000.0,
            quantity=1.0,
            order_id="test1"
        )
        
        # Check that event was emitted
        self.assertEqual(self.collector.get_event_count(EventType.ORDER_ADDED), 1)
        
        # Check event data
        events = self.collector.get_events_by_type(EventType.ORDER_ADDED)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].get("order", {}).get("order_id"), "test1")
        self.assertEqual(events[0].get("symbol"), "BTC/USD")
    
    def test_cancel_order_event(self):
        """Test that cancelling an order emits an event."""
        # Add and cancel order
        order_id = self.orderbook.add_order(
            side="buy",
            price=10000.0,
            quantity=1.0,
            order_id="test1"
        )
        
        # Reset collector
        self.collector.reset()
        
        # Cancel the order
        self.orderbook.cancel_order(order_id)
        
        # Check that event was emitted
        self.assertEqual(self.collector.get_event_count(EventType.ORDER_CANCELLED), 1)
        
        # Check event data
        events = self.collector.get_events_by_type(EventType.ORDER_CANCELLED)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].get("order_id"), "test1")
        self.assertEqual(events[0].get("symbol"), "BTC/USD")
    
    def test_modify_order_event(self):
        """Test that modifying an order emits an event."""
        # Add order
        order_id = self.orderbook.add_order(
            side="buy",
            price=10000.0,
            quantity=1.0,
            order_id="test1"
        )
        
        # Reset collector
        self.collector.reset()
        
        # Modify the order
        self.orderbook.modify_order(
            order_id=order_id,
            new_price=10100.0,
            new_quantity=1.5
        )
        
        # Check that event was emitted
        self.assertEqual(self.collector.get_event_count(EventType.ORDER_MODIFIED), 1)
        
        # Check event data
        events = self.collector.get_events_by_type(EventType.ORDER_MODIFIED)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].get("order_id"), "test1")
        self.assertEqual(events[0].get("original_price"), 10000.0)
        self.assertEqual(events[0].get("new_price"), 10100.0)
        self.assertEqual(events[0].get("original_quantity"), 1.0)
        self.assertEqual(events[0].get("new_quantity"), 1.5)
    
    def test_trade_execution_events(self):
        """Test that trade execution emits appropriate events."""
        # Add a sell order
        self.orderbook.add_order(
            side="sell",
            price=10000.0,
            quantity=1.0,
            order_id="sell1"
        )
        
        # Reset collector
        self.collector.reset()
        
        # Add a matching buy order
        self.orderbook.add_order(
            side="buy",
            price=10000.0,
            quantity=0.5,
            order_id="buy1"
        )
        
        # Check that trade event was emitted
        self.assertEqual(self.collector.get_event_count(EventType.TRADE_EXECUTED), 1)
        
        # Check that fill events were emitted
        self.assertGreaterEqual(self.collector.get_event_count(EventType.ORDER_FILLED), 2)
        
        # Check trade event data
        trade_events = self.collector.get_events_by_type(EventType.TRADE_EXECUTED)
        self.assertEqual(len(trade_events), 1)
        self.assertEqual(trade_events[0].get("trade", {}).get("price"), 10000.0)
        self.assertEqual(trade_events[0].get("trade", {}).get("quantity"), 0.5)
        
        # Verify maker fill event
        self.assertTrue(self.collector.has_event(
            EventType.ORDER_FILLED,
            lambda data: data.get("order_id") == "sell1" and data.get("filled_quantity") == 0.5
        ))
        
        # Verify taker fill event
        self.assertTrue(self.collector.has_event(
            EventType.ORDER_FILLED,
            lambda data: data.get("order_id") == "buy1" and data.get("fully_filled") is True
        ))
    
    def test_full_match_events(self):
        """Test events when an order is fully matched immediately."""
        # Add a sell order
        self.orderbook.add_order(
            side="sell",
            price=10000.0,
            quantity=1.0,
            order_id="sell1"
        )
        
        # Reset collector
        self.collector.reset()
        
        # Add a matching buy order that fully matches
        self.orderbook.add_order(
            side="buy",
            price=10000.0,
            quantity=1.0,
            order_id="buy1"
        )
        
        # Check that trade event was emitted
        self.assertEqual(self.collector.get_event_count(EventType.TRADE_EXECUTED), 1)
        
        # Check that fill events were emitted
        fill_events = self.collector.get_events_by_type(EventType.ORDER_FILLED)
        self.assertEqual(len(fill_events), 2)  # Both orders fully filled
        
        # Verify both orders show as fully filled
        self.assertTrue(self.collector.has_event(
            EventType.ORDER_FILLED,
            lambda data: data.get("order_id") == "sell1" and data.get("fully_filled") is True
        ))
        
        self.assertTrue(self.collector.has_event(
            EventType.ORDER_FILLED,
            lambda data: data.get("order_id") == "buy1" and data.get("fully_filled") is True
        ))
    
    def test_order_expiry_events(self):
        """Test events when an order expires."""
        # Add an order with short expiry
        expiry_time = time.time() + 0.1
        self.orderbook.add_order(
            side="buy",
            price=10000.0,
            quantity=1.0,
            order_id="exp1",
            time_in_force="GTD",
            expiry_time=expiry_time
        )
        
        # Reset collector
        self.collector.reset()
        
        # Wait for expiry
        time.sleep(0.2)
        
        # Trigger cleanup
        self.orderbook.clean_expired_orders()
        
        # Check for expiry event
        self.assertEqual(self.collector.get_event_count(EventType.ORDER_EXPIRED), 1)
        
        # Verify expiry event details
        expiry_events = self.collector.get_events_by_type(EventType.ORDER_EXPIRED)
        self.assertEqual(len(expiry_events), 1)
        self.assertEqual(expiry_events[0].get("order_id"), "exp1")
    
    def test_ioc_order_events(self):
        """Test events when using IOC orders."""
        # Add a sell order
        self.orderbook.add_order(
            side="sell",
            price=10000.0,
            quantity=2.0,
            order_id="sell1"
        )
        
        # Reset collector
        self.collector.reset()
        
        # Add an IOC buy order that partially matches
        self.orderbook.add_order(
            side="buy",
            price=10000.0,
            quantity=1.0,
            order_id="buy1",
            time_in_force="IOC"
        )
        
        # Check that trade event was emitted
        self.assertEqual(self.collector.get_event_count(EventType.TRADE_EXECUTED), 1)
        
        # Check for fill events
        self.assertEqual(self.collector.get_event_count(EventType.ORDER_FILLED), 2)
        
        # Verify no order added event since IOC orders aren't added to the book
        self.assertEqual(self.collector.get_event_count(EventType.ORDER_ADDED), 0)
    
    def test_concurrent_event_handling(self):
        """Test event emission with concurrent operations."""
        # Define a slow event handler to test concurrent processing
        events_received = []
        
        def slow_handler(event_type, data):
            """Slow event handler to simulate real-world processing."""
            time.sleep(0.01)  # Small delay
            events_received.append((event_type, data))
        
        # Subscribe slow handler to all events
        self.event_manager.subscribe_all(slow_handler)
        
        # Run multiple operations in parallel
        def add_orders():
            for i in range(10):
                self.orderbook.add_order(
                    side="buy",
                    price=10000.0 + i,
                    quantity=1.0,
                    order_id=f"test{i}"
                )
        
        # Create threads
        threads = [Thread(target=add_orders) for _ in range(3)]
        
        # Start threads
        for thread in threads:
            thread.start()
        
        # Wait for threads to complete
        for thread in threads:
            thread.join()
        
        # Give event handlers time to complete
        time.sleep(0.5)
        
        # Verify all events were received
        self.assertEqual(len(events_received), 30)  # 10 orders × 3 threads
        
        # Verify correct event types
        self.assertTrue(all(et == EventType.ORDER_ADDED for et, _ in events_received))


if __name__ == "__main__":
    unittest.main() 