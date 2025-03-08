# Manticore OrderBook User Guide

## Introduction

Manticore OrderBook is a high-performance trading order book implementation written in Python. It provides a complete solution for financial trading applications, supporting multiple order types, advanced matching algorithms, and real-time market data processing.

## Installation

Install the package from PyPI:

```bash
pip3 install manticore-orderbook
```

Or install from source:

```bash
git clone https://github.com/your-organization/manticore-orderbook.git
cd manticore-orderbook
pip3 install -e .
```

## Getting Started

### Basic Usage

```python
from manticore_orderbook import OrderBook
from manticore_orderbook.enums import Side

# Create an order book for BTC/USD
orderbook = OrderBook("BTC", "USD", price_precision=2, quantity_precision=8)

# Add some orders
orderbook.add_order("order1", Side.BUY, 10000.00, 1.0)  # Buy 1 BTC at $10,000
orderbook.add_order("order2", Side.BUY, 9900.00, 2.0)   # Buy 2 BTC at $9,900
orderbook.add_order("order3", Side.SELL, 10100.00, 1.5) # Sell 1.5 BTC at $10,100
orderbook.add_order("order4", Side.SELL, 10200.00, 0.5) # Sell 0.5 BTC at $10,200

# Get the current state of the order book
snapshot = orderbook.get_snapshot()
print("Current Order Book State:")
print(f"Bids: {snapshot['bids']}")
print(f"Asks: {snapshot['asks']}")

# Add a matching order that will execute immediately
orderbook.add_order("order5", Side.BUY, 10100.00, 0.5)  # This will match with order3

# Get the executed trades
trades = orderbook.get_trades()
print("\nExecuted Trades:")
for trade in trades:
    print(f"Price: {trade.price}, Amount: {trade.amount}, Taker: {trade.taker_order_id}, Maker: {trade.maker_order_id}")
```

### Order Types

Manticore OrderBook supports multiple order types through its strategy pattern:

#### Limit Orders

The default order type. Specifies a price at which to buy or sell.

```python
orderbook.add_order("limit1", Side.BUY, 10000.00, 1.0)  # Standard limit order
```

#### Market Orders

Execute immediately at the best available price.

```python
from manticore_orderbook.strategies import MarketOrderStrategy

# Market buy order for 0.5 BTC
orderbook.add_order("market1", Side.BUY, None, 0.5, strategy=MarketOrderStrategy())
```

#### Fill-or-Kill (FOK) Orders

Must be filled completely or not at all.

```python
from manticore_orderbook.strategies import FOKOrderStrategy

# FOK buy order - buy 2 BTC at $10,050 or cancel
orderbook.add_order("fok1", Side.BUY, 10050.00, 2.0, strategy=FOKOrderStrategy())
```

#### Immediate-or-Cancel (IOC) Orders

Execute immediately what can be filled and cancel the rest.

```python
from manticore_orderbook.strategies import IOCOrderStrategy

# IOC sell order - sell up to 1 BTC at $10,100, cancel remainder
orderbook.add_order("ioc1", Side.SELL, 10100.00, 1.0, strategy=IOCOrderStrategy())
```

#### Post-Only Orders

Only add liquidity, never take it. Reject if would execute immediately.

```python
from manticore_orderbook.strategies import PostOnlyOrderStrategy

# Post-only buy order - add to book only if doesn't match
orderbook.add_order("post1", Side.BUY, 9900.00, 3.0, strategy=PostOnlyOrderStrategy())
```

#### Good-Till-Date (GTD) Orders

Remain active until a specified expiration time.

```python
from manticore_orderbook.strategies import GTDOrderStrategy
import datetime

# Order expires in 24 hours
expiry = datetime.datetime.now() + datetime.timedelta(days=1)
orderbook.add_order("gtd1", Side.SELL, 10200.00, 0.75, strategy=GTDOrderStrategy(expiry))
```

### Event Handling

Subscribe to order book events:

```python
from manticore_orderbook.enums import EventType

def on_order_added(event):
    print(f"New order added: {event.order_id} - {event.side} {event.amount} @ {event.price}")

def on_trade_executed(event):
    print(f"Trade executed: {event.amount} @ {event.price}")
    print(f"Maker: {event.maker_order_id}, Taker: {event.taker_order_id}")

# Register event handlers
orderbook.event_manager.register(EventType.ORDER_ADDED, on_order_added)
orderbook.event_manager.register(EventType.TRADE_EXECUTED, on_trade_executed)
```

## Advanced Usage

### Price Improvement

Manticore OrderBook supports price improvement, which allows orders to be executed at better prices than requested:

