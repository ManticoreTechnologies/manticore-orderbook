"""
Performance test suite for the order book.

Tests the performance of the order book under various load scenarios.
"""

import unittest
import time
import random
import statistics
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict, Any

from manticore_orderbook import OrderBook, MarketManager, EventManager


class PerformanceTest(unittest.TestCase):
    """Base class for performance tests."""
    
    def setUp(self):
        """Set up the test case."""
        self.event_manager = EventManager(enable_logging=False)
        self.orderbook = OrderBook(
            symbol="TEST/USD",
            enable_logging=False,
            event_manager=self.event_manager
        )
        self.market_manager = MarketManager(enable_logging=False)
        self.market_manager.create_market(
            symbol="TEST/USD",
            event_manager=self.event_manager
        )
    
    def tearDown(self):
        """Clean up after the test."""
        self.orderbook.clear()
    
    def generate_random_price(self, base_price=10000.0, volatility=0.05):
        """Generate a random price."""
        return base_price * (1 + random.uniform(-volatility, volatility))
    
    def generate_random_quantity(self, min_qty=0.1, max_qty=10.0):
        """Generate a random quantity."""
        return random.uniform(min_qty, max_qty)


class TestBasicOperations(PerformanceTest):
    """Test the performance of basic order book operations."""
    
    def test_add_order_performance(self):
        """Test the performance of adding orders."""
        num_orders = 10000
        latencies = []
        
        # Add orders and measure latency
        for i in range(num_orders):
            side = "buy" if random.random() < 0.5 else "sell"
            price = self.generate_random_price()
            quantity = self.generate_random_quantity()
            
            start_time = time.time()
            self.orderbook.add_order(
                side=side,
                price=price,
                quantity=quantity,
                order_id=f"order{i}"
            )
            latency = (time.time() - start_time) * 1000  # Convert to ms
            latencies.append(latency)
        
        # Calculate statistics
        avg_latency = statistics.mean(latencies)
        median_latency = statistics.median(latencies)
        p95_latency = sorted(latencies)[int(num_orders * 0.95)]
        
        print(f"\nAdd Order Performance ({num_orders} orders):")
        print(f"  Average latency: {avg_latency:.2f} ms")
        print(f"  Median latency: {median_latency:.2f} ms")
        print(f"  95th percentile: {p95_latency:.2f} ms")
        
        # Basic assertion to catch severe performance regressions
        self.assertLess(median_latency, 1.0, "Median add order latency exceeds 1ms")
    
    def test_snapshot_performance(self):
        """Test the performance of getting order book snapshots."""
        num_orders = 10000
        num_snapshots = 1000
        
        # Add orders to create a realistic book
        for i in range(num_orders):
            side = "buy" if random.random() < 0.5 else "sell"
            price = self.generate_random_price()
            quantity = self.generate_random_quantity()
            
            self.orderbook.add_order(
                side=side,
                price=price,
                quantity=quantity,
                order_id=f"order{i}"
            )
        
        # Measure snapshot latency
        latencies = []
        for i in range(num_snapshots):
            start_time = time.time()
            snapshot = self.orderbook.get_snapshot(depth=10)
            latency = (time.time() - start_time) * 1000  # Convert to ms
            latencies.append(latency)
        
        # Calculate statistics
        avg_latency = statistics.mean(latencies)
        median_latency = statistics.median(latencies)
        p95_latency = sorted(latencies)[int(num_snapshots * 0.95)]
        
        print(f"\nSnapshot Performance ({num_snapshots} snapshots):")
        print(f"  Average latency: {avg_latency:.2f} ms")
        print(f"  Median latency: {median_latency:.2f} ms")
        print(f"  95th percentile: {p95_latency:.2f} ms")
        
        # Basic assertion to catch severe performance regressions
        self.assertLess(median_latency, 0.5, "Median snapshot latency exceeds 0.5ms")
    
    def test_matching_performance(self):
        """Test the performance of order matching."""
        # Add bids
        for i in range(1000):
            price = 10000.0 - (i * 10)
            self.orderbook.add_order(
                side="buy",
                price=price,
                quantity=1.0,
                order_id=f"bid{i}"
            )
        
        # Add asks
        for i in range(1000):
            price = 10100.0 + (i * 10)
            self.orderbook.add_order(
                side="sell",
                price=price,
                quantity=1.0,
                order_id=f"ask{i}"
            )
        
        # Measure matching performance with crossing orders
        num_matches = 100
        latencies = []
        
        for i in range(num_matches):
            # Add matching order
            start_time = time.time()
            self.orderbook.add_order(
                side="buy" if i % 2 == 0 else "sell",
                price=10050.0,
                quantity=0.1,
                order_id=f"match{i}"
            )
            latency = (time.time() - start_time) * 1000  # Convert to ms
            latencies.append(latency)
        
        # Calculate statistics
        avg_latency = statistics.mean(latencies)
        median_latency = statistics.median(latencies)
        p95_latency = sorted(latencies)[int(num_matches * 0.95)]
        
        print(f"\nMatching Performance ({num_matches} matches):")
        print(f"  Average latency: {avg_latency:.2f} ms")
        print(f"  Median latency: {median_latency:.2f} ms")
        print(f"  95th percentile: {p95_latency:.2f} ms")
        
        # Basic assertion to catch severe performance regressions
        self.assertLess(median_latency, 1.0, "Median matching latency exceeds 1ms")


