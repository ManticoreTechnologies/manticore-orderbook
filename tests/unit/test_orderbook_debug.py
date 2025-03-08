#!/usr/bin/env python3
"""
Debug tests for the Manticore OrderBook.

These tests focus on specific edge cases and behaviors that were previously
isolated in separate test scripts. They're consolidated here as part of
the more structured test framework.
"""

import unittest
import logging
from manticore_orderbook import OrderBook, EventManager, EventType

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('orderbook_debug_test')


class OrderBookDebugTest(unittest.TestCase):
    """Debug tests for investigating specific orderbook behaviors."""
    
    def setUp(self):
        """Set up a new order book for each test."""
        self.orderbook = OrderBook(symbol="TEST")
    
    def test_bid_sorting(self):
        """Test that bids are sorted correctly with highest price first."""
        # Add buy orders with specific prices
        self.orderbook.add_order(side="buy", price=10000.0, quantity=1.0, order_id="buy1")
        self.orderbook.add_order(side="buy", price=10200.0, quantity=1.0, order_id="buy2")
        self.orderbook.add_order(side="buy", price=9800.0, quantity=1.0, order_id="buy3")
        
        # Verify the internal state has correct prices
        self.assertEqual(len(self.orderbook._bid_orders), 3)
        self.assertTrue(10000.0 in self.orderbook._bid_orders)
        self.assertTrue(10200.0 in self.orderbook._bid_orders)
        self.assertTrue(9800.0 in self.orderbook._bid_orders)
        
        # Get snapshot and verify bids are sorted correctly (highest first)
        snapshot = self.orderbook.get_snapshot()
        self.assertEqual(len(snapshot["bids"]), 3)
        
        # Extract bid prices from the snapshot
        bid_prices = [bid["price"] for bid in snapshot["bids"]]
        
        # Check sorting
        self.assertEqual(bid_prices[0], 10200.0, "Highest bid should be first")
        self.assertEqual(bid_prices[1], 10000.0, "Middle bid should be second")
        self.assertEqual(bid_prices[2], 9800.0, "Lowest bid should be third")
    
    def test_ask_sorting(self):
        """Test that asks are sorted correctly with lowest price first."""
        # Add sell orders with specific prices
        self.orderbook.add_order(side="sell", price=10300.0, quantity=1.0, order_id="sell1")
        self.orderbook.add_order(side="sell", price=10500.0, quantity=1.0, order_id="sell2")
        self.orderbook.add_order(side="sell", price=10100.0, quantity=1.0, order_id="sell3")
        
        # Verify the internal state has correct prices
        self.assertEqual(len(self.orderbook._ask_orders), 3)
        self.assertTrue(10300.0 in self.orderbook._ask_orders)
        self.assertTrue(10500.0 in self.orderbook._ask_orders)
        self.assertTrue(10100.0 in self.orderbook._ask_orders)
        
        # Get snapshot and verify asks are sorted correctly (lowest first)
        snapshot = self.orderbook.get_snapshot()
        self.assertEqual(len(snapshot["asks"]), 3)
        
        # Extract ask prices from the snapshot
        ask_prices = [ask["price"] for ask in snapshot["asks"]]
        
        # Check sorting
        self.assertEqual(ask_prices[0], 10100.0, "Lowest ask should be first")
        self.assertEqual(ask_prices[1], 10300.0, "Middle ask should be second")
        self.assertEqual(ask_prices[2], 10500.0, "Highest ask should be third")
    
    def test_snapshot_consistency(self):
        """Test that the snapshot correctly represents the orderbook state."""
        # Add buy orders with specific prices
        self.orderbook.add_order(side="buy", price=10000.0, quantity=1.0, order_id="buy1")
        self.orderbook.add_order(side="buy", price=10200.0, quantity=1.0, order_id="buy2")
        self.orderbook.add_order(side="buy", price=9800.0, quantity=1.0, order_id="buy3")
        
        # Add sell orders with specific prices
        self.orderbook.add_order(side="sell", price=10300.0, quantity=1.0, order_id="sell1")
        self.orderbook.add_order(side="sell", price=10500.0, quantity=1.0, order_id="sell2")
        self.orderbook.add_order(side="sell", price=10100.0, quantity=1.0, order_id="sell3")
        
        # Get snapshot
        snapshot = self.orderbook.get_snapshot()
        
        # Check all bid prices are in the snapshot
        for price in self.orderbook._bid_orders:
            found = any(bid["price"] == price for bid in snapshot["bids"])
            self.assertTrue(found, f"Price {price} should be in the snapshot bids")
        
        # Check all ask prices are in the snapshot
        for price in self.orderbook._ask_orders:
            found = any(ask["price"] == price for ask in snapshot["asks"])
            self.assertTrue(found, f"Price {price} should be in the snapshot asks")
        
        # Check bid quantities
        for price, orders in self.orderbook._bid_orders.items():
            expected_quantity = sum(order["quantity"] for order in orders.values())
            found = False
            for bid in snapshot["bids"]:
                if bid["price"] == price:
                    self.assertEqual(bid["quantity"], expected_quantity, 
                                   f"Quantity for price {price} should match")
                    found = True
            self.assertTrue(found, f"Price {price} should be in the snapshot bids")
        
        # Check ask quantities
        for price, orders in self.orderbook._ask_orders.items():
            expected_quantity = sum(order["quantity"] for order in orders.values())
            found = False
            for ask in snapshot["asks"]:
                if ask["price"] == price:
                    self.assertEqual(ask["quantity"], expected_quantity, 
                                   f"Quantity for price {price} should match")
                    found = True
            self.assertTrue(found, f"Price {price} should be in the snapshot asks")
    
    def test_price_level_removal(self):
        """Test that price levels are properly removed when all orders at that level are gone."""
        # Add an order
        self.orderbook.add_order(side="buy", price=10000.0, quantity=1.0, order_id="buy1")
        
        # Verify the price level exists
        self.assertTrue(10000.0 in self.orderbook._bid_orders)
        self.assertTrue(10000.0 in self.orderbook._bids)
        
        # Cancel the order
        self.orderbook.cancel_order("buy1")
        
        # Verify the price level was removed
        self.assertFalse(10000.0 in self.orderbook._bid_orders)
        self.assertFalse(10000.0 in self.orderbook._bids)
    
    def test_partial_fill_price_level_preservation(self):
        """Test that price levels are preserved when orders are partially filled."""
        # Add orders
        self.orderbook.add_order(side="buy", price=10000.0, quantity=2.0, order_id="buy1")
        
        # Add a matching order that will partially fill
        self.orderbook.add_order(side="sell", price=10000.0, quantity=1.0, order_id="sell1")
        
        # Verify the price level still exists
        self.assertTrue(10000.0 in self.orderbook._bid_orders)
        self.assertTrue(10000.0 in self.orderbook._bids)
        
        # Verify the order was partially filled
        order = self.orderbook.get_order("buy1")
        self.assertEqual(order["quantity"], 1.0)
    
    def test_complete_fill_price_level_removal(self):
        """Test that price levels are removed when orders are completely filled."""
        # Add a buy order
        self.orderbook.add_order(side="buy", price=10000.0, quantity=1.0, order_id="buy1")
        
        # Verify the price level exists
        snapshot = self.orderbook.get_snapshot()
        self.assertEqual(len(snapshot["bids"]), 1)
        self.assertEqual(snapshot["bids"][0]["price"], 10000.0)
        
        # Add a matching sell order that will completely fill the buy order
        self.orderbook.add_order(side="sell", price=10000.0, quantity=1.0, order_id="sell1")
        
        # Verify the buy order was completely filled and removed
        order = self.orderbook.get_order("buy1")
        self.assertIsNone(order, "Completely filled orders should be removed from the orderbook")
        
        # Verify the price level was removed
        snapshot = self.orderbook.get_snapshot()
        self.assertEqual(len(snapshot["bids"]), 0, "Price level should be removed when all orders are filled")


if __name__ == "__main__":
    unittest.main() 