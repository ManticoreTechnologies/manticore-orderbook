# Manticore OrderBook Professional Visualization Tool

This directory contains the professional version of the Manticore OrderBook visualization tool. This tool provides a modern, user-friendly interface for interacting with and visualizing the orderbook.

## Features

- **Real-time Order Book Display** - Live visualization of the order book with depth indication
- **Interactive Price Chart** - Professional TradingView-style chart with candlestick data
- **Trade History** - Track recent trades with sorting and filtering
- **Order Management** - Place and cancel orders through an intuitive interface
- **Multiple Order Types** - Support for limit, market, and stop-limit orders
- **Dark/Light Themes** - Professional UI with theme options
- **Responsive Design** - Works on desktop and mobile devices

## Getting Started

### Prerequisites

- Python 3.7 or higher
- Required Python packages: `flask`, `flask-socketio`, `termcolor`

You can install the required packages with:

```bash
pip3 install flask flask-socketio termcolor
```

### Running the Visualization Tool

#### Option 1: Using the Shell Script (Recommended)

The easiest way to start the tool is using the provided shell script:

```bash
chmod +x start_visualizer.sh  # Make it executable (first time only)
./start_visualizer.sh
```

#### Option 2: Running Directly with Python

You can also run the server directly with Python:

```bash
python3 run_server.py
```

### Command Line Options

Both methods support the following command line options:

- `--symbol SYMBOL` - Set the trading pair symbol (default: BTC/USD)
- `--port PORT` - Set the web server port (default: 5000)
- `--host HOST` - Set the web server host (default: 127.0.0.1)
- `--auto-generate` - Automatically generate random orders for testing
- `--debug` - Enable debug mode with additional logging

Example:

```bash
./start_visualizer.sh --symbol ETH/USD --port 8080 --debug
```

### Accessing the Interface

Once the server is running, access the visualization tool by navigating to:

```
http://127.0.0.1:5000/
```

(Replace 5000 with your chosen port if you specified a different one)

## Compatibility Considerations

This tool works with any version of the Manticore OrderBook library. For older versions, a compatibility adapter is automatically applied.

For more information about compatibility, see the [COMPATIBILITY.md](./COMPATIBILITY.md) file.

## Project Structure

- `run_server.py` - The main server script
- `start_visualizer.sh` - Shell script for easy startup
- `static/` - CSS, JavaScript, and other static assets
- `templates/` - HTML templates for the web interface
- `COMPATIBILITY.md` - Compatibility documentation

## Troubleshooting

If you encounter any issues:

1. Check the terminal output for error messages
2. Ensure all required packages are installed
3. Check the browser console for frontend errors
4. Try running with the `--debug` flag for more detailed logging

If you're still having issues, please report them on the project's issue tracker. 