"""
Test script to verify the snapshot issue.
"""

from manticore_orderbook import OrderBook

def test_snapshot():
    """Test the snapshot functionality."""
    # Create a new order book
    orderbook = OrderBook(symbol="TEST")
    
    # Add buy orders
    orderbook.add_order(side="buy", price=10000.0, quantity=1.0, order_id="buy1")
    orderbook.add_order(side="buy", price=10200.0, quantity=1.0, order_id="buy2")
    orderbook.add_order(side="buy", price=9800.0, quantity=1.0, order_id="buy3")
    
    # Print internal state
    print("Internal _bids:", orderbook._bids)
    print("Bid orders:", {p: list(orders.keys()) for p, orders in orderbook._bid_orders.items()})
    
    # Get snapshot
    snapshot = orderbook.get_snapshot()
    print("\nSnapshot bids:", snapshot["bids"])
    
    # Print the sorted bid orders keys
    sorted_bids = sorted(orderbook._bid_orders.keys(), reverse=True)
    print("\nSorted bid orders keys:", sorted_bids)
    
    # Manually create a snapshot
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
    
    print("\nManual snapshot:", manual_snapshot)

if __name__ == "__main__":
    test_snapshot() 