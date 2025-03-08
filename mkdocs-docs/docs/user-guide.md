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
git clone https://github.com/manticoretechnologies/manticore-orderbook.git
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