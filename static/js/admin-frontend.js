/**
 * Dynamic Admin Frontend Interface
 * Modern component-based admin interface with real-time updates, inline editing,
 * drag-and-drop functionality, and mobile-responsive design
 */

class AdminFrontendInterface {
    constructor() {
        this.components = new Map();
        this.realTimeUpdates = new Map();
        this.dragDropInstances = new Map();
        this.inlineEditors = new Map();
        this.themePreview = null;
        this.mobileBreakpoint = 768;
        
        this.init();
    }

    init() {
        console.log('🚀 Admin Frontend Interface Initialized');
        
        // Initialize core components
        this.initializeComponents();
        this.setupEventListeners();
        this.startRealTimeUpdates();
        this.initializeMobileOptimizations();
        
        // Initialize specific features
        this.initializeInlineEditing();
        this.initializeDragAndDrop();
        this.initializeThemePreview();
        this.initializeResponsiveDashboard();
    }

    // ==================== COMPONENT SYSTEM ====================
    
    initializeComponents() {
        // Register all admin components
        this.registerComponent('dashboard', new DashboardComponent());
        this.registerComponent('userManager', new UserManagerComponent());
        this.registerComponent('productManager', new ProductManagerComponent());
        this.registerComponent('contentEditor', new ContentEditorComponent());
        this.registerComponent('themeCustomizer', new ThemeCustomizerComponent());
        this.registerComponent('analyticsPanel', new AnalyticsPanelComponent());
        this.registerComponent('orderManager', new OrderManagerComponent());
        this.registerComponent('systemMonitor', new SystemMonitorComponent());
    }

    registerComponent(name, component) {
        this.components.set(name, component);
        component.init();
    }

    getComponent(name) {
        return this.components.get(name);
    }

    // ==================== REAL-TIME DASHBOARD ====================
    
    initializeResponsiveDashboard() {
        const dashboard = this.getComponent('dashboard');
        if (dashboard) {
            dashboard.setupRealTimeMetrics();
            dashboard.initializeWidgets();
            dashboard.setupResponsiveLayout();
        }
    }

    startRealTimeUpdates() {
        // Update dashboard metrics every 30 seconds
        this.realTimeUpdates.set('dashboard', setInterval(() => {
            this.updateDashboardMetrics();
        }, 30000));

        // Update notifications every 10 seconds
        this.realTimeUpdates.set('notifications', setInterval(() => {
            this.updateNotifications();
        }, 10000));

        // Update system status every 60 seconds
        this.realTimeUpdates.set('system', setInterval(() => {
            this.updateSystemStatus();
        }, 60000));
    }

    async updateDashboardMetrics() {
        try {
            const response = await fetch('/api/admin/analytics/dashboard-metrics');
            const data = await response.json();
            
            if (data.success) {
                this.getComponent('dashboard').updateMetrics(data.data);
                this.getComponent('analyticsPanel').updateCharts(data.data);
            }
        } catch (error) {
            console.error('Dashboard metrics update error:', error);
        }
    }

    async updateNotifications() {
        try {
            const response = await fetch('/api/admin/system/notifications');
            const data = await response.json();
            
            if (data.success) {
                this.displayNotifications(data.data.notifications);
            }
        } catch (error) {
            console.error('Notifications update error:', error);
        }
    }

    async updateSystemStatus() {
        try {
            const response = await fetch('/api/admin/system/status');
            const data = await response.json();
            
            if (data.success) {
                this.getComponent('systemMonitor').updateStatus(data.data);
            }
        } catch (error) {
            console.error('System status update error:', error);
        }
    }

    // ==================== INLINE EDITING ====================
    
    initializeInlineEditing() {
        // Initialize rich text editors for content management
        this.setupInlineTextEditors();
        this.setupInlineImageEditors();
        this.setupInlineConfigEditors();
    }

    setupInlineTextEditors() {
        const editableElements = document.querySelectorAll('[data-editable="text"]');
        
        editableElements.forEach(element => {
            const editor = new InlineTextEditor(element);
            this.inlineEditors.set(element.dataset.contentId, editor);
        });
    }

