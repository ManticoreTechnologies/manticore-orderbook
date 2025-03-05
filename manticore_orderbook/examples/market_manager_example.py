"""
Example demonstrating MarketManager functionality with multiple markets and Time-In-Force orders.
"""

import time
import logging
from datetime import datetime, timedelta

from manticore_orderbook.market_manager import MarketManager
from manticore_orderbook.models import TimeInForce

# Configure logging
logging.basicConfig(level=logging.INFO)

def print_separator(title):
    """Print a section separator with title."""
    print("\n" + "=" * 80)
    print(f" {title} ".center(80, "="))
    print("=" * 80 + "\n")

def main():
    """Run the multi-market example."""
    # Initialize market manager
    manager = MarketManager(enable_logging=True)
    
    print_separator("CREATING MARKETS")
    
    # Create multiple markets (trading pairs)
    btc_usd = manager.create_market(
        symbol="BTC/USD", 
        maker_fee_rate=0.001,  # 0.1% maker fee
        taker_fee_rate=0.002,  # 0.2% taker fee
        enable_price_improvement=True
    )
    
    eth_usd = manager.create_market(
        symbol="ETH/USD",
        maker_fee_rate=0.0015,  # 0.15% maker fee
        taker_fee_rate=0.0025,  # 0.25% taker fee
        enable_price_improvement=True
    )
    
    ltc_usd = manager.create_market(
        symbol="LTC/USD",
        maker_fee_rate=0.002,  # 0.2% maker fee
        taker_fee_rate=0.003,  # 0.3% taker fee
        enable_price_improvement=False
    )
    
    # List all markets
    markets = manager.list_markets()
    print(f"Available markets: {', '.join(markets)}")
    
    # GOOD TILL CANCELLED (GTC) ORDERS EXAMPLE
    print_separator("GOOD TILL CANCELLED (GTC) ORDERS")
    
    # Add some GTC orders to BTC/USD market
    print("Adding GTC orders to BTC/USD market...")
    
    # Place bid orders
    user1_bid1 = manager.place_order(
        symbol="BTC/USD",
        side="buy",
        price=48000.0,
        quantity=1.5,
        user_id="user1",
        time_in_force="GTC"  # Good Till Cancelled (default)
    )
    
    user2_bid1 = manager.place_order(
        symbol="BTC/USD",
        side="buy",
        price=47800.0,
        quantity=2.0,
        user_id="user2",
        time_in_force="GTC"
    )
    
    # Place ask orders
    user3_ask1 = manager.place_order(
        symbol="BTC/USD",
        side="sell",
        price=49000.0,
        quantity=1.0,
        user_id="user3",
        time_in_force="GTC"
    )
    
    user4_ask1 = manager.place_order(
        symbol="BTC/USD",
        side="sell",
        price=49200.0,
        quantity=2.0,
        user_id="user4",
        time_in_force="GTC"
    )
    
    # Get BTC/USD order book snapshot
    btc_snapshot = manager.get_market_snapshot("BTC/USD")
    print("\nBTC/USD Order Book:")
    print("Bids:")
    for bid in btc_snapshot["bids"]:
        print(f"  ${bid['price']:.2f}: {bid['quantity']:.4f} BTC ({bid['order_count']} orders)")
    
    print("Asks:")
    for ask in btc_snapshot["asks"]:
        print(f"  ${ask['price']:.2f}: {ask['quantity']:.4f} BTC ({ask['order_count']} orders)")
    
    # Add orders to ETH/USD market
    print("\nAdding orders to ETH/USD market...")
    
    # Place bid orders
    manager.place_order(
        symbol="ETH/USD",
        side="buy",
        price=3200.0,
        quantity=10.0,
        user_id="user1",
        time_in_force="GTC"
    )
    
    manager.place_order(
        symbol="ETH/USD",
        side="buy",
        price=3150.0,
        quantity=15.0,
        user_id="user5",
        time_in_force="GTC"
    )
    
    # Place ask orders
    manager.place_order(
        symbol="ETH/USD",
        side="sell",
        price=3250.0,
        quantity=8.0,
        user_id="user2",
        time_in_force="GTC"
    )
    
    manager.place_order(
        symbol="ETH/USD",
        side="sell",
        price=3300.0,
        quantity=12.0,
        user_id="user3",
        time_in_force="GTC"
    )
    
    # Get ETH/USD order book snapshot
    eth_snapshot = manager.get_market_snapshot("ETH/USD")
    print("\nETH/USD Order Book:")
    print("Bids:")
    for bid in eth_snapshot["bids"]:
        print(f"  ${bid['price']:.2f}: {bid['quantity']:.4f} ETH ({bid['order_count']} orders)")
    
    print("Asks:")
    for ask in eth_snapshot["asks"]:
        print(f"  ${ask['price']:.2f}: {ask['quantity']:.4f} ETH ({ask['order_count']} orders)")
    
    # IMMEDIATE OR CANCEL (IOC) ORDERS EXAMPLE
    print_separator("IMMEDIATE OR CANCEL (IOC) ORDERS")
    
    print("Placing IOC orders that will partially match...")
    
    # IOC order that will partially match against the order book
    ioc_order_id = manager.place_order(
        symbol="BTC/USD",
        side="buy",
        price=49100.0,  # Above the best ask price
        quantity=1.5,    # More than available at best ask
        user_id="user5",
        time_in_force="IOC"  # Immediate Or Cancel
    )
    
    print(f"IOC order {ioc_order_id} executed")
    
    # Check the order book after IOC order
    btc_snapshot = manager.get_market_snapshot("BTC/USD")
    print("\nBTC/USD Order Book after IOC order:")
    print("Bids:")
    for bid in btc_snapshot["bids"]:
        print(f"  ${bid['price']:.2f}: {bid['quantity']:.4f} BTC ({bid['order_count']} orders)")
    
    print("Asks:")
    for ask in btc_snapshot["asks"]:
        print(f"  ${ask['price']:.2f}: {ask['quantity']:.4f} BTC ({ask['order_count']} orders)")
    
    # FILL OR KILL (FOK) ORDERS EXAMPLE
    print_separator("FILL OR KILL (FOK) ORDERS")
    
    print("Placing FOK order that will not fully match (and thus be cancelled)...")
    
    # FOK order that won't fully match
    fok_order_id = manager.place_order(
        symbol="BTC/USD",
        side="buy",
        price=49300.0,  # Above all ask prices
        quantity=3.0,    # More than total available quantity
        user_id="user6",
        time_in_force="FOK"  # Fill Or Kill
    )
    
    print(f"FOK order {fok_order_id} was not fully matched, so it was cancelled")
    
    # Check the order book (should be unchanged)
    btc_snapshot = manager.get_market_snapshot("BTC/USD")
    print("\nBTC/USD Order Book (unchanged after FOK):")
    print("Asks:")
    for ask in btc_snapshot["asks"]:
        print(f"  ${ask['price']:.2f}: {ask['quantity']:.4f} BTC ({ask['order_count']} orders)")
    
    # GOOD TILL DATE (GTD) ORDERS EXAMPLE
    print_separator("GOOD TILL DATE (GTD) ORDERS")
    
    # Set expiry time 5 seconds from now
    expiry_time = time.time() + 5
    expiry_str = datetime.fromtimestamp(expiry_time).strftime("%H:%M:%S")
    
    print(f"Placing GTD order that expires at {expiry_str} (5 seconds from now)...")
    
    # GTD order that will expire
    gtd_order_id = manager.place_order(
        symbol="LTC/USD",
        side="buy",
        price=65.0,
        quantity=50.0,
        user_id="user7",
        time_in_force="GTD",  # Good Till Date
        expiry_time=expiry_time
    )
    
    print(f"GTD order {gtd_order_id} placed and will expire in 5 seconds")
    
    # Get LTC/USD order book snapshot
    ltc_snapshot = manager.get_market_snapshot("LTC/USD")
    print("\nLTC/USD Order Book with GTD order:")
    print("Bids:")
    for bid in ltc_snapshot["bids"]:
        print(f"  ${bid['price']:.2f}: {bid['quantity']:.4f} LTC ({bid['order_count']} orders)")
    
    # Wait for expiry
    print("\nWaiting for GTD order to expire...")
    time.sleep(6)  # Wait 6 seconds to ensure expiry
    
    # Manually clean expired orders
    expired_count = manager.clean_expired_orders()
    print(f"Expired orders cleaned: {expired_count}")
    
    # Check LTC/USD order book again
    ltc_snapshot = manager.get_market_snapshot("LTC/USD")
    print("\nLTC/USD Order Book after GTD order expired:")
    print("Bids:")
    if ltc_snapshot["bids"]:
        for bid in ltc_snapshot["bids"]:
            print(f"  ${bid['price']:.2f}: {bid['quantity']:.4f} LTC ({bid['order_count']} orders)")
    else:
        print("  (No bids)")
    
    # USER OPERATIONS
    print_separator("USER OPERATIONS")
    
    # Get all orders for a user
    user1_orders = manager.get_user_orders("user1")
    print(f"User1 has {len(user1_orders)} active orders:")
    for order in user1_orders:
        print(f"  {order['order_id']} - {order['symbol']}: {order['side']} {order['quantity']} @ ${order['price']}")
    
    # OVERALL STATISTICS
    print_separator("OVERALL STATISTICS")
    
    # Get statistics
    stats = manager.get_statistics()
    print(f"Total markets: {stats['total_markets']}")
    print(f"Total orders: {stats['total_orders']}")
    print(f"Total users: {stats['total_users']}")
    
    print("\nMarket statistics:")
    for symbol, market_stats in stats['markets'].items():
        print(f"\n{symbol}:")
        print(f"  Orders added: {market_stats['num_orders_added']}")
        print(f"  Orders cancelled: {market_stats['num_orders_cancelled']}")
        print(f"  Trades executed: {market_stats['num_trades_executed']}")
        if 'total_volume_traded' in market_stats:
            print(f"  Total volume traded: {market_stats['total_volume_traded']}")
        if 'bid_levels' in market_stats and 'ask_levels' in market_stats:
            print(f"  Bid levels: {market_stats['bid_levels']}")
            print(f"  Ask levels: {market_stats['ask_levels']}")
    
    # LATENCY STATISTICS
    print_separator("LATENCY METRICS")
    
    # Get latency statistics for BTC/USD market
    latency_stats = btc_usd.get_latency_stats()
    
    print("BTC/USD Market Latency Metrics:")
    for operation, metrics in latency_stats.items():
        if metrics.get('count', 0) > 0:
            print(f"\n{operation}:")
            print(f"  Count: {metrics.get('count', 0)}")
            if 'mean' in metrics:
                print(f"  Mean: {metrics['mean'] * 1000:.4f} ms")
            if 'p50' in metrics:
                print(f"  Median: {metrics['p50'] * 1000:.4f} ms")
            if 'p90' in metrics:
                print(f"  90th percentile: {metrics['p90'] * 1000:.4f} ms")
            if 'min' in metrics and 'max' in metrics:
                print(f"  Min/Max: {metrics['min'] * 1000:.4f} ms / {metrics['max'] * 1000:.4f} ms")

if __name__ == "__main__":
    main() 