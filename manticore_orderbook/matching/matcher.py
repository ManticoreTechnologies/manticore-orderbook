"""
Order matching engine for the Manticore OrderBook.

This module implements the core matching engine that processes orders and 
matches them according to price-time priority rules.
"""

import logging
import time
import uuid
from typing import Dict, List, Optional, Any

from ..book_management.book_manager import BookManager
from ..event_manager import EventManager, EventType
from .strategies import (
    OrderMatchingStrategy,
    LimitOrderStrategy,
    MarketOrderStrategy,
    FillOrKillOrderStrategy,
    ImmediateOrCancelOrderStrategy,
    StopOrderStrategy,
    PostOnlyOrderStrategy,
    IcebergOrderStrategy,
    GoodTillDateOrderStrategy
)

# Configure logging
logger = logging.getLogger("manticore_orderbook.matching")


class OrderMatcher:
    """
    OrderMatcher handles the logic for matching orders in the order book.
    
    It uses specialized strategies for different order types to process orders
    according to their specific requirements.
    """
    
    def __init__(self, enable_price_improvement: bool = False,
                maker_fee_rate: float = 0.0, taker_fee_rate: float = 0.0,
                book_manager: Optional[BookManager] = None,
                event_manager: Optional[EventManager] = None):
        """
        Initialize a new OrderMatcher.
        
        Args:
            enable_price_improvement: Whether to enable price improvement matching
            maker_fee_rate: Fee rate for makers (0.001 = 0.1%)
            taker_fee_rate: Fee rate for takers (0.001 = 0.1%)
            book_manager: BookManager instance to use
            event_manager: EventManager instance to use
        """
        self.enable_price_improvement = enable_price_improvement
        self.maker_fee_rate = maker_fee_rate
        self.taker_fee_rate = taker_fee_rate
        self.book_manager = book_manager
        self.event_manager = event_manager
        
        # Initialize order matching strategies
        self._strategies = {}
    
    def _get_strategy(self, order: Dict[str, Any]) -> OrderMatchingStrategy:
        """
        Get the appropriate strategy for an order.
        
        Args:
            order: Order dictionary
            
        Returns:
            An OrderMatchingStrategy instance appropriate for the order
        """
        order_type = order.get("order_type", "LIMIT")
        order_type = order_type.upper() if order_type is not None else "LIMIT"
        
        time_in_force = order.get("time_in_force", "GTC")
        time_in_force = time_in_force.upper() if time_in_force is not None else "GTC"
        
        # Strategy key combines order type and time-in-force
        strategy_key = f"{order_type}_{time_in_force}"
        
        # Return cached strategy if available
        if strategy_key in self._strategies:
            return self._strategies[strategy_key]
        
        # Create new strategy based on order type and time-in-force
        if time_in_force == "FOK":
            strategy = FillOrKillOrderStrategy(
                book_manager=self.book_manager,
                event_manager=self.event_manager,
                maker_fee_rate=self.maker_fee_rate,
                taker_fee_rate=self.taker_fee_rate
            )
        elif time_in_force == "IOC":
            strategy = ImmediateOrCancelOrderStrategy(
                book_manager=self.book_manager,
                event_manager=self.event_manager,
                maker_fee_rate=self.maker_fee_rate,
                taker_fee_rate=self.taker_fee_rate
            )
        elif time_in_force == "GTD":
            strategy = GoodTillDateOrderStrategy(
                book_manager=self.book_manager,
                event_manager=self.event_manager,
                maker_fee_rate=self.maker_fee_rate,
                taker_fee_rate=self.taker_fee_rate
            )
        elif order_type == "MARKET":
            strategy = MarketOrderStrategy(
                book_manager=self.book_manager,
                event_manager=self.event_manager,
                maker_fee_rate=self.maker_fee_rate,
                taker_fee_rate=self.taker_fee_rate
            )
        elif order_type in ("STOP_LIMIT", "STOP_MARKET"):
            strategy = StopOrderStrategy(
                book_manager=self.book_manager,
                event_manager=self.event_manager,
                maker_fee_rate=self.maker_fee_rate,
                taker_fee_rate=self.taker_fee_rate
            )
        elif order_type == "POST_ONLY":
            strategy = PostOnlyOrderStrategy(
                book_manager=self.book_manager,
                event_manager=self.event_manager,
                maker_fee_rate=self.maker_fee_rate,
                taker_fee_rate=self.taker_fee_rate
            )
        elif order_type == "ICEBERG":
            strategy = IcebergOrderStrategy(
                book_manager=self.book_manager,
                event_manager=self.event_manager,
                maker_fee_rate=self.maker_fee_rate,
                taker_fee_rate=self.taker_fee_rate
            )
        else:  # Default to limit order strategy
            strategy = LimitOrderStrategy(
                book_manager=self.book_manager,
                event_manager=self.event_manager,
                maker_fee_rate=self.maker_fee_rate,
                taker_fee_rate=self.taker_fee_rate
            )
        
        # Cache strategy for future use
        self._strategies[strategy_key] = strategy
        
        return strategy
    
    def process_order(self, order: Dict[str, Any]) -> str:
        """
        Process an order, either adding it to the book or matching it against existing orders.
        
        Args:
            order: Dictionary containing order data
            
        Returns:
            Order ID of the processed order
        """
        # Ensure order has an ID
        if not order.get("order_id"):
            order["order_id"] = str(uuid.uuid4())
        
        # Validate order parameters
        side = order.get("side", "").lower() if order.get("side") else ""
        if side not in ("buy", "bid", "sell", "ask"):
            raise ValueError(f"Invalid order side: {side}")
            
        # Validate price for non-market orders
        order_type = order.get("order_type", "LIMIT").upper() if order.get("order_type") else "LIMIT"
        if order_type != "MARKET":
            price = order.get("price")
            if price is None or price <= 0:
                raise ValueError(f"Invalid price for {order_type} order: {price}")
                
        # Validate quantity
        quantity = order.get("quantity")
        if quantity is None or quantity <= 0:
            raise ValueError(f"Invalid quantity: {quantity}")
        
        # Keep track of original quantity for FOK orders
        time_in_force = order.get("time_in_force", "GTC")
        if time_in_force is not None and time_in_force.upper() == "FOK":
            order["original_quantity"] = order["quantity"]
        
        # Get the appropriate strategy for this order
        strategy = self._get_strategy(order)
        
        # Process the order using the strategy
        trades = strategy.process(order)
        
        return order["order_id"]
    
    def check_stop_orders(self) -> int:
        """
        Check all stop orders and trigger them if their conditions are met.
        
        Returns:
            Number of stop orders triggered
        """
        count = 0
        stop_orders = []
        
        # Find all stop orders
        for order_id, order in self.book_manager._orders.items():
            order_type = order.get("order_type", "").upper()
            if order_type in ("STOP_LIMIT", "STOP_MARKET") and not order.get("is_triggered", False):
                stop_orders.append((order_id, order))
        
        # Check each stop order
        for order_id, order in stop_orders:
            # Create a stop order strategy
            strategy = StopOrderStrategy(
                book_manager=self.book_manager,
                event_manager=self.event_manager,
                maker_fee_rate=self.maker_fee_rate,
                taker_fee_rate=self.taker_fee_rate
            )
            
            # Check if stop conditions are met
            if strategy._check_stop_conditions(order):
                # Remove from book so we can re-process it
                self.book_manager.remove_order(order_id)
                
                # Process the order now that it's triggered
                self.process_order(order)
                
                count += 1
                
                # Notify that the stop order was triggered
                if self.event_manager:
                    self.event_manager.publish(EventType.ORDER_TRIGGERED, {
                        "order_id": order_id
                    })
        
        return count
    
    def update_trailing_stops(self) -> int:
        """
        Update all trailing stop orders based on current market prices.
        
        Returns:
            Number of trailing stops updated
        """
        count = 0
        trailing_stops = []
        
        # Find all trailing stop orders
        for order_id, order in self.book_manager._orders.items():
            if order.get("order_type", "").upper() == "TRAILING_STOP":
                trailing_stops.append((order_id, order))
        
        # Update each trailing stop
        for order_id, order in trailing_stops:
            side = order["side"].lower()
            trail_value = order.get("trail_value")
            trail_is_percent = order.get("trail_is_percent", False)
            
            if trail_value is None:
                continue
                
            if side in ("buy", "bid"):
                # For buy trailing stops, update when price drops
                best_ask = self.book_manager.get_best_ask()
                if best_ask is None:
                    continue
                    
                if not order.get("last_price"):
                    # Initialize with current price
                    order["last_price"] = best_ask
                    order["stop_price"] = self._calculate_stop_price(best_ask, trail_value, trail_is_percent, side)
                    count += 1
                elif best_ask < order.get("last_price", float('inf')):
                    # Price has moved lower, adjust stop price
                    order["last_price"] = best_ask
                    order["stop_price"] = self._calculate_stop_price(best_ask, trail_value, trail_is_percent, side)
                    count += 1
            else:  # side in ("sell", "ask")
                # For sell trailing stops, update when price rises
                best_bid = self.book_manager.get_best_bid()
                if best_bid is None:
                    continue
                    
                if not order.get("last_price"):
                    # Initialize with current price
                    order["last_price"] = best_bid
                    order["stop_price"] = self._calculate_stop_price(best_bid, trail_value, trail_is_percent, side)
                    count += 1
                elif best_bid > order.get("last_price", 0):
                    # Price has moved higher, adjust stop price
                    order["last_price"] = best_bid
                    order["stop_price"] = self._calculate_stop_price(best_bid, trail_value, trail_is_percent, side)
                    count += 1
        
        return count
    
    def _correct_crossed_book(self) -> int:
        """
        Check if the order book is crossed and resolve crossed orders.
        
        A crossed book occurs when the highest bid price is greater than or equal to
        the lowest ask price. This method matches orders to prevent a crossed state.
        
        Returns:
            Number of orders matched to fix the crossed book
        """
        if not self.book_manager:
            return 0
            
        count = 0
        while True:
            # Get best bid and ask
            best_bid = self.book_manager.get_best_bid()
            best_ask = self.book_manager.get_best_ask()
            
            # If either is None or no cross exists, we're done
            if best_bid is None or best_ask is None or best_bid < best_ask:
                break
            
            # Find all orders at these price levels
            bid_orders = self.book_manager.get_orders_at_price("buy", best_bid)
            ask_orders = self.book_manager.get_orders_at_price("sell", best_ask)
            
            # If we have no orders at these prices, something is wrong
            if not bid_orders or not ask_orders:
                logger.error(f"Crossed book detected (bid={best_bid}, ask={best_ask}) but no orders found at these levels")
                break
                
            # Sort orders by timestamp (oldest first)
            sorted_bids = sorted(bid_orders.items(), key=lambda x: x[1]["timestamp"])
            sorted_asks = sorted(ask_orders.items(), key=lambda x: x[1]["timestamp"])
            
            # Match orders in time priority order
            for bid_id, bid_order in sorted_bids:
                if not sorted_asks:
                    break
                    
                for ask_idx, (ask_id, ask_order) in enumerate(sorted_asks):
                    # Determine match quantity
                    match_qty = min(bid_order["quantity"], ask_order["quantity"])
                    if match_qty <= 0:
                        continue
                        
                    # Create a trade
                    trade_price = best_ask  # Use ask price for the trade (taker pays ask)
                    
                    # Update order quantities
                    bid_order["quantity"] -= match_qty
                    ask_order["quantity"] -= match_qty
                    
                    # Create and record the trade
                    trade = {
                        "trade_id": str(uuid.uuid4()),
                        "maker_order_id": ask_id,  # Ask was in the book first
                        "taker_order_id": bid_id,  # Bid is the taker in this case
                        "price": trade_price,
                        "quantity": match_qty,
                        "timestamp": time.time(),
                        "maker_fee": match_qty * trade_price * self.maker_fee_rate,
                        "taker_fee": match_qty * trade_price * self.taker_fee_rate,
                        "maker_user_id": ask_order.get("user_id"),
                        "taker_user_id": bid_order.get("user_id")
                    }
                    
                    self.book_manager.add_trade(trade)
                    
                    # Publish trade event
                    if self.event_manager:
                        self.event_manager.publish(EventType.TRADE, trade)
                    
                    count += 1
                    
                    # Remove filled orders
                    if bid_order["quantity"] <= 0:
                        self.book_manager.remove_order(bid_id)
                        if self.event_manager:
                            self.event_manager.publish(EventType.ORDER_FILLED, {
                                "order_id": bid_id
                            })
                        break  # This bid is fully matched, move to next bid
                        
                    if ask_order["quantity"] <= 0:
                        self.book_manager.remove_order(ask_id)
                        if self.event_manager:
                            self.event_manager.publish(EventType.ORDER_FILLED, {
                                "order_id": ask_id
                            })
                        sorted_asks.pop(ask_idx)  # Remove this ask from the list
                        
                # If no more asks, break out of the bid loop
                if not sorted_asks:
                    break
            
            # If we didn't match anything, break to avoid infinite loop
            if count == 0:
                logger.warning(f"Could not resolve crossed book (bid={best_bid}, ask={best_ask})")
                break
                
        return count
    
    def _calculate_stop_price(self, price: float, trail_value: float, 
                            trail_is_percent: bool, side: str) -> float:
        """
        Calculate the stop price for a trailing stop order.
        
        Args:
            price: Current price
            trail_value: Trail value (absolute or percentage)
            trail_is_percent: Whether trail value is a percentage
            side: Order side
            
        Returns:
            Calculated stop price
        """
        if trail_is_percent:
            trail_amount = price * (trail_value / 100.0)
        else:
            trail_amount = trail_value
            
        if side in ("buy", "bid"):
            # For buy trailing stops, stop price is above current price
            return price + trail_amount
        else:  # side in ("sell", "ask")
            # For sell trailing stops, stop price is below current price
            return price - trail_amount 