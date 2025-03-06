"""
Data models for the order book system.
"""

import time
import uuid
import logging
from dataclasses import dataclass
from enum import Enum, auto
from typing import Dict, List, Optional, Any

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
            raise ValueError(f"Invalid time_in_force: {tif_str}. Must be 'GTC', 'IOC', 'FOK', or 'GTD'.")
    
    def __str__(self) -> str:
        """Return string representation of time-in-force."""
        return self.name


@dataclass
class Order:
    """Represents an order in the order book."""
    order_id: str
    side: Side
    price: float
    quantity: float
    timestamp: float  # Unix timestamp for order creation/update
    time_in_force: TimeInForce = TimeInForce.GTC
    expiry_time: Optional[float] = None
    user_id: Optional[str] = None  # User who placed the order, for fee tracking
    
    def __init__(
        self, 
        side: str, 
        price: float, 
        quantity: float, 
        order_id: Optional[str] = None,
        timestamp: Optional[float] = None,
        time_in_force: Optional[str] = None,
        expiry_time: Optional[float] = None,
        user_id: Optional[str] = None
    ):
        """
        Initialize a new order.
        
        Args:
            side: 'buy' or 'sell'
            price: Order price
            quantity: Order quantity
            order_id: Unique order ID (generated if not provided)
            timestamp: Order timestamp (current time if not provided)
            time_in_force: Time-in-force option ('GTC', 'IOC', 'FOK', 'GTD')
            expiry_time: Time when the order expires (required for GTD)
            user_id: User ID who placed the order (for fee tracking)
        """
        self.order_id = order_id or str(uuid.uuid4())
        self.side = Side.from_string(side)
        self.price = float(price)
        self.quantity = float(quantity)
        self.timestamp = timestamp or time.time()
        self.time_in_force = TimeInForce.from_string(time_in_force)
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
        Update order price and/or quantity.
        
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
        """Convert order to dictionary representation."""
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


@dataclass
class Trade:
    """Represents a trade in the order book."""
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
        """Convert trade to dictionary representation."""
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