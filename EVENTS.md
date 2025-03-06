# Manticore OrderBook Event System

The event system is a core feature of the Manticore OrderBook, enabling loose coupling between components and providing a foundation for integrating with external systems like storage, matching engines, and API servers.

## Event Types

The `EventType` enum in `manticore_orderbook.event_manager` defines all the events that can be published:

### Order Lifecycle Events

| Event Type | Description | When It's Triggered | Key Data Fields |
|------------|-------------|---------------------|-----------------|
| `ORDER_ADDED` | An order has been added to the order book | After an order is successfully added | order_id, side, price, quantity, timestamp, time_in_force, expiry_time, user_id |
| `ORDER_MODIFIED` | An existing order has been modified | After an order's price, quantity, or expiry time is changed | order_id, side, price, old_quantity, new_quantity, old_expiry_time, new_expiry_time, timestamp, user_id |
| `ORDER_CANCELLED` | An order has been cancelled | After an order is successfully removed from the book | order_id, side, price, quantity, timestamp, user_id |
| `ORDER_FILLED` | An order has been partially or fully filled | After a trade that partially or fully fills an order | order_id, fill_price, fill_quantity, remaining_quantity, timestamp, user_id, is_maker, fee |
| `ORDER_EXPIRED` | An order has expired due to time-in-force | When the expiry checker finds an expired order | order_id, side, price, quantity, expiry_time, user_id |

### Trade Events

| Event Type | Description | When It's Triggered | Key Data Fields |
|------------|-------------|---------------------|-----------------|
| `TRADE_EXECUTED` | A trade has been executed | After a successful match between orders | maker_order_id, taker_order_id, price, quantity, timestamp, maker_user_id, taker_user_id, maker_fee, taker_fee |

### Price Level Events

| Event Type | Description | When It's Triggered | Key Data Fields |
|------------|-------------|---------------------|-----------------|
| `PRICE_LEVEL_ADDED` | A new price level has been added | When the first order at a price is added | side, price, quantity, order_count |
| `PRICE_LEVEL_REMOVED` | A price level has been removed | When the last order at a price is removed | side, price, timestamp |
| `PRICE_LEVEL_CHANGED` | The quantity at a price level has changed | When orders are added/removed/modified at an existing price | side, price, quantity, order_count, timestamp |

### Book Events

| Event Type | Description | When It's Triggered | Key Data Fields |
|------------|-------------|---------------------|-----------------|
| `BOOK_UPDATED` | General update to book state | After any significant change to the book | timestamp |
| `DEPTH_CHANGED` | The top N levels of the book changed | When price levels near the top of the book change | timestamp, top_bid, top_ask |
| `SNAPSHOT_CREATED` | A snapshot of the book has been created | When a snapshot is explicitly created | symbol, timestamp |

### Market Events

| Event Type | Description | When It's Triggered | Key Data Fields |
|------------|-------------|---------------------|-----------------|
| `MARKET_CREATED` | A new market has been created | When a new order book is initialized | symbol |
| `MARKET_CLEARED` | A market has been cleared of all orders | When the order book is cleared | symbol, timestamp |
| `MARKET_DELETED` | A market has been deleted | When an order book is deleted | symbol, timestamp |

### System Events

| Event Type | Description | When It's Triggered | Key Data Fields |
|------------|-------------|---------------------|-----------------|
| `ERROR` | An error has occurred | When a significant error occurs in the system | error_type, error_message, timestamp |

## Event Data Structure

Each event published by the system includes:

- **event_type**: The type of event (from EventType enum)
- **data**: A dictionary containing event-specific data
- **timestamp**: When the event occurred
- **symbol**: The market symbol associated with the event (if applicable)

## Complete Event Payload Examples

### ORDER_ADDED Event

```python
{
    "event_type": "ORDER_ADDED",
    "data": {
        "order_id": "order123",
        "side": "buy",
        "price": 19500.0,
        "quantity": 1.5,
        "timestamp": 1645678901.123,
        "time_in_force": "GTC",
        "expiry_time": None,
        "user_id": "user456"
    },
    "timestamp": 1645678901.123,
    "symbol": "BTC/USD"
}
```

### ORDER_MODIFIED Event

```python
{
    "event_type": "ORDER_MODIFIED",
    "data": {
        "order_id": "order123",
        "side": "buy",
        "price": 19500.0,
        "old_quantity": 1.5,
        "new_quantity": 2.0,
        "old_expiry_time": None,
        "new_expiry_time": None,
        "timestamp": 1645678902.456,
        "user_id": "user456"
    },
    "timestamp": 1645678902.456,
    "symbol": "BTC/USD"
}
```

### ORDER_CANCELLED Event

```python
{
    "event_type": "ORDER_CANCELLED",
    "data": {
        "order_id": "order123",
        "side": "buy",
        "price": 19500.0,
        "quantity": 1.5,
        "timestamp": 1645678901.123,
        "user_id": "user456"
    },
    "timestamp": 1645678903.789,
    "symbol": "BTC/USD"
}
```

### ORDER_FILLED Event

