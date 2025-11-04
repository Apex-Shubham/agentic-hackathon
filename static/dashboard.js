// Apex Trading Bot Dashboard - Main JavaScript

let performanceChart = null;
let refreshInterval = null;

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    initChart();
    loadAllData();
    
    // Refresh every 5 seconds
    refreshInterval = setInterval(loadAllData, 5000);
});

// Initialize performance chart
function initChart() {
    const ctx = document.getElementById('performanceChart');
    if (!ctx) return;
    
    performanceChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: 'Portfolio Value',
                data: [],
                borderColor: '#10b981',
                backgroundColor: 'rgba(16, 185, 129, 0.1)',
                borderWidth: 2,
                fill: true,
                tension: 0.4
            }, {
                label: 'Initial Capital',
                data: [],
                borderColor: '#6b7280',
                borderWidth: 1,
                borderDash: [5, 5],
                fill: false
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: true,
                    labels: {
                        color: '#cbd5e1'
                    }
                }
            },
            scales: {
                x: {
                    ticks: { color: '#cbd5e1' },
                    grid: { color: '#334155' }
                },
                y: {
                    ticks: { 
                        color: '#cbd5e1',
                        callback: function(value) {
                            return '$' + value.toLocaleString();
                        }
                    },
                    grid: { color: '#334155' }
                }
            }
        }
    });
}

// Load all data
async function loadAllData() {
    await Promise.all([
        loadPortfolio(),
        loadMetrics(),
        loadPositions(),
        loadTrades(),
        loadDecisions(),
        loadPerformance(),
        loadHealth(),
        loadRealizedPnL()
    ]);
}

// Load portfolio data
async function loadPortfolio() {
    try {
        const response = await fetch('/api/portfolio');
        const result = await response.json();
        
        if (result.status === 'success') {
            const data = result.data;
            
            // Store initial capital for chart
            if (!initialCapital) {
                initialCapital = data.initial_capital;
            }
            
            // Update portfolio metrics
            document.getElementById('portfolioValue').textContent = formatCurrency(data.total_value);
            document.getElementById('availableBalance').textContent = formatCurrency(data.available_balance);
            document.getElementById('openPositions').textContent = data.position_count || 0;
            
            const totalReturn = data.total_return;
            const returnEl = document.getElementById('totalReturn');
            returnEl.textContent = formatPercent(totalReturn);
            returnEl.className = 'metric-value' + (totalReturn >= 0 ? ' positive' : ' negative');
            
            document.getElementById('returnChange').textContent = 
                `Initial: ${formatCurrency(data.initial_capital)}`;
            document.getElementById('returnChange').className = 
                'metric-change' + (totalReturn >= 0 ? ' positive' : ' negative');
            
            const drawdown = data.drawdown_percent;
            document.getElementById('drawdown').textContent = formatPercent(drawdown);
            document.getElementById('drawdownIndicator').textContent = 
                drawdown > 20 ? '⚠️ High' : drawdown > 10 ? '⚠️ Moderate' : '✓ Safe';
            document.getElementById('drawdownIndicator').className = 
                'metric-change' + (drawdown > 20 ? ' negative' : drawdown > 10 ? '' : ' positive');
            
            document.getElementById('unrealizedPnL').textContent = 
                `PnL: ${formatCurrency(data.unrealized_pnl)}`;
            document.getElementById('unrealizedPnL').className = 
                'metric-change' + (data.unrealized_pnl >= 0 ? ' positive' : ' negative');
            
            // Circuit breaker alert
            const alertBanner = document.getElementById('circuitBreakerAlert');
            if (data.circuit_breaker_level) {
                alertBanner.style.display = 'flex';
                document.getElementById('circuitBreakerText').textContent = 
                    `Circuit Breaker Active: ${data.circuit_breaker_level}`;
            } else {
                alertBanner.style.display = 'none';
            }
        }
    } catch (error) {
        console.error('Error loading portfolio:', error);
    }
}

