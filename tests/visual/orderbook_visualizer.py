#!/usr/bin/env python3
"""
Manticore Professional Orderbook Visualization Tool

This is a standalone tool for visualizing and testing the orderbook.
It provides a professional web interface that shows the live orderbook and allows
for placing and canceling orders with advanced features.
"""

import argparse
import logging
import random
import threading
import time
import sys
import os
import json
import uuid
from datetime import datetime, timedelta
from flask import Flask, render_template, send_from_directory, jsonify, request
from flask_socketio import SocketIO

# Ensure the manticore_orderbook is in the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
from manticore_orderbook import OrderBook, EventManager, EventType

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('orderbook_visualizer')

# Initialize Flask app
app = Flask(__name__, 
            template_folder='../../manticore_orderbook/examples/templates',
            static_folder='../../manticore_orderbook/examples/static')
app.config['SECRET_KEY'] = 'manticore_professional_trading'
socketio = SocketIO(app, cors_allowed_origins="*")

# Create orderbook components
event_manager = EventManager()
orderbook = None  # Will be initialized later

# Keep track of recent trades and open orders
MAX_TRADE_HISTORY = 100
recent_trades = []
open_orders = {}  # Map of order_id to order details

# Order generation configuration
ORDER_GEN_ENABLED = False
order_gen_thread = None
GEN_INTERVAL_SECONDS = 1.0
PRICE_VOLATILITY = 0.02  # 2% volatility for random prices
BASE_PRICE = 20000.0     # Default base price

# Trade history for chart data (simulated)
OHLC_HISTORY = []

# Add OrderBook compatibility adapter
class OrderBookAdapter:
    """
    Adapter to handle compatibility with different versions of the OrderBook class.
    This ensures the visualization tool works with both old and new versions of the OrderBook.
    """
    def __init__(self, orderbook_instance):
        """Initialize with the original OrderBook instance."""
        self.orderbook = orderbook_instance
        self._check_snapshot_method()
    
    def _check_snapshot_method(self):
        """Check if the orderbook's get_snapshot method accepts a depth parameter."""
        import inspect
        signature = inspect.signature(self.orderbook.get_snapshot)
        self.has_depth_param = 'depth' in signature.parameters
        if not self.has_depth_param:
            logger.warning("OrderBook.get_snapshot() does not accept 'depth' parameter. Using compatibility mode.")
    
    def get_snapshot(self, depth=None):
        """
        Get a snapshot of the order book, handling different versions of the method.
        
        Args:
            depth: Optional depth parameter (ignored if not supported)
            
        Returns:
            Order book snapshot dict
        """
        try:
            if self.has_depth_param:
                snapshot = self.orderbook.get_snapshot(depth=depth)
            else:
                snapshot = self.orderbook.get_snapshot()
            
            # Make sure the snapshot has the expected structure
            if 'bids' not in snapshot:
                snapshot['bids'] = []
            if 'asks' not in snapshot:
                snapshot['asks'] = []
            
            # Fix any formatting issues
            for side in ['bids', 'asks']:
                for level in snapshot[side]:
                    # Ensure all levels have quantity and price as floats
                    if 'quantity' in level:
                        level['quantity'] = float(level['quantity'])
                    if 'price' in level:
                        level['price'] = float(level['price'])
                    
                    # Add total if not present
                    if 'total' not in level and 'quantity' in level:
                        level['total'] = float(level['quantity'])
            
            logger.debug(f"Snapshot retrieved: {len(snapshot['bids'])} bids, {len(snapshot['asks'])} asks")
            return snapshot
        except Exception as e:
            logger.error(f"Error getting order book snapshot: {str(e)}")
            return {'bids': [], 'asks': []}
    
    def __getattr__(self, name):
        """Delegate all other method calls to the original orderbook instance."""
        return getattr(self.orderbook, name)

