#!/usr/bin/env python3
"""
Benchmark script for the manticore-orderbook package.

This script demonstrates the performance characteristics of the OrderBook
implementation, including its advanced features for high-frequency trading.
"""

import time
import random
import logging
import statistics
from typing import List, Dict, Any
from tabulate import tabulate

from manticore_orderbook.orderbook import OrderBook
from manticore_orderbook.models import Order, Side

def format_time(seconds, precision=4):
    """Format time for display in the most appropriate unit."""
    if seconds < 1e-6:
        return f"{seconds * 1e9:.{precision}f} ns"
    elif seconds < 1e-3:
        return f"{seconds * 1e6:.{precision}f} µs"
    elif seconds < 1:
        return f"{seconds * 1e3:.{precision}f} ms"
    else:
        return f"{seconds:.{precision}f} s"

def generate_price(base_price=10000.0, volatility=0.01):
    """Generate a random price around a base price."""
    return round(base_price * (1 + volatility * (random.random() - 0.5)), 2)

def generate_quantity(min_qty=0.1, max_qty=10.0):
    """Generate a random quantity."""
    return round(random.uniform(min_qty, max_qty), 4)

def generate_orders(num_orders: int, base_price: float = 10000.0) -> List[Dict[str, Any]]:
    """Generate a list of random orders."""
    orders = []
    for _ in range(num_orders):
        side = "buy" if random.random() > 0.5 else "sell"
        price_offset = random.uniform(-0.02, 0.02)  # 2% price variation
        
        if side == "buy":
            # Buys typically slightly below current price
            price = base_price * (1 + price_offset - 0.005)
        else:
            # Sells typically slightly above current price
            price = base_price * (1 + price_offset + 0.005)
        
        quantity = generate_quantity()
        
        orders.append({
            "side": side,
            "price": round(price, 2),
            "quantity": quantity
        })
    
    return orders

def benchmark_basic_operations(order_book: OrderBook, n_orders=10000, n_modifications=1000, n_cancellations=1000):
    """
    Benchmark basic order book operations.
    
    Tests:
    1. Adding n_orders
    2. Modifying n_modifications randomly selected orders
    3. Cancelling n_cancellations randomly selected orders
    
    Returns:
        Dictionary with timing results
    """
    print(f"\n=== Benchmarking Basic Operations ===")
    print(f"Adding {n_orders} orders, modifying {n_modifications}, and cancelling {n_cancellations}...")
    
    results = {}
    order_ids = []
    
    # Benchmark adding orders
    start_time = time.time()
    for _ in range(n_orders):
        side = "buy" if random.random() > 0.5 else "sell"
        price = generate_price()
        quantity = generate_quantity()
        
        order_id = order_book.add_order(side, price, quantity)
        order_ids.append(order_id)
    
    add_time = time.time() - start_time
    results["add_orders"] = {
        "total_time": add_time,
        "avg_time_per_order": add_time / n_orders,
        "operations_per_second": n_orders / add_time
    }
    
    print(f"Time to add {n_orders} orders: {format_time(add_time)}")
    print(f"Average time per order: {format_time(add_time/n_orders)}")
    print(f"Orders per second: {n_orders/add_time:.2f}")
    
    # Snapshot the book to see the spread
    snapshot = order_book.get_snapshot(5)
    best_bid = snapshot["bids"][0]["price"] if snapshot["bids"] else None
    best_ask = snapshot["asks"][0]["price"] if snapshot["asks"] else None
    
    print(f"Order book after adding orders:")
    print(f"Best bid: {best_bid}")
    print(f"Best ask: {best_ask}")
    print(f"Spread: {best_ask - best_bid if (best_bid and best_ask) else 'N/A'}")
    
    # Benchmark modifying orders
    if n_modifications > 0 and order_ids:
        modification_ids = random.sample(order_ids, min(n_modifications, len(order_ids)))
        
        start_time = time.time()
        for order_id in modification_ids:
            # Get current order
            order_info = order_book.get_order(order_id)
            if not order_info:
                continue
                
            # Modify price by a small amount
            new_price = order_info["price"] * (1 + random.uniform(-0.005, 0.005))
            
            # Modify quantity by a small amount (only decreasing to maintain position)
            new_quantity = order_info["quantity"] * random.uniform(0.5, 0.9)
            
            order_book.modify_order(order_id, new_price=round(new_price, 2), new_quantity=round(new_quantity, 4))
        
        modify_time = time.time() - start_time
        results["modify_orders"] = {
            "total_time": modify_time,
            "avg_time_per_modification": modify_time / n_modifications,
            "operations_per_second": n_modifications / modify_time
        }
        
        print(f"\nTime to modify {n_modifications} orders: {format_time(modify_time)}")
        print(f"Average time per modification: {format_time(modify_time/n_modifications)}")
        print(f"Modifications per second: {n_modifications/modify_time:.2f}")
    
    # Benchmark cancelling orders
    if n_cancellations > 0 and order_ids:
        cancellation_ids = random.sample(order_ids, min(n_cancellations, len(order_ids)))
        
        start_time = time.time()
        for order_id in cancellation_ids:
            order_book.cancel_order(order_id)
        
        cancel_time = time.time() - start_time
        results["cancel_orders"] = {
            "total_time": cancel_time,
            "avg_time_per_cancellation": cancel_time / n_cancellations,
            "operations_per_second": n_cancellations / cancel_time
        }
        
        print(f"\nTime to cancel {n_cancellations} orders: {format_time(cancel_time)}")
        print(f"Average time per cancellation: {format_time(cancel_time/n_cancellations)}")
        print(f"Cancellations per second: {n_cancellations/cancel_time:.2f}")
    
    # Get statistics
    stats = order_book.get_statistics()
    print(f"\nOrder book statistics:")
    print(f"- Bid levels: {stats['bid_levels']}")
    print(f"- Ask levels: {stats['ask_levels']}")
    print(f"- Total orders: {stats['total_orders']}")
    print(f"- Trades executed: {stats['num_trades_executed']}")
    
    return results

