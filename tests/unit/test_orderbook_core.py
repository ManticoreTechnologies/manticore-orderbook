#!/usr/bin/env python3
"""
Core unit tests for Manticore OrderBook implementation.

These tests verify the fundamental operation of the orderbook,
including order matching, price levels, and other core functionality.
"""

import unittest
import logging
import time
from manticore_orderbook import OrderBook, EventManager, EventType, Side

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('orderbook_test')


class OrderBookTestCase(unittest.TestCase):
    """Base test case for OrderBook with common setup."""
    
    def setUp(self):
        """Set up the test by creating an orderbook instance."""
        self.event_manager = EventManager()
        self.orderbook = OrderBook(
            symbol="BTC/USD",
            event_manager=self.event_manager,
            enable_price_improvement=False,  # Disable price improvement for predictable test results
            maker_fee_rate=0.001, 
            taker_fee_rate=0.002
        )
        
        # Capture events for test verification
        self.captured_events = []
        
        # Subscribe to orderbook events
        for event_type in EventType:
            self.event_manager.subscribe(
                event_type, 
                lambda event_type, data: self.captured_events.append((event_type, data))
            )
    
    def tearDown(self):
        """Clean up after the test."""
        self.orderbook.clear()
        self.captured_events = []


class TestOrderBookBasicFunctionality(OrderBookTestCase):
    """Test basic orderbook functionality."""
    
    def test_initialization(self):
        """Test that the orderbook initializes correctly."""
        self.assertEqual(self.orderbook.symbol, "BTC/USD")
        self.assertEqual(self.orderbook.maker_fee_rate, 0.001)
        self.assertEqual(self.orderbook.taker_fee_rate, 0.002)
        
        # Verify initial state
        snapshot = self.orderbook.get_snapshot()
        self.assertEqual(len(snapshot["bids"]), 0)
        self.assertEqual(len(snapshot["asks"]), 0)
    
    def test_add_orders(self):
        """Test adding orders to the book."""
        # Add a buy order
        bid_id = self.orderbook.add_order(side="buy", price=9000.00, quantity=1.0, order_id="bid1")
        self.assertEqual(bid_id, "bid1")
        
        # Add a sell order
        ask_id = self.orderbook.add_order(side="sell", price=9500.00, quantity=1.0, order_id="ask1")
        self.assertEqual(ask_id, "ask1")
        
        # Verify orders were added
        snapshot = self.orderbook.get_snapshot()
        self.assertEqual(len(snapshot["bids"]), 1)
        self.assertEqual(len(snapshot["asks"]), 1)
        
        # Verify price levels
        self.assertEqual(snapshot["bids"][0]["price"], 9000.00)
        self.assertEqual(snapshot["asks"][0]["price"], 9500.00)
    
    def test_order_sorting(self):
        """Test that orders are properly sorted by price."""
        # Add buy orders
        self.orderbook.add_order(side="buy", price=9000.00, quantity=1.0, order_id="bid1")
        self.orderbook.add_order(side="buy", price=9100.00, quantity=0.5, order_id="bid2")
        self.orderbook.add_order(side="buy", price=9050.00, quantity=2.0, order_id="bid3")
        
        # Add sell orders
        self.orderbook.add_order(side="sell", price=9500.00, quantity=1.0, order_id="ask1")
        self.orderbook.add_order(side="sell", price=9300.00, quantity=1.5, order_id="ask2")
        self.orderbook.add_order(side="sell", price=9400.00, quantity=0.75, order_id="ask3")
        
        # Get snapshot and verify sorting
        snapshot = self.orderbook.get_snapshot()
        
        # Bids should be sorted by price descending (highest first)
        bids = sorted(snapshot["bids"], key=lambda x: x["price"], reverse=True)
        self.assertEqual(bids[0]["price"], 9100.00)
        self.assertEqual(bids[1]["price"], 9050.00)
        self.assertEqual(bids[2]["price"], 9000.00)
        
        # Asks should be sorted by price ascending (lowest first)
        asks = sorted(snapshot["asks"], key=lambda x: x["price"])
        self.assertEqual(asks[0]["price"], 9300.00)
        self.assertEqual(asks[1]["price"], 9400.00)
        self.assertEqual(asks[2]["price"], 9500.00)


