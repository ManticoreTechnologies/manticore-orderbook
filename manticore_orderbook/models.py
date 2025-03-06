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
        side_str = side_str.lower()
        if side_str in ('buy', 'bid'):
            return cls.BUY
        elif side_str in ('sell', 'ask'):
            return cls.SELL
        else:
            raise ValueError(f"Invalid side: {side_str}. Must be 'buy' or 'sell'.")
    
    def __str__(self) -> str:
        """Return string representation of side."""
        return "buy" if self == Side.BUY else "sell"


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
    """
    order_id: str
    side: Side
    price: float
    quantity: float
    timestamp: float
    time_in_force: TimeInForce = TimeInForce.GTC
    expiry_time: Optional[float] = None
    user_id: Optional[str] = None
    
    def __init__(
        self, 
        side: Union[str, Side], 
        price: float, 
        quantity: float, 
        order_id: Optional[str] = None,
        timestamp: Optional[float] = None,
        time_in_force: Union[str, TimeInForce, None] = None,
        expiry_time: Optional[float] = None,
        user_id: Optional[str] = None
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
        """
        self.order_id = order_id or str(uuid.uuid4())
        self.side = side if isinstance(side, Side) else Side.from_string(side)
        self.price = float(price)
        self.quantity = float(quantity)
        self.timestamp = timestamp or time.time()
        self.time_in_force = (time_in_force if isinstance(time_in_force, TimeInForce) 
                             else TimeInForce.from_string(time_in_force))
        self.expiry_time = expiry_time
        self.user_id = user_id
        
        # Validation
        if self.price <= 0:
            raise ValueError("Price must be positive")
        if self.quantity <= 0:
            raise ValueError("Quantity must be positive")
        if self.time_in_force == TimeInForce.GTD and self.expiry_time is None:
            raise ValueError("Expiry time is required for GTD orders")
    
    def update(self, price: Optional[float] = None, quantity: Optional[float] = None,
               expiry_time: Optional[float] = None) -> None:
        """
        Update order price, quantity, and/or expiry time.
        
        Args:
            price: New price (if None, keep current price)
            quantity: New quantity (if None, keep current quantity)
            expiry_time: New expiry time (if None, keep current expiry time)
        """
        if price is not None:
            if price <= 0:
                raise ValueError("Price must be positive")
            self.price = float(price)
        
        if quantity is not None:
            if quantity <= 0:
                raise ValueError("Quantity must be positive")
            self.quantity = float(quantity)
        
        if expiry_time is not None:
            self.expiry_time = expiry_time
            
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
            "user_id": self.user_id
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
            user_id=data.get("user_id")
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