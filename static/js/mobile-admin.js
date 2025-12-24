/**
 * Mobile Admin Interface JavaScript
 * Handles touch interactions, push notifications, and mobile-specific functionality
 */

class MobileAdminInterface {
    constructor() {
        this.touchStartX = 0;
        this.touchStartY = 0;
        this.touchStartTime = 0;
        this.longPressTimer = null;
        this.swipeThreshold = 50;
        this.longPressDelay = 500;
        this.notifications = [];
        this.isOnline = navigator.onLine;
        
        this.init();
    }
    
    init() {
        this.setupTouchHandlers();
        this.setupPushNotifications();
        this.setupOfflineHandling();
        this.setupOrientationHandling();
        this.setupKeyboardHandling();
        this.preventZoom();
        this.setupHapticFeedback();
    }
    
    // ==================== TOUCH INTERACTION HANDLING ====================
    
    setupTouchHandlers() {
        // Touch event listeners
        document.addEventListener('touchstart', this.handleTouchStart.bind(this), { passive: false });
        document.addEventListener('touchmove', this.handleTouchMove.bind(this), { passive: false });
        document.addEventListener('touchend', this.handleTouchEnd.bind(this), { passive: false });
        
        // Prevent context menu on long press for better UX
        document.addEventListener('contextmenu', (e) => {
            if (e.target.closest('.mobile-admin-content')) {
                e.preventDefault();
            }
        });
    }
    
    handleTouchStart(e) {
        const touch = e.touches[0];
        this.touchStartX = touch.clientX;
        this.touchStartY = touch.clientY;
        this.touchStartTime = Date.now();
        
        // Setup long press detection
        this.longPressTimer = setTimeout(() => {
            this.handleLongPress(e);
        }, this.longPressDelay);
    }
    
    handleTouchMove(e) {
        // Cancel long press if user moves finger
        if (this.longPressTimer) {
            clearTimeout(this.longPressTimer);
            this.longPressTimer = null;
        }
        
        // Handle pull-to-refresh
        if (window.scrollY === 0 && e.touches[0].clientY > this.touchStartY + 50) {
            this.handlePullToRefresh();
        }
    }
    
    handleTouchEnd(e) {
        if (this.longPressTimer) {
            clearTimeout(this.longPressTimer);
            this.longPressTimer = null;
        }
        
        if (!this.touchStartX || !this.touchStartY) return;
        
        const touch = e.changedTouches[0];
        const touchEndX = touch.clientX;
        const touchEndY = touch.clientY;
        const touchDuration = Date.now() - this.touchStartTime;
        
        const diffX = this.touchStartX - touchEndX;
        const diffY = this.touchStartY - touchEndY;
        
        // Detect swipe gestures
        if (Math.abs(diffX) > Math.abs(diffY) && Math.abs(diffX) > this.swipeThreshold) {
            if (diffX > 0) {
                this.handleSwipeLeft(e);
            } else {
                this.handleSwipeRight(e);
            }
        } else if (Math.abs(diffY) > this.swipeThreshold) {
            if (diffY > 0) {
                this.handleSwipeUp(e);
            } else {
                this.handleSwipeDown(e);
            }
        }
        
        // Reset touch coordinates
        this.touchStartX = 0;
        this.touchStartY = 0;
        this.touchStartTime = 0;
    }
    
    handleLongPress(e) {
        const target = e.target.closest('[data-long-press]');
        if (target) {
            this.triggerHapticFeedback('medium');
            const action = target.dataset.longPress;
            this.executeLongPressAction(action, target);
        }
    }
    
    handleSwipeLeft(e) {
        const target = e.target.closest('[data-swipe-left]');
        if (target) {
            const action = target.dataset.swipeLeft;
            this.executeSwipeAction(action, target, 'left');
        }
    }
    