def track_trade(trade_data):
    """
    Store and process recent trades with enhanced metadata for the professional UI.
    """
    trade_record = {
        'id': trade_data.get('trade_id', str(uuid.uuid4())),
        'time': trade_data.get('timestamp', time.time()),
        'price': trade_data.get('price'),
        'quantity': trade_data.get('quantity'),
        'side': trade_data.get('taker_side', 'unknown'),
        'value': trade_data.get('price', 0) * trade_data.get('quantity', 0),
        'maker_id': trade_data.get('maker_order_id', ''),
        'taker_id': trade_data.get('taker_order_id', '')
    }
    
    recent_trades.append(trade_record)
    if len(recent_trades) > MAX_TRADE_HISTORY:
        recent_trades.pop(0)
    
    # Update OHLC data for the chart
    update_ohlc_data(trade_record)
    
    # Remove completed orders from the open orders list
    if trade_record['maker_id'] in open_orders and open_orders[trade_record['maker_id']]['quantity'] <= trade_record['quantity']:
        del open_orders[trade_record['maker_id']]
    
    if trade_record['taker_id'] in open_orders and open_orders[trade_record['taker_id']]['quantity'] <= trade_record['quantity']:
        del open_orders[trade_record['taker_id']]


def update_ohlc_data(trade):
    """
    Update OHLC (Open, High, Low, Close) data for charting.
    This is a simplified simulation for visualization purposes.
    """
    global OHLC_HISTORY
    
    current_time = int(time.time())
    # Round to the nearest minute for a 1-minute candle
    candle_timestamp = current_time - (current_time % 60)
    
    if not OHLC_HISTORY or OHLC_HISTORY[-1]['time'] < candle_timestamp:
        # Create a new candle
        new_candle = {
            'time': candle_timestamp,
            'open': trade['price'],
            'high': trade['price'],
            'low': trade['price'],
            'close': trade['price'],
            'volume': trade['quantity']
        }
        OHLC_HISTORY.append(new_candle)
        
        # Keep a reasonable history size
        if len(OHLC_HISTORY) > 100:
            OHLC_HISTORY.pop(0)
    else:
        # Update the current candle
        current_candle = OHLC_HISTORY[-1]
        current_candle['high'] = max(current_candle['high'], trade['price'])
        current_candle['low'] = min(current_candle['low'], trade['price'])
        current_candle['close'] = trade['price']
        current_candle['volume'] += trade['quantity']


@app.route('/')
def index():
    """Render the professional orderbook visualization page."""
    return render_template('synced_orderbook.html')


@app.route('/api/trades')
def api_trades():
    """Return recent trades as JSON."""
    return jsonify(recent_trades)


@app.route('/api/ohlc')
def api_ohlc():
    """Return OHLC data for charting as JSON."""
    return jsonify(OHLC_HISTORY)


@app.route('/api/orders')
def api_orders():
    """Return open orders as JSON."""
    return jsonify(list(open_orders.values()))


@app.route('/static/<path:path>')
def send_static(path):
    """Serve static files."""
    return send_from_directory('static', path)


@socketio.on('connect')
def handle_connect():
    """Handle new client connection with enhanced initial data."""
    logger.info(f"Client connected")
    
    # Send initial orderbook state
    emit_orderbook_update()
    
    # Send recent trades
    socketio.emit('trade_history', recent_trades)
    
    # Send open orders - convert to list for consistent format
    open_orders_list = list(open_orders.values())
    logger.info(f"Sending {len(open_orders_list)} open orders to client")
    socketio.emit('open_orders', open_orders_list)
    
    # Send OHLC data
    socketio.emit('ohlc_data', OHLC_HISTORY)
    
    # Send generator status
    socketio.emit('generator_status', {'enabled': ORDER_GEN_ENABLED})


