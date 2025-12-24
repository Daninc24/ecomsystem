/**
 * Admin Frontend Components
 * Individual component classes for the admin interface
 */

// ==================== BASE COMPONENT ====================

class BaseAdminComponent {
    constructor(containerId) {
        this.containerId = containerId;
        this.container = null;
        this.isInitialized = false;
    }

    init() {
        this.container = document.getElementById(this.containerId);
        if (this.container) {
            this.isInitialized = true;
            this.render();
            this.setupEventListeners();
        }
    }

    render() {
        // Override in subclasses
    }

    setupEventListeners() {
        // Override in subclasses
    }

    destroy() {
        if (this.container) {
            this.container.innerHTML = '';
        }
        this.isInitialized = false;
    }

    async apiCall(endpoint, options = {}) {
        try {
            const response = await fetch(endpoint, {
                headers: {
                    'Content-Type': 'application/json',
                    ...options.headers
                },
                ...options
            });
            
            // Check if response is HTML (likely a redirect to login)
            const contentType = response.headers.get('content-type');
            if (contentType && contentType.includes('text/html')) {
                console.warn(`Received HTML response for ${endpoint}, likely authentication required`);
                throw new Error('Authentication required. Please log in.');
            }
            
            return await response.json();
        } catch (error) {
            console.error(`API call failed for ${endpoint}:`, error);
            throw error;
        }
    }
}

// ==================== DASHBOARD COMPONENT ====================

class DashboardComponent extends BaseAdminComponent {
    constructor() {
        super('admin-dashboard-container');
        this.metrics = {};
        this.widgets = new Map();
        this.charts = new Map();
    }

    render() {
        if (!this.container) return;

        this.container.innerHTML = `
            <div class="admin-dashboard">
                <div class="dashboard-header">
                    <h1>Admin Dashboard</h1>
                    <div class="dashboard-actions">
                        <button class="btn btn-primary" data-action="refreshDashboard">
                            <i class="icon-refresh"></i> Refresh
                        </button>
                        <button class="btn btn-secondary" data-action="customizeLayout">
                            <i class="icon-settings"></i> Customize
                        </button>
                    </div>
                </div>
                
                <div class="dashboard-metrics" id="dashboard-metrics">
                    <!-- Metrics will be populated here -->
                </div>
                
                <div class="dashboard-grid" id="dashboard-grid">
                    <!-- Widgets will be populated here -->
                </div>
            </div>
        `;

        this.loadMetrics();
        this.loadWidgets();
    }

    setupEventListeners() {
        if (!this.container) return;

        this.container.addEventListener('click', (e) => {
            const action = e.target.getAttribute('data-action');
            if (action === 'refreshDashboard') {
                this.refreshDashboard();
            } else if (action === 'customizeLayout') {
                this.openLayoutCustomizer();
            }
        });
    }

    async loadMetrics() {
        try {
            const data = await this.apiCall('/api/admin/analytics/dashboard-metrics');
            if (data.success) {
                this.metrics = data.data;
                this.renderMetrics();
            }
        } catch (error) {
            console.error('Failed to load dashboard metrics:', error);
        }
    }

    renderMetrics() {
        const metricsContainer = document.getElementById('dashboard-metrics');
        if (!metricsContainer) return;

        const metricsHTML = Object.entries(this.metrics).map(([key, value]) => `
            <div class="metric-card" data-metric="${key}">
                <div class="metric-icon">
                    <i class="icon-${this.getMetricIcon(key)}"></i>
                </div>
                <div class="metric-content">
                    <div class="metric-value" id="metric-${key}">${this.formatMetricValue(key, value)}</div>
                    <div class="metric-label">${this.getMetricLabel(key)}</div>
                </div>
                <div class="metric-trend">
                    <span class="trend-indicator ${this.getTrendClass(key)}">
                        <i class="icon-${this.getTrendIcon(key)}"></i>
                        ${this.getTrendValue(key)}%
                    </span>
                </div>
            </div>
        `).join('');

        metricsContainer.innerHTML = metricsHTML;
    }

