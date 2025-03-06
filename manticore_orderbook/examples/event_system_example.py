"""
Event System example demonstrating how to use the Manticore OrderBook event system.

This example shows:
1. How to subscribe to specific events
2. How to use event data in external systems
3. How to build modular components that interact only via events
"""

from manticore_orderbook import OrderBook, EventManager, EventType
import time
import json
from collections import defaultdict
from tabulate import tabulate


class EventLogger:
    """Component that logs all events to demonstrate monitoring capabilities."""
    
    def __init__(self):
        self.event_counts = defaultdict(int)
        self.events = []
        
    def log_event(self, event_type, data):
        """Log an event and update statistics."""
        self.event_counts[event_type.name] += 1
        self.events.append({
            "timestamp": time.time(),
            "type": event_type.name,
            "data": data
        })
        
        # Simple log message
        print(f"EVENT: {event_type.name} - {json.dumps(data, default=str)[:80]}")
        
    def print_summary(self):
        """Print a summary of events received."""
        print("\n=== Event Summary ===")
        summary = [(event_type, count) for event_type, count in self.event_counts.items()]
        print(tabulate(summary, headers=["Event Type", "Count"], tablefmt="simple"))


class WebSocketEmulator:
    """Simulates a WebSocket server that would broadcast order book updates to clients."""
    
    def __init__(self):
        self.connected_clients = 0
        self.messages_sent = 0
        
    def connect_client(self):
        """Simulate a client connection."""
        self.connected_clients += 1
        print(f"WebSocket: Client connected. Total clients: {self.connected_clients}")
        
    def disconnect_client(self):
        """Simulate a client disconnection."""
        if self.connected_clients > 0:
            self.connected_clients -= 1
            print(f"WebSocket: Client disconnected. Total clients: {self.connected_clients}")
    
    def handle_order_book_event(self, event_type, data):
        """Handle an order book event by sending to all connected clients."""
        if self.connected_clients > 0:
            # In a real implementation, this would serialize and send to clients
            message = {
                "type": event_type.name,
                "data": data,
                "timestamp": time.time()
            }
            
            self.messages_sent += 1
            
            # Print every 5 messages to avoid cluttering the output
            if self.messages_sent % 5 == 0:
                print(f"WebSocket: Broadcast message to {self.connected_clients} clients")


class NotificationService:
    """Simulates a notification service for important order book events."""
    
    def __init__(self):
        self.user_preferences = {
            "user1": {
                "order_filled": True,
                "trade_executed": True
            },
            "user2": {
                "order_filled": True,
                "order_cancelled": True
            }
        }
        
    def handle_order_filled(self, event_type, data):
        """Handle ORDER_FILLED events to send user notifications."""
        if event_type != EventType.ORDER_FILLED:
            return
            
        user_id = data.get("user_id")
        if not user_id:
            return
            
        # Check if user wants notifications for this event
        preferences = self.user_preferences.get(user_id, {})
        if preferences.get("order_filled", False):
            # In a real implementation, this would send an actual notification
            print(f"Notification: User {user_id} notified about fill for order {data['order_id']}")
    
    def handle_trade_executed(self, event_type, data):
        """Handle TRADE_EXECUTED events to send user notifications."""
        if event_type != EventType.TRADE_EXECUTED:
            return
            
        # Notify both maker and taker
        maker_id = data.get("maker_user_id")
        taker_id = data.get("taker_user_id")
        
        for user_id in [maker_id, taker_id]:
            if not user_id:
                continue
                
            # Check if user wants notifications for this event
            preferences = self.user_preferences.get(user_id, {})
            if preferences.get("trade_executed", False):
                # In a real implementation, this would send an actual notification
                print(f"Notification: User {user_id} notified about trade execution")


def main():
    """Run the event system example."""
    # Create components
    event_manager = EventManager()
    order_book = OrderBook(symbol="BTC/USD", event_manager=event_manager)
    
    # Create auxiliary systems
    logger = EventLogger()
    websocket = WebSocketEmulator()
    notifications = NotificationService()
    
    print("=== Manticore OrderBook Event System Example ===\n")
    
    # Set up event subscriptions
    
    # Logger subscribes to all events
    event_manager.subscribe_all(logger.log_event)
    
    # WebSocket subscribes to selected events that clients need
    event_manager.subscribe(EventType.ORDER_ADDED, websocket.handle_order_book_event)
    event_manager.subscribe(EventType.ORDER_CANCELLED, websocket.handle_order_book_event)
    event_manager.subscribe(EventType.PRICE_LEVEL_ADDED, websocket.handle_order_book_event)
    event_manager.subscribe(EventType.PRICE_LEVEL_REMOVED, websocket.handle_order_book_event)
    event_manager.subscribe(EventType.BOOK_UPDATED, websocket.handle_order_book_event)
    
    # Notification service subscribes to user-specific events
    event_manager.subscribe(EventType.ORDER_FILLED, notifications.handle_order_filled)
    event_manager.subscribe(EventType.TRADE_EXECUTED, notifications.handle_trade_executed)
    
    # Connect some simulated clients
    for _ in range(3):
        websocket.connect_client()
    
    # Perform some order book operations
    print("\n=== Adding Orders ===")
    order_book.add_order(side="buy", price=19500.0, quantity=1.0, order_id="order1", user_id="user1")
    order_book.add_order(side="buy", price=19450.0, quantity=2.0, order_id="order2", user_id="user1")
    order_book.add_order(side="sell", price=19600.0, quantity=1.5, order_id="order3", user_id="user2")
    
    # Let a client disconnect
    websocket.disconnect_client()
    
    # More operations
    print("\n=== Matching Orders ===")
    order_book.add_order(side="sell", price=19450.0, quantity=0.5, order_id="order4", user_id="user2")
    
    print("\n=== Cancelling an Order ===")
    order_book.cancel_order("order2")
    
    # Print event summary
    logger.print_summary()
    
    print("\n=== Final OrderBook State ===")
    snapshot = order_book.get_snapshot()
    print("Bids:")
    for bid in snapshot["bids"]:
        print(f"  {bid['quantity']} @ {bid['price']}")
    
    print("Asks:")
    for ask in snapshot["asks"]:
        print(f"  {ask['quantity']} @ {ask['price']}")


if __name__ == "__main__":
    main() 