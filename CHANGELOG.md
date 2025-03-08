# Changelog

All notable changes to the manticore-orderbook project will be documented in this file.

## [1.0.1] - 2025-03-08

### Enhanced

- Improved market order processing reliability
- Enhanced visualization interface with horizontal layout
- Fixed error handling for invalid inputs

### Changed

- Modernized UI design for the visualization tool
- Updated company information across all documentation
- Improved socket connection reliability
- Enhanced error handling and user feedback

### Added

- New notification system for trade confirmations
- Better metrics display for market data
- Improved responsive design for different screen sizes

## [1.0.0] - 2023-03-06

### Major Refactoring

- Complete refactoring of the codebase to focus on core orderbook functionality
- Removed market manager, storage, and API modules to focus on integration-ready design
- Enhanced event system for improved integration with external systems

### Changed

- Redesigned the module to focus on a single responsibility - order book management
- Improved event system for better integration with external systems
- Comprehensive documentation for integration with other modules
- More consistent APIs and data structures

### Removed

- Removed `MarketManager` (to be replaced by external module)
- Removed storage functionality (to be handled by manticore-storage)
- Removed API server functionality
- Removed example files not related to core functionality

### Added

- New integration guides for connecting with other modules
- Detailed event system documentation
- Improved integration patterns and examples

## [0.3.0] - 2023-02-15

### Added

- Added batch operations for improved performance
- Implemented price improvement feature
- Added latency monitoring for performance analysis

### Changed

- Optimized depth queries with caching
- Improved thread safety for concurrent operations
- Enhanced fee calculation

## [0.2.0] - 2023-01-20

### Added

- Added Time-In-Force support (GTC, IOC, FOK, GTD)
- Implemented order expiry management
- Added user tracking for fee calculation

### Changed

- Improved matching algorithm efficiency
- Enhanced error handling and logging

## [0.1.0] - 2023-01-05

### Added

- Initial implementation of OrderBook with price-time priority
- Basic order management (add, modify, cancel)
- Simple matching engine
- Snapshot functionality
- Trade history tracking 