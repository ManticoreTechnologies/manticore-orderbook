# Integrating Manticore OrderBook

This guide provides detailed instructions on how to integrate the Manticore OrderBook module with other components of your cryptocurrency exchange system.

## Table of Contents

1. [Introduction](#introduction)
2. [Integration with manticore-storage](#integration-with-manticore-storage)
3. [Integration with manticore-matching](#integration-with-manticore-matching)
4. [Building a Complete Exchange System](#building-a-complete-exchange-system)
5. [Best Practices](#best-practices)
6. [Performance Considerations](#performance-considerations)
7. [Troubleshooting](#troubleshooting)

## Introduction

Manticore OrderBook is designed as a core component in a modular exchange architecture. It focuses on efficiently managing order books with price-time priority matching, while delegating other concerns like persistence, authentication, and risk management to specialized modules.

The key interface between Manticore OrderBook and other modules is the **event system**. By subscribing to events from the OrderBook, other modules can react to changes in the order book state without tight coupling between components.

### Architecture Diagram

```
┌───────────────────┐      ┌───────────────────┐      ┌───────────────────┐
│  manticore-auth   │      │  manticore-risk   │      │   manticore-api   │
└─────────┬─────────┘      └─────────┬─────────┘      └─────────┬─────────┘
          │                          │                          │
          │                          │                          │
          │                          │                          │
┌─────────▼─────────┐      ┌─────────▼─────────┐      ┌─────────▼─────────┐
│ manticore-orderbook◄─────►manticore-storage  │      │manticore-matching │
└─────────┬─────────┘      └─────────┬─────────┘      └─────────┬─────────┘
          │                          │                          │
          │                          │                          │
          └──────────────────────────┴──────────────────────────┘
```

## Integration with manticore-storage

The manticore-storage module handles persistent storage of order data, trade history, and other information needed for an exchange. Here's how to integrate the two modules:

### Setup

1. Initialize both modules:

```python
from manticore_orderbook import OrderBook, EventManager, EventType
from manticore_storage import StorageManager  # Assumed interface

# Create instances
event_manager = EventManager()
orderbook = OrderBook(symbol="BTC/USD")
storage = StorageManager(connection_string="your_db_connection_string")
```

### Event-Based Persistence

2. Subscribe to orderbook events to persist changes:

```python
# Handler for order events
def handle_order_event(event_type, data):
    if event_type == EventType.ORDER_ADDED:
        # Store new order
        storage.save_order(data)
    elif event_type == EventType.ORDER_MODIFIED:
        # Update existing order
        storage.update_order(data["order_id"], data)
    elif event_type == EventType.ORDER_CANCELLED:
        # Mark order as cancelled
        storage.mark_order_cancelled(data["order_id"])
    elif event_type == EventType.ORDER_FILLED:
        # Update fill status
        storage.update_order_fill(data["order_id"], data["filled_quantity"])

# Handler for trade events
def handle_trade_event(event_type, data):
    # Store trade record
    storage.save_trade(data)

# Subscribe to events
event_manager.subscribe(EventType.ORDER_ADDED, handle_order_event)
event_manager.subscribe(EventType.ORDER_MODIFIED, handle_order_event)
event_manager.subscribe(EventType.ORDER_CANCELLED, handle_order_event)
event_manager.subscribe(EventType.ORDER_FILLED, handle_order_event)
event_manager.subscribe(EventType.TRADE_EXECUTED, handle_trade_event)
```

### Restoring State from Storage

3. Initialize orderbook from storage:

```python
# When starting the system, load existing active orders
def initialize_orderbook_from_storage():
    active_orders = storage.get_active_orders(symbol="BTC/USD")
    
    # Sort by timestamp to maintain proper time priority
    sorted_orders = sorted(active_orders, key=lambda x: x["timestamp"])
    
    # Add to orderbook in order
    for order_data in sorted_orders:
        try:
            orderbook.add_order(
                side=order_data["side"],
                price=order_data["price"],
                quantity=order_data["quantity"],
                order_id=order_data["order_id"],
                timestamp=order_data["timestamp"],
                time_in_force=order_data["time_in_force"],
                expiry_time=order_data.get("expiry_time"),
                user_id=order_data.get("user_id")
            )
        except Exception as e:
            logger.error(f"Failed to restore order {order_data['order_id']}: {str(e)}")

# Call this during system startup
initialize_orderbook_from_storage()
```

### Periodic Snapshots

4. Create periodic snapshots for faster recovery:

```python
def create_orderbook_snapshot():
    snapshot = orderbook.get_snapshot(depth=0)  # Get full depth
    storage.save_snapshot(symbol="BTC/USD", data=snapshot)
    
    # Publish event for external subscribers
    event_manager.publish(
        event_type=EventType.SNAPSHOT_CREATED,
        data={"symbol": "BTC/USD", "timestamp": time.time()},
        symbol="BTC/USD"
    )

# Call this periodically (e.g., every 5 minutes)
import threading
import time

def snapshot_scheduler():
    while True:
        time.sleep(300)  # 5 minutes
        create_orderbook_snapshot()

# Start snapshot thread
snapshot_thread = threading.Thread(target=snapshot_scheduler, daemon=True)
snapshot_thread.start()
```

## Integration with manticore-matching

For more advanced matching algorithms beyond basic price-time priority, you might have a separate matching engine module.

### Basic Integration

```python
from manticore_orderbook import OrderBook, Order, EventType, EventManager
from manticore_matching import MatchingEngine  # Hypothetical module

# Initialize components
event_manager = EventManager()
orderbook = OrderBook(symbol="BTC/USD")
matching_engine = MatchingEngine(strategy="pro_rata")  # Example strategy

# Integration approach 1: Pre-process orders before adding to the order book
def pre_process_order(event_type, data):
    if data.get("special_instructions"):
        # Apply custom matching logic before adding to order book
        matching_result = matching_engine.process_order(data)
        
        # If the matching engine generated trades, publish them
        for trade in matching_result.get("trades", []):
            event_manager.publish(
                event_type=EventType.TRADE_EXECUTED,
                data=trade,
                symbol="BTC/USD"
            )
            
        # If the order should not be added to the book, stop processing
        if matching_result.get("cancel_order", False):
            return
    
    # Continue with normal order book processing

# Subscribe to the pre-process hook
event_manager.subscribe(EventType.ORDER_ADDED, pre_process_order)

# Integration approach 2: Post-process trades after they occur
def post_process_trade(event_type, data):
    # Apply custom allocation rules
    modified_trade = matching_engine.apply_allocation_rules(data)
    
    # If the trade was modified, update it
    if modified_trade != data:
        # Update in storage
        storage.update_trade(modified_trade["trade_id"], modified_trade)

# Subscribe to trade events
event_manager.subscribe(EventType.TRADE_EXECUTED, post_process_trade)
```

## Building a Complete Exchange System

Here's a simplified example of how to integrate multiple components into a cohesive exchange system:

```python
from manticore_orderbook import OrderBook, EventManager, EventType
# Hypothetical imports for other modules
from manticore_storage import StorageManager
from manticore_auth import AuthManager
from manticore_risk import RiskManager
from manticore_api import ApiServer

class Exchange:
    def __init__(self, config):
        # Core components
        self.event_manager = EventManager()
        self.storage = StorageManager(config["storage"])
        self.auth = AuthManager(config["auth"])
        self.risk = RiskManager(config["risk"])
        
        # Initialize markets
        self.markets = {}
        self.initialize_markets()
        
        # Set up API layer
        self.api = ApiServer(self, config["api"])
        
        # Connect event handlers
        self.setup_event_handlers()
    
    def initialize_markets(self):
        # Load market configurations from storage
        market_configs = self.storage.get_market_configs()
        
        for config in market_configs:
            symbol = config["symbol"]
            # Create order book for each market
            self.markets[symbol] = OrderBook(
                symbol=symbol,
                maker_fee_rate=config.get("maker_fee_rate", 0.0),
                taker_fee_rate=config.get("taker_fee_rate", 0.0)
            )
            
            # Load existing orders
            active_orders = self.storage.get_active_orders(symbol)
            for order in active_orders:
                # Add to order book
                self.markets[symbol].add_order(
                    side=order["side"],
                    price=order["price"],
                    quantity=order["quantity"],
                    order_id=order["order_id"],
                    time_in_force=order["time_in_force"],
                    expiry_time=order.get("expiry_time"),
                    user_id=order.get("user_id")
                )
    
    def setup_event_handlers(self):
        # Register storage handlers for each market
        for symbol, order_book in self.markets.items():
            # Set up persistence
            def handle_order_event(event_type, data):
                # Forward to storage module
                if event_type == EventType.ORDER_ADDED:
                    self.storage.save_order(data)
                # Handle other event types...
            
            # Subscribe to events
            self.event_manager.subscribe(EventType.ORDER_ADDED, handle_order_event)
            # Subscribe to other event types...
    
    def place_order(self, user_id, symbol, side, price, quantity,
                   time_in_force="GTC", expiry_time=None):
        """Main entry point for placing an order."""
        # 1. Authentication check
        if not self.auth.is_authenticated(user_id):
            return {"error": "User not authenticated"}
        
        # 2. Risk check
        risk_result = self.risk.check_order(
            user_id=user_id,
            symbol=symbol,
            side=side,
            price=price,
            quantity=quantity
        )
        
        if not risk_result["approved"]:
            return {"error": f"Risk check failed: {risk_result['reason']}"}
        
        # 3. Get the appropriate order book
        order_book = self.markets.get(symbol)
        if not order_book:
            return {"error": f"Market {symbol} not found"}
        
        # 4. Place the order
        try:
            order_id = order_book.add_order(
                side=side,
                price=price,
                quantity=quantity,
                time_in_force=time_in_force,
                expiry_time=expiry_time,
                user_id=user_id
            )
            return {"order_id": order_id, "status": "placed"}
        except Exception as e:
            return {"error": f"Failed to place order: {str(e)}"}
    
    # Other exchange functionality...
```

## Best Practices

### 1. Use Events for Loose Coupling

Use the event system for communication between modules rather than direct method calls wherever possible. This allows modules to be developed, tested, and replaced independently.

### 2. Idempotent Operations

Design your storage integration to handle idempotent operations, where processing the same event multiple times doesn't cause issues. This is crucial for handling recovery scenarios.

```python
def handle_order_added(event_type, data):
    order_id = data["order_id"]
    
    # Check if order already exists before saving
    existing = storage.get_order(order_id)
    if existing:
        # Maybe log duplicate
        return
    
    # Otherwise save the order
    storage.save_order(data)
```

### 3. Handle Event Failures Gracefully

When subscribing to events, ensure that failures in one handler don't affect others:

```python
def safe_event_handler(handler_func):
    def wrapped(event_type, data):
        try:
            return handler_func(event_type, data)
        except Exception as e:
            logger.error(f"Error in event handler: {str(e)}")
            # Maybe store the failed event for later replay
            storage.save_failed_event(event_type, data, str(e))
    return wrapped

# Use the decorator when subscribing
event_manager.subscribe(EventType.ORDER_ADDED, safe_event_handler(handle_order_added))
```

### 4. Periodic Reconciliation

Periodically reconcile the state of the order book with the storage system to catch any discrepancies:

```python
def reconcile_orderbook_with_storage():
    """Compare orderbook state with storage and fix inconsistencies."""
    storage_orders = storage.get_active_orders(symbol="BTC/USD")
    orderbook_orders = orderbook.get_all_orders()
    
    # Find orders in storage but not in orderbook
    storage_order_ids = {o["order_id"] for o in storage_orders}
    orderbook_order_ids = {o["order_id"] for o in orderbook_orders}
    
    missing_in_orderbook = storage_order_ids - orderbook_order_ids
    for order_id in missing_in_orderbook:
        order = next(o for o in storage_orders if o["order_id"] == order_id)
        logger.warning(f"Order {order_id} found in storage but not in orderbook, restoring")
        orderbook.add_order(**order)
    
    # Find orders in orderbook but not in storage
    missing_in_storage = orderbook_order_ids - storage_order_ids
    for order_id in missing_in_storage:
        order = next(o for o in orderbook_orders if o["order_id"] == order_id)
        logger.warning(f"Order {order_id} found in orderbook but not in storage, persisting")
        storage.save_order(order)
```

## Performance Considerations

### 1. Batch Processing

For high-volume systems, consider batching database operations instead of processing each event individually:

```python
class BatchStorageHandler:
    def __init__(self, storage_manager, batch_size=100, flush_interval=5.0):
        self.storage = storage_manager
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        self.order_batch = []
        self.trade_batch = []
        self.last_flush = time.time()
        self.lock = threading.Lock()
        
        # Start background flush thread
        self.flush_thread = threading.Thread(target=self._flush_loop, daemon=True)
        self.flush_thread.start()
    
    def handle_order(self, event_type, data):
        with self.lock:
            self.order_batch.append((event_type, data))
        
        if len(self.order_batch) >= self.batch_size:
            self.flush()
    
    def handle_trade(self, event_type, data):
        with self.lock:
            self.trade_batch.append(data)
            
        if len(self.trade_batch) >= self.batch_size:
            self.flush()
    
    def flush(self):
        with self.lock:
            if not self.order_batch and not self.trade_batch:
                return
                
            # Process orders
            orders_to_process = list(self.order_batch)
            self.order_batch = []
            
            # Process trades
            trades_to_process = list(self.trade_batch)
            self.trade_batch = []
        
        # Process outside the lock
        try:
            if orders_to_process:
                self.storage.batch_save_orders(orders_to_process)
            
            if trades_to_process:
                self.storage.batch_save_trades(trades_to_process)
                
            self.last_flush = time.time()
        except Exception as e:
            logger.error(f"Error in batch flush: {str(e)}")
            # Handle failure - maybe requeue items
    
    def _flush_loop(self):
        while True:
            time.sleep(0.1)  # Short sleep to prevent CPU spin
            
            current_time = time.time()
            if current_time - self.last_flush >= self.flush_interval:
                self.flush()
```

### 2. Asynchronous Processing

Consider using asynchronous event handlers for non-critical paths:

```python
import asyncio
from concurrent.futures import ThreadPoolExecutor

class AsyncEventProcessor:
    def __init__(self, max_workers=10):
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.loop = asyncio.get_event_loop()
    
    def handle_event(self, event_type, data):
        # Submit to thread pool
        self.executor.submit(self._process_event, event_type, data)
    
    def _process_event(self, event_type, data):
        # Process in background thread
        try:
            if event_type == EventType.ORDER_ADDED:
                # Handle order added
                pass
            elif event_type == EventType.TRADE_EXECUTED:
                # Handle trade
                pass
        except Exception as e:
            logger.error(f"Error processing event: {str(e)}")
```

## Troubleshooting

### Common Integration Issues

1. **Event Handling Exceptions**: Ensure all event handlers have proper exception handling to prevent one bad event from breaking the system.

2. **Order Timestamp Confusion**: When restoring order books from storage, make sure to maintain the original timestamps to preserve price-time priority.

3. **Race Conditions**: Be careful with concurrent operations, especially during startup/recovery when initializing from storage.

4. **Database Connection Issues**: Implement retries and connection pooling for database operations.

5. **Memory Leaks**: Watch for accumulating event subscribers or cached data that isn't being cleaned up.

### Debugging Tools

Create debugging utilities to inspect the state of the system:

```python
def debug_orderbook_state(orderbook, storage):
    """Compare and print orderbook vs storage state."""
    ob_snapshot = orderbook.get_snapshot(depth=0)  # Full depth
    storage_snapshot = storage.get_active_orders_snapshot()
    
    print("Order Book Bids:", len(ob_snapshot["bids"]))
    print("Storage Bids:", len(storage_snapshot["bids"]))
    print("Order Book Asks:", len(ob_snapshot["asks"]))
    print("Storage Asks:", len(storage_snapshot["asks"]))
    
    # Find discrepancies
    ob_bid_prices = {level["price"] for level in ob_snapshot["bids"]}
    storage_bid_prices = {level["price"] for level in storage_snapshot["bids"]}
    
    print("Bid prices in OB but not storage:", ob_bid_prices - storage_bid_prices)
    print("Bid prices in storage but not OB:", storage_bid_prices - ob_bid_prices)
    
    # Similar checks for asks...
```

### Health Monitoring

Implement health check endpoints to monitor the system:

```python
def get_system_health():
    return {
        "orderbook": {
            "status": "healthy",
            "bid_levels": len(orderbook.get_snapshot()["bids"]),
            "ask_levels": len(orderbook.get_snapshot()["asks"]),
            "last_trade_time": orderbook.last_trade_time if hasattr(orderbook, "last_trade_time") else None
        },
        "storage": {
            "status": storage.check_connection(),
            "pending_writes": storage.get_pending_write_count() if hasattr(storage, "get_pending_write_count") else None
        },
        "event_manager": {
            "subscribers": event_manager.get_subscriber_count()
        }
    }
```

## Conclusion

By following these integration patterns, you can build a robust cryptocurrency exchange system that leverages the high-performance Manticore OrderBook while maintaining clean separation of concerns. The event-driven architecture allows for flexibility and extensibility as your requirements evolve. 