```python
{
    "event_type": "ORDER_FILLED",
    "data": {
        "order_id": "order123",
        "fill_price": 19500.0,
        "fill_quantity": 1.0,
        "remaining_quantity": 0.5,
        "timestamp": 1645678904.987,
        "user_id": "user456",
        "is_maker": true,
        "fee": 0.195
    },
    "timestamp": 1645678904.987,
    "symbol": "BTC/USD"
}
```

### ORDER_EXPIRED Event

```python
{
    "event_type": "ORDER_EXPIRED",
    "data": {
        "order_id": "order123",
        "side": "buy",
        "price": 19500.0,
        "quantity": 1.5,
        "expiry_time": 1645678905.678,
        "user_id": "user456"
    },
    "timestamp": 1645678905.678,
    "symbol": "BTC/USD"
}
```

### TRADE_EXECUTED Event

```python
{
    "event_type": "TRADE_EXECUTED",
    "data": {
        "trade_id": "trade789",
        "maker_order_id": "order123", 
        "taker_order_id": "order456",
        "price": 19500.0,
        "quantity": 1.0,
        "timestamp": 1645678906.789,
        "maker_fee": 0.195,  # Based on 0.1% maker fee
        "taker_fee": 0.39,   # Based on 0.2% taker fee
        "maker_user_id": "user456",
        "taker_user_id": "user789"
    },
    "timestamp": 1645678906.789,
    "symbol": "BTC/USD"
}
```

### PRICE_LEVEL_ADDED Event

```python
{
    "event_type": "PRICE_LEVEL_ADDED",
    "data": {
        "side": "buy",
        "price": 19500.0,
        "quantity": 1.5,
        "order_count": 1
    },
    "timestamp": 1645678907.123,
    "symbol": "BTC/USD"
}
```

### PRICE_LEVEL_REMOVED Event

```python
{
    "event_type": "PRICE_LEVEL_REMOVED",
    "data": {
        "side": "buy",
        "price": 19500.0,
        "timestamp": 1645678908.456
    },
    "timestamp": 1645678908.456,
    "symbol": "BTC/USD"
}
```

### PRICE_LEVEL_CHANGED Event

```python
{
    "event_type": "PRICE_LEVEL_CHANGED",
    "data": {
        "side": "buy",
        "price": 19500.0,
        "quantity": 2.5,  # Total quantity at this price level
        "order_count": 2,  # Number of orders at this price level
        "timestamp": 1645678909.789
    },
    "timestamp": 1645678909.789,
    "symbol": "BTC/USD"
}
```

### DEPTH_CHANGED Event

```python
{
    "event_type": "DEPTH_CHANGED",
    "data": {
        "timestamp": 1645678910.123,
        "top_bid": 19500.0,  # Highest bid price
        "top_ask": 19600.0   # Lowest ask price
    },
    "timestamp": 1645678910.123,
    "symbol": "BTC/USD"
}
```

### BOOK_UPDATED Event

```python
{
    "event_type": "BOOK_UPDATED",
    "data": {
        "timestamp": 1645678911.456
    },
    "timestamp": 1645678911.456,
    "symbol": "BTC/USD"
}
```

## Integration Patterns

### 1. Storage Integration Pattern

```python
from manticore_orderbook import OrderBook, EventManager, EventType

# Create components
event_manager = EventManager()
order_book = OrderBook(symbol="BTC/USD", event_manager=event_manager)
storage_client = YourStorageClient()  # Your storage implementation

# Set up storage handlers
def persist_order(event_type, data):
    if event_type == EventType.ORDER_ADDED:
        # Save new order to storage
        storage_client.save_order(data)
    elif event_type == EventType.ORDER_MODIFIED:
        # Update existing order in storage
        storage_client.update_order(data["order_id"], data)
    elif event_type == EventType.ORDER_CANCELLED or event_type == EventType.ORDER_EXPIRED:
        # Mark order as cancelled/expired in storage
        storage_client.mark_order_inactive(data["order_id"], event_type.name.lower())

def persist_trade(event_type, data):
    # Save trade record to storage
    storage_client.save_trade(data)

def update_price_level(event_type, data):
    # Update price level information
    storage_client.update_price_level(data["side"], data["price"], 
                                    data.get("quantity", 0), 
                                    data.get("order_count", 0))

# Subscribe to events
event_manager.subscribe(EventType.ORDER_ADDED, persist_order)
event_manager.subscribe(EventType.ORDER_MODIFIED, persist_order)
event_manager.subscribe(EventType.ORDER_CANCELLED, persist_order)
event_manager.subscribe(EventType.ORDER_EXPIRED, persist_order)
event_manager.subscribe(EventType.TRADE_EXECUTED, persist_trade)
event_manager.subscribe(EventType.PRICE_LEVEL_ADDED, update_price_level)
event_manager.subscribe(EventType.PRICE_LEVEL_CHANGED, update_price_level)
event_manager.subscribe(EventType.PRICE_LEVEL_REMOVED, update_price_level)
```

### 2. WebSocket Integration Pattern

