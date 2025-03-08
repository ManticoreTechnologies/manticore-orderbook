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

## Using the Event System

### Subscribing to Events

To listen for specific events, you can subscribe a handler function to one or more event types:

```python
from manticore_orderbook import OrderBook
from manticore_orderbook.enums import EventType

# Create an order book
orderbook = OrderBook("BTC/USD")

# Define your event handler function
def on_trade(event_type, data):
    print(f"Trade executed: {data['quantity']} @ {data['price']}")
    print(f"Maker: {data['maker_order_id']}, Taker: {data['taker_order_id']}")

# Subscribe to trade events
orderbook.event_manager.subscribe(EventType.TRADE_EXECUTED, on_trade)
```

### Handling Multiple Event Types

You can subscribe a single handler to multiple event types:

```python
def order_lifecycle_handler(event_type, data):
    if event_type == EventType.ORDER_ADDED:
        print(f"Order added: {data['order_id']}")
    elif event_type == EventType.ORDER_MODIFIED:
        print(f"Order modified: {data['order_id']}")
    elif event_type == EventType.ORDER_CANCELLED:
        print(f"Order cancelled: {data['order_id']}")
    elif event_type == EventType.ORDER_FILLED:
        print(f"Order filled: {data['order_id']}, quantity: {data['fill_quantity']}")

# Subscribe to multiple events
for event_type in [EventType.ORDER_ADDED, EventType.ORDER_MODIFIED, 
                  EventType.ORDER_CANCELLED, EventType.ORDER_FILLED]:
    orderbook.event_manager.subscribe(event_type, order_lifecycle_handler)
```

### Unsubscribing from Events

You can unsubscribe a handler when you no longer need it:

```python
# Unsubscribe from an event
orderbook.event_manager.unsubscribe(EventType.TRADE_EXECUTED, on_trade)

# Unsubscribe from all events (for a specific handler)
orderbook.event_manager.unsubscribe_all(order_lifecycle_handler)
```

### Subscribing to All Events

For logging or monitoring purposes, you might want to subscribe to all events:

```python
def log_all_events(event_type, data):
    print(f"Event: {event_type}, Data: {data}")

# Subscribe to all events
orderbook.event_manager.subscribe_all(log_all_events)
```

## Example: Building a WebSocket Feed

Here's how you could use the event system to build a real-time WebSocket feed:

```python
from flask import Flask
from flask_socketio import SocketIO
from manticore_orderbook import OrderBook
from manticore_orderbook.enums import EventType

app = Flask(__name__)
socketio = SocketIO(app)
orderbook = OrderBook("BTC/USD")

# Send events to WebSocket clients
def emit_event(event_type, data):
    event_name = str(event_type).replace('EventType.', '').lower()
    socketio.emit(event_name, data)

# Subscribe to all relevant events
for event_type in [EventType.ORDER_ADDED, EventType.ORDER_CANCELLED, 
                  EventType.ORDER_FILLED, EventType.TRADE_EXECUTED,
                  EventType.BOOK_UPDATED]:
    orderbook.event_manager.subscribe(event_type, emit_event)

# WebSocket endpoint to get the current order book
@socketio.on('get_orderbook')
def handle_get_orderbook():
    snapshot = orderbook.get_snapshot(depth=20)
    return snapshot

if __name__ == '__main__':
    socketio.run(app, debug=True)
``` 