    async loadWidgets() {
        try {
            const data = await this.apiCall('/api/admin/configuration/dashboard-widgets');
            if (data.success) {
                this.renderWidgets(data.data.widgets);
            }
        } catch (error) {
            console.error('Failed to load dashboard widgets:', error);
        }
    }

    renderWidgets(widgets) {
        const gridContainer = document.getElementById('dashboard-grid');
        if (!gridContainer) return;

        const widgetsHTML = widgets.map(widget => `
            <div class="dashboard-widget" data-widget-id="${widget.id}" data-widget-type="${widget.type}">
                <div class="widget-header">
                    <h3>${widget.title}</h3>
                    <div class="widget-actions">
                        <button class="widget-action" data-action="refreshWidget" data-widget-id="${widget.id}">
                            <i class="icon-refresh"></i>
                        </button>
                        <button class="widget-action" data-action="configureWidget" data-widget-id="${widget.id}">
                            <i class="icon-settings"></i>
                        </button>
                        <div class="drag-handle">
                            <i class="icon-drag"></i>
                        </div>
                    </div>
                </div>
                <div class="widget-content" id="widget-content-${widget.id}">
                    <!-- Widget content will be loaded here -->
                </div>
            </div>
        `).join('');

        gridContainer.innerHTML = widgetsHTML;

        // Load content for each widget
        widgets.forEach(widget => {
            this.loadWidgetContent(widget);
        });
    }

    async loadWidgetContent(widget) {
        const contentContainer = document.getElementById(`widget-content-${widget.id}`);
        if (!contentContainer) return;

        try {
            const data = await this.apiCall(`/api/admin/widgets/${widget.type}/${widget.id}`);
            if (data.success) {
                this.renderWidgetContent(contentContainer, widget.type, data.data);
            }
        } catch (error) {
            console.error(`Failed to load widget content for ${widget.id}:`, error);
            contentContainer.innerHTML = '<div class="widget-error">Failed to load widget content</div>';
        }
    }

    renderWidgetContent(container, type, data) {
        switch (type) {
            case 'chart':
                this.renderChartWidget(container, data);
                break;
            case 'table':
                this.renderTableWidget(container, data);
                break;
            case 'list':
                this.renderListWidget(container, data);
                break;
            case 'metric':
                this.renderMetricWidget(container, data);
                break;
            default:
                container.innerHTML = '<div class="widget-placeholder">Widget type not supported</div>';
        }
    }

