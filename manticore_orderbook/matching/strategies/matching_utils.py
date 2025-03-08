"""
Utility functions for order matching strategies.

This module provides common matching logic that can be shared across different
order matching strategies.
"""

import time
import uuid
from typing import Dict, List, Any, Tuple

from ...event_manager import EventType


def create_trade(maker_id: str, maker_order: Dict[str, Any], 
                taker_id: str, taker_order: Dict[str, Any],
                price: float, quantity: float,
                maker_fee_rate: float, taker_fee_rate: float) -> Dict[str, Any]:
    """
    Create a trade record between a maker and taker order.
    
    Args:
        maker_id: ID of the maker order
        maker_order: Maker order dictionary
        taker_id: ID of the taker order
        taker_order: Taker order dictionary
        price: Trade execution price
        quantity: Trade quantity
        maker_fee_rate: Fee rate for maker
        taker_fee_rate: Fee rate for taker
        
    Returns:
        Trade dictionary
    """
    trade = {
        "trade_id": str(uuid.uuid4()),
        "maker_order_id": maker_id,
        "taker_order_id": taker_id,
        "price": price,
        "quantity": quantity,
        "timestamp": time.time(),
        "maker_user_id": maker_order.get("user_id"),
        "taker_user_id": taker_order.get("user_id")
    }
    
    # Calculate fees
    trade_value = price * quantity
    trade["maker_fee"] = trade_value * maker_fee_rate
    trade["taker_fee"] = trade_value * taker_fee_rate
    
    return trade


def match_against_book(order: Dict[str, Any], book_manager, event_manager,
                      maker_fee_rate: float, taker_fee_rate: float) -> List[Dict[str, Any]]:
    """
    Match an order against the book according to price-time priority.
    
    Args:
        order: Order to match
        book_manager: BookManager instance
        event_manager: EventManager instance
        maker_fee_rate: Fee rate for makers
        taker_fee_rate: Fee rate for takers
        
    Returns:
        List of trade dictionaries resulting from the match
    """
    side = order["side"].lower()
    order_id = order["order_id"]
    remaining_qty = order["quantity"]
    trades = []
    price = order.get("price")
    
    if side in ("buy", "bid"):
        # Get sorted asks - lowest price first
        ask_prices = sorted(book_manager._asks)
        
        # Loop through each price level from lowest to highest
        for ask_price in ask_prices:
            # Stop if the price is above our limit
            if price is not None and ask_price > price:
                break
            
            # Get all orders at this price level
            orders_at_price = book_manager.get_orders_at_price("sell", ask_price)
            if not orders_at_price:
                continue
            
            # Match each order at this price level in time priority
            for maker_id, maker_order in list(orders_at_price.items()):
                maker_qty = maker_order["quantity"]
                
                # Calculate the trade quantity
                trade_qty = min(remaining_qty, maker_qty)
                
                # Update the maker order quantity in the book
                maker_order["quantity"] -= trade_qty
                
                # Update _orders dictionary as well for both maker order
                if maker_id in book_manager._orders:
                    book_manager._orders[maker_id]["quantity"] -= trade_qty
                
                # Create the trade
                trade = create_trade(
                    maker_id=maker_id,
                    maker_order=maker_order,
                    taker_id=order_id,
                    taker_order=order,
                    price=ask_price,
                    quantity=trade_qty,
                    maker_fee_rate=maker_fee_rate,
                    taker_fee_rate=taker_fee_rate
                )
                
                # Add the trade to our results and to the book manager
                trades.append(trade)
                book_manager.add_trade(trade)
                
                # Publish trade events
                if event_manager:
                    event_manager.publish(EventType.TRADE, trade)
                    event_manager.publish(EventType.TRADE_EXECUTED, trade)
                
                # Update remaining quantity
                remaining_qty -= trade_qty
                
                # Remove maker order if fully filled, or notify of modification
                if maker_order["quantity"] <= 0:
                    book_manager.remove_order(maker_id)
                    if event_manager:
                        event_manager.publish(EventType.ORDER_FILLED, {
                            "order_id": maker_id
                        })
                else:
                    if event_manager:
                        event_manager.publish(EventType.ORDER_MODIFIED, {
                            "order_id": maker_id,
                            "quantity": maker_order["quantity"]
                        })
                
                # Exit if we've filled the entire order
                if remaining_qty <= 0:
                    break
            
            # Exit the loop if the order is fully filled
            if remaining_qty <= 0:
                break
    else:  # "sell" or "ask"
        # Get sorted bids - highest price first
        bid_prices = sorted(book_manager._bids, reverse=True)
        
        # Loop through each price level from highest to lowest
        for bid_price in bid_prices:
            # Stop if the price is below our limit
            if price is not None and bid_price < price:
                break
            
            # Get all orders at this price level
            orders_at_price = book_manager.get_orders_at_price("buy", bid_price)
            if not orders_at_price:
                continue
            
            # Match each order at this price level in time priority
            for maker_id, maker_order in list(orders_at_price.items()):
                maker_qty = maker_order["quantity"]
                
                # Calculate the trade quantity
                trade_qty = min(remaining_qty, maker_qty)
                
                # Update the maker order quantity in the book
                maker_order["quantity"] -= trade_qty
                
                # Update _orders dictionary as well for maker order
                if maker_id in book_manager._orders:
                    book_manager._orders[maker_id]["quantity"] -= trade_qty
                
                # Create the trade
                trade = create_trade(
                    maker_id=maker_id,
                    maker_order=maker_order,
                    taker_id=order_id,
                    taker_order=order,
                    price=bid_price,
                    quantity=trade_qty,
                    maker_fee_rate=maker_fee_rate,
                    taker_fee_rate=taker_fee_rate
                )
                
                # Add the trade to our results and to the book manager
                trades.append(trade)
                book_manager.add_trade(trade)
                
                # Publish trade events
                if event_manager:
                    event_manager.publish(EventType.TRADE, trade)
                    event_manager.publish(EventType.TRADE_EXECUTED, trade)
                
                # Update remaining quantity
                remaining_qty -= trade_qty
                
                # Remove maker order if fully filled, or notify of modification
                if maker_order["quantity"] <= 0:
                    book_manager.remove_order(maker_id)
                    if event_manager:
                        event_manager.publish(EventType.ORDER_FILLED, {
                            "order_id": maker_id
                        })
                else:
                    if event_manager:
                        event_manager.publish(EventType.ORDER_MODIFIED, {
                            "order_id": maker_id,
                            "quantity": maker_order["quantity"]
                        })
                
                # Exit if we've filled the entire order
                if remaining_qty <= 0:
                    break
            
            # Exit the loop if the order is fully filled
            if remaining_qty <= 0:
                break
    
    # Update the taker order with remaining quantity
    order["quantity"] = remaining_qty
    
    # Also update the order in the orders dictionary if it exists
    if order_id in book_manager._orders:
        book_manager._orders[order_id]["quantity"] = remaining_qty
    
    return trades