    setupInlineImageEditors() {
        const editableImages = document.querySelectorAll('[data-editable="image"]');
        
        editableImages.forEach(element => {
            const editor = new InlineImageEditor(element);
            this.inlineEditors.set(element.dataset.contentId, editor);
        });
    }

    setupInlineConfigEditors() {
        const configElements = document.querySelectorAll('[data-editable="config"]');
        
        configElements.forEach(element => {
            const editor = new InlineConfigEditor(element);
            this.inlineEditors.set(element.dataset.configKey, editor);
        });
    }

    // ==================== DRAG AND DROP ====================
    
    initializeDragAndDrop() {
        this.setupProductDragDrop();
        this.setupContentDragDrop();
        this.setupCategoryDragDrop();
        this.setupDashboardWidgetDragDrop();
    }

    setupProductDragDrop() {
        const productContainer = document.getElementById('product-management-container');
        if (productContainer) {
            const dragDrop = new DragDropManager(productContainer, {
                itemSelector: '.product-item',
                handleSelector: '.drag-handle',
                onDrop: this.handleProductReorder.bind(this)
            });
            this.dragDropInstances.set('products', dragDrop);
        }
    }

    setupContentDragDrop() {
        const contentContainer = document.getElementById('content-management-container');
        if (contentContainer) {
            const dragDrop = new DragDropManager(contentContainer, {
                itemSelector: '.content-block',
                handleSelector: '.drag-handle',
                onDrop: this.handleContentReorder.bind(this)
            });
            this.dragDropInstances.set('content', dragDrop);
        }
    }

    setupCategoryDragDrop() {
        const categoryTree = document.getElementById('category-tree');
        if (categoryTree) {
            const dragDrop = new TreeDragDropManager(categoryTree, {
                itemSelector: '.category-item',
                onDrop: this.handleCategoryReorder.bind(this)
            });
            this.dragDropInstances.set('categories', dragDrop);
        }
    }

    setupDashboardWidgetDragDrop() {
        const dashboardGrid = document.getElementById('dashboard-grid');
        if (dashboardGrid) {
            const dragDrop = new GridDragDropManager(dashboardGrid, {
                itemSelector: '.dashboard-widget',
                onDrop: this.handleWidgetReorder.bind(this)
            });
            this.dragDropInstances.set('widgets', dragDrop);
        }
    }