def benchmark_batch_operations(order_book: OrderBook, batch_sizes=[100, 1000, 10000]):
    """
    Benchmark batch operations.
    
    Tests adding orders in batches of different sizes.
    
    Returns:
        Dictionary with timing results
    """
    print(f"\n=== Benchmarking Batch Operations ===")
    results = {}
    
    for batch_size in batch_sizes:
        # Clear the book before each test
        order_book.clear()
        
        # Generate a batch of orders
        orders = generate_orders(batch_size)
        
        # Time the batch operation
        start_time = time.time()
        order_ids = order_book.batch_add_orders(orders)
        batch_time = time.time() - start_time
        
        results[f"batch_{batch_size}"] = {
            "total_time": batch_time,
            "avg_time_per_order": batch_time / batch_size,
            "operations_per_second": batch_size / batch_time
        }
        
        print(f"Time to add batch of {batch_size} orders: {format_time(batch_time)}")
        print(f"Average time per order in batch: {format_time(batch_time/batch_size)}")
        print(f"Batch processing rate: {batch_size/batch_time:.2f} orders/second")
        
        # Get statistics
        stats = order_book.get_statistics()
        print(f"Trades executed: {stats['num_trades_executed']}")
        print(f"Total orders remaining: {stats['total_orders']}")
    
    return results

def benchmark_depth_queries(order_book: OrderBook, query_depths=[1, 5, 10, 20, 50], iterations=1000):
    """
    Benchmark order book depth queries.
    
    Tests getting snapshots at different depths.
    
    Returns:
        Dictionary with timing results
    """
    print(f"\n=== Benchmarking Depth Queries ===")
    results = {}
    
    # Ensure the book has sufficient orders
    if order_book.get_statistics()["total_orders"] < 1000:
        orders = generate_orders(10000)
        order_book.batch_add_orders(orders)
    
    for depth in query_depths:
        times = []
        
        for _ in range(iterations):
            start_time = time.time()
            snapshot = order_book.get_snapshot(depth=depth)
            query_time = time.time() - start_time
            times.append(query_time)
        
        avg_time = statistics.mean(times)
        min_time = min(times)
        max_time = max(times)
        p95_time = statistics.quantiles(times, n=20)[18]  # 95th percentile
        
        results[f"depth_{depth}"] = {
            "avg_time": avg_time,
            "min_time": min_time,
            "max_time": max_time,
            "p95_time": p95_time,
            "queries_per_second": 1 / avg_time
        }
        
        print(f"Depth {depth} query ({iterations} iterations):")
        print(f"  Average time: {format_time(avg_time)}")
        print(f"  Min time: {format_time(min_time)}")
        print(f"  Max time: {format_time(max_time)}")
        print(f"  P95 time: {format_time(p95_time)}")
        print(f"  Queries per second: {1/avg_time:.2f}")
    
    return results

