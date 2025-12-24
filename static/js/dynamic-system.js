/**
 * Dynamic E-Commerce System - Real-time Features
 * Handles all dynamic functionality including real-time updates, notifications, and interactive features
 */

class DynamicECommerceSystem {
    constructor() {
        this.init();
        this.setupEventListeners();
        this.startRealTimeUpdates();
        this.initializeNotifications();
    }

    init() {
        console.log('🚀 Dynamic E-Commerce System Initialized');
        this.cartCount = 0;
        this.notifications = [];
        this.updateInterval = null;
        this.socketConnection = null;
        
        // Initialize components
        this.initializeSearch();
        this.initializeFilters();
        this.initializeCart();
        this.initializeDashboard();
        this.initializeVendorFeatures();
    }

    // ==================== REAL-TIME SEARCH ====================
    initializeSearch() {
        const searchInput = document.getElementById('search-input');
        const searchResults = document.getElementById('search-results');
        
        if (searchInput) {
            let searchTimeout;
            
            searchInput.addEventListener('input', (e) => {
                clearTimeout(searchTimeout);
                const query = e.target.value.trim();
                
                if (query.length < 2) {
                    this.hideSearchResults();
                    return;
                }
                
                searchTimeout = setTimeout(() => {
                    this.performRealTimeSearch(query);
                }, 300);
            });
            
            // Hide results when clicking outside
            document.addEventListener('click', (e) => {
                if (!searchInput.contains(e.target) && !searchResults?.contains(e.target)) {
                    this.hideSearchResults();
                }
            });
        }
    }

    async performRealTimeSearch(query) {
        try {
            const response = await fetch(`/api/search?q=${encodeURIComponent(query)}`);
            const data = await response.json();
            
            if (data.success) {
                this.displaySearchResults(data.results);
            }
        } catch (error) {
            console.error('Search error:', error);
        }
    }

    displaySearchResults(results) {
        let searchResults = document.getElementById('search-results');
        
        if (!searchResults) {
            searchResults = document.createElement('div');
            searchResults.id = 'search-results';
            searchResults.className = 'search-results-dropdown';
            document.getElementById('search-input').parentNode.appendChild(searchResults);
        }
        
        if (results.length === 0) {
            searchResults.innerHTML = '<div class="search-no-results">No products found</div>';
        } else {
            searchResults.innerHTML = results.map(product => `
                <div class="search-result-item" onclick="window.location.href='/product/${product.id}'">
                    <img src="${product.image_url}" alt="${product.name}" class="search-result-image">
                    <div class="search-result-info">
                        <div class="search-result-name">${product.name}</div>
                        <div class="search-result-price">$${product.price}</div>
                        ${product.vendor_name ? `<div class="search-result-vendor">by ${product.vendor_name}</div>` : ''}
                    </div>
                </div>
            `).join('');
        }
        
        searchResults.style.display = 'block';
    }

    hideSearchResults() {
        const searchResults = document.getElementById('search-results');
        if (searchResults) {
            searchResults.style.display = 'none';
        }
    }

    // ==================== DYNAMIC FILTERS ====================
    initializeFilters() {
        const filterElements = document.querySelectorAll('.filter-option');
        const priceRange = document.getElementById('price-range');
        const sortSelect = document.getElementById('sort-select');
        
        filterElements.forEach(filter => {
            filter.addEventListener('change', () => this.applyFilters());
        });
        
        if (priceRange) {
            priceRange.addEventListener('input', () => {
                document.getElementById('price-display').textContent = `$0 - $${priceRange.value}`;
                clearTimeout(this.filterTimeout);
                this.filterTimeout = setTimeout(() => this.applyFilters(), 500);
            });
        }
        
        if (sortSelect) {
            sortSelect.addEventListener('change', () => this.applyFilters());
        }
    }

    async applyFilters() {
        const filters = this.getActiveFilters();
        const productsContainer = document.getElementById('products-container');
        
        if (!productsContainer) return;
        
        // Show loading state
        productsContainer.innerHTML = '<div class="loading-spinner">Loading products...</div>';
        
        try {
            const response = await fetch('/api/products/filter', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(filters)
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.displayFilteredProducts(data.products);
                this.updateResultsCount(data.total);
            }
        } catch (error) {
            console.error('Filter error:', error);
            productsContainer.innerHTML = '<div class="error-message">Error loading products</div>';
        }
    }

