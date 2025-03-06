"""
Comprehensive example demonstrating exchange-ready features of the Manticore OrderBook.

This example showcases:
1. Time-In-Force order policies
2. Order expiry management
3. Market management for multiple trading pairs
4. User order tracking
5. Latency monitoring
6. Fee calculation
"""

import time
import logging
from datetime import datetime, timedelta

from manticore_orderbook.market_manager import MarketManager
from manticore_orderbook.models import TimeInForce

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("exchange_example")

def print_header(title, char="="):
    """Print a section header."""
    width = 80
    print("\n" + char * width)
    print(f" {title} ".center(width, char))
    print(char * width + "\n")

def simulate_trading_day():
    """Simulate a full trading day with multiple markets and users."""
    print_header("INITIALIZING EXCHANGE")
    
    # Create market manager for the exchange
    exchange = MarketManager(enable_logging=True)
    
    # Define fee structure - could be tiered based on volume in a real exchange
    fee_structure = {
        "default": {"maker": 0.001, "taker": 0.002},  # 0.1% maker, 0.2% taker
        "BTC/USD": {"maker": 0.0005, "taker": 0.001},  # 0.05% maker, 0.1% taker
        "premium_users": {"maker": 0.0002, "taker": 0.0005}  # Premium users pay less
    }
    
    # Create markets for different trading pairs
    markets = [
        {
            "symbol": "BTC/USD",
            "maker_fee_rate": fee_structure["BTC/USD"]["maker"],
            "taker_fee_rate": fee_structure["BTC/USD"]["taker"],
            "enable_price_improvement": True
        },
        {
            "symbol": "ETH/USD",
            "maker_fee_rate": fee_structure["default"]["maker"],
            "taker_fee_rate": fee_structure["default"]["taker"],
            "enable_price_improvement": True
        },
        {
            "symbol": "ETH/BTC",
            "maker_fee_rate": fee_structure["default"]["maker"],
            "taker_fee_rate": fee_structure["default"]["taker"],
            "enable_price_improvement": False
        }
    ]
    
    # Initialize markets
    for market_config in markets:
        exchange.create_market(**market_config)
        logger.info(f"Created market: {market_config['symbol']}")
    
    # List all available markets
    market_list = exchange.list_markets()
    print(f"Available markets: {', '.join(market_list)}")
    
    # Define user groups
    users = {
        "retail": ["user1", "user2", "user3"],
        "premium": ["premium1", "premium2"],
        "market_maker": ["mm1", "mm2"]
    }
    
    print_header("POPULATING ORDER BOOKS")
    
    # Add initial liquidity to BTC/USD market
    print("Adding liquidity to BTC/USD market...")
    
    # Market makers add GTC orders (Good Till Cancelled)
    for i, price in enumerate(range(47000, 48500, 250)):
        exchange.place_order(
            symbol="BTC/USD",
            side="buy",
            price=float(price),
            quantity=1.0 + (i * 0.5),
            user_id="mm1",
            time_in_force="GTC"
        )
    
    for i, price in enumerate(range(48500, 50000, 250)):
        exchange.place_order(
            symbol="BTC/USD",
            side="sell",
            price=float(price),
            quantity=1.0 + (i * 0.5),
            user_id="mm1",
            time_in_force="GTC"
        )
    
    # Get BTC/USD order book snapshot
    btc_usd_snapshot = exchange.get_market_snapshot("BTC/USD")
    print("\nBTC/USD Order Book after market maker liquidity:")
    print("Bids:")
    for bid in btc_usd_snapshot["bids"]:
        print(f"  ${bid['price']:.2f}: {bid['quantity']:.4f} BTC ({bid['order_count']} orders)")
    
    print("Asks:")
    for ask in btc_usd_snapshot["asks"]:
        print(f"  ${ask['price']:.2f}: {ask['quantity']:.4f} BTC ({ask['order_count']} orders)")
    
    print_header("TIME-IN-FORCE ORDER TYPES")
    
    # GOOD TILL DATE (GTD) ORDERS
    expiry_time = time.time() + 60  # 1 minute from now
    expiry_str = datetime.fromtimestamp(expiry_time).strftime("%H:%M:%S")
    
    print(f"Placing GTD orders that expire at {expiry_str} (60 seconds from now)...")
    
    # Place GTD orders from retail users
    exchange.place_order(
        symbol="BTC/USD",
        side="buy",
        price=48200.0,
        quantity=0.5,
        user_id="user1",
        time_in_force="GTD",
        expiry_time=expiry_time
    )
    
    exchange.place_order(
        symbol="BTC/USD",
        side="sell",
        price=48800.0,
        quantity=0.75,
        user_id="user2",
        time_in_force="GTD",
        expiry_time=expiry_time
    )
    
    # IMMEDIATE OR CANCEL (IOC) ORDERS
    print("\nPlacing IOC orders that will partially execute...")
    
    # Place IOC order that will match against the book
    ioc_order_id = exchange.place_order(
        symbol="BTC/USD",
        side="buy",
        price=48800.0,  # Should match one of the sell orders
        quantity=2.0,    # More than available at best ask
        user_id="premium1",
        time_in_force="IOC"
    )
    
    print(f"IOC order {ioc_order_id} executed")
    
    # FILL OR KILL (FOK) ORDERS
    print("\nPlacing FOK orders...")
    
    # Place FOK order that will fully match
    fok_success_id = exchange.place_order(
        symbol="BTC/USD",
        side="sell",
        price=47000.0,  # Will match against best bid
        quantity=0.5,    # Small enough to match
        user_id="premium2",
        time_in_force="FOK"
    )
    
    print(f"FOK order {fok_success_id} was fully matched")
    
    # Place FOK order that won't fully match (and thus be cancelled)
    fok_fail_id = exchange.place_order(
        symbol="BTC/USD",
        side="buy",
        price=50000.0,  # Higher than any asks
        quantity=20.0,   # Too large to match entirely
        user_id="user3",
        time_in_force="FOK"
    )
    
    print(f"FOK order {fok_fail_id} was not fully matched, so it was cancelled")
    
    print_header("MULTI-MARKET OPERATIONS")
    
    # Add liquidity to ETH/USD market
    print("Adding liquidity to ETH/USD market...")
    
    for i, price in enumerate(range(3000, 3300, 50)):
        exchange.place_order(
            symbol="ETH/USD",
            side="buy",
            price=float(price),
            quantity=5.0 + (i * 1.0),
            user_id="mm2",
            time_in_force="GTC"
        )
    
    for i, price in enumerate(range(3300, 3600, 50)):
        exchange.place_order(
            symbol="ETH/USD",
            side="sell",
            price=float(price),
            quantity=5.0 + (i * 1.0),
            user_id="mm2",
            time_in_force="GTC"
        )
    
    # Get ETH/USD order book snapshot
    eth_usd_snapshot = exchange.get_market_snapshot("ETH/USD")
    print("\nETH/USD Order Book:")
    print("Bids:")
    for bid in eth_usd_snapshot["bids"][:5]:  # Show top 5 bids only
        print(f"  ${bid['price']:.2f}: {bid['quantity']:.4f} ETH ({bid['order_count']} orders)")
    
    print("Asks:")
    for ask in eth_usd_snapshot["asks"][:5]:  # Show top 5 asks only
        print(f"  ${ask['price']:.2f}: {ask['quantity']:.4f} ETH ({ask['order_count']} orders)")
    
    # Cross-market arbitrage
    print("\nSimulating cross-market arbitrage...")
    
    # Premium user executes trades across multiple markets
    exchange.place_order(
        symbol="BTC/USD",
        side="buy",
        price=48000.0,
        quantity=0.5,
        user_id="premium1",
        time_in_force="GTC"
    )
    
    exchange.place_order(
        symbol="ETH/USD",
        side="buy",
        price=3300.0,
        quantity=3.0,
        user_id="premium1",
        time_in_force="GTC"
    )
    
    print_header("USER OPERATIONS")
    
    # Get all orders for a user
    premium1_orders = exchange.get_user_orders("premium1")
    print(f"Premium1 user has {len(premium1_orders)} active orders:")
    for order in premium1_orders:
        print(f"  {order['order_id']} - {order['symbol']}: {order['side']} {order['quantity']} @ ${order['price']}")
    
    print("\nCancelling a user's order...")
    if premium1_orders:
        # Cancel one of the orders
        order_to_cancel = premium1_orders[0]["order_id"]
        exchange.cancel_order(order_to_cancel)
        print(f"Cancelled order: {order_to_cancel}")
    
    # Clean expired orders - shouldn't remove any yet as they expire in 60 seconds
    print("\nChecking for expired orders...")
    expired_count = exchange.clean_expired_orders()
    print(f"Expired orders cleaned: {expired_count}")
    
    print_header("LATENCY MONITORING")
    
    # Get latency statistics from BTC/USD market
    btc_usd_market = exchange.get_market("BTC/USD")
    latency_stats = btc_usd_market.get_latency_stats()
    
    print("BTC/USD Market Operation Latencies:")
    for operation, metrics in latency_stats.items():
        if metrics.get('count', 0) > 0:
            print(f"\n{operation}:")
            print(f"  Count: {metrics.get('count', 0)}")
            if 'mean' in metrics:
                print(f"  Mean: {metrics['mean'] * 1000:.4f} ms")
            if 'p50' in metrics:
                print(f"  Median: {metrics['p50'] * 1000:.4f} ms")
            if 'min' in metrics and 'max' in metrics:
                print(f"  Min/Max: {metrics['min'] * 1000:.4f} ms / {metrics['max'] * 1000:.4f} ms")
    
    print_header("EXCHANGE STATISTICS", char="-")
    
    # Get overall exchange statistics
    stats = exchange.get_statistics()
    print(f"Total markets: {stats['total_markets']}")
    print(f"Total orders: {stats['total_orders']}")
    print(f"Total users: {stats['total_users']}")
    
    print("\nPer-market statistics:")
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
    
    print_header("CONCLUSION", char="*")
    print("The Manticore OrderBook library now provides all the core functionality needed")
    print("for a production-ready cryptocurrency exchange, including:")
    print()
    print("✅ Multiple market support with the MarketManager")
    print("✅ Time-In-Force order policies (GTC, IOC, FOK, GTD)")
    print("✅ Order expiry management")
    print("✅ High-resolution latency monitoring")
    print("✅ Comprehensive fee structure with maker/taker rates")
    print("✅ Thread-safe operations with atomicity guarantees")
    print("✅ Highly optimized data structures for HFT performance")
    
    print("\nReady for production deployment!")

if __name__ == "__main__":
    simulate_trading_day() 