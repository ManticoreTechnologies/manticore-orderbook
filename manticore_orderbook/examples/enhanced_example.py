#!/usr/bin/env python3
"""
Enhanced example demonstrating the advanced features of the Manticore OrderBook.

This example shows:
1. Creating an order book with price improvement and fees
2. Adding orders using both individual and batch methods
3. Using efficient depth queries and snapshots
4. Price-time priority matching with price improvement
5. Atomic order modifications
6. Retrieving detailed statistics and trade history
"""

import time
import random
from pprint import pprint
from manticore_orderbook.orderbook import OrderBook

def run_enhanced_example():
    """Run a comprehensive example of the OrderBook's features."""
    print("\n=== Manticore OrderBook Enhanced Example ===\n")
    
    # Create an order book with price improvement and fees
    print("Creating OrderBook with price improvement and fees...")
    book = OrderBook(
        symbol="BTC/USD",
        enable_price_improvement=True,
        maker_fee_rate=0.001,  # 0.1% maker fee
        taker_fee_rate=0.002,  # 0.2% taker fee
        enable_logging=True,
        log_level=20  # INFO level
    )
    
    # Add some limit orders
    print("\nAdding limit orders...")
    book.add_order("buy", 19950.0, 1.0, "bid1")
    book.add_order("buy", 19900.0, 2.0, "bid2")
    book.add_order("buy", 19850.0, 3.0, "bid3")
    book.add_order("sell", 20050.0, 1.5, "ask1")
    book.add_order("sell", 20100.0, 2.5, "ask2")
    book.add_order("sell", 20150.0, 3.5, "ask3")
    
    # Get current order book snapshot
    print("\nCurrent order book snapshot:")
    snapshot = book.get_snapshot(depth=5)
    print("Bids:")
    for bid in snapshot["bids"]:
        print(f"  {bid['price']}: {bid['quantity']} ({bid['order_count']} orders)")
    
    print("Asks:")
    for ask in snapshot["asks"]:
        print(f"  {ask['price']}: {ask['quantity']} ({ask['order_count']} orders)")
    
    # Get best bid/ask
    best_bid_ask = book.get_best_bid_ask() if hasattr(book, 'get_best_bid_ask') else None
    if best_bid_ask:
        print(f"Best bid: {best_bid_ask['bid_price']} ({best_bid_ask['bid_quantity']})")
        print(f"Best ask: {best_bid_ask['ask_price']} ({best_bid_ask['ask_quantity']})")
        print(f"Spread: {best_bid_ask['spread']}")
    
    # Demonstrate batch order insertion
    print("\nAdding batch of orders...")
    batch_orders = [
        {"side": "buy", "price": 19925.0, "quantity": 0.5},
        {"side": "buy", "price": 19875.0, "quantity": 1.5},
        {"side": "sell", "price": 20075.0, "quantity": 0.75},
        {"side": "sell", "price": 20125.0, "quantity": 1.75}
    ]
    batch_order_ids = book.batch_add_orders(batch_orders)
    print(f"Added {len(batch_order_ids)} orders in batch")
    
    # Show updated snapshot
    print("\nUpdated order book snapshot:")
    snapshot = book.get_snapshot(depth=5)
    print("Bids:")
    for bid in snapshot["bids"]:
        print(f"  {bid['price']}: {bid['quantity']} ({bid['order_count']} orders)")
    
    print("Asks:")
    for ask in snapshot["asks"]:
        print(f"  {ask['price']}: {ask['quantity']} ({ask['order_count']} orders)")
    
    # Demonstrate order modification
    print("\nModifying an order...")
    book.modify_order("bid1", new_price=19975.0, new_quantity=1.2)
    print("Modified bid1: price=19950.0 -> 19975.0, quantity=1.0 -> 1.2")
    
    # Show order info
    print("\nOrder information for bid1:")
    bid1_info = book.get_order("bid1")
    if bid1_info:
        pprint(bid1_info)
    
    # Add a matching order to trigger a trade with price improvement
    print("\nAdding a market sell order to trigger price improvement...")
    market_order_id = book.add_order("sell", 19900.0, 0.5, "market_sell")
    
    # Show trades
    print("\nTrade history:")
    trades = book.get_trade_history(limit=5)
    for trade in trades:
        print(f"  {trade['quantity']} @ {trade['price']} (Maker: {trade['maker_order_id']}, Taker: {trade['taker_order_id']})")
        print(f"  Maker fee: {trade['maker_fee']}, Taker fee: {trade['taker_fee']}")
        print(f"  Total value: {trade['value']}")
    
    # Get statistics
    print("\nOrder book statistics:")
    stats = book.get_statistics()
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    # Demonstrate depth queries
    print("\nDepth queries:")
    top_bid_depth = book.get_order_depth_at_price("buy", 19975.0)
    print(f"Depth at top bid (19975.0): {top_bid_depth}")
    
    top_ask_depth = book.get_order_depth_at_price("sell", 20050.0)
    print(f"Depth at top ask (20050.0): {top_ask_depth}")
    
    print("\nExample complete.")

if __name__ == "__main__":
    run_enhanced_example() 