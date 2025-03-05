from manticore_orderbook import OrderBook

if __name__ == "__main__":
    # Create a new order book
    orderbook = OrderBook(symbol="BTC/USD")
    
    print("Adding buy1: price=10000.0")
    orderbook.add_order(side="buy", price=10000.0, quantity=1.0, order_id="buy1")
    print("Internal _bids list after buy1:", orderbook._bids)
    
    print("\nAdding buy2: price=10200.0")
    orderbook.add_order(side="buy", price=10200.0, quantity=1.0, order_id="buy2")
    print("Internal _bids list after buy2:", orderbook._bids)
    
    print("\nAdding buy3: price=9800.0")
    orderbook.add_order(side="buy", price=9800.0, quantity=1.0, order_id="buy3")
    print("Internal _bids list after buy3:", orderbook._bids)
    
    # Get all bids and print them
    snapshot = orderbook.get_snapshot()
    print("\nFinal snapshot bids:")
    for i, bid in enumerate(snapshot["bids"]):
        print(f"{i}: Price: {bid['price']}, Quantity: {bid['quantity']}")
    
    # Check internal dictionaries
    print("\nBid orders dictionary keys:")
    for price in orderbook._bid_orders:
        print(f"Price {price} has {len(orderbook._bid_orders[price])} orders") 