```python
# Create an order book with price improvement enabled
orderbook = OrderBook("ETH", "USD", enable_price_improvement=True)

# Add orders
orderbook.add_order("sell1", Side.SELL, 2000.00, 1.0)
orderbook.add_order("sell2", Side.SELL, 1990.00, 1.0)  # Better price

# When a buy order comes in at 2000.00, it will match with sell2 first
# due to price improvement, even though sell1 was added first
orderbook.add_order("buy1", Side.BUY, 2000.00, 0.5)
```

### Customizing the Order Book

You can customize various aspects of the order book:

```python
from manticore_orderbook import OrderBook
from manticore_orderbook.matchers import PriceTimeMatcher

# Create an order book with custom settings
orderbook = OrderBook(
    base_asset="BTC",
    quote_asset="USD",
    price_precision=2,        # 2 decimal places for price
    quantity_precision=8,     # 8 decimal places for quantity
    enable_price_improvement=True,
    matcher=PriceTimeMatcher()  # Explicit matcher algorithm
)
```

### Handling Market Data

Get various market statistics:

```python
# Get the best bid and ask prices
snapshot = orderbook.get_snapshot()
best_bid = snapshot['bids'][0]['price'] if snapshot['bids'] else None
best_ask = snapshot['asks'][0]['price'] if snapshot['asks'] else None
spread = best_ask - best_bid if (best_bid and best_ask) else None

print(f"Best bid: {best_bid}")
print(f"Best ask: {best_ask}")
print(f"Spread: {spread}")

# Get market depth
bids = orderbook.get_bids(limit=10)  # Top 10 bids
asks = orderbook.get_asks(limit=10)  # Top 10 asks

# Get order count
order_count = orderbook.get_order_count()
print(f"Total active orders: {order_count}")

# Get last trade price
last_price = orderbook.get_last_price()
print(f"Last traded price: {last_price}")
```

## Performance Tips

1. **Batch Processing**  
   If adding multiple orders at once, add them all before calling `match_orders()` to reduce processing overhead.

2. **Limit Snapshot Size**  
   When getting book snapshots, specify limits to reduce data size:
   ```python
   # Get only top 5 bids and asks
   snapshot = orderbook.get_snapshot(bid_limit=5, ask_limit=5)
   ```

3. **Event Handling**  
   Keep event handlers lightweight. For heavy processing, queue events and process asynchronously.

4. **Order ID Generation**  
   Use efficient order ID generation. Shorter strings use less memory.

## Example Applications

### Simple Trading Simulation

```python
import random
from manticore_orderbook import OrderBook
from manticore_orderbook.enums import Side

def run_simulation(num_orders=1000, price_range=(9000, 11000)):
    orderbook = OrderBook("BTC", "USD")
    order_ids = []
    
    for i in range(num_orders):
        order_id = f"order_{i}"
        side = Side.BUY if random.random() > 0.5 else Side.SELL
        price = random.uniform(*price_range)
        amount = round(random.uniform(0.1, 2.0), 8)
        
        try:
            orderbook.add_order(order_id, side, price, amount)
            order_ids.append(order_id)
            
            # Randomly cancel some orders
            if random.random() < 0.2 and order_ids:
                cancel_id = random.choice(order_ids)
                try:
                    orderbook.cancel_order(cancel_id)
                    order_ids.remove(cancel_id)
                except ValueError:
                    # Order might have been already filled
                    pass
        except ValueError as e:
            print(f"Error adding order: {e}")
    
    # Simulation results
    trades = orderbook.get_trades()
    snapshot = orderbook.get_snapshot()
    
    print(f"Total trades executed: {len(trades)}")
    print(f"Remaining bids: {len(snapshot['bids'])}")
    print(f"Remaining asks: {len(snapshot['asks'])}")
    
    # Calculate volume
    total_volume = sum(trade.amount for trade in trades)
    print(f"Total volume traded: {total_volume} BTC")

run_simulation(1000)
```

## Troubleshooting

### Common Issues

1. **Order not being matched as expected**  
   Ensure that the price levels are compatible for matching. For buy orders, the price must be greater than or equal to the sell price.

2. **Order rejected with validation error**  
   Check that order parameters meet validation requirements:
   - Price and amount must be positive
   - Price must respect price precision
   - Amount must respect quantity precision

3. **Market orders not executing**  
   Ensure there is sufficient liquidity on the opposite side of the book.

4. **Events not being processed**  
   Verify that event handlers are registered correctly and the event types match.

### Debugging Tips

Enable logging for detailed information:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Next Steps

- Check the [API Documentation](API.md) for detailed reference
- Explore the examples directory for more usage patterns
- Read the source code to understand the implementation details

## Contributing

Contributions are welcome! Please see our [Contributing Guide](CONTRIBUTING.md) for details on how to submit pull requests, report issues, and suggest features.

## License

Manticore OrderBook is licensed under the MIT License. See the [LICENSE](../LICENSE) file for details. 