class TestOrderMatching(OrderBookTestCase):
    """Test order matching and execution."""
    
    def test_no_matching_with_spread(self):
        """Test that orders don't match when there's a spread."""
        # Add a buy order
        self.orderbook.add_order(side="buy", price=9000.00, quantity=1.0, order_id="bid1")
        
        # Add a sell order with a spread
        self.orderbook.add_order(side="sell", price=9500.00, quantity=1.0, order_id="ask1")
        
        # Verify no trades occurred
        trades = self.orderbook.get_trade_history()
        self.assertEqual(len(trades), 0)
        
        # Verify both orders are in the book
        snapshot = self.orderbook.get_snapshot()
        self.assertEqual(len(snapshot["bids"]), 1)
        self.assertEqual(len(snapshot["asks"]), 1)
    
    def test_market_buy_order(self):
        """Test a market buy order matches against the lowest ask."""
        # Add a sell order
        self.orderbook.add_order(side="sell", price=9500.00, quantity=1.0, order_id="ask1")
        
        # Add a market buy order that crosses the book
        order_id = self.orderbook.add_order(side="buy", price=10000.00, quantity=1.0, order_id="market_buy")
        
        # Verify the order was fully matched
        order = self.orderbook.get_order(order_id)
        self.assertIsNone(order)
        
        # Verify a trade was created
        trades = self.orderbook.get_trade_history()
        self.assertEqual(len(trades), 1)
        self.assertEqual(trades[0]["price"], 9500.00)
        self.assertEqual(trades[0]["quantity"], 1.0)
    
    def test_market_sell_order(self):
        """Test a market sell order matches against the highest bid."""
        # Add a buy order
        self.orderbook.add_order(side="buy", price=9000.00, quantity=1.0, order_id="bid1")
        
        # Add a market sell order that crosses the book
        order_id = self.orderbook.add_order(side="sell", price=8000.00, quantity=1.0, order_id="market_sell")
        
        # Verify the order was fully matched
        order = self.orderbook.get_order(order_id)
        self.assertIsNone(order)
        
        # Verify a trade was created
        trades = self.orderbook.get_trade_history()
        self.assertEqual(len(trades), 1)
        self.assertEqual(trades[0]["price"], 9000.00)
        self.assertEqual(trades[0]["quantity"], 1.0)
    
    def test_partial_fill(self):
        """Test partial order filling."""
        # Add a buy order
        self.orderbook.add_order(side="buy", price=9000.00, quantity=2.0, order_id="bid1")
        
        # Add a sell order with smaller quantity
        order_id = self.orderbook.add_order(side="sell", price=8000.00, quantity=1.0, order_id="partial_sell")
        
        # Verify the order was fully matched
        order = self.orderbook.get_order(order_id)
        self.assertIsNone(order)
        
        # Verify a trade was created
        trades = self.orderbook.get_trade_history()
        self.assertEqual(len(trades), 1)
        self.assertEqual(trades[0]["price"], 9000.00)
        self.assertEqual(trades[0]["quantity"], 1.0)
        
        # Verify the buy order is still in the book with reduced quantity
        snapshot = self.orderbook.get_snapshot()
        self.assertEqual(len(snapshot["bids"]), 1)
        self.assertEqual(snapshot["bids"][0]["quantity"], 1.0)


