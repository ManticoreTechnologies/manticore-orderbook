# Manticore OrderBook

A high-performance, exchange-ready Python library for managing order book data in trading systems. Production-optimized for high-frequency trading environments with multi-market support.

## Features

- Fast order book management with strict price-time priority
- Efficient order matching engine with optional price improvement
- Support for limit orders (buy/sell)
- Atomic order modification and cancellation
- Batch operations for efficient processing
- High-performance depth queries and cached snapshots
- Detailed trade history tracking with fee calculation
- High-resolution performance monitoring
- Thread-safe operations with atomic guarantees
- O(log N) performance for critical operations
- Multi-market support with the MarketManager
- Time-In-Force policies (GTC, IOC, FOK, GTD)
- Order expiry management
- Latency monitoring with detailed metrics
- Comprehensive stress tests and benchmarks

## Installation

```bash
pip3 install manticore-orderbook
```

Or for development:

```bash
git clone https://github.com/manticoretechnologies/manticore-orderbook.git
cd manticore-orderbook
pip3 install -e .
```

## Quick Start

```python
from manticore_orderbook import OrderBook
import time

# Create an order book with optional features
orderbook = OrderBook(
    symbol="BTC/USD",
    enable_price_improvement=True,  # Enable price improvement for taker orders
    maker_fee_rate=0.001,           # 0.1% fee for makers
    taker_fee_rate=0.002            # 0.2% fee for takers
)

# Add buy (bid) order
order_id_1 = orderbook.add_order(
    side="buy", 
    price=20000.0, 
    quantity=1.5, 
    order_id="order1",
    time_in_force="GTC"  # Good Till Cancelled (default)
)

# Add sell (ask) order with expiry
order_id_2 = orderbook.add_order(
    side="sell", 
    price=20100.0, 
    quantity=2.0, 
    order_id="order2",
    time_in_force="GTD",  # Good Till Date
    expiry_time=time.time() + 3600  # Expires in 1 hour
)

# Get order book snapshot with depth
snapshot = orderbook.get_snapshot(depth=10)
print(f"Bids: {snapshot['bids']}")
print(f"Asks: {snapshot['asks']}")

# Modify an order (atomic operation)
orderbook.modify_order(
    order_id="order1", 
    new_price=20050.0, 
    new_quantity=1.8,
    new_expiry_time=None  # Leave expiry unchanged
)

# Cancel an order
orderbook.cancel_order(order_id="order2")

# Get recent trades with fees
trades = orderbook.get_trade_history(limit=10)
print(f"Recent trades: {trades}")

# Batch add multiple orders for efficiency
orders = [
    {"side": "buy", "price": 19950.0, "quantity": 1.2, "time_in_force": "GTC"},
    {"side": "buy", "price": 19900.0, "quantity": 2.0, "time_in_force": "GTC"},
    {"side": "sell", "price": 20150.0, "quantity": 0.5, "time_in_force": "IOC"}  # Immediate Or Cancel
]
order_ids = orderbook.batch_add_orders(orders)

# Get order book statistics
stats = orderbook.get_statistics()
print(f"Order book statistics: {stats}")

# Check latency metrics
latency_stats = orderbook.get_latency_stats()
print(f"Latency statistics: {latency_stats}")
```

## Multi-Market Support

The library includes a `MarketManager` for managing multiple order books:

```python
from manticore_orderbook import MarketManager

# Create a market manager
manager = MarketManager()

# Create multiple markets
btc_usd = manager.create_market(
    symbol="BTC/USD", 
    maker_fee_rate=0.001,
    taker_fee_rate=0.002
)

eth_usd = manager.create_market(
    symbol="ETH/USD",
    maker_fee_rate=0.0015,
    taker_fee_rate=0.0025
)

# Place orders in different markets
manager.place_order(
    symbol="BTC/USD",
    side="buy",
    price=48000.0,
    quantity=1.5,
    user_id="user1",
    time_in_force="GTC"
)

manager.place_order(
    symbol="ETH/USD",
    side="sell",
    price=3250.0,
    quantity=8.0,
    user_id="user2",
    time_in_force="GTD",
    expiry_time=time.time() + 3600  # 1 hour
)

# Get snapshots of all markets
btc_snapshot = manager.get_market_snapshot("BTC/USD")
eth_snapshot = manager.get_market_snapshot("ETH/USD")

# Get user's orders across all markets
user1_orders = manager.get_user_orders("user1")

# Clean up expired orders in all markets
expired_orders = manager.clean_expired_orders()

# Get overall statistics
stats = manager.get_statistics()
```

## Exchange-Ready Features

The Manticore OrderBook is designed to be used in production trading systems, with features specifically tailored for exchange operations:

### Production Readiness
- **Multi-market support**: Manage multiple trading pairs with a single MarketManager
- **User order tracking**: Track and manage orders by user ID across all markets
- **Fee calculation**: Configurable maker/taker fee rates with automatic calculation
- **Order expiry**: Automated cleanup of expired orders
- **Latency monitoring**: High-resolution timing of all operations
- **Error handling**: Robust error handling and recovery mechanisms

### Time-In-Force Policies

The order book supports the following Time-In-Force policies:

- **GTC (Good Till Cancelled)**: Order remains active until explicitly cancelled or fully filled
- **IOC (Immediate Or Cancel)**: Fills what it can immediately, then cancels any remaining quantity
- **FOK (Fill Or Kill)**: Either fills the entire order immediately or cancels it entirely
- **GTD (Good Till Date)**: Order remains active until a specified expiry time is reached

### Example: Creating a Complete Exchange