@socketio.on('place_order')
def handle_place_order(data):
    """Handle order placement from UI with enhanced order types."""
    try:
        order_type = data.get('order_type', 'limit').lower()
        side = data.get('side', '').lower()
        quantity_str = data.get('quantity', '')
        
        # Validate required fields
        if not side or not quantity_str:
            logger.error(f"Missing required fields in order: {data}")
            # Return response through callback if available
            return {
                'success': False,
                'message': 'Missing required fields'
            }
            
        # Parse and validate quantity
        try:
            quantity = float(quantity_str)
            if quantity <= 0:
                raise ValueError("Quantity must be positive")
        except (ValueError, TypeError) as e:
            logger.error(f"Invalid quantity: {quantity_str} - {str(e)}")
            # Return response through callback if available
            return {
                'success': False,
                'message': f'Invalid quantity: {str(e)}'
            }
        
        # Process different order types
        order_params = {
            'side': side,
            'quantity': quantity,
            'order_type': order_type
        }
        
        # Handle different order types
        if order_type == 'market':
            # For market orders, set price to ensure it crosses the book
            if side == 'buy':
                # Set price high to match against any ask
                price = BASE_PRICE * 1.5  # 50% above base price
            else:
                # Set price low to match against any bid
                price = BASE_PRICE * 0.5  # 50% below base price
            order_params['price'] = price
        elif order_type == 'limit':
            # Process regular limit orders
            price_str = data.get('price', '')
            try:
                price = float(price_str)
                if price <= 0:
                    raise ValueError("Price must be positive")
                order_params['price'] = price
            except (ValueError, TypeError) as e:
                logger.error(f"Invalid price: {price_str} - {str(e)}")
                # Return response through callback if available
                return {
                    'success': False,
                    'message': f'Invalid price: {str(e)}'
                }
        elif order_type == 'stop_limit':
            # Process stop-limit orders
            price_str = data.get('price', '')
            stop_price_str = data.get('stop_price', '')
            try:
                price = float(price_str)
                stop_price = float(stop_price_str)
                if price <= 0 or stop_price <= 0:
                    raise ValueError("Price and stop price must be positive")
                order_params['price'] = price
                order_params['stop_price'] = stop_price
            except (ValueError, TypeError) as e:
                logger.error(f"Invalid price or stop price - {str(e)}")
                # Return response through callback if available
                return {
                    'success': False,
                    'message': f'Invalid price parameters: {str(e)}'
                }
        
        # Add user ID for tracking
        order_params['user_id'] = 'web_user'
        
        # Place the order
        order_id = orderbook.add_order(**order_params)
        
        # Save order to open orders with consistent property names
        open_orders[order_id] = {
            'id': order_id,
            'order_id': order_id,  # Add both id and order_id for compatibility
            'type': order_type,
            'order_type': order_type,  # Add both type and order_type for compatibility
            'side': side,
            'price': order_params.get('price'),
            'quantity': quantity,
            'time': time.time(),
            'timestamp': time.time(),  # Add both time and timestamp for compatibility
            'stop_price': order_params.get('stop_price')
        }
        
        # Send updated open orders to all clients
        socketio.emit('open_orders', list(open_orders.values()))
        
        logger.info(f"Order placed: {side} {quantity} @ {order_params.get('price')} ({order_type})")
        
        # Return success response through callback if available
        return {
            'success': True,
            'message': f'{side.upper()} {order_type.upper()} order placed successfully',
            'order_id': order_id,
            'order_details': open_orders[order_id]
        }
        
    except Exception as e:
        logger.error(f"Error placing order: {str(e)}")
        # Return error response through callback if available
        return {
            'success': False,
            'message': f'Server error: {str(e)}'
        }


@socketio.on('cancel_order')
def handle_cancel_order(data):
    """Handle order cancellation from UI."""
    try:
        order_id = data.get('order_id')
        if not order_id:
            socketio.emit('cancel_result', {
                'success': False,
                'message': 'No order ID provided'
            })
            return
            
        result = orderbook.cancel_order(order_id)
        if result:
            # Remove from open orders
            if order_id in open_orders:
                del open_orders[order_id]
                
            socketio.emit('cancel_result', {
                'success': True,
                'message': f'Order {order_id} canceled successfully',
                'order_id': order_id
            })
            
            # Send updated open orders
            socketio.emit('open_orders', list(open_orders.values()))
            
            logger.info(f"Order canceled: {order_id}")
        else:
            socketio.emit('cancel_result', {
                'success': False,
                'message': f'Order {order_id} not found or already filled'
            })
            
    except Exception as e:
        logger.error(f"Error canceling order: {str(e)}")
        socketio.emit('cancel_result', {
            'success': False,
            'message': f'Server error: {str(e)}'
        })


@socketio.on('cancel_all_orders')
def handle_cancel_all_orders():
    """Handle cancellation of all open orders."""
    try:
        cancel_count = 0
        failed_count = 0
        order_ids = list(open_orders.keys())
        
        for order_id in order_ids:
            result = orderbook.cancel_order(order_id)
            if result:
                del open_orders[order_id]
                cancel_count += 1
            else:
                failed_count += 1
                
        socketio.emit('cancel_all_result', {
            'success': True,
            'message': f'Canceled {cancel_count} orders, {failed_count} failed',
            'canceled': cancel_count,
            'failed': failed_count
        })
        
        # Send updated open orders
        socketio.emit('open_orders', list(open_orders.values()))
        logger.info(f"Canceled {cancel_count} orders, {failed_count} failed")
            
    except Exception as e:
        logger.error(f"Error in cancel all orders: {str(e)}")
        socketio.emit('cancel_all_result', {
            'success': False,
            'message': f'Server error: {str(e)}'
        })


