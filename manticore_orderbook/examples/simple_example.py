"""
Simple example showing how to use the Manticore OrderBook library.
"""

from manticore_orderbook import OrderBook

def main():
    """Run a simple order book example."""
    # Create an order book
    print("Creating order book for BTC/USD...")
    orderbook = OrderBook(symbol="BTC/USD")
    
    # Add some buy orders
    print("\nAdding buy orders...")
    orderbook.add_order(side="buy", price=19500.0, quantity=1.5, order_id="bid1")
    orderbook.add_order(side="buy", price=19400.0, quantity=2.0, order_id="bid2")
    orderbook.add_order(side="buy", price=19550.0, quantity=1.0, order_id="bid3")
    
    # Add some sell orders
    print("Adding sell orders...")
    orderbook.add_order(side="sell", price=19600.0, quantity=1.0, order_id="ask1")
    orderbook.add_order(side="sell", price=19650.0, quantity=2.0, order_id="ask2")
    
    # Display the initial state of the order book
    print("\nInitial Order Book:")
    snapshot = orderbook.get_snapshot()
    print_snapshot(snapshot)
    
    # Modify an order
    print("\nModifying bid3 to price=19580.0, quantity=1.2...")
    orderbook.modify_order("bid3", new_price=19580.0, new_quantity=1.2)
    
    # Display the order book after modification
    print("\nOrder Book after modification:")
    snapshot = orderbook.get_snapshot()
    print_snapshot(snapshot)
    
    # Add a matching order that crosses the spread
    print("\nAdding a sell order that crosses with the highest bid...")
    orderbook.add_order(side="sell", price=19500.0, quantity=0.5, order_id="matching_ask")
    
    # Display the order book after matching
    print("\nOrder Book after matching:")
    snapshot = orderbook.get_snapshot()
    print_snapshot(snapshot)
    
    # Display trade history
    print("\nTrade History:")
    trades = orderbook.get_trade_history()
    for trade in trades:
        print(f"Trade: {trade['quantity']} @ {trade['price']} "
              f"(Maker: {trade['maker_order_id']}, Taker: {trade['taker_order_id']})")
    
    # Cancel an order
    print("\nCancelling bid2...")
    orderbook.cancel_order("bid2")
    
    # Display the final state of the order book
    print("\nFinal Order Book:")
    snapshot = orderbook.get_snapshot()
    print_snapshot(snapshot)


def print_snapshot(snapshot):
    """Pretty print an order book snapshot."""
    print("Bids (Buy Orders):")
    for bid in snapshot["bids"]:
        print(f"  {bid['quantity']} @ {bid['price']} ({bid['order_count']} orders)")
    
    print("Asks (Sell Orders):")
    for ask in snapshot["asks"]:
        print(f"  {ask['quantity']} @ {ask['price']} ({ask['order_count']} orders)")


if __name__ == "__main__":
    main() 