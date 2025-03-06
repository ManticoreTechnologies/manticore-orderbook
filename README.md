# Manticore OrderBook

A high-performance, event-driven order book implementation for cryptocurrency exchanges. This module provides the core order matching engine with price-time priority, designed to be integrated with other modules in a larger exchange system.

## Overview

Manticore OrderBook is designed with a focused purpose: to provide a fast, reliable order book implementation that serves as the foundation for cryptocurrency exchange systems. It handles the core functionalities of an order book without overreaching into areas that should be handled by separate specialized modules.

### Key Features

- **High-Performance Matching Engine**: Implements price-time priority matching with optimized data structures
- **Event-Driven Architecture**: Provides a robust event system for integration with other components
- **Thread-Safe Operations**: All operations are thread-safe for reliable concurrent use
- **Comprehensive Order Types**: Supports various time-in-force options (GTC, IOC, FOK, GTD)
- **Clean API**: Provides a simple, well-documented API for easy integration

## Documentation

- [API Documentation](API.md) - Detailed API reference
- [Event System Documentation](EVENTS.md) - Complete guide to the event system
- [Integration Guide](INTEGRATION.md) - How to integrate with other systems
- [Performance Benchmarks](BENCHMARKS.md) - Performance metrics and tuning

## Installation

```bash
pip3 install manticore-orderbook
```

Or install from source:

```bash
git clone https://github.com/your-repo/manticore-orderbook.git
cd manticore-orderbook
pip3 install -e .
```

## Basic Usage

Here's a simple example of how to use the OrderBook:

```python
from manticore_orderbook import OrderBook
from manticore_orderbook.event_manager import EventManager, EventType

# Create an event manager
event_manager = EventManager()

# Create a new order book
order_book = OrderBook(symbol="BTC/USD", event_manager=event_manager)

# Subscribe to events
def handle_trade(event_type, data):
    print(f"Trade executed: {data}")

event_manager.subscribe(EventType.TRADE_EXECUTED, handle_trade)

# Add orders
order_book.add_order(side="buy", price=19500.0, quantity=1.5, order_id="bid1")
order_book.add_order(side="sell", price=19600.0, quantity=1.0, order_id="ask1")

# Execute a matching order that will generate a trade
order_book.add_order(side="buy", price=19700.0, quantity=0.5, order_id="bid2") 

# Get the current state of the order book
snapshot = order_book.get_snapshot(depth=5)
print(snapshot)

# Get order book statistics
stats = order_book.get_statistics()
print(stats)
```

## Integration with Other Modules

### Integration with manticore-storage

The OrderBook module is designed to work seamlessly with a separate storage module. Here's how to integrate with manticore-storage:

```python
from manticore_orderbook import OrderBook, EventType, EventManager
from manticore_storage import StorageManager  # Hypothetical import

# Create components
event_manager = EventManager()
order_book = OrderBook(symbol="BTC/USD")
storage = StorageManager(database_url="postgresql://user:pass@localhost/exchange")

# Set up persistence via events
def persist_order(event_type, data):
    if event_type == EventType.ORDER_ADDED:
        storage.save_order(data)
    elif event_type == EventType.ORDER_MODIFIED:
        storage.update_order(data["order_id"], data)
    elif event_type == EventType.ORDER_CANCELLED:
        storage.mark_order_cancelled(data["order_id"])

def persist_trade(event_type, data):
    storage.save_trade(data)

# Subscribe to events
event_manager.subscribe(EventType.ORDER_ADDED, persist_order)
event_manager.subscribe(EventType.ORDER_MODIFIED, persist_order)
event_manager.subscribe(EventType.ORDER_CANCELLED, persist_order)
event_manager.subscribe(EventType.TRADE_EXECUTED, persist_trade)

# Operation continues with automatic persistence
order_book.add_order(side="buy", price=19500.0, quantity=1.5)
```

### Integration with manticore-matching

For more advanced matching algorithms beyond the basic price-time priority:

```python
from manticore_orderbook import OrderBook, Order, EventType, EventManager
from manticore_matching import MatchingEngine  # Hypothetical import

# Create components
event_manager = EventManager()
order_book = OrderBook(symbol="BTC/USD")
matching_engine = MatchingEngine(strategy="pro_rata")  # Example custom matching strategy

# Intercept orders before they're added to the book
def pre_process_order(event_type, data):
    # Apply custom matching logic
    if data.get("special_instructions"):
        matching_engine.process_special_order(data)

# Subscribe to pre-processing
event_manager.subscribe(EventType.ORDER_ADDED, pre_process_order)
```

