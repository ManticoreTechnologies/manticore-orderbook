# Integrating Manticore OrderBook

This guide provides detailed instructions on how to integrate the Manticore OrderBook module with other components of your cryptocurrency exchange system.

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

## Integration with Storage Systems

The storage module handles persistent storage of order data, trade history, and other information needed for an exchange. Here's how to integrate the two modules:

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
    
    # Add orders to the orderbook
    for order in sorted_orders:
        orderbook.add_order(
            order_id=order["order_id"],
            side=order["side"],
            price=order["price"],
            quantity=order["quantity"],
            time_in_force=order["time_in_force"],
            expiry_time=order["expiry_time"],
            user_id=order["user_id"],
            order_type=order["order_type"]
        )
```

## Integration with API Servers

To integrate Manticore OrderBook with a REST or WebSocket API server:

```python
from flask import Flask, request, jsonify
from manticore_orderbook import OrderBook

app = Flask(__name__)
orderbook = OrderBook(symbol="BTC/USD")

@app.route('/api/orders', methods=['POST'])
def place_order():
    data = request.json
    
    try:
        order_id = orderbook.add_order(
            side=data['side'],
            price=data.get('price'),  # None for market orders
            quantity=data['quantity'],
            order_id=data.get('client_order_id'),  # Optional client-provided ID
            time_in_force=data.get('time_in_force', 'GTC'),
            user_id=data.get('user_id')
        )
        
        return jsonify({
            "status": "success",
            "order_id": order_id
        }), 201
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 400

@app.route('/api/orders/<order_id>', methods=['DELETE'])
def cancel_order(order_id):
    success = orderbook.cancel_order(order_id)
    
    if success:
        return jsonify({
            "status": "success",
            "message": f"Order {order_id} cancelled"
        }), 200
    else:
        return jsonify({
            "status": "error",
            "message": f"Order {order_id} not found or already filled"
        }), 404

@app.route('/api/orderbook', methods=['GET'])
def get_orderbook():
    depth = request.args.get('depth', default=10, type=int)
    snapshot = orderbook.get_snapshot(depth=depth)
    
    return jsonify(snapshot), 200
```

## Best Practices

1. **Error Handling**: Always wrap order operations in try-except blocks to handle invalid orders gracefully.

2. **Batch Operations**: When loading multiple orders, use batch operations when available to improve performance.

3. **Consistency Checks**: Periodically verify that the database state and in-memory orderbook state are consistent.

4. **Event Ordering**: Be aware of event ordering when subscribing to multiple event types. Some operations may depend on events being processed in a specific order.

5. **Connection Management**: Implement reconnection logic for database connections and ensure proper cleanup on shutdown. 