"""
Isolated test script to debug the OrderBook issue.
"""

from manticore_orderbook import OrderBook

def test_bid_sorting():
    """Test bid sorting in isolation."""
    print("Creating a new OrderBook instance")
    orderbook = OrderBook(symbol="TEST")
    
    print("\nAdding buy1: price=10000.0")
    orderbook.add_order(side="buy", price=10000.0, quantity=1.0, order_id="buy1")
    print("Internal _bids:", orderbook._bids)
    print("Bid orders:", {p: list(orders.keys()) for p, orders in orderbook._bid_orders.items()})
    
    print("\nAdding buy2: price=10200.0")
    orderbook.add_order(side="buy", price=10200.0, quantity=1.0, order_id="buy2")
    print("Internal _bids:", orderbook._bids)
    print("Bid orders:", {p: list(orders.keys()) for p, orders in orderbook._bid_orders.items()})
    
    print("\nAdding buy3: price=9800.0")
    orderbook.add_order(side="buy", price=9800.0, quantity=1.0, order_id="buy3")
    print("Internal _bids:", orderbook._bids)
    print("Bid orders:", {p: list(orders.keys()) for p, orders in orderbook._bid_orders.items()})
    
    print("\nGetting snapshot")
    snapshot = orderbook.get_snapshot()
    print("Snapshot bids:", snapshot["bids"])
    print("Bid prices from snapshot:", [bid["price"] for bid in snapshot["bids"]])
    
    # Check if all prices in _bids are in the snapshot
    print("\nChecking if all prices in _bids are in the snapshot:")
    for price in orderbook._bids:
        found = any(bid["price"] == price for bid in snapshot["bids"])
        print(f"Price {price} in snapshot: {found}")
    
    # Check if all prices in _bid_orders are in the snapshot
    print("\nChecking if all prices in _bid_orders are in the snapshot:")
    for price in orderbook._bid_orders:
        found = any(bid["price"] == price for bid in snapshot["bids"])
        print(f"Price {price} in snapshot: {found}")

if __name__ == "__main__":
    test_bid_sorting() 