    handleSwipeRight(e) {
        const target = e.target.closest('[data-swipe-right]');
        if (target) {
            const action = target.dataset.swipeRight;
            this.executeSwipeAction(action, target, 'right');
        }
        
        // Global swipe right to go back
        if (window.history.length > 1) {
            this.showBackConfirmation();
        }
    }
    
    handleSwipeUp(e) {
        // Swipe up to show more options
        const moreMenu = document.querySelector('.mobile-more-menu');
        if (moreMenu) {
            this.showMoreMenu();
        }
    }
    
    handleSwipeDown(e) {
        // Swipe down to refresh or close modals
        const modal = document.querySelector('.mobile-modal.active');
        if (modal) {
            this.closeModal(modal);
        } else if (window.scrollY === 0) {
            this.handlePullToRefresh();
        }
    }
    
    // ==================== PUSH NOTIFICATIONS ====================
    
    async setupPushNotifications() {
        if ('serviceWorker' in navigator && 'PushManager' in window) {
            try {
                const registration = await navigator.serviceWorker.register('/sw.js');
                console.log('Service Worker registered:', registration);
                
                const permission = await this.requestNotificationPermission();
                if (permission === 'granted') {
                    await this.subscribeToPushNotifications(registration);
                }
            } catch (error) {
                console.error('Service Worker registration failed:', error);
            }
        }
    }
    
    async requestNotificationPermission() {
        if ('Notification' in window) {
            const permission = await Notification.requestPermission();
            return permission;
        }
        return 'denied';
    }
    
    async subscribeToPushNotifications(registration) {
        try {
            const subscription = await registration.pushManager.subscribe({
                userVisibleOnly: true,
                applicationServerKey: this.urlBase64ToUint8Array(this.getVapidPublicKey())
            });
            
            // Send subscription to server
            await this.sendSubscriptionToServer(subscription);
        } catch (error) {
            console.error('Push subscription failed:', error);
        }
    }
    