    getActiveFilters() {
        const filters = {
            categories: [],
            price_max: null,
            sort: 'name',
            search: ''
        };
        
        // Get selected categories
        document.querySelectorAll('.category-filter:checked').forEach(checkbox => {
            filters.categories.push(checkbox.value);
        });
        
        // Get price range
        const priceRange = document.getElementById('price-range');
        if (priceRange) {
            filters.price_max = parseFloat(priceRange.value);
        }
        
        // Get sort option
        const sortSelect = document.getElementById('sort-select');
        if (sortSelect) {
            filters.sort = sortSelect.value;
        }
        
        // Get search query
        const searchInput = document.getElementById('search-input');
        if (searchInput) {
            filters.search = searchInput.value.trim();
        }
        
        return filters;
    }

    displayFilteredProducts(products) {
        const productsContainer = document.getElementById('products-container');
        
        if (products.length === 0) {
            productsContainer.innerHTML = `
                <div class="no-products-message">
                    <h3>No products found</h3>
                    <p>Try adjusting your filters or search terms</p>
                </div>
            `;
            return;
        }
        
        productsContainer.innerHTML = products.map(product => `
            <div class="product-card" data-product-id="${product.id}">
                <div class="product-image-container">
                    <img src="${product.image_url}" alt="${product.name}" class="product-image">
                    ${product.discount_percentage > 0 ? `<div class="discount-badge">-${product.discount_percentage}%</div>` : ''}
                    ${product.is_featured ? '<div class="featured-badge">Featured</div>' : ''}
                </div>
                <div class="product-info">
                    <h3 class="product-name">${product.name}</h3>
                    <p class="product-description">${product.description.substring(0, 100)}...</p>
                    <div class="product-price">
                        ${product.discount_percentage > 0 ? 
                            `<span class="original-price">$${product.price}</span>
                             <span class="discounted-price">$${(product.price * (1 - product.discount_percentage / 100)).toFixed(2)}</span>` :
                            `<span class="price">$${product.price}</span>`
                        }
                    </div>
                    ${product.vendor_name ? `<div class="vendor-info">by ${product.vendor_name}</div>` : ''}
                    <div class="product-actions">
                        <button class="btn btn-primary add-to-cart-btn" onclick="dynamicSystem.addToCart(${product.id})">
                            Add to Cart
                        </button>
                        <button class="btn btn-secondary" onclick="window.location.href='/product/${product.id}'">
                            View Details
                        </button>
                    </div>
                </div>
            </div>
        `).join('');
        
        // Add animation
        this.animateProductCards();
    }

    animateProductCards() {
        const cards = document.querySelectorAll('.product-card');
        cards.forEach((card, index) => {
            card.style.opacity = '0';
            card.style.transform = 'translateY(20px)';
            
            setTimeout(() => {
                card.style.transition = 'all 0.3s ease';
                card.style.opacity = '1';
                card.style.transform = 'translateY(0)';
            }, index * 100);
        });
    }

    updateResultsCount(total) {
        const resultsCount = document.getElementById('results-count');
        if (resultsCount) {
            resultsCount.textContent = `${total} products found`;
        }
    }

    // ==================== DYNAMIC CART ====================
    initializeCart() {
        this.updateCartDisplay();
        this.setupCartEventListeners();
    }

    setupCartEventListeners() {
        // Quantity update buttons
        document.addEventListener('click', (e) => {
            if (e.target.classList.contains('quantity-increase')) {
                const cartId = e.target.dataset.cartId;
                const currentQty = parseInt(e.target.previousElementSibling.value);
                this.updateCartQuantity(cartId, currentQty + 1);
            }
            
            if (e.target.classList.contains('quantity-decrease')) {
                const cartId = e.target.dataset.cartId;
                const currentQty = parseInt(e.target.nextElementSibling.value);
                if (currentQty > 1) {
                    this.updateCartQuantity(cartId, currentQty - 1);
                }
            }
            
            if (e.target.classList.contains('remove-from-cart')) {
                const cartId = e.target.dataset.cartId;
                this.removeFromCart(cartId);
            }
        });
        
        // Quantity input direct change
        document.addEventListener('change', (e) => {
            if (e.target.classList.contains('quantity-input')) {
                const cartId = e.target.dataset.cartId;
                const quantity = parseInt(e.target.value);
                if (quantity > 0) {
                    this.updateCartQuantity(cartId, quantity);
                }
            }
        });
    }

