#!/usr/bin/env python3
"""
Benchmarks for the Manticore OrderBook implementation.

This module contains benchmarks to measure the performance of various
OrderBook operations under high loads. It simulates realistic trading
scenarios with a focus on throughput and latency.
"""

import unittest
import logging
import time
import random
import multiprocessing
import threading
from statistics import mean, median, stdev
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict, Any, Tuple

from manticore_orderbook import OrderBook, EventManager, EventType

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('benchmark')


class OrderBookBenchmarkTest(unittest.TestCase):
    """
    Comprehensive performance benchmarks for the OrderBook implementation.
    
    These benchmarks measure:
    1. Order addition throughput
    2. Order cancellation throughput
    3. Order matching throughput
    4. Mixed operations throughput
    5. Multithreaded operation performance
    """
    
    def setUp(self):
        """Set up test environment with optimized OrderBook configuration."""
        self.event_manager = EventManager(max_history_size=100000)
        self.orderbook = OrderBook(
            symbol="BTC/USD",
            event_manager=self.event_manager,
            max_trade_history=100000,
            enable_price_improvement=True,
            maker_fee_rate=0.001,
            taker_fee_rate=0.002
        )
        
        # Performance results storage
        self.results = {}
    
    def tearDown(self):
        """Clean up and report results."""
        self.orderbook.clear()
        
        # Print benchmark results
        if self.results:
            logger.info("=== BENCHMARK RESULTS ===")
            for test_name, metrics in self.results.items():
                logger.info(f"Test: {test_name}")
                for key, value in metrics.items():
                    if isinstance(value, (list, tuple)):
                        try:
                            logger.info(f"  {key}: mean={mean(value):.2f}, median={median(value):.2f}, stddev={stdev(value):.2f}, min={min(value):.2f}, max={max(value):.2f}")
                        except:
                            logger.info(f"  {key}: {value}")
                    else:
                        logger.info(f"  {key}: {value}")
    
    def _generate_limit_orders(self, count: int, price_range: Tuple[float, float], 
                               side: str = None) -> List[Dict[str, Any]]:
        """
        Generate a list of limit orders with realistic parameters.
        
        Args:
            count: Number of orders to generate
            price_range: Tuple of (min_price, max_price)
            side: Order side, or None for random sides
            
        Returns:
            List of order parameters
        """
        orders = []
        min_price, max_price = price_range
        
        for i in range(count):
            # Determine side
            if side is None:
                order_side = random.choice(["buy", "sell"])
            else:
                order_side = side
                
            # Generate price with realistic distribution
            price = random.uniform(min_price, max_price)
            
            # Generate quantity with realistic distribution
            quantity = random.lognormvariate(0, 0.5)
            quantity = max(0.001, min(10.0, quantity))
            
            # Create order
            orders.append({
                "side": order_side,
                "price": price,
                "quantity": quantity,
                "order_id": f"benchmark_{i}_{time.time()}",
                "order_type": "LIMIT"
            })
            
        return orders
    
    def test_order_addition_throughput(self):
        """Benchmark order addition throughput."""
        logger.info("=== Testing Order Addition Throughput ===")
        
        # Parameters
        num_orders = 10000
        
        # Generate orders
        orders = self._generate_limit_orders(
            num_orders, 
            price_range=(19000, 21000)
        )
        
        # Time order addition
        start_time = time.time()
        order_ids = []
        
        for order in orders:
            order_id = self.orderbook.add_order(**order)
            order_ids.append(order_id)
            
        end_time = time.time()
        elapsed = end_time - start_time
        throughput = num_orders / elapsed
        
        # Store results
        self.results["order_addition"] = {
            "num_orders": num_orders,
            "elapsed_time": elapsed,
            "throughput": throughput
        }
        
        logger.info(f"Added {num_orders} orders in {elapsed:.2f} seconds")
        logger.info(f"Order addition throughput: {throughput:.2f} orders/second")
        
        # Verify some orders were added to the book (not all should match)
        snapshot = self.orderbook.get_snapshot()
        num_in_book = 0
        if "bids" in snapshot:
            num_in_book += sum(level.get("orderCount", 0) for level in snapshot["bids"])
        if "asks" in snapshot:
            num_in_book += sum(level.get("orderCount", 0) for level in snapshot["asks"])
            
        logger.info(f"Orders successfully added to the book: {num_in_book} / {num_orders}")
        
        # Clear for next test
        self.orderbook.clear()
    
    def test_order_cancellation_throughput(self):
        """Benchmark order cancellation throughput."""
        logger.info("=== Testing Order Cancellation Throughput ===")
        
        # Parameters
        num_orders = 1000
        
        # Generate and add non-matching orders
        buy_orders = self._generate_limit_orders(
            num_orders // 2, 
            price_range=(19000, 19500),
            side="buy"
        )
        
        sell_orders = self._generate_limit_orders(
            num_orders // 2, 
            price_range=(20500, 21000),
            side="sell"
        )
        
        orders = buy_orders + sell_orders
        order_ids = []
        
        for order in orders:
            order_id = self.orderbook.add_order(**order)
            order_ids.append(order_id)
            
        # Time order cancellation
        start_time = time.time()
        
        for order_id in order_ids:
            self.orderbook.cancel_order(order_id)
            
        end_time = time.time()
        elapsed = end_time - start_time
        throughput = num_orders / elapsed
        
        # Store results
        self.results["order_cancellation"] = {
            "num_cancellations": num_orders,
            "elapsed_time": elapsed,
            "throughput": throughput
        }
        
        logger.info(f"Canceled {num_orders} orders in {elapsed:.2f} seconds")
        logger.info(f"Order cancellation throughput: {throughput:.2f} cancels/second")
        
        # Clear for next test
        self.orderbook.clear()
    
    def test_order_matching_throughput(self):
        """Benchmark order matching throughput."""
        logger.info("=== Testing Order Matching Throughput ===")
        
        # Parameters
        num_orders = 5000
        
        # Prepare the book with limit orders
        sell_orders = self._generate_limit_orders(
            num_orders // 2, 
            price_range=(20000, 21000),
            side="sell"
        )
        
        for order in sell_orders:
            self.orderbook.add_order(**order)
            
        # Generate matching buy orders
        buy_orders = self._generate_limit_orders(
            num_orders // 2, 
            price_range=(20000, 21000),
            side="buy"
        )
        
        # Track trades
        trades = []
        def trade_handler(event_type, data):
            if event_type == EventType.TRADE_EXECUTED:
                trades.append(data)
                
        self.event_manager.subscribe(EventType.TRADE_EXECUTED, trade_handler)
        
        # Time matching
        start_time = time.time()
        
        for order in buy_orders:
            self.orderbook.add_order(**order)
            
        end_time = time.time()
        elapsed = end_time - start_time
        
        # Calculate throughput and match rate
        throughput = (num_orders // 2) / elapsed
        matches = len(trades)
        match_rate = (matches / (num_orders // 2)) * 100
        
        # Store results
        self.results["order_matching"] = {
            "num_attempted_matches": num_orders // 2,
            "num_actual_matches": matches,
            "match_rate": match_rate,
            "elapsed_time": elapsed,
            "throughput": throughput
        }
        
        logger.info(f"Processed {num_orders // 2} orders in {elapsed:.2f} seconds")
        logger.info(f"Order matching throughput: {throughput:.2f} orders/second")
        logger.info(f"Match rate: {match_rate:.2f}% ({matches}/{num_orders//2})")
        
        # Clear for next test
        self.orderbook.clear()
    
    def test_mixed_operations_throughput(self):
        """Benchmark mixed operations (add, cancel, match) throughput."""
        logger.info("=== Testing Mixed Operations Throughput ===")
        
        # Parameters
        num_operations = 10000
        
        # Prepare initial orderbook state
        initial_orders = self._generate_limit_orders(
            1000, 
            price_range=(19000, 21000)
        )
        
        for order in initial_orders:
            self.orderbook.add_order(**order)
            
        # Get initial orders
        orders = self.orderbook.get_orders()
        order_ids = list(orders.keys())
        
        # Track operations
        num_adds = 0
        num_cancels = 0
        num_matches = 0
        
        # Track trades
        trades = []
        def trade_handler(event_type, data):
            if event_type == EventType.TRADE_EXECUTED:
                trades.append(data)
                
        self.event_manager.subscribe(EventType.TRADE_EXECUTED, trade_handler)
        
        # Time mixed operations
        start_time = time.time()
        
        for i in range(num_operations):
            op_type = random.choices(
                ["add", "cancel", "match"],
                weights=[0.6, 0.3, 0.1],
                k=1
            )[0]
            
            if op_type == "add":
                # Add a new order
                order = self._generate_limit_orders(1, price_range=(19000, 21000))[0]
                order_id = self.orderbook.add_order(**order)
                order_ids.append(order_id)
                num_adds += 1
                
            elif op_type == "cancel" and order_ids:
                # Cancel an existing order
                order_id = random.choice(order_ids)
                self.orderbook.cancel_order(order_id)
                order_ids.remove(order_id)
                num_cancels += 1
                
            elif op_type == "match":
                # Add a market order to match against existing orders
                side = random.choice(["buy", "sell"])
                self.orderbook.add_order(
                    side=side,
                    price=None,
                    quantity=random.uniform(0.1, 1.0),
                    order_type="MARKET"
                )
                num_matches += 1
        
        end_time = time.time()
        elapsed = end_time - start_time
        throughput = num_operations / elapsed
        
        # Store results
        self.results["mixed_operations"] = {
            "num_operations": num_operations,
            "num_adds": num_adds,
            "num_cancels": num_cancels,
            "num_matches": num_matches,
            "num_trades": len(trades),
            "elapsed_time": elapsed,
            "throughput": throughput
        }
        
        logger.info(f"Processed {num_operations} mixed operations in {elapsed:.2f} seconds")
        logger.info(f"Mixed operations throughput: {throughput:.2f} ops/second")
        logger.info(f"Operations breakdown: {num_adds} adds, {num_cancels} cancels, {num_matches} matches")
        logger.info(f"Resulted in {len(trades)} trades")
        
        # Clear for next test
        self.orderbook.clear()
    
    def test_concurrent_operations(self):
        """Benchmark concurrent operations using multiple threads."""
        logger.info("=== Testing Concurrent Operations ===")
        
        # Parameters
        num_threads = min(8, multiprocessing.cpu_count())
        num_operations_per_thread = 1000
        total_operations = num_threads * num_operations_per_thread
        
        # Initialize with some orders
        initial_orders = self._generate_limit_orders(
            500, 
            price_range=(19000, 21000)
        )
        
        initial_order_ids = {}
        for order in initial_orders:
            order_id = self.orderbook.add_order(**order)
            initial_order_ids[order_id] = order
            
        # Set up thread synchronization
        order_ids_lock = threading.Lock()
        order_ids = list(initial_order_ids.keys())
        results = {
            "elapsed_times": [],
            "throughputs": [],
            "total_adds": 0,
            "total_cancels": 0,
            "total_matches": 0
        }
        
        # Define worker function
        def worker(thread_id, num_operations):
            local_adds = 0
            local_cancels = 0
            local_matches = 0
            
            start_time = time.time()
            
            for i in range(num_operations):
                # Randomly select operation type with realistic weights
                op_type = random.choices(
                    ["add", "cancel", "match"],
                    weights=[0.6, 0.3, 0.1],
                    k=1
                )[0]
                
                if op_type == "add":
                    # Add a new order
                    order = self._generate_limit_orders(1, price_range=(19000, 21000))[0]
                    order_id = self.orderbook.add_order(**order)
                    with order_ids_lock:
                        order_ids.append(order_id)
                    local_adds += 1
                    
                elif op_type == "cancel":
                    # Cancel an existing order
                    with order_ids_lock:
                        if order_ids:
                            order_id = random.choice(order_ids)
                            order_ids.remove(order_id)
                    
                    if order_id:
                        self.orderbook.cancel_order(order_id)
                        local_cancels += 1
                    
                elif op_type == "match":
                    # Add a market order to match against existing orders
                    side = random.choice(["buy", "sell"])
                    self.orderbook.add_order(
                        side=side,
                        price=None,
                        quantity=random.uniform(0.1, 1.0),
                        order_type="MARKET"
                    )
                    local_matches += 1
            
            end_time = time.time()
            elapsed = end_time - start_time
            throughput = num_operations / elapsed
            
            # Return results
            return {
                "thread_id": thread_id,
                "elapsed_time": elapsed,
                "throughput": throughput,
                "adds": local_adds,
                "cancels": local_cancels,
                "matches": local_matches
            }
        
        # Run threads
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [
                executor.submit(worker, i, num_operations_per_thread)
                for i in range(num_threads)
            ]
            
            thread_results = [future.result() for future in futures]
        
        # Aggregate results
        for result in thread_results:
            results["elapsed_times"].append(result["elapsed_time"])
            results["throughputs"].append(result["throughput"])
            results["total_adds"] += result["adds"]
            results["total_cancels"] += result["cancels"]
            results["total_matches"] += result["matches"]
        
        avg_elapsed = mean(results["elapsed_times"])
        total_throughput = sum(results["throughputs"])
        
        # Store results
        self.results["concurrent_operations"] = {
            "num_threads": num_threads,
            "num_operations": total_operations,
            "elapsed_times": results["elapsed_times"],
            "per_thread_throughputs": results["throughputs"],
            "total_throughput": total_throughput,
            "total_adds": results["total_adds"],
            "total_cancels": results["total_cancels"],
            "total_matches": results["total_matches"]
        }
        
        logger.info(f"Concurrent operations with {num_threads} threads:")
        logger.info(f"Total operations: {total_operations}")
        logger.info(f"Average thread time: {avg_elapsed:.2f} seconds")
        logger.info(f"Total throughput: {total_throughput:.2f} ops/second")
        logger.info(f"Operations breakdown: {results['total_adds']} adds, "
                   f"{results['total_cancels']} cancels, {results['total_matches']} matches")
        
        # Clear for next test
        self.orderbook.clear()


if __name__ == "__main__":
    unittest.main() 