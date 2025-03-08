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

## Advanced Usage

### Different Order Types

```python
from manticore_orderbook.strategies import (
    MarketOrderStrategy,
    FOKOrderStrategy,
    IOCOrderStrategy,
    PostOnlyOrderStrategy,
    GTDOrderStrategy
)
import datetime

# Market order
orderbook.add_order("market1", Side.BUY, None, 0.5, 
                   strategy=MarketOrderStrategy())

# Fill-or-Kill order
orderbook.add_order("fok1", Side.BUY, 10050.00, 2.0,
                   strategy=FOKOrderStrategy())

# Immediate-or-Cancel order
orderbook.add_order("ioc1", Side.SELL, 10100.00, 1.0,
                   strategy=IOCOrderStrategy())

# Post-Only order
orderbook.add_order("post1", Side.BUY, 9900.00, 3.0,
                   strategy=PostOnlyOrderStrategy())

# Good-Till-Date order
expiry = datetime.datetime.now() + datetime.timedelta(days=1)
orderbook.add_order("gtd1", Side.SELL, 10200.00, 0.75,
                   strategy=GTDOrderStrategy(expiry))
```

### Price Improvement

```python
# Create an order book with price improvement enabled
orderbook = OrderBook("ETH", "USD", enable_price_improvement=True)

# The order book will automatically match orders at the best available price,
# even if that's better than what the taker requested
```

## Performance

Manticore OrderBook is designed for high-performance trading applications:

- **Order Addition**: ~15,000 orders/second
- **Order Cancellation**: ~14,000 cancels/second
- **Order Matching**: ~17,000 orders/second with multiple matches

## Documentation

- [User Guide](docs/USER_GUIDE.md) - Comprehensive guide to using the library
- [API Documentation](docs/API.md) - Detailed API reference
- [Examples](examples/) - Code examples demonstrating various features

## Visualization

Manticore OrderBook includes a visualization server for real-time order book display:

```bash
python3 -m manticore_orderbook.visualizer
```

![OrderBook Visualization](docs/images/orderbook_viz.png)

## Development

### Setup Development Environment

```bash
# Clone the repository
git clone https://github.com/manticoretechnologies/manticore-orderbook.git
cd manticore-orderbook

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install development dependencies
pip3 install -e ".[dev]"
```

### Running Tests

```bash
# Run all tests
python3 -m unittest discover

# Run specific test module
python3 -m unittest tests.test_orderbook

# Run benchmarks
python3 -m tests.benchmark.test_orderbook_benchmark
```

## Contributing

Contributions are welcome! Please see our [Contributing Guide](CONTRIBUTING.md) for details on how to submit pull requests, report issues, and suggest features.

## License

Manticore OrderBook is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## Contact

- **Website**: [https://manticore.technology](https://manticore.technology)
- **Email**: [dev@manticore.technology](mailto:dev@manticore.technology)
- **GitHub**: [https://github.com/manticoretechnologies](https://github.com/manticoretechnologies) 