@socketio.on('toggle_order_generation')
def handle_toggle_generation(data):
    """Toggle automatic order generation with enhanced configuration options."""
    global ORDER_GEN_ENABLED, order_gen_thread, GEN_INTERVAL_SECONDS
    
    enabled = data.get('enabled', False)
    ORDER_GEN_ENABLED = enabled
    
    # Update generation interval if provided
    if 'interval' in data:
        try:
            interval = float(data['interval'])
            if 0.1 <= interval <= 10.0:  # Reasonable bounds
                GEN_INTERVAL_SECONDS = interval
        except (ValueError, TypeError):
            pass
    
    if enabled and (order_gen_thread is None or not order_gen_thread.is_alive()):
        # Start a new order generator thread
        order_gen_thread = threading.Thread(target=order_generator, daemon=True)
        order_gen_thread.start()
        socketio.emit('generator_status', {
            'enabled': True,
            'interval': GEN_INTERVAL_SECONDS
        })
        logger.info(f"Order generation started with interval {GEN_INTERVAL_SECONDS}s")
    elif not enabled:
        # Generator will stop at next check of ORDER_GEN_ENABLED
        socketio.emit('generator_status', {
            'enabled': False,
            'interval': GEN_INTERVAL_SECONDS
        })
        logger.info("Order generation stopped")


def emit_orderbook_update():
    """Send enhanced orderbook state to all clients."""
    try:
        # Get orderbook snapshot with depth parameter (handled by adapter)
        snapshot = orderbook.get_snapshot(depth=25)
        logger.debug(f"Emitting orderbook update: {len(snapshot['bids'])} bids, {len(snapshot['asks'])} asks")
        
        # Calculate market stats if possible
        if snapshot["bids"] and snapshot["asks"]:
            # Find best bid/ask prices
            try:
                sorted_bids = sorted([level["price"] for level in snapshot["bids"]], reverse=True)
                sorted_asks = sorted([level["price"] for level in snapshot["asks"]])
                
                best_bid = sorted_bids[0] if sorted_bids else 0
                best_ask = sorted_asks[0] if sorted_asks else float('inf')
                
                # Ensure the book isn't crossed
                if best_ask <= best_bid:
                    logger.warning(f"Crossed orderbook detected: best bid {best_bid} >= best ask {best_ask}")
                    # Artificially adjust for visualization
                    best_ask = best_bid * 1.0001
                
                mid_price = (best_bid + best_ask) / 2
                spread = best_ask - best_bid
                spread_percent = (spread / mid_price) * 100
                
                # Calculate 24h change (simulated for demo)
                change_24h = ((mid_price - BASE_PRICE) / BASE_PRICE) * 100
                
                # Calculate 24h volume (simulated for demo)
                volume_24h = sum(trade['quantity'] for trade in recent_trades[-100:])
                
                # Calculate total bid/ask depth
                total_bid_qty = sum(level["quantity"] for level in snapshot["bids"])
                total_ask_qty = sum(level["quantity"] for level in snapshot["asks"])
                
                snapshot["stats"] = {
                    "best_bid": best_bid,
                    "best_ask": best_ask,
                    "mid_price": mid_price,
                    "spread": spread,
                    "spread_percent": spread_percent,
                    "change_24h": change_24h,
                    "volume_24h": volume_24h,
                    "total_bid_qty": total_bid_qty,
                    "total_ask_qty": total_ask_qty
                }
                logger.debug(f"Stats calculated: spread={spread}, mid_price={mid_price}")
            except Exception as e:
                logger.error(f"Error calculating orderbook stats: {str(e)}")
                snapshot["stats"] = {}
        else:
            logger.debug("Not enough data to calculate stats (empty book)")
            snapshot["stats"] = {}
        
        # Add timestamp
        snapshot["timestamp"] = time.time()
        
        # Add open order count
        snapshot["open_order_count"] = len(open_orders)
        
        # Emit to all clients
        socketio.emit('orderbook_update', snapshot)
        logger.debug("Orderbook update emitted successfully")
        
    except Exception as e:
        logger.error(f"Error sending orderbook update: {str(e)}")
        # Try to send an empty orderbook if there's an error
        try:
            empty_snapshot = {"bids": [], "asks": [], "stats": {}, "timestamp": time.time()}
            socketio.emit('orderbook_update', empty_snapshot)
            logger.debug("Empty orderbook update emitted as fallback")
        except Exception as inner_e:
            logger.error(f"Error sending empty orderbook update: {str(inner_e)}")


