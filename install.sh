#!/bin/bash
# Installation script for manticore-orderbook

# Ensure pip is available
if ! command -v pip3 &> /dev/null; then
    echo "Error: pip3 is not installed. Please install pip3 first."
    exit 1
fi

# Install the package in development mode
echo "Installing manticore-orderbook in development mode..."
pip3 install -e .

echo "Installation complete!"
echo "You can now import the package with: from manticore_orderbook import OrderBook" 