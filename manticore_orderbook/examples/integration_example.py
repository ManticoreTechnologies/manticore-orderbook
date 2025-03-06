"""
Integration example showing how to connect Manticore OrderBook with external modules.

This example demonstrates how to:
1. Set up event handlers to integrate with a storage system
2. Use the event system for monitoring and logging
3. Implement simple persistence patterns
"""

from manticore_orderbook import OrderBook, EventManager, EventType
import json
import time


class MockStorageClient:
    """Mock implementation of a storage client to demonstrate integration."""
    
    def __init__(self):
        self.orders = {}
        self.trades = []
        self.price_levels = {"buy": {}, "sell": {}}
        
    def save_order(self, order_data):
        """Save an order to storage."""
        self.orders[order_data["order_id"]] = order_data
        print(f"Storage: Saved order {order_data['order_id']}")
        
    def update_order(self, order_id, order_data):
        """Update an existing order in storage."""
        if order_id in self.orders:
            self.orders[order_id] = order_data
            print(f"Storage: Updated order {order_id}")
            
    def cancel_order(self, order_id):
        """Mark an order as cancelled in storage."""
        if order_id in self.orders:
            self.orders[order_id]["status"] = "cancelled"
            print(f"Storage: Marked order {order_id} as cancelled")
            
    def save_trade(self, trade_data):
        """Save a trade to storage."""
        self.trades.append(trade_data)
        print(f"Storage: Saved trade between {trade_data['maker_order_id']} and {trade_data['taker_order_id']}")
        
    def update_price_level(self, side, price, quantity, order_count):
        """Update a price level in storage."""
        self.price_levels[side][price] = {"quantity": quantity, "order_count": order_count}
        print(f"Storage: Updated {side} price level at {price}")
        
    def get_active_orders(self, symbol=None):
        """Get all active orders for a symbol."""
        return [order for order in self.orders.values() 
                if order.get("status") != "cancelled" and 
                (symbol is None or order.get("symbol") == symbol)]


def main():
    """Run the integration example."""
    # Create instances
    event_manager = EventManager()
    orderbook = OrderBook(symbol="BTC/USD")
    storage = MockStorageClient()
    
    print("=== Manticore OrderBook Integration Example ===\n")
    
    # Set up event handlers for integration with storage
    def handle_order_event(event_type, data):
        """Handle order-related events."""
        if event_type == EventType.ORDER_ADDED:
            storage.save_order(data)
        elif event_type == EventType.ORDER_MODIFIED:
            storage.update_order(data["order_id"], data)
        elif event_type == EventType.ORDER_CANCELLED:
            storage.cancel_order(data["order_id"])
            
    def handle_trade_event(event_type, data):
        """Handle trade events."""
        storage.save_trade(data)
        
    def handle_price_level_event(event_type, data):
        """Handle price level events."""
        if event_type in [EventType.PRICE_LEVEL_ADDED, EventType.PRICE_LEVEL_CHANGED]:
            storage.update_price_level(
                data["side"], 
                data["price"], 
                data["quantity"], 
                data["order_count"]
            )
    
    # Subscribe to events
    event_manager.subscribe(EventType.ORDER_ADDED, handle_order_event)
    event_manager.subscribe(EventType.ORDER_MODIFIED, handle_order_event)
    event_manager.subscribe(EventType.ORDER_CANCELLED, handle_order_event)
    event_manager.subscribe(EventType.TRADE_EXECUTED, handle_trade_event)
    event_manager.subscribe(EventType.PRICE_LEVEL_ADDED, handle_price_level_event)
    event_manager.subscribe(EventType.PRICE_LEVEL_CHANGED, handle_price_level_event)
    
    # Add a general event logger
    def log_all_events(event_type, data):
        """Log all events for monitoring."""
        print(f"Event: {event_type.name}, Data: {json.dumps(data, default=str)[:100]}...")
    
    event_manager.subscribe_all(log_all_events)
    
    # Demonstrate the integration
    print("\n=== Adding Orders ===")
    orderbook.add_order(side="buy", price=19500.0, quantity=1.5, order_id="bid1")
    orderbook.add_order(side="sell", price=19600.0, quantity=1.0, order_id="ask1")
    
    print("\n=== Modifying an Order ===")
    orderbook.modify_order("bid1", new_quantity=2.0)
    
    print("\n=== Executing a Trade ===")
    orderbook.add_order(side="buy", price=19650.0, quantity=0.5, order_id="bid2")
    
    print("\n=== Cancelling an Order ===")
    orderbook.cancel_order("ask1")
    
    # Show how to restore from storage
    print("\n=== Restoring OrderBook From Storage ===")
    print("Creating a new order book instance...")
    
    # Simulate application restart
    new_orderbook = OrderBook(symbol="BTC/USD")
    
    # Restore from "storage"
    active_orders = storage.get_active_orders(symbol="BTC/USD")
    print(f"Found {len(active_orders)} active orders in storage")
    
    # Sort by timestamp to maintain proper time priority
    sorted_orders = sorted(active_orders, key=lambda x: x.get("timestamp", 0))
    
    # Add to orderbook in order
    for order_data in sorted_orders:
        try:
            new_orderbook.add_order(
                side=order_data["side"],
                price=order_data["price"],
                quantity=order_data["quantity"],
                order_id=order_data["order_id"],
                user_id=order_data.get("user_id")
            )
            print(f"Restored order {order_data['order_id']}")
        except Exception as e:
            print(f"Failed to restore order {order_data['order_id']}: {e}")
    
    print("\n=== Restored OrderBook State ===")
    snapshot = new_orderbook.get_snapshot()
    print("Bids:")
    for bid in snapshot["bids"]:
        print(f"  {bid['quantity']} @ {bid['price']}")
    
    print("Asks:")
    for ask in snapshot["asks"]:
        print(f"  {ask['quantity']} @ {ask['price']}")


if __name__ == "__main__":
    main() 