    async addToCart(productId, quantity = 1) {
        try {
            const response = await fetch('/add_to_cart', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    product_id: productId,
                    quantity: quantity
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.showNotification('Product added to cart!', 'success');
                this.updateCartDisplay();
                this.animateCartIcon();
            } else {
                this.showNotification(data.message || 'Error adding to cart', 'error');
                
                // If user needs to log in, redirect to login page
                if (data.redirect) {
                    setTimeout(() => {
                        window.location.href = data.redirect;
                    }, 2000);
                }
            }
        } catch (error) {
            console.error('Add to cart error:', error);
            this.showNotification('Error adding to cart', 'error');
        }
    }

    async updateCartQuantity(cartId, quantity) {
        try {
            const response = await fetch('/update_cart', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    cart_id: cartId,
                    quantity: quantity
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.updateCartDisplay();
                this.updateCartTotals();
            } else {
                this.showNotification('Error updating cart', 'error');
            }
        } catch (error) {
            console.error('Update cart error:', error);
        }
    }

    async removeFromCart(cartId) {
        if (!confirm('Remove this item from cart?')) return;
        
        try {
            const response = await fetch('/remove_from_cart', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    cart_id: cartId
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.showNotification('Item removed from cart', 'success');
                this.updateCartDisplay();
                this.removeCartItem(cartId);
            }
        } catch (error) {
            console.error('Remove from cart error:', error);
        }
    }

    removeCartItem(cartId) {
        const cartItem = document.querySelector(`[data-cart-id="${cartId}"]`).closest('.cart-item');
        if (cartItem) {
            cartItem.style.transition = 'all 0.3s ease';
            cartItem.style.opacity = '0';
            cartItem.style.transform = 'translateX(-100%)';
            
            setTimeout(() => {
                cartItem.remove();
                this.updateCartTotals();
            }, 300);
        }
    }

    async updateCartDisplay() {
        try {
            const response = await fetch('/api/cart/count');
            const data = await response.json();
            
            if (data.success) {
                this.cartCount = data.count;
                const cartBadge = document.getElementById('cart-count');
                if (cartBadge) {
                    cartBadge.textContent = this.cartCount;
                    cartBadge.style.display = this.cartCount > 0 ? 'block' : 'none';
                }
            }
        } catch (error) {
            console.error('Cart display update error:', error);
        }
    }

    updateCartTotals() {
        const cartItems = document.querySelectorAll('.cart-item');
        let subtotal = 0;
        
        cartItems.forEach(item => {
            const price = parseFloat(item.dataset.price);
            const quantity = parseInt(item.querySelector('.quantity-input').value);
            subtotal += price * quantity;
        });
        
        const tax = subtotal * 0.08; // 8% tax
        const shipping = subtotal > 50 ? 0 : 10; // Free shipping over $50
        const total = subtotal + tax + shipping;
        
        // Update display
        document.getElementById('cart-subtotal').textContent = `$${subtotal.toFixed(2)}`;
        document.getElementById('cart-tax').textContent = `$${tax.toFixed(2)}`;
        document.getElementById('cart-shipping').textContent = shipping === 0 ? 'Free' : `$${shipping.toFixed(2)}`;
        document.getElementById('cart-total').textContent = `$${total.toFixed(2)}`;
    }

    animateCartIcon() {
        const cartIcon = document.getElementById('cart-icon');
        if (cartIcon) {
            cartIcon.classList.add('cart-bounce');
            setTimeout(() => {
                cartIcon.classList.remove('cart-bounce');
            }, 600);
        }
    }

    // ==================== REAL-TIME DASHBOARD ====================
    initializeDashboard() {
        if (window.location.pathname.includes('/admin') || window.location.pathname.includes('/vendor')) {
            this.startDashboardUpdates();
            this.initializeCharts();
        }
    }

    startDashboardUpdates() {
        // Update dashboard stats every 30 seconds
        setInterval(() => {
            this.updateDashboardStats();
        }, 30000);
    }