def simulate_match(order: Dict[str, Any], book_manager) -> Tuple[List[Dict[str, Any]], float]:
    """
    Simulate matching an order without actually executing trades.
    
    Args:
        order: Order to simulate matching
        book_manager: BookManager instance
        
    Returns:
        Tuple of (list of simulated trades, remaining quantity)
    """
    # Create a deep copy of the order to avoid modifying the original
    sim_order = order.copy()
    
    # Create a dummy event manager that doesn't actually publish events
    class DummyEventManager:
        def publish(self, *args, **kwargs):
            pass
    
    # Create a dummy book manager that doesn't actually modify the book
    class DummyBookManager:
        def __init__(self, real_book_manager):
            self._real_book_manager = real_book_manager
            self._asks = real_book_manager._asks.copy()
            self._bids = real_book_manager._bids.copy()
            # Add _orders attribute to handle the updates we added in match_against_book
            self._orders = {}
            
        def get_orders_at_price(self, side, price):
            # Create a deep copy of the orders to avoid modifying the real book
            orders = self._real_book_manager.get_orders_at_price(side, price)
            return {order_id: order.copy() for order_id, order in orders.items()}
            
        def get_best_ask(self):
            return self._real_book_manager.get_best_ask()
            
        def get_best_bid(self):
            return self._real_book_manager.get_best_bid()
            
        def remove_order(self, order_id):
            # Don't actually remove the order
            pass
            
        def add_trade(self, trade):
            # Don't actually add the trade
            pass
    
    # Create the dummy book manager
    dummy_book_manager = DummyBookManager(book_manager)
    
    # Match the order using the dummy managers
    trades = match_against_book(
        order=sim_order,
        book_manager=dummy_book_manager,
        event_manager=DummyEventManager(),
        maker_fee_rate=0.0,  # Fees don't matter for simulation
        taker_fee_rate=0.0
    )
    
    return trades, sim_order["quantity"] 