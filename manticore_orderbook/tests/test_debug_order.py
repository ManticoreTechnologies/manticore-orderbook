"""
Debug test for order book sorting.
"""

import unittest
from manticore_orderbook import OrderBook

class TestDebugOrderBookSorting(unittest.TestCase):
    """Debug test for order book sorting issue."""
    
    def test_debug_bid_sorting(self):
        """Debug the bid sorting issue."""
        orderbook = OrderBook(symbol="BTC/USD")
        
        print("\n--- DEBUGGING BID SORTING ---")
        
        print("Adding order buy1: price=10000.0")
        orderbook.add_order(side="buy", price=10000.0, quantity=1.0, order_id="buy1")
        print("Internal _bids list:", orderbook._bids)
        
        print("\nAdding order buy2: price=10200.0")
        orderbook.add_order(side="buy", price=10200.0, quantity=1.0, order_id="buy2")
        print("Internal _bids list:", orderbook._bids)
        
        print("\nAdding order buy3: price=9800.0")
        orderbook.add_order(side="buy", price=9800.0, quantity=1.0, order_id="buy3")
        print("Internal _bids list:", orderbook._bids)
        
        # Get snapshot
        snapshot = orderbook.get_snapshot()
        print("\nSnapshot bids:")
        for i, bid in enumerate(snapshot["bids"]):
            print(f"{i}: Price: {bid['price']}, Quantity: {bid['quantity']}")
        
        print("\nBid prices from snapshot:", [bid["price"] for bid in snapshot["bids"]])
        
        # This should now pass:
        bid_prices = [bid["price"] for bid in snapshot["bids"]]
        self.assertListEqual(bid_prices, [10200.0, 10000.0, 9800.0])

if __name__ == "__main__":
    unittest.main() 