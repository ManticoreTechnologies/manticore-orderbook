# Compatibility Guide for Manticore OrderBook Visualization Tool

This document explains compatibility considerations when using the Manticore Professional OrderBook Visualization Tool with different versions of the Manticore OrderBook library.

## OrderBook API Compatibility Issues

The visualization tool is designed to work with the latest version of the Manticore OrderBook library, but it includes compatibility layers to handle older versions or API changes.

### `get_snapshot()` Method Compatibility

The most common compatibility issue relates to the `get_snapshot()` method of the `OrderBook` class.

#### Current Behavior

The visualization tool expects the `get_snapshot()` method to accept a `depth` parameter, which limits the number of price levels returned in the snapshot:

```python
# Expected signature
def get_snapshot(self, depth: Optional[int] = None) -> dict:
    ...
```

#### Compatibility Solution

When using the visualization tool with an `OrderBook` implementation that doesn't support the `depth` parameter, the tool automatically detects this and applies a compatibility adapter (`OrderBookAdapter` class). This adapter:

1. Wraps the original OrderBook instance
2. Provides a compatible `get_snapshot()` method that handles the depth parameter
3. Passes through all other method calls to the underlying OrderBook instance

This allows the visualization tool to work with any version of the OrderBook library without modifications.

## Detecting Compatibility Issues

When you start the visualization server, it will automatically check the compatibility of your OrderBook implementation and display warnings if issues are detected:

```
⚠️ WARNING: Your OrderBook implementation doesn't have a 'depth' parameter in get_snapshot().
   The visualization tool has been patched to work with this version, but some features may be limited.
   Consider updating your OrderBook implementation or the visualization tool for full functionality.
```

## Recommended Updates

If you're developing with the Manticore OrderBook library, consider updating your `OrderBook` class to include the `depth` parameter in the `get_snapshot()` method:

```python
def get_snapshot(self, depth: Optional[int] = None) -> dict:
    """
    Get a snapshot of the current order book state.
    
    Args:
        depth: Maximum number of price levels to include (optional)
        
    Returns:
        Dictionary containing order book state
    """
    with self._lock:
        bids = list(self.book_manager._bids)
        asks = list(self.book_manager._asks)
        
        # Apply depth limit if specified
        if depth is not None:
            bids = bids[:depth] if bids else []
            asks = asks[:depth] if asks else []
        
        # Build the snapshot
        bid_levels = {}
        for price in bids:
            orders = self.book_manager.get_orders_at_price("buy", price)
            quantity = sum(order["quantity"] for order in orders.values())
            bid_levels[price] = quantity
            
        ask_levels = {}
        for price in asks:
            orders = self.book_manager.get_orders_at_price("sell", price)
            quantity = sum(order["quantity"] for order in orders.values())
            ask_levels[price] = quantity
            
        return {
            "symbol": self.symbol,
            "bids": bid_levels,
            "asks": ask_levels,
            "timestamp": time.time()
        }
```

This update ensures full compatibility with the visualization tool while maintaining backward compatibility with existing code.

## Other Compatibility Issues

### Event Types

Another potential compatibility issue is with the `EventType` enum in the `event_manager.py` file. Different versions of the library might have different event types defined. If you see errors related to missing event types, make sure your `EventType` enum includes all the necessary events:

```python
class EventType(Enum):
    """Event types that can be published by the order book system."""
    # Order lifecycle events
    ORDER_ADDED = auto()
    ORDER_MODIFIED = auto()
    ORDER_CANCELLED = auto()
    ORDER_FILLED = auto()
    
    # Trade events
    TRADE_EXECUTED = auto()
    
    # Book events
    PRICE_LEVEL_ADDED = auto()
    PRICE_LEVEL_REMOVED = auto()
    PRICE_LEVEL_CHANGED = auto()
    BOOK_UPDATED = auto()
    BOOK_CLEARED = auto()
    DEPTH_CHANGED = auto()
```

### Fee Calculation

Some versions of the OrderBook might calculate fees differently. If you're seeing unexpected fee values, make sure your Trade class's constructor aligns with what the visualization tool expects:

```python
def __init__(self, maker_order_id, taker_order_id, price, quantity, 
            trade_id=None, timestamp=None, 
            maker_fee=None, taker_fee=None,
            maker_fee_rate=0.0, taker_fee_rate=0.0):
    # ...
```

## Getting Help

If you continue to experience compatibility issues, please check the GitHub repository for the latest updates or open an issue with details about your specific problem. 