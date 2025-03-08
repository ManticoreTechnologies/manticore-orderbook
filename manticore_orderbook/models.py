"""
Data models for the Manticore OrderBook system.

These models represent the core data structures used by the order book system,
including orders and trades. They are designed to be serializable for easy integration
with storage systems.
"""

import time
import uuid
import logging
from dataclasses import dataclass
from enum import Enum, auto
from typing import Dict, List, Optional, Any, Union

# Configure logging
logger = logging.getLogger("manticore_orderbook.models")

class Side(Enum):
    """Order side enumeration."""
    BUY = auto()
    SELL = auto()
    
    @classmethod
    def from_string(cls, side_str: str) -> 'Side':
        """Convert a string to a Side enum value."""
        if side_str.upper() in ('BUY', 'BID'):
            return cls.BUY
        elif side_str.upper() in ('SELL', 'ASK'):
            return cls.SELL
        else:
            raise ValueError(f"Invalid side: {side_str}. Must be 'buy' or 'sell'.")
    
    def __str__(self) -> str:
        return self.name.lower()


class OrderType(Enum):
    """Order type enumeration."""
    LIMIT = auto()      # Standard limit order
    MARKET = auto()     # Market order (executed at best available price)
    STOP_LIMIT = auto() # Stop-limit order (becomes limit order when price reaches stop price)
    STOP_MARKET = auto() # Stop-market order (becomes market order when price reaches stop price)
    POST_ONLY = auto()  # Only provides liquidity, never takes it
    ICEBERG = auto()    # Shows only part of the total order quantity
    TRAILING_STOP = auto()  # Stop price that moves with the market
    
    @classmethod
    def from_string(cls, type_str: Optional[str]) -> 'OrderType':
        """Convert a string to an OrderType enum value."""
        if type_str is None:
            return cls.LIMIT
            
        type_str = type_str.upper()
        if type_str == 'LIMIT':
            return cls.LIMIT
        elif type_str == 'MARKET':
            return cls.MARKET
        elif type_str == 'STOP_LIMIT':
            return cls.STOP_LIMIT
        elif type_str == 'STOP_MARKET':
            return cls.STOP_MARKET
        elif type_str == 'POST_ONLY':
            return cls.POST_ONLY
        elif type_str == 'ICEBERG':
            return cls.ICEBERG
        elif type_str == 'TRAILING_STOP':
            return cls.TRAILING_STOP
        else:
            raise ValueError(f"Invalid order type: {type_str}")
    
    def __str__(self) -> str:
        return self.name.lower()


class TimeInForce(Enum):
    """Time-in-force options for orders."""
    GTC = auto()  # Good Till Cancelled (default)
    IOC = auto()  # Immediate Or Cancel (fill what you can immediately, cancel the rest)
    FOK = auto()  # Fill Or Kill (fill completely immediately or cancel completely)
    GTD = auto()  # Good Till Date (good until a specified date/time)
    
    @classmethod
    def from_string(cls, tif_str: Optional[str]) -> 'TimeInForce':
        """Convert a string to a TimeInForce enum value."""
        if tif_str is None:
            return cls.GTC
            
        tif_str = tif_str.upper()
        if tif_str == 'GTC':
            return cls.GTC
        elif tif_str == 'IOC':
            return cls.IOC
        elif tif_str == 'FOK':
            return cls.FOK
        elif tif_str == 'GTD':
            return cls.GTD
        else:
            raise ValueError(f"Invalid time in force: {tif_str}. Must be 'GTC', 'IOC', 'FOK', or 'GTD'.")
    
    def __str__(self) -> str:
        """Return string representation of time in force."""
        return self.name


