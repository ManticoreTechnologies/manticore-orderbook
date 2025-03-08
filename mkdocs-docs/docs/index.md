# Manticore OrderBook

A high-performance, feature-rich limit order book implementation for financial trading applications.

[![Python Versions](https://img.shields.io/badge/python-3.7%20%7C%203.8%20%7C%203.9%20%7C%203.10-blue)]()
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Features

✅ **Complete Order Book Implementation** - Full-featured limit order book with best-in-class performance  
✅ **Multiple Order Types** - Support for limit, market, FOK, IOC, post-only, and GTD orders  
✅ **Price Improvement** - Optional price improvement for better execution  
✅ **Event-Driven Architecture** - Real-time events for order added, cancelled, and trades executed  
✅ **High Performance** - Optimized for high-throughput trading (17,000+ orders/second)  
✅ **Comprehensive API** - Clean, intuitive interface with extensive documentation  
✅ **Production Ready** - Extensively tested and benchmarked

## Installation

```bash
# From PyPI
pip3 install manticore-orderbook

# From source
git clone https://github.com/manticoretechnologies/manticore-orderbook.git
cd manticore-orderbook
pip3 install -e .
```

## Quick Start

```python
from manticore_orderbook import OrderBook
from manticore_orderbook.enums import Side, EventType

# Create an order book for BTC/USD
orderbook = OrderBook("BTC", "USD")

# Register event handlers
def on_trade(event):
    print(f"Trade executed: {event.amount} @ {event.price}")

orderbook.event_manager.register(EventType.TRADE_EXECUTED, on_trade)

# Add orders
orderbook.add_order("bid1", Side.BUY, 10000.00, 1.0)
orderbook.add_order("ask1", Side.SELL, 10100.00, 0.5)

# Get a snapshot of the current order book state
snapshot = orderbook.get_snapshot()
print(f"Best bid: {snapshot['bids'][0]['price'] if snapshot['bids'] else 'None'}")
print(f"Best ask: {snapshot['asks'][0]['price'] if snapshot['asks'] else 'None'}")

# Add a matching order that will execute
orderbook.add_order("match1", Side.BUY, 10100.00, 0.2)
```

For more detailed instructions, please see the [User Guide](user-guide.md).