def handle_orderbook_event(event_type, data):
    """Process orderbook events with enhanced data for the professional UI."""
    try:
        # For structure changes, update the book
        if event_type in [
            EventType.PRICE_LEVEL_ADDED, 
            EventType.PRICE_LEVEL_CHANGED,
            EventType.PRICE_LEVEL_REMOVED,
            EventType.DEPTH_CHANGED,
            EventType.ORDER_ADDED,
            EventType.ORDER_MODIFIED,
            EventType.ORDER_CANCELLED,
            EventType.ORDER_FILLED,
            EventType.BOOK_UPDATED
        ]:
            emit_orderbook_update()
        
        # Handle various order events
        if event_type == EventType.ORDER_ADDED:
            order_id = data.get('order_id')
            if order_id and order_id not in open_orders:
                # This is just for visualization as we already track orders in handle_place_order
                order_details = orderbook.get_order(order_id)
                if order_details:
                    open_orders[order_id] = {
                        'id': order_id,
                        'type': order_details.get('order_type', 'limit'),
                        'side': order_details.get('side', 'unknown'),
                        'price': order_details.get('price'),
                        'quantity': order_details.get('quantity'),
                        'time': order_details.get('timestamp', time.time()),
                        'stop_price': order_details.get('stop_price')
                    }
                    socketio.emit('open_orders', list(open_orders.values()))
        
        # Handle order modification
        elif event_type == EventType.ORDER_MODIFIED:
            order_id = data.get('order_id')
            if order_id and order_id in open_orders:
                order_details = orderbook.get_order(order_id)
                if order_details:
                    open_orders[order_id].update({
                        'price': order_details.get('price'),
                        'quantity': order_details.get('quantity'),
                        'stop_price': order_details.get('stop_price')
                    })
                    socketio.emit('open_orders', list(open_orders.values()))
        
        # Handle order filled or cancelled
        elif event_type in [EventType.ORDER_FILLED, EventType.ORDER_CANCELLED]:
            order_id = data.get('order_id')
            if order_id and order_id in open_orders:
                del open_orders[order_id]
                socketio.emit('open_orders', list(open_orders.values()))
                
        # Handle trade events
        elif event_type == EventType.TRADE_EXECUTED:
            track_trade(data)
            
            # Format trade for UI
            trade = {
                'id': data.get('trade_id', ''),
                'price': float(data['price']),
                'quantity': float(data['quantity']),
                'time': data.get('timestamp', time.time()),
                'side': data.get('taker_side', 'unknown'),
                'value': float(data['price']) * float(data['quantity'])
            }
            
            # Emit the trade to clients
            socketio.emit('trade', trade)
            logger.info(f"Trade: {data['quantity']} @ {data['price']} - {data.get('taker_side', 'unknown')}")
            
    except Exception as e:
        logger.error(f"Error in orderbook event handler: {str(e)}")