@dataclass
class Order:
    """
    Represents an order in the order book.
    
    Attributes:
        order_id: Unique order identifier
        side: Buy or sell side
        price: Order price
        quantity: Order quantity
        timestamp: Unix timestamp when the order was created/updated
        time_in_force: Order time-in-force policy
        expiry_time: Time when the order expires (for GTD orders)
        user_id: ID of the user who placed the order
        order_type: Type of order (limit, market, etc.)
        stop_price: Price at which stop orders trigger
        trail_value: Value or percentage for trailing stop orders
        trail_is_percent: Whether trail_value is a percentage (True) or absolute value (False)
        displayed_quantity: Visible quantity for iceberg orders
        execution_price: Actual execution price (different from price for market orders)
        is_triggered: Whether a stop order has been triggered
    """
    order_id: str
    side: Side
    price: float
    quantity: float
    timestamp: float
    time_in_force: TimeInForce = TimeInForce.GTC
    expiry_time: Optional[float] = None
    user_id: Optional[str] = None
    order_type: OrderType = OrderType.LIMIT
    stop_price: Optional[float] = None
    trail_value: Optional[float] = None
    trail_is_percent: bool = False
    displayed_quantity: Optional[float] = None
    execution_price: Optional[float] = None
    is_triggered: bool = False
    
    def __init__(
        self, 
        side: Union[str, Side], 
        price: float, 
        quantity: float, 
        order_id: Optional[str] = None,
        timestamp: Optional[float] = None,
        time_in_force: Union[str, TimeInForce, None] = None,
        expiry_time: Optional[float] = None,
        user_id: Optional[str] = None,
        order_type: Union[str, OrderType, None] = None,
        stop_price: Optional[float] = None,
        trail_value: Optional[float] = None,
        trail_is_percent: bool = False,
        displayed_quantity: Optional[float] = None
    ):
        """
        Initialize a new order.
        
        Args:
            side: 'buy' or 'sell' (or Side enum)
            price: Order price
            quantity: Order quantity
            order_id: Unique order ID (generated if not provided)
            timestamp: Order timestamp (current time if not provided)
            time_in_force: Time-in-force option ('GTC', 'IOC', 'FOK', 'GTD')
            expiry_time: Time when the order expires (required for GTD)
            user_id: User ID who placed the order
            order_type: Type of order ('LIMIT', 'MARKET', 'STOP_LIMIT', etc.)
            stop_price: Price at which stop orders are triggered
            trail_value: Value or percentage for trailing stop orders
            trail_is_percent: Whether trail_value is a percentage
            displayed_quantity: Visible quantity for iceberg orders
        """
        self.order_id = order_id or str(uuid.uuid4())
        self.side = side if isinstance(side, Side) else Side.from_string(side)
        self.price = float(price) if price is not None else None
        self.quantity = float(quantity)
        self.timestamp = timestamp or time.time()
        self.time_in_force = (time_in_force if isinstance(time_in_force, TimeInForce) 
                             else TimeInForce.from_string(time_in_force))
        self.expiry_time = expiry_time
        self.user_id = user_id
        self.order_type = (order_type if isinstance(order_type, OrderType)
                          else OrderType.from_string(order_type))
        self.stop_price = float(stop_price) if stop_price is not None else None
        self.trail_value = float(trail_value) if trail_value is not None else None
        self.trail_is_percent = bool(trail_is_percent)
        self.displayed_quantity = float(displayed_quantity) if displayed_quantity is not None else None
        self.execution_price = None
        self.is_triggered = False
        
        # Validation
        if self.order_type == OrderType.LIMIT and (self.price is None or self.price <= 0):
            raise ValueError("Price must be positive for limit orders")
        
        if self.order_type == OrderType.MARKET:
            self.price = None  # Market orders have no price
            
        if self.quantity <= 0:
            raise ValueError("Quantity must be positive")
            
        if self.time_in_force == TimeInForce.GTD and self.expiry_time is None:
            raise ValueError("Expiry time is required for GTD orders")
            
        if self.order_type in (OrderType.STOP_LIMIT, OrderType.STOP_MARKET) and self.stop_price is None:
            raise ValueError("Stop price is required for stop orders")
            
        if self.order_type == OrderType.TRAILING_STOP and self.trail_value is None:
            raise ValueError("Trail value is required for trailing stop orders")
            
        if self.order_type == OrderType.ICEBERG:
            if self.displayed_quantity is None:
                # Default to 10% of total quantity if not specified
                self.displayed_quantity = self.quantity * 0.1
            elif self.displayed_quantity > self.quantity:
                raise ValueError("Displayed quantity cannot be greater than total quantity")
    
    def update(self, price: Optional[float] = None, quantity: Optional[float] = None,
               expiry_time: Optional[float] = None, stop_price: Optional[float] = None, 
               trail_value: Optional[float] = None, trail_is_percent: Optional[bool] = None,
               displayed_quantity: Optional[float] = None) -> None:
        """
        Update order price, quantity, and/or expiry time.
        
        Args:
            price: New price (if None, keep current price)
            quantity: New quantity (if None, keep current quantity)
            expiry_time: New expiry time (if None, keep current expiry time)
            stop_price: New stop price for stop orders
            trail_value: New trail value for trailing stop orders
            trail_is_percent: New trail_is_percent setting
            displayed_quantity: New displayed quantity for iceberg orders
        """
        if price is not None:
            if self.order_type == OrderType.LIMIT and price <= 0:
                raise ValueError("Price must be positive for limit orders")
            self.price = float(price)
        
        if quantity is not None:
            if quantity <= 0:
                raise ValueError("Quantity must be positive")
            self.quantity = float(quantity)
            
            # Update displayed quantity proportionally for iceberg orders
            if self.order_type == OrderType.ICEBERG and self.displayed_quantity is not None:
                ratio = self.displayed_quantity / self.quantity
                self.displayed_quantity = quantity * ratio
        
        if expiry_time is not None:
            self.expiry_time = expiry_time
            
        if stop_price is not None:
            if self.order_type not in (OrderType.STOP_LIMIT, OrderType.STOP_MARKET):
                raise ValueError("Cannot set stop_price for non-stop orders")
            self.stop_price = float(stop_price)
            
        if trail_value is not None:
            if self.order_type != OrderType.TRAILING_STOP:
                raise ValueError("Cannot set trail_value for non-trailing stop orders")
            self.trail_value = float(trail_value)
            
        if trail_is_percent is not None:
            if self.order_type != OrderType.TRAILING_STOP:
                raise ValueError("Cannot set trail_is_percent for non-trailing stop orders")
            self.trail_is_percent = bool(trail_is_percent)
            
        if displayed_quantity is not None:
            if self.order_type != OrderType.ICEBERG:
                raise ValueError("Cannot set displayed_quantity for non-iceberg orders")
            if displayed_quantity > self.quantity:
                raise ValueError("Displayed quantity cannot be greater than total quantity")
            self.displayed_quantity = float(displayed_quantity)
            
        # Update timestamp when order is modified
        self.timestamp = time.time()
    
    def is_expired(self, current_time: Optional[float] = None) -> bool:
        """
        Check if the order has expired.
        
        Args:
            current_time: Current time (if None, use current system time)
            
        Returns:
            True if order has expired, False otherwise
        """
        if self.expiry_time is None:
            return False
            
        current_time = current_time or time.time()
        return current_time >= self.expiry_time
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert order to dictionary representation.
        
        Returns:
            Dict containing order data in a serializable format
        """
        return {
            "order_id": self.order_id,
            "side": str(self.side),
            "price": self.price,
            "quantity": self.quantity,
            "timestamp": self.timestamp,
            "time_in_force": str(self.time_in_force),
            "expiry_time": self.expiry_time,
            "user_id": self.user_id,
            "order_type": str(self.order_type),
            "stop_price": self.stop_price,
            "trail_value": self.trail_value,
            "trail_is_percent": self.trail_is_percent,
            "displayed_quantity": self.displayed_quantity,
            "execution_price": self.execution_price,
            "is_triggered": self.is_triggered
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Order':
        """
        Create an order from a dictionary.
        
        Args:
            data: Dictionary containing order data
            
        Returns:
            Order object
        """
        return cls(
            side=data["side"],
            price=data["price"],
            quantity=data["quantity"],
            order_id=data["order_id"],
            timestamp=data["timestamp"],
            time_in_force=data.get("time_in_force"),
            expiry_time=data.get("expiry_time"),
            user_id=data.get("user_id"),
            order_type=data.get("order_type"),
            stop_price=data.get("stop_price"),
            trail_value=data.get("trail_value"),
            trail_is_percent=data.get("trail_is_percent", False),
            displayed_quantity=data.get("displayed_quantity")
        )


@dataclass
class Trade:
    """
    Represents a trade in the order book.
    
    Attributes:
        trade_id: Unique trade identifier
        maker_order_id: ID of the order that was already in the book
        taker_order_id: ID of the order that matched against the maker
        price: Execution price of the trade
        quantity: Quantity of the trade
        timestamp: Unix timestamp when the trade occurred
        maker_fee: Fee charged to the maker
        taker_fee: Fee charged to the taker
        maker_user_id: ID of the maker user
        taker_user_id: ID of the taker user
    """
    trade_id: str
    maker_order_id: str
    taker_order_id: str
    price: float
    quantity: float
    timestamp: float
    maker_fee: float = 0.0
    taker_fee: float = 0.0
    maker_user_id: Optional[str] = None
    taker_user_id: Optional[str] = None
    
    def __init__(
        self,
        maker_order_id: str,
        taker_order_id: str,
        price: float,
        quantity: float,
        trade_id: Optional[str] = None,
        timestamp: Optional[float] = None,
        maker_fee: Optional[float] = None,
        taker_fee: Optional[float] = None,
        maker_fee_rate: float = 0.0,
        taker_fee_rate: float = 0.0,
        maker_user_id: Optional[str] = None,
        taker_user_id: Optional[str] = None
    ):
        """
        Initialize a new trade.
        
        Args:
            maker_order_id: ID of the maker order
            taker_order_id: ID of the taker order
            price: Trade execution price
            quantity: Trade quantity
            trade_id: Unique trade ID (generated if not provided)
            timestamp: Trade timestamp (current time if not provided)
            maker_fee: Explicit maker fee (if None, calculated from rate)
            taker_fee: Explicit taker fee (if None, calculated from rate)
            maker_fee_rate: Fee rate for maker (e.g., 0.001 for 0.1%)
            taker_fee_rate: Fee rate for taker (e.g., 0.002 for 0.2%)
            maker_user_id: User ID of the maker
            taker_user_id: User ID of the taker
        """
        self.trade_id = trade_id or str(uuid.uuid4())
        self.maker_order_id = maker_order_id
        self.taker_order_id = taker_order_id
        self.price = float(price)
        self.quantity = float(quantity)
        self.timestamp = timestamp or time.time()
        self.maker_user_id = maker_user_id
        self.taker_user_id = taker_user_id
        
        # Calculate fees if not explicitly provided
        trade_value = self.price * self.quantity
        self.maker_fee = maker_fee if maker_fee is not None else trade_value * maker_fee_rate
        self.taker_fee = taker_fee if taker_fee is not None else trade_value * taker_fee_rate
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert trade to dictionary representation.
        
        Returns:
            Dict containing trade data in a serializable format
        """
        return {
            "trade_id": self.trade_id,
            "maker_order_id": self.maker_order_id,
            "taker_order_id": self.taker_order_id,
            "price": self.price,
            "quantity": self.quantity,
            "timestamp": self.timestamp,
            "maker_fee": self.maker_fee,
            "taker_fee": self.taker_fee,
            "maker_user_id": self.maker_user_id,
            "taker_user_id": self.taker_user_id,
            "value": self.price * self.quantity
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Trade':
        """
        Create a trade from a dictionary.
        
        Args:
            data: Dictionary containing trade data
            
        Returns:
            Trade object
        """
        return cls(
            maker_order_id=data["maker_order_id"],
            taker_order_id=data["taker_order_id"],
            price=data["price"],
            quantity=data["quantity"],
            trade_id=data["trade_id"],
            timestamp=data["timestamp"],
            maker_fee=data.get("maker_fee", 0.0),
            taker_fee=data.get("taker_fee", 0.0),
            maker_user_id=data.get("maker_user_id"),
            taker_user_id=data.get("taker_user_id")
        ) 