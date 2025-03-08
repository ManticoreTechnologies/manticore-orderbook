#!/bin/bash
# Start the Manticore OrderBook Visualization Tool
# This script makes it easy to launch the professional trading interface

# Default configuration
SYMBOL="BTC/USD"
PORT=5000
HOST="127.0.0.1"
AUTO_GENERATE="--auto-generate"
DEBUG=""

# Display usage information
function show_help {
    echo "Manticore OrderBook Visualization Tool"
    echo ""
    echo "Usage: $0 [options]"
    echo ""
    echo "Options:"
    echo "  -s, --symbol SYMBOL     Trading pair symbol (default: BTC/USD)"
    echo "  -p, --port PORT         Port to run the server on (default: 5000)"
    echo "  -h, --host HOST         Host to bind the server to (default: 127.0.0.1)"
    echo "  -n, --no-generate       Disable auto-generation of random orders"
    echo "  -d, --debug             Enable debug mode"
    echo "  --help                  Display this help message"
    echo ""
    echo "Example:"
    echo "  $0 --symbol ETH/USD --port 8080 --debug"
    echo ""
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -s|--symbol)
            SYMBOL="$2"
            shift 2
            ;;
        -p|--port)
            PORT="$2"
            shift 2
            ;;
        -h|--host)
            HOST="$2"
            shift 2
            ;;
        -n|--no-generate)
            AUTO_GENERATE=""
            shift
            ;;
        -d|--debug)
            DEBUG="--debug"
            shift
            ;;
        --help)
            show_help
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

# Change to the project root directory
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$PROJECT_ROOT" || exit 1

# Ensure required packages are installed
if ! python3 -c "import termcolor" &>/dev/null; then
    echo "Installing required packages..."
    python3 -m pip install termcolor
fi

# Start the visualizer
echo "Starting Manticore Professional OrderBook Visualization Tool..."
python3 manticore_orderbook/examples/run_server.py \
    --symbol "$SYMBOL" \
    --port "$PORT" \
    --host "$HOST" \
    $AUTO_GENERATE \
    $DEBUG

# Make script executable
# chmod +x manticore_orderbook/examples/start_visualizer.sh 