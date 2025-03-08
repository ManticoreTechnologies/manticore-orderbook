/**
 * Manticore OrderBook Visualization
 * 
 * This file contains the JavaScript code for the order book visualization,
 * featuring real-time updates, depth chart, and statistics.
 */

// Global variables
let socket;
let orderbookData = { bids: {}, asks: {}, stats: {} };
let currentPrecision = 2;
let isDarkTheme = true;
let currentSymbol = "BTC/USD";

// Socket connection setup
let hasLoggedInitialData = false;

// Initialize the application when DOM is fully loaded
document.addEventListener('DOMContentLoaded', function() {
    console.log("DOM fully loaded, initializing application...");
    
    // Socket connection
    const socket = io({
        reconnectionDelayMax: 10000,
        reconnectionAttempts: 10,
        transports: ['websocket']
    });

    // DOM Elements - Update selectors to match new HTML structure
    const bidsElement = document.getElementById('bids');
    const asksElement = document.getElementById('asks');
    const statusIndicator = document.querySelector('.status-indicator');
    const themeToggle = document.getElementById('theme-toggle');
    const autoGenerateToggle = document.getElementById('autoGenerateOrders');
    const noOrdersMessage = document.getElementById('no-orders-message');
    const noTradesMessage = document.getElementById('no-trades-message');
    const ordersTable = document.getElementById('orders');
    const tradesTable = document.getElementById('trades');
    const bestBidDisplay = document.querySelector('.best-bid-value');
    const bestAskDisplay = document.querySelector('.best-ask-value');
    const spreadDisplay = document.querySelector('.spread-value');
    const midPriceDisplay = document.querySelector('.mid-price-value');
    const bidVolumeDisplay = document.querySelector('.bid-volume-value');
    const askVolumeDisplay = document.querySelector('.ask-volume-value');
    const spreadRowDisplay = document.querySelector('.spread-row .spread-value');
    const cancelAllBtn = document.getElementById('cancelAllBtn');
    const precisionButtons = document.querySelectorAll('.precision-btn');
    
    // State variables
    let orderbookData = {
        bids: [],
        asks: [],
        bestBid: null,
        bestAsk: null,
        spread: null
    };
    let openOrders = [];
    let recentTrades = [];
    let precision = 2;
    let isConnected = false;
    
    // Setup socket connection
    function setupSocketConnection() {
        console.log("Setting up socket connection...");
        
        socket.on('connect', function() {
            console.log('Connected to server');
            isConnected = true;
            updateConnectionStatus(true);
        });
        
        socket.on('disconnect', function() {
            console.log('Disconnected from server');
            isConnected = false;
            updateConnectionStatus(false);
        });
        
        socket.on('orderbook_update', function(data) {
            console.log('Received orderbook update');
            updateOrderbook(data);
        });
        
        socket.on('trade', function(trade) {
            console.log('Received trade');
            addTrade(trade);
        });
        
        socket.on('trades', function(trades) {
            console.log('Received trade history', trades.length);
            recentTrades = trades;
            updateTrades(trades);
        });
        
        socket.on('order_placed', function(order) {
            console.log('Order placed', order);
            openOrders.push(order);
            updateOpenOrders();
            
            // Show notification
            showNotification(
                'Order Placed',
                `${order.side.toUpperCase()} ${formatNumber(order.quantity)} at ${formatNumber(order.price)}`,
                'success'
            );
        });
        
        socket.on('order_cancelled', function(data) {
            console.log('Order cancelled', data);
            
            // Remove from open orders
            openOrders = openOrders.filter(order => order.order_id !== data.order_id);
            updateOpenOrders();
            
            // Show notification
            showNotification('Order Cancelled', 'Order was successfully cancelled', 'info');
        });
        
        socket.on('orders', function(orders) {
            console.log('Received open orders', orders.length);
            openOrders = orders;
            updateOpenOrders();
        });
        
        socket.on('generator_status', function(status) {
            console.log('Received generator status', status);
            updateGeneratorStatus(status);
        });
        
        socket.on('ohlc', function(data) {
            console.log('Received OHLC data');
            if (typeof updateChart === 'function') {
                updateChart(data);
            } else {
                console.log(`Received ${data.candles.length} OHLC candles`);
            }
        });
        
        console.log("Socket event handlers registered");
    }
    
    // Update connection status indicator
    function updateConnectionStatus(connected) {
        if (!statusIndicator) {
            console.warn('Status indicator not found in DOM');
            return;
        }
        
        const statusDiv = statusIndicator.querySelector('div');
        const statusIcon = statusIndicator.querySelector('.spinner-grow');
        const statusText = statusIndicator.querySelector('small');
        
        if (connected) {
            statusDiv.style.backgroundColor = 'rgba(76, 175, 80, 0.15)';
            statusIcon.classList.remove('text-warning');
            statusIcon.classList.add('text-success');
            statusText.textContent = 'Connected';
            statusText.classList.remove('text-warning');
            statusText.classList.add('text-success');
        } else {
            statusDiv.style.backgroundColor = 'rgba(255, 193, 7, 0.15)';
            statusIcon.classList.remove('text-success');
            statusIcon.classList.add('text-warning');
            statusText.textContent = 'Connecting';
            statusText.classList.remove('text-success');
            statusText.classList.add('text-warning');
        }
    }
    
    // Process and handle orderbook updates
    function updateOrderbook(data) {
        try {
            console.log('Initial orderbook data:', data);
            
            // Update data
            if (data.bids) orderbookData.bids = data.bids;
            if (data.asks) orderbookData.asks = data.asks;
            
            // Update best bid/ask
            if (orderbookData.bids.length > 0) {
                orderbookData.bestBid = Math.max(...orderbookData.bids.map(b => b.price));
            }
            
            if (orderbookData.asks.length > 0) {
                orderbookData.bestAsk = Math.min(...orderbookData.asks.map(a => a.price));
            }
            
            // Update spread
            if (orderbookData.bestBid && orderbookData.bestAsk) {
                orderbookData.spread = orderbookData.bestAsk - orderbookData.bestBid;
            }
            
            // Render updates
            renderOrderbook();
            
        } catch (err) {
            console.error('Error updating orderbook:', err);
        }
    }
    
    // Render the orderbook to the DOM
    function renderOrderbook() {
        try {
            // Get DOM elements if not already cached
            const bidsElement = document.getElementById('bids');
            const asksElement = document.getElementById('asks');
            
            if (!bidsElement || !asksElement) {
                console.error('Orderbook containers not found in the DOM. Looking for #bids and #asks');
                return;
            }
            
            // Clear current content
            bidsElement.innerHTML = '';
            asksElement.innerHTML = '';
            
            // Sort asks (highest price first for display)
            const sortedAsks = [...orderbookData.asks].sort((a, b) => b.price - a.price);
            
            // Render asks
            sortedAsks.forEach(ask => {
                const row = document.createElement('tr');
                row.className = 'ask-row';
                
                // Calculate depth percentage for visualization
                const maxAskAmount = Math.max(...orderbookData.asks.map(a => a.amount || a.quantity || 0));
                const askAmount = ask.amount || ask.quantity || 0;
                const depthPercent = maxAskAmount > 0 ? (askAmount / maxAskAmount) * 100 : 0;
                
                row.style.setProperty('--depth-percent', `${depthPercent}%`);
                row.classList.add('ask-row-depth');
                
                // Format values
                const price = formatNumber(ask.price);
                const amount = formatNumber(askAmount, 4);
                const total = formatNumber((ask.price * askAmount));
                
                row.innerHTML = `
                    <td class="text-end">${price}</td>
                    <td class="text-end">${amount}</td>
                    <td class="text-end">${total}</td>
                `;
                
                asksElement.appendChild(row);
            });
            
            // Sort bids (highest price first)
            const sortedBids = [...orderbookData.bids].sort((a, b) => b.price - a.price);
            
            // Render bids
            sortedBids.forEach(bid => {
                const row = document.createElement('tr');
                row.className = 'bid-row';
                
                // Calculate depth percentage
                const maxBidAmount = Math.max(...orderbookData.bids.map(b => b.amount || b.quantity || 0));
                const bidAmount = bid.amount || bid.quantity || 0;
                const depthPercent = maxBidAmount > 0 ? (bidAmount / maxBidAmount) * 100 : 0;
                
                row.style.setProperty('--depth-percent', `${depthPercent}%`);
                row.classList.add('bid-row-depth');
                
                // Format values
                const price = formatNumber(bid.price);
                const amount = formatNumber(bidAmount, 4);
                const total = formatNumber((bid.price * bidAmount));
                
                row.innerHTML = `
                    <td class="text-end">${price}</td>
                    <td class="text-end">${amount}</td>
                    <td class="text-end">${total}</td>
                `;
                
                bidsElement.appendChild(row);
            });
            
            // Update market metrics
            updateMarketMetrics();
            
        } catch (err) {
            console.error('Error rendering orderbook:', err);
        }
    }
    
    // Update market metrics display
    function updateMarketMetrics() {
        try {
            // Update best bid display
            if (bestBidDisplay && orderbookData.bestBid) {
                bestBidDisplay.textContent = formatNumber(orderbookData.bestBid, precision);
                bestBidDisplay.classList.add('text-success');
            }
            
            // Update best ask display
            if (bestAskDisplay && orderbookData.bestAsk) {
                bestAskDisplay.textContent = formatNumber(orderbookData.bestAsk, precision);
                bestAskDisplay.classList.add('text-danger');
            }
            
            // Update spread display
            if (spreadDisplay && orderbookData.spread) {
                spreadDisplay.textContent = formatNumber(orderbookData.spread, precision);
            }
            
            // Update spread row display
            if (spreadRowDisplay && orderbookData.spread) {
                spreadRowDisplay.textContent = formatNumber(orderbookData.spread, precision);
            }
            
            // Update mid price
            if (midPriceDisplay && orderbookData.bestBid && orderbookData.bestAsk) {
                const midPrice = (orderbookData.bestBid + orderbookData.bestAsk) / 2;
                midPriceDisplay.textContent = formatNumber(midPrice, precision);
            }
            
            // Update bid volume
            if (bidVolumeDisplay) {
                const totalBidVolume = orderbookData.bids.reduce((sum, bid) => sum + (bid.amount || bid.quantity), 0);
                bidVolumeDisplay.textContent = formatNumber(totalBidVolume, 4);
            }
            
            // Update ask volume
            if (askVolumeDisplay) {
                const totalAskVolume = orderbookData.asks.reduce((sum, ask) => sum + (ask.amount || ask.quantity), 0);
                askVolumeDisplay.textContent = formatNumber(totalAskVolume, 4);
            }
        } catch (err) {
            console.error('Error updating market metrics:', err);
        }
    }
    
    // Format number with given precision
    function formatNumber(value, precisionValue = precision) {
        if (value === undefined || value === null) return '-.--';
        return parseFloat(value).toFixed(precisionValue);
    }
    
    // Update generator status
    function updateGeneratorStatus(status) {
        try {
            const autoGenerateToggle = document.getElementById('autoGenerateOrders');
            if (autoGenerateToggle) {
                autoGenerateToggle.checked = status.enabled;
            } else {
                console.warn('Auto-generate toggle element not found with ID "autoGenerateOrders"');
            }
        } catch (err) {
            console.error('Error updating generator status:', err);
        }
    }
    
    // Update open orders table
    function updateOpenOrders() {
        try {
            console.log('Updating open orders table with', openOrders.length, 'orders');
            
            // Get table element if not already cached
            const ordersTable = document.getElementById('orders');
            const noOrdersMessage = document.getElementById('no-orders-message');
            
            if (!ordersTable) {
                console.error('Orders table not found with ID "orders"');
                return;
            }
            
            // Clear current orders
            ordersTable.innerHTML = '';
            
            // Show/hide empty state message
            if (noOrdersMessage) {
                noOrdersMessage.style.display = openOrders.length === 0 ? 'block' : 'none';
            }
            
            if (openOrders.length === 0) return;
            
            // Render orders
            openOrders.forEach(order => {
                try {
                    // Handle different property names (order.order_type vs order.type)
                    const orderType = order.order_type || order.type || 'unknown';
                    const side = order.side || 'unknown';
                    const price = order.price || 0;
                    const quantity = order.quantity || order.amount || 0;
                    const total = price * quantity;
                    const time = order.timestamp 
                        ? new Date(order.timestamp * 1000).toLocaleTimeString() 
                        : new Date().toLocaleTimeString();
                    const orderId = order.order_id || order.id || Math.random().toString(36).substring(2, 10);
                    
                    const row = document.createElement('tr');
                    row.innerHTML = `
                        <td>${orderType.toUpperCase()}</td>
                        <td class="${side.toLowerCase() === 'buy' ? 'text-success' : 'text-danger'}">${side.toUpperCase()}</td>
                        <td class="text-end">${formatNumber(price)}</td>
                        <td class="text-end">${formatNumber(quantity, 4)}</td>
                        <td class="text-end">${formatNumber(total)}</td>
                        <td>${time}</td>
                        <td>
                            <button class="btn btn-sm btn-outline-danger cancel-order-btn" data-order-id="${orderId}">
                                <i class="fas fa-times"></i>
                            </button>
                        </td>
                    `;
                    
                    ordersTable.appendChild(row);
                } catch (err) {
                    console.error('Error rendering order row:', err);
                }
            });
            
            // Add event listeners to cancel buttons
            document.querySelectorAll('.cancel-order-btn').forEach(btn => {
                btn.addEventListener('click', function() {
                    const orderId = this.getAttribute('data-order-id');
                    cancelOrder(orderId);
                });
            });
            
        } catch (err) {
            console.error('Error updating open orders:', err);
        }
    }
    
    // Update trades table
    function updateTrades() {
        try {
            // Get table element if not already cached
            const tradesTable = document.getElementById('trades');
            const noTradesMessage = document.getElementById('no-trades-message');
            
            if (!tradesTable) {
                console.error('Trades table not found with ID "trades"');
                return;
            }
            
            // Clear current trades
            tradesTable.innerHTML = '';
            
            // Show/hide empty state message
            if (noTradesMessage) {
                noTradesMessage.style.display = recentTrades.length === 0 ? 'block' : 'none';
            }
            
            if (recentTrades.length === 0) return;
            
            // Sort trades by timestamp (newest first)
            const sortedTrades = [...recentTrades].sort((a, b) => {
                const timeA = a.timestamp || 0;
                const timeB = b.timestamp || 0;
                return timeB - timeA;
            });
            
            // Display only recent trades (limit to 50)
            const displayTrades = sortedTrades.slice(0, 50);
            
            // Render trades
            displayTrades.forEach(trade => {
                try {
                    // Handle taker side vs maker side
                    let side = trade.side;
                    if (!side) {
                        // Try to determine side from maker/taker
                        if (trade.taker_side) {
                            side = trade.taker_side;
                        } else if (trade.is_buyer_maker) {
                            side = 'sell'; // If buyer is maker, taker is seller
                        } else {
                            side = 'buy'; // Default
                        }
                    }
                    
                    const price = trade.price || 0;
                    const quantity = trade.quantity || trade.amount || 0;
                    const total = price * quantity;
                    const time = trade.timestamp 
                        ? new Date(trade.timestamp * 1000).toLocaleTimeString() 
                        : new Date().toLocaleTimeString();
                    
                    const row = document.createElement('tr');
                    row.className = side.toLowerCase() === 'buy' ? 'text-success' : 'text-danger';
                    
                    row.innerHTML = `
                        <td class="text-end">${formatNumber(price)}</td>
                        <td class="text-end">${formatNumber(quantity, 4)}</td>
                        <td class="text-end">${formatNumber(total)}</td>
                        <td>${time}</td>
                    `;
                    
                    tradesTable.appendChild(row);
                } catch (err) {
                    console.error('Error rendering trade row:', err);
                }
            });
            
        } catch (err) {
            console.error('Error updating trades:', err);
        }
    }
    
    // Add a new trade to the list
    function addTrade(trade) {
        // Add to recent trades
        recentTrades.unshift(trade);
        
        // Limit to 100 trades
        if (recentTrades.length > 100) {
            recentTrades = recentTrades.slice(0, 100);
        }
        
        // Update trades display
        updateTrades();
    }
    
    // Cancel an order
    function cancelOrder(orderId) {
        if (!socket.connected) {
            showNotification('Error', 'Not connected to server', 'error');
            return;
        }
        
        socket.emit('cancel_order', { order_id: orderId });
        showNotification('Cancelling Order', 'Request sent to cancel order', 'info');
        
        // Optimistically update UI
        openOrders = openOrders.filter(order => {
            const id = order.order_id || order.id;
            return id !== orderId;
        });
        
        updateOpenOrders();
    }
    
    // Cancel all orders
    function cancelAllOrders() {
        if (!socket.connected) {
            showNotification('Error', 'Not connected to server', 'error');
            return;
        }
        
        socket.emit('cancel_all_orders');
        showNotification('Cancelling All Orders', 'Request sent to cancel all orders', 'info');
        
        // Optimistically update UI
        openOrders = [];
        updateOpenOrders();
    }
    
    // Show a notification toast
    function showNotification(title, message, type = 'info') {
        if (typeof showNotification === 'function' && typeof showNotification !== 'undefined') {
            // Use the global showNotification function if available
            window.showNotification(title, message, type);
            return;
        }
        
        // Fallback to console logging if notification function is not available
        const prefix = type === 'error' ? '❌ ERROR:' : 
                       type === 'success' ? '✅ SUCCESS:' : 
                       type === 'warning' ? '⚠️ WARNING:' : 'ℹ️ INFO:';
        
        console.log(`${prefix} ${title} - ${message}`);
    }
    
    // Setup event listeners
    function setupEventListeners() {
        console.log("Setting up event listeners...");
        
        // Theme toggle
        if (themeToggle) {
            themeToggle.addEventListener('click', function() {
                const body = document.body;
                if (body.classList.contains('light-theme')) {
                    body.classList.remove('light-theme');
                    themeToggle.classList.add('dark');
                    localStorage.setItem('theme', 'dark');
                } else {
                    body.classList.add('light-theme');
                    themeToggle.classList.remove('dark');
                    localStorage.setItem('theme', 'light');
                }
            });
        }
        
        // Precision selector
        if (precisionButtons) {
            precisionButtons.forEach(button => {
                button.addEventListener('click', function() {
                    precisionButtons.forEach(btn => btn.classList.remove('active'));
                    this.classList.add('active');
                    precision = parseInt(this.getAttribute('data-precision'), 10);
                    renderOrderbook();
                });
            });
        }
        
        // Auto generate orders toggle
        if (autoGenerateToggle) {
            autoGenerateToggle.addEventListener('change', function() {
                socket.emit('toggle_generator', { enabled: this.checked });
                showNotification(
                    'Auto Generate',
                    this.checked ? 'Order generator enabled' : 'Order generator disabled',
                    'info'
                );
            });
        }
        
        // Cancel all orders button
        if (cancelAllBtn) {
            cancelAllBtn.addEventListener('click', cancelAllOrders);
        }
        
        // Form submit handlers for limit, market, and stop-limit orders
        setupOrderForms();
    }
    
    // Apply saved theme
    function applyTheme() {
        console.log("Applying dark theme...");
        const savedTheme = localStorage.getItem('theme');
        
        if (savedTheme === 'light') {
            document.body.classList.add('light-theme');
            if (themeToggle) themeToggle.classList.remove('dark');
        } else {
            document.body.classList.remove('light-theme');
            if (themeToggle) themeToggle.classList.add('dark');
        }
        
        console.log("Theme applied successfully");
    }
    
    // Setup Order Form Functionality 
    function setupOrderForms() {
        // Tab handling for order types using Bootstrap's tab system
        const tabElements = document.querySelectorAll('.nav-tabs .nav-link');
        tabElements.forEach(tab => {
            tab.addEventListener('click', function(e) {
                // Let Bootstrap handle the tabs
                if (this.getAttribute('data-bs-toggle') === 'tab') {
                    return;
                }
                
                e.preventDefault();
                
                // Activate this tab
                tabElements.forEach(t => {
                    t.classList.remove('active');
                    t.setAttribute('aria-selected', 'false');
                });
                this.classList.add('active');
                this.setAttribute('aria-selected', 'true');
                
                // Show the corresponding panel
                const target = this.getAttribute('data-bs-target');
                const panels = document.querySelectorAll('.tab-pane');
                panels.forEach(panel => {
                    if (panel.id === target.substring(1)) {
                        panel.classList.add('show', 'active');
                    } else {
                        panel.classList.remove('show', 'active');
                    }
                });
            });
        });
        
        // Side button handlers (buy/sell)
        const sideButtons = document.querySelectorAll('.side-btn');
        sideButtons.forEach(button => {
            button.addEventListener('click', function() {
                const sideButtonsGroup = this.closest('.btn-group').querySelectorAll('.side-btn');
                const side = this.getAttribute('data-side');
                const form = this.closest('form');
                const submitButton = form.querySelector('button[type="submit"]');
                
                // Update button states
                sideButtonsGroup.forEach(btn => {
                    if (btn === this) {
                        if (side === 'buy') {
                            btn.classList.remove('btn-outline-success');
                            btn.classList.add('btn-success');
                            
                            // Update other button to outline variant
                            sideButtonsGroup.forEach(otherBtn => {
                                if (otherBtn !== btn) {
                                    otherBtn.classList.remove('btn-danger');
                                    otherBtn.classList.add('btn-outline-danger');
                                }
                            });
                            
                            // Update submit button
                            submitButton.classList.remove('btn-danger');
                            submitButton.classList.add('btn-success');
                            submitButton.textContent = 'Buy BTC';
                        } else {
                            btn.classList.remove('btn-outline-danger');
                            btn.classList.add('btn-danger');
                            
                            // Update other button to outline variant
                            sideButtonsGroup.forEach(otherBtn => {
                                if (otherBtn !== btn) {
                                    otherBtn.classList.remove('btn-success');
                                    otherBtn.classList.add('btn-outline-success');
                                }
                            });
                            
                            // Update submit button
                            submitButton.classList.remove('btn-success');
                            submitButton.classList.add('btn-danger');
                            submitButton.textContent = 'Sell BTC';
                        }
                    }
                });
            });
        });
        
        // Calculate total for limit orders
        const limitPriceInput = document.getElementById('limitPrice');
        const limitAmountInput = document.getElementById('limitAmount');
        const limitTotalInput = document.getElementById('limitTotal');
        
        function calculateLimitTotal() {
            if (!limitPriceInput || !limitAmountInput || !limitTotalInput) return;
            const price = parseFloat(limitPriceInput.value) || 0;
            const amount = parseFloat(limitAmountInput.value) || 0;
            limitTotalInput.value = (price * amount).toFixed(2);
        }
        
        if (limitPriceInput && limitAmountInput && limitTotalInput) {
            limitPriceInput.addEventListener('input', calculateLimitTotal);
            limitAmountInput.addEventListener('input', calculateLimitTotal);
        }
        
        // Calculate total for stop-limit orders
        const stopLimitPriceInput = document.getElementById('stopLimitPrice');
        const stopLimitAmountInput = document.getElementById('stopLimitAmount');
        const stopLimitTotalInput = document.getElementById('stopLimitTotal');
        
        function calculateStopLimitTotal() {
            if (!stopLimitPriceInput || !stopLimitAmountInput || !stopLimitTotalInput) return;
            const price = parseFloat(stopLimitPriceInput.value) || 0;
            const amount = parseFloat(stopLimitAmountInput.value) || 0;
            stopLimitTotalInput.value = (price * amount).toFixed(2);
        }
        
        if (stopLimitPriceInput && stopLimitAmountInput && stopLimitTotalInput) {
            stopLimitPriceInput.addEventListener('input', calculateStopLimitTotal);
            stopLimitAmountInput.addEventListener('input', calculateStopLimitTotal);
        }
        
        // Form submission handlers
        const limitOrderForm = document.getElementById('limit-order-form');
        if (limitOrderForm) {
            limitOrderForm.addEventListener('submit', function(e) {
                e.preventDefault();
                const activeButton = this.querySelector('.side-btn.btn-success, .side-btn.btn-danger');
                const side = activeButton ? activeButton.getAttribute('data-side') : 'buy';
                placeLimitOrder(
                    side,
                    parseFloat(limitPriceInput.value),
                    parseFloat(limitAmountInput.value)
                );
            });
        }
        
        const marketOrderForm = document.getElementById('market-order-form');
        if (marketOrderForm) {
            marketOrderForm.addEventListener('submit', function(e) {
                e.preventDefault();
                const activeButton = this.querySelector('.side-btn.btn-success, .side-btn.btn-danger');
                const side = activeButton ? activeButton.getAttribute('data-side') : 'buy';
                placeMarketOrder(
                    side,
                    parseFloat(document.getElementById('marketAmount').value)
                );
            });
        }
        
        const stopLimitOrderForm = document.getElementById('stoplimit-order-form');
        if (stopLimitOrderForm) {
            stopLimitOrderForm.addEventListener('submit', function(e) {
                e.preventDefault();
                const activeButton = this.querySelector('.side-btn.btn-success, .side-btn.btn-danger');
                const side = activeButton ? activeButton.getAttribute('data-side') : 'buy';
                placeStopLimitOrder(
                    side,
                    parseFloat(document.getElementById('stopPrice').value),
                    parseFloat(stopLimitPriceInput.value),
                    parseFloat(stopLimitAmountInput.value)
                );
            });
        }
    }
    
    // Place a limit order
    function placeLimitOrder(side, price, amount) {
        if (!socket.connected) {
            showNotification('Error', 'Not connected to server', 'error');
            return;
        }
        
        if (!price || !amount) {
            showNotification('Error', 'Please enter both price and amount', 'error');
            return;
        }
        
        const order = {
            type: 'limit',
            side: side,
            price: price,
            quantity: amount
        };
        
        console.log('Placing limit order:', order);
        socket.emit('place_order', order);
        
        // Clear form
        const priceInput = document.getElementById('limitPrice');
        const amountInput = document.getElementById('limitAmount');
        const totalInput = document.getElementById('limitTotal');
        
        if (priceInput) priceInput.value = '';
        if (amountInput) amountInput.value = '';
        if (totalInput) totalInput.value = '';
    }
    
    // Place a market order
    function placeMarketOrder(side, amount) {
        if (!socket.connected) {
            showNotification('Error', 'Not connected to server', 'error');
            return;
        }
        
        if (!amount) {
            showNotification('Error', 'Please enter an amount', 'error');
            return;
        }
        
        // Market orders need a price field to be valid, even though the price is determined by the matching engine
        // The server will use this as a placeholder and apply the appropriate price logic for market orders
        const order = {
            type: 'market',
            side: side,
            quantity: amount,
            price: side === 'buy' ? 999999.99 : 0.01 // Use a price that will cross the book
        };
        
        console.log('Placing market order:', order);
        socket.emit('place_order', order);
        
        // Clear form
        const amountInput = document.getElementById('marketAmount');
        if (amountInput) amountInput.value = '';
    }
    
    // Place a stop-limit order
    function placeStopLimitOrder(side, stopPrice, limitPrice, amount) {
        if (!socket.connected) {
            showNotification('Error', 'Not connected to server', 'error');
            return;
        }
        
        if (!stopPrice || !limitPrice || !amount) {
            showNotification('Error', 'Please fill all fields', 'error');
            return;
        }
        
        const order = {
            type: 'stop_limit',
            side: side,
            price: limitPrice,
            stop_price: stopPrice,
            quantity: amount
        };
        
        console.log('Placing stop-limit order:', order);
        socket.emit('place_order', order);
        
        // Clear form
        const stopPriceInput = document.getElementById('stopPrice');
        const limitPriceInput = document.getElementById('stopLimitPrice');
        const amountInput = document.getElementById('stopLimitAmount');
        const totalInput = document.getElementById('stopLimitTotal');
        
        if (stopPriceInput) stopPriceInput.value = '';
        if (limitPriceInput) limitPriceInput.value = '';
        if (amountInput) amountInput.value = '';
        if (totalInput) totalInput.value = '';
    }
    
    // Initialize
    function init() {
        console.log("DOM loaded. Initializing application...");
        
        // Apply theme
        applyTheme();
        
        // Setup socket connection
        setupSocketConnection();
        
        // Setup event listeners
        setupEventListeners();
        
        // Request initial data
        socket.emit('get_orderbook');
        socket.emit('get_trades');
        socket.emit('get_orders');
        socket.emit('get_generator_status');
        
        console.log("Application initialized successfully");
    }
    
    // Run initialization
    init();
}); 