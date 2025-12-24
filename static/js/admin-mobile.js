/**
 * Mobile-Optimized Admin Interface Components
 * Provides touch-friendly interfaces and mobile-specific functionality
 */

// ==================== MOBILE NAVIGATION MANAGER ====================

class MobileNavigationManager {
    constructor() {
        this.isMenuOpen = false;
        this.mobileBreakpoint = 768;
        this.touchStartX = 0;
        this.touchStartY = 0;
        this.swipeThreshold = 50;
        
        this.init();
    }

    init() {
        this.createMobileMenu();
        this.setupEventListeners();
        this.handleResize();
    }

    createMobileMenu() {
        // Check if mobile menu already exists
        if (document.getElementById('mobile-admin-menu')) return;

        const mobileMenu = document.createElement('div');
        mobileMenu.id = 'mobile-admin-menu';
        mobileMenu.className = 'mobile-admin-menu';
        mobileMenu.innerHTML = `
            <div class="mobile-menu-overlay"></div>
            <div class="mobile-menu-content">
                <div class="mobile-menu-header">
                    <h3>Admin Menu</h3>
                    <button class="mobile-menu-close" type="button">
                        <i class="icon-x"></i>
                    </button>
                </div>
                
                <div class="mobile-menu-body">
                    <nav class="mobile-nav">
                        <a href="/admin/dashboard" class="mobile-nav-item">
                            <i class="icon-home"></i>
                            <span>Dashboard</span>
                        </a>
                        <a href="/admin/users" class="mobile-nav-item">
                            <i class="icon-users"></i>
                            <span>Users</span>
                        </a>
                        <a href="/admin/products" class="mobile-nav-item">
                            <i class="icon-package"></i>
                            <span>Products</span>
                        </a>
                        <a href="/admin/orders" class="mobile-nav-item">
                            <i class="icon-shopping-cart"></i>
                            <span>Orders</span>
                        </a>
                        <a href="/admin/content" class="mobile-nav-item">
                            <i class="icon-edit"></i>
                            <span>Content</span>
                        </a>
                        <a href="/admin/theme" class="mobile-nav-item">
                            <i class="icon-palette"></i>
                            <span>Theme</span>
                        </a>
                        <a href="/admin/analytics" class="mobile-nav-item">
                            <i class="icon-bar-chart"></i>
                            <span>Analytics</span>
                        </a>
                        <a href="/admin/settings" class="mobile-nav-item">
                            <i class="icon-settings"></i>
                            <span>Settings</span>
                        </a>
                    </nav>
                </div>
                
                <div class="mobile-menu-footer">
                    <div class="admin-user-info">
                        <div class="user-avatar">
                            <i class="icon-user"></i>
                        </div>
                        <div class="user-details">
                            <div class="user-name">Admin User</div>
                            <div class="user-role">Administrator</div>
                        </div>
                    </div>
                    <button class="btn btn-secondary btn-sm logout-btn">
                        <i class="icon-log-out"></i> Logout
                    </button>
                </div>
            </div>
        `;

        document.body.appendChild(mobileMenu);
    }