    renderChartWidget(container, data) {
        const canvas = document.createElement('canvas');
        canvas.id = `chart-${Date.now()}`;
        container.appendChild(canvas);

        if (typeof Chart !== 'undefined') {
            new Chart(canvas, {
                type: data.chartType || 'line',
                data: data.chartData,
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    ...data.chartOptions
                }
            });
        }
    }

    renderTableWidget(container, data) {
        const table = `
            <div class="widget-table-container">
                <table class="widget-table">
                    <thead>
                        <tr>
                            ${data.headers.map(header => `<th>${header}</th>`).join('')}
                        </tr>
                    </thead>
                    <tbody>
                        ${data.rows.map(row => `
                            <tr>
                                ${row.map(cell => `<td>${cell}</td>`).join('')}
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            </div>
        `;
        container.innerHTML = table;
    }

    renderListWidget(container, data) {
        const list = `
            <div class="widget-list">
                ${data.items.map(item => `
                    <div class="widget-list-item">
                        <div class="list-item-content">
                            <div class="list-item-title">${item.title}</div>
                            <div class="list-item-subtitle">${item.subtitle || ''}</div>
                        </div>
                        <div class="list-item-value">${item.value}</div>
                    </div>
                `).join('')}
            </div>
        `;
        container.innerHTML = list;
    }

    renderMetricWidget(container, data) {
        const metric = `
            <div class="widget-metric">
                <div class="widget-metric-value">${data.value}</div>
                <div class="widget-metric-label">${data.label}</div>
                ${data.trend ? `
                    <div class="widget-metric-trend ${data.trend > 0 ? 'positive' : 'negative'}">
                        <i class="icon-${data.trend > 0 ? 'arrow-up' : 'arrow-down'}"></i>
                        ${Math.abs(data.trend)}%
                    </div>
                ` : ''}
            </div>
        `;
        container.innerHTML = metric;
    }

    updateMetrics(newMetrics) {
        Object.entries(newMetrics).forEach(([key, value]) => {
            const element = document.getElementById(`metric-${key}`);
            if (element) {
                const currentValue = this.parseMetricValue(element.textContent);
                const newValue = this.parseMetricValue(this.formatMetricValue(key, value));
                
                if (currentValue !== newValue) {
                    this.animateMetricChange(element, currentValue, newValue, key);
                }
            }
        });
        
        this.metrics = { ...this.metrics, ...newMetrics };
    }

    animateMetricChange(element, from, to, key) {
        const duration = 1000;
        const startTime = performance.now();
        
        const animate = (currentTime) => {
            const elapsed = currentTime - startTime;
            const progress = Math.min(elapsed / duration, 1);
            
            const current = from + (to - from) * this.easeOutCubic(progress);
            element.textContent = this.formatMetricValue(key, current);
            
            if (progress < 1) {
                requestAnimationFrame(animate);
            }
        };
        
        requestAnimationFrame(animate);
    }

    easeOutCubic(t) {
        return 1 - Math.pow(1 - t, 3);
    }

    setupRealTimeMetrics() {
        // This method is called by the main interface
        console.log('Real-time metrics setup for dashboard');
    }

    initializeWidgets() {
        // This method is called by the main interface
        console.log('Widgets initialized for dashboard');
    }

    setupResponsiveLayout() {
        // This method is called by the main interface
        console.log('Responsive layout setup for dashboard');
    }

    refreshDashboard() {
        this.loadMetrics();
        this.loadWidgets();
    }

    openLayoutCustomizer() {
        // Open layout customization modal
        console.log('Opening layout customizer');
    }

    // Helper methods
    getMetricIcon(key) {
        const icons = {
            users: 'users',
            orders: 'shopping-cart',
            revenue: 'dollar-sign',
            products: 'package',
            vendors: 'store'
        };
        return icons[key] || 'bar-chart';
    }

    getMetricLabel(key) {
        const labels = {
            users: 'Total Users',
            orders: 'Total Orders',
            revenue: 'Revenue',
            products: 'Products',
            vendors: 'Vendors'
        };
        return labels[key] || key.charAt(0).toUpperCase() + key.slice(1);
    }

    formatMetricValue(key, value) {
        if (key === 'revenue') {
            return new Intl.NumberFormat('en-US', {
                style: 'currency',
                currency: 'USD'
            }).format(value);
        }
        return new Intl.NumberFormat('en-US').format(value);
    }

    parseMetricValue(text) {
        return parseFloat(text.replace(/[^0-9.-]+/g, '')) || 0;
    }

    getTrendClass(key) {
        // This would be calculated based on historical data
        return Math.random() > 0.5 ? 'positive' : 'negative';
    }

    getTrendIcon(key) {
        return this.getTrendClass(key) === 'positive' ? 'arrow-up' : 'arrow-down';
    }

    getTrendValue(key) {
        // This would be calculated based on historical data
        return Math.floor(Math.random() * 20) + 1;
    }

    handleResize(isMobile) {
        const grid = document.getElementById('dashboard-grid');
        if (grid) {
            if (isMobile) {
                grid.classList.add('mobile-layout');
            } else {
                grid.classList.remove('mobile-layout');
            }
        }
    }
}

// ==================== USER MANAGER COMPONENT ====================

class UserManagerComponent extends BaseAdminComponent {
    constructor() {
        super('user-management-container');
        this.users = [];
        this.filters = {};
        this.sortBy = 'created_at';
        this.sortOrder = 'desc';
    }

    render() {
        if (!this.container) return;

        this.container.innerHTML = `
            <div class="user-manager">
                <div class="user-manager-header">
                    <h2>User Management</h2>
                    <div class="user-manager-actions">
                        <button class="btn btn-primary" data-action="addUser">
                            <i class="icon-plus"></i> Add User
                        </button>
                        <button class="btn btn-secondary" data-action="exportUsers">
                            <i class="icon-download"></i> Export
                        </button>
                    </div>
                </div>
                
                <div class="user-manager-filters">
                    <div class="filter-group">
                        <input type="text" class="form-control" placeholder="Search users..." id="user-search">
                        <select class="form-control" id="user-role-filter">
                            <option value="">All Roles</option>
                            <option value="admin">Admin</option>
                            <option value="vendor">Vendor</option>
                            <option value="customer">Customer</option>
                        </select>
                        <select class="form-control" id="user-status-filter">
                            <option value="">All Status</option>
                            <option value="active">Active</option>
                            <option value="inactive">Inactive</option>
                            <option value="suspended">Suspended</option>
                        </select>
                    </div>
                </div>
                
                <div class="user-manager-content">
                    <div class="user-list" id="user-list">
                        <!-- Users will be populated here -->
                    </div>
                </div>
            </div>
        `;

        this.loadUsers();
    }

    setupEventListeners() {
        if (!this.container) return;

        // Search functionality
        const searchInput = document.getElementById('user-search');
        if (searchInput) {
            searchInput.addEventListener('input', this.debounce(() => {
                this.applyFilters();
            }, 300));
        }

        // Filter functionality
        const roleFilter = document.getElementById('user-role-filter');
        const statusFilter = document.getElementById('user-status-filter');
        
        if (roleFilter) {
            roleFilter.addEventListener('change', () => this.applyFilters());
        }
        
        if (statusFilter) {
            statusFilter.addEventListener('change', () => this.applyFilters());
        }

        // Action buttons
        this.container.addEventListener('click', (e) => {
            const action = e.target.getAttribute('data-action');
            const userId = e.target.getAttribute('data-user-id');
            
            switch (action) {
                case 'addUser':
                    this.openAddUserModal();
                    break;
                case 'editUser':
                    this.openEditUserModal(userId);
                    break;
                case 'deleteUser':
                    this.deleteUser(userId);
                    break;
                case 'suspendUser':
                    this.suspendUser(userId);
                    break;
                case 'activateUser':
                    this.activateUser(userId);
                    break;
                case 'exportUsers':
                    this.exportUsers();
                    break;
            }
        });
    }

    async loadUsers() {
        try {
            const data = await this.apiCall('/api/admin/users');
            if (data.success) {
                this.users = data.data.users;
                this.renderUsers();
            }
        } catch (error) {
            console.error('Failed to load users:', error);
        }
    }

    renderUsers() {
        const userList = document.getElementById('user-list');
        if (!userList) return;

        if (this.users.length === 0) {
            userList.innerHTML = '<div class="empty-state">No users found</div>';
            return;
        }

        const usersHTML = this.users.map(user => `
            <div class="user-item" data-user-id="${user.id}">
                <div class="user-avatar">
                    <img src="${user.avatar_url || '/static/images/default-avatar.png'}" alt="${user.username}">
                </div>
                <div class="user-info">
                    <div class="user-name">${user.username}</div>
                    <div class="user-email">${user.email}</div>
                    <div class="user-meta">
                        <span class="user-role role-${user.role}">${user.role}</span>
                        <span class="user-status status-${user.status}">${user.status}</span>
                        <span class="user-date">Joined ${this.formatDate(user.created_at)}</span>
                    </div>
                </div>
                <div class="user-actions">
                    <button class="btn btn-sm btn-secondary" data-action="editUser" data-user-id="${user.id}">
                        <i class="icon-edit"></i> Edit
                    </button>
                    ${user.status === 'active' ? 
                        `<button class="btn btn-sm btn-warning" data-action="suspendUser" data-user-id="${user.id}">
                            <i class="icon-pause"></i> Suspend
                        </button>` :
                        `<button class="btn btn-sm btn-success" data-action="activateUser" data-user-id="${user.id}">
                            <i class="icon-play"></i> Activate
                        </button>`
                    }
                    <button class="btn btn-sm btn-danger" data-action="deleteUser" data-user-id="${user.id}">
                        <i class="icon-trash"></i> Delete
                    </button>
                </div>
            </div>
        `).join('');

        userList.innerHTML = usersHTML;
    }

    applyFilters() {
        const searchTerm = document.getElementById('user-search')?.value.toLowerCase() || '';
        const roleFilter = document.getElementById('user-role-filter')?.value || '';
        const statusFilter = document.getElementById('user-status-filter')?.value || '';

        const filteredUsers = this.users.filter(user => {
            const matchesSearch = !searchTerm || 
                user.username.toLowerCase().includes(searchTerm) ||
                user.email.toLowerCase().includes(searchTerm);
            
            const matchesRole = !roleFilter || user.role === roleFilter;
            const matchesStatus = !statusFilter || user.status === statusFilter;

            return matchesSearch && matchesRole && matchesStatus;
        });

        // Temporarily replace users array for rendering
        const originalUsers = this.users;
        this.users = filteredUsers;
        this.renderUsers();
        this.users = originalUsers;
    }

    async openAddUserModal() {
        const modal = this.createUserModal('Add New User');
        this.setupUserFormEvents(modal);
    }

    async openEditUserModal(userId) {
        try {
            // Get user data first
            const userData = await this.apiCall(`/api/admin/users/${userId}`);
            if (userData.success) {
                const modal = this.createUserModal('Edit User', userData.data);
                this.setupUserFormEvents(modal, userData.data);
            } else {
                this.showNotification('Failed to load user data', 'error');
            }
        } catch (error) {
            console.error('Failed to load user for editing:', error);
            this.showNotification('Failed to load user data', 'error');
        }
    }

    createUserModal(title, user = null) {
        const isEdit = user !== null;
        
        const modal = document.createElement('div');
        modal.className = 'admin-modal user-modal';
        modal.innerHTML = `
            <div class="modal-overlay"></div>
            <div class="modal-content">
                <div class="modal-header">
                    <h3>${title}</h3>
                    <button class="modal-close">&times;</button>
                </div>
                <div class="modal-body">
                    <form id="user-form" class="admin-form">
                        <div class="form-row">
                            <div class="form-group">
                                <label for="user-username">Username *</label>
                                <input type="text" id="user-username" name="username" required 
                                       value="${user ? user.username : ''}" 
                                       placeholder="Enter username"
                                       ${isEdit ? 'readonly' : ''}>
                                <small class="form-help">Username cannot be changed after creation</small>
                            </div>
                            <div class="form-group">
                                <label for="user-email">Email *</label>
                                <input type="email" id="user-email" name="email" required 
                                       value="${user ? user.email : ''}" 
                                       placeholder="Enter email address">
                            </div>
                        </div>
                        
                        <div class="form-row">
                            <div class="form-group">
                                <label for="user-first-name">First Name</label>
                                <input type="text" id="user-first-name" name="first_name" 
                                       value="${user ? user.first_name || '' : ''}" 
                                       placeholder="Enter first name">
                            </div>
                            <div class="form-group">
                                <label for="user-last-name">Last Name</label>
                                <input type="text" id="user-last-name" name="last_name" 
                                       value="${user ? user.last_name || '' : ''}" 
                                       placeholder="Enter last name">
                            </div>
                        </div>
                        
                        <div class="form-row">
                            <div class="form-group">
                                <label for="user-phone">Phone</label>
                                <input type="tel" id="user-phone" name="phone" 
                                       value="${user ? user.phone || '' : ''}" 
                                       placeholder="Enter phone number">
                            </div>
                            <div class="form-group">
                                <label for="user-status">Status</label>
                                <select id="user-status" name="is_active" class="form-control">
                                    <option value="true" ${user && user.is_active ? 'selected' : ''}>Active</option>
                                    <option value="false" ${user && !user.is_active ? 'selected' : ''}>Inactive</option>
                                </select>
                            </div>
                        </div>
                        
                        ${!isEdit ? `
                        <div class="form-row">
                            <div class="form-group">
                                <label for="user-password">Password *</label>
                                <input type="password" id="user-password" name="password" required 
                                       placeholder="Enter password" minlength="6">
                                <small class="form-help">Minimum 6 characters</small>
                            </div>
                            <div class="form-group">
                                <label for="user-confirm-password">Confirm Password *</label>
                                <input type="password" id="user-confirm-password" name="confirm_password" required 
                                       placeholder="Confirm password">
                            </div>
                        </div>
                        ` : ''}
                        
                        <div class="form-group">
                            <label>Roles</label>
                            <div class="role-checkboxes" id="user-roles">
                                <label class="checkbox-label">
                                    <input type="checkbox" name="roles" value="admin" 
                                           ${user && user.roles && user.roles.some(r => r.name === 'admin') ? 'checked' : ''}>
                                    <span>Administrator</span>
                                </label>
                                <label class="checkbox-label">
                                    <input type="checkbox" name="roles" value="vendor" 
                                           ${user && user.roles && user.roles.some(r => r.name === 'vendor') ? 'checked' : ''}>
                                    <span>Vendor</span>
                                </label>
                                <label class="checkbox-label">
                                    <input type="checkbox" name="roles" value="customer" 
                                           ${user && user.roles && user.roles.some(r => r.name === 'customer') ? 'checked' : ''}>
                                    <span>Customer</span>
                                </label>
                            </div>
                        </div>
                        
                        <div class="form-actions">
                            <button type="button" class="btn btn-secondary" data-action="cancel">Cancel</button>
                            <button type="submit" class="btn btn-primary">
                                ${isEdit ? 'Update User' : 'Create User'}
                            </button>
                        </div>
                    </form>
                </div>
            </div>
        `;
        
        document.body.appendChild(modal);
        
        // Show modal
        setTimeout(() => {
            modal.classList.add('show');
        }, 100);
        
        return modal;
    }

    setupUserFormEvents(modal, user = null) {
        const form = modal.querySelector('#user-form');
        const isEdit = user !== null;
        
        // Close modal events
        modal.querySelector('.modal-close').addEventListener('click', () => {
            this.closeModal(modal);
        });
        
        modal.querySelector('.modal-overlay').addEventListener('click', () => {
            this.closeModal(modal);
        });
        
        modal.querySelector('[data-action="cancel"]').addEventListener('click', () => {
            this.closeModal(modal);
        });
        
        // Password confirmation validation (for new users)
        if (!isEdit) {
            const passwordInput = form.querySelector('#user-password');
            const confirmPasswordInput = form.querySelector('#user-confirm-password');
            
            const validatePasswords = () => {
                if (passwordInput.value !== confirmPasswordInput.value) {
                    confirmPasswordInput.setCustomValidity('Passwords do not match');
                } else {
                    confirmPasswordInput.setCustomValidity('');
                }
            };
            
            passwordInput.addEventListener('input', validatePasswords);
            confirmPasswordInput.addEventListener('input', validatePasswords);
        }
        
        // Form submission
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const formData = new FormData(form);
            const userData = {};
            
            // Convert form data to object
            for (let [key, value] of formData.entries()) {
                if (key === 'roles') {
                    if (!userData.roles) userData.roles = [];
                    userData.roles.push(value);
                } else if (key === 'is_active') {
                    userData[key] = value === 'true';
                } else {
                    userData[key] = value;
                }
            }
            
            // Handle unchecked roles
            if (!userData.roles) userData.roles = [];
            
            try {
                const url = isEdit ? `/api/admin/users/${user.id}` : '/api/admin/users';
                const method = isEdit ? 'PUT' : 'POST';
                
                const response = await this.apiCall(url, {
                    method: method,
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify(userData)
                });
                
                if (response.success) {
                    this.closeModal(modal);
                    this.loadUsers(); // Reload the user list
                    this.showNotification(
                        isEdit ? 'User updated successfully' : 'User created successfully', 
                        'success'
                    );
                } else {
                    // Handle validation errors
                    if (response.errors) {
                        this.displayFormErrors(form, response.errors);
                    } else {
                        this.showNotification(response.error || 'Failed to save user', 'error');
                    }
                }
            } catch (error) {
                console.error('Failed to save user:', error);
                this.showNotification('Failed to save user', 'error');
            }
        });
    }

    displayFormErrors(form, errors) {
        // Clear previous errors
        form.querySelectorAll('.field-error').forEach(error => error.remove());
        form.querySelectorAll('.error').forEach(field => field.classList.remove('error'));
        
        // Display new errors
        Object.entries(errors).forEach(([field, messages]) => {
            const input = form.querySelector(`[name="${field}"]`);
            if (input) {
                input.classList.add('error');
                
                const errorDiv = document.createElement('div');
                errorDiv.className = 'field-error';
                errorDiv.textContent = Array.isArray(messages) ? messages[0] : messages;
                
                input.parentNode.appendChild(errorDiv);
            }
        });
    }

    closeModal(modal) {
        modal.classList.remove('show');
        setTimeout(() => {
            document.body.removeChild(modal);
        }, 300);
    }

    showNotification(message, type) {
        // Simple notification - in a real app, this would integrate with a notification system
        console.log(`${type.toUpperCase()}: ${message}`);
        
        // Create a simple toast notification
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.textContent = message;
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 12px 20px;
            border-radius: 4px;
            color: white;
            z-index: 10000;
            font-weight: 500;
            background-color: ${type === 'success' ? '#10b981' : type === 'error' ? '#ef4444' : '#3b82f6'};
        `;
        
        document.body.appendChild(notification);
        
        setTimeout(() => {
            notification.style.opacity = '0';
            setTimeout(() => {
                if (notification.parentNode) {
                    document.body.removeChild(notification);
                }
            }, 300);
        }, 3000);
    }

    async deleteUser(userId) {
        if (!confirm('Are you sure you want to delete this user?')) return;

        try {
            const data = await this.apiCall(`/api/admin/users/${userId}`, {
                method: 'DELETE'
            });
            
            if (data.success) {
                this.users = this.users.filter(user => user.id !== userId);
                this.renderUsers();
                this.showNotification('User deleted successfully', 'success');
            }
        } catch (error) {
            console.error('Failed to delete user:', error);
            this.showNotification('Failed to delete user', 'error');
        }
    }

    async suspendUser(userId) {
        try {
            const data = await this.apiCall(`/api/admin/users/${userId}/suspend`, {
                method: 'POST'
            });
            
            if (data.success) {
                const user = this.users.find(u => u.id === userId);
                if (user) {
                    user.status = 'suspended';
                    this.renderUsers();
                    this.showNotification('User suspended successfully', 'success');
                }
            }
        } catch (error) {
            console.error('Failed to suspend user:', error);
            this.showNotification('Failed to suspend user', 'error');
        }
    }

    async activateUser(userId) {
        try {
            const data = await this.apiCall(`/api/admin/users/${userId}/activate`, {
                method: 'POST'
            });
            
            if (data.success) {
                const user = this.users.find(u => u.id === userId);
                if (user) {
                    user.status = 'active';
                    this.renderUsers();
                    this.showNotification('User activated successfully', 'success');
                }
            }
        } catch (error) {
            console.error('Failed to activate user:', error);
            this.showNotification('Failed to activate user', 'error');
        }
    }

    async exportUsers() {
        try {
            const response = await fetch('/api/admin/users/export', {
                method: 'GET'
            });
            
            if (response.ok) {
                const blob = await response.blob();
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `users-export-${new Date().toISOString().split('T')[0]}.csv`;
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                window.URL.revokeObjectURL(url);
                
                this.showNotification('Users exported successfully', 'success');
            }
        } catch (error) {
            console.error('Failed to export users:', error);
            this.showNotification('Failed to export users', 'error');
        }
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
        // This would typically call the main interface's notification system
        console.log(`${type.toUpperCase()}: ${message}`);
    }
}

// Export components for browser use
if (typeof window !== 'undefined') {
    window.BaseAdminComponent = BaseAdminComponent;
    window.DashboardComponent = DashboardComponent;
    window.UserManagerComponent = UserManagerComponent;
}

// Export components for use in other scripts
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        BaseAdminComponent,
        DashboardComponent,
        UserManagerComponent
    };
}