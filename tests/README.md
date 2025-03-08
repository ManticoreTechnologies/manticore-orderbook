# Manticore OrderBook Test Framework

This directory contains the test suite for the Manticore OrderBook implementation. The tests are organized into three main categories:

## Test Structure

- **Unit Tests** (`unit/`): Tests for individual components of the orderbook in isolation.
- **Integration Tests** (`integration/`): Tests for multiple components working together.
- **Visual Tests** (`visual/`): Tests and tools for visualizing the orderbook.

## Running Tests

### Unit Tests

To run all unit tests:

```bash
python3 -m unittest discover tests/unit
```

To run a specific unit test:

```bash
python3 -m unittest tests/unit/test_orderbook_core.py
```

### Integration Tests

To run all integration tests:

```bash
python3 -m unittest discover tests/integration
```

To run a specific integration test:

```bash
python3 -m unittest tests/integration/test_event_system.py
```

### Visual Tests

The visual tests directory contains standalone tools for visualizing and interacting with the orderbook. These are not standard unittest tests, but rather tools that provide a visual interface for manual testing and verification.

#### Professional OrderBook Visualization Tool

The latest version of the visualizer is available as a professional tool with advanced features:

```bash
# Using the convenience script (recommended)
./manticore_orderbook/examples/start_visualizer.sh

# Or directly via Python
python3 manticore_orderbook/examples/run_server.py
```

Optional parameters:
- `--symbol SYMBOL`: Set the trading pair symbol (default: BTC/USD)
- `--port PORT`: Set the port for the web server (default: 5000)
- `--host HOST`: Set the host for the web server (default: 127.0.0.1)
- `--auto-generate`: Auto-generate random orders for testing
- `--debug`: Enable debug mode with more detailed logging

#### Features of the Professional Visualization Tool

The professional visualization tool includes:

1. **Real-time Order Book Visualization** - See bids and asks with depth visualization
2. **Interactive Price Chart** - View price movements over time with candlestick data
3. **Trade History** - Track all executed trades in real-time
4. **Order Management** - Place, modify, and cancel orders directly from the UI
5. **Multiple Order Types** - Support for limit, market, and stop-limit orders
6. **Dark and Light Themes** - Professional UI with theme options
7. **Responsive Design** - Works on desktop and mobile devices

#### Legacy Visualizer

For backward compatibility, the original visualizer is still available:

```bash
python3 tests/visual/orderbook_visualizer.py
```

## Writing New Tests

### Unit Tests

When writing unit tests:
1. Create a new file in the `tests/unit/` directory with the prefix `test_`.
2. Extend the `unittest.TestCase` class.
3. Use descriptive test method names that start with `test_`.
4. Focus on testing a single component in isolation.
5. Use appropriate assertions to verify expected behavior.

Example:
```python
import unittest
from manticore_orderbook import OrderBook

class TestOrderBookSpecificFeature(unittest.TestCase):
    def setUp(self):
        # Setup code
        pass
        
    def test_feature_behavior(self):
        # Test code
        self.assertEqual(expected, actual)
```

### Integration Tests

When writing integration tests:
1. Create a new file in the `tests/integration/` directory with the prefix `test_`.
2. Test the interaction between multiple components.
3. Consider using mocks or stubs for external dependencies if appropriate.
4. Test realistic workflows that end users would perform.

### Visual Tests

When creating visual test tools:
1. Create a standalone script in the `tests/visual/` directory.
2. Use Flask, Tkinter, or other UI frameworks to visualize the orderbook.
3. Include command-line arguments for configurability.
4. Add clear documentation on how to use the tool.

## Test Coverage

We aim to maintain high test coverage of the codebase. Each pull request should include appropriate tests for new features or bug fixes.

To generate a test coverage report:

```bash
pip3 install coverage
coverage run -m unittest discover tests
coverage report -m
```

## Common Testing Patterns

### Testing Order Placement and Matching

```python
def test_basic_order_matching(self):
    # Add a sell order
    sell_id = self.orderbook.add_order(side="sell", price=100.0, quantity=1.0)
    
    # Add a buy order that should match
    buy_id = self.orderbook.add_order(side="buy", price=100.0, quantity=1.0)
    
    # Verify the orderbook is empty (orders matched completely)
    self.assertEqual(0, len(self.orderbook.get_bids()))
    self.assertEqual(0, len(self.orderbook.get_asks()))
```

### Testing Event Generation

```python
def test_order_add_event(self):
    events_received = []
    
    def event_handler(event_type, data):
        events_received.append((event_type, data))
    
    self.event_manager.subscribe(EventType.ORDER_ADDED, event_handler)
    
    # Add an order
    order_id = self.orderbook.add_order(side="buy", price=100.0, quantity=1.0)
    
    # Verify an ORDER_ADDED event was generated
    self.assertEqual(1, len(events_received))
    self.assertEqual(EventType.ORDER_ADDED, events_received[0][0])
    self.assertEqual(order_id, events_received[0][1]["order_id"])
``` 