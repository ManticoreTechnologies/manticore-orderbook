# API Reference

This page documents the main classes and methods of the Manticore OrderBook library.

## OrderBook Class

The main class that implements the order book functionality.

```python
class OrderBook:
    def __init__(self, symbol: str, max_trade_history: int = 10000,
                 maker_fee_rate: float = 0.0, taker_fee_rate: float = 0.0,
                 enable_logging: bool = True, log_level: int = logging.INFO,
                 check_expiry_interval: float = 1.0,
                 event_manager: Optional[EventManager] = None,
                 enable_price_improvement: bool = True)
```

### Constructor Parameters

- `symbol`: Trading pair symbol (e.g., "BTC/USD")
- `max_trade_history`: Maximum number of trades to keep in history
- `maker_fee_rate`: Fee rate for makers (liquidity providers)
- `taker_fee_rate`: Fee rate for takers (liquidity takers)
- `enable_logging`: Whether to enable logging
- `log_level`: Logging level (from Python's logging module)
- `check_expiry_interval`: Interval in seconds to check for expired orders
- `event_manager`: Custom event manager instance (optional)
- `enable_price_improvement`: Whether to enable price improvement for orders

### Main Methods

#### Adding Orders

```python
def add_order(self, side: str, price: float, quantity: float, order_id: Optional[str] = None,
              time_in_force: Optional[str] = None, expiry_time: Optional[float] = None,
              user_id: Optional[str] = None, order_type: Optional[str] = None,
              stop_price: Optional[float] = None, trail_value: Optional[float] = None,
              trail_is_percent: bool = False, displayed_quantity: Optional[float] = None) -> str
```

Adds a new order to the order book.

#### Cancelling Orders

```python
def cancel_order(self, order_id: str) -> bool
```

Cancels an existing order.

#### Modifying Orders

```python
def modify_order(self, order_id: str, new_price: Optional[float] = None, 
                 new_quantity: Optional[float] = None,
                 new_expiry_time: Optional[float] = None,
                 new_stop_price: Optional[float] = None,
                 new_trail_value: Optional[float] = None,
                 new_trail_is_percent: Optional[bool] = None,
                 new_displayed_quantity: Optional[float] = None) -> bool
```

Modifies an existing order.

#### Getting the Order Book Snapshot

```python
def get_snapshot(self, depth: int = None) -> Dict[str, Any]
```

Returns a snapshot of the current state of the order book.

#### Getting Order Details

```python
def get_order(self, order_id: str) -> Optional[Dict[str, Any]]
```

Returns details of a specific order.

#### Getting Trade History

```python
def get_trade_history(self, limit: int = 100) -> List[Dict[str, Any]]
```

Returns the trade history.

## Order Class

Represents an order in the order book.

```python
class Order:
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
    )
```

### Constructor Parameters

- `side`: Order side ('buy' or 'sell')
- `price`: Order price
- `quantity`: Order quantity
- `order_id`: Unique order ID (generated if not provided)
- `timestamp`: Order timestamp (current time if not provided)
- `time_in_force`: Time-in-force option ('GTC', 'IOC', 'FOK', 'GTD')
- `expiry_time`: Time when the order expires (required for GTD)
- `user_id`: User ID who placed the order
- `order_type`: Type of order ('LIMIT', 'MARKET', 'STOP_LIMIT', etc.)
- `stop_price`: Price at which stop orders are triggered
- `trail_value`: Value or percentage for trailing stop orders
- `trail_is_percent`: Whether trail_value is a percentage
- `displayed_quantity`: Visible quantity for iceberg orders

### Main Methods

#### Updating an Order

```python
def update(self, price: Optional[float] = None, quantity: Optional[float] = None,
           expiry_time: Optional[float] = None, stop_price: Optional[float] = None, 
           trail_value: Optional[float] = None, trail_is_percent: Optional[bool] = None,
           displayed_quantity: Optional[float] = None) -> None
```

Updates an order's properties.

#### Checking Expiration

```python
def is_expired(self, current_time: Optional[float] = None) -> bool
```

Checks if the order has expired.

#### Serialization

```python
def to_dict(self) -> Dict[str, Any]
```

Converts order to dictionary representation.

```python
@classmethod
def from_dict(cls, data: Dict[str, Any]) -> 'Order'
```

Creates an order from a dictionary.

## Trade Class

Represents a trade in the order book.

```python
class Trade:
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
    )
```

### Constructor Parameters

- `maker_order_id`: ID of the maker order
- `taker_order_id`: ID of the taker order
- `price`: Trade execution price
- `quantity`: Trade quantity
- `trade_id`: Unique trade ID (generated if not provided)
- `timestamp`: Trade timestamp (current time if not provided)
- `maker_fee`: Explicit maker fee (if None, calculated from rate)
- `taker_fee`: Explicit taker fee (if None, calculated from rate)
- `maker_fee_rate`: Fee rate for maker (e.g., 0.001 for 0.1%)
- `taker_fee_rate`: Fee rate for taker (e.g., 0.002 for 0.2%)
- `maker_user_id`: User ID of the maker
- `taker_user_id`: User ID of the taker

### Main Methods

#### Serialization

```python
def to_dict(self) -> Dict[str, Any]
```

Converts trade to dictionary representation.

```python
@classmethod
def from_dict(cls, data: Dict[str, Any]) -> 'Trade'
```

Creates a trade from a dictionary.

## EventManager Class

Manages events in the order book system.

```python
class EventManager:
    def __init__(self, enable_logging: bool = True, log_level: int = logging.INFO,
                 max_history_size: int = 1000)
```

### Constructor Parameters

- `enable_logging`: Whether to enable logging
- `log_level`: Logging level
- `max_history_size`: Maximum number of events to keep in history

### Main Methods

#### Event Subscription

```python
def subscribe(self, event_type: EventType, handler: EventHandler) -> None
```

Subscribes a handler to an event type.

```python
def unsubscribe(self, event_type: EventType, handler: EventHandler) -> bool
```

Unsubscribes a handler from an event type.

#### Event Publishing

```python
def publish(self, event_type: EventType, data: Dict[str, Any], symbol: Optional[str] = None) -> None
```

Publishes an event to all subscribers.

#### Event History

```python
def get_event_history(self, limit: int = 100, event_type: Optional[EventType] = None,
                     symbol: Optional[str] = None) -> List[Dict[str, Any]]
```

Retrieves event history with optional filtering. 