    async sendSubscriptionToServer(subscription) {
        try {
            const response = await fetch('/api/admin/push-subscription', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(subscription)
            });
            
            if (!response.ok) {
                throw new Error('Failed to send subscription to server');
            }
        } catch (error) {
            console.error('Failed to send subscription:', error);
        }
    }
    
    showLocalNotification(title, options = {}) {
        if ('Notification' in window && Notification.permission === 'granted') {
            const notification = new Notification(title, {
                icon: '/static/images/favicon-32x32.png',
                badge: '/static/images/favicon-16x16.png',
                vibrate: [200, 100, 200],
                ...options
            });
            
            notification.onclick = () => {
                window.focus();
                if (options.url) {
                    window.location.href = options.url;
                }
                notification.close();
            };
            
            // Auto-close after 5 seconds
            setTimeout(() => notification.close(), 5000);
        }
    }
    
    // ==================== OFFLINE HANDLING ====================
    
    setupOfflineHandling() {
        window.addEventListener('online', () => {
            this.isOnline = true;
            this.showNotification('Connection restored', { type: 'success' });
            this.syncOfflineData();
        });
        
        window.addEventListener('offline', () => {
            this.isOnline = false;
            this.showNotification('You are offline', { type: 'warning' });
        });
    }
    
    async syncOfflineData() {
        // Sync any offline data when connection is restored
        const offlineData = this.getOfflineData();
        if (offlineData.length > 0) {
            try {
                await this.uploadOfflineData(offlineData);
                this.clearOfflineData();
                this.showNotification('Data synced successfully', { type: 'success' });
            } catch (error) {
                console.error('Failed to sync offline data:', error);
                this.showNotification('Failed to sync data', { type: 'error' });
            }
        }
    }
    
    // ==================== ORIENTATION HANDLING ====================
    
    setupOrientationHandling() {
        window.addEventListener('orientationchange', () => {
            setTimeout(() => {
                this.handleOrientationChange();
            }, 100);
        });
        
        // Also listen for resize events
        window.addEventListener('resize', this.debounce(() => {
            this.handleOrientationChange();
        }, 250));
    }
    
    handleOrientationChange() {
        // Adjust layout based on orientation
        const isLandscape = window.innerWidth > window.innerHeight;
        document.body.classList.toggle('landscape', isLandscape);
        
        // Scroll to top to prevent layout issues
        window.scrollTo(0, 0);
        
        // Adjust grid layouts
        this.adjustGridLayouts(isLandscape);
    }
    
    adjustGridLayouts(isLandscape) {
        const statsGrid = document.querySelector('.mobile-stats-grid');
        if (statsGrid && window.innerHeight < 500 && isLandscape) {
            statsGrid.style.gridTemplateColumns = 'repeat(4, 1fr)';
        } else if (statsGrid) {
            statsGrid.style.gridTemplateColumns = '';
        }
    }
    
    // ==================== KEYBOARD HANDLING ====================
    
    setupKeyboardHandling() {
        // Handle virtual keyboard on mobile
        let initialViewportHeight = window.innerHeight;
        
        window.addEventListener('resize', () => {
            const currentHeight = window.innerHeight;
            const heightDifference = initialViewportHeight - currentHeight;
            
            // If height decreased significantly, keyboard is likely open
            if (heightDifference > 150) {
                document.body.classList.add('keyboard-open');
                this.adjustForKeyboard(true);
            } else {
                document.body.classList.remove('keyboard-open');
                this.adjustForKeyboard(false);
            }
        });
    }
    
    adjustForKeyboard(isOpen) {
        const bottomNav = document.querySelector('.mobile-bottom-nav');
        if (bottomNav) {
            bottomNav.style.display = isOpen ? 'none' : 'flex';
        }
        
        // Scroll active input into view
        if (isOpen) {
            const activeInput = document.activeElement;
            if (activeInput && activeInput.tagName === 'INPUT') {
                setTimeout(() => {
                    activeInput.scrollIntoView({ behavior: 'smooth', block: 'center' });
                }, 300);
            }
        }
    }
    
    // ==================== UTILITY FUNCTIONS ====================
    
    preventZoom() {
        // Prevent zoom on double tap
        let lastTouchEnd = 0;
        document.addEventListener('touchend', (event) => {
            const now = Date.now();
            if (now - lastTouchEnd <= 300) {
                event.preventDefault();
            }
            lastTouchEnd = now;
        }, false);
        
        // Prevent pinch zoom
        document.addEventListener('gesturestart', (e) => e.preventDefault());
        document.addEventListener('gesturechange', (e) => e.preventDefault());
    }
    
    setupHapticFeedback() {
        // Check if device supports haptic feedback
        this.hasHapticFeedback = 'vibrate' in navigator;
    }
    
    triggerHapticFeedback(intensity = 'light') {
        if (!this.hasHapticFeedback) return;
        
        const patterns = {
            light: [10],
            medium: [20],
            heavy: [30],
            success: [10, 50, 10],
            error: [50, 50, 50]
        };
        
        navigator.vibrate(patterns[intensity] || patterns.light);
    }
    
    showNotification(message, options = {}) {
        const notification = document.createElement('div');
        notification.className = `mobile-notification ${options.type || 'info'}`;
        
        notification.innerHTML = `
            <div class="mobile-notification-content">
                <div class="mobile-notification-icon">
                    ${this.getNotificationIcon(options.type)}
                </div>
                <div class="mobile-notification-text">
                    <div class="mobile-notification-title">${options.title || 'Notification'}</div>
                    <div class="mobile-notification-message">${message}</div>
                </div>
            </div>
        `;
        
        document.body.appendChild(notification);
        
        // Animate in
        setTimeout(() => notification.classList.add('show'), 100);
        
        // Auto-remove
        setTimeout(() => {
            notification.classList.remove('show');
            setTimeout(() => notification.remove(), 300);
        }, options.duration || 3000);
    }
    
    getNotificationIcon(type) {
        const icons = {
            success: '✅',
            error: '❌',
            warning: '⚠️',
            info: 'ℹ️'
        };
        return icons[type] || icons.info;
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
    
    urlBase64ToUint8Array(base64String) {
        const padding = '='.repeat((4 - base64String.length % 4) % 4);
        const base64 = (base64String + padding)
            .replace(/-/g, '+')
            .replace(/_/g, '/');
        
        const rawData = window.atob(base64);
        const outputArray = new Uint8Array(rawData.length);
        
        for (let i = 0; i < rawData.length; ++i) {
            outputArray[i] = rawData.charCodeAt(i);
        }
        return outputArray;
    }
    
    getVapidPublicKey() {
        // This should be your VAPID public key
        return 'YOUR_VAPID_PUBLIC_KEY_HERE';
    }
    
    // ==================== ACTION HANDLERS ====================
    
    executeLongPressAction(action, target) {
        switch (action) {
            case 'context-menu':
                this.showContextMenu(target);
                break;
            case 'quick-edit':
                this.showQuickEdit(target);
                break;
            case 'bulk-select':
                this.toggleBulkSelect(target);
                break;
            default:
                console.log('Long press action:', action);
        }
    }
    
    executeSwipeAction(action, target, direction) {
        switch (action) {
            case 'delete':
                this.showDeleteConfirmation(target);
                break;
            case 'archive':
                this.archiveItem(target);
                break;
            case 'mark-read':
                this.markAsRead(target);
                break;
            default:
                console.log('Swipe action:', action, direction);
        }
    }
    
    showContextMenu(target) {
        // Implementation for context menu
        console.log('Showing context menu for:', target);
    }
    
    showQuickEdit(target) {
        // Implementation for quick edit
        console.log('Showing quick edit for:', target);
    }
    
    toggleBulkSelect(target) {
        // Implementation for bulk select
        console.log('Toggling bulk select for:', target);
    }
    
    showDeleteConfirmation(target) {
        // Implementation for delete confirmation
        console.log('Showing delete confirmation for:', target);
    }
    
    archiveItem(target) {
        // Implementation for archiving
        console.log('Archiving item:', target);
    }
    
    markAsRead(target) {
        // Implementation for mark as read
        console.log('Marking as read:', target);
    }
    
    handlePullToRefresh() {
        // Implementation for pull to refresh
        console.log('Pull to refresh triggered');
        window.location.reload();
    }
    
    showBackConfirmation() {
        if (confirm('Go back to previous page?')) {
            window.history.back();
        }
    }
    
    showMoreMenu() {
        // Implementation for more menu
        console.log('Showing more menu');
    }
    
    closeModal(modal) {
        modal.classList.remove('active');
    }
    
    // ==================== OFFLINE DATA MANAGEMENT ====================
    
    getOfflineData() {
        const data = localStorage.getItem('mobileAdminOfflineData');
        return data ? JSON.parse(data) : [];
    }
    
    saveOfflineData(data) {
        const existingData = this.getOfflineData();
        existingData.push({
            ...data,
            timestamp: Date.now(),
            id: Date.now().toString()
        });
        localStorage.setItem('mobileAdminOfflineData', JSON.stringify(existingData));
    }
    
    clearOfflineData() {
        localStorage.removeItem('mobileAdminOfflineData');
    }
    
    async uploadOfflineData(data) {
        // Implementation for uploading offline data
        const response = await fetch('/api/admin/sync-offline-data', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(data)
        });
        
        if (!response.ok) {
            throw new Error('Failed to sync offline data');
        }
        
        return response.json();
    }
}

// Initialize mobile admin interface when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    if (window.innerWidth <= 768) {
        window.mobileAdmin = new MobileAdminInterface();
    }
});

// Export for use in other scripts
if (typeof module !== 'undefined' && module.exports) {
    module.exports = MobileAdminInterface;
}