def generate_random_order():
    """Generate a realistic random order for testing and visualization."""
    # Get current market state
    snapshot = orderbook.get_snapshot(depth=10)
    
    # Initialize default values
    best_bid = None
    best_ask = None
    
    # Determine current mid price
    if snapshot["bids"] and snapshot["asks"]:
        best_bid = max(level["price"] for level in snapshot["bids"])
        best_ask = min(level["price"] for level in snapshot["asks"])
        mid_price = (best_bid + best_ask) / 2
    else:
        mid_price = BASE_PRICE
        
    # For market orders, we need safe values if the book is empty
    if not best_bid and "stats" in snapshot and snapshot["stats"].get("bestBid"):
        best_bid = snapshot["stats"]["bestBid"]
    else:
        best_bid = mid_price * 0.99  # Fallback
        
    if not best_ask and "stats" in snapshot and snapshot["stats"].get("bestAsk"):
        best_ask = snapshot["stats"]["bestAsk"]
    else:
        best_ask = mid_price * 1.01  # Fallback
    
    # Choose random side
    side = random.choice(["buy", "sell"])
    
    # Determine order type with probabilities
    order_type_rand = random.random()
    if order_type_rand < 0.7:  # 70% chance of limit order
        order_type = "limit"
    elif order_type_rand < 0.9:  # 20% chance of market order
        order_type = "market"
    else:  # 10% chance of stop order
        order_type = "stop_limit"
    
    # Generate quantity with realistic distribution
    # Use a lognormal distribution for more realistic quantity sizes
    quantity = round(random.lognormvariate(0, 0.5), 3)
    quantity = max(0.001, min(10.0, quantity))  # Bound between 0.001 and 10 BTC
    
    # Generate price based on order type and market conditions
    if order_type == "market":
        # Market order - price isn't important as it will cross immediately
        price = None
        stop_price = None
    elif order_type == "limit":
        # Limit order - more realistic price levels
        if side == "buy":
            # Buyers typically place orders slightly below market
            price_factor = 1.0 - (random.betavariate(2, 5) * PRICE_VOLATILITY)
            price = round(mid_price * price_factor, 2)
            stop_price = None
        else:
            # Sellers typically place orders slightly above market
            price_factor = 1.0 + (random.betavariate(2, 5) * PRICE_VOLATILITY)
            price = round(mid_price * price_factor, 2)
            stop_price = None
    else:  # stop_limit
        # Stop limit order
        if side == "buy":
            # Buy stop is typically above market
            stop_factor = 1.0 + (random.betavariate(2, 5) * PRICE_VOLATILITY * 2)
            stop_price = round(mid_price * stop_factor, 2)
            price = round(stop_price * 1.005, 2)  # Limit price slightly higher
        else:
            # Sell stop is typically below market
            stop_factor = 1.0 - (random.betavariate(2, 5) * PRICE_VOLATILITY * 2)
            stop_price = round(mid_price * stop_factor, 2)
            price = round(stop_price * 0.995, 2)  # Limit price slightly lower
    
    # For market orders, we need to set a price that will cross
    if order_type == "market":
        if side == "buy":
            price = best_ask * 1.1 if snapshot["asks"] else mid_price * 1.1
        else:
            price = best_bid * 0.9 if snapshot["bids"] else mid_price * 0.9
    
    return {
        "side": side,
        "price": price,
        "quantity": quantity,
        "order_type": order_type,
        "stop_price": stop_price
    }


def order_generator():
    """Generate realistic random orders periodically."""
    global ORDER_GEN_ENABLED
    
    logger.info("Order generator started")
    
    while ORDER_GEN_ENABLED:
        try:
            # Generate and place a random order
            order_params = generate_random_order()
            
            # Filter out None values for the API call
            filtered_params = {k: v for k, v in order_params.items() if v is not None}
            
            # Add user ID for tracking
            filtered_params['user_id'] = 'auto_generator'
            
            # Place the order
            order_id = orderbook.add_order(**filtered_params)
            
            order_type_str = order_params.get('order_type', 'limit')
            side = order_params.get('side', 'unknown')
            price = order_params.get('price', 'market')
            quantity = order_params.get('quantity', 0)
            
            logger.debug(f"Generated {order_type_str} {side} order: {quantity} @ {price}")
            
            # Random delay between orders with some variability
            delay = random.expovariate(1.0 / GEN_INTERVAL_SECONDS)
            delay = max(0.1, min(GEN_INTERVAL_SECONDS * 3, delay))  # Bound the delay
            time.sleep(delay)
            
            # Occasionally cancel some orders to simulate realistic behavior
            if random.random() < 0.2 and open_orders:  # 20% chance to cancel an order
                order_to_cancel = random.choice(list(open_orders.keys()))
                orderbook.cancel_order(order_to_cancel)
                logger.debug(f"Cancelled auto-generated order: {order_to_cancel}")
            
        except Exception as e:
            logger.error(f"Error in order generator: {str(e)}")
            time.sleep(1)  # Pause on error
    
    logger.info("Order generator stopped")