    setupEventListeners() {
        // Menu toggle button
        document.addEventListener('click', (e) => {
            if (e.target.matches('.mobile-menu-toggle, .mobile-menu-toggle *')) {
                this.toggleMenu();
            }
            
            if (e.target.matches('.mobile-menu-close, .mobile-menu-overlay')) {
                this.closeMenu();
            }
        });

        // Swipe gestures
        document.addEventListener('touchstart', this.handleTouchStart.bind(this), { passive: true });
        document.addEventListener('touchmove', this.handleTouchMove.bind(this), { passive: true });
        document.addEventListener('touchend', this.handleTouchEnd.bind(this), { passive: true });

        // Window resize
        window.addEventListener('resize', this.handleResize.bind(this));

        // Escape key
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && this.isMenuOpen) {
                this.closeMenu();
            }
        });
    }

    handleTouchStart(e) {
        if (e.touches.length !== 1) return;
        
        const touch = e.touches[0];
        this.touchStartX = touch.clientX;
        this.touchStartY = touch.clientY;
    }

    handleTouchMove(e) {
        if (!this.touchStartX || !this.touchStartY) return;
        if (e.touches.length !== 1) return;

        const touch = e.touches[0];
        const deltaX = touch.clientX - this.touchStartX;
        const deltaY = touch.clientY - this.touchStartY;

        // Only handle horizontal swipes
        if (Math.abs(deltaY) > Math.abs(deltaX)) return;

        // Swipe from left edge to open menu
        if (this.touchStartX < 20 && deltaX > this.swipeThreshold && !this.isMenuOpen) {
            this.openMenu();
        }
        
        // Swipe right to close menu
        if (this.isMenuOpen && deltaX < -this.swipeThreshold) {
            this.closeMenu();
        }
    }

    handleTouchEnd() {
        this.touchStartX = 0;
        this.touchStartY = 0;
    }

    handleResize() {
        const isMobile = window.innerWidth <= this.mobileBreakpoint;
        
        if (!isMobile && this.isMenuOpen) {
            this.closeMenu();
        }
        
        // Update body class for mobile styles
        if (isMobile) {
            document.body.classList.add('mobile-admin');
        } else {
            document.body.classList.remove('mobile-admin');
        }
    }

    toggleMenu() {
        if (this.isMenuOpen) {
            this.closeMenu();
        } else {
            this.openMenu();
        }
    }

    openMenu() {
        const menu = document.getElementById('mobile-admin-menu');
        if (!menu) return;

        this.isMenuOpen = true;
        menu.classList.add('open');
        document.body.style.overflow = 'hidden';
        
        // Focus trap
        const firstFocusable = menu.querySelector('.mobile-menu-close');
        if (firstFocusable) {
            firstFocusable.focus();
        }
    }

    closeMenu() {
        const menu = document.getElementById('mobile-admin-menu');
        if (!menu) return;

        this.isMenuOpen = false;
        menu.classList.remove('open');
        document.body.style.overflow = '';
    }
}

// ==================== TOUCH GESTURE HANDLER ====================

class TouchGestureHandler {
    constructor() {
        this.gestures = new Map();
        this.activeGestures = new Map();
        
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.registerDefaultGestures();
    }

    setupEventListeners() {
        document.addEventListener('touchstart', this.handleTouchStart.bind(this), { passive: false });
        document.addEventListener('touchmove', this.handleTouchMove.bind(this), { passive: false });
        document.addEventListener('touchend', this.handleTouchEnd.bind(this), { passive: false });
    }

    registerDefaultGestures() {
        // Pull to refresh
        this.registerGesture('pullToRefresh', {
            element: '.admin-content',
            direction: 'down',
            threshold: 100,
            callback: this.handlePullToRefresh.bind(this)
        });

        // Swipe to delete
        this.registerGesture('swipeToDelete', {
            element: '.list-item, .table-row',
            direction: 'left',
            threshold: 80,
            callback: this.handleSwipeToDelete.bind(this)
        });

        // Long press for context menu
        this.registerGesture('longPress', {
            element: '.admin-item',
            duration: 500,
            callback: this.handleLongPress.bind(this)
        });
    }

    registerGesture(name, config) {
        this.gestures.set(name, config);
    }

    handleTouchStart(e) {
        const touch = e.touches[0];
        const element = e.target;
        
        // Check for applicable gestures
        this.gestures.forEach((config, name) => {
            if (element.matches(config.element) || element.closest(config.element)) {
                this.activeGestures.set(name, {
                    config,
                    element: element.closest(config.element) || element,
                    startX: touch.clientX,
                    startY: touch.clientY,
                    startTime: Date.now(),
                    moved: false
                });
                
                // Start long press timer if applicable
                if (config.duration) {
                    setTimeout(() => {
                        const gesture = this.activeGestures.get(name);
                        if (gesture && !gesture.moved) {
                            config.callback(gesture.element, 'longpress');
                            this.activeGestures.delete(name);
                        }
                    }, config.duration);
                }
            }
        });
    }

