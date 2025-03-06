"""
Performance benchmarking example for Manticore OrderBook.

This example demonstrates various benchmarks to measure the performance of the OrderBook
in different scenarios:
1. Basic operations (add, modify, cancel orders)
2. Matching performance
3. Batch operations
4. High-frequency updates
5. Memory usage

Usage:
    python3 performance_benchmark.py [--full] [--operations=10000]

Options:
    --full          Run all benchmarks including longer ones
    --operations=N  Number of operations for each benchmark (default: 10000)
"""

import argparse
import logging
import os
import random
import sys
import time
import gc
import psutil
from typing import Dict, List, Tuple, Any, Optional
import statistics
from tabulate import tabulate

# Add parent directory to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from manticore_orderbook.orderbook import OrderBook
from manticore_orderbook.event_manager import EventManager
from manticore_orderbook.models import TimeInForce

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("manticore_orderbook")

def format_time(seconds: float) -> str:
    """Format time in a human-readable way."""
    if seconds < 0.001:
        return f"{seconds * 1000000:.2f} μs"
    elif seconds < 1:
        return f"{seconds * 1000:.2f} ms"
    else:
        return f"{seconds:.4f} s"

def format_ops(count: int, seconds: float) -> str:
    """Format operations per second."""
    ops_per_second = count / seconds if seconds > 0 else 0
    if ops_per_second >= 1000000:
        return f"{ops_per_second / 1000000:.2f}M ops/s"
    elif ops_per_second >= 1000:
        return f"{ops_per_second / 1000:.2f}K ops/s"
    else:
        return f"{ops_per_second:.2f} ops/s"

def random_price() -> float:
    """Generate a random price between 9000 and 11000."""
    return round(random.uniform(9400, 10600), 2)

def random_quantity() -> float:
    """Generate a random quantity between 0.1 and 10."""
    return round(random.uniform(0.1, 10), 4)