@app.route('/api/debug/book_data')
def api_debug_book_data():
    """Return debug information about the order book."""
    try:
        # Get direct access to the book manager's data
        book_data = {}
        
        # Check if orderbook is initialized
        if orderbook:
            # Get snapshot
            snapshot = orderbook.get_snapshot(depth=100)
            book_data['snapshot'] = snapshot
            
            # Get direct access to book manager if possible
            if hasattr(orderbook, 'orderbook') and hasattr(orderbook.orderbook, 'book_manager'):
                # Accessing through the adapter and orderbook
                book_manager = orderbook.orderbook.book_manager
                book_data['direct_access'] = True
            elif hasattr(orderbook, 'book_manager'):
                # Direct access to book_manager
                book_manager = orderbook.book_manager
                book_data['direct_access'] = True
            else:
                book_data['direct_access'] = False
                book_manager = None
            
            if book_manager:
                # Try to get all order IDs
                book_data['order_count'] = len(getattr(book_manager, '_orders', {}))
                book_data['price_levels'] = {
                    'bids': len(getattr(book_manager, '_bids', {})),
                    'asks': len(getattr(book_manager, '_asks', {}))
                }
        else:
            book_data['error'] = 'Orderbook not initialized'
        
        return jsonify(book_data)
    except Exception as e:
        return jsonify({'error': str(e)})


def initialize_orderbook(symbol, price_improvement=None):
    """Initialize the orderbook with a realistic market structure."""
    global orderbook, BASE_PRICE, OHLC_HISTORY
    
    logger.info(f"Initializing orderbook for {symbol}")
    
    # Create the orderbook
    original_orderbook = OrderBook(
        symbol=symbol,
        event_manager=event_manager,
        maker_fee_rate=0.0015,  # 0.15% maker fee
        taker_fee_rate=0.0025   # 0.25% taker fee
    )
    
    # Wrap the orderbook with the compatibility adapter
    orderbook = OrderBookAdapter(original_orderbook)
    
    # Subscribe to orderbook events
    for event_type in EventType:
        event_manager.subscribe(event_type, handle_orderbook_event)
    
    # Set base price based on symbol
    if symbol == "BTC/USD":
        BASE_PRICE = 20000.0
    elif symbol == "ETH/USD":
        BASE_PRICE = 1500.0
    elif symbol == "SOL/USD":
        BASE_PRICE = 45.0
    else:
        BASE_PRICE = 100.0
    
    # Initialize OHLC data with realistic historical data
    generate_historical_ohlc(symbol)
    
    # Define price ranges to avoid crossed orderbook
    lowest_ask = BASE_PRICE * 1.001  # 0.1% above base price
    highest_bid = BASE_PRICE * 0.999  # 0.1% below base price
    
    # Add bid orders (buy orders) with realistic distribution
    for i in range(20):
        # Create a more realistic price distribution
        if i < 5:
            # Tighter spreads near the top of the book
            offset = i * 0.05 * BASE_PRICE / 100
        else:
            # Wider spreads further from the top
            offset = (5 * 0.05 + (i - 5) * 0.2) * BASE_PRICE / 100
            
        price = highest_bid - offset
        
        # Quantities tend to be larger away from the midpoint
        quantity_factor = 1.0 + (i * 0.15)
        base_quantity = random.lognormvariate(0, 0.5)  # Lognormal distribution for quantity
        quantity = round(base_quantity * quantity_factor, 4)
        quantity = max(0.001, min(5.0, quantity))  # Bound between 0.001 and 5 BTC
        
        try:
            order_id = orderbook.add_order(side="buy", price=price, quantity=quantity)
            logger.debug(f"Added bid order: id={order_id}, price={price}, quantity={quantity}")
        except Exception as e:
            logger.error(f"Error adding bid order: {str(e)}")
    
    # Add ask orders (sell orders) with realistic distribution
    for i in range(20):
        # Create a more realistic price distribution
        if i < 5:
            # Tighter spreads near the top of the book
            offset = i * 0.05 * BASE_PRICE / 100
        else:
            # Wider spreads further from the top
            offset = (5 * 0.05 + (i - 5) * 0.2) * BASE_PRICE / 100
            
        price = lowest_ask + offset
        
        # Quantities tend to be larger away from the midpoint
        quantity_factor = 1.0 + (i * 0.15)
        base_quantity = random.lognormvariate(0, 0.5)  # Lognormal distribution for quantity
        quantity = round(base_quantity * quantity_factor, 4)
        quantity = max(0.001, min(5.0, quantity))  # Bound between 0.001 and 5 BTC
        
        try:
            order_id = orderbook.add_order(side="sell", price=price, quantity=quantity)
            logger.debug(f"Added ask order: id={order_id}, price={price}, quantity={quantity}")
        except Exception as e:
            logger.error(f"Error adding ask order: {str(e)}")
    
    # Check if orders were added successfully
    snapshot = orderbook.get_snapshot()
    logger.info(f"Orderbook initialized with {len(snapshot['bids'])} bids and {len(snapshot['asks'])} asks")
    
    logger.info("Orderbook initialized with realistic market structure")