// Load metrics
async function loadMetrics() {
    try {
        const response = await fetch('/api/metrics');
        const result = await response.json();
        
        if (result.status === 'success') {
            const data = result.data;
            
            document.getElementById('totalTrades').textContent = data.total_trades || 0;
            document.getElementById('winRate').textContent = formatPercent(data.win_rate || 0);
            document.getElementById('sharpeRatio').textContent = (data.sharpe_ratio || 0).toFixed(2);
            document.getElementById('profitFactor').textContent = (data.profit_factor || 0).toFixed(2);
            document.getElementById('avgWin').textContent = formatCurrency(data.avg_win || 0);
            // Open positions count will be updated from portfolio API
        }
    } catch (error) {
        console.error('Error loading metrics:', error);
    }
}

// Load positions
async function loadPositions() {
    try {
        const response = await fetch('/api/portfolio');
        const result = await response.json();
        
        if (result.status === 'success') {
            const positions = result.data.positions || [];
            const tbody = document.getElementById('positionsBody');
            
            if (positions.length === 0) {
                tbody.innerHTML = '<tr><td colspan="8" class="empty-state">No open positions</td></tr>';
                return;
            }
            
            tbody.innerHTML = positions.map(pos => `
                <tr>
                    <td>${pos.symbol}</td>
                    <td><span class="badge ${pos.side?.toLowerCase() || 'hold'}">${pos.side || 'N/A'}</span></td>
                    <td>${formatCurrency(pos.entry_price || 0)}</td>
                    <td>${formatCurrency(pos.current_price || pos.entry_price || 0)}</td>
                    <td>${formatNumber(pos.quantity || 0)}</td>
                    <td>${pos.leverage || 1}x</td>
                    <td class="${(pos.pnl || 0) >= 0 ? 'positive' : 'negative'}">
                        ${formatCurrency(pos.pnl || 0)}
                    </td>
                    <td class="${(pos.pnl_percent || 0) >= 0 ? 'positive' : 'negative'}">
                        ${formatPercent(pos.pnl_percent || 0)}
                    </td>
                </tr>
            `).join('');
        }
    } catch (error) {
        console.error('Error loading positions:', error);
    }
}

// Load recent trades
async function loadTrades() {
    try {
        const response = await fetch('/api/trades?limit=20');
        const result = await response.json();
        
        if (result.status === 'success') {
            const trades = result.data || [];
            const tbody = document.getElementById('tradesBody');
            
            if (trades.length === 0) {
                tbody.innerHTML = '<tr><td colspan="9" class="empty-state">No trades yet</td></tr>';
                return;
            }
            
            tbody.innerHTML = trades.map(trade => `
                <tr>
                    <td>${formatTime(trade.timestamp)}</td>
                    <td>${trade.symbol || 'N/A'}</td>
                    <td><span class="badge ${trade.side?.toLowerCase() || 'hold'}">${trade.side || 'N/A'}</span></td>
                    <td>${formatCurrency(trade.entry_price || 0)}</td>
                    <td>${formatCurrency(trade.exit_price || trade.entry_price || 0)}</td>
                    <td>${trade.leverage || 1}x</td>
                    <td class="${(trade.pnl || 0) >= 0 ? 'positive' : 'negative'}">
                        ${formatCurrency(trade.pnl || 0)}
                    </td>
                    <td class="${(trade.pnl_percent || 0) >= 0 ? 'positive' : 'negative'}">
                        ${formatPercent(trade.pnl_percent || 0)}
                    </td>
                    <td>${trade.strategy || 'unknown'}</td>
                </tr>
            `).join('');
        }
    } catch (error) {
        console.error('Error loading trades:', error);
    }
}

// Load recent decisions
async function loadDecisions() {
    try {
        const response = await fetch('/api/decisions?limit=20');
        const result = await response.json();
        
        if (result.status === 'success') {
            const decisions = result.data || [];
            const tbody = document.getElementById('decisionsBody');
            
            if (decisions.length === 0) {
                tbody.innerHTML = '<tr><td colspan="8" class="empty-state">No decisions yet</td></tr>';
                return;
            }
            
            tbody.innerHTML = decisions.map(dec => `
                <tr>
                    <td>${formatTime(dec.timestamp)}</td>
                    <td>${dec.asset || 'N/A'}</td>
                    <td><span class="badge ${dec.action?.toLowerCase() || 'hold'}">${dec.action || 'HOLD'}</span></td>
                    <td>${(dec.confidence || 0).toFixed(0)}%</td>
                    <td>${(dec.position_size_percent || 0).toFixed(1)}%</td>
                    <td>${dec.leverage || 1}x</td>
                    <td title="${dec.entry_reason || ''}">${truncate(dec.entry_reason || '', 50)}</td>
                    <td>${dec.market_regime || 'UNKNOWN'}</td>
                </tr>
            `).join('');
        }
    } catch (error) {
        console.error('Error loading decisions:', error);
    }
}

// Load performance data for chart
let initialCapital = null;

async function loadPerformance() {
    try {
        // Get initial capital from portfolio API
        if (!initialCapital) {
            const portfolioResponse = await fetch('/api/portfolio');
            const portfolioResult = await portfolioResponse.json();
            if (portfolioResult.status === 'success') {
                initialCapital = portfolioResult.data.initial_capital;
            }
        }
        
        const response = await fetch('/api/performance?hours=24');
        const result = await response.json();
        
        if (result.status === 'success' && performanceChart) {
            const data = result.data || [];
            
            if (data.length > 0 && initialCapital) {
                const labels = data.map(d => formatTimeShort(d.timestamp));
                const values = data.map(d => d.portfolio_value || 0);
                const initialLine = data.map(() => initialCapital);
                
                performanceChart.data.labels = labels;
                performanceChart.data.datasets[0].data = values;
                performanceChart.data.datasets[1].data = initialLine;
                performanceChart.update('none');
            }
        }
    } catch (error) {
        console.error('Error loading performance:', error);
    }
}

// Load health status
async function loadHealth() {
    try {
        const response = await fetch('/api/health');
        const result = await response.json();
        
        if (result.status === 'success') {
            const data = result.data;
            const statusDot = document.querySelector('.status-dot');
            const statusText = document.getElementById('statusText');
            
            if (data.overall) {
                statusDot.classList.add('active');
                statusText.textContent = 'Bot Running';
            } else {
                statusDot.classList.remove('active');
                statusText.textContent = 'Bot Issues Detected';
            }
        }
    } catch (error) {
        console.error('Error loading health:', error);
    }
}

// Load realized PnL
async function loadRealizedPnL() {
    try {
        const response = await fetch('/api/realized_pnl');
        const result = await response.json();
        if (result.status === 'success' && result.data) {
            const value = result.data.realized_pnl;
            const el = document.getElementById('realizedPnL');
            if (el) {
                el.textContent = formatCurrency(value);
                el.className = 'metric-value' + (value >= 0 ? ' positive' : ' negative');
            }
        }
    } catch (error) {
        console.error('Error loading realized PnL:', error);
    }
}

// Utility functions
function formatCurrency(value) {
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD',
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    }).format(value || 0);
}

function formatPercent(value) {
    const sign = value >= 0 ? '+' : '';
    return `${sign}${(value || 0).toFixed(2)}%`;
}

function formatNumber(value) {
    return new Intl.NumberFormat('en-US', {
        minimumFractionDigits: 2,
        maximumFractionDigits: 6
    }).format(value || 0);
}

function formatTime(isoString) {
    if (!isoString) return 'N/A';
    const date = new Date(isoString);
    return date.toLocaleString('en-US', {
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

function formatTimeShort(isoString) {
    if (!isoString) return '';
    const date = new Date(isoString);
    return date.toLocaleTimeString('en-US', {
        hour: '2-digit',
        minute: '2-digit'
    });
}

function truncate(str, length) {
    if (!str) return '';
    return str.length > length ? str.substring(0, length) + '...' : str;
}