def benchmark_basic_operations(order_book, n_orders=1000):
    """
    Benchmark basic order book operations:
    - Adding orders
    - Modifying orders
    - Cancelling orders
    """
    print(f"=== Benchmarking Basic Operations (n={n_orders}) ===")
    results = {}
    
    # Generate random orders
    orders = []
    order_ids = []
    for i in range(n_orders):
        side = "buy" if random.random() > 0.5 else "sell"
        price = random_price()
        quantity = random_quantity()
        order_id = f"order-{i}"
        orders.append((side, price, quantity, order_id))
        order_ids.append(order_id)
    
    # Benchmark adding orders
    print("Adding orders...")
    start_time = time.time()
    for side, price, quantity, order_id in orders:
        order_book.add_order(side, price, quantity, order_id)
    end_time = time.time()
    
    # Count active orders 
    actual_orders_added = len(order_book._orders)
    
    add_time = end_time - start_time
    results["add_orders_time"] = add_time
    results["add_orders_ops"] = format_ops(n_orders, add_time)
    results["add_orders_count"] = actual_orders_added
    print(f"Added {actual_orders_added} orders in {format_time(add_time)}")
    print(f"Rate: {format_ops(n_orders, add_time)}")
    
    # Benchmark order modification
    print("Modifying orders...")
    n_modifications = min(n_orders, actual_orders_added)
    orders_to_modify = random.sample(order_ids, n_modifications)
    
    start_time = time.time()
    for order_id in orders_to_modify:
        new_quantity = random_quantity()
        order_book.modify_order(order_id, new_quantity=new_quantity)
    end_time = time.time()
    
    modify_time = end_time - start_time
    results["modify_orders_time"] = modify_time
    results["modify_orders_ops"] = format_ops(n_modifications, modify_time)
    results["modify_orders_count"] = n_modifications
    print(f"Modified {n_modifications} orders in {format_time(modify_time)}")
    print(f"Rate: {format_ops(n_modifications, modify_time)}")
    
    # Benchmark order cancellation
    print("Cancelling orders...")
    n_cancellations = min(n_orders // 2, actual_orders_added)
    orders_to_cancel = random.sample(order_ids, n_cancellations)
    
    start_time = time.time()
    for order_id in orders_to_cancel:
        order_book.cancel_order(order_id)
    end_time = time.time()
    
    cancel_time = end_time - start_time
    results["cancel_orders_time"] = cancel_time
    results["cancel_orders_ops"] = format_ops(n_cancellations, cancel_time)
    results["cancel_orders_count"] = n_cancellations
    print(f"Cancelled {n_cancellations} orders in {format_time(cancel_time)}")
    print(f"Rate: {format_ops(n_cancellations, cancel_time)}")
    
    return results

def benchmark_matching(order_book, n_orders=1000):
    """Benchmark the matching engine with a set of crossing orders."""
    print(f"\n=== Benchmarking Matching Performance (n={n_orders}) ===")
    results = {}
    
    # Clear previous orders
    order_ids = list(order_book._orders.keys())
    for order_id in order_ids:
        order_book.cancel_order(order_id)
    
    # Create a baseline of orders
    baseline_orders = 1000
    for i in range(baseline_orders):
        side = "buy" if i % 2 == 0 else "sell"
        # Ensure orders don't cross
        if side == "buy":
            price = random_price() * 0.9  # Lower price for buys
        else:
            price = random_price() * 1.1  # Higher price for sells
        quantity = random_quantity()
        order_id = f"baseline-{i}"
        order_book.add_order(side, price, quantity, order_id)
    
    # Generate matching orders
    match_orders = []
    for i in range(n_orders):
        # Alternate sides to ensure matches
        side = "buy" if i % 2 == 0 else "sell"
        # Use aggressive prices to ensure matching
        if side == "buy":
            price = random_price() * 1.1  # Higher price for buys to match sells
        else:
            price = random_price() * 0.9  # Lower price for sells to match buys
        quantity = random_quantity()
        order_id = f"match-{i}"
        match_orders.append((side, price, quantity, order_id))
    
    # Measure matching performance
    start_time = time.time()
    for side, price, quantity, order_id in match_orders:
        order_book.add_order(side, price, quantity, order_id)
    end_time = time.time()
    
    matching_time = end_time - start_time
    matching_rate = n_orders / matching_time
    
    results["matching_time"] = matching_time
    results["matching_rate"] = matching_rate
    results["matching_ops"] = format_ops(n_orders, matching_time)
    
    # Get statistics on trades
    trades = order_book.get_trade_history(limit=n_orders)
    trade_count = len(trades)
    trade_rate = trade_count / matching_time if matching_time > 0 else 0
    
    results["trade_count"] = trade_count
    results["trade_rate"] = trade_rate
    
    print(f"Processed {n_orders} potentially matching orders in {format_time(matching_time)}")
    print(f"Generated {trade_count} trades at {format_ops(trade_count, matching_time)}")
    print(f"Overall matching rate: {format_ops(n_orders, matching_time)}")
    
    return results

def benchmark_batch_operations(order_book, n_orders=1000, batch_size=100):
    """Benchmark batch operations."""
    print(f"\n=== Benchmarking Batch Operations (n={n_orders}, batch_size={batch_size}) ===")
    results = {}
    
    # Clear previous orders
    order_ids = list(order_book._orders.keys())
    for order_id in order_ids:
        order_book.cancel_order(order_id)
    
    # Generate batch orders
    batches = []
    n_batches = n_orders // batch_size
    for batch_idx in range(n_batches):
        batch = []
        for i in range(batch_size):
            idx = batch_idx * batch_size + i
            side = "buy" if random.random() > 0.5 else "sell"
            price = random_price()
            quantity = random_quantity()
            order_id = f"batch-{idx}"
            # Create a dictionary for batch_add_orders
            batch.append({
                'side': side,
                'price': price,
                'quantity': quantity,
                'order_id': order_id
            })
        batches.append(batch)
    
    # Benchmark batch add
    start_time = time.time()
    for batch in batches:
        order_book.batch_add_orders(batch)
    end_time = time.time()
    
    batch_add_time = end_time - start_time
    results["batch_add_time"] = batch_add_time
    results["batch_add_ops"] = format_ops(n_orders, batch_add_time)
    results["batch_add_count"] = n_orders
    
    # Count how many orders actually got added (some might have matched immediately)
    actual_orders_added = len(order_book._orders)
    
    print(f"Batch added {n_orders} orders in {format_time(batch_add_time)}")
    print(f"Rate: {format_ops(n_orders, batch_add_time)}")
    
    # Benchmark batch cancel
    # Create batches of order IDs to cancel
    all_order_ids = list(order_book._orders.keys())
    cancel_batches = []
    orders_to_cancel = min(n_orders // 2, len(all_order_ids))
    cancel_batch_size = min(batch_size, orders_to_cancel)
    n_cancel_batches = orders_to_cancel // cancel_batch_size
    
    selected_orders = random.sample(all_order_ids, orders_to_cancel)
    for i in range(n_cancel_batches):
        start_idx = i * cancel_batch_size
        end_idx = start_idx + cancel_batch_size
        cancel_batches.append(selected_orders[start_idx:end_idx])
    
    start_time = time.time()
    for batch in cancel_batches:
        order_book.batch_cancel_orders(batch)
    end_time = time.time()
    
    batch_cancel_time = end_time - start_time
    results["batch_cancel_time"] = batch_cancel_time
    results["batch_cancel_ops"] = format_ops(orders_to_cancel, batch_cancel_time)
    results["batch_cancel_count"] = orders_to_cancel
    
    print(f"Batch cancelled {orders_to_cancel} orders in {format_time(batch_cancel_time)}")
    print(f"Rate: {format_ops(orders_to_cancel, batch_cancel_time)}")
    
    return results

def benchmark_depth_queries(order_book, n_queries=10000, max_depth=100):
    """Benchmark depth queries at various levels."""
    print(f"\n=== Benchmarking Depth Queries (n={n_queries}) ===")
    results = {}
    
    # Clear previous orders
    order_ids = list(order_book._orders.keys())
    for order_id in order_ids:
        order_book.cancel_order(order_id)
    
    # Add a large number of orders at various price levels
    order_count = 50000
    print(f"Preparing order book with {order_count} orders...")
    
    for i in range(order_count):
        side = "buy" if random.random() > 0.5 else "sell"
        price = random_price()
        quantity = random_quantity()
        order_id = f"depth-{i}"
        order_book.add_order(side, price, quantity, order_id)
    
    # Query at different depths
    depths = [1, 5, 10, 20, 50, max_depth]
    depth_results = {}
    
    for depth in depths:
        queries_for_depth = n_queries // len(depths)
        
        start_time = time.time()
        for _ in range(queries_for_depth):
            order_book.get_snapshot(depth=depth)
        end_time = time.time()
        
        query_time = end_time - start_time
        depth_results[depth] = {
            "time": query_time,
            "queries": queries_for_depth,
            "rate": queries_for_depth / query_time
        }
        
        print(f"Depth {depth}: {queries_for_depth} queries in {format_time(query_time)} ({format_ops(queries_for_depth, query_time)})")
    
    results["depth_queries"] = depth_results
    return results

def benchmark_memory_usage(n_orders=100000):
    """Benchmark memory usage for a large number of orders."""
    print(f"\n=== Benchmarking Memory Usage (n={n_orders}) ===")
    results = {}
    
    # Get baseline memory usage
    gc.collect()
    process = psutil.Process(os.getpid())
    base_memory = process.memory_info().rss / (1024 * 1024)  # MB
    
    # Create a new order book
    event_manager = EventManager()
    order_book = OrderBook("MEMORY-TEST", event_manager=event_manager, enable_logging=False)
    
    gc.collect()
    
    # Add orders
    print(f"Adding {n_orders} orders...")
    for i in range(n_orders):
        side = "buy" if i % 2 == 0 else "sell"
        price = random_price()
        quantity = random_quantity()
        order_id = f"memory-{i}"
        order_book.add_order(side, price, quantity, order_id)
        
        # Print progress
        if i > 0 and i % 10000 == 0:
            current_memory = process.memory_info().rss / (1024 * 1024)
            print(f"Progress: {i}/{n_orders} orders added, current memory usage: {current_memory:.2f} MB")
    
    # Measure final memory usage
    gc.collect()
    final_memory = process.memory_info().rss / (1024 * 1024)
    memory_used = final_memory - base_memory
    bytes_per_order = (memory_used * 1024 * 1024) / n_orders if n_orders > 0 else 0
    
    results["base_memory_mb"] = base_memory
    results["final_memory_mb"] = final_memory
    results["memory_used_mb"] = memory_used
    results["bytes_per_order"] = bytes_per_order
    
    print(f"Base memory usage: {base_memory:.2f} MB")
    print(f"Final memory usage: {final_memory:.2f} MB")
    print(f"Memory used for {n_orders} orders: {memory_used:.2f} MB")
    print(f"Average memory per order: {bytes_per_order:.2f} bytes")
    
    return results

def print_summary_table(results):
    """Print a summary table of benchmark results."""
    print("\n=== Performance Summary ===")
    
    headers = ["Operation", "Count", "Time", "Performance"]
    rows = []
    
    # Basic operations
    if "add_orders_time" in results:
        rows.append([
            "Add Orders", 
            f"{results['add_orders_count']}",
            f"{format_time(results['add_orders_time'])}",
            f"{results['add_orders_ops']}"
        ])
    
    if "modify_orders_time" in results:
        rows.append([
            "Modify Orders", 
            f"{results['modify_orders_count']}",
            f"{format_time(results['modify_orders_time'])}",
            f"{results['modify_orders_ops']}"
        ])
    
    if "cancel_orders_time" in results:
        rows.append([
            "Cancel Orders", 
            f"{results['cancel_orders_count']}",
            f"{format_time(results['cancel_orders_time'])}",
            f"{results['cancel_orders_ops']}"
        ])
    
    # Matching
    if "matching_time" in results:
        rows.append([
            "Order Matching", 
            f"{results.get('trade_count', 'N/A')}",
            f"{format_time(results['matching_time'])}",
            f"{results['matching_ops']}"
        ])
    
    # Batch operations
    if "batch_add_time" in results:
        rows.append([
            "Batch Add", 
            f"{results['batch_add_count']}",
            f"{format_time(results['batch_add_time'])}",
            f"{results['batch_add_ops']}"
        ])
    
    if "batch_cancel_time" in results:
        rows.append([
            "Batch Cancel", 
            f"{results['batch_cancel_count']}",
            f"{format_time(results['batch_cancel_time'])}",
            f"{results['batch_cancel_ops']}"
        ])
    
    # Memory usage
    if "memory_used_mb" in results:
        rows.append([
            "Memory Usage", 
            f"{results.get('memory_used_mb', 'N/A'):.2f} MB",
            f"{results.get('bytes_per_order', 'N/A'):.2f} bytes/order",
            "N/A"
        ])
    
    # Print table using format strings
    col_widths = [max(len(headers[i]), max(len(row[i]) for row in rows)) for i in range(len(headers))]
    
    header_row = " | ".join(f"{headers[i]:<{col_widths[i]}}" for i in range(len(headers)))
    separator = "-+-".join("-" * width for width in col_widths)
    
    print(header_row)
    print(separator)
    
    for row in rows:
        formatted_row = " | ".join(f"{row[i]:<{col_widths[i]}}" for i in range(len(row)))
        print(formatted_row)

def main():
    parser = argparse.ArgumentParser(description="Benchmark the Manticore OrderBook")
    parser.add_argument("--operations", type=int, default=1000, help="Number of operations to benchmark")
    parser.add_argument("--all", action="store_true", help="Run all benchmarks")
    parser.add_argument("--basic", action="store_true", help="Run basic operations benchmark")
    parser.add_argument("--matching", action="store_true", help="Run matching benchmark")
    parser.add_argument("--batch", action="store_true", help="Run batch operations benchmark")
    parser.add_argument("--depth", action="store_true", help="Run depth queries benchmark")
    parser.add_argument("--memory", action="store_true", help="Run memory usage benchmark")
    
    args = parser.parse_args()
    
    n_operations = args.operations
    
    # Check if specific benchmarks are selected
    run_specific = args.basic or args.matching or args.batch or args.depth or args.memory
    
    # If --all or no specific benchmark is selected, run all
    run_all = args.all or not run_specific
    
    # Create event manager and order book
    event_manager = EventManager()
    order_book = OrderBook("BTC/USD", event_manager=event_manager)
    
    results = {}
    
    # Run benchmarks
    if run_all or args.basic:
        basic_results = benchmark_basic_operations(order_book, n_orders=n_operations)
        results.update(basic_results)
    
    if run_all or args.matching:
        matching_results = benchmark_matching(order_book, n_orders=n_operations)
        results.update(matching_results)
    
    if run_all or args.batch:
        batch_results = benchmark_batch_operations(order_book, n_orders=n_operations)
        results.update(batch_results)
    
    if run_all or args.depth:
        depth_results = benchmark_depth_queries(order_book, n_queries=min(10000, n_operations * 10))
        results.update(depth_results)
    
    if run_all or args.memory:
        memory_results = benchmark_memory_usage(n_orders=min(100000, n_operations * 10))
        results.update(memory_results)
    
    # Print summary
    print_summary_table(results)

if __name__ == "__main__":
    print("=== Manticore OrderBook Performance Benchmark ===")
    print(f"Operations: {sys.argv[2] if len(sys.argv) > 2 else 1000}")
    main() 