class TestConcurrentOperations(PerformanceTest):
    """Test the performance of concurrent order book operations."""
    
    def test_concurrent_add_orders(self):
        """Test adding orders concurrently."""
        num_threads = 10
        orders_per_thread = 1000
        total_orders = num_threads * orders_per_thread
        
        def add_orders(thread_id):
            """Add orders from a worker thread."""
            latencies = []
            for i in range(orders_per_thread):
                side = "buy" if random.random() < 0.5 else "sell"
                price = self.generate_random_price()
                quantity = self.generate_random_quantity()
                
                start_time = time.time()
                self.orderbook.add_order(
                    side=side,
                    price=price,
                    quantity=quantity,
                    order_id=f"thread{thread_id}_order{i}"
                )
                latency = (time.time() - start_time) * 1000  # Convert to ms
                latencies.append(latency)
            
            return latencies
        
        # Execute threads
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            results = list(executor.map(add_orders, range(num_threads)))
        
        # Flatten latencies
        all_latencies = [latency for thread_latencies in results for latency in thread_latencies]
        
        # Calculate statistics
        avg_latency = statistics.mean(all_latencies)
        median_latency = statistics.median(all_latencies)
        p95_latency = sorted(all_latencies)[int(total_orders * 0.95)]
        
        print(f"\nConcurrent Add Performance ({total_orders} orders, {num_threads} threads):")
        print(f"  Average latency: {avg_latency:.2f} ms")
        print(f"  Median latency: {median_latency:.2f} ms")
        print(f"  95th percentile: {p95_latency:.2f} ms")
        
        # Verify correct number of orders were added
        self.assertEqual(len(self.orderbook._orders), total_orders)
    
    def test_mixed_workload(self):
        """Test mixed workload with adds, cancels, and matches."""
        num_threads = 8
        operations_per_thread = 500
        
        # Pre-populate order book
        for i in range(5000):
            side = "buy" if random.random() < 0.5 else "sell"
            price = self.generate_random_price()
            quantity = self.generate_random_quantity()
            
            self.orderbook.add_order(
                side=side,
                price=price,
                quantity=quantity,
                order_id=f"init_order{i}"
            )
        
        # Track all orders
        all_orders = list(self.orderbook._orders.keys())
        
        def mixed_operations(thread_id):
            """Perform mixed operations from a worker thread."""
            thread_orders = []
            latencies = {
                "add": [],
                "cancel": [],
                "match": []
            }
            
            for i in range(operations_per_thread):
                op_type = random.choice(["add", "cancel", "match"])
                
                if op_type == "add":
                    # Add order
                    side = "buy" if random.random() < 0.5 else "sell"
                    price = self.generate_random_price()
                    quantity = self.generate_random_quantity()
                    
                    start_time = time.time()
                    order_id = self.orderbook.add_order(
                        side=side,
                        price=price,
                        quantity=quantity,
                        order_id=f"thread{thread_id}_order{i}"
                    )
                    latency = (time.time() - start_time) * 1000
                    latencies["add"].append(latency)
                    
                    # Track the order
                    thread_orders.append(order_id)
                
                elif op_type == "cancel" and all_orders:
                    # Cancel an existing order
                    if thread_orders:
                        # Prefer cancelling an order from this thread
                        order_id = random.choice(thread_orders)
                        thread_orders.remove(order_id)
                    else:
                        # Fall back to any order
                        order_id = random.choice(all_orders)
                    
                    start_time = time.time()
                    self.orderbook.cancel_order(order_id)
                    latency = (time.time() - start_time) * 1000
                    latencies["cancel"].append(latency)
                    
                    # Update global order list
                    if order_id in all_orders:
                        all_orders.remove(order_id)
                
                elif op_type == "match":
                    # Add an order that might match
                    side = "buy" if random.random() < 0.5 else "sell"
                    price = 10000.0  # Middle of the price range
                    quantity = self.generate_random_quantity(0.1, 1.0)
                    
                    start_time = time.time()
                    self.orderbook.add_order(
                        side=side,
                        price=price,
                        quantity=quantity,
                        order_id=f"thread{thread_id}_match{i}"
                    )
                    latency = (time.time() - start_time) * 1000
                    latencies["match"].append(latency)
            
            return latencies
        
        # Execute threads
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            results = list(executor.map(mixed_operations, range(num_threads)))
        
        # Combine latencies
        combined_latencies = {
            "add": [],
            "cancel": [],
            "match": []
        }
        
        for thread_result in results:
            for op_type, latencies in thread_result.items():
                combined_latencies[op_type].extend(latencies)
        
        # Print statistics for each operation type
        print("\nMixed Workload Performance:")
        for op_type, latencies in combined_latencies.items():
            if not latencies:
                continue
                
            avg_latency = statistics.mean(latencies)
            median_latency = statistics.median(latencies)
            p95_latency = sorted(latencies)[int(len(latencies) * 0.95)]
            
            print(f"  {op_type.capitalize()} Operations ({len(latencies)} operations):")
            print(f"    Average latency: {avg_latency:.2f} ms")
            print(f"    Median latency: {median_latency:.2f} ms")
            print(f"    95th percentile: {p95_latency:.2f} ms")