```python
from manticore_orderbook import OrderBook, EventManager, EventType

# Create components
event_manager = EventManager()
order_book = OrderBook(symbol="BTC/USD", event_manager=event_manager)
websocket_server = YourWebSocketServer()  # Your WebSocket implementation

# Set up WebSocket handlers
def push_depth_update(event_type, data):
    if event_type in [EventType.PRICE_LEVEL_ADDED, EventType.PRICE_LEVEL_CHANGED, EventType.PRICE_LEVEL_REMOVED]:
        # Get latest order book snapshot for WebSocket clients
        snapshot = order_book.get_snapshot(depth=10)
        
        # Push to all clients subscribed to order book updates
        websocket_server.broadcast(
            channel="orderbook:BTC/USD",
            message={
                "type": "depth_update",
                "data": snapshot,
                "timestamp": data["timestamp"]
            }
        )

def push_trade(event_type, data):
    # Push trade to all clients subscribed to trade updates
    websocket_server.broadcast(
        channel="trades:BTC/USD",
        message={
            "type": "trade",
            "data": data
        }
    )

# Subscribe to events
event_manager.subscribe(EventType.PRICE_LEVEL_ADDED, push_depth_update)
event_manager.subscribe(EventType.PRICE_LEVEL_CHANGED, push_depth_update)
event_manager.subscribe(EventType.PRICE_LEVEL_REMOVED, push_depth_update)
event_manager.subscribe(EventType.DEPTH_CHANGED, push_depth_update)
event_manager.subscribe(EventType.TRADE_EXECUTED, push_trade)
```

### 3. Notification Integration Pattern

```python
from manticore_orderbook import OrderBook, EventManager, EventType

# Create components
event_manager = EventManager()
order_book = OrderBook(symbol="BTC/USD", event_manager=event_manager)
notification_service = YourNotificationService()  # Your notification implementation

# Set up notification handlers
def notify_order_fill(event_type, data):
    if "user_id" in data and data["user_id"]:
        user_id = data["user_id"]
        order_id = data["order_id"]
        fill_quantity = data["fill_quantity"]
        fill_price = data["fill_price"]
        remaining = data["remaining_quantity"]
        
        # Determine if fully or partially filled
        if remaining <= 0:
            message = f"Your order {order_id} was fully filled: {fill_quantity} @ {fill_price}"
        else:
            message = f"Your order {order_id} was partially filled: {fill_quantity} @ {fill_price}, {remaining} remaining"
        
        # Send notification to user
        notification_service.send_notification(user_id, "order_fill", message)

def notify_trade(event_type, data):
    # Notify maker user
    if data.get("maker_user_id"):
        notification_service.send_notification(
            data["maker_user_id"],
            "trade",
            f"Your order {data['maker_order_id']} executed a trade: {data['quantity']} @ {data['price']}"
        )
    
    # Notify taker user
    if data.get("taker_user_id"):
        notification_service.send_notification(
            data["taker_user_id"],
            "trade",
            f"Your order {data['taker_order_id']} executed a trade: {data['quantity']} @ {data['price']}"
        )

# Subscribe to events
event_manager.subscribe(EventType.ORDER_FILLED, notify_order_fill)
event_manager.subscribe(EventType.TRADE_EXECUTED, notify_trade)
```

### 4. Risk Management Integration Pattern

```python
from manticore_orderbook import OrderBook, EventManager, EventType

# Create components
event_manager = EventManager()
order_book = OrderBook(symbol="BTC/USD", event_manager=event_manager)
risk_engine = YourRiskEngine()  # Your risk management implementation

# Set up risk handlers
def track_position(event_type, data):
    if event_type == EventType.TRADE_EXECUTED:
        # Update positions for both maker and taker
        if data.get("maker_user_id"):
            side = "sell" if data.get("maker_side", "buy") == "buy" else "buy"
            risk_engine.update_position(
                user_id=data["maker_user_id"],
                symbol="BTC/USD",
                side=side,
                quantity=data["quantity"],
                price=data["price"]
            )
        
        if data.get("taker_user_id"):
            risk_engine.update_position(
                user_id=data["taker_user_id"],
                symbol="BTC/USD",
                side=data.get("taker_side", "buy"),
                quantity=data["quantity"],
                price=data["price"]
            )

# Subscribe to events
event_manager.subscribe(EventType.TRADE_EXECUTED, track_position)
```

## Best Practices for Event-Driven Integration

1. **Keep Event Handlers Fast**: Event handlers should be quick to avoid blocking the event system. For time-consuming operations, use asynchronous processing.

2. **Implement Idempotent Handlers**: Make your event handlers idempotent to handle potential duplicate events during system recovery.

3. **Use Appropriate Event Types**: Subscribe only to the events your component needs to handle, avoiding unnecessary processing.

4. **Handle Exceptions**: Always catch and handle exceptions in your event handlers to prevent system crashes.

5. **Consider Event Batching**: For high-volume systems, consider batching event processing to reduce system load.

6. **Maintain Event History**: Use the event history for recovery, debugging, and auditing purposes.

7. **Standardize Event Handling**: Create consistent patterns for handling different event types across your system.

8. **Test Event Integrations**: Thoroughly test your event handlers with realistic data and failure scenarios. 