    async updateDashboardStats() {
        try {
            const response = await fetch('/api/dashboard/stats');
            const data = await response.json();
            
            if (data.success && data.data) {
                this.updateStatCards(data.data);
                this.updateRecentActivity(data.recent_activity);
            }
        } catch (error) {
            console.error('Dashboard update error:', error);
        }
    }

    updateStatCards(stats) {
        if (!stats || typeof stats !== 'object') {
            console.warn('Invalid stats data received:', stats);
            return;
        }
        
        Object.keys(stats).forEach(key => {
            const element = document.getElementById(`stat-${key}`);
            if (element) {
                const currentValue = parseInt(element.textContent) || 0;
                const newValue = stats[key] || 0;
                
                if (currentValue !== newValue) {
                    this.animateNumber(element, currentValue, newValue);
                }
            }
        });
    }

    updateRecentActivity(activities) {
        if (!activities || !Array.isArray(activities)) {
            return;
        }
        
        const activityContainer = document.getElementById('recent-activity');
        if (!activityContainer) {
            return;
        }
        
        const activityHTML = activities.map(activity => `
            <div class="activity-item">
                <div class="activity-icon">
                    <i class="icon-${activity.type || 'info'}"></i>
                </div>
                <div class="activity-content">
                    <div class="activity-title">${activity.title || 'Activity'}</div>
                    <div class="activity-time">${activity.time || 'Just now'}</div>
                </div>
            </div>
        `).join('');
        
        activityContainer.innerHTML = activityHTML;
    }

    animateNumber(element, start, end) {
        const duration = 1000;
        const startTime = performance.now();
        
        const animate = (currentTime) => {
            const elapsed = currentTime - startTime;
            const progress = Math.min(elapsed / duration, 1);
            
            const current = Math.floor(start + (end - start) * progress);
            element.textContent = current;
            
            if (progress < 1) {
                requestAnimationFrame(animate);
            }
        };
        
        requestAnimationFrame(animate);
    }

    initializeCharts() {
        // Initialize Chart.js charts if available
        if (typeof Chart !== 'undefined') {
            this.initializeSalesChart();
            this.initializeProductChart();
        }
    }

