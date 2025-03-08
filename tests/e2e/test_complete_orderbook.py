#!/usr/bin/env python3
"""
End-to-end tests for the Manticore OrderBook implementation.

These tests verify that all order types work together correctly in
realistic trading scenarios.
"""

import unittest
import logging
import time
import threading
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from manticore_orderbook import OrderBook, EventManager, EventType

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('e2e_test')


class CompleteOrderBookE2ETest(unittest.TestCase):
    """
    End-to-end tests for the complete OrderBook functionality.
    
    These tests simulate a realistic trading environment with multiple
    traders placing different types of orders simultaneously.
    """
    
    def setUp(self):
        """Set up testing environment."""
        self.event_manager = EventManager()
        self.orderbook = OrderBook(
            symbol="BTC/USD",
            event_manager=self.event_manager,
            enable_price_improvement=True,
            maker_fee_rate=0.001,
            taker_fee_rate=0.002
        )
        
        # Track events for verification
        self.event_counts = defaultdict(int)
        self.events_lock = threading.Lock()
        self.trades = []
        
        # Subscribe to events
        for event_type in EventType:
            self.event_manager.subscribe(event_type, self._handle_event)
    
    def _handle_event(self, event_type, data):
        """Handle events and track them for verification."""
        with self.events_lock:
            self.event_counts[event_type] += 1
            
            # Record trades for verification
            if event_type == EventType.TRADE_EXECUTED:
                self.trades.append(data)
    
    def _reset_trackers(self):
        """Reset event counts and trades."""
        with self.events_lock:
            self.event_counts.clear()
            self.trades.clear()
    
    def tearDown(self):
        """Clean up resources."""
        self.event_manager = None
        self.orderbook = None
    
    def test_all_order_types_e2e(self):
        """
        Test all order types working together in a realistic scenario.
        
        This test simulates a market with various traders placing different
        types of orders and verifies that they are matched correctly.
        """
        # Initialize the order book with some limit orders
        self.orderbook.add_order(
            side="buy", price=9800, quantity=1.0, order_id="buy_1",
            time_in_force="GTC", order_type="LIMIT"
        )
        self.orderbook.add_order(
            side="buy", price=9850, quantity=2.0, order_id="buy_2", 
            time_in_force="GTC", order_type="LIMIT"
        )
        self.orderbook.add_order(
            side="sell", price=10200, quantity=1.5, order_id="sell_1",
            time_in_force="GTC", order_type="LIMIT"
        )
        self.orderbook.add_order(
            side="sell", price=10150, quantity=2.5, order_id="sell_2",
            time_in_force="GTC", order_type="LIMIT"
        )
        
        # Verify initial state
        snapshot = self.orderbook.get_snapshot()
        self.assertEqual(len(snapshot["bids"]), 2)
        self.assertEqual(len(snapshot["asks"]), 2)
        self.assertEqual(snapshot["stats"]["bestBid"], 9850)
        self.assertEqual(snapshot["stats"]["bestAsk"], 10150)
        
        # Reset event counters
        self._reset_trackers()
        
        # Test 1: Market order should execute immediately
        self.orderbook.add_order(
            side="buy", price=None, quantity=1.0, order_id="market_buy_1",
            order_type="MARKET"
        )
        
        # Verify market order execution
        self.assertGreaterEqual(self.event_counts[EventType.TRADE_EXECUTED], 1)
        
        # Test 2: Fill-or-Kill order that can be fully filled
        self.orderbook.add_order(
            side="buy", price=10200, quantity=1.0, order_id="fok_buy_1",
            time_in_force="FOK", order_type="LIMIT"
        )
        
        # Verify FOK execution
        self.assertGreaterEqual(self.event_counts[EventType.TRADE_EXECUTED], 2)
        
        # Test 3: Fill-or-Kill order that cannot be fully filled
        self.orderbook.add_order(
            side="buy", price=10150, quantity=10.0, order_id="fok_buy_2",
            time_in_force="FOK", order_type="LIMIT"
        )
        
        # Store the trade count before next order
        trade_count_before_ioc = self.event_counts[EventType.TRADE_EXECUTED]
        
        # Test 4: Immediate-or-Cancel order
        self.orderbook.add_order(
            side="buy", price=10200, quantity=5.0, order_id="ioc_buy_1",
            time_in_force="IOC", order_type="LIMIT"
        )
        
        # Verify IOC partial execution
        self.assertGreater(self.event_counts[EventType.TRADE_EXECUTED], trade_count_before_ioc)
        
        # Store the trade count before next order
        trade_count_before_post_only = self.event_counts[EventType.TRADE_EXECUTED]
        
        # Test 5: Post-Only order that would cross
        self.orderbook.add_order(
            side="buy", price=10300, quantity=1.0, order_id="post_only_buy_1",
            order_type="POST_ONLY"
        )
        
        # Verify Post-Only behavior (no additional trades)
        self.assertEqual(self.event_counts[EventType.TRADE_EXECUTED], trade_count_before_post_only)
        
        # Test 6: Post-Only order that doesn't cross
        self.orderbook.add_order(
            side="buy", price=10100, quantity=1.0, order_id="post_only_buy_2",
            order_type="POST_ONLY"
        )
        
        # Verify Post-Only order was added to book
        snapshot = self.orderbook.get_snapshot()
        found = False
        for bid in snapshot["bids"]:
            if bid["price"] == 10100:
                found = True
                break
        self.assertTrue(found)
        
        # Test 7: Iceberg order
        self.orderbook.add_order(
            side="sell", price=10300, quantity=5.0, order_id="iceberg_sell_1",
            order_type="ICEBERG", displayed_quantity=1.0
        )
        
        # Verify iceberg initial display
        snapshot = self.orderbook.get_snapshot()
        found = False
        for ask in snapshot["asks"]:
            if ask["price"] == 10300:
                self.assertTrue(ask["quantity"] <= 1.0)
                found = True
                break
        self.assertTrue(found)
        
        # Test 8: Good-till-date order
        future_time = time.time() + 3600  # 1 hour in the future
        self.orderbook.add_order(
            side="buy", price=10000, quantity=1.0, order_id="gtd_buy_1",
            time_in_force="GTD", expiry_time=future_time
        )
        
        # Verify GTD order was added
        snapshot = self.orderbook.get_snapshot()
        found = False
        for bid in snapshot["bids"]:
            if bid["price"] == 10000:
                found = True
                break
        self.assertTrue(found)
        
        # Test 9: Stop-limit order
        self.orderbook.add_order(
            side="sell", price=9700, quantity=1.0, order_id="stop_limit_sell_1",
            order_type="STOP_LIMIT", stop_price=9800
        )
        
        # This shouldn't be triggered yet, as the price hasn't moved below 9800
        snapshot = self.orderbook.get_snapshot()
        for ask in snapshot["asks"]:
            self.assertNotEqual(ask["price"], 9700)
            
        # Simulate price movement to trigger stop order by executing some trades
        self.orderbook.add_order(
            side="sell", price=9750, quantity=0.5, order_id="trigger_sell_1"
        )
        
        # Add a market order to hit that price
        self.orderbook.add_order(
            side="buy", price=None, quantity=0.5, order_id="market_buy_2",
            order_type="MARKET"
        )
        
        # Now the stop should be triggered
        snapshot = self.orderbook.get_snapshot()
        found = False
        for ask in snapshot["asks"]:
            if ask["price"] == 9700:
                found = True
                break
        
        # Either the order should be in the book or already executed
        trade_executed = False
        for trade in self.trades:
            if trade.get("maker_order_id") == "stop_limit_sell_1" or trade.get("taker_order_id") == "stop_limit_sell_1":
                trade_executed = True
                break
                
        self.assertTrue(found or trade_executed)
        
        # Test all event counts
        self.assertGreater(self.event_counts[EventType.ORDER_ADDED], 0)
        self.assertGreater(self.event_counts[EventType.TRADE_EXECUTED], 0)
        
        # Final verification: Check the order book state with a deep snapshot
        final_snapshot = self.orderbook.get_snapshot()
        logger.info(f"Final order book state: {final_snapshot}")
        logger.info(f"Total trades executed: {len(self.trades)}")
        
        # Verify that the book is in a valid state
        if final_snapshot["bids"] and final_snapshot["asks"]:
            best_bid = final_snapshot["stats"]["bestBid"]
            best_ask = final_snapshot["stats"]["bestAsk"]
            self.assertLess(best_bid, best_ask, "Order book is crossed!")


if __name__ == "__main__":
    unittest.main() 