class TestOrderbookEdgeCases(OrderBookTestCase):
    """Test edge cases and potential issues in the orderbook."""
    
    def test_crossed_book_prevention(self):
        """Test that crossed books are prevented."""
        # Add initial orders
        self.orderbook.add_order(side="buy", price=9000.00, quantity=1.0, order_id="bid1")
        self.orderbook.add_order(side="sell", price=9500.00, quantity=1.0, order_id="ask1")
        
        # Try to add a buy order that would cross the book
        self.orderbook.add_order(side="buy", price=10000.00, quantity=0.5, order_id="crossing_bid")
        
        # Verify it was matched rather than creating a crossed book
        snapshot = self.orderbook.get_snapshot()
        best_bid = max(level["price"] for level in snapshot["bids"]) if snapshot["bids"] else 0
        best_ask = min(level["price"] for level in snapshot["asks"]) if snapshot["asks"] else float('inf')
        
        # The best bid should still be lower than the best ask
        self.assertLess(best_bid, best_ask)
        
        # Verify a trade was created
        trades = self.orderbook.get_trade_history()
        self.assertEqual(len(trades), 1)
        
    def test_fill_or_kill_orders(self):
        """Test fill-or-kill orders."""
        # Add some buy orders
        self.orderbook.add_order(side="buy", price=9000.0, quantity=1.0, order_id="buy1")
        self.orderbook.add_order(side="buy", price=9100.0, quantity=1.0, order_id="buy2")
        
        # Add some sell orders
        self.orderbook.add_order(side="sell", price=9500.0, quantity=1.0, order_id="sell1")
        self.orderbook.add_order(side="sell", price=9600.0, quantity=1.0, order_id="sell2")
        
        # Add a FOK buy order with price that isn't high enough to be fully filled
        order_id = self.orderbook.add_order(
            side="buy", 
            price=9400.0,  # Not high enough to match any sell orders
            quantity=1.0, 
            time_in_force="FOK"
        )
        
        # Should not have executed any trades
        trades = self.orderbook.get_trade_history()
        self.assertEqual(len(trades), 0, "FOK order should not execute any trades if it cannot be fully filled")
        
        # Order should not be in the book
        self.assertIsNone(self.orderbook.get_order(order_id))
        
        # Clear trade history before the next test
        self.orderbook.book_manager.clear_trade_history()
        
        # Now add a FOK buy order with price high enough to be fully filled
        order_id = self.orderbook.add_order(
            side="buy", 
            price=9600.0,  # High enough to match sell1
            quantity=1.0, 
            time_in_force="FOK"
        )
        
        # Should have executed one trade
        trades = self.orderbook.get_trade_history()
        print(f"Trade history after first FOK match: {trades}")
        self.assertEqual(len(trades), 1, "FOK order should execute trades if it can be fully filled")
        
        # Order should not be in the book (since it was fully filled)
        self.assertIsNone(self.orderbook.get_order(order_id))
        
        # Test a FOK order that requires multiple price levels to fill
        # Clear the orderbook first
        self.orderbook.clear()
        
        # Explicitly clear trade history to ensure we start fresh
        self.orderbook.book_manager.clear_trade_history()
        
        # Add orders at multiple price levels
        self.orderbook.add_order(side="sell", price=9500.0, quantity=0.5, order_id="sell1")
        self.orderbook.add_order(side="sell", price=9600.0, quantity=0.5, order_id="sell2")
        
        # Add a FOK order that needs both levels to fill
        order_id = self.orderbook.add_order(
            side="buy", 
            price=9600.0,
            quantity=1.0, 
            time_in_force="FOK"
        )
        
        # Should have executed two trades
        trades = self.orderbook.get_trade_history()
        print(f"Trade history after multiple-price FOK match: {trades}")
        self.assertEqual(len(trades), 2, "FOK order should match against multiple price levels if needed")
        
        # Order should not be in the book
        self.assertIsNone(self.orderbook.get_order(order_id))
    
    def test_multiple_price_levels(self):
        """Test matching against multiple price levels."""
        # Clear the orderbook first
        self.orderbook.clear()
        
        # Explicitly clear trade history
        self.orderbook.book_manager.clear_trade_history()
        
        # Add sell orders at multiple price levels
        self.orderbook.add_order(side="sell", price=9300.0, quantity=1.0, order_id="ask1")
        self.orderbook.add_order(side="sell", price=9400.0, quantity=2.0, order_id="ask2")
        self.orderbook.add_order(side="sell", price=9500.0, quantity=3.0, order_id="ask3")
        
        # Add a buy order that crosses multiple levels
        self.orderbook.add_order(side="buy", price=9400.0, quantity=3.0, order_id="bid1")
        
        # Should match against ask1 and ask2 completely
        trades = self.orderbook.get_trade_history()
        print(f"Trade history in multiple price levels test: {trades}")
        self.assertEqual(len(trades), 2, "Should have 2 trades (1.0 @ 9300, 2.0 @ 9400)")
        
        # Verify trade details
        self.assertEqual(trades[0]["price"], 9300.0)
        self.assertEqual(trades[0]["quantity"], 1.0)
        self.assertEqual(trades[1]["price"], 9400.0)
        self.assertEqual(trades[1]["quantity"], 2.0)
        
        # Only ask3 should remain in the book
        asks = self.orderbook.get_snapshot()["asks"]
        self.assertEqual(len(asks), 1)
        self.assertEqual(asks[0]["price"], 9500.0)
        self.assertEqual(asks[0]["quantity"], 3.0)
        
        # The bids should be empty (bid1 was fully matched)
        bids = self.orderbook.get_snapshot()["bids"]
        self.assertEqual(len(bids), 0)


if __name__ == "__main__":
    unittest.main() 