def benchmark_price_improvement(n_orders=1000):
    """
    Benchmark price improvement feature.
    
    Compares trade execution with and without price improvement.
    
    Returns:
        Dictionary with comparison results
    """
    print(f"\n=== Benchmarking Price Improvement ===")
    
    # Create two order books
    book_standard = OrderBook("BTC/USD", enable_price_improvement=False, enable_logging=False)
    book_improved = OrderBook("BTC/USD", enable_price_improvement=True, enable_logging=False)
    
    # Add the same limit orders to both books
    limit_orders = generate_orders(n_orders // 2, base_price=10000.0)
    book_standard.batch_add_orders(limit_orders)
    book_improved.batch_add_orders(limit_orders)
    
    # Generate market orders with prices that would benefit from price improvement
    market_orders = []
    for _ in range(n_orders // 10):
        side = "buy" if random.random() > 0.5 else "sell"
        
        if side == "buy":
            # Buy with a higher price than necessary
            price = 10100.0  # Well above the best ask
        else:
            # Sell with a lower price than necessary
            price = 9900.0   # Well below the best bid
        
        quantity = generate_quantity()
        
        market_orders.append({
            "side": side,
            "price": price,
            "quantity": quantity
        })
    
    # Execute market orders on both books
    for order in market_orders:
        book_standard.add_order(order["side"], order["price"], order["quantity"])
        book_improved.add_order(order["side"], order["price"], order["quantity"])
    
    # Compare trade execution
    standard_trades = book_standard.get_trade_history(1000)
    improved_trades = book_improved.get_trade_history(1000)
    
    # Calculate average execution prices
    if standard_trades and improved_trades:
        std_buy_prices = [t["price"] for t in standard_trades if t["taker_order_id"] == t["maker_order_id"]]
        std_sell_prices = [t["price"] for t in standard_trades if t["taker_order_id"] != t["maker_order_id"]]
        
        imp_buy_prices = [t["price"] for t in improved_trades if t["taker_order_id"] == t["maker_order_id"]]
        imp_sell_prices = [t["price"] for t in improved_trades if t["taker_order_id"] != t["maker_order_id"]]
        
        results = {
            "standard": {
                "trades_executed": len(standard_trades),
                "avg_buy_price": statistics.mean(std_buy_prices) if std_buy_prices else None,
                "avg_sell_price": statistics.mean(std_sell_prices) if std_sell_prices else None
            },
            "improved": {
                "trades_executed": len(improved_trades),
                "avg_buy_price": statistics.mean(imp_buy_prices) if imp_buy_prices else None,
                "avg_sell_price": statistics.mean(imp_sell_prices) if imp_sell_prices else None
            }
        }
        
        print(f"Standard execution:")
        print(f"  Trades executed: {results['standard']['trades_executed']}")
        print(f"  Average buy price: {results['standard']['avg_buy_price']:.2f}" if results['standard']['avg_buy_price'] else "  No buy trades")
        print(f"  Average sell price: {results['standard']['avg_sell_price']:.2f}" if results['standard']['avg_sell_price'] else "  No sell trades")
        
        print(f"\nPrice improved execution:")
        print(f"  Trades executed: {results['improved']['trades_executed']}")
        print(f"  Average buy price: {results['improved']['avg_buy_price']:.2f}" if results['improved']['avg_buy_price'] else "  No buy trades")
        print(f"  Average sell price: {results['improved']['avg_sell_price']:.2f}" if results['improved']['avg_sell_price'] else "  No sell trades")
        
        if results['standard']['avg_buy_price'] and results['improved']['avg_buy_price']:
            buy_improvement = (results['standard']['avg_buy_price'] - results['improved']['avg_buy_price']) / results['standard']['avg_buy_price'] * 100
            print(f"  Buy price improvement: {buy_improvement:.2f}%")
        
        if results['standard']['avg_sell_price'] and results['improved']['avg_sell_price']:
            sell_improvement = (results['improved']['avg_sell_price'] - results['standard']['avg_sell_price']) / results['standard']['avg_sell_price'] * 100
            print(f"  Sell price improvement: {sell_improvement:.2f}%")
        
        return results
    else:
        print("Not enough trades to compare price improvement")
        return {}

def benchmark_stress_test(order_book: OrderBook, n_iterations=10, orders_per_iteration=1000):
    """
    Stress test the order book with a mix of operations.
    
    Performs multiple iterations, each with a mix of:
    - Adding new orders
    - Modifying existing orders
    - Cancelling orders
    - Taking snapshots
    - Getting depth at specific prices
    
    Returns:
        Dictionary with timing results
    """
    print(f"\n=== Performing Stress Test ===")
    print(f"Running {n_iterations} iterations with {orders_per_iteration} orders per iteration")
    
    total_orders = 0
    total_modifications = 0
    total_cancellations = 0
    total_trades = 0
    
    iteration_times = []
    order_book.clear()
    
    for i in range(n_iterations):
        print(f"Iteration {i+1}/{n_iterations}...")
        
        start_time = time.time()
        
        # Generate new orders (70% of operations)
        n_new_orders = int(orders_per_iteration * 0.7)
        orders = generate_orders(n_new_orders)
        order_ids = order_book.batch_add_orders(orders)
        total_orders += n_new_orders
        
        # Store active order IDs
        all_order_ids = list(order_book._orders.keys())
        if not all_order_ids:
            continue
            
        # Modify orders (15% of operations)
        n_modifications = int(orders_per_iteration * 0.15)
        modification_ids = random.sample(all_order_ids, min(n_modifications, len(all_order_ids)))
        
        for order_id in modification_ids:
            # Get current order
            order_info = order_book.get_order(order_id)
            if not order_info:
                continue
                
            # Modify price or quantity
            if random.random() > 0.5:
                # Price modification
                new_price = order_info["price"] * (1 + random.uniform(-0.01, 0.01))
                order_book.modify_order(order_id, new_price=round(new_price, 2))
            else:
                # Quantity modification (decrease only)
                new_quantity = order_info["quantity"] * random.uniform(0.5, 0.9)
                order_book.modify_order(order_id, new_quantity=round(new_quantity, 4))
        
        total_modifications += n_modifications
        
        # Cancel orders (15% of operations)
        n_cancellations = int(orders_per_iteration * 0.15)
        cancellation_ids = random.sample(all_order_ids, min(n_cancellations, len(all_order_ids)))
        
        for order_id in cancellation_ids:
            order_book.cancel_order(order_id)
        
        total_cancellations += n_cancellations
        
        # Take snapshots at various depths
        for depth in [1, 5, 10, 20]:
            order_book.get_snapshot(depth=depth)
        
        # Get depth at specific prices
        for _ in range(10):
            if order_book._bids:
                price = random.choice(order_book._bids)
                order_book.get_order_depth_at_price("buy", price)
            
            if order_book._asks:
                price = random.choice(order_book._asks)
                order_book.get_order_depth_at_price("sell", price)
        
        iteration_time = time.time() - start_time
        iteration_times.append(iteration_time)
        
        # Get current statistics
        stats = order_book.get_statistics()
        total_trades = stats["num_trades_executed"]
        
        print(f"  Iteration time: {format_time(iteration_time)}")
        print(f"  Orders: {stats['total_orders']}, Trades: {stats['num_trades_executed']}")
        print(f"  Bid levels: {stats['bid_levels']}, Ask levels: {stats['ask_levels']}")
    
    # Calculate summary statistics
    avg_iteration_time = statistics.mean(iteration_times)
    total_time = sum(iteration_times)
    
    results = {
        "total_time": total_time,
        "avg_iteration_time": avg_iteration_time,
        "total_orders": total_orders,
        "total_modifications": total_modifications,
        "total_cancellations": total_cancellations,
        "total_trades": total_trades,
        "operations_per_second": (total_orders + total_modifications + total_cancellations) / total_time
    }
    
    print(f"\nStress test results:")
    print(f"Total time: {format_time(total_time)}")
    print(f"Average iteration time: {format_time(avg_iteration_time)}")
    print(f"Total orders added: {total_orders}")
    print(f"Total modifications: {total_modifications}")
    print(f"Total cancellations: {total_cancellations}")
    print(f"Total trades executed: {total_trades}")
    print(f"Operations per second: {results['operations_per_second']:.2f}")
    
    return results

def run_benchmark(num_orders: int = 10000, num_modifications: int = 1000, num_cancellations: int = 1000):
    """
    Run comprehensive benchmarks on the OrderBook implementation.
    
    Args:
        num_orders: Number of orders to add in basic benchmark
        num_modifications: Number of orders to modify in basic benchmark
        num_cancellations: Number of orders to cancel in basic benchmark
    """
    print("=== Manticore OrderBook Benchmark ===")
    
    # Create an order book with default settings
    order_book = OrderBook("BTC/USD", enable_logging=False)
    
    # Run benchmark tests
    try:
        # Basic operations
        basic_results = benchmark_basic_operations(
            order_book, 
            n_orders=num_orders, 
            n_modifications=num_modifications, 
            n_cancellations=num_cancellations
        )
        
        # Batch operations
        batch_results = benchmark_batch_operations(
            order_book,
            batch_sizes=[100, 1000, 5000]
        )
        
        # Depth queries
        depth_results = benchmark_depth_queries(
            order_book,
            query_depths=[1, 5, 10, 20, 50],
            iterations=500
        )
        
        # Price improvement
        improvement_results = benchmark_price_improvement(n_orders=5000)
        
        # Stress test
        stress_results = benchmark_stress_test(
            order_book,
            n_iterations=5,
            orders_per_iteration=2000
        )
        
        # Print summary
        print("\n=== Summary of Benchmark Results ===")
        print(f"OrderBook implementation handled:")
        print(f"- {num_orders} orders at {basic_results['add_orders']['operations_per_second']:.2f} orders/second")
        print(f"- {num_modifications} modifications at {basic_results['modify_orders']['operations_per_second']:.2f} modifications/second")
        print(f"- {num_cancellations} cancellations at {basic_results['cancel_orders']['operations_per_second']:.2f} cancellations/second")
        print(f"- Batch processing of 1000 orders in {batch_results['batch_1000']['total_time']:.4f} seconds")
        print(f"- Depth-10 snapshot in {depth_results['depth_10']['avg_time']*1000:.4f} ms")
        print(f"- Stress test: {stress_results['operations_per_second']:.2f} operations/second overall")
        
        # Create a table of all results
        rows = []
        rows.append(["Add Orders", f"{basic_results['add_orders']['operations_per_second']:.2f}/s", f"{format_time(basic_results['add_orders']['avg_time_per_order'])}"])
        rows.append(["Modify Orders", f"{basic_results['modify_orders']['operations_per_second']:.2f}/s", f"{format_time(basic_results['modify_orders']['avg_time_per_modification'])}"])
        rows.append(["Cancel Orders", f"{basic_results['cancel_orders']['operations_per_second']:.2f}/s", f"{format_time(basic_results['cancel_orders']['avg_time_per_cancellation'])}"])
        
        for size in [100, 1000, 5000]:
            if f"batch_{size}" in batch_results:
                rows.append([f"Batch {size} Orders", f"{batch_results[f'batch_{size}']['operations_per_second']:.2f}/s", f"{format_time(batch_results[f'batch_{size}']['total_time'])}"])
        
        for depth in [1, 5, 10, 20, 50]:
            if f"depth_{depth}" in depth_results:
                rows.append([f"Depth {depth} Query", f"{depth_results[f'depth_{depth}']['queries_per_second']:.2f}/s", f"{format_time(depth_results[f'depth_{depth}']['avg_time'])}"])
        
        print("\nDetailed Performance Metrics:")
        print(tabulate(rows, headers=["Operation", "Rate", "Time per Operation"], tablefmt="grid"))
        
    except ImportError:
        print("Couldn't import tabulate. Install with: pip install tabulate")
        
    except Exception as e:
        print(f"Error during benchmark: {str(e)}")
        raise

if __name__ == "__main__":
    run_benchmark(num_orders=10000, num_modifications=1000, num_cancellations=1000) 