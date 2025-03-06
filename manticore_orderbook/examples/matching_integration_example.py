"""
Example demonstrating integration between manticore-orderbook and a hypothetical matching engine.

This example shows:
1. How to intercept orders before they're processed by the order book
2. How to delegate special order types to a specialized matching engine
3. How to handle orders with custom matching algorithms
"""

from manticore_orderbook import OrderBook, EventManager, EventType
import time


class MockMatchingEngine:
    """Mock implementation of a matching engine to demonstrate integration."""
    
    def __init__(self, order_book):
        """Initialize with a reference to the order book."""
        self.order_book = order_book
        
    def process_iceberg_order(self, side, price, display_quantity, total_quantity, order_id=None):
        """Process an iceberg order by splitting it into visible and hidden portions."""
        print(f"MatchingEngine: Processing iceberg order with {display_quantity}/{total_quantity} visible")
        
        # Generate a unique order ID if not provided
        if not order_id:
            order_id = f"iceberg-{int(time.time()*1000)}"
            
        # Add the visible portion to the order book
        visible_order_id = f"{order_id}-visible"
        self.order_book.add_order(
            side=side,
            price=price,
            quantity=display_quantity,
            order_id=visible_order_id,
            metadata={"is_iceberg": True, "parent_id": order_id}
        )
        
        # Track the hidden portion
        self.hidden_quantity = total_quantity - display_quantity
        self.parent_order_id = order_id
        
        print(f"MatchingEngine: Added visible portion {display_quantity} @ {price}")
        print(f"MatchingEngine: Reserved hidden portion {self.hidden_quantity}")
        
        return visible_order_id
    
    def handle_fill(self, event_type, data):
        """Handle fill events to replenish iceberg orders."""
        # Skip if not a fill event
        if event_type != EventType.ORDER_FILLED:
            return
            
        # Check if this is an iceberg order
        order_id = data.get("order_id")
        metadata = data.get("metadata", {})
        
        if metadata and metadata.get("is_iceberg") and hasattr(self, "hidden_quantity"):
            # Order was fully filled
            if data.get("remaining_quantity", 0) == 0 and self.hidden_quantity > 0:
                display_quantity = min(data.get("original_quantity", 0), self.hidden_quantity)
                
                # Add a new visible portion
                new_visible_id = f"{metadata['parent_id']}-visible-{int(time.time()*1000)}"
                self.order_book.add_order(
                    side=data.get("side"),
                    price=data.get("price"),
                    quantity=display_quantity,
                    order_id=new_visible_id,
                    metadata={"is_iceberg": True, "parent_id": metadata["parent_id"]}
                )
                
                print(f"MatchingEngine: Replenished iceberg with {display_quantity} @ {data.get('price')}")
                
                self.hidden_quantity -= display_quantity
    
    def calculate_pro_rata_allocation(self, orders, total_quantity):
        """Demonstrate a more complex matching algorithm with pro-rata allocation."""
        total_available = sum(order.get("quantity", 0) for order in orders)
        
        if total_available <= 0:
            return []
            
        allocations = []
        for order in orders:
            # Calculate percentage of total
            percentage = order.get("quantity", 0) / total_available
            allocation = min(order.get("quantity", 0), percentage * total_quantity)
            
            allocations.append({
                "order_id": order.get("order_id"),
                "allocation": allocation
            })
            
        print(f"MatchingEngine: Pro-rata allocated {total_quantity} units across {len(orders)} orders")
        return allocations


def main():
    """Run the matching integration example."""
    # Create components
    event_manager = EventManager()
    order_book = OrderBook(symbol="BTC/USD")
    matching_engine = MockMatchingEngine(order_book)
    
    print("=== Manticore OrderBook + Matching Engine Integration Example ===\n")
    
    # Set up event handlers for integration with matching engine
    event_manager.subscribe(EventType.ORDER_FILLED, matching_engine.handle_fill)
    
    # Define a pre-processor for intercepting orders with special requirements
    def preprocess_order(order_type, side, price, quantity, order_id=None, **kwargs):
        """Preprocess orders to handle special order types."""
        if order_type == "iceberg":
            # Get the display size
            display_quantity = kwargs.get("display_quantity", quantity * 0.1)
            
            # Let the matching engine handle it
            return matching_engine.process_iceberg_order(
                side=side,
                price=price,
                display_quantity=display_quantity,
                total_quantity=quantity,
                order_id=order_id
            )
        
        # For regular orders, just add directly to the order book
        return order_book.add_order(
            side=side,
            price=price,
            quantity=quantity,
            order_id=order_id,
            **kwargs
        )
    
    # Add some regular orders
    print("\n=== Adding Regular Orders ===")
    preprocess_order(
        order_type="limit", 
        side="buy", 
        price=19500.0, 
        quantity=1.5, 
        order_id="reg-bid1"
    )
    preprocess_order(
        order_type="limit", 
        side="sell", 
        price=19600.0, 
        quantity=1.0, 
        order_id="reg-ask1"
    )
    
    # Add an iceberg order
    print("\n=== Adding Iceberg Order ===")
    preprocess_order(
        order_type="iceberg",
        side="buy",
        price=19550.0,
        quantity=10.0,  # Total size
        display_quantity=2.0,  # Visible size
        order_id="iceberg-bid1"
    )
    
    # Show current state
    print("\n=== Current OrderBook State ===")
    snapshot = order_book.get_snapshot()
    print("Bids:")
    for bid in snapshot["bids"]:
        print(f"  {bid['quantity']} @ {bid['price']}")
    
    print("Asks:")
    for ask in snapshot["asks"]:
        print(f"  {ask['quantity']} @ {ask['price']}")
    
    # Execute a trade that fills part of the iceberg
    print("\n=== Executing Trade That Fills Iceberg ===")
    order_book.add_order(side="sell", price=19550.0, quantity=2.0, order_id="matching-ask1")
    
    # Show updated state after replenishment
    print("\n=== OrderBook State After Iceberg Replenishment ===")
    snapshot = order_book.get_snapshot()
    print("Bids:")
    for bid in snapshot["bids"]:
        print(f"  {bid['quantity']} @ {bid['price']}")
    
    # Demonstrate a pro-rata matching algorithm
    print("\n=== Pro-Rata Matching Algorithm ===")
    # Create multiple orders at the same price level
    orders = [
        {"order_id": "pro1", "quantity": 5.0, "price": 19500.0},
        {"order_id": "pro2", "quantity": 3.0, "price": 19500.0},
        {"order_id": "pro3", "quantity": 2.0, "price": 19500.0}
    ]
    
    # Calculate pro-rata allocation
    allocations = matching_engine.calculate_pro_rata_allocation(orders, 5.0)
    
    print("Pro-rata allocations for 5.0 units:")
    for allocation in allocations:
        print(f"  Order {allocation['order_id']}: {allocation['allocation']:.2f} units")


if __name__ == "__main__":
    main() 