    async handleProductReorder(fromIndex, toIndex, itemId) {
        try {
            const response = await fetch('/api/admin/products/reorder', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ 
                    product_id: itemId, 
                    from_index: fromIndex, 
                    to_index: toIndex 
                })
            });
            
            const data = await response.json();
            if (!data.success) {
                this.showNotification('Failed to reorder products', 'error');
            }
        } catch (error) {
            console.error('Product reorder error:', error);
            this.showNotification('Error reordering products', 'error');
        }
    }

    async handleContentReorder(fromIndex, toIndex, itemId) {
        try {
            const response = await fetch('/api/admin/content/reorder', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ 
                    content_id: itemId, 
                    from_index: fromIndex, 
                    to_index: toIndex 
                })
            });
            
            const data = await response.json();
            if (!data.success) {
                this.showNotification('Failed to reorder content', 'error');
            }
        } catch (error) {
            console.error('Content reorder error:', error);
            this.showNotification('Error reordering content', 'error');
        }
    }

    async handleCategoryReorder(fromPath, toPath, itemId) {
        try {
            const response = await fetch('/api/admin/products/categories/reorder', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ 
                    category_id: itemId, 
                    from_path: fromPath, 
                    to_path: toPath 
                })
            });
            
            const data = await response.json();
            if (!data.success) {
                this.showNotification('Failed to reorder categories', 'error');
            }
        } catch (error) {
            console.error('Category reorder error:', error);
            this.showNotification('Error reordering categories', 'error');
        }
    }

    async handleWidgetReorder(fromIndex, toIndex, widgetId) {
        try {
            const response = await fetch('/api/admin/configuration/dashboard-layout', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ 
                    widget_id: widgetId, 
                    from_index: fromIndex, 
                    to_index: toIndex 
                })
            });
            
            const data = await response.json();
            if (!data.success) {
                this.showNotification('Failed to reorder dashboard widgets', 'error');
            }
        } catch (error) {
            console.error('Widget reorder error:', error);
            this.showNotification('Error reordering widgets', 'error');
        }
    }

    // ==================== THEME PREVIEW ====================
    
    initializeThemePreview() {
        const themeCustomizer = this.getComponent('themeCustomizer');
        if (themeCustomizer) {
            this.themePreview = new LiveThemePreview();
            themeCustomizer.setPreviewHandler(this.themePreview);
        }
    }

    // ==================== MOBILE OPTIMIZATIONS ====================
    
    initializeMobileOptimizations() {
        this.setupMobileNavigation();
        this.setupTouchGestures();
        this.setupMobileModals();
        this.optimizeForTouch();
    }

    setupMobileNavigation() {
        const mobileNav = new MobileNavigationManager();
        mobileNav.init();
    }

    setupTouchGestures() {
        const gestureHandler = new TouchGestureHandler();
        gestureHandler.init();
    }

    setupMobileModals() {
        const modalManager = new MobileModalManager();
        modalManager.init();
    }

    optimizeForTouch() {
        // Ensure all interactive elements are touch-friendly
        const interactiveElements = document.querySelectorAll('button, .btn, .clickable, [role="button"]');
        
        interactiveElements.forEach(element => {
            const rect = element.getBoundingClientRect();
            if (rect.height < 44 || rect.width < 44) {
                element.style.minHeight = '44px';
                element.style.minWidth = '44px';
                element.style.display = 'flex';
                element.style.alignItems = 'center';
                element.style.justifyContent = 'center';
            }
        });
    }

    // ==================== EVENT LISTENERS ====================
    
    setupEventListeners() {
        // Global event listeners
        document.addEventListener('click', this.handleGlobalClick.bind(this));
        document.addEventListener('keydown', this.handleGlobalKeydown.bind(this));
        window.addEventListener('resize', this.handleWindowResize.bind(this));
        window.addEventListener('orientationchange', this.handleOrientationChange.bind(this));
        
        // Visibility change for pausing/resuming updates
        document.addEventListener('visibilitychange', this.handleVisibilityChange.bind(this));
    }

    handleGlobalClick(event) {
        // Handle various click events
        const target = event.target;
        
        // Handle inline editing activation
        if (target.hasAttribute('data-editable')) {
            this.activateInlineEditor(target);
        }
        
        // Handle modal triggers
        if (target.hasAttribute('data-modal-trigger')) {
            this.openModal(target.getAttribute('data-modal-trigger'));
        }
        
        // Handle component actions
        if (target.hasAttribute('data-action')) {
            this.handleComponentAction(target);
        }
    }

    handleGlobalKeydown(event) {
        // Global keyboard shortcuts
        if (event.ctrlKey || event.metaKey) {
            switch (event.key) {
                case 's':
                    event.preventDefault();
                    this.saveCurrentChanges();
                    break;
                case 'z':
                    event.preventDefault();
                    if (event.shiftKey) {
                        this.redo();
                    } else {
                        this.undo();
                    }
                    break;
                case '/':
                    event.preventDefault();
                    this.focusSearch();
                    break;
            }
        }
        
        // Escape key handling
        if (event.key === 'Escape') {
            this.handleEscapeKey();
        }
    }

    handleWindowResize() {
        // Responsive adjustments
        const isMobile = window.innerWidth <= this.mobileBreakpoint;
        
        this.components.forEach(component => {
            if (component.handleResize) {
                component.handleResize(isMobile);
            }
        });
        
        // Adjust drag and drop for mobile
        this.dragDropInstances.forEach(instance => {
            instance.setMobileMode(isMobile);
        });
    }

    handleOrientationChange() {
        setTimeout(() => {
            this.handleWindowResize();
        }, 100);
    }

    handleVisibilityChange() {
        if (document.hidden) {
            // Pause real-time updates when page is not visible
            this.pauseRealTimeUpdates();
        } else {
            // Resume updates when page becomes visible
            this.resumeRealTimeUpdates();
        }
    }

    // ==================== UTILITY METHODS ====================
    
    activateInlineEditor(element) {
        const contentId = element.dataset.contentId || element.dataset.configKey;
        const editor = this.inlineEditors.get(contentId);
        
        if (editor) {
            editor.activate();
        }
    }

    openModal(modalId) {
        const modal = document.getElementById(modalId);
        if (modal) {
            modal.classList.add('show');
            document.body.style.overflow = 'hidden';
        }
    }

    handleComponentAction(element) {
        const action = element.getAttribute('data-action');
        const component = element.getAttribute('data-component');
        
        if (component && this.components.has(component)) {
            const comp = this.components.get(component);
            if (comp[action]) {
                comp[action](element);
            }
        }
    }

    saveCurrentChanges() {
        // Save all pending changes
        this.inlineEditors.forEach(editor => {
            if (editor.hasChanges()) {
                editor.save();
            }
        });
        
        this.showNotification('Changes saved successfully', 'success');
    }

    undo() {
        // Implement undo functionality
        console.log('Undo action');
    }

    redo() {
        // Implement redo functionality
        console.log('Redo action');
    }

    focusSearch() {
        const searchInput = document.querySelector('.admin-search-input');
        if (searchInput) {
            searchInput.focus();
        }
    }

    handleEscapeKey() {
        // Close modals, cancel inline editing, etc.
        const activeModal = document.querySelector('.modal.show');
        if (activeModal) {
            activeModal.classList.remove('show');
            document.body.style.overflow = '';
        }
        
        // Cancel active inline editors
        this.inlineEditors.forEach(editor => {
            if (editor.isActive()) {
                editor.cancel();
            }
        });
    }

    pauseRealTimeUpdates() {
        this.realTimeUpdates.forEach((interval, key) => {
            clearInterval(interval);
        });
    }

    resumeRealTimeUpdates() {
        this.startRealTimeUpdates();
    }

    showNotification(message, type = 'info', duration = 3000) {
        const notification = document.createElement('div');
        notification.className = `admin-notification admin-notification-${type}`;
        notification.innerHTML = `
            <div class="admin-notification-content">
                <span class="admin-notification-message">${message}</span>
                <button class="admin-notification-close" onclick="this.parentElement.parentElement.remove()">×</button>
            </div>
        `;
        
        let container = document.getElementById('admin-notification-container');
        if (!container) {
            container = document.createElement('div');
            container.id = 'admin-notification-container';
            container.className = 'admin-notification-container';
            document.body.appendChild(container);
        }
        
        container.appendChild(notification);
        
        // Animate in
        setTimeout(() => {
            notification.classList.add('show');
        }, 100);
        
        // Auto remove
        if (duration > 0) {
            setTimeout(() => {
                notification.classList.add('hide');
                setTimeout(() => {
                    if (notification.parentNode) {
                        notification.parentNode.removeChild(notification);
                    }
                }, 300);
            }, duration);
        }
    }

    displayNotifications(notifications) {
        const notificationPanel = document.getElementById('notification-panel');
        if (notificationPanel && notifications.length > 0) {
            notifications.forEach(notification => {
                this.showNotification(notification.message, notification.type, 0);
            });
        }
    }

    // ==================== PUBLIC API ====================
    
    getComponentAPI() {
        return {
            dashboard: this.getComponent('dashboard'),
            userManager: this.getComponent('userManager'),
            productManager: this.getComponent('productManager'),
            contentEditor: this.getComponent('contentEditor'),
            themeCustomizer: this.getComponent('themeCustomizer'),
            analyticsPanel: this.getComponent('analyticsPanel'),
            orderManager: this.getComponent('orderManager'),
            systemMonitor: this.getComponent('systemMonitor')
        };
    }

    destroy() {
        // Cleanup when interface is destroyed
        this.pauseRealTimeUpdates();
        
        this.components.forEach(component => {
            if (component.destroy) {
                component.destroy();
            }
        });
        
        this.dragDropInstances.forEach(instance => {
            instance.destroy();
        });
        
        this.inlineEditors.forEach(editor => {
            editor.destroy();
        });
    }
}

// Initialize the admin frontend interface when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    if (document.body.classList.contains('admin-page')) {
        window.adminInterface = new AdminFrontendInterface();
    }
});

// Export for use in other scripts
if (typeof module !== 'undefined' && module.exports) {
    module.exports = AdminFrontendInterface;
}