```python
# Initialize the exchange with multiple markets
exchange = MarketManager(enable_logging=True)

# Set up markets with different fee structures
markets = [
    {
        "symbol": "BTC/USD",
        "maker_fee_rate": 0.0005,  # 0.05% fee
        "taker_fee_rate": 0.001,   # 0.1% fee
        "enable_price_improvement": True
    },
    {
        "symbol": "ETH/USD",
        "maker_fee_rate": 0.001,   # 0.1% fee
        "taker_fee_rate": 0.002,   # 0.2% fee
        "enable_price_improvement": True
    },
    {
        "symbol": "ETH/BTC",
        "maker_fee_rate": 0.001,
        "taker_fee_rate": 0.002,
        "enable_price_improvement": False
    }
]

# Initialize all markets
for market_config in markets:
    exchange.create_market(**market_config)

# Place orders with different Time-In-Force policies
exchange.place_order(
    symbol="BTC/USD",
    side="buy",
    price=47500.0,
    quantity=1.0,
    user_id="market_maker1",
    time_in_force="GTC"  # Good Till Cancelled
)

# Place a time-limited order
exchange.place_order(
    symbol="ETH/USD",
    side="sell",
    price=3300.0,
    quantity=5.0,
    user_id="trader1",
    time_in_force="GTD",  # Good Till Date
    expiry_time=time.time() + 3600  # 1 hour
)

# Place an IOC order that will execute immediately or be cancelled
exchange.place_order(
    symbol="BTC/USD",
    side="buy",
    price=48000.0,
    quantity=0.5,
    user_id="trader2",
    time_in_force="IOC"  # Immediate Or Cancel
)

# Get exchange-wide statistics
stats = exchange.get_statistics()
print(f"Total markets: {stats['total_markets']}")
print(f"Total orders: {stats['total_orders']}")
print(f"Total users: {stats['total_users']}")

# Check latency across all markets
for symbol in exchange.list_markets():
    market = exchange.get_market(symbol)
    latency = market.get_latency_stats()
    print(f"{symbol} latency metrics: {latency}")
```

## Documentation

The `OrderBook` class provides the following key methods:

### Order Management
- `add_order(side, price, quantity, order_id=None, time_in_force=None, expiry_time=None, user_id=None)`: Add a new limit order
- `batch_add_orders(orders)`: Add multiple orders efficiently in a single batch
- `modify_order(order_id, new_price=None, new_quantity=None, new_expiry_time=None)`: Modify an existing order atomically
- `cancel_order(order_id)`: Cancel an existing order
- `batch_cancel_orders(order_ids)`: Cancel multiple orders efficiently in a single batch
- `clean_expired_orders()`: Remove expired orders from the book

### Order Book Information
- `get_snapshot(depth=10)`: Get the current state of the order book with specified depth
- `get_order_depth_at_price(side, price)`: Get total quantity at a specific price level
- `get_order(order_id)`: Get information about a specific order
- `get_trade_history(limit=100)`: Get recent trades including fees

### Performance Monitoring
- `get_statistics()`: Get detailed statistics about the order book operations
- `get_latency_stats()`: Get detailed latency metrics for operations
- `clear()`: Clear all orders from the order book

The `MarketManager` class provides:

### Market Management
- `create_market(symbol, maker_fee_rate=0, taker_fee_rate=0, enable_price_improvement=True)`: Create a new market
- `get_market(symbol)`: Get a specific market
- `list_markets()`: List all available markets
- `remove_market(symbol)`: Remove a market

### Cross-Market Operations
- `place_order(symbol, side, price, quantity, user_id=None, time_in_force="GTC", expiry_time=None)`: Place an order in a specific market
- `cancel_order(order_id)`: Cancel an order by its ID
- `modify_order(order_id, new_price=None, new_quantity=None, new_expiry_time=None)`: Modify an existing order
- `get_user_orders(user_id)`: Get all orders for a specific user across all markets
- `get_market_snapshot(symbol, depth=10)`: Get a snapshot of a specific market
- `clean_expired_orders()`: Clean expired orders across all markets
- `get_statistics()`: Get statistics across all markets

## Advanced Features

### Price-Time Priority (FIFO)
The order book implements strict price-time priority, ensuring that orders at the same price level are executed in the order they were received.

### Price Improvement
When enabled, the price improvement feature allows taker orders to execute at better prices than their limit prices if such prices are available in the order book.

### Atomic Operations
All order modifications are atomic, ensuring that the order book remains in a consistent state even in case of errors or exceptions.

### Efficient Depth Queries
The order book implements efficient depth queries using caching strategies, ensuring that frequently accessed information like top price levels is retrieved with minimal overhead.

### Thread Safety
All operations are thread-safe, making the order book suitable for use in multi-threaded environments.

### Latency Monitoring
The library includes comprehensive latency monitoring for all operations, with detailed statistics including mean, median, 90th percentile, and 99th percentile latency times.

## Performance

The library uses efficient data structures to ensure high performance:
- Order insertions, modifications, and cancellations are O(log N) operations
- Order matching happens automatically when prices cross
- Batch operations provide significant performance improvements for high-volume scenarios
- Depth queries use caching for fast access to frequently used information
- All trade history is kept in memory with configurable size limits

Run the included benchmark script to evaluate performance on your system:

```bash
python3 benchmark.py
```

## Integration

This library is designed to be integrated easily with other components:
- No external dependencies required for core functionality
- Clean, simple API for integration with other systems
- Fully self-contained with no persistence requirements
- Proper Python packaging for easy distribution and installation

## License

MIT 