def generate_historical_ohlc(symbol):
    """Generate realistic historical OHLC data for the chart."""
    global OHLC_HISTORY
    
    # Clear existing history
    OHLC_HISTORY = []
    
    # Set base values depending on the symbol
    if symbol == "BTC/USD":
        base_price = 20000.0
        volatility = 0.02  # 2% daily volatility
    elif symbol == "ETH/USD":
        base_price = 1500.0
        volatility = 0.025  # 2.5% daily volatility
    elif symbol == "SOL/USD":
        base_price = 45.0
        volatility = 0.035  # 3.5% daily volatility
    else:
        base_price = 100.0
        volatility = 0.02
    
    # Generate 1-minute candles for the past 24 hours
    current_time = int(time.time())
    start_time = current_time - (24 * 60 * 60)  # 24 hours ago
    
    price = base_price
    
    for timestamp in range(start_time, current_time, 60):  # 60 seconds = 1 minute
        # Random price movement following geometric Brownian motion
        price_change = random.normalvariate(0, volatility / (24 * 60))
        price = price * (1 + price_change)
        
        # Generate OHLC
        open_price = price
        high_price = price * (1 + random.uniform(0, volatility / (24 * 30)))
        low_price = price * (1 - random.uniform(0, volatility / (24 * 30)))
        close_price = price
        
        # Generate volume with lognormal distribution
        volume = random.lognormvariate(-1, 1) * 0.5
        
        OHLC_HISTORY.append({
            'time': timestamp,
            'open': open_price,
            'high': high_price,
            'low': low_price,
            'close': close_price,
            'volume': volume
        })
    
    logger.info(f"Generated {len(OHLC_HISTORY)} historical candles for {symbol}")


def run_visualizer(args):
    """Run the professional orderbook visualizer."""
    # Initialize the orderbook
    initialize_orderbook(args.symbol)
    
    # Start order generator if enabled
    global ORDER_GEN_ENABLED
    ORDER_GEN_ENABLED = args.auto_generate
    
    if ORDER_GEN_ENABLED:
        global order_gen_thread
        order_gen_thread = threading.Thread(target=order_generator, daemon=True)
        order_gen_thread.start()
    
    # Start the web server
    logger.info(f"Starting Professional Orderbook Visualizer on http://{args.host}:{args.port}")
    socketio.run(app, host=args.host, port=args.port, debug=args.debug)


def parse_args():
    """Parse command line arguments with enhanced options."""
    parser = argparse.ArgumentParser(description="Manticore Professional OrderBook Visualizer")
    parser.add_argument("--symbol", default="BTC/USD", help="Trading pair symbol")
    parser.add_argument("--port", type=int, default=5000, help="Port to run the server on")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind the server to")
    parser.add_argument("--auto-generate", action="store_true", help="Auto-generate random orders")
    parser.add_argument("--interval", type=float, default=1.0, 
                        help="Interval between auto-generated orders (seconds)")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    
    args = parser.parse_args()
    
    # Set the global interval if specified
    global GEN_INTERVAL_SECONDS
    if args.interval:
        GEN_INTERVAL_SECONDS = args.interval
        
    return args


if __name__ == "__main__":
    # Parse command line arguments
    args = parse_args()
    
    # Configure logging based on debug flag
    if args.debug:
        logger.setLevel(logging.DEBUG)
    
    # Run the visualizer
    run_visualizer(args) 