class TestMarketManagerPerformance(PerformanceTest):
    """Test the performance of the MarketManager."""
    
    def setUp(self):
        """Set up the test case."""
        super().setUp()
        
        # Create multiple markets
        for i in range(10):
            self.market_manager.create_market(
                symbol=f"COIN{i}/USD",
                event_manager=self.event_manager
            )
    
    def test_multi_market_operations(self):
        """Test operations across multiple markets."""
        operations_per_market = 1000
        markets = self.market_manager.list_markets()
        
        # Track latencies by operation and market
        latencies = {
            "place_order": [],
            "cancel_order": [],
            "get_snapshot": []
        }
        
        # Track orders by market
        market_orders = {market: [] for market in markets}
        
        # Place orders in each market
        for market in markets:
            for i in range(operations_per_market):
                side = "buy" if random.random() < 0.5 else "sell"
                price = self.generate_random_price()
                quantity = self.generate_random_quantity()
                
                start_time = time.time()
                order_id = self.market_manager.place_order(
                    symbol=market,
                    side=side,
                    price=price,
                    quantity=quantity,
                    order_id=f"{market}_order{i}"
                )
                latency = (time.time() - start_time) * 1000
                latencies["place_order"].append(latency)
                
                # Track the order
                if order_id:
                    market_orders[market].append(order_id)
        
        # Cancel some orders
        for market in markets:
            orders = market_orders[market]
            num_to_cancel = min(len(orders), operations_per_market // 2)
            
            for _ in range(num_to_cancel):
                order_id = orders.pop()
                
                start_time = time.time()
                self.market_manager.cancel_order(order_id)
                latency = (time.time() - start_time) * 1000
                latencies["cancel_order"].append(latency)
        
        # Get snapshots
        for market in markets:
            for _ in range(100):  # 100 snapshots per market
                start_time = time.time()
                self.market_manager.get_market_snapshot(market)
                latency = (time.time() - start_time) * 1000
                latencies["get_snapshot"].append(latency)
        
        # Print statistics
        print("\nMarketManager Performance:")
        for op_type, op_latencies in latencies.items():
            avg_latency = statistics.mean(op_latencies)
            median_latency = statistics.median(op_latencies)
            p95_latency = sorted(op_latencies)[int(len(op_latencies) * 0.95)]
            
            print(f"  {op_type.replace('_', ' ').title()} ({len(op_latencies)} operations):")
            print(f"    Average latency: {avg_latency:.2f} ms")
            print(f"    Median latency: {median_latency:.2f} ms")
            print(f"    95th percentile: {p95_latency:.2f} ms")


if __name__ == "__main__":
    unittest.main() 