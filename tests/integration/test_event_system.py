#!/usr/bin/env python3
"""
Integration tests for the OrderBook event system.

These tests verify that events are properly generated and
processed when the orderbook is modified.
"""

import unittest
import logging
from collections import defaultdict
from manticore_orderbook import OrderBook, EventManager, EventType

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('event_test')


class TestEventSystem(unittest.TestCase):
    """Test the orderbook's event system."""
    
    def setUp(self):
        """Set up the test fixtures."""
        self.event_manager = EventManager()
        self.orderbook = OrderBook(
            symbol="BTC/USD",
            event_manager=self.event_manager,
            enable_price_improvement=False
        )
        
        # Track events by type
        self.event_count = defaultdict(int)
        self.last_event_data = {}
        
        # Subscribe to all event types
        for event_type in EventType:
            self.event_manager.subscribe(
                event_type,
                lambda event_type, data: self._handle_event(event_type, data)
            )
    
    def _handle_event(self, event_type, data):
        """Handle events and track them for verification."""
        self.event_count[event_type] += 1
        self.last_event_data[event_type] = data
    
    def tearDown(self):
        """Clean up after the test."""
        self.orderbook.clear()
        self.event_count.clear()
        self.last_event_data.clear()
    
    def test_order_add_events(self):
        """Test that adding orders generates appropriate events."""
        # Add a buy order
        self.orderbook.add_order(side="buy", price=9000.00, quantity=1.0, order_id="bid1")
        
        # Verify ORDER_ADDED event was generated
        self.assertEqual(self.event_count[EventType.ORDER_ADDED], 1)
        
        # Verify event data
        event_data = self.last_event_data[EventType.ORDER_ADDED]
        self.assertEqual(event_data["order_id"], "bid1")
    
    def test_order_match_events(self):
        """Test that matching orders generates appropriate events."""
        # Add a buy order
        self.orderbook.add_order(side="buy", price=9000.00, quantity=1.0, order_id="bid1")
        
        # Add a sell order that crosses
        self.orderbook.add_order(side="sell", price=8500.00, quantity=1.0, order_id="ask1")
        
        # Verify TRADE_EXECUTED event was generated
        self.assertEqual(self.event_count[EventType.TRADE_EXECUTED], 1)
        
        # Verify ORDER_FILLED events were generated
        self.assertEqual(self.event_count[EventType.ORDER_FILLED], 2)  # One for each order
        
        # Verify trade data
        trade_data = self.last_event_data[EventType.TRADE_EXECUTED]
        self.assertEqual(trade_data["maker_order_id"], "bid1")
        self.assertEqual(trade_data["taker_order_id"], "ask1")
        self.assertEqual(trade_data["price"], 9000.00)
        self.assertEqual(trade_data["quantity"], 1.0)
    
    def test_order_cancel_events(self):
        """Test that canceling orders generates appropriate events."""
        # Add an order then cancel it
        self.orderbook.add_order(side="buy", price=9000.00, quantity=1.0, order_id="bid1")
        self.orderbook.cancel_order("bid1")
        
        # Verify ORDER_CANCELLED event was generated
        self.assertEqual(self.event_count[EventType.ORDER_CANCELLED], 1)
        
        # Verify event data
        event_data = self.last_event_data[EventType.ORDER_CANCELLED]
        self.assertEqual(event_data["order_id"], "bid1")
    
    def test_order_modify_events(self):
        """Test that modifying orders generates appropriate events."""
        # Add an order
        self.orderbook.add_order(side="buy", price=9000.00, quantity=1.0, order_id="bid1")
        
        # Modify the order
        self.orderbook.modify_order("bid1", new_quantity=2.0)
        
        # Verify ORDER_MODIFIED event was generated
        self.assertEqual(self.event_count[EventType.ORDER_MODIFIED], 1)
        
        # Verify event data
        event_data = self.last_event_data[EventType.ORDER_MODIFIED]
        self.assertEqual(event_data["order_id"], "bid1")
        self.assertEqual(event_data["new_quantity"], 2.0)
    
    def test_multiple_event_subscribers(self):
        """Test that multiple subscribers receive events."""
        # Create counters for two separate subscribers
        counter1 = 0
        counter2 = 0
        
        # Create subscriber functions
        def subscriber1(event_type, data):
            nonlocal counter1
            if event_type == EventType.ORDER_ADDED:
                counter1 += 1
        
        def subscriber2(event_type, data):
            nonlocal counter2
            if event_type == EventType.ORDER_ADDED:
                counter2 += 1
        
        # Subscribe both functions
        self.event_manager.subscribe(EventType.ORDER_ADDED, subscriber1)
        self.event_manager.subscribe(EventType.ORDER_ADDED, subscriber2)
        
        # Add some orders
        self.orderbook.add_order(side="buy", price=9000.00, quantity=1.0, order_id="bid1")
        self.orderbook.add_order(side="buy", price=9100.00, quantity=1.0, order_id="bid2")
        
        # Verify both subscribers were called
        self.assertEqual(counter1, 2)
        self.assertEqual(counter2, 2)
    
    def test_unsubscribe(self):
        """Test that unsubscribing stops events."""
        # Create counter and subscriber
        counter = 0
        
        def subscriber(event_type, data):
            nonlocal counter
            counter += 1
        
        # Subscribe, generate an event, then unsubscribe
        self.event_manager.subscribe(EventType.ORDER_ADDED, subscriber)
        self.orderbook.add_order(side="buy", price=9000.00, quantity=1.0, order_id="bid1")
        self.assertEqual(counter, 1)
        
        # Unsubscribe and verify no more events are received
        self.event_manager.unsubscribe(EventType.ORDER_ADDED, subscriber)
        self.orderbook.add_order(side="buy", price=9100.00, quantity=1.0, order_id="bid2")
        self.assertEqual(counter, 1)  # Still 1, not 2


if __name__ == "__main__":
    unittest.main() 