### Using with a Full Exchange System

In a complete exchange system, the OrderBook would be one component among many. Here's a conceptual example:

```python
from manticore_orderbook import OrderBook, EventManager
from manticore_storage import StorageManager  # Hypothetical
from manticore_auth import AuthManager  # Hypothetical
from manticore_risk import RiskManager  # Hypothetical
from manticore_api import ApiServer  # Hypothetical

class Exchange:
    def __init__(self):
        # Core components
        self.event_manager = EventManager()
        self.storage = StorageManager()
        self.auth = AuthManager()
        self.risk = RiskManager()
        
        # Create order books for each market
        self.markets = {}
        self.setup_markets()
        
        # API layer
        self.api = ApiServer(self)
    
    def setup_markets(self):
        market_configs = self.storage.get_market_configs()
        for config in market_configs:
            symbol = config["symbol"]
            self.markets[symbol] = OrderBook(symbol=symbol)
            
    def place_order(self, user_id, symbol, side, price, quantity):
        # Authenticate
        if not self.auth.validate_user(user_id):
            return {"error": "Unauthorized"}
            
        # Risk check
        if not self.risk.check_order(user_id, symbol, side, price, quantity):
            return {"error": "Risk limits exceeded"}
            
        # Place the order
        order_book = self.markets.get(symbol)
        if not order_book:
            return {"error": "Market not found"}
            
        order_id = order_book.add_order(
            side=side, 
            price=price, 
            quantity=quantity,
            user_id=user_id
        )
        
        return {"order_id": order_id}
```

## Event System

The event system is at the heart of integration capabilities. Here are the key events you can subscribe to:

| Event Type | Description | Data Payload |
|------------|-------------|--------------|
| ORDER_ADDED | Triggered when an order is added to the book | Order details |
| ORDER_MODIFIED | Triggered when an order is modified | Updated order details |
| ORDER_CANCELLED | Triggered when an order is cancelled | Order ID and metadata |
| ORDER_FILLED | Triggered when an order is partially or fully filled | Fill details |
| TRADE_EXECUTED | Triggered when a trade is executed | Trade details |
| PRICE_LEVEL_CHANGED | Triggered when a price level changes | Price level details |
| BOOK_UPDATED | General notification that the book state has changed | Summary of changes |

## Benchmark Results

The OrderBook has been benchmarked for performance. Here are the key metrics:

- Adding orders: ~28,000 orders/second
- Modifying orders: ~64,000 modifications/second
- Cancelling orders: ~120,000 cancellations/second
- Matching orders: ~50,000 operations/second in batch mode
- Depth queries: ~170,000 queries/second

You can run the benchmarks yourself with:

```bash
python3 benchmark.py
```

## Development

### Running Tests

```bash
python3 -m unittest discover
```

### Building the Package

```bash
python3 setup.py bdist_wheel
```

## API Reference

### OrderBook

The core class that manages orders and handles matching.

```python
order_book = OrderBook(
    symbol="BTC/USD",
    maker_fee_rate=0.001,  # 0.1%
    taker_fee_rate=0.002,  # 0.2%
    enable_logging=True
)
```

#### Key Methods

- `add_order(side, price, quantity, order_id=None, time_in_force=None)`: Add a new order to the book
- `modify_order(order_id, new_price=None, new_quantity=None)`: Modify an existing order
- `cancel_order(order_id)`: Cancel an order
- `get_snapshot(depth=10)`: Get the current order book state
- `get_order(order_id)`: Get details of a specific order
- `get_statistics()`: Get order book statistics

### EventManager

Manages the event system for all components.

```python
event_manager = EventManager(enable_logging=True, max_history_size=1000)
```

#### Key Methods

- `subscribe(event_type, handler)`: Subscribe to an event type
- `unsubscribe(event_type, handler)`: Unsubscribe from an event type
- `publish(event_type, data, symbol=None)`: Publish an event
- `subscribe_all(handler)`: Subscribe to all event types
- `get_event_history(limit=100)`: Get recent event history

## Design Considerations

1. **Separation of Concerns**: The OrderBook focuses solely on order book management without handling persistence, authentication, etc.
2. **Event-Driven Architecture**: All state changes are published as events, allowing other components to react accordingly
3. **Performance First**: Data structures and algorithms are optimized for high throughput
4. **Thread Safety**: All methods are protected against concurrent access

## License

MIT License 