#!/usr/bin/env python3
"""
Stress tests for the Manticore OrderBook implementation.

These tests verify the orderbook's stability and correctness under
stressful conditions including high volumes, rapid order changes,
and potentially invalid operations.
"""

import unittest
import logging
import random
import threading
import time
import concurrent.futures
from collections import defaultdict
from manticore_orderbook import OrderBook, EventManager, EventType

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('orderbook_stress_test')


class OrderBookStressTest(unittest.TestCase):
    """Stress tests for the OrderBook implementation."""
    
    def setUp(self):
        """Set up testing environment."""
        self.event_manager = EventManager()
        self.orderbook = OrderBook(
            symbol="BTC/USD",
            event_manager=self.event_manager,
            enable_price_improvement=True,
            maker_fee_rate=0.001,
            taker_fee_rate=0.002
        )
        
        # Track events for verification
        self.event_counts = defaultdict(int)
        self.events_lock = threading.Lock()
        
        # Subscribe to all event types
        for event_type in EventType:
            self.event_manager.subscribe(event_type, self._event_handler)
    
    def _event_handler(self, event_type, data):
        """Handle events and count them by type."""
        with self.events_lock:
            self.event_counts[event_type] += 1
    
    def tearDown(self):
        """Clean up after tests."""
        self.orderbook.clear()
        self.event_counts.clear()
    
    def test_concurrent_order_operations(self):
        """Test concurrent order operations."""
        # Number of threads and operations per thread
        num_threads = 10
        ops_per_thread = 100
        
        # Track created order IDs for verification
        created_order_ids = []
        order_ids_lock = threading.Lock()
        
        def worker_thread(thread_id):
            """Worker function for concurrent operations."""
            local_order_ids = []
            
            for i in range(ops_per_thread):
                op_type = random.choice(['add', 'cancel', 'modify'])
                
                if op_type == 'add' or not local_order_ids:
                    # Add a new order
                    side = 'buy' if random.random() < 0.5 else 'sell'
                    price_base = 9000 if side == 'buy' else 11000
                    price = price_base + (random.random() * 1000)
                    quantity = 0.1 + (random.random() * 0.9)
                    
                    order_id = self.orderbook.add_order(
                        side=side,
                        price=price,
                        quantity=quantity,
                        order_id=f"t{thread_id}_op{i}"
                    )
                    
                    # Check if order was added (not fully matched)
                    if self.orderbook.get_order(order_id):
                        local_order_ids.append(order_id)
                        with order_ids_lock:
                            created_order_ids.append(order_id)
                
                elif op_type == 'cancel' and local_order_ids:
                    # Cancel a previously added order
                    order_id = random.choice(local_order_ids)
                    result = self.orderbook.cancel_order(order_id)
                    
                    if result:
                        local_order_ids.remove(order_id)
                
                elif op_type == 'modify' and local_order_ids:
                    # Modify a previously added order
                    order_id = random.choice(local_order_ids)
                    order = self.orderbook.get_order(order_id)
                    
                    if order:
                        new_quantity = order["quantity"] * (0.5 + (random.random() * 1.0))
                        
                        # Sometimes modify price
                        if random.random() < 0.3:
                            if order["side"] == "buy":
                                # Adjust buy price down to avoid crossing
                                new_price = order["price"] * 0.95
                            else:
                                # Adjust sell price up to avoid crossing
                                new_price = order["price"] * 1.05
                        else:
                            new_price = None
                        
                        self.orderbook.modify_order(
                            order_id=order_id,
                            new_quantity=new_quantity,
                            new_price=new_price
                        )
        
        # Launch threads
        start_time = time.time()
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(worker_thread, i) for i in range(num_threads)]
            concurrent.futures.wait(futures)
        
        end_time = time.time()
        elapsed = end_time - start_time
        
        # Log results
        logger.info(f"Concurrent test completed in {elapsed:.2f} seconds")
        logger.info(f"Total operations: {num_threads * ops_per_thread}")
        logger.info(f"Operations per second: {(num_threads * ops_per_thread) / elapsed:.2f}")
        
        # Verify the orderbook is in a valid state
        self._verify_orderbook_state()
        
        # Log event counts
        with self.events_lock:
            for event_type, count in self.event_counts.items():
                logger.info(f"Event {event_type}: {count}")
    
    def test_rapid_crossing_orders(self):
        """Test rapid addition of crossing orders."""
        # Track trade execution counts
        trade_count = 0
        
        def trade_counter(event_type, data):
            nonlocal trade_count
            if event_type == EventType.TRADE_EXECUTED:
                trade_count += 1
        
        # Subscribe to trade events
        self.event_manager.subscribe(EventType.TRADE_EXECUTED, trade_counter)
        
        # Create initial book state
        for i in range(50):
            # Add buys from 9000-9490
            self.orderbook.add_order(
                side="buy",
                price=9000 + (i * 10),
                quantity=1.0,
                order_id=f"init_buy_{i}"
            )
            
            # Add sells from 10500-10990
            self.orderbook.add_order(
                side="sell",
                price=10500 + (i * 10),
                quantity=1.0,
                order_id=f"init_sell_{i}"
            )
        
        # Add a rapid series of crossing orders
        num_crossing_orders = 100
        start_time = time.time()
        
        for i in range(num_crossing_orders):
            # Alternate between crossing buys and sells
            if i % 2 == 0:
                # Add a buy that crosses the lowest sell
                self.orderbook.add_order(
                    side="buy",
                    price=11000,  # Well above lowest ask
                    quantity=0.5,
                    order_id=f"cross_buy_{i}"
                )
            else:
                # Add a sell that crosses the highest buy
                self.orderbook.add_order(
                    side="sell",
                    price=9000,  # Well below highest bid
                    quantity=0.5,
                    order_id=f"cross_sell_{i}"
                )
        
        end_time = time.time()
        elapsed = end_time - start_time
        
        # Log results
        logger.info(f"Rapid crossing test completed in {elapsed:.2f} seconds")
        logger.info(f"Orders per second: {num_crossing_orders / elapsed:.2f}")
        logger.info(f"Trades executed: {trade_count}")
        
        # Verify that trades were executed
        self.assertGreater(trade_count, 0)
        
        # Verify the orderbook is in a valid state
        self._verify_orderbook_state()
    
    def test_invalid_order_handling(self):
        """Test that invalid orders are handled correctly."""
        # Test adding order with invalid side
        with self.assertRaises(ValueError):
            self.orderbook.add_order(
                side="invalid_side",
                price=10000,
                quantity=1.0
            )
        
        # Test adding order with invalid price
        with self.assertRaises(ValueError):
            self.orderbook.add_order(
                side="buy",
                price=-1000,  # Negative price
                quantity=1.0
            )
        
        # Test adding order with invalid quantity
        with self.assertRaises(ValueError):
            self.orderbook.add_order(
                side="buy",
                price=10000,
                quantity=0  # Zero quantity
            )
        
        # Test modifying a non-existent order
        result = self.orderbook.modify_order(
            order_id="non_existent_order",
            new_quantity=2.0
        )
        self.assertFalse(result)
        
        # Test canceling a non-existent order
        result = self.orderbook.cancel_order("non_existent_order")
        self.assertFalse(result)
        
        # Verify the orderbook is still in a valid state
        self._verify_orderbook_state()
    
    def test_order_spam_stability(self):
        """Test stability under order spam conditions."""
        # Create a large number of small orders
        num_orders = 5000
        start_time = time.time()
        
        for i in range(num_orders):
            side = "buy" if i % 2 == 0 else "sell"
            base_price = 9000 if side == "buy" else 11000
            
            # Create a slightly different price for each order to test price level handling
            price = base_price + (i % 100)
            quantity = 0.01  # Very small quantity
            
            self.orderbook.add_order(
                side=side,
                price=price,
                quantity=quantity,
                order_id=f"spam_{i}"
            )
            
            # Occasionally cancel or modify some orders
            if i % 10 == 0 and i > 0:
                self.orderbook.cancel_order(f"spam_{i-5}")
            elif i % 15 == 0 and i > 0:
                self.orderbook.modify_order(
                    order_id=f"spam_{i-10}",
                    new_quantity=0.02
                )
        
        end_time = time.time()
        elapsed = end_time - start_time
        
        # Log results
        logger.info(f"Order spam test completed in {elapsed:.2f} seconds")
        logger.info(f"Orders per second: {num_orders / elapsed:.2f}")
        
        # Get a snapshot of the final state
        snapshot = self.orderbook.get_snapshot()
        buy_levels = len(snapshot["bids"])
        sell_levels = len(snapshot["asks"])
        
        logger.info(f"Final orderbook state: {buy_levels} buy levels, {sell_levels} sell levels")
        
        # Verify the orderbook is in a valid state
        self._verify_orderbook_state()
    
    def _verify_orderbook_state(self):
        """Verify that the orderbook is in a valid state."""
        snapshot = self.orderbook.get_snapshot()
        
        # Check if the book is crossed
        if snapshot["bids"] and snapshot["asks"]:
            highest_bid = max(level["price"] for level in snapshot["bids"])
            lowest_ask = min(level["price"] for level in snapshot["asks"])
            
            self.assertLess(highest_bid, lowest_ask, 
                           f"Orderbook is crossed: highest bid {highest_bid} >= lowest ask {lowest_ask}")
        
        # Verify quantity invariants
        for bid in snapshot["bids"]:
            self.assertGreater(bid["quantity"], 0, "Bid quantity must be positive")
            self.assertGreater(bid["price"], 0, "Bid price must be positive")
        
        for ask in snapshot["asks"]:
            self.assertGreater(ask["quantity"], 0, "Ask quantity must be positive")
            self.assertGreater(ask["price"], 0, "Ask price must be positive")


if __name__ == "__main__":
    unittest.main() 