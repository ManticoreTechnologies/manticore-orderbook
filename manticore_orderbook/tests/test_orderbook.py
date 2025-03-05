"""
Tests for the OrderBook implementation.
"""

import unittest
import time
from manticore_orderbook import OrderBook


class TestOrderBook(unittest.TestCase):
    """Tests for the OrderBook class."""
    
    def setUp(self):
        """Set up a new order book for each test."""
        self.orderbook = OrderBook(symbol="BTC/USD")
    
    def test_add_order(self):
        """Test adding orders to the book."""
        # Add a buy order
        order_id = self.orderbook.add_order(side="buy", price=10000.0, quantity=1.0)
        self.assertIsNotNone(order_id)
        
        # Add a sell order
        order_id = self.orderbook.add_order(side="sell", price=10100.0, quantity=2.0)
        self.assertIsNotNone(order_id)
        
        # Get snapshot and verify
        snapshot = self.orderbook.get_snapshot()
        self.assertEqual(len(snapshot["bids"]), 1)
        self.assertEqual(len(snapshot["asks"]), 1)
        
        self.assertEqual(snapshot["bids"][0]["price"], 10000.0)
        self.assertEqual(snapshot["bids"][0]["quantity"], 1.0)
        
        self.assertEqual(snapshot["asks"][0]["price"], 10100.0)
        self.assertEqual(snapshot["asks"][0]["quantity"], 2.0)
    
    def test_cancel_order(self):
        """Test cancelling orders from the book."""
        # Add orders
        bid_id = self.orderbook.add_order(side="buy", price=10000.0, quantity=1.0)
        ask_id = self.orderbook.add_order(side="sell", price=10100.0, quantity=2.0)
        
        # Cancel bid
        result = self.orderbook.cancel_order(bid_id)
        self.assertTrue(result)
        
        # Get snapshot and verify bid is gone
        snapshot = self.orderbook.get_snapshot()
        self.assertEqual(len(snapshot["bids"]), 0)
        self.assertEqual(len(snapshot["asks"]), 1)
        
        # Try to cancel non-existent order
        result = self.orderbook.cancel_order("non-existent")
        self.assertFalse(result)
    
    def test_modify_order(self):
        """Test modifying orders in the book."""
        # Add an order
        order_id = self.orderbook.add_order(side="buy", price=10000.0, quantity=1.0)
        
        # Modify quantity
        result = self.orderbook.modify_order(order_id, new_quantity=2.0)
        self.assertTrue(result)
        
        # Get snapshot and verify
        snapshot = self.orderbook.get_snapshot()
        self.assertEqual(snapshot["bids"][0]["quantity"], 2.0)
        
        # Modify price
        result = self.orderbook.modify_order(order_id, new_price=10050.0)
        self.assertTrue(result)
        
        # Get snapshot and verify
        snapshot = self.orderbook.get_snapshot()
        self.assertEqual(snapshot["bids"][0]["price"], 10050.0)
        
        # Modify both price and quantity
        result = self.orderbook.modify_order(order_id, new_price=10100.0, new_quantity=3.0)
        self.assertTrue(result)
        
        # Get snapshot and verify
        snapshot = self.orderbook.get_snapshot()
        self.assertEqual(snapshot["bids"][0]["price"], 10100.0)
        self.assertEqual(snapshot["bids"][0]["quantity"], 3.0)
    
    def test_order_matching(self):
        """Test that orders are matched correctly."""
        # Add a buy order
        self.orderbook.add_order(side="buy", price=10000.0, quantity=1.0, order_id="buy1")
        
        # Add a matching sell order
        self.orderbook.add_order(side="sell", price=10000.0, quantity=0.5, order_id="sell1")
        
        # Check that the buy order is partially filled
        snapshot = self.orderbook.get_snapshot()
        self.assertEqual(len(snapshot["bids"]), 1)
        self.assertEqual(snapshot["bids"][0]["quantity"], 0.5)
        self.assertEqual(len(snapshot["asks"]), 0)  # Sell order fully filled
        
        # Check trade history
        trades = self.orderbook.get_trade_history()
        self.assertEqual(len(trades), 1)
        self.assertEqual(trades[0]["quantity"], 0.5)
        self.assertEqual(trades[0]["price"], 10000.0)
        
        # Add another sell order that crosses
        self.orderbook.add_order(side="sell", price=9900.0, quantity=1.0, order_id="sell2")
        
        # Check that the buy order is fully filled
        snapshot = self.orderbook.get_snapshot()
        self.assertEqual(len(snapshot["bids"]), 0)  # Buy order fully filled
        self.assertEqual(len(snapshot["asks"]), 1)  # Sell order partially filled
        self.assertEqual(snapshot["asks"][0]["quantity"], 0.5)
        
        # Check updated trade history
        trades = self.orderbook.get_trade_history()
        self.assertEqual(len(trades), 2)
    
    def test_price_time_priority(self):
        """Test that orders are executed in price-time priority."""
        # Add buy orders at same price but different times
        self.orderbook.add_order(side="buy", price=10000.0, quantity=1.0, order_id="buy1")
        self.orderbook.add_order(side="buy", price=10000.0, quantity=1.0, order_id="buy2")
        
        # Add buy order at better price
        self.orderbook.add_order(side="buy", price=10100.0, quantity=1.0, order_id="buy3")
        
        # Add a crossing sell order
        self.orderbook.add_order(side="sell", price=9000.0, quantity=2.5, order_id="sell1")
        
        # Check trades (should be buy3, buy1, buy2 in that order)
        trades = self.orderbook.get_trade_history()
        self.assertEqual(len(trades), 3)
        self.assertEqual(trades[2]["maker_order_id"], "buy3")  # Best price first
        self.assertEqual(trades[1]["maker_order_id"], "buy1")  # Then oldest at same price
        self.assertEqual(trades[0]["maker_order_id"], "buy2")  # Then youngest at same price
    
    def test_get_snapshot_depth(self):
        """Test getting a snapshot with limited depth."""
        # Add multiple orders at different prices
        for i in range(5):
            self.orderbook.add_order(side="buy", price=10000.0 - i*100, quantity=1.0)
            self.orderbook.add_order(side="sell", price=10100.0 + i*100, quantity=1.0)
        
        # Get snapshot with depth=3
        snapshot = self.orderbook.get_snapshot(depth=3)
        self.assertEqual(len(snapshot["bids"]), 3)
        self.assertEqual(len(snapshot["asks"]), 3)
        
        # Verify highest bids and lowest asks are included
        self.assertEqual(snapshot["bids"][0]["price"], 10000.0)
        self.assertEqual(snapshot["bids"][1]["price"], 9900.0)
        self.assertEqual(snapshot["bids"][2]["price"], 9800.0)
        
        self.assertEqual(snapshot["asks"][0]["price"], 10100.0)
        self.assertEqual(snapshot["asks"][1]["price"], 10200.0)
        self.assertEqual(snapshot["asks"][2]["price"], 10300.0)
    
    def test_bids_asks_sorted_correctly(self):
        """Test that bids and asks are sorted correctly."""
        # Create a separate test for bid sorting
        self._test_bid_sorting()
        
        # Create a separate test for ask sorting
        self._test_ask_sorting()
    
    def _test_bid_sorting(self):
        """Test that bids are sorted correctly (highest first)."""
        # Create a fresh order book
        orderbook = OrderBook(symbol="TEST")
        
        # Add buy orders with specific prices
        orderbook.add_order(side="buy", price=10000.0, quantity=1.0, order_id="buy1")
        orderbook.add_order(side="buy", price=10200.0, quantity=1.0, order_id="buy2")
        orderbook.add_order(side="buy", price=9800.0, quantity=1.0, order_id="buy3")
        
        # Verify the internal state
        self.assertEqual(len(orderbook._bid_orders), 3)
        self.assertTrue("buy1" in orderbook._bid_orders[10000.0])
        self.assertTrue("buy2" in orderbook._bid_orders[10200.0])
        self.assertTrue("buy3" in orderbook._bid_orders[9800.0])
        
        # Create a manual snapshot
        sorted_bids = sorted(orderbook._bid_orders.keys(), reverse=True)
        manual_snapshot = []
        for price in sorted_bids:
            orders = orderbook._bid_orders[price]
            if orders:
                total_quantity = sum(order.quantity for order in orders.values())
                manual_snapshot.append({
                    "price": price,
                    "quantity": total_quantity,
                    "order_count": len(orders)
                })
        
        # Verify the manual snapshot
        self.assertEqual(len(manual_snapshot), 3)
        self.assertEqual(manual_snapshot[0]["price"], 10200.0)
        self.assertEqual(manual_snapshot[1]["price"], 10000.0)
        self.assertEqual(manual_snapshot[2]["price"], 9800.0)
    
    def _test_ask_sorting(self):
        """Test that asks are sorted correctly (lowest first)."""
        # Create a fresh order book
        orderbook = OrderBook(symbol="TEST")
        
        # Add sell orders with specific prices
        orderbook.add_order(side="sell", price=10300.0, quantity=1.0, order_id="ask1")
        orderbook.add_order(side="sell", price=10500.0, quantity=1.0, order_id="ask2")
        orderbook.add_order(side="sell", price=10100.0, quantity=1.0, order_id="ask3")
        
        # Verify the internal state
        self.assertEqual(len(orderbook._ask_orders), 3)
        self.assertTrue("ask1" in orderbook._ask_orders[10300.0])
        self.assertTrue("ask2" in orderbook._ask_orders[10500.0])
        self.assertTrue("ask3" in orderbook._ask_orders[10100.0])
        
        # Create a manual snapshot
        sorted_asks = sorted(orderbook._ask_orders.keys())
        manual_snapshot = []
        for price in sorted_asks:
            orders = orderbook._ask_orders[price]
            if orders:
                total_quantity = sum(order.quantity for order in orders.values())
                manual_snapshot.append({
                    "price": price,
                    "quantity": total_quantity,
                    "order_count": len(orders)
                })
        
        # Verify the manual snapshot
        self.assertEqual(len(manual_snapshot), 3)
        self.assertEqual(manual_snapshot[0]["price"], 10100.0)
        self.assertEqual(manual_snapshot[1]["price"], 10300.0)
        self.assertEqual(manual_snapshot[2]["price"], 10500.0)


if __name__ == "__main__":
    unittest.main() 