# Changelog

All notable changes to the manticore-orderbook library will be documented in this file.

## [0.3.0] - 2025-03-05

### Added
- MarketManager for multi-market support
- Time-In-Force order policies (GTC, IOC, FOK, GTD)
- Order expiry management with automatic cleanup
- High-resolution latency monitoring for all operations
- User-based order tracking across markets
- Enhanced fee structure with configurable rates
- Comprehensive exchange example
- Performance improvements for production use

### Improved
- Thread safety with enhanced locking mechanism
- Error handling and recovery for all operations
- Documentation with multi-market examples
- Latency statistics with percentile calculations
- API design for exchange integration

### Fixed
- Order expiry edge cases
- Race conditions in multi-threaded environments
- Fee calculation for partial fills

## [0.2.0] - 2025-03-04

### Added
- Efficient depth queries with caching for improved performance
- Batch order operations for high-frequency trading scenarios
- Atomic order modifications with rollback on error
- Price improvement matching logic for better execution prices
- Enhanced trade records with fee calculations
- Thread-safety for all operations with proper locking
- Comprehensive performance benchmarks
- Makefile for common development tasks
- Enhanced examples demonstrating advanced features
- Optional dependencies for development and benchmarking

### Improved
- Order book snapshots with configurable depth
- Internal data structures optimized for high-frequency operations
- FIFO execution for orders at the same price level
- Detailed logging and debugging capabilities
- Documentation with examples of advanced features

### Fixed
- Bid ordering to ensure proper price-time priority
- Edge cases in order matching algorithm

## [0.1.0] - 2025-03-01

### Added
- Initial release of manticore-orderbook
- Basic order book functionality with price-time priority
- Support for limit orders (buy/sell)
- Order modification and cancellation
- Simple order book snapshots
- Trade history tracking 