    handleTouchMove(e) {
        if (e.touches.length !== 1) return;
        
        const touch = e.touches[0];
        
        this.activeGestures.forEach((gesture, name) => {
            const deltaX = touch.clientX - gesture.startX;
            const deltaY = touch.clientY - gesture.startY;
            
            gesture.moved = Math.abs(deltaX) > 5 || Math.abs(deltaY) > 5;
            gesture.deltaX = deltaX;
            gesture.deltaY = deltaY;
            
            // Handle pull to refresh visual feedback
            if (name === 'pullToRefresh' && deltaY > 0) {
                this.updatePullToRefreshIndicator(gesture.element, deltaY);
            }
            
            // Handle swipe visual feedback
            if (name === 'swipeToDelete' && deltaX < 0) {
                this.updateSwipeToDeleteIndicator(gesture.element, deltaX);
            }
        });
    }

    handleTouchEnd(e) {
        this.activeGestures.forEach((gesture, name) => {
            const config = gesture.config;
            
            // Check if gesture threshold was met
            if (config.direction && config.threshold) {
                let thresholdMet = false;
                
                switch (config.direction) {
                    case 'left':
                        thresholdMet = gesture.deltaX < -config.threshold;
                        break;
                    case 'right':
                        thresholdMet = gesture.deltaX > config.threshold;
                        break;
                    case 'up':
                        thresholdMet = gesture.deltaY < -config.threshold;
                        break;
                    case 'down':
                        thresholdMet = gesture.deltaY > config.threshold;
                        break;
                }
                
                if (thresholdMet) {
                    config.callback(gesture.element, config.direction);
                } else {
                    // Reset visual feedback
                    this.resetGestureIndicator(gesture.element, name);
                }
            }
        });
        
        this.activeGestures.clear();
    }

    updatePullToRefreshIndicator(element, deltaY) {
        let indicator = element.querySelector('.pull-to-refresh-indicator');
        
        if (!indicator) {
            indicator = document.createElement('div');
            indicator.className = 'pull-to-refresh-indicator';
            indicator.innerHTML = '<i class="icon-refresh"></i><span>Pull to refresh</span>';
            element.insertBefore(indicator, element.firstChild);
        }
        
        const progress = Math.min(deltaY / 100, 1);
        indicator.style.transform = `translateY(${deltaY * 0.5}px) scale(${progress})`;
        indicator.style.opacity = progress;
        
        if (progress >= 1) {
            indicator.querySelector('span').textContent = 'Release to refresh';
            indicator.classList.add('ready');
        } else {
            indicator.querySelector('span').textContent = 'Pull to refresh';
            indicator.classList.remove('ready');
        }
    }

    updateSwipeToDeleteIndicator(element, deltaX) {
        let deleteAction = element.querySelector('.swipe-delete-action');
        
        if (!deleteAction) {
            deleteAction = document.createElement('div');
            deleteAction.className = 'swipe-delete-action';
            deleteAction.innerHTML = '<i class="icon-trash"></i>';
            element.appendChild(deleteAction);
        }
        
        const progress = Math.min(Math.abs(deltaX) / 80, 1);
        element.style.transform = `translateX(${deltaX}px)`;
        deleteAction.style.opacity = progress;
        
        if (progress >= 1) {
            deleteAction.classList.add('ready');
        } else {
            deleteAction.classList.remove('ready');
        }
    }

    resetGestureIndicator(element, gestureName) {
        switch (gestureName) {
            case 'pullToRefresh':
                const indicator = element.querySelector('.pull-to-refresh-indicator');
                if (indicator) {
                    indicator.style.transform = 'translateY(-100px) scale(0)';
                    indicator.style.opacity = '0';
                    setTimeout(() => {
                        if (indicator.parentNode) {
                            indicator.parentNode.removeChild(indicator);
                        }
                    }, 300);
                }
                break;
                
            case 'swipeToDelete':
                element.style.transform = '';
                const deleteAction = element.querySelector('.swipe-delete-action');
                if (deleteAction) {
                    deleteAction.style.opacity = '0';
                    setTimeout(() => {
                        if (deleteAction.parentNode) {
                            deleteAction.parentNode.removeChild(deleteAction);
                        }
                    }, 300);
                }
                break;
        }
    }