    initializeSalesChart() {
        const ctx = document.getElementById('sales-chart');
        if (!ctx) return;
        
        // This would be populated with real data from the backend
        new Chart(ctx, {
            type: 'line',
            data: {
                labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'],
                datasets: [{
                    label: 'Sales',
                    data: [12, 19, 3, 5, 2, 3],
                    borderColor: 'rgb(75, 192, 192)',
                    tension: 0.1
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    title: {
                        display: true,
                        text: 'Monthly Sales'
                    }
                }
            }
        });
    }

    initializeProductChart() {
        const ctx = document.getElementById('product-chart');
        if (!ctx) return;
        
        // Product performance chart
        new Chart(ctx, {
            type: 'bar',
            data: {
                labels: ['Electronics', 'Clothing', 'Home & Garden', 'Sports', 'Books'],
                datasets: [{
                    label: 'Products Sold',
                    data: [65, 59, 80, 81, 56],
                    backgroundColor: [
                        'rgba(255, 99, 132, 0.2)',
                        'rgba(54, 162, 235, 0.2)',
                        'rgba(255, 205, 86, 0.2)',
                        'rgba(75, 192, 192, 0.2)',
                        'rgba(153, 102, 255, 0.2)'
                    ],
                    borderColor: [
                        'rgba(255, 99, 132, 1)',
                        'rgba(54, 162, 235, 1)',
                        'rgba(255, 205, 86, 1)',
                        'rgba(75, 192, 192, 1)',
                        'rgba(153, 102, 255, 1)'
                    ],
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    title: {
                        display: true,
                        text: 'Product Performance'
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true
                    }
                }
            }
        });
    }

    // ==================== VENDOR FEATURES ====================
    initializeVendorFeatures() {
        if (window.location.pathname.includes('/vendor')) {
            this.setupVendorDashboard();
            this.initializeProductManagement();
        }
    }

    setupVendorDashboard() {
        // Real-time order notifications for vendors
        this.startVendorNotifications();
    }

    async startVendorNotifications() {
        // Poll for new orders every minute
        setInterval(async () => {
            try {
                const response = await fetch('/api/vendor/new-orders');
                const data = await response.json();
                
                if (data.success && data.new_orders.length > 0) {
                    data.new_orders.forEach(order => {
                        this.showNotification(
                            `New order #${order.order_number} - $${order.total}`,
                            'info',
                            5000
                        );
                    });
                }
            } catch (error) {
                console.error('Vendor notifications error:', error);
            }
        }, 60000);
    }

    initializeProductManagement() {
        // Dynamic product form validation
        const productForm = document.getElementById('product-form');
        if (productForm) {
            this.setupProductFormValidation(productForm);
        }
    }

    setupProductFormValidation(form) {
        const inputs = form.querySelectorAll('input, textarea, select');
        
        inputs.forEach(input => {
            input.addEventListener('blur', () => {
                this.validateField(input);
            });
            
            input.addEventListener('input', () => {
                this.clearFieldError(input);
            });
        });
    }

    validateField(field) {
        const value = field.value.trim();
        let isValid = true;
        let errorMessage = '';
        
        // Required field validation
        if (field.hasAttribute('required') && !value) {
            isValid = false;
            errorMessage = 'This field is required';
        }
        
        // Specific field validations
        switch (field.type) {
            case 'email':
                if (value && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value)) {
                    isValid = false;
                    errorMessage = 'Please enter a valid email address';
                }
                break;
            case 'number':
                if (value && (isNaN(value) || parseFloat(value) < 0)) {
                    isValid = false;
                    errorMessage = 'Please enter a valid positive number';
                }
                break;
            case 'url':
                if (value && !/^https?:\/\/.+/.test(value)) {
                    isValid = false;
                    errorMessage = 'Please enter a valid URL starting with http:// or https://';
                }
                break;
        }
        
        this.displayFieldValidation(field, isValid, errorMessage);
        return isValid;
    }

    displayFieldValidation(field, isValid, errorMessage) {
        const errorElement = field.parentNode.querySelector('.field-error');
        
        if (isValid) {
            field.classList.remove('error');
            field.classList.add('valid');
            if (errorElement) {
                errorElement.remove();
            }
        } else {
            field.classList.remove('valid');
            field.classList.add('error');
            
            if (!errorElement) {
                const error = document.createElement('div');
                error.className = 'field-error';
                error.textContent = errorMessage;
                field.parentNode.appendChild(error);
            } else {
                errorElement.textContent = errorMessage;
            }
        }
    }

    clearFieldError(field) {
        field.classList.remove('error');
        const errorElement = field.parentNode.querySelector('.field-error');
        if (errorElement) {
            errorElement.remove();
        }
    }

    // ==================== NOTIFICATIONS ====================
    initializeNotifications() {
        // Create notification container
        if (!document.getElementById('notification-container')) {
            const container = document.createElement('div');
            container.id = 'notification-container';
            container.className = 'notification-container';
            document.body.appendChild(container);
        }
    }

    showNotification(message, type = 'info', duration = 3000) {
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.innerHTML = `
            <div class="notification-content">
                <span class="notification-message">${message}</span>
                <button class="notification-close" onclick="this.parentElement.parentElement.remove()">×</button>
            </div>
        `;
        
        const container = document.getElementById('notification-container');
        container.appendChild(notification);
        
        // Animate in
        setTimeout(() => {
            notification.classList.add('show');
        }, 100);
        
        // Auto remove
        if (duration > 0) {
            setTimeout(() => {
                this.removeNotification(notification);
            }, duration);
        }
    }

    removeNotification(notification) {
        notification.classList.add('hide');
        setTimeout(() => {
            if (notification.parentNode) {
                notification.parentNode.removeChild(notification);
            }
        }, 300);
    }

    // ==================== REAL-TIME UPDATES ====================
    startRealTimeUpdates() {
        // Start periodic updates for dynamic content
        this.updateInterval = setInterval(() => {
            this.performRealTimeUpdates();
        }, 30000); // Update every 30 seconds
    }

    async performRealTimeUpdates() {
        // Update cart count
        this.updateCartDisplay();
        
        // Update dashboard if on admin/vendor pages
        if (window.location.pathname.includes('/admin') || window.location.pathname.includes('/vendor')) {
            this.updateDashboardStats();
        }
        
        // Update stock levels on product pages
        if (window.location.pathname.includes('/product/')) {
            this.updateProductStock();
        }
    }

    async updateProductStock() {
        const productId = window.location.pathname.split('/').pop();
        
        try {
            const response = await fetch(`/api/product/${productId}/stock`);
            const data = await response.json();
            
            if (data.success) {
                const stockElement = document.getElementById('product-stock');
                if (stockElement) {
                    stockElement.textContent = `${data.stock} in stock`;
                    
                    // Update stock status
                    const addToCartBtn = document.getElementById('add-to-cart-btn');
                    if (addToCartBtn) {
                        if (data.stock === 0) {
                            addToCartBtn.disabled = true;
                            addToCartBtn.textContent = 'Out of Stock';
                        } else if (data.stock < 5) {
                            stockElement.classList.add('low-stock');
                        }
                    }
                }
            }
        } catch (error) {
            console.error('Stock update error:', error);
        }
    }

    // ==================== EVENT LISTENERS ====================
    setupEventListeners() {
        // Global event listeners
        document.addEventListener('DOMContentLoaded', () => {
            this.initializeTooltips();
            this.initializeModals();
            this.initializeLazyLoading();
        });
        
        // Handle page visibility changes
        document.addEventListener('visibilitychange', () => {
            if (document.hidden) {
                // Pause updates when page is not visible
                if (this.updateInterval) {
                    clearInterval(this.updateInterval);
                }
            } else {
                // Resume updates when page becomes visible
                this.startRealTimeUpdates();
            }
        });
    }

    initializeTooltips() {
        const tooltipElements = document.querySelectorAll('[data-tooltip]');
        
        tooltipElements.forEach(element => {
            element.addEventListener('mouseenter', (e) => {
                this.showTooltip(e.target, e.target.dataset.tooltip);
            });
            
            element.addEventListener('mouseleave', () => {
                this.hideTooltip();
            });
        });
    }

    showTooltip(element, text) {
        const tooltip = document.createElement('div');
        tooltip.className = 'tooltip';
        tooltip.textContent = text;
        document.body.appendChild(tooltip);
        
        const rect = element.getBoundingClientRect();
        tooltip.style.left = rect.left + (rect.width / 2) - (tooltip.offsetWidth / 2) + 'px';
        tooltip.style.top = rect.top - tooltip.offsetHeight - 10 + 'px';
        
        setTimeout(() => tooltip.classList.add('show'), 100);
    }

    hideTooltip() {
        const tooltip = document.querySelector('.tooltip');
        if (tooltip) {
            tooltip.remove();
        }
    }

    initializeModals() {
        // Modal functionality
        document.addEventListener('click', (e) => {
            if (e.target.classList.contains('modal-trigger')) {
                const modalId = e.target.dataset.modal;
                this.openModal(modalId);
            }
            
            if (e.target.classList.contains('modal-close') || e.target.classList.contains('modal-overlay')) {
                this.closeModal();
            }
        });
    }

    openModal(modalId) {
        const modal = document.getElementById(modalId);
        if (modal) {
            modal.classList.add('show');
            document.body.style.overflow = 'hidden';
        }
    }

    closeModal() {
        const modals = document.querySelectorAll('.modal.show');
        modals.forEach(modal => {
            modal.classList.remove('show');
        });
        document.body.style.overflow = '';
    }

    initializeLazyLoading() {
        const images = document.querySelectorAll('img[data-src]');
        
        const imageObserver = new IntersectionObserver((entries, observer) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const img = entry.target;
                    img.src = img.dataset.src;
                    img.classList.remove('lazy');
                    observer.unobserve(img);
                }
            });
        });
        
        images.forEach(img => imageObserver.observe(img));
    }

    // ==================== UTILITY METHODS ====================
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

    throttle(func, limit) {
        let inThrottle;
        return function() {
            const args = arguments;
            const context = this;
            if (!inThrottle) {
                func.apply(context, args);
                inThrottle = true;
                setTimeout(() => inThrottle = false, limit);
            }
        };
    }

    formatCurrency(amount) {
        return new Intl.NumberFormat('en-US', {
            style: 'currency',
            currency: 'USD'
        }).format(amount);
    }

    formatDate(date) {
        return new Intl.DateTimeFormat('en-US', {
            year: 'numeric',
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        }).format(new Date(date));
    }
}

// Initialize the dynamic system when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.dynamicSystem = new DynamicECommerceSystem();
});

// Export for use in other scripts
if (typeof module !== 'undefined' && module.exports) {
    module.exports = DynamicECommerceSystem;
}