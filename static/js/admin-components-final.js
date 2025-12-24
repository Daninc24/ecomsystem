/**
 * Final Admin Frontend Components
 * Analytics, Order Management, and System Monitoring components
 */

// ==================== ANALYTICS PANEL COMPONENT ====================

class AnalyticsPanelComponent extends BaseAdminComponent {
    constructor() {
        super('analytics-panel-container');
        this.charts = new Map();
        this.metrics = {};
        this.dateRange = '7d';
    }

    render() {
        if (!this.container) return;

        this.container.innerHTML = `
            <div class="analytics-panel">
                <div class="analytics-header">
                    <h2>Analytics Dashboard</h2>
                    <div class="analytics-controls">
                        <select class="form-control" id="analytics-date-range">
                            <option value="1d">Last 24 Hours</option>
                            <option value="7d" selected>Last 7 Days</option>
                            <option value="30d">Last 30 Days</option>
                            <option value="90d">Last 90 Days</option>
                            <option value="1y">Last Year</option>
                        </select>
                        <button class="btn btn-secondary" data-action="exportReport">
                            <i class="icon-download"></i> Export Report
                        </button>
                        <button class="btn btn-primary" data-action="refreshAnalytics">
                            <i class="icon-refresh"></i> Refresh
                        </button>
                    </div>
                </div>
                
                <div class="analytics-summary">
                    <div class="summary-cards" id="analytics-summary-cards">
                        <!-- Summary cards will be populated here -->
                    </div>
                </div>
                
                <div class="analytics-charts">
                    <div class="chart-grid">
                        <div class="chart-container">
                            <h3>Revenue Trends</h3>
                            <canvas id="revenue-chart"></canvas>
                        </div>
                        
                        <div class="chart-container">
                            <h3>User Growth</h3>
                            <canvas id="user-growth-chart"></canvas>
                        </div>
                        
                        <div class="chart-container">
                            <h3>Order Volume</h3>
                            <canvas id="order-volume-chart"></canvas>
                        </div>
                        
                        <div class="chart-container">
                            <h3>Top Products</h3>
                            <canvas id="top-products-chart"></canvas>
                        </div>
                    </div>
                </div>
                
                <div class="analytics-tables">
                    <div class="table-grid">
                        <div class="analytics-table-container">
                            <h3>Recent Transactions</h3>
                            <div class="table-wrapper" id="recent-transactions-table">
                                <!-- Table will be populated here -->
                            </div>
                        </div>
                        
                        <div class="analytics-table-container">
                            <h3>Top Customers</h3>
                            <div class="table-wrapper" id="top-customers-table">
                                <!-- Table will be populated here -->
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;

        this.loadAnalyticsData();
    }

    setupEventListeners() {
        if (!this.container) return;

        // Date range change
        const dateRangeSelect = document.getElementById('analytics-date-range');
        if (dateRangeSelect) {
            dateRangeSelect.addEventListener('change', (e) => {
                this.dateRange = e.target.value;
                this.loadAnalyticsData();
            });
        }

        // Action buttons
        this.container.addEventListener('click', (e) => {
            const action = e.target.getAttribute('data-action');
            
            switch (action) {
                case 'refreshAnalytics':
                    this.loadAnalyticsData();
                    break;
                case 'exportReport':
                    this.exportReport();
                    break;
            }
        });
    }

    async loadAnalyticsData() {
        try {
            const data = await this.apiCall(`/api/admin/analytics/dashboard?range=${this.dateRange}`);
            if (data.success) {
                this.metrics = data.data;
                this.renderSummaryCards();
                this.renderCharts();
                this.renderTables();
            }
        } catch (error) {
            console.error('Failed to load analytics data:', error);
        }
    }

    renderSummaryCards() {
        const container = document.getElementById('analytics-summary-cards');
        if (!container || !this.metrics.summary) return;

        const cardsHTML = Object.entries(this.metrics.summary).map(([key, data]) => `
            <div class="analytics-summary-card">
                <div class="card-icon">
                    <i class="icon-${this.getMetricIcon(key)}"></i>
                </div>
                <div class="card-content">
                    <div class="card-value">${this.formatMetricValue(key, data.value)}</div>
                    <div class="card-label">${this.getMetricLabel(key)}</div>
                    <div class="card-change ${data.change >= 0 ? 'positive' : 'negative'}">
                        <i class="icon-${data.change >= 0 ? 'arrow-up' : 'arrow-down'}"></i>
                        ${Math.abs(data.change)}% vs previous period
                    </div>
                </div>
            </div>
        `).join('');

        container.innerHTML = cardsHTML;
    }

    renderCharts() {
        if (typeof Chart === 'undefined') {
            console.warn('Chart.js not loaded');
            return;
        }

        this.renderRevenueChart();
        this.renderUserGrowthChart();
        this.renderOrderVolumeChart();
        this.renderTopProductsChart();
    }

    renderRevenueChart() {
        const canvas = document.getElementById('revenue-chart');
        if (!canvas || !this.metrics.revenue) return;

        if (this.charts.has('revenue')) {
            this.charts.get('revenue').destroy();
        }

        const chart = new Chart(canvas, {
            type: 'line',
            data: {
                labels: this.metrics.revenue.labels,
                datasets: [{
                    label: 'Revenue',
                    data: this.metrics.revenue.data,
                    borderColor: '#4299e1',
                    backgroundColor: 'rgba(66, 153, 225, 0.1)',
                    tension: 0.4,
                    fill: true
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            callback: function(value) {
                                return '$' + value.toLocaleString();
                            }
                        }
                    }
                }
            }
        });

        this.charts.set('revenue', chart);
    }

    renderUserGrowthChart() {
        const canvas = document.getElementById('user-growth-chart');
        if (!canvas || !this.metrics.userGrowth) return;

        if (this.charts.has('userGrowth')) {
            this.charts.get('userGrowth').destroy();
        }

        const chart = new Chart(canvas, {
            type: 'bar',
            data: {
                labels: this.metrics.userGrowth.labels,
                datasets: [{
                    label: 'New Users',
                    data: this.metrics.userGrowth.data,
                    backgroundColor: '#48bb78',
                    borderRadius: 4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true
                    }
                }
            }
        });

        this.charts.set('userGrowth', chart);
    }

    renderOrderVolumeChart() {
        const canvas = document.getElementById('order-volume-chart');
        if (!canvas || !this.metrics.orderVolume) return;

        if (this.charts.has('orderVolume')) {
            this.charts.get('orderVolume').destroy();
        }

        const chart = new Chart(canvas, {
            type: 'line',
            data: {
                labels: this.metrics.orderVolume.labels,
                datasets: [{
                    label: 'Orders',
                    data: this.metrics.orderVolume.data,
                    borderColor: '#ed8936',
                    backgroundColor: 'rgba(237, 137, 54, 0.1)',
                    tension: 0.4,
                    fill: true
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true
                    }
                }
            }
        });

        this.charts.set('orderVolume', chart);
    }

    renderTopProductsChart() {
        const canvas = document.getElementById('top-products-chart');
        if (!canvas || !this.metrics.topProducts) return;

        if (this.charts.has('topProducts')) {
            this.charts.get('topProducts').destroy();
        }

        const chart = new Chart(canvas, {
            type: 'doughnut',
            data: {
                labels: this.metrics.topProducts.labels,
                datasets: [{
                    data: this.metrics.topProducts.data,
                    backgroundColor: [
                        '#4299e1',
                        '#48bb78',
                        '#ed8936',
                        '#f56565',
                        '#9f7aea'
                    ]
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom'
                    }
                }
            }
        });

        this.charts.set('topProducts', chart);
    }

    renderTables() {
        this.renderRecentTransactionsTable();
        this.renderTopCustomersTable();
    }

    renderRecentTransactionsTable() {
        const container = document.getElementById('recent-transactions-table');
        if (!container || !this.metrics.recentTransactions) return;

        const tableHTML = `
            <table class="analytics-table">
                <thead>
                    <tr>
                        <th>Order ID</th>
                        <th>Customer</th>
                        <th>Amount</th>
                        <th>Status</th>
                        <th>Date</th>
                    </tr>
                </thead>
                <tbody>
                    ${this.metrics.recentTransactions.map(transaction => `
                        <tr>
                            <td>#${transaction.id}</td>
                            <td>${transaction.customer}</td>
                            <td>$${transaction.amount.toFixed(2)}</td>
                            <td><span class="status-badge status-${transaction.status}">${transaction.status}</span></td>
                            <td>${this.formatDate(transaction.date)}</td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>
        `;

        container.innerHTML = tableHTML;
    }

    renderTopCustomersTable() {
        const container = document.getElementById('top-customers-table');
        if (!container || !this.metrics.topCustomers) return;

        const tableHTML = `
            <table class="analytics-table">
                <thead>
                    <tr>
                        <th>Customer</th>
                        <th>Orders</th>
                        <th>Total Spent</th>
                        <th>Last Order</th>
                    </tr>
                </thead>
                <tbody>
                    ${this.metrics.topCustomers.map(customer => `
                        <tr>
                            <td>
                                <div class="customer-info">
                                    <div class="customer-name">${customer.name}</div>
                                    <div class="customer-email">${customer.email}</div>
                                </div>
                            </td>
                            <td>${customer.orderCount}</td>
                            <td>$${customer.totalSpent.toFixed(2)}</td>
                            <td>${this.formatDate(customer.lastOrder)}</td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>
        `;

        container.innerHTML = tableHTML;
    }

    updateCharts(newData) {
        this.metrics = { ...this.metrics, ...newData };
        this.renderSummaryCards();
        this.renderCharts();
        this.renderTables();
    }

    async exportReport() {
        try {
            const response = await fetch(`/api/admin/analytics/export?range=${this.dateRange}`, {
                method: 'GET'
            });
            
            if (response.ok) {
                const blob = await response.blob();
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `analytics-report-${this.dateRange}-${new Date().toISOString().split('T')[0]}.pdf`;
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                window.URL.revokeObjectURL(url);
                
                this.showNotification('Report exported successfully', 'success');
            }
        } catch (error) {
            console.error('Failed to export report:', error);
            this.showNotification('Failed to export report', 'error');
        }
    }

    getMetricIcon(key) {
        const icons = {
            revenue: 'dollar-sign',
            orders: 'shopping-cart',
            users: 'users',
            conversion: 'trending-up',
            avgOrder: 'bar-chart'
        };
        return icons[key] || 'bar-chart';
    }

    getMetricLabel(key) {
        const labels = {
            revenue: 'Total Revenue',
            orders: 'Total Orders',
            users: 'New Users',
            conversion: 'Conversion Rate',
            avgOrder: 'Avg Order Value'
        };
        return labels[key] || key.charAt(0).toUpperCase() + key.slice(1);
    }

    formatMetricValue(key, value) {
        if (key === 'revenue' || key === 'avgOrder') {
            return new Intl.NumberFormat('en-US', {
                style: 'currency',
                currency: 'USD'
            }).format(value);
        } else if (key === 'conversion') {
            return value.toFixed(1) + '%';
        }
        return new Intl.NumberFormat('en-US').format(value);
    }

    formatDate(dateString) {
        return new Date(dateString).toLocaleDateString();
    }

    showNotification(message, type) {
        console.log(`${type.toUpperCase()}: ${message}`);
    }

    destroy() {
        super.destroy();
        this.charts.forEach(chart => chart.destroy());
        this.charts.clear();
    }
}

// ==================== ORDER MANAGER COMPONENT ====================

class OrderManagerComponent extends BaseAdminComponent {
    constructor() {
        super('order-management-container');
        this.orders = [];
        this.selectedOrders = new Set();
        this.filters = {};
    }

    render() {
        if (!this.container) return;

        this.container.innerHTML = `
            <div class="order-manager">
                <div class="order-manager-header">
                    <h2>Order Management</h2>
                    <div class="order-manager-actions">
                        <button class="btn btn-secondary" data-action="bulkUpdate" id="bulk-update-btn" disabled>
                            <i class="icon-edit"></i> Bulk Update (<span id="selected-order-count">0</span>)
                        </button>
                        <button class="btn btn-secondary" data-action="exportOrders">
                            <i class="icon-download"></i> Export
                        </button>
                        <button class="btn btn-primary" data-action="refreshOrders">
                            <i class="icon-refresh"></i> Refresh
                        </button>
                    </div>
                </div>
                
                <div class="order-manager-filters">
                    <div class="filter-group">
                        <input type="text" class="form-control" placeholder="Search orders..." id="order-search">
                        <select class="form-control" id="order-status-filter">
                            <option value="">All Status</option>
                            <option value="pending">Pending</option>
                            <option value="processing">Processing</option>
                            <option value="shipped">Shipped</option>
                            <option value="delivered">Delivered</option>
                            <option value="cancelled">Cancelled</option>
                            <option value="refunded">Refunded</option>
                        </select>
                        <select class="form-control" id="order-date-filter">
                            <option value="">All Time</option>
                            <option value="today">Today</option>
                            <option value="week">This Week</option>
                            <option value="month">This Month</option>
                            <option value="quarter">This Quarter</option>
                        </select>
                        <input type="number" class="form-control" placeholder="Min Amount" id="min-amount-filter">
                        <input type="number" class="form-control" placeholder="Max Amount" id="max-amount-filter">
                    </div>
                </div>
                
                <div class="order-manager-content">
                    <div class="order-list" id="order-list">
                        <!-- Orders will be populated here -->
                    </div>
                </div>
                
                <div class="order-pagination" id="order-pagination">
                    <!-- Pagination will be populated here -->
                </div>
            </div>
        `;

        this.loadOrders();
    }

    setupEventListeners() {
        if (!this.container) return;

        // Search functionality
        const searchInput = document.getElementById('order-search');
        if (searchInput) {
            searchInput.addEventListener('input', this.debounce(() => {
                this.applyFilters();
            }, 300));
        }

        // Filter functionality
        const filters = ['order-status-filter', 'order-date-filter', 'min-amount-filter', 'max-amount-filter'];
        filters.forEach(filterId => {
            const filter = document.getElementById(filterId);
            if (filter) {
                filter.addEventListener('change', () => this.applyFilters());
            }
        });

        // Order selection
        this.container.addEventListener('change', (e) => {
            if (e.target.classList.contains('order-select')) {
                const orderId = e.target.getAttribute('data-order-id');
                if (e.target.checked) {
                    this.selectedOrders.add(orderId);
                } else {
                    this.selectedOrders.delete(orderId);
                }
                this.updateBulkUpdateButton();
            }
        });

        // Action buttons
        this.container.addEventListener('click', (e) => {
            const action = e.target.getAttribute('data-action');
            const orderId = e.target.getAttribute('data-order-id');

            switch (action) {
                case 'viewOrder':
                    this.viewOrderDetails(orderId);
                    break;
                case 'updateStatus':
                    this.updateOrderStatus(orderId);
                    break;
                case 'processRefund':
                    this.processRefund(orderId);
                    break;
                case 'printLabel':
                    this.printShippingLabel(orderId);
                    break;
                case 'bulkUpdate':
                    this.openBulkUpdateModal();
                    break;
                case 'exportOrders':
                    this.exportOrders();
                    break;
                case 'refreshOrders':
                    this.loadOrders();
                    break;
            }
        });
    }

    async loadOrders() {
        try {
            const data = await this.apiCall('/api/admin/orders');
            if (data.success) {
                this.orders = data.data.orders;
                this.renderOrders();
                this.renderPagination(data.data.pagination);
            }
        } catch (error) {
            console.error('Failed to load orders:', error);
        }
    }

    renderOrders() {
        const orderList = document.getElementById('order-list');
        if (!orderList) return;

        if (this.orders.length === 0) {
            orderList.innerHTML = '<div class="empty-state">No orders found</div>';
            return;
        }

        const ordersHTML = this.orders.map(order => `
            <div class="order-item" data-order-id="${order.id}">
                <div class="order-checkbox">
                    <input type="checkbox" class="order-select" data-order-id="${order.id}">
                </div>
                
                <div class="order-info">
                    <div class="order-header">
                        <div class="order-number">#${order.order_number}</div>
                        <div class="order-date">${this.formatDate(order.created_at)}</div>
                        <div class="order-status">
                            <span class="status-badge status-${order.status}">${order.status}</span>
                        </div>
                    </div>
                    
                    <div class="order-details">
                        <div class="order-customer">
                            <strong>${order.customer_name}</strong>
                            <span class="customer-email">${order.customer_email}</span>
                        </div>
                        
                        <div class="order-items">
                            ${order.items.slice(0, 3).map(item => `
                                <span class="order-item-name">${item.name} (${item.quantity})</span>
                            `).join(', ')}
                            ${order.items.length > 3 ? `<span class="more-items">+${order.items.length - 3} more</span>` : ''}
                        </div>
                        
                        <div class="order-shipping">
                            <div class="shipping-address">
                                <i class="icon-map-pin"></i>
                                ${order.shipping_address.city}, ${order.shipping_address.state}
                            </div>
                            ${order.tracking_number ? `
                                <div class="tracking-number">
                                    <i class="icon-truck"></i>
                                    Tracking: ${order.tracking_number}
                                </div>
                            ` : ''}
                        </div>
                    </div>
                </div>
                
                <div class="order-amount">
                    <div class="order-total">$${order.total_amount.toFixed(2)}</div>
                    <div class="payment-method">${order.payment_method}</div>
                </div>
                
                <div class="order-actions">
                    <button class="btn btn-sm btn-secondary" data-action="viewOrder" data-order-id="${order.id}">
                        <i class="icon-eye"></i> View
                    </button>
                    <button class="btn btn-sm btn-primary" data-action="updateStatus" data-order-id="${order.id}">
                        <i class="icon-edit"></i> Update
                    </button>
                    ${order.status === 'delivered' || order.status === 'cancelled' ? `
                        <button class="btn btn-sm btn-warning" data-action="processRefund" data-order-id="${order.id}">
                            <i class="icon-dollar-sign"></i> Refund
                        </button>
                    ` : ''}
                    ${order.status === 'processing' || order.status === 'shipped' ? `
                        <button class="btn btn-sm btn-success" data-action="printLabel" data-order-id="${order.id}">
                            <i class="icon-printer"></i> Label
                        </button>
                    ` : ''}
                </div>
            </div>
        `).join('');

        orderList.innerHTML = ordersHTML;
    }

    renderPagination(pagination) {
        const paginationContainer = document.getElementById('order-pagination');
        if (!paginationContainer || !pagination) return;

        const { current_page, total_pages, total_items } = pagination;
        
        let paginationHTML = `
            <div class="pagination-info">
                Showing ${((current_page - 1) * 20) + 1}-${Math.min(current_page * 20, total_items)} of ${total_items} orders
            </div>
            <div class="pagination-controls">
        `;

        if (current_page > 1) {
            paginationHTML += `
                <button class="btn btn-sm btn-secondary" data-page="${current_page - 1}">
                    <i class="icon-chevron-left"></i> Previous
                </button>
            `;
        }

        // Page numbers
        const startPage = Math.max(1, current_page - 2);
        const endPage = Math.min(total_pages, current_page + 2);

        for (let i = startPage; i <= endPage; i++) {
            paginationHTML += `
                <button class="btn btn-sm ${i === current_page ? 'btn-primary' : 'btn-secondary'}" data-page="${i}">
                    ${i}
                </button>
            `;
        }

        if (current_page < total_pages) {
            paginationHTML += `
                <button class="btn btn-sm btn-secondary" data-page="${current_page + 1}">
                    Next <i class="icon-chevron-right"></i>
                </button>
            `;
        }

        paginationHTML += '</div>';
        paginationContainer.innerHTML = paginationHTML;

        // Add pagination event listeners
        paginationContainer.addEventListener('click', (e) => {
            const page = e.target.getAttribute('data-page');
            if (page) {
                this.loadOrders(page);
            }
        });
    }

    updateBulkUpdateButton() {
        const bulkUpdateBtn = document.getElementById('bulk-update-btn');
        const selectedCount = document.getElementById('selected-order-count');
        
        if (bulkUpdateBtn && selectedCount) {
            const count = this.selectedOrders.size;
            selectedCount.textContent = count;
            bulkUpdateBtn.disabled = count === 0;
        }
    }

    async viewOrderDetails(orderId) {
        try {
            const data = await this.apiCall(`/api/admin/orders/${orderId}`);
            if (data.success) {
                this.openOrderDetailsModal(data.data.order);
            }
        } catch (error) {
            console.error('Failed to load order details:', error);
        }
    }

    openOrderDetailsModal(order) {
        // Create and show order details modal
        console.log('Opening order details modal for:', order);
    }

    async updateOrderStatus(orderId) {
        // Open status update modal
        console.log('Opening status update modal for:', orderId);
    }

    async processRefund(orderId) {
        if (!confirm('Are you sure you want to process a refund for this order?')) return;

        try {
            const data = await this.apiCall(`/api/admin/orders/${orderId}/refund`, {
                method: 'POST'
            });
            
            if (data.success) {
                this.loadOrders();
                this.showNotification('Refund processed successfully', 'success');
            }
        } catch (error) {
            console.error('Failed to process refund:', error);
            this.showNotification('Failed to process refund', 'error');
        }
    }

    async printShippingLabel(orderId) {
        try {
            const response = await fetch(`/api/admin/orders/${orderId}/shipping-label`, {
                method: 'GET'
            });
            
            if (response.ok) {
                const blob = await response.blob();
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `shipping-label-${orderId}.pdf`;
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                window.URL.revokeObjectURL(url);
            }
        } catch (error) {
            console.error('Failed to print shipping label:', error);
            this.showNotification('Failed to print shipping label', 'error');
        }
    }

    applyFilters() {
        // Implementation for filtering orders
        console.log('Applying order filters');
    }

    formatDate(dateString) {
        return new Date(dateString).toLocaleDateString();
    }

    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }

    showNotification(message, type) {
        console.log(`${type.toUpperCase()}: ${message}`);
    }
}

// ==================== SYSTEM MONITOR COMPONENT ====================

class SystemMonitorComponent extends BaseAdminComponent {
    constructor() {
        super('system-monitor-container');
        this.systemStatus = {};
        this.alerts = [];
        this.updateInterval = null;
        this.cpuChart = null;
        this.memoryChart = null;
        this.diskChart = null;
        this.networkChart = null;
    }

    render() {
        if (!this.container) return;

        this.container.innerHTML = `
            <div class="system-monitor">
                <div class="system-monitor-header">
                    <h2>System Monitoring</h2>
                    <div class="system-monitor-actions">
                        <button class="btn btn-secondary" data-action="clearAlerts">
                            <i class="icon-x"></i> Clear Alerts
                        </button>
                        <button class="btn btn-primary" data-action="refreshStatus">
                            <i class="icon-refresh"></i> Refresh
                        </button>
                    </div>
                </div>
                
                <div class="system-status-overview">
                    <div class="status-cards" id="system-status-cards">
                        <!-- Status cards will be populated here -->
                    </div>
                </div>
                
                <div class="system-alerts">
                    <h3>System Alerts</h3>
                    <div class="alerts-list" id="system-alerts-list">
                        <!-- Alerts will be populated here -->
                    </div>
                </div>
                
                <div class="system-metrics">
                    <div class="metrics-grid">
                        <div class="metric-chart-container">
                            <h3>CPU Usage</h3>
                            <canvas id="cpu-usage-chart"></canvas>
                        </div>
                        
                        <div class="metric-chart-container">
                            <h3>Memory Usage</h3>
                            <canvas id="memory-usage-chart"></canvas>
                        </div>
                        
                        <div class="metric-chart-container">
                            <h3>Disk Usage</h3>
                            <canvas id="disk-usage-chart"></canvas>
                        </div>
                        
                        <div class="metric-chart-container">
                            <h3>Network Traffic</h3>
                            <canvas id="network-traffic-chart"></canvas>
                        </div>
                    </div>
                </div>
                
                <div class="system-logs">
                    <h3>Recent System Logs</h3>
                    <div class="logs-container" id="system-logs-container">
                        <!-- Logs will be populated here -->
                    </div>
                </div>
            </div>
        `;

        this.loadSystemStatus();
        this.startRealTimeUpdates();
    }

    setupEventListeners() {
        if (!this.container) return;

        this.container.addEventListener('click', (e) => {
            const action = e.target.getAttribute('data-action');
            
            switch (action) {
                case 'refreshStatus':
                    this.loadSystemStatus();
                    break;
                case 'clearAlerts':
                    this.clearAlerts();
                    break;
            }
        });
    }

    async loadSystemStatus() {
        try {
            const data = await this.apiCall('/api/admin/system/status');
            if (data.success) {
                this.systemStatus = data.data.status;
                this.alerts = data.data.alerts || [];
                this.renderStatusCards();
                this.renderAlerts();
                this.renderMetricCharts();
                this.renderSystemLogs(data.data.logs || []);
            }
        } catch (error) {
            console.error('Failed to load system status:', error);
        }
    }

    renderStatusCards() {
        const container = document.getElementById('system-status-cards');
        if (!container) return;

        const services = this.systemStatus.services || {};
        const cardsHTML = Object.entries(services).map(([service, status]) => `
            <div class="system-status-card status-${status.status}">
                <div class="status-icon">
                    <i class="icon-${this.getServiceIcon(service)}"></i>
                </div>
                <div class="status-content">
                    <div class="status-name">${this.formatServiceName(service)}</div>
                    <div class="status-value">${status.status.toUpperCase()}</div>
                    <div class="status-details">
                        ${status.uptime ? `Uptime: ${status.uptime}` : ''}
                        ${status.responseTime ? `Response: ${status.responseTime}ms` : ''}
                    </div>
                </div>
            </div>
        `).join('');

        container.innerHTML = cardsHTML;
    }

    renderAlerts() {
        const container = document.getElementById('system-alerts-list');
        if (!container) return;

        if (this.alerts.length === 0) {
            container.innerHTML = '<div class="no-alerts">No active alerts</div>';
            return;
        }

        const alertsHTML = this.alerts.map(alert => `
            <div class="system-alert alert-${alert.severity}">
                <div class="alert-icon">
                    <i class="icon-${this.getAlertIcon(alert.severity)}"></i>
                </div>
                <div class="alert-content">
                    <div class="alert-title">${alert.title}</div>
                    <div class="alert-message">${alert.message}</div>
                    <div class="alert-time">${this.formatDate(alert.timestamp)}</div>
                </div>
                <div class="alert-actions">
                    <button class="btn btn-sm btn-secondary" data-action="dismissAlert" data-alert-id="${alert.id}">
                        Dismiss
                    </button>
                </div>
            </div>
        `).join('');

        container.innerHTML = alertsHTML;
    }

    renderMetricCharts() {
        if (typeof Chart === 'undefined') return;

        this.renderCPUChart();
        this.renderMemoryChart();
        this.renderDiskChart();
        this.renderNetworkChart();
    }

    renderCPUChart() {
        const canvas = document.getElementById('cpu-usage-chart');
        if (!canvas || !this.systemStatus.metrics?.cpu) return;

        // Destroy existing chart if it exists
        if (this.cpuChart) {
            this.cpuChart.destroy();
        }

        this.cpuChart = new Chart(canvas, {
            type: 'line',
            data: {
                labels: this.systemStatus.metrics.cpu.labels,
                datasets: [{
                    label: 'CPU Usage %',
                    data: this.systemStatus.metrics.cpu.data,
                    borderColor: '#f56565',
                    backgroundColor: 'rgba(245, 101, 101, 0.1)',
                    tension: 0.4,
                    fill: true
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        max: 100,
                        ticks: {
                            callback: function(value) {
                                return value + '%';
                            }
                        }
                    }
                }
            }
        });
    }

    renderMemoryChart() {
        const canvas = document.getElementById('memory-usage-chart');
        if (!canvas || !this.systemStatus.metrics?.memory) return;

        // Destroy existing chart if it exists
        if (this.memoryChart) {
            this.memoryChart.destroy();
        }

        this.memoryChart = new Chart(canvas, {
            type: 'doughnut',
            data: {
                labels: ['Used', 'Free'],
                datasets: [{
                    data: [
                        this.systemStatus.metrics.memory.used,
                        this.systemStatus.metrics.memory.total - this.systemStatus.metrics.memory.used
                    ],
                    backgroundColor: ['#ed8936', '#e2e8f0']
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom'
                    }
                }
            }
        });
    }

    renderDiskChart() {
        const canvas = document.getElementById('disk-usage-chart');
        if (!canvas || !this.systemStatus.metrics?.disk) return;

        // Destroy existing chart if it exists
        if (this.diskChart) {
            this.diskChart.destroy();
        }

        this.diskChart = new Chart(canvas, {
            type: 'bar',
            data: {
                labels: this.systemStatus.metrics.disk.labels,
                datasets: [{
                    label: 'Disk Usage %',
                    data: this.systemStatus.metrics.disk.data,
                    backgroundColor: '#4299e1'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        max: 100,
                        ticks: {
                            callback: function(value) {
                                return value + '%';
                            }
                        }
                    }
                }
            }
        });
    }

    renderNetworkChart() {
        const canvas = document.getElementById('network-traffic-chart');
        if (!canvas || !this.systemStatus.metrics?.network) return;

        // Destroy existing chart if it exists
        if (this.networkChart) {
            this.networkChart.destroy();
            this.networkChart = null;
        }

        this.networkChart = new Chart(canvas, {
            type: 'line',
            data: {
                labels: this.systemStatus.metrics.network.labels,
                datasets: [{
                    label: 'Inbound',
                    data: this.systemStatus.metrics.network.inbound,
                    borderColor: '#48bb78',
                    backgroundColor: 'rgba(72, 187, 120, 0.1)',
                    tension: 0.4
                }, {
                    label: 'Outbound',
                    data: this.systemStatus.metrics.network.outbound,
                    borderColor: '#ed8936',
                    backgroundColor: 'rgba(237, 137, 54, 0.1)',
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom'
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            callback: function(value) {
                                return value + ' MB/s';
                            }
                        }
                    }
                }
            }
        });
    }

    renderSystemLogs(logs) {
        const container = document.getElementById('system-logs-container');
        if (!container) return;

        const logsHTML = logs.map(log => `
            <div class="system-log-entry log-${log.level}">
                <div class="log-timestamp">${this.formatDate(log.timestamp)}</div>
                <div class="log-level">${log.level.toUpperCase()}</div>
                <div class="log-message">${log.message}</div>
            </div>
        `).join('');

        container.innerHTML = logsHTML;
    }

    updateStatus(newStatus) {
        this.systemStatus = { ...this.systemStatus, ...newStatus };
        this.renderStatusCards();
        this.renderMetricCharts();
    }

    startRealTimeUpdates() {
        this.updateInterval = setInterval(() => {
            this.loadSystemStatus();
        }, 30000); // Update every 30 seconds
    }

    async clearAlerts() {
        try {
            const data = await this.apiCall('/api/admin/system/alerts/clear', {
                method: 'POST'
            });
            
            if (data.success) {
                this.alerts = [];
                this.renderAlerts();
                this.showNotification('Alerts cleared successfully', 'success');
            }
        } catch (error) {
            console.error('Failed to clear alerts:', error);
            this.showNotification('Failed to clear alerts', 'error');
        }
    }

    getServiceIcon(service) {
        const icons = {
            database: 'database',
            api: 'server',
            cache: 'zap',
            storage: 'hard-drive',
            email: 'mail'
        };
        return icons[service] || 'server';
    }

    formatServiceName(service) {
        return service.replace(/([A-Z])/g, ' $1').replace(/^./, str => str.toUpperCase());
    }

    getAlertIcon(severity) {
        const icons = {
            critical: 'alert-triangle',
            warning: 'alert-circle',
            info: 'info'
        };
        return icons[severity] || 'info';
    }

    formatDate(dateString) {
        return new Date(dateString).toLocaleString();
    }

    showNotification(message, type) {
        console.log(`${type.toUpperCase()}: ${message}`);
    }

    destroy() {
        super.destroy();
        if (this.updateInterval) {
            clearInterval(this.updateInterval);
        }
    }
}

// Export components for browser use
if (typeof window !== 'undefined') {
    window.AnalyticsPanelComponent = AnalyticsPanelComponent;
    window.OrderManagerComponent = OrderManagerComponent;
    window.SystemMonitorComponent = SystemMonitorComponent;
}

// Export final components for Node.js
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        AnalyticsPanelComponent,
        OrderManagerComponent,
        SystemMonitorComponent
    };
}