    handlePullToRefresh(element) {
        // Trigger refresh
        if (window.adminInterface) {
            window.adminInterface.updateDashboardMetrics();
        }
        
        // Show loading state
        const indicator = element.querySelector('.pull-to-refresh-indicator');
        if (indicator) {
            indicator.innerHTML = '<i class="icon-refresh spinning"></i><span>Refreshing...</span>';
            
            setTimeout(() => {
                this.resetGestureIndicator(element, 'pullToRefresh');
            }, 2000);
        }
    }

    handleSwipeToDelete(element) {
        if (confirm('Are you sure you want to delete this item?')) {
            element.style.transform = 'translateX(-100%)';
            element.style.opacity = '0';
            
            setTimeout(() => {
                if (element.parentNode) {
                    element.parentNode.removeChild(element);
                }
            }, 300);
            
            // Trigger delete API call
            const itemId = element.dataset.itemId || element.dataset.id;
            if (itemId) {
                this.deleteItem(itemId);
            }
        } else {
            this.resetGestureIndicator(element, 'swipeToDelete');
        }
    }

    handleLongPress(element) {
        // Show context menu
        this.showContextMenu(element);
    }

    showContextMenu(element) {
        const contextMenu = document.createElement('div');
        contextMenu.className = 'mobile-context-menu';
        contextMenu.innerHTML = `
            <div class="context-menu-overlay"></div>
            <div class="context-menu-content">
                <div class="context-menu-header">
                    <h4>Actions</h4>
                    <button class="context-menu-close">×</button>
                </div>
                <div class="context-menu-actions">
                    <button class="context-action" data-action="edit">
                        <i class="icon-edit"></i> Edit
                    </button>
                    <button class="context-action" data-action="duplicate">
                        <i class="icon-copy"></i> Duplicate
                    </button>
                    <button class="context-action" data-action="delete">
                        <i class="icon-trash"></i> Delete
                    </button>
                </div>
            </div>
        `;
        
        document.body.appendChild(contextMenu);
        
        // Show menu
        setTimeout(() => {
            contextMenu.classList.add('show');
        }, 100);
        
        // Handle actions
        contextMenu.addEventListener('click', (e) => {
            if (e.target.matches('.context-menu-close, .context-menu-overlay')) {
                this.closeContextMenu(contextMenu);
            }
            
            const action = e.target.closest('.context-action');
            if (action) {
                this.handleContextAction(element, action.dataset.action);
                this.closeContextMenu(contextMenu);
            }
        });
    }

    closeContextMenu(menu) {
        menu.classList.remove('show');
        setTimeout(() => {
            if (menu.parentNode) {
                menu.parentNode.removeChild(menu);
            }
        }, 300);
    }

    handleContextAction(element, action) {
        const itemId = element.dataset.itemId || element.dataset.id;
        
        switch (action) {
            case 'edit':
                // Trigger edit action
                console.log('Edit item:', itemId);
                break;
            case 'duplicate':
                // Trigger duplicate action
                console.log('Duplicate item:', itemId);
                break;
            case 'delete':
                if (confirm('Are you sure you want to delete this item?')) {
                    this.deleteItem(itemId);
                }
                break;
        }
    }

    async deleteItem(itemId) {
        try {
            const response = await fetch(`/api/admin/items/${itemId}`, {
                method: 'DELETE'
            });
            
            const data = await response.json();
            
            if (data.success) {
                // Remove from DOM
                const element = document.querySelector(`[data-item-id="${itemId}"], [data-id="${itemId}"]`);
                if (element) {
                    element.style.transform = 'translateX(-100%)';
                    element.style.opacity = '0';
                    
                    setTimeout(() => {
                        if (element.parentNode) {
                            element.parentNode.removeChild(element);
                        }
                    }, 300);
                }
            }
        } catch (error) {
            console.error('Delete error:', error);
        }
    }
}

// ==================== MOBILE MODAL MANAGER ====================

class MobileModalManager {
    constructor() {
        this.activeModal = null;
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.optimizeExistingModals();
    }

    setupEventListeners() {
        document.addEventListener('click', (e) => {
            if (e.target.matches('[data-mobile-modal]')) {
                const modalId = e.target.getAttribute('data-mobile-modal');
                this.openModal(modalId);
            }
        });
    }

    optimizeExistingModals() {
        const modals = document.querySelectorAll('.modal');
        
        modals.forEach(modal => {
            this.makeMobileFriendly(modal);
        });
    }

    makeMobileFriendly(modal) {
        // Add mobile class
        modal.classList.add('mobile-optimized');
        
        // Ensure proper viewport handling
        const modalContent = modal.querySelector('.modal-content');
        if (modalContent) {
            modalContent.style.maxHeight = '90vh';
            modalContent.style.overflowY = 'auto';
        }
        
        // Add swipe to close functionality
        this.addSwipeToClose(modal);
        
        // Optimize form inputs
        const inputs = modal.querySelectorAll('input, textarea, select');
        inputs.forEach(input => {
            this.optimizeInput(input);
        });
    }

    addSwipeToClose(modal) {
        let startY = 0;
        let currentY = 0;
        let isDragging = false;
        
        const modalContent = modal.querySelector('.modal-content');
        if (!modalContent) return;
        
        modalContent.addEventListener('touchstart', (e) => {
            startY = e.touches[0].clientY;
            isDragging = true;
        }, { passive: true });
        
        modalContent.addEventListener('touchmove', (e) => {
            if (!isDragging) return;
            
            currentY = e.touches[0].clientY;
            const deltaY = currentY - startY;
            
            // Only allow downward swipes
            if (deltaY > 0) {
                modalContent.style.transform = `translateY(${deltaY}px)`;
                modalContent.style.opacity = 1 - (deltaY / 300);
            }
        }, { passive: true });
        
        modalContent.addEventListener('touchend', () => {
            if (!isDragging) return;
            
            const deltaY = currentY - startY;
            
            if (deltaY > 100) {
                // Close modal
                this.closeModal(modal);
            } else {
                // Snap back
                modalContent.style.transform = '';
                modalContent.style.opacity = '';
            }
            
            isDragging = false;
        }, { passive: true });
    }

    optimizeInput(input) {
        // Add appropriate input modes for mobile keyboards
        switch (input.type) {
            case 'email':
                input.setAttribute('inputmode', 'email');
                break;
            case 'tel':
                input.setAttribute('inputmode', 'tel');
                break;
            case 'number':
                input.setAttribute('inputmode', 'numeric');
                break;
            case 'url':
                input.setAttribute('inputmode', 'url');
                break;
        }
        
        // Ensure minimum touch target size
        const rect = input.getBoundingClientRect();
        if (rect.height < 44) {
            input.style.minHeight = '44px';
            input.style.padding = '12px';
        }
    }

    openModal(modalId) {
        const modal = document.getElementById(modalId);
        if (!modal) return;
        
        this.activeModal = modal;
        this.makeMobileFriendly(modal);
        
        modal.classList.add('show');
        document.body.style.overflow = 'hidden';
        
        // Focus first input
        const firstInput = modal.querySelector('input, textarea, select');
        if (firstInput) {
            setTimeout(() => {
                firstInput.focus();
            }, 300);
        }
    }

    closeModal(modal) {
        if (!modal) modal = this.activeModal;
        if (!modal) return;
        
        modal.classList.remove('show');
        document.body.style.overflow = '';
        
        // Reset transforms
        const modalContent = modal.querySelector('.modal-content');
        if (modalContent) {
            modalContent.style.transform = '';
            modalContent.style.opacity = '';
        }
        
        this.activeModal = null;
    }
}

// Export mobile components
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        MobileNavigationManager,
        TouchGestureHandler,
        MobileModalManager
    };
}