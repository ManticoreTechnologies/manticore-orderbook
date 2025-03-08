#!/usr/bin/env python3
"""
Run the Manticore OrderBook Visualization Tool.

This script starts the professional visualization server that provides a UI
for interacting with the orderbook.
"""

import argparse
import os
import sys
import termcolor
import inspect

# Add parent directory to path for imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from tests.visual.orderbook_visualizer import run_visualizer

def check_compatibility():
    """
    Check if the current OrderBook implementation is compatible with this visualization tool.
    """
    from manticore_orderbook import OrderBook
    
    # Check if get_snapshot method accepts a depth parameter
    signature = inspect.signature(OrderBook.get_snapshot)
    has_depth_param = 'depth' in signature.parameters
    
    if not has_depth_param:
        print("\n⚠️  WARNING: Your OrderBook implementation doesn't have a 'depth' parameter in get_snapshot().")
        print("   The visualization tool has been patched to work with this version, but some features may be limited.")
        print("   Consider updating your OrderBook implementation or the visualization tool for full functionality.")

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Manticore Professional OrderBook Visualization Tool")
    parser.add_argument("--symbol", default="BTC/USD", help="Trading pair symbol")
    parser.add_argument("--port", type=int, default=5000, help="Port to run the server on")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind the server to")
    parser.add_argument("--auto-generate", action="store_true", help="Auto-generate random orders")
    parser.add_argument("--interval", type=float, default=1.0, 
                    help="Interval between auto-generated orders (seconds)")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    
    return parser.parse_args()

def main():
    """Main entry point for the script."""
    # Check compatibility with current OrderBook implementation
    check_compatibility()
    
    args = parse_args()
    
    # Print a professional startup banner
    print(termcolor.colored("""
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║  Manticore Professional OrderBook Visualization Tool         ║
║                                                              ║
║  Trading Pair: {symbol:<44} ║
║  Server URL:   http://{host}:{port:<40} ║
║  Auto-Generate Orders: {auto_gen:<34} ║
║  {interval_text:<60} ║
║                                                              ║
║  Press Ctrl+C to stop the server                             ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
    """.format(
        symbol=args.symbol,
        host=args.host,
        port=args.port,
        auto_gen="Enabled" if args.auto_generate else "Disabled",
        interval_text=f"(Interval: {args.interval} seconds)" if args.auto_generate else "",
    ), "cyan"))
    
    # Run the visualizer
